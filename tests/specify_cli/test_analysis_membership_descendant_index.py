"""Membership descendant authority remains exact without rescanning per query."""

from collections.abc import Iterator
from pathlib import Path

from specify_cli.analysis_inputs import _SourceMembership


def test_descendants_preserve_head_index_and_path_boundaries(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    tracked_deleted = root / "authority" / "deleted.md"
    staged_added = root / "authority" / "nested" / "new.md"
    sibling = root / "authority-other" / "other.md"
    membership = _SourceMembership(
        head=frozenset({tracked_deleted, sibling}),
        index={staged_added: ("100644", 0, "H")},
        ignored=(),
        selection_policy=(),
    )

    assert membership.descendants(root / "authority") == frozenset({tracked_deleted, staged_added})
    assert membership.descendants(root / "authority" / "nested") == frozenset({staged_added})
    assert membership.descendants(tracked_deleted) == frozenset()
    assert membership.descendants(root / "absent") == frozenset()
    assert membership.descendants(root) == frozenset({tracked_deleted, staged_added, sibling})


def test_repeated_authority_queries_do_not_rescan_membership(tmp_path: Path) -> None:
    observations = {"visits": 0}

    class ObservedMembership(frozenset[Path]):
        def __iter__(self) -> Iterator[Path]:
            for path in super().__iter__():
                observations["visits"] += 1
                yield path

        def __or__(self, other: frozenset[Path] | set[Path]) -> frozenset[Path]:
            return ObservedMembership(super().__or__(other))

    root = tmp_path / "repo"
    files = [root / "authority" / f"section-{i}" / "source.md" for i in range(80)]
    membership = _SourceMembership(
        head=ObservedMembership(files),
        index={root / "staged" / "new.md": ("100644", 0, "H")},
        ignored=(),
        selection_policy=(),
    )
    for path in files:
        assert membership.descendants(path.parent) == frozenset({path})
    for _ in range(3):
        assert membership.descendants(root / "authority") == frozenset(files)
        assert membership.descendants(root / "absent") == frozenset()

    # Full membership traversal may build an index once; query count must not
    # multiply scans. This measures observed work rather than machine timing.
    assert observations["visits"] <= 2 * (len(files) + len(membership.index))


def test_distinct_observations_do_not_share_stale_membership(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    old = root / "authority" / "old.md"
    new = root / "authority" / "new.md"
    first = _SourceMembership(frozenset({old}), {}, (), ())
    second = _SourceMembership(frozenset({new}), {}, (), ())

    assert first.descendants(root / "authority") == frozenset({old})
    assert second.descendants(root / "authority") == frozenset({new})
    assert first.descendants(root / "authority") == frozenset({old})
