"""Targeted tests for Op record schema-v2 migration helpers (3.3.0)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure worktree src/ shadows any installed package version.
_WORKTREE_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_WORKTREE_SRC) not in sys.path:
    sys.path.insert(0, str(_WORKTREE_SRC))

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
