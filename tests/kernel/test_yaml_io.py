"""Unit tests for kernel.yaml_io — shared YAML serialize/atomic-write seam.

The kernel module is zero-dependency shared infrastructure used by
specify_cli, charter, and doctrine. These tests must remain independent of
all higher-level modules.

Coverage:
- serialize_mapping: trailing-whitespace normalization on wrapped scalars,
  safe-load round-trip equality, literal-scalar whitespace preservation,
  CommentedMap round-trip (pins the rt-dumper requirement — a safe dumper
  raises RepresenterError on a CommentedMap, which arbiter relies on).
- write_mapping_atomic: temp-then-rename atomicity, no trailing-whitespace
  lines in the written file.
- _normalize_nonsemantic_trailing_whitespace: YAMLError fallback returns the
  original bytes unchanged.

Red-first note: before src/kernel/yaml_io.py existed, every test in this file
failed at collection with ModuleNotFoundError: No module named 'kernel.yaml_io'.
That is the red-first evidence for this whole module — it was verified by
running this suite against the pre-migration tree (writer.py held the only
copy of the normalizer) before src/kernel/yaml_io.py was created.
"""

from __future__ import annotations

import os as _os
import subprocess
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

from kernel.yaml_io import (
    CANONICAL_YAML_WIDTH,
    _normalize_nonsemantic_trailing_whitespace,
    serialize_mapping,
    write_mapping_atomic,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# serialize_mapping
# ---------------------------------------------------------------------------


def test_serialize_mapping_strips_trailing_whitespace_from_wrapped_scalars() -> None:
    """A long prose scalar that wraps at a NARROW width leaves trailing
    whitespace on the wrap-continuation line; serialize_mapping must strip it,
    and the safe-load round-trip must still equal the original data.
    """
    details = (
        "An analysis-report.md artifact is present for this mission. Review "
        "its findings to understand documented issues and decisions that were "
        "made during implementation, then reconcile them against the record."
    )
    data = {
        "not_helpful": [
            {
                "id": "n-001",
                "category": "doc",
                "summary": "analysis-report.md present with findings",
                "evidence_refs": ["e-007"],
                "details": details,
            }
        ]
    }

    # Precondition guard: prove a dump at a narrow width genuinely wraps and
    # leaves a trailing-whitespace line, so this test cannot silently go
    # vacuous if a future ruamel stops emitting the artifact. Use width=80 to
    # force wrapping regardless of CANONICAL_YAML_WIDTH's own default.
    probe = YAML(typ="rt")
    probe.default_flow_style = False
    probe.preserve_quotes = True
    probe.width = 80
    from io import BytesIO

    probe_buf = BytesIO()
    probe.dump(data, probe_buf)
    raw = probe_buf.getvalue().decode("utf-8")
    assert any(line.endswith((" ", "\t")) for line in raw.splitlines()), "expected the raw dump to contain a trailing-whitespace line; test is vacuous otherwise"

    serialized = serialize_mapping(data, width=80)
    text = serialized.decode("utf-8")

    assert all(not line.endswith((" ", "\t")) for line in text.splitlines())
    assert YAML(typ="safe").load(text) == data


@pytest.mark.parametrize("trailing", [" ", "\t"])
def test_serialize_mapping_preserves_literal_scalar_trailing_whitespace(trailing: str) -> None:
    """A literal block scalar (``|``) may legitimately end a line in
    whitespace — that whitespace is semantically part of the content and
    must survive normalization untouched.
    """
    details = LiteralScalarString(f"first line ends in semantic whitespace{trailing}\nsecond line")

    serialized = serialize_mapping({"details": details})
    loaded = YAML(typ="safe").load(serialized.decode("utf-8"))

    assert loaded == {"details": str(details)}


def test_serialize_mapping_round_trips_commented_map_without_representer_error() -> None:
    """Pin the rt-dumper requirement: a CommentedMap loaded via a round-trip
    YAML instance must serialize through serialize_mapping with NO
    RepresenterError. This is exactly what arbiter's frontmatter-merge does
    (load existing frontmatter, mutate it, re-dump) — a safe (typ='safe')
    dumper raises RepresenterError on a CommentedMap, which is why
    serialize_mapping is contractually rt, not safe.
    """
    loader = YAML(typ="rt")
    loader.preserve_quotes = True
    source = "wp_id: WP07\nreviewer: reviewer-renata\nverdict: rejected\n"
    commented_map = loader.load(source)

    commented_map["arbiter_override"] = {"decided_by": "arbiter", "reason": "override"}

    # Must not raise RepresenterError.
    serialized = serialize_mapping(commented_map)

    loaded = YAML(typ="safe").load(serialized.decode("utf-8"))
    assert loaded["wp_id"] == "WP07"
    assert loaded["arbiter_override"] == {"decided_by": "arbiter", "reason": "override"}


def test_canonical_yaml_width_is_4096() -> None:
    assert CANONICAL_YAML_WIDTH == 4096


# ---------------------------------------------------------------------------
# write_mapping_atomic
# ---------------------------------------------------------------------------


def test_write_mapping_atomic_uses_temp_then_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The write must go through a .tmp sibling file and an os.replace rename
    — never a direct write to the target path.
    """
    target = tmp_path / "record.yaml"
    captured_replace: list[tuple[str, str]] = []
    original_replace = _os.replace

    def capturing_replace(src: str, dst: str) -> None:
        captured_replace.append((src, dst))
        original_replace(src, dst)

    monkeypatch.setattr(_os, "replace", capturing_replace)

    write_mapping_atomic({"x": 1}, target)

    assert len(captured_replace) == 1
    src_path, dst_path = captured_replace[0]
    assert Path(src_path).parent == target.parent
    assert ".tmp" in Path(src_path).name
    assert Path(dst_path) == target
    assert target.exists()
    assert not Path(src_path).exists()


def test_write_mapping_atomic_output_has_no_trailing_whitespace_lines(tmp_path: Path) -> None:
    target = tmp_path / "record.yaml"
    details = (
        "An analysis-report.md artifact is present for this mission. Review "
        "its findings to understand documented issues and decisions that were "
        "made during implementation, then reconcile them against the record."
    )
    write_mapping_atomic({"details": details}, target, width=80)

    text = target.read_text(encoding="utf-8")
    assert all(not line.endswith((" ", "\t")) for line in text.splitlines())
    assert YAML(typ="safe").load(text) == {"details": details}


def test_write_mapping_atomic_mkdir_creates_parent(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir" / "record.yaml"
    assert not target.parent.exists()

    write_mapping_atomic({"x": 1}, target, mkdir=True)

    assert target.exists()
    assert YAML(typ="safe").load(target.read_text(encoding="utf-8")) == {"x": 1}


def test_write_mapping_atomic_cleans_up_tempfile_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "record.yaml"

    def failing_write(fd: int, data: bytes) -> int:
        raise OSError("Simulated disk full")

    monkeypatch.setattr(_os, "write", failing_write)

    with pytest.raises(OSError):
        write_mapping_atomic({"x": 1}, target)

    assert not target.exists()
    leftover = [f for f in tmp_path.iterdir() if ".tmp" in f.name]
    assert leftover == [], f"Unexpected tempfiles left behind: {leftover}"


def test_write_mapping_atomic_crash_leaves_no_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "record.yaml"

    def crashing_replace(src: str, dst: str) -> None:
        raise OSError("Simulated crash mid-replace")

    monkeypatch.setattr(_os, "replace", crashing_replace)

    with pytest.raises(OSError):
        write_mapping_atomic({"x": 1}, target)

    assert not target.exists()


def test_write_mapping_atomic_dir_fsync_failure_is_non_fatal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Best-effort dir fsync failure does not propagate; the write still
    succeeds.
    """
    target = tmp_path / "record.yaml"
    original_fsync = _os.fsync
    fsync_call_count = [0]

    def flaky_fsync(fd: int) -> None:
        fsync_call_count[0] += 1
        # Fail only the second call (the directory fsync, after the file fsync).
        if fsync_call_count[0] >= 2:
            raise OSError("Simulated directory fsync failure")
        original_fsync(fd)

    monkeypatch.setattr(_os, "fsync", flaky_fsync)

    write_mapping_atomic({"x": 1}, target)

    assert target.exists()


# ---------------------------------------------------------------------------
# _normalize_nonsemantic_trailing_whitespace — YAMLError fallback
# ---------------------------------------------------------------------------


def test_normalize_yaml_error_fallback_returns_original_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the safety re-parse cannot confirm the normalized form is
    semantically identical (because it can't be parsed at all), the original
    (un-normalized) bytes must be returned unchanged.
    """
    from ruamel.yaml.error import YAMLError

    original = b"key: value \nother: thing\t\n"

    class ExplodingYAML:
        def __init__(self, typ: str = "safe") -> None:
            pass

        def load(self, stream: object) -> None:
            raise YAMLError("simulated unparsable input")

    import kernel.yaml_io as yaml_io_module

    monkeypatch.setattr(yaml_io_module, "YAML", ExplodingYAML)

    result = _normalize_nonsemantic_trailing_whitespace(original)
    assert result == original


def test_normalize_no_trailing_whitespace_is_a_noop() -> None:
    """When there is nothing to strip, the normalizer must return the exact
    same bytes object content without touching the YAML parser at all.
    """
    original = b"key: value\nother: thing\n"
    assert _normalize_nonsemantic_trailing_whitespace(original) == original


@pytest.mark.parametrize("mask", [0o022, 0o077])
def test_private_yaml_mode_precedes_first_payload_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mask: int) -> None:
    target = tmp_path / "private.yaml"
    target.write_text("original: true\n")
    target.chmod(0o600)
    original_write = _os.write
    observed: list[int] = []

    def inspect_write(fd: int, data: bytes) -> int:
        observed.append(_os.fstat(fd).st_mode & 0o777)
        return original_write(fd, data)

    monkeypatch.setattr(_os, "write", inspect_write)
    previous = _os.umask(mask)
    try:
        write_mapping_atomic({"private": "synthetic"}, target)
    finally:
        _os.umask(previous)
    assert observed and set(observed) == {0o600}
    assert target.stat().st_mode & 0o777 == 0o600


def test_atomic_yaml_completes_short_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "short.yaml"
    original_write = _os.write
    monkeypatch.setattr(_os, "write", lambda fd, data: original_write(fd, data[:2]))
    write_mapping_atomic({"message": "complete synthetic value"}, target)
    assert YAML(typ="safe").load(target.read_bytes()) == {"message": "complete synthetic value"}


def test_atomic_yaml_zero_progress_preserves_original(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "zero.yaml"
    original = b"original: true\n"
    target.write_bytes(original)
    monkeypatch.setattr(_os, "write", lambda fd, data: 0)
    with pytest.raises(OSError):
        write_mapping_atomic({"replacement": True}, target)
    assert target.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp.*"))


def test_atomic_yaml_exclusive_collision_preserves_foreign_temporary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "collision.yaml"
    monkeypatch.setattr(_os, "urandom", lambda length: b"\x01" * length)
    foreign = target.with_name(f"{target.name}.tmp.{_os.getpid()}.01010101")
    foreign.write_bytes(b"foreign successor")
    with pytest.raises(FileExistsError):
        write_mapping_atomic({"replacement": True}, target)
    assert foreign.read_bytes() == b"foreign successor"
    assert not target.exists()


def test_atomic_yaml_refuses_target_replacement_before_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "changed.yaml"
    target.write_bytes(b"original: true\n")
    original_write = _os.write
    replaced = False

    def replace_during_write(fd: int, data: bytes) -> int:
        nonlocal replaced
        if not replaced:
            replaced = True
            successor = tmp_path / "successor.yaml"
            successor.write_bytes(b"successor: retained\n")
            successor.replace(target)
        return original_write(fd, data)

    monkeypatch.setattr(_os, "write", replace_during_write)
    with pytest.raises(OSError):
        write_mapping_atomic({"replacement": True}, target)
    assert target.read_bytes() == b"successor: retained\n"


@pytest.mark.parametrize("mask, expected", [(0o022, 0o644), (0o077, 0o600)])
def test_new_yaml_keeps_caller_umask(tmp_path: Path, mask: int, expected: int) -> None:
    target = tmp_path / "new.yaml"
    previous = _os.umask(mask)
    try:
        write_mapping_atomic({"synthetic": True}, target)
    finally:
        _os.umask(previous)
    assert target.stat().st_mode & 0o777 == expected


def test_atomic_yaml_refuses_symlink_without_touching_referent(tmp_path: Path) -> None:
    referent = tmp_path / "original.yaml"
    referent.write_bytes(b"original: retained\n")
    target = tmp_path / "link.yaml"
    target.symlink_to(referent)
    with pytest.raises(OSError):
        write_mapping_atomic({"replacement": True}, target)
    assert target.is_symlink()
    assert referent.read_bytes() == b"original: retained\n"
    assert not list(tmp_path.glob("*.tmp.*"))


def test_atomic_yaml_refuses_nonregular_and_setid_destinations(tmp_path: Path) -> None:
    directory = tmp_path / "directory.yaml"
    directory.mkdir()
    with pytest.raises(OSError):
        write_mapping_atomic({"replacement": True}, directory)
    target = tmp_path / "privileged.yaml"
    target.write_bytes(b"original: retained\n")
    target.chmod(0o4600)
    try:
        with pytest.raises(OSError):
            write_mapping_atomic({"replacement": True}, target)
        assert target.read_bytes() == b"original: retained\n"
    finally:
        target.chmod(0o600)


@pytest.mark.parametrize("initially_present", [False, True])
def test_atomic_yaml_refuses_destination_arrival_or_mode_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, initially_present: bool) -> None:
    target = tmp_path / "changing.yaml"
    if initially_present:
        target.write_bytes(b"original: retained\n")
        target.chmod(0o600)
    original_write = _os.write

    def change_target(fd: int, data: bytes) -> int:
        if initially_present:
            target.chmod(0o640)
        else:
            target.write_bytes(b"successor: retained\n")
        return original_write(fd, data)

    monkeypatch.setattr(_os, "write", change_target)
    with pytest.raises(OSError):
        write_mapping_atomic({"replacement": True}, target)
    assert target.read_bytes() == (b"original: retained\n" if initially_present else b"successor: retained\n")
    if initially_present:
        assert target.stat().st_mode & 0o777 == 0o640


def test_atomic_yaml_preserves_foreign_temporary_successor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "temporary.yaml"
    target.write_bytes(b"original: retained\n")
    monkeypatch.setattr(_os, "urandom", lambda length: b"\x02" * length)
    temporary = target.with_name(f"{target.name}.tmp.{_os.getpid()}.02020202")
    original_write = _os.write

    def replace_temporary(fd: int, data: bytes) -> int:
        count = original_write(fd, data)
        temporary.unlink()
        temporary.write_bytes(b"foreign successor")
        return count

    monkeypatch.setattr(_os, "write", replace_temporary)
    with pytest.raises(OSError):
        write_mapping_atomic({"replacement": True}, target)
    assert temporary.read_bytes() == b"foreign successor"
    assert target.read_bytes() == b"original: retained\n"


def test_atomic_yaml_refuses_parent_redirection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    target = parent / "record.yaml"
    target.write_bytes(b"original: retained\n")
    saved = tmp_path / "original-parent"
    original_write = _os.write

    def redirect_parent(fd: int, data: bytes) -> int:
        count = original_write(fd, data)
        parent.rename(saved)
        parent.mkdir()
        target.write_bytes(b"successor: retained\n")
        return count

    monkeypatch.setattr(_os, "write", redirect_parent)
    with pytest.raises(OSError):
        write_mapping_atomic({"replacement": True}, target)
    assert target.read_bytes() == b"successor: retained\n"
    assert (saved / "record.yaml").read_bytes() == b"original: retained\n"


@pytest.mark.skipif(sys.platform != "darwin", reason="Native Darwin ACL contract")
def test_atomic_yaml_refuses_native_extended_acl(tmp_path: Path) -> None:
    target = tmp_path / "acl.yaml"
    original = b"original: retained\n"
    target.write_bytes(original)
    subprocess.run(
        ["/bin/chmod", "+a", "everyone allow read", str(target)],
        check=True,
        capture_output=True,
        timeout=5,
    )
    try:
        with pytest.raises(OSError, match="ACL"):
            write_mapping_atomic({"replacement": True}, target)
        assert target.read_bytes() == original
        assert not list(tmp_path.glob("*.tmp.*"))
    finally:
        subprocess.run(
            ["/bin/chmod", "-N", str(target)],
            check=True,
            capture_output=True,
            timeout=5,
        )


@pytest.mark.parametrize("attribute", ["system.posix_acl_access", "security.selinux"])
def test_atomic_yaml_refuses_unsupported_access_metadata_before_effects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, attribute: str) -> None:
    """Exercise the xattr API contract even on hosts without that native API."""
    target = tmp_path / "private.yaml"
    original = b"original: retained\n"
    target.write_bytes(original)
    target.chmod(0o600)
    before = target.stat()
    inspected: list[Path] = []

    def names(path: Path, *, follow_symlinks: bool) -> list[str]:
        assert follow_symlinks is False
        inspected.append(path)
        return [attribute]

    monkeypatch.setattr(_os, "listxattr", names, raising=False)
    with pytest.raises(OSError, match="Unsupported access-control metadata"):
        write_mapping_atomic({"replacement": True}, target)
    assert inspected == [tmp_path], "refuse at the parent before temporary or target effects"
    after = target.stat()
    assert all(
        getattr(before, field) == getattr(after, field)
        for field in ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")
    )
    assert target.read_bytes() == original
    assert list(tmp_path.iterdir()) == [target]
