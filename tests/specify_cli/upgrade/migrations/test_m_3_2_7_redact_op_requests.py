"""Targeted tests for OpRequest redaction migration helpers (3.2.7).

These tests pin the low-level behavior that was under review:
- only ULID-named records are eligible for migration,
- extension fields are preserved while redacting started requests,
- lock acquisition failures are captured as migration errors.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import sys
from pathlib import Path

import pytest

# Ensure worktree src/ shadows any installed package version.
_WORKTREE_SRC = Path(__file__).resolve().parents[5] / "src"
if str(_WORKTREE_SRC) not in sys.path:
    sys.path.insert(0, str(_WORKTREE_SRC))

import specify_cli.upgrade.migrations.m_3_2_7_redact_op_requests as migration
from specify_cli.invocation.record import REDACTED_REQUEST_SUMMARY


pytestmark = [pytest.mark.unit, pytest.mark.fast]

_INVOCATION_ID = "01ABCDEFGHJKMNPQRSTVWXYZ12"


def _write_line(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_eligible_files_only_includes_ulid_records(tmp_path: Path) -> None:
    ops_dir = tmp_path / "kitty-ops"
    ops_dir.mkdir(parents=True)

    valid = ops_dir / f"{_INVOCATION_ID}.jsonl"
    junk = ops_dir / "notes.jsonl"
    valid.write_text("", encoding="utf-8")
    junk.write_text("", encoding="utf-8")

    assert migration._eligible_files(tmp_path) == [valid]


def test_redact_started_event_preserves_extensions() -> None:
    payload = {
        "event": "started",
        "invocation_id": _INVOCATION_ID,
        "profile_id": "agent-001",
        "action": "implement",
        "request_text": "the requested change",
        "actor": "claude",
        "mode_of_work": "query",
        "governance_context_hash": "abcd1234ef",
        "governance_context_available": True,
        "started_at": "2026-07-29T12:00:00+00:00",
        "extension_field": "keep-this",
    }

    redacted = migration._redact_started_event(payload)
    assert redacted is not None
    redacted_data = json.loads(redacted)

    assert redacted_data["event"] == "started"
    assert "request_text" not in redacted_data
    assert redacted_data["request_summary"] == REDACTED_REQUEST_SUMMARY
    assert "extension_field" in redacted_data
    assert redacted_data["extension_field"] == "keep-this"


def test_rewrite_file_returns_error_when_lock_entry_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / f"{_INVOCATION_ID}.jsonl"
    _write_line(
        file_path,
        {
            "event": "started",
            "invocation_id": _INVOCATION_ID,
            "profile_id": "agent-001",
            "action": "implement",
            "request_text": "the requested change",
            "actor": "claude",
            "mode_of_work": "query",
            "governance_context_hash": "abcd1234ef",
            "governance_context_available": True,
            "started_at": "2026-07-29T12:00:00+00:00",
        },
    )

    @contextmanager
    def fail_lock(_path: Path):
        raise OSError("lock unavailable")
        yield

    monkeypatch.setattr(migration, "invocation_record_lock", fail_lock)

    outcome = migration._rewrite_once(file_path, (migration._redact_started_event,), False, is_op_record=True)
    assert outcome.error is not None
    assert "Could not rewrite" in outcome.error
