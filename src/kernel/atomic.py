"""Atomic file write utility.

Guarantees: file is either complete old content or complete new content,
never partial. Uses write-to-temp-then-rename on the same filesystem.

Also exposes the canonical *no-op-stable* comparison core (umbrella #1914):
a pure, I/O-free :func:`substantively_equal` that decides whether a freshly
rendered payload differs from existing content *modulo* a caller-supplied
volatile-field projection. Surfaces that re-render tracked files on every run
(charter synthesis, status snapshots, upgrade metadata, ...) share this
comparison so a no-op run leaves the committed bytes untouched and the working
tree clean.

It lives in ``kernel`` (the dependency-free root) rather than
``specify_cli.core`` so the ``charter`` layer can adopt it without crossing the
``charter ↛ specify_cli`` boundary (see
``tests/architectural/test_layer_rules.py`` Invariant 3). specify_cli-level
callers import it directly from ``kernel.atomic``.

Phase 1 (#1914) ships :func:`substantively_equal` with charter synthesis as its
first adopter (via ``src/charter/activation/synthesizer/write_pipeline.py``). A
``write_if_changed`` convenience that gates :func:`atomic_write` on this core —
for byte-comparable writers like status.json (#524) — is deferred to the
Phase-2 convergence so it lands with its first real consumer (the symbol-level
dead-code ratchet forbids shipping it as unwired public surface).
"""

from __future__ import annotations

import contextlib
import os
import tempfile
import secrets

from kernel.no_follow import fd_relative_dir_ops_supported, open_no_follow
from collections.abc import Callable
from pathlib import Path

__all__ = [
    "atomic_write",
    "substantively_equal",
]

# A volatile-field projection: given decoded text and a set of volatile keys,
# return the "substantive content" form that two semantically-identical renders
# produce identically. Pluggable so the core makes NO assumptions about the
# serialization format (the charter YAML-canonical-line stripper is one such
# projection, passed in by the caller — see ``src/charter/synthesizer``).
StripFn = Callable[[str, frozenset[str]], str]


def atomic_write(path: Path, content: str | bytes, *, mkdir: bool = False, durable: bool = False, expected_parent: tuple[int, int] | None = None) -> None:
    """Write *content* atomically to *path*.

    Parameters
    ----------
    path : Path
        Target file path.
    content : str | bytes
        File content. ``str`` is encoded to UTF-8; ``bytes`` is written raw.
    mkdir : bool
        If True, create parent directories before writing (non-durable mode).
    durable : bool
        Opt into private, descriptor-anchored writes and strict file/parent fsync.
        Parent directories must already exist; unsupported capabilities or sync
        failures raise. Failure after replacement leaves the outcome unconfirmed.
    expected_parent : tuple[int, int] | None
        Optional device/inode binding, checked on the open parent descriptor.
        Supported only with durable=True; existing callers retain their contract.
    """
    if durable:
        if mkdir:
            raise ValueError("Durable writes require an existing parent directory")
        _durable_write(path, content.encode("utf-8") if isinstance(content, str) else content, expected_parent)
        return
    if expected_parent is not None:
        raise ValueError("Parent identity binding requires a durable write")
    if mkdir:
        path.parent.mkdir(parents=True, exist_ok=True)

    raw = content.encode("utf-8") if isinstance(content, str) else content

    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".atomic-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        # fd is now closed by the context manager
        Path(tmp_path).replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(fd)
        with contextlib.suppress(OSError):
            Path(tmp_path).unlink()
        raise


def _durable_write(path: Path, raw: bytes, expected_parent: tuple[int, int] | None) -> None:
    """Strict, descriptor-anchored write; sync failure is never durable success.

    Refuses platforms without fd-relative no-follow operations. Existing atomic
    callers retain their original contract. The caller owns a dedicated lock.
    """
    if not fd_relative_dir_ops_supported():
        raise OSError("Strict durable writes are unsupported on this platform")
    candidate = path.absolute()
    if ".." in candidate.parts:
        raise ValueError("Durable path cannot contain parent traversal")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent_fd = open_no_follow(Path(candidate.anchor), flags)
    tmp_name = ".atomic-" + secrets.token_hex(16) + ".tmp"
    try:
        for part in candidate.parent.parts[1:]:
            next_fd = os.open(part, flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        info = os.fstat(parent_fd)
        if expected_parent is not None and (info.st_dev, info.st_ino) != expected_parent:
            raise OSError("Durable parent identity changed")
        fd = os.open(tmp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd)
        try:
            remaining = memoryview(raw)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise OSError("Durable write made no progress")
                remaining = remaining[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp_name, candidate.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name, dir_fd=parent_fd)
        os.close(parent_fd)


def substantively_equal(
    existing: str | bytes,
    candidate: str | bytes,
    *,
    volatile_keys: frozenset[str] = frozenset(),
    strip: StripFn | None = None,
) -> bool:
    """Return True if *candidate* equals *existing* for no-op-stability purposes.

    Pure and I/O-free — the canonical comparison core for umbrella #1914. The
    caller is responsible for reading existing content from disk (and for
    deciding what an *absent* file means); this function only compares two
    in-memory payloads.

    Default behaviour (``strip is None``) is a plain byte/text comparison —
    correct for surfaces whose rendered payload carries no volatile fields
    (e.g. status.json snapshots, #524).

    When a ``strip`` projection is supplied, both sides are decoded to text and
    run through ``strip(text, volatile_keys)`` before comparison; equality
    *modulo* the volatile fields then signals a no-op. The projection is
    pluggable precisely so this core bakes in NO format assumptions — charter
    passes its YAML-canonical-line stripper, a future JSON surface could pass a
    structural projection, etc.

    Parameters
    ----------
    existing, candidate:
        The two payloads to compare. ``str`` is compared as text; ``bytes`` is
        compared raw on the default path and decoded as UTF-8 when a ``strip``
        projection is in play.
    volatile_keys:
        Keys handed to the ``strip`` projection. Ignored on the default path.
    strip:
        Optional volatile-field projection. ``None`` ⇒ pure byte/text compare.
    """
    if strip is None:
        return _as_bytes(existing) == _as_bytes(candidate)
    existing_text = _as_text(existing)
    candidate_text = _as_text(candidate)
    return strip(existing_text, volatile_keys) == strip(candidate_text, volatile_keys)


def _as_bytes(value: str | bytes) -> bytes:
    return value.encode("utf-8") if isinstance(value, str) else value


def _as_text(value: str | bytes) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else value
