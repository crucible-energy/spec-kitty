"""Shared YAML serialization and durable-write primitives for the kernel layer.

Canonical home for the house YAML-dump conventions used by every writer that
persists a mapping (dict / ``CommentedMap``) as YAML: round-trip dumper (so
``ruamel`` comment/quote/anchor fidelity and ``CommentedMap`` inputs survive),
a wide fixed line width (so wrapped prose never fragments a scalar across
lines), and a post-dump normalizer that strips the non-semantic trailing
whitespace ``ruamel`` leaves on wrapped-scalar continuation lines.

Adopted by ``specify_cli.retrospective.writer`` (moved here verbatim) and
``specify_cli.review.arbiter`` (#3058) so both surfaces share one seam instead
of hand-rolling the same dump-then-normalize dance with drifting width
settings.
"""

from __future__ import annotations

import contextlib
import errno
import os
import stat
import sys
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from kernel.no_follow import chmod_fd, open_no_follow

__all__ = [
    "serialize_mapping",
    "write_mapping_atomic",
]

# Matches the house "prevent line wrapping" width used across writers
# (e.g. ``specify_cli.review.artifacts._make_yaml``): wide enough that no
# reviewer-prose or retrospective-detail scalar wraps under normal use.
CANONICAL_YAML_WIDTH = 4096


def serialize_mapping(data: Mapping[str, Any], *, width: int = CANONICAL_YAML_WIDTH) -> bytes:
    """Serialize a mapping to canonical YAML bytes.

    Uses a round-trip (``typ="rt"``) dumper, not a safe dumper: a safe dumper
    raises ``RepresenterError`` on a ``ruamel.yaml.comments.CommentedMap``
    (arbiter and other frontmatter-merge callers pass one in, since they load
    existing frontmatter with ``preserve_quotes=True`` before mutating it),
    and it would also strip the comment/quote fidelity round-trip is for.

    The dump is post-processed by :func:`_normalize_nonsemantic_trailing_whitespace`
    to remove the trailing-space/tab artifacts ``ruamel`` leaves on wrapped
    scalar continuation lines, without touching semantically-significant
    trailing whitespace inside literal block scalars.
    """
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.width = width

    buf = BytesIO()
    yaml.dump(data, buf)
    return _normalize_nonsemantic_trailing_whitespace(buf.getvalue())


def _normalize_nonsemantic_trailing_whitespace(serialized: bytes) -> bytes:
    """Remove writer wrapping artifacts only when YAML meaning remains unchanged.

    Falls back to the original bytes if the safety re-parse cannot confirm the
    normalized form is semantically identical, so normalization is never worse
    than emitting the un-normalized dump.
    """
    normalized = b"\n".join(line.rstrip(b" \t\r") for line in serialized.split(b"\n"))
    if normalized == serialized:
        return serialized

    yaml = YAML(typ="safe")
    try:
        original_data = yaml.load(serialized)
        normalized_data = yaml.load(normalized)
    except YAMLError:
        return serialized
    return normalized if normalized_data == original_data else serialized


def _file_preimage(info: os.stat_result | None) -> tuple[int, ...] | None:
    if info is None:
        return None
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_uid,
        info.st_gid,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        getattr(info, "st_flags", 0),
    )


def _refuse_privileged_metadata(path: Path) -> None:
    """Refuse access-control metadata this permission-only writer cannot retain."""
    if hasattr(os, "listxattr"):
        names = os.listxattr(path, follow_symlinks=False)
        if any(name.startswith(("system.posix_acl_", "security.")) for name in names):
            raise OSError(f"Unsupported access-control metadata on {path}")
    if sys.platform == "darwin":
        # Darwin ACLs are not exposed by listxattr. Inspect the native ACL;
        # neither copy it nor infer its absence from ordinary Unix mode bits.
        import ctypes

        libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
        libc.acl_get_fd_np.argtypes = [ctypes.c_int, ctypes.c_int]
        libc.acl_get_fd_np.restype = ctypes.c_void_p
        libc.acl_get_entry.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
        libc.acl_get_entry.restype = ctypes.c_int
        libc.acl_free.argtypes = [ctypes.c_void_p]
        libc.acl_free.restype = ctypes.c_int
        fd = open_no_follow(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        acl = None
        try:
            before = os.fstat(fd)
            acl = libc.acl_get_fd_np(fd, 0x100)  # ACL_TYPE_EXTENDED
            if not acl:
                error = ctypes.get_errno()
                # Darwin reports an absent FILESEC_ACL property as ENOENT.
                # A live no-follow descriptor and matching path distinguish
                # that case from a missing or replaced filesystem object.
                if error == errno.ENOENT and _file_preimage(before) == _file_preimage(os.fstat(fd)) == _file_preimage(path.lstat()):
                    return
                raise OSError(error, os.strerror(error), str(path))
            entry = ctypes.c_void_p()
            result = libc.acl_get_entry(acl, 0, ctypes.byref(entry))  # ACL_FIRST_ENTRY
            if result == 0:
                raise OSError(f"Unsupported extended ACL on {path}")
            # Apple's API returns -1/EINVAL at the end of a valid ACL,
            # including an empty ACL (unlike Linux's 1/0 iteration API).
            # This handle came directly from successful acl_get_fd_np above.
            if ctypes.get_errno() != errno.EINVAL:
                error = ctypes.get_errno()
                raise OSError(error, os.strerror(error), str(path))
        finally:
            try:
                if acl:
                    libc.acl_free(acl)
            finally:
                os.close(fd)


def _destination_stat(path: Path) -> os.stat_result | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o7000 or getattr(info, "st_flags", 0):
        raise OSError(f"Unsupported YAML destination type or privilege metadata: {path}")
    _refuse_privileged_metadata(path)
    return info


def write_mapping_atomic(
    data: Mapping[str, Any],
    path: Path,
    *,
    width: int = CANONICAL_YAML_WIDTH,
    mkdir: bool = False,
) -> None:
    """Write complete YAML durably, preserving supported existing permissions.

    Existing regular-file modes apply before the first payload write. New
    files retain 0644 filtered by the caller's umask. Unsupported access-control
    metadata is refused rather than silently copied or discarded. Ordinary
    extended attributes are outside this permission-only contract.

    Sequence:
    1. Serialize ``data`` via :func:`serialize_mapping`.
    2. Write to a uniquely-named ``.tmp`` file in ``path.parent`` (created
       ``O_WRONLY | O_CREAT | O_EXCL`` so two concurrent writers never
       collide), ``fsync`` the file descriptor, close.
    3. ``os.replace(tmp, path)`` — atomic rename.
    4. Best-effort ``fsync`` on the parent directory fd to flush the rename
       into the directory inode (non-fatal on failure).

    A changed destination or parent preimage refuses publication. This is a
    detected-change check, not atomic compare-and-swap: callers must coordinate
    concurrent writers, including the interval after the final check. Platforms
    without descriptor chmod use the existing no_follow helper's path fallback;
    native Windows ACL preservation is not claimed.

    Cleanup touches only the exact temporary created here, still matching its
    final observed identity. A create collision or foreign replacement remains
    untouched. Original exceptions propagate; directory fsync stays best effort.
    """
    path = path.absolute()
    if mkdir:
        path.parent.mkdir(parents=True, exist_ok=True)

    serialized = serialize_mapping(data, width=width)
    parent_path = path.parent.resolve(strict=True)
    parent_info = path.parent.lstat()
    if not stat.S_ISDIR(parent_info.st_mode):
        raise OSError(f"Unsupported YAML parent: {path.parent}")
    parent_identity = (parent_info.st_dev, parent_info.st_ino, parent_info.st_mode, parent_info.st_uid, parent_info.st_gid)
    _refuse_privileged_metadata(path.parent)
    original = _destination_stat(path)

    tmp_name = f"{path.name}.tmp.{os.getpid()}.{os.urandom(4).hex()}"
    tmp_path = path.parent / tmp_name

    temporary: os.stat_result | None = None
    try:
        fd = os.open(str(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            temporary = os.fstat(fd)
            if original is not None:
                if (temporary.st_uid, temporary.st_gid) != (original.st_uid, original.st_gid):
                    raise OSError(f"Unsupported YAML ownership change: {path}")
                chmod_fd(fd, tmp_path, stat.S_IMODE(original.st_mode))
            offset = 0
            while offset < len(serialized):
                count = os.write(fd, serialized[offset:])
                if count <= 0:
                    raise OSError("YAML temporary write made no progress")
                offset += count
            os.fsync(fd)
        finally:
            try:
                temporary = os.fstat(fd)
            finally:
                os.close(fd)

        current_parent = path.parent.lstat()
        if (
            path.parent.resolve(strict=True) != parent_path
            or (current_parent.st_dev, current_parent.st_ino, current_parent.st_mode, current_parent.st_uid, current_parent.st_gid) != parent_identity
        ):
            raise OSError(f"YAML parent changed before publication: {path.parent}")
        _refuse_privileged_metadata(path.parent)
        if _file_preimage(_destination_stat(path)) != _file_preimage(original):
            raise OSError(f"YAML destination changed before publication: {path}")
        if _file_preimage(tmp_path.lstat()) != _file_preimage(temporary):
            raise OSError(f"YAML temporary changed before publication: {tmp_path}")

        os.replace(str(tmp_path), str(path))

        # Best-effort dir fsync.
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    except Exception:
        with contextlib.suppress(OSError):
            if temporary is not None and _file_preimage(tmp_path.lstat()) == _file_preimage(temporary):
                tmp_path.unlink()
        raise
