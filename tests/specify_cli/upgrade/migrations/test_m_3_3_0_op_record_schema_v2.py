"""Targeted tests for Op record schema-v2 migration helpers (3.3.0)."""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path

import pytest

import specify_cli.upgrade.migrations.m_3_3_0_op_record_schema_v2 as migration
from specify_cli.invocation.record import REDACTED_REQUEST_SUMMARY


pytestmark = [pytest.mark.unit, pytest.mark.fast]

_INVOCATION_ID = "01ABCDEFGHJKMNPQRSTVWXYZ12"
_VALID_DIGEST = "sha256:" + "a" * 64


def test_eligible_files_only_includes_ulid_records(tmp_path: Path) -> None:
    ops_dir = tmp_path / "kitty-ops"
    ops_dir.mkdir(parents=True)

    valid = ops_dir / f"{_INVOCATION_ID}.jsonl"
    valid.write_text("", encoding="utf-8")

    non_invocation = ops_dir / "notes.jsonl"
    non_invocation.write_text("", encoding="utf-8")

    assert migration._eligible_files(tmp_path) == [valid]


def test_file_scans_contain_os_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ops_dir = tmp_path / "kitty-ops"
    ops_dir.mkdir(parents=True)
    original_glob = Path.glob

    def _unreadable_glob(path: Path, pattern: str) -> Iterator[Path]:
        if path == ops_dir:
            raise OSError("directory became unreadable")
        return original_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", _unreadable_glob)

    assert migration._eligible_files(tmp_path) == []
    assert migration._quarantined_files(tmp_path) == []
    assert migration.OpRecordSchemaV2Migration().detect(tmp_path) is False


def test_worktree_scan_contains_os_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    worktrees_dir = tmp_path / ".worktrees"
    worktrees_dir.mkdir()
    original_iterdir = Path.iterdir

    def _unreadable_iterdir(path: Path) -> Iterator[Path]:
        if path == worktrees_dir:
            raise OSError("directory became unreadable")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", _unreadable_iterdir)

    assert migration._checkout_roots(tmp_path) == [tmp_path]
    assert migration.OpRecordSchemaV2Migration().detect(tmp_path) is False


@pytest.mark.parametrize("failure", [None, "fsync", "open"])
def test_fsync_dir_closes_opened_descriptor_when_supported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str | None) -> None:
    calls: list[tuple[str, int]] = []

    def _open(_path: Path, _flags: int) -> int:
        if failure == "open":
            raise OSError("unsupported")
        calls.append(("open", 17))
        return 17

    def _fsync(descriptor: int) -> None:
        calls.append(("fsync", descriptor))
        if failure == "fsync":
            raise OSError("unsupported")

    def _close(descriptor: int) -> None:
        calls.append(("close", descriptor))

    monkeypatch.setattr(migration.os, "open", _open)
    monkeypatch.setattr(migration.os, "fsync", _fsync)
    monkeypatch.setattr(migration.os, "close", _close)

    migration._fsync_dir(tmp_path)

    expected = [] if failure == "open" else [("open", 17), ("fsync", 17), ("close", 17)]
    assert calls == expected


def test_atomic_rewrite_fsyncs_parent_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / f"{_INVOCATION_ID}.jsonl"
    path.write_text("before\n", encoding="utf-8")
    synced: list[Path] = []
    monkeypatch.setattr(migration, "_fsync_dir", synced.append)

    assert migration._atomic_rewrite(path, ["after"], ["before"])
    assert synced == [tmp_path]


def test_apply_reports_unvisited_lane_with_legacy_records(tmp_path: Path) -> None:
    (tmp_path / "kitty-ops").mkdir()
    lane_ops = tmp_path / ".worktrees" / "lane-a" / "kitty-ops"
    lane_ops.mkdir(parents=True)
    (lane_ops / f"{_INVOCATION_ID}.jsonl").write_text(
        json.dumps(
            {
                "event": "started",
                "invocation_id": _INVOCATION_ID,
                "profile_id": "agent-001",
                "request_text": "the request body",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = migration.OpRecordSchemaV2Migration().apply(tmp_path)

    assert result.success
    assert result.warnings == ["Legacy Op records remain in .worktrees/lane-a; they are migrated when that lane is upgraded"]


def test_started_provenance_preserves_existing_digest_for_schema_validation() -> None:
    existing = {
        "invocation_id": _INVOCATION_ID,
        "request_digest": _VALID_DIGEST,
    }
    assert migration._started_provenance(existing) == (REDACTED_REQUEST_SUMMARY, _VALID_DIGEST)

    invalid = {
        "invocation_id": _INVOCATION_ID,
        "request_digest": "bad:123",
    }
    # Validation of the rebuilt event owns rejection of a malformed value and
    # records the corresponding warning.
    assert migration._started_provenance(invalid) == (REDACTED_REQUEST_SUMMARY, "bad:123")


def test_plan_file_preserves_start_event_extension_fields(tmp_path: Path) -> None:
    path = tmp_path / f"{_INVOCATION_ID}.jsonl"
    path.write_text(
        json.dumps(
            {
                "event": "started",
                "invocation_id": _INVOCATION_ID,
                "profile_id": "agent-001",
                "action": "implement",
                "request_text": "the request body",
                "actor": "claude",
                "mode_of_work": "query",
                "governance_context_hash": "abcd1234ef",
                "governance_context_available": True,
                "started_at": "2026-07-29T12:00:00+00:00",
                "trace_id": "keep-me",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    plan = migration._plan_file(path)
    assert plan.action == "rewrite"
    assert plan.source_lines and len(plan.source_lines) == 1
    migrated = json.loads(plan.new_lines[0])

    assert migrated["trace_id"] == "keep-me"
    assert migrated["event"] == "started"
    assert migrated["request_summary"] == REDACTED_REQUEST_SUMMARY
    assert "request_text" not in migrated
