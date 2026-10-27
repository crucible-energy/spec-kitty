"""Shared post-base history is not independent concurrent work."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.consolidation.drivers import MergeDriverError, run_event_log_driver

pytestmark = pytest.mark.fast


def _transition(event_id: str, destination: str) -> dict[str, str]:
    return {
        "event_id": event_id,
        "at": event_id,
        "wp_id": "WP01",
        "from_lane": "in_review",
        "to_lane": destination,
    }


def _inputs(tmp_path: Path, *groups: list[dict[str, str]]) -> list[Path]:
    paths = [tmp_path / name for name in ("base", "ours", "theirs")]
    for path, events in zip(paths, groups, strict=True):
        path.write_text("".join(json.dumps(event) + "\n" for event in events))
    return paths


@pytest.mark.parametrize("reverse", [False, True])
def test_shared_review_cycles_merge_with_one_sided_extension(tmp_path: Path, reverse: bool) -> None:
    shared = [_transition("01", "planned"), _transition("02", "approved")]
    extended = [*shared, _transition("03", "approved")]
    sides = (shared, extended) if reverse else (extended, shared)
    base, ours, theirs = _inputs(tmp_path, [], *sides)

    run_event_log_driver(str(base), str(ours), str(theirs))

    assert [json.loads(line) for line in ours.read_text().splitlines()] == extended


@pytest.mark.parametrize("decision", ["planned", "canceled"])
def test_independent_decisions_still_conflict_after_shared_history(tmp_path: Path, decision: str) -> None:
    shared = [_transition("01", "planned"), _transition("02", "approved")]
    base, ours, theirs = _inputs(tmp_path, [], [*shared, _transition("03", decision)], [*shared, _transition("04", "approved")])
    before = ours.read_bytes()

    with pytest.raises(MergeDriverError, match="concurrent transitions"):
        run_event_log_driver(str(base), str(ours), str(theirs))

    assert ours.read_bytes() == before


def test_shared_id_with_conflicting_payload_is_not_shared_history(tmp_path: Path) -> None:
    base, ours, theirs = _inputs(tmp_path, [], [_transition("01", "approved")], [_transition("01", "blocked")])
    before = ours.read_bytes()

    with pytest.raises(MergeDriverError, match="Conflicting payloads"):
        run_event_log_driver(str(base), str(ours), str(theirs))

    assert ours.read_bytes() == before


def test_base_history_is_preserved_when_absent_from_both_sides(tmp_path: Path) -> None:
    original = _transition("01", "planned")
    base, ours, theirs = _inputs(tmp_path, [original], [], [])

    run_event_log_driver(str(base), str(ours), str(theirs))

    assert json.loads(ours.read_text()) == original


def test_malformed_shared_history_refuses_without_writing(tmp_path: Path) -> None:
    base, ours, theirs = _inputs(tmp_path, [], [], [])
    ours.write_text("{invalid}\n")
    before = ours.read_bytes()

    with pytest.raises(MergeDriverError, match="invalid JSON"):
        run_event_log_driver(str(base), str(ours), str(theirs))

    assert ours.read_bytes() == before
