"""NUL-safe inventory retains detached HEADs and literal workspace paths."""

from pathlib import Path

import pytest

from kernel.git.worktree_registry import parse_worktree_records

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_literal_paths_detached_and_bare_records() -> None:
    # Virtual protocol paths are parsed only; no shared filesystem location is used.
    raw = b"worktree /fixture/a path\nwith newline\0HEAD " + b"a" * 40 + b"\0detached\0\0worktree /fixture/bare\0bare\0\0"
    records = parse_worktree_records(raw)
    assert records[0].path == Path("/fixture/a path\nwith newline")
    assert records[0].head == "a" * 40
    assert records[0].detached and records[0].branch is None
    assert records[1].bare and records[1].head is None


@pytest.mark.parametrize(
    "raw",
    [
        b"worktree /fixture/a\0\xff bad\0\0",
        b"HEAD a\0\0",
        b"worktree /fixture/a\0worktree /fixture/b\0\0",
        b"worktree /fixture/a\0HEAD bad\0\0",
        b"worktree /fixture/a\0HEAD " + b"a" * 40 + b"\0branch refs/heads/a\0detached\0\0",
    ],
)
def test_ambiguous_inventory_refuses(raw: bytes) -> None:
    with pytest.raises(ValueError, match="Workspace inventory"):
        parse_worktree_records(raw)


def test_inventory_is_bounded() -> None:
    with pytest.raises(ValueError, match="bounded scope"):
        parse_worktree_records(b"worktree /fixture/a\0bare\0\0" * 2, max_records=1)
