"""Tests for the kitty-ops Op record v2 schema migration (WP05, FR-011).

Covers every row of the normative migration mapping table in
``kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/data-model.md``, plus
deletion reporting, atomicity (tmp cleanup), double-run idempotency, the
``detect()`` matrix, and the excluded-files guarantee.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from threading import Event, Thread

import pytest
from filelock import FileLock

from specify_cli.invocation import writer as writer_module
from specify_cli.invocation.record import OpCompletedEvent, OpStartedEvent
from specify_cli.invocation.writer import InvocationWriter
from specify_cli.upgrade.migrations import m_3_3_0_op_record_schema_v2 as mod
from specify_cli.upgrade.migrations.m_3_3_0_op_record_schema_v2 import (
    EXCLUDED_FILES,
    OpRecordSchemaV2Migration,
)
from specify_cli.upgrade.migrations.base import MigrationResult

pytestmark = pytest.mark.fast

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
ULID2 = "01BX5ZZKBKACTAV9WEVGEMMVRZ"
# Only <invocation-ULID>.jsonl files are Op records, so fixtures standing in for
# distinct records need distinct ULID names rather than descriptive ones.
ULID3 = "01CDEFGHJKMNPQRSTVWXYZ0123"
ULID4 = "01D0123456789ABCDEFGHJKMNP"


@pytest.fixture
def migration() -> OpRecordSchemaV2Migration:
    return OpRecordSchemaV2Migration()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "kitty-ops").mkdir()
    return tmp_path


def _write(project: Path, name: str, lines: list[str]) -> Path:
    path = project / "kitty-ops" / name
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def _legacy_started(**overrides: object) -> str:
    data: dict[str, object] = {
        "event": "started",
        "invocation_id": ULID,
        "profile_id": "python-pedro",
        "action": "implement",
        "request_text": "do the thing",
        "governance_context_hash": "abcd1234abcd1234",
        "governance_context_available": True,
        "actor": "claude",
        "router_confidence": "exact",
        "started_at": "2026-01-01T00:00:00Z",
    }
    data.update(overrides)
    for key in [k for k, v in data.items() if v is ...]:
        del data[key]
    return json.dumps(data)


def _legacy_completed(**overrides: object) -> str:
    data: dict[str, object] = {
        "event": "completed",
        "invocation_id": ULID,
        "completed_at": "2026-01-01T01:00:00Z",
        "outcome": "done",
        "evidence_ref": None,
    }
    data.update(overrides)
    for key in [k for k, v in data.items() if v is ...]:
        del data[key]
    return json.dumps(data)


def _v2_file_lines() -> list[str]:
    started = OpStartedEvent(
        invocation_id=ULID,
        profile_id="python-pedro",
        action="implement",
        request_text="do the thing",
        actor="claude",
        mode_of_work="task_execution",
        governance_context_hash="abcd1234abcd1234",
        governance_context_available=True,
        started_at="2026-01-01T00:00:00Z",
    )
    completed = OpCompletedEvent(
        invocation_id=ULID,
        completed_at="2026-01-01T01:00:00Z",
        outcome="done",
        closed_by="agent",
    )
    return [started.to_jsonl_line(), completed.to_jsonl_line()]


# ---------------------------------------------------------------------------
# Mapping table rows
# ---------------------------------------------------------------------------


class TestMappingTable:
    def test_started_event_rewritten_to_v2(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 1: started with invocation_id + profile_id → OpStartedEvent."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        result = migration.apply(project)
        assert result.success
        line = json.loads(path.read_text().splitlines()[0])
        assert line["mode_of_work"] == "task_execution"  # missing → default
        assert line["actor"] == "claude"  # preserved when non-empty
        assert line["action"] == "implement"
        assert line["profile_id"] == "python-pedro"
        assert line["started_at"] == "2026-01-01T00:00:00Z"
        assert "request_text" not in line
        assert line["request_summary"] == "Request content withheld by local trail policy."
        assert line["request_digest"].startswith("sha256:")
        # round-trips through the v2 model
        OpStartedEvent.model_validate(line)

    def test_rewrite_preserves_model_id(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(model_id="gpt-5.6")])

        migration.apply(project)

        line = json.loads(path.read_text().splitlines()[0])
        assert line["model_id"] == "gpt-5.6"

    def test_mode_of_work_null_becomes_task_execution(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(mode_of_work=None)])
        migration.apply(project)
        line = json.loads(path.read_text().splitlines()[0])
        assert line["mode_of_work"] == "task_execution"

    def test_missing_actor_and_action_become_unrecorded(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 2: missing/empty actor or action → literal "unrecorded"."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(actor=..., action="")])
        migration.apply(project)
        line = json.loads(path.read_text().splitlines()[0])
        assert line["actor"] == "unrecorded"
        assert line["action"] == "unrecorded"

    def test_invalid_mode_of_work_is_deleted_not_skipped(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """A bogus non-empty mode_of_work is not "already v2" and fails closed."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(mode_of_work="bogus")])
        result = migration.apply(project)
        assert not path.exists()
        assert any("Deleted unsalvageable" in change for change in result.changes_made)

    def test_completed_with_outcome_gains_closed_by_agent(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 3: completed with non-null outcome → closed_by="agent"."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(), _legacy_completed(outcome="failed")])
        result = migration.apply(project)
        completed = json.loads(path.read_text().splitlines()[1])
        assert completed["outcome"] == "failed"
        assert completed["closed_by"] == "agent"
        assert completed["completed_at"] == "2026-01-01T01:00:00Z"
        assert not result.warnings
        OpCompletedEvent.model_validate(completed)

    def test_invalid_completed_closed_by_is_repaired_not_skipped(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """A bogus non-empty closed_by is not already-v2; repair to agent."""
        path = _write(
            project,
            f"{ULID}.jsonl",
            [_legacy_started(), _legacy_completed(outcome="done", closed_by="bogus")],
        )
        migration.apply(project)
        completed = json.loads(path.read_text().splitlines()[1])
        assert completed["outcome"] == "done"
        assert completed["closed_by"] == "agent"

    def test_missing_completed_at_falls_back_to_started_at_and_flags(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 3 fallback: missing completed_at → started_at, flagged in report."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(), _legacy_completed(completed_at=None)])
        result = migration.apply(project)
        completed = json.loads(path.read_text().splitlines()[1])
        assert completed["completed_at"] == "2026-01-01T00:00:00Z"
        assert any("completed_at" in w and ULID in w for w in result.warnings)

    def test_null_outcome_becomes_abandoned(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 4: null outcome (old auto-close artifact) → abandoned, agent."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(), _legacy_completed(outcome=None)])
        migration.apply(project)
        completed = json.loads(path.read_text().splitlines()[1])
        assert completed["outcome"] == "abandoned"
        assert completed["closed_by"] == "agent"

    def test_link_and_glossary_events_pass_through_byte_identical(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 5: link/glossary events pass through unchanged."""
        link_lines = [
            json.dumps({"event": "artifact_link", "invocation_id": ULID, "path": "a.md"}),
            json.dumps({"event": "commit_link", "invocation_id": ULID, "sha": "deadbeef"}),
            json.dumps({"event": "glossary_checked", "invocation_id": ULID}),
        ]
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(), *link_lines])
        migration.apply(project)
        assert path.read_text().splitlines()[1:] == link_lines

    def test_unsalvageable_files_deleted_and_reported(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 6: unparseable / identity-less started event → delete + report."""
        bad_json = _write(project, f"{ULID}.jsonl", ["{not json"])
        no_profile = _write(project, f"{ULID2}.jsonl", [_legacy_started(profile_id=...)])
        no_inv = _write(project, f"{ULID3}.jsonl", [_legacy_started(invocation_id="")])
        no_started = _write(project, f"{ULID4}.jsonl", [_legacy_completed()])
        result = migration.apply(project)
        for path in (bad_json, no_profile, no_inv, no_started):
            assert not path.exists()
        assert sum("Deleted unsalvageable" in c for c in result.changes_made) == 4
        summary = [w for w in result.warnings if "Deleted 4 unsalvageable" in w]
        assert summary and f"{ULID}.jsonl" in summary[0]

    def test_invalid_utf8_record_is_deleted_instead_of_crashing(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """Binary garbage is an unreadable record, not an upgrade-aborting crash."""
        path = project / "kitty-ops" / f"{ULID}.jsonl"
        path.write_bytes(b"\xff\xfe not utf-8\n")

        assert migration.detect(project) is True
        result = migration.apply(project)

        assert result.success, result.errors
        assert not path.exists()
        assert any("Deleted unsalvageable" in change for change in result.changes_made)

    def test_invalid_utf8_lane_record_does_not_abort_detection(
        self, migration: OpRecordSchemaV2Migration, tmp_path: Path
    ) -> None:
        """A lane record with invalid UTF-8 must not escape ``detect()``."""
        checkout = tmp_path / "repo"
        (checkout / "kitty-ops").mkdir(parents=True)
        lane_record = checkout / ".worktrees" / "lane-a" / "kitty-ops" / f"{ULID}.jsonl"
        lane_record.parent.mkdir(parents=True)
        lane_record.write_bytes(b"\xff\xfe not utf-8\n")

        assert migration.detect(checkout) is True

    def test_already_v2_file_skipped_untouched(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 7: already-v2 file (completed has closed_by) → skip."""
        path = _write(project, f"{ULID}.jsonl", _v2_file_lines())
        before = path.read_bytes()
        result = migration.apply(project)
        assert path.read_bytes() == before
        assert result.changes_made == []


# ---------------------------------------------------------------------------
# Idempotency / atomicity
# ---------------------------------------------------------------------------


class TestIdempotencyAndAtomicity:
    def test_double_run_is_byte_identical_noop(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        _write(project, f"{ULID}.jsonl", [_legacy_started(), _legacy_completed(outcome=None)])
        _write(project, f"{ULID2}.jsonl", [_legacy_started(invocation_id=ULID2, actor="")])
        _write(project, "bad.jsonl", ["{nope"])
        first = migration.apply(project)
        assert first.changes_made
        snapshot = {p.name: p.read_bytes() for p in (project / "kitty-ops").glob("*.jsonl")}
        second = migration.apply(project)
        assert second.changes_made == []
        assert second.warnings == []
        after = {p.name: p.read_bytes() for p in (project / "kitty-ops").glob("*.jsonl")}
        assert after == snapshot

    def test_detect_false_after_migration(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        _write(project, f"{ULID}.jsonl", [_legacy_started()])
        assert migration.detect(project) is True
        migration.apply(project)
        assert migration.detect(project) is False

    def test_stuck_lock_fails_without_marking_the_migration_complete(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``UpgradeRunner._apply_migration`` calls ``apply`` with no guard.

        A ``filelock.Timeout`` escaping here would abort the whole upgrade with
        a traceback, but declaring success would permanently skip the still-
        legacy record. The result must fail cleanly so a later run can retry.
        """
        monkeypatch.setattr(writer_module, "_INVOCATION_LOCK_TIMEOUT_SECONDS", 0.05)
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        original = path.read_bytes()

        with FileLock(str(path.with_name(f".{path.name}.lock")), timeout=5):
            result = migration.apply(project)

        assert result.success is False
        assert result.changes_made == []
        assert any(path.name in error for error in result.errors)
        assert path.read_bytes() == original
        # Still legacy, so a later run retries it.
        assert migration.detect(project) is True

    def test_tmp_file_cleaned_up_on_replace_failure(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        original = path.read_bytes()

        def boom(src: object, dst: object) -> None:
            raise OSError("simulated replace failure")

        monkeypatch.setattr(mod.os, "replace", boom)
        # Neither the runner nor the CLI wraps apply(), so an I/O fault has to
        # come back as a failed MigrationResult rather than a traceback.
        result = migration.apply(project)
        assert result.success is False
        assert any(path.name in error for error in result.errors)
        assert path.read_bytes() == original  # original never partially written
        assert list((project / "kitty-ops").glob("*.tmp")) == []

    def test_atomic_rewrite_uses_os_replace(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write(project, f"{ULID}.jsonl", [_legacy_started()])
        calls: list[tuple[str, str]] = []
        real_replace = os.replace

        def spy(src: object, dst: object) -> None:
            calls.append((str(src), str(dst)))
            real_replace(src, dst)  # type: ignore[arg-type]

        monkeypatch.setattr(mod.os, "replace", spy)
        migration.apply(project)
        assert len(calls) == 1
        assert Path(calls[0][0]).name.startswith(f".{ULID}.jsonl.")
        assert calls[0][0].endswith(".tmp")
        assert calls[0][1].endswith(f"{ULID}.jsonl")

    def test_atomic_rewrite_does_not_follow_a_precreated_temporary_symlink(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
    ) -> None:
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        outside = project / "outside.txt"
        outside.write_text("leave untouched", encoding="utf-8")
        path.with_name(path.name + ".tmp").symlink_to(outside)

        result = migration.apply(project)

        assert result.success
        assert outside.read_text(encoding="utf-8") == "leave untouched"
        assert json.loads(path.read_text(encoding="utf-8"))["event"] == "started"

    def test_rewrite_does_not_drop_append_started_after_planning(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        writer = InvocationWriter(project)
        append_started = Event()
        append_finished = Event()

        def _append_link() -> None:
            append_started.set()
            writer.append_correlation_link(ULID, ref="evidence.md")
            append_finished.set()

        append_thread = Thread(target=_append_link)
        real_replace = mod.os.replace

        def _replace_after_append_attempt(source: object, target: object) -> None:
            append_thread.start()
            assert append_started.wait(timeout=1)
            time.sleep(0.05)
            assert not append_finished.is_set()
            real_replace(source, target)

        monkeypatch.setattr(mod.os, "replace", _replace_after_append_attempt)

        result = migration.apply(project)
        append_thread.join(timeout=1)

        assert result.success
        assert append_finished.is_set()
        assert [json.loads(line)["event"] for line in path.read_text(encoding="utf-8").splitlines()] == [
            "started",
            "artifact_link",
        ]

    def test_schema_rewrite_retries_instead_of_dropping_a_stale_writer_append(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A writer from before the shared lock cannot be silently overwritten."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        late_line = json.dumps({"event": "artifact_link", "invocation_id": ULID, "ref": "evidence.md"})
        original_read_text = Path.read_text
        appended = False

        def _append_between_snapshot_and_swap(candidate: Path, *args: object, **kwargs: object) -> str:
            nonlocal appended
            contents = original_read_text(candidate, *args, **kwargs)
            if candidate == path and not appended:
                appended = True
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(late_line + "\n")
            return contents

        monkeypatch.setattr(Path, "read_text", _append_between_snapshot_and_swap)

        result = migration.apply(project)

        assert result.success, result.errors
        assert appended
        assert [json.loads(line)["event"] for line in path.read_text(encoding="utf-8").splitlines()] == [
            "started",
            "artifact_link",
        ]

    @pytest.mark.skipif(not Path("/proc/self/fd").exists(), reason="needs /proc to count open handles")
    def test_swap_holds_no_handle_on_the_record_where_the_inode_cannot_be_drained(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Windows refuses to replace a destination this process still holds open."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        original_replace = mod.os.replace
        handles_at_swap: list[int] = []

        def _count_handles_then_replace(source: object, target: object) -> None:
            target_path = Path(str(target))
            handles = sum(
                1
                for entry in Path("/proc/self/fd").iterdir()
                if entry.exists() and entry.resolve() == target_path.resolve()
            )
            handles_at_swap.append(handles)
            original_replace(source, target)

        monkeypatch.setattr(mod, "DRAIN_SUPPORTED", False)
        monkeypatch.setattr(mod.os, "replace", _count_handles_then_replace)

        result = migration.apply(project)

        assert result.success, result.errors
        assert handles_at_swap == [0], "the swap ran with the record still open, which Windows rejects"
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert [event["event"] for event in events] == ["started"]
        assert events[0]["mode_of_work"] == "task_execution"
        assert not migration.detect(project)

    def test_append_landing_after_the_snapshot_check_survives_the_swap(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The compare and the swap are separate, so the old inode must be drained."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        late_line = json.dumps({"event": "artifact_link", "invocation_id": ULID, "ref": "evidence.md"})
        original_replace = mod.os.replace
        appended = False

        def _append_between_check_and_replace(source: object, target: object) -> None:
            nonlocal appended
            if not appended:
                appended = True
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(late_line + "\n")
            original_replace(source, target)

        monkeypatch.setattr(mod.os, "replace", _append_between_check_and_replace)

        result = migration.apply(project)

        assert result.success, result.errors
        assert appended
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert [event["event"] for event in events] == ["started", "artifact_link"]
        assert events[0]["mode_of_work"] == "task_execution"
        assert not migration.detect(project)

    def test_schema_rewrite_fails_closed_when_stale_writers_never_settle(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        original_read_text = Path.read_text

        def _append_on_every_read(candidate: Path, *args: object, **kwargs: object) -> str:
            contents = original_read_text(candidate, *args, **kwargs)
            if candidate == path:
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"event": "artifact_link", "invocation_id": ULID}) + "\n")
            return contents

        monkeypatch.setattr(Path, "read_text", _append_on_every_read)

        result = migration.apply(project)

        assert result.success is False
        assert any(path.name in error for error in result.errors)

    def test_unsalvageable_delete_waits_for_the_record_to_settle(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A record still being written must be replanned, never unlinked.

        Deletion is irreversible, so a partial file that finishes landing
        between planning and execution has to be re-read instead of destroyed.
        """
        path = _write(project, f"{ULID}.jsonl", ["{partial"])
        settled = "".join(line + "\n" for line in _v2_file_lines())
        original_read_text = Path.read_text
        reads = 0

        def _finish_the_write_after_planning(candidate: Path, *args: object, **kwargs: object) -> str:
            nonlocal reads
            contents = original_read_text(candidate, *args, **kwargs)
            if candidate == path:
                reads += 1
                if reads == 2:
                    path.write_text(settled, encoding="utf-8")
            return contents

        monkeypatch.setattr(Path, "read_text", _finish_the_write_after_planning)

        result = migration.apply(project)

        assert result.success, result.errors
        assert path.exists()
        assert original_read_text(path, encoding="utf-8") == settled
        assert not any("Deleted" in change for change in result.changes_made)

    def test_writer_that_finishes_during_quarantine_is_restored_not_deleted(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A record completed while it is moved aside comes back, not unlinked."""
        path = _write(project, f"{ULID}.jsonl", ["{partial"])
        settled = "".join(line + "\n" for line in _v2_file_lines())
        real_quarantine = mod._quarantine

        def _finish_the_write_after_the_move(candidate: Path) -> Path | None:
            quarantined = real_quarantine(candidate)
            if quarantined is not None:
                quarantined.write_text(settled, encoding="utf-8")
            return quarantined

        monkeypatch.setattr(mod, "_quarantine", _finish_the_write_after_the_move)

        result = migration.apply(project)

        assert result.success, result.errors
        assert path.read_text(encoding="utf-8") == settled
        assert not any("Deleted" in change for change in result.changes_made)
        assert list(path.parent.glob(f"*{mod._QUARANTINE_SUFFIX}")) == []

    def test_record_still_being_appended_is_restored_instead_of_unlinked(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Bytes that change across the move mean the inode must survive."""
        path = _write(project, f"{ULID}.jsonl", ["{partial"])
        real_quarantine = mod._quarantine

        def _keep_appending_after_the_move(candidate: Path) -> Path | None:
            quarantined = real_quarantine(candidate)
            if quarantined is not None:
                with quarantined.open("a", encoding="utf-8") as handle:
                    handle.write("{still partial\n")
            return quarantined

        monkeypatch.setattr(mod, "_quarantine", _keep_appending_after_the_move)

        result = migration.apply(project)

        assert result.success is False
        assert any(path.name in error for error in result.errors)
        assert path.read_text(encoding="utf-8") == "{partial\n{still partial\n"
        assert list(path.parent.glob(f"*{mod._QUARANTINE_SUFFIX}")) == []

    def test_interrupted_quarantine_stays_visible_to_detect(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """A quarantine left by a killed run must not silence the migration."""
        quarantine = project / "kitty-ops" / f".{ULID}.jsonl{mod._QUARANTINE_SUFFIX}"
        quarantine.write_text(_legacy_started() + "\n", encoding="utf-8")

        assert migration.detect(project) is True

    def test_interrupted_quarantine_is_restored_and_repaired(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """Reclaimed bytes go back under their own name and get migrated."""
        record = project / "kitty-ops" / f"{ULID}.jsonl"
        quarantine = project / "kitty-ops" / f".{record.name}{mod._QUARANTINE_SUFFIX}"
        quarantine.write_text(_legacy_started() + "\n", encoding="utf-8")

        result = migration.apply(project)

        assert result.success, result.errors
        assert not quarantine.exists()
        assert json.loads(record.read_text(encoding="utf-8").splitlines()[0])["mode_of_work"] == "task_execution"
        assert migration.detect(project) is False

    def test_stale_quarantine_is_discarded_when_the_record_was_recreated(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """Unsalvageable bytes are dropped rather than clobbering a new record."""
        record = _write(project, f"{ULID}.jsonl", _v2_file_lines())
        fresh = record.read_bytes()
        quarantine = project / "kitty-ops" / f".{record.name}{mod._QUARANTINE_SUFFIX}"
        quarantine.write_text("{partial\n", encoding="utf-8")

        result = migration.apply(project)

        assert result.success, result.errors
        assert not quarantine.exists()
        assert record.read_bytes() == fresh

    def test_hidden_file_with_the_suffix_is_not_treated_as_a_quarantine(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """A foreign file must not be handed a record name by the reclaim pass."""
        ops_dir = project / "kitty-ops"
        ops_dir.mkdir(parents=True, exist_ok=True)
        foreign = ops_dir / f".notes.txt{mod._QUARANTINE_SUFFIX}"
        foreign.write_text("not an op record\n", encoding="utf-8")

        assert migration.detect(project) is False
        result = migration.apply(project)

        assert result.success, result.errors
        assert result.changes_made == []
        assert foreign.read_text(encoding="utf-8") == "not an op record\n"
        assert not (ops_dir / "notes.txt").exists()

    def test_non_ulid_record_name_is_not_reclaimed_from_a_quarantine(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """Op record names are invocation ULIDs, so no other stem may be reclaimed."""
        ops_dir = project / "kitty-ops"
        ops_dir.mkdir(parents=True, exist_ok=True)
        foreign = ops_dir / f".notes.jsonl{mod._QUARANTINE_SUFFIX}"
        foreign.write_text("{partial\n", encoding="utf-8")

        assert migration.detect(project) is False
        result = migration.apply(project)

        assert result.success, result.errors
        assert result.changes_made == []
        assert foreign.read_text(encoding="utf-8") == "{partial\n"
        assert not (ops_dir / "notes.jsonl").exists()

    def test_excluded_record_name_is_not_reclaimed_from_a_quarantine(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """Reclaim must not synthesize a file the migration may never touch."""
        ops_dir = project / "kitty-ops"
        ops_dir.mkdir(parents=True, exist_ok=True)
        excluded = next(iter(sorted(mod.EXCLUDED_FILES)))
        foreign = ops_dir / f".{excluded}{mod._QUARANTINE_SUFFIX}"
        foreign.write_text("{partial\n", encoding="utf-8")

        assert migration.detect(project) is False
        result = migration.apply(project)

        assert result.success, result.errors
        assert foreign.exists()
        assert not (ops_dir / excluded).exists()

    def test_restore_waits_for_the_writer_creating_that_record(
        self,
        project: Path,
    ) -> None:
        """The existence check and the rename are held under the record lock.

        ``os.replace`` overwrites, and ``write_started`` creates a record under
        ``invocation_record_lock``. Without that lock here, a creation landing
        between the check and the rename is silently replaced by these older
        bytes and its audit event is lost.
        """
        ops_dir = project / "kitty-ops"
        origin = ops_dir / f"{ULID}.jsonl"
        quarantine = ops_dir / f".{origin.name}{mod._QUARANTINE_SUFFIX}"
        quarantine.write_text(_legacy_started() + "\n", encoding="utf-8")
        fresh = _legacy_started(invocation_id=ULID, action="review") + "\n"
        holding = Event()
        release = Event()
        restored: list[bool] = []

        def _create_under_the_record_lock() -> None:
            with writer_module.invocation_record_lock(origin):
                holding.set()
                release.wait(timeout=5)
                origin.write_text(fresh, encoding="utf-8")

        creator = Thread(target=_create_under_the_record_lock)
        restorer = Thread(target=lambda: restored.append(mod._restore(quarantine, origin)))
        creator.start()
        assert holding.wait(timeout=5)
        restorer.start()
        restorer.join(timeout=0.2)

        assert restorer.is_alive(), "restore did not wait for the record lock"

        release.set()
        creator.join(timeout=5)
        restorer.join(timeout=5)

        assert restored == [False]
        assert origin.read_text(encoding="utf-8") == fresh
        assert quarantine.read_text(encoding="utf-8") == _legacy_started() + "\n"

    def test_writer_finishing_during_a_discard_keeps_the_quarantined_bytes(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A stale writer still attached to a quarantine can complete the record."""
        record = _write(project, f"{ULID}.jsonl", _v2_file_lines())
        quarantine = project / "kitty-ops" / f".{record.name}{mod._QUARANTINE_SUFFIX}"
        quarantine.write_text("{partial\n", encoding="utf-8")
        settled = _legacy_started(invocation_id=ULID2) + "\n"
        real_plan = mod._plan_file
        planned: list[Path] = []

        def _finish_the_write_after_planning(candidate: Path) -> mod._FilePlan:
            plan = real_plan(candidate)
            if candidate == quarantine and not planned:
                planned.append(candidate)
                quarantine.write_text(settled, encoding="utf-8")
            return plan

        monkeypatch.setattr(mod, "_plan_file", _finish_the_write_after_planning)

        result = migration.apply(project)

        assert result.success is False
        assert any(quarantine.name in error for error in result.errors)
        assert quarantine.read_text(encoding="utf-8") == settled

    def test_quarantine_that_never_settles_is_left_for_the_next_run(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unsalvageable bytes that keep moving must not be unlinked."""
        record = _write(project, f"{ULID}.jsonl", _v2_file_lines())
        quarantine = project / "kitty-ops" / f".{record.name}{mod._QUARANTINE_SUFFIX}"
        quarantine.write_text("{partial\n", encoding="utf-8")
        real_plan = mod._plan_file

        def _keep_appending_after_planning(candidate: Path) -> mod._FilePlan:
            plan = real_plan(candidate)
            if candidate == quarantine:
                with quarantine.open("a", encoding="utf-8") as handle:
                    handle.write("{still partial\n")
            return plan

        monkeypatch.setattr(mod, "_plan_file", _keep_appending_after_planning)

        result = migration.apply(project)

        assert result.success is False
        assert any(quarantine.name in error for error in result.errors)
        assert quarantine.exists()

    def test_dry_run_reports_a_stale_quarantine_without_discarding_it(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """A preview of the discard must leave the quarantine on disk."""
        record = _write(project, f"{ULID}.jsonl", _v2_file_lines())
        quarantine = project / "kitty-ops" / f".{record.name}{mod._QUARANTINE_SUFFIX}"
        quarantine.write_text("{partial\n", encoding="utf-8")

        result = migration.apply(project, dry_run=True)

        assert result.success, result.errors
        assert any("Would discard stale quarantine" in change for change in result.changes_made)
        assert quarantine.exists()

    def test_salvageable_quarantine_over_a_recreated_record_is_reported(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """Two live records under one name need an operator, not a guess."""
        record = _write(project, f"{ULID}.jsonl", _v2_file_lines())
        fresh = record.read_bytes()
        quarantine = project / "kitty-ops" / f".{record.name}{mod._QUARANTINE_SUFFIX}"
        quarantine.write_text(_legacy_started(invocation_id=ULID2) + "\n", encoding="utf-8")

        result = migration.apply(project)

        assert result.success is False
        assert any(quarantine.name in error for error in result.errors)
        assert quarantine.exists()
        assert record.read_bytes() == fresh

    def test_io_failure_is_reported_instead_of_aborting_the_upgrade(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A read-only trail must fail the migration, not raise out of apply()."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])

        def _refuse_to_lock(_path: Path) -> object:
            raise OSError(30, "Read-only file system")

        monkeypatch.setattr(mod, "invocation_record_lock", _refuse_to_lock)

        result = migration.apply(project)

        assert result.success is False
        assert any(path.name in error for error in result.errors)
        assert path.read_text(encoding="utf-8") == _legacy_started() + "\n"

    def test_schema_migration_waits_for_started_record_initialization(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Creation holds the same lock until the first record line is durable."""
        writer = InvocationWriter(project)
        path = writer.invocation_path(ULID)
        created = Event()
        release_writer = Event()
        writer_errors: list[Exception] = []
        migration_result: list[MigrationResult] = []
        original_open = Path.open

        def _pause_after_exclusive_create(candidate: Path, *args: object, **kwargs: object):
            handle = original_open(candidate, *args, **kwargs)
            if candidate == path and args and args[0] == "x":
                created.set()
                assert release_writer.wait(timeout=1)
            return handle

        monkeypatch.setattr(writer_module.Path, "open", _pause_after_exclusive_create)

        def _write_started() -> None:
            try:
                writer.write_started(
                    OpStartedEvent(
                        invocation_id=ULID,
                        profile_id="python-pedro",
                        action="implement",
                        request_text="started while upgrading",
                        actor="codex",
                        mode_of_work="task_execution",
                        governance_context_hash="abcd1234abcd1234",
                        governance_context_available=True,
                        started_at="2026-01-01T00:00:00Z",
                    )
                )
            except Exception as exc:  # pragma: no cover - surfaced below
                writer_errors.append(exc)

        writer_thread = Thread(target=_write_started)
        writer_thread.start()
        assert created.wait(timeout=1)
        migration_thread = Thread(target=lambda: migration_result.append(migration.apply(project)))
        migration_thread.start()
        time.sleep(0.05)
        assert migration_result == []
        release_writer.set()
        writer_thread.join(timeout=1)
        migration_thread.join(timeout=1)

        assert not writer_errors
        assert migration_result and migration_result[0].success is True
        assert json.loads(path.read_text(encoding="utf-8").splitlines()[0])["event"] == "started"

    def test_dry_run_changes_nothing(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        legacy = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        bad = _write(project, f"{ULID2}.jsonl", ["{nope"])
        before = (legacy.read_bytes(), bad.read_bytes())
        result = migration.apply(project, dry_run=True)
        assert (legacy.read_bytes(), bad.read_bytes()) == before
        assert any(c.startswith("Would rewrite") for c in result.changes_made)
        assert any(c.startswith("Would delete") for c in result.changes_made)
        assert migration.detect(project) is True


# ---------------------------------------------------------------------------
# detect() matrix / exclusions / registration
# ---------------------------------------------------------------------------


class TestDetectMatrix:
    def test_detect_false_without_kitty_ops(self, migration: OpRecordSchemaV2Migration, tmp_path: Path) -> None:
        assert migration.detect(tmp_path) is False

    def test_detect_false_for_empty_ops_dir(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        assert migration.detect(project) is False

    def test_detect_false_when_only_excluded_files_exist(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        for name in EXCLUDED_FILES:
            _write(project, name, [_legacy_started()])  # legacy-looking content
        assert migration.detect(project) is False

    def test_detect_false_for_v2_only(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        _write(project, f"{ULID}.jsonl", _v2_file_lines())
        assert migration.detect(project) is False

    @pytest.mark.parametrize(
        "lines",
        [
            [_legacy_started()],  # legacy started (no mode_of_work)
            _v2_file_lines()[:1] + [_legacy_completed()],  # legacy completed
            ["{nope"],  # unsalvageable
        ],
        ids=["legacy-started", "legacy-completed", "unsalvageable"],
    )
    def test_detect_true_for_legacy_shapes(self, migration: OpRecordSchemaV2Migration, project: Path, lines: list[str]) -> None:
        _write(project, f"{ULID}.jsonl", lines)
        assert migration.detect(project) is True

    def test_foreign_jsonl_in_kitty_ops_is_not_treated_as_a_record(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """Only ``<invocation-ULID>.jsonl`` files are Op records.

        ``InvocationWriter.invocation_path()`` never emits another name, so a
        foreign JSONL parked beside the trail (an operator backup, say) is not
        this migration's to plan: it would be deleted as an unrepairable record.
        """
        foreign = _write(project, "backup.jsonl", [_legacy_started(), "{not even json"])
        before = foreign.read_bytes()

        assert migration.detect(project) is False
        result = migration.apply(project)

        assert result.success, result.errors
        assert foreign.exists()
        assert foreign.read_bytes() == before

    def test_excluded_files_never_touched_by_apply(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        excluded = {name: _write(project, name, [_legacy_started(), "{not even json"]) for name in EXCLUDED_FILES}
        _write(project, f"{ULID}.jsonl", [_legacy_started()])
        before = {name: p.read_bytes() for name, p in excluded.items()}
        migration.apply(project)
        assert {name: p.read_bytes() for name, p in excluded.items()} == before

    def test_can_apply_requires_ops_dir(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        bare = project / "no-ops-here"
        bare.mkdir()
        ok, _reason = migration.can_apply(bare)
        assert ok is False
        ok, reason = migration.can_apply(project)
        assert ok is True and reason == ""

    def test_migration_is_registered(self) -> None:
        from specify_cli.upgrade.registry import MigrationRegistry

        ids = {m.migration_id for m in MigrationRegistry.get_all()}
        assert "3_3_0_op_record_schema_v2" in ids

    def test_symlinked_ops_dir_is_not_rewritten(self, migration: OpRecordSchemaV2Migration, tmp_path: Path) -> None:
        """``glob()`` follows a symlinked ``kitty-ops`` straight out of the checkout."""
        checkout = tmp_path / "repo"
        checkout.mkdir()
        outside = tmp_path / "other-checkout" / "kitty-ops"
        outside.mkdir(parents=True)
        outside_record = outside / f"{ULID}.jsonl"
        outside_record.write_text(_legacy_started() + "\n", encoding="utf-8")
        (checkout / "kitty-ops").symlink_to(outside, target_is_directory=True)

        assert migration.detect(checkout) is False
        ok, _reason = migration.can_apply(checkout)
        assert ok is False
        assert migration.apply(checkout).success
        assert outside_record.read_text(encoding="utf-8") == _legacy_started() + "\n"

    def test_symlinked_worktrees_root_is_not_scanned(self, migration: OpRecordSchemaV2Migration, tmp_path: Path) -> None:
        """Lane discovery must not follow a symlinked ``.worktrees`` either.

        The lanes behind such a link are ordinary directories, so the per-child
        symlink guard accepts them and another checkout's records become
        eligible for rewriting.
        """
        checkout = tmp_path / "repo"
        (checkout / "kitty-ops").mkdir(parents=True)
        outside_worktrees = tmp_path / "outside-worktrees"
        outside_record = outside_worktrees / "lane-a" / "kitty-ops" / f"{ULID}.jsonl"
        outside_record.parent.mkdir(parents=True)
        outside_record.write_text(_legacy_started() + "\n", encoding="utf-8")
        (checkout / ".worktrees").symlink_to(outside_worktrees, target_is_directory=True)

        assert migration.detect(checkout) is False
        assert migration.apply(checkout).success
        assert outside_record.read_text(encoding="utf-8") == _legacy_started() + "\n"

    def test_symlinked_record_is_not_rewritten(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """A symlinked record resolves outside the checkout the same way."""
        outside = project.parent / "outside.jsonl"
        outside.write_text(_legacy_started() + "\n", encoding="utf-8")
        (project / "kitty-ops" / f"{ULID}.jsonl").symlink_to(outside)

        assert migration.detect(project) is False
        assert migration.apply(project).success
        assert outside.read_text(encoding="utf-8") == _legacy_started() + "\n"


# ---------------------------------------------------------------------------
# Provenance preservation during schema repair
# ---------------------------------------------------------------------------


def _redacted_v2_started(**overrides: object) -> str:
    """A raw-request-free v2 started row carrying real correlation provenance."""
    from specify_cli.invocation.record import request_provenance

    summary, digest = request_provenance("rotate the production secret")
    data: dict[str, object] = {
        "event": "started",
        "invocation_id": ULID,
        "profile_id": "python-pedro",
        "action": "implement",
        "request_summary": summary,
        "request_digest": digest,
        "actor": "claude",
        "mode_of_work": "task_execution",
        "governance_context_hash": "abcd1234abcd1234",
        "governance_context_available": True,
        "started_at": "2026-01-01T00:00:00Z",
    }
    data.update(overrides)
    for key in [k for k, v in data.items() if v is ...]:
        del data[key]
    return json.dumps(data)


class TestProvenancePreservation:
    def test_existing_request_digest_survives_a_completed_row_repair(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
    ) -> None:
        """A legacy completed row rebuilds the file; the digest must not be re-derived."""
        from specify_cli.invocation.record import request_provenance

        _summary, digest = request_provenance("rotate the production secret")
        path = _write(project, f"{ULID}.jsonl", [_redacted_v2_started(), _legacy_completed()])

        assert migration.detect(project) is True
        result = migration.apply(project)

        assert result.success, result.errors
        started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert started["request_digest"] == digest
        assert "request_text" not in started

    def test_absent_digest_is_not_replaced_by_the_empty_string_digest(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
    ) -> None:
        """A row with no raw request and no digest stays without one."""
        from specify_cli.invocation.record import request_provenance

        _summary, empty_digest = request_provenance("")
        path = _write(project, f"{ULID}.jsonl", [_redacted_v2_started(request_digest=...), _legacy_completed()])

        result = migration.apply(project)

        assert result.success, result.errors
        started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert started.get("request_digest") != empty_digest
        assert "request_digest" not in started

    def test_raw_request_still_drives_provenance(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """A legacy row carrying the raw request is still digested and redacted."""
        from specify_cli.invocation.record import request_provenance

        summary, digest = request_provenance("do the thing")
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])

        assert migration.apply(project).success
        started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert started["request_summary"] == summary
        assert started["request_digest"] == digest
        assert "request_text" not in started

    def test_empty_raw_request_still_derives_its_provenance(
        self, migration: OpRecordSchemaV2Migration, project: Path
    ) -> None:
        """Key presence distinguishes an empty request from an absent one."""
        from specify_cli.invocation.record import request_provenance

        _summary, empty_digest = request_provenance("")
        _other_summary, stale_digest = request_provenance("stale request")
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(request_text="", request_digest=stale_digest)])

        result = migration.apply(project)

        assert result.success, result.errors
        started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert started["request_digest"] == empty_digest
        assert started["request_digest"] != stale_digest
        assert "request_text" not in started

    @pytest.mark.parametrize("request_value", [["do", "the", "thing"], {"request": "do the thing"}])
    def test_non_string_raw_request_drops_the_recorded_digest(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        request_value: object,
    ) -> None:
        """A present non-string raw request leaves no trustworthy digest behind.

        This repair removes ``request_text``, so a digest kept beside a payload
        it was never derived from would survive as untrustworthy provenance the
        redaction migration can no longer reach.
        """
        from specify_cli.invocation.record import request_provenance

        _summary, stale_digest = request_provenance("stale request")
        path = _write(
            project,
            f"{ULID}.jsonl",
            [_legacy_started(request_text=request_value, request_digest=stale_digest)],
        )

        result = migration.apply(project)

        assert result.success, result.errors
        started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert "request_text" not in started
        assert "request_digest" not in started

    def test_rebuilt_started_row_keeps_its_extension_fields(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
    ) -> None:
        """A repaired row keeps append-only keys the event model ignores.

        A raw-v2 row (v2-shaped, but still carrying ``request_text``) is
        deliberately classified non-v2 and rebuilt here, so this repair is the
        only pass that sees it. Rebuilding from the fixed schema field list
        would drop unrelated extension or audit keys along with the request.
        """
        path = _write(
            project,
            f"{ULID}.jsonl",
            [
                _legacy_started(
                    mode_of_work="advisory",
                    audit_trace_id="trace-42",
                    request_text="do the thing",
                )
            ],
        )

        result = migration.apply(project)

        assert result.success, result.errors
        started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert "request_text" not in started
        assert started["audit_trace_id"] == "trace-42"
        assert started["mode_of_work"] == "advisory"
        assert started["request_digest"].startswith("sha256:")
        assert migration.detect(project) is False

    def test_dropped_digest_does_not_survive_from_the_original_row(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
    ) -> None:
        """Preserving unknown keys must not resurrect a rejected schema field.

        ``_validated_started`` drops a corrupt digest, so the corrupt value from
        the original row must not be carried back in beside the repaired ones.
        """
        path = _write(
            project,
            f"{ULID}.jsonl",
            [_legacy_started(request_text=..., request_digest="sha256:not-a-digest", audit_trace_id="trace-42")],
        )

        result = migration.apply(project)

        assert result.success, result.errors
        started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert "request_digest" not in started
        assert started["audit_trace_id"] == "trace-42"

    def test_corrupt_preserved_digest_is_dropped_instead_of_deleting_the_record(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
    ) -> None:
        """A digest copied out of the repaired file must not cost the whole record."""
        path = _write(project, f"{ULID}.jsonl", [_redacted_v2_started(request_digest="sha256:not-a-digest"), _legacy_completed()])

        result = migration.apply(project)

        assert result.success, result.errors
        assert path.exists()
        assert any("request_digest" in warning for warning in result.warnings)
        started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert "request_digest" not in started
        assert started["invocation_id"] == ULID


# ---------------------------------------------------------------------------
# Retryability of a timed-out rewrite
# ---------------------------------------------------------------------------


class TestStuckLockRetryability:
    def test_timed_out_worktree_rewrite_is_a_fatal_failure(self, migration: OpRecordSchemaV2Migration) -> None:
        """A nonfatal failure would let the runner stamp the worktree as upgraded."""
        assert migration.worktree_failure_is_fatal is True

    def test_migration_stays_selectable_after_the_version_advances(self, project: Path) -> None:
        """Selection must still reach the migration once the project moves past it."""
        from specify_cli.upgrade.registry import MigrationRegistry

        _write(project, f"{ULID}.jsonl", [_legacy_started()])

        applicable = MigrationRegistry.get_applicable("3.2.1", "3.3.0", project)

        assert any(m.migration_id == "3_3_0_op_record_schema_v2" for m in applicable)

    def test_worktree_only_repair_stays_selectable_after_the_root_advances(
        self, migration: OpRecordSchemaV2Migration, tmp_path: Path
    ) -> None:
        """A timed-out lane has no root record to make the migration selectable."""
        from specify_cli.upgrade.registry import MigrationRegistry

        root = tmp_path / "root"
        root.mkdir()
        lane_ops = root / ".worktrees" / "lane-a" / "kitty-ops"
        lane_ops.mkdir(parents=True)
        (lane_ops / f"{ULID}.jsonl").write_text(_legacy_started() + "\n", encoding="utf-8")

        applicable = MigrationRegistry.get_applicable("3.2.1", "3.3.0", root)

        assert migration.detect(root) is True
        assert migration.can_apply(root) == (True, "")
        assert any(candidate.migration_id == migration.migration_id for candidate in applicable)
