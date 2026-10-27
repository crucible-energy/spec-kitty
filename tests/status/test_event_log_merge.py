"""Tests for semantic merging of status.events.jsonl files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.status.event_log_merge import (
    EventLogMergeError,
    _read_event_file,
    merge_event_log_files,
    merge_event_payloads,
)

pytestmark = pytest.mark.fast

runner = CliRunner()


def _event(event_id: str, at: str, wp_id: str = "WP01") -> dict[str, object]:
    return {
        "actor": "tester",
        "at": at,
        "event_id": event_id,
        "execution_mode": "worktree",
        "force": False,
        "from_lane": "planned",
        "mission_slug": "079-post-555-release-hardening",
        "reason": None,
        "review_ref": None,
        "to_lane": "claimed",
        "wp_id": wp_id,
    }


def _write_jsonl(path: Path, payloads: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(payload, sort_keys=True) + "\n" for payload in payloads),
        encoding="utf-8",
    )


def test_merge_event_payloads_deduplicates_and_sorts() -> None:
    base = [_event("01AAA000000000000000000001", "2026-04-09T06:00:00Z")]
    ours = [_event("01BBB000000000000000000002", "2026-04-09T06:02:00Z")]
    theirs = [
        _event("01AAA000000000000000000001", "2026-04-09T06:00:00Z"),
        _event("01CCC000000000000000000003", "2026-04-09T06:01:00Z"),
    ]

    merged = merge_event_payloads(base, ours, theirs)

    assert [payload["event_id"] for payload in merged] == [
        "01AAA000000000000000000001",
        "01CCC000000000000000000003",
        "01BBB000000000000000000002",
    ]


def test_merge_event_payloads_rejects_conflicting_duplicate_event_id() -> None:
    original = _event("01DDD000000000000000000004", "2026-04-09T06:00:00Z")
    conflicting = dict(original)
    conflicting["to_lane"] = "blocked"

    with pytest.raises(EventLogMergeError, match="Conflicting payloads"):
        merge_event_payloads([original], [conflicting])


def test_merge_event_log_files_writes_union_to_output_path(tmp_path: Path) -> None:
    base_path = tmp_path / "base.jsonl"
    ours_path = tmp_path / "ours.jsonl"
    theirs_path = tmp_path / "theirs.jsonl"
    output_path = tmp_path / "merged.jsonl"

    _write_jsonl(base_path, [_event("01AAA000000000000000000001", "2026-04-09T06:00:00Z")])
    _write_jsonl(ours_path, [_event("01BBB000000000000000000002", "2026-04-09T06:01:00Z")])
    _write_jsonl(theirs_path, [_event("01CCC000000000000000000003", "2026-04-09T06:02:00Z")])

    merge_event_log_files(
        base_path=base_path,
        ours_path=ours_path,
        theirs_path=theirs_path,
        output_path=output_path,
    )

    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert [json.loads(line)["event_id"] for line in lines] == [
        "01AAA000000000000000000001",
        "01BBB000000000000000000002",
        "01CCC000000000000000000003",
    ]


def test_merge_driver_event_log_cli_reports_validation_errors(tmp_path: Path) -> None:
    base_path = tmp_path / "base.jsonl"
    ours_path = tmp_path / "ours.jsonl"
    theirs_path = tmp_path / "theirs.jsonl"
    _write_jsonl(base_path, [_event("01AAA000000000000000000001", "2026-04-09T06:00:00Z")])
    ours_path.write_text("{bad json}\n", encoding="utf-8")
    _write_jsonl(theirs_path, [_event("01BBB000000000000000000002", "2026-04-09T06:01:00Z")])

    result = runner.invoke(
        cli_app,
        [
            "merge-driver-event-log",
            str(base_path),
            str(ours_path),
            str(theirs_path),
        ],
    )

    assert result.exit_code == 1
    assert "invalid JSON" in result.output


def test_read_event_file_missing_path_returns_empty_list(tmp_path: Path) -> None:
    assert _read_event_file(tmp_path / "missing.jsonl") == []


def test_read_event_file_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        "\n" + json.dumps(_event("01AAA000000000000000000001", "2026-04-09T06:00:00Z"), sort_keys=True) + "\n\n",
        encoding="utf-8",
    )

    assert _read_event_file(path) == [_event("01AAA000000000000000000001", "2026-04-09T06:00:00Z")]


def test_read_event_file_rejects_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('["not", "an", "object"]\n', encoding="utf-8")

    with pytest.raises(EventLogMergeError, match="is not a JSON object"):
        _read_event_file(path)


def test_read_event_file_requires_event_id(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"at": "2026-04-09T06:00:00Z"}, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(EventLogMergeError, match="missing a valid event_id"):
        _read_event_file(path)


def test_read_event_file_accepts_event_without_timestamp(tmp_path: Path) -> None:
    # Non-status event types (e.g. tracker events) may lack 'at'/'timestamp';
    # they must be accepted so the merge driver handles mixed event logs.
    payload = {"event_id": "01AAA000000000000000000001"}
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    events = _read_event_file(path)
    assert len(events) == 1
    assert events[0]["event_id"] == "01AAA000000000000000000001"


def test_merge_event_payloads_mixed_at_timestamp_neither() -> None:
    """AC-F2 (FR-008c, WP03): mixed-schema event logs sort deterministically.

    The sort key is the two-tuple
    ``(str(payload.get("at") or payload.get("timestamp", "")), event_id)``:

    * an event carrying ``at`` sorts by ``at``;
    * an event carrying only ``timestamp`` sorts by ``timestamp``;
    * an event carrying neither sorts by the empty string (i.e. FIRST);
    * the **tie-break is the ULID ``event_id``**, which makes the ordering
      total — two events never compare equal, so the result is stable across
      repeated runs and across input-group permutations.
    """
    at_only = _event("01BBB000000000000000000002", "2026-04-09T06:02:00Z")
    timestamp_only: dict[str, object] = {
        "event_id": "01CCC000000000000000000003",
        "timestamp": "2026-04-09T06:01:00Z",
    }
    neither_a: dict[str, object] = {"event_id": "01AAA000000000000000000001"}
    neither_b: dict[str, object] = {"event_id": "01AAB000000000000000000004"}

    expected_order = [
        "01AAA000000000000000000001",  # no key → "" sorts first; ULID tie-break
        "01AAB000000000000000000004",
        "01CCC000000000000000000003",  # timestamp 06:01
        "01BBB000000000000000000002",  # at 06:02
    ]

    forward = merge_event_payloads([at_only], [timestamp_only], [neither_a, neither_b])
    reversed_groups = merge_event_payloads([neither_b, neither_a], [timestamp_only], [at_only])

    assert [payload["event_id"] for payload in forward] == expected_order
    assert forward == reversed_groups, "mixed-schema sort must be deterministic and total across input permutations (AC-F2)"
    # Repeated runs over identical input are byte-stable.
    assert merge_event_payloads([at_only], [timestamp_only], [neither_a, neither_b]) == forward


@pytest.mark.parametrize("left,right", [(True, 1), (False, 0), (1, 1.0), ([True], [1])])
def test_merge_event_payloads_preserves_typed_json_identity(left: object, right: object) -> None:
    original = {**_event("01TYPED000000000000000001", "2026-10-27T00:00:00Z"), "policy_metadata": {"opaque": {"approved": left}}}
    conflicting = {**original, "policy_metadata": {"opaque": {"approved": right}}}
    with pytest.raises(EventLogMergeError, match="Conflicting payloads"):
        merge_event_payloads([original], [conflicting])


def test_actual_driver_refuses_nested_typed_json_identity_collision_without_writing(tmp_path: Path) -> None:
    from specify_cli.consolidation.drivers import MergeDriverError, run_event_log_driver

    base, ours, theirs = [tmp_path / name for name in ("base.jsonl", "ours.jsonl", "theirs.jsonl")]
    original = {**_event("01TYPED000000000000000002", "2026-10-27T00:00:00Z"), "policy_metadata": {"opaque": {"approved": True}}}
    conflicting = {**original, "policy_metadata": {"opaque": {"approved": 1}}}
    _write_jsonl(base, [])
    _write_jsonl(ours, [original])
    _write_jsonl(theirs, [conflicting])
    before = ours.read_bytes()
    with pytest.raises(MergeDriverError, match="Conflicting payloads"):
        run_event_log_driver(str(base), str(ours), str(theirs))
    assert ours.read_bytes() == before


def test_typed_json_identity_collision_is_not_shared_fork_history() -> None:
    from specify_cli.status import detect_concurrent_fork

    original = {
        **_event("01TYPED000000000000000003", "2026-10-27T00:00:00Z"),
        "from_lane": "in_review",
        "to_lane": "planned",
        "policy_metadata": {"opaque": {"approved": True}},
    }
    conflicting = {**original, "policy_metadata": {"opaque": {"approved": 1}}}
    approval = {**_event("01TYPED000000000000000004", "2026-10-27T00:00:01Z"), "from_lane": "in_review", "to_lane": "approved"}
    assert detect_concurrent_fork([], [original], [conflicting, approval]) is not None


def test_equivalent_typed_json_key_orders_still_deduplicate() -> None:
    original = {**_event("01TYPED000000000000000005", "2026-10-27T00:00:00Z"), "policy_metadata": {"opaque": {"approved": True, "count": 1}}}
    reordered = {**original, "policy_metadata": {"opaque": {"count": 1, "approved": True}}}
    assert merge_event_payloads([original], [reordered]) == [original]
