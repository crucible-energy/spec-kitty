"""Regression tests for the post-schema Op request redaction migration."""

from __future__ import annotations

import contextlib
import json
import time
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from typing import TextIO

import pytest
from filelock import FileLock

from glossary import events as glossary_events
from specify_cli.invocation import writer as invocation_writer
from specify_cli.invocation.record import REDACTED_REQUEST_SUMMARY
from specify_cli.invocation.writer import InvocationWriter
from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations import _late_append_drain as late_append_drain
from specify_cli.upgrade.migrations import m_3_2_7_redact_op_requests as redaction_migration
from specify_cli.upgrade.migrations.m_3_2_7_redact_op_requests import (
    OpRecordRequestRedactionMigration,
)
from specify_cli.upgrade.registry import MigrationRegistry
from specify_cli.upgrade.runner import MigrationRunner

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "kitty-ops").mkdir()
    return tmp_path


def _write(project: Path, name: str, lines: list[str]) -> Path:
    path = project / "kitty-ops" / name
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def _raw_v2_started(**overrides: object) -> str:
    data: dict[str, object] = {
        "event": "started",
        "invocation_id": ULID,
        "profile_id": "python-pedro",
        "action": "implement",
        "request_text": "rotate the secret",
        "actor": "codex",
        "mode_of_work": "task_execution",
        "governance_context_hash": "abcd1234abcd1234",
        "governance_context_available": True,
        "started_at": "2026-07-29T00:00:00Z",
        "model_id": "gpt-5.6",
    }
    data.update(overrides)
    return json.dumps(data)


def _raw_glossary_checked() -> str:
    """A historical observation with request-derived conflict details."""
    return json.dumps(
        {
            "event": "glossary_checked",
            "invocation_id": ULID,
            "matched_urns": ["glossary:d93244e7"],
            "high_severity": [
                {
                    "term": {"surface_text": "supersecret"},
                    "conflict_type": "ambiguous",
                    "severity": "high",
                    "candidate_senses": [{"surface": "supersecret", "definition": "secret request term"}],
                    "context": "request_text",
                }
            ],
            "all_conflicts": [
                {
                    "term": {"surface_text": "supersecret"},
                    "conflict_type": "ambiguous",
                    "severity": "high",
                    "candidate_senses": [{"surface": "supersecret", "definition": "secret request term"}],
                    "context": "request_text",
                }
            ],
            "tokens_checked": 3,
            "duration_ms": 1.4,
            "error_msg": None,
        }
    )


def _raw_candidate_event() -> str:
    return json.dumps(
        {
            "event_type": "TermCandidateObserved",
            "term": "supersecret",
            "source_step": f"profile-invocation:{ULID}",
            "actor_id": "codex",
            "confidence": 1.0,
            "extraction_method": "request_text",
            "context": "source: request_text",
            "mission_id": f"profile-invocation-{ULID}",
            "run_id": ULID,
            "timestamp": "2026-07-29T00:00:00Z",
        }
    )


def test_current_version_migration_redacts_raw_v2_request_and_preserves_model_id(
    project: Path,
) -> None:
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert result.success
    started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert "request_text" not in started
    assert started["request_summary"] == "Request content withheld by local trail policy."
    assert started["request_digest"].startswith("sha256:")
    assert started["model_id"] == "gpt-5.6"
    assert not migration.detect(project)


def test_schema_invalid_started_record_is_still_redacted(project: Path) -> None:
    """An older record missing a current-v2 field must not keep its raw request.

    This migration targets the current version, so a record skipped here is
    never revisited; validation must not decide whether the prompt is cleaned.
    """
    raw = json.loads(_raw_v2_started())
    del raw["mode_of_work"]
    raw["legacy_only_field"] = "preserved"
    path = _write(project, f"{ULID}.jsonl", [json.dumps(raw)])
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert result.success
    started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert "request_text" not in started
    assert started["request_summary"] == REDACTED_REQUEST_SUMMARY
    assert started["request_digest"].startswith("sha256:")
    # Only the raw request is removed; the rest is left to its schema migration.
    assert "mode_of_work" not in started
    assert started["legacy_only_field"] == "preserved"
    assert started["governance_context_hash"] == "abcd1234abcd1234"
    assert not migration.detect(project)


def test_schema_valid_started_record_keeps_its_extension_fields(project: Path) -> None:
    """A privacy pass must not silently discard unrelated append-only metadata.

    Extension or audit keys unknown to ``OpStartedEvent`` are ignored by the
    model, so rebuilding the row from the parsed event would drop them along
    with the raw request.
    """
    raw = json.loads(_raw_v2_started())
    raw["audit_trace_id"] = "trace-42"
    path = _write(project, f"{ULID}.jsonl", [json.dumps(raw)])
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert result.success, result.errors
    started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert "request_text" not in started
    assert started["request_summary"] == REDACTED_REQUEST_SUMMARY
    assert started["request_digest"].startswith("sha256:")
    assert started["audit_trace_id"] == "trace-42"
    assert started["mode_of_work"] == "task_execution"
    assert not migration.detect(project)


@pytest.mark.parametrize("request_value", [["rotate", "the", "secret"], {"request": "rotate the secret"}])
def test_non_string_raw_request_is_removed_without_inventing_a_digest(
    project: Path, request_value: object
) -> None:
    """JSON-valid historical request payloads can still contain sensitive text."""
    raw = json.loads(_raw_v2_started())
    raw["request_text"] = request_value
    raw["request_digest"] = "sha256:" + "a" * 64
    path = _write(project, f"{ULID}.jsonl", [json.dumps(raw)])

    result = OpRecordRequestRedactionMigration().apply(project)

    assert result.success, result.errors
    started = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert "request_text" not in started
    assert started["request_summary"] == REDACTED_REQUEST_SUMMARY
    assert "request_digest" not in started


def test_migration_redacts_historical_glossary_events_and_conflict_terms(
    project: Path,
) -> None:
    op_path = _write(
        project,
        f"{ULID}.jsonl",
        [_raw_v2_started(), _raw_glossary_checked()],
    )
    glossary_path = project / ".kittify" / "events" / "glossary" / f"profile-invocation-{ULID}.events.jsonl"
    glossary_path.parent.mkdir(parents=True)
    glossary_path.write_text(_raw_candidate_event() + "\n", encoding="utf-8")

    result = OpRecordRequestRedactionMigration().apply(project)

    assert result.success, result.errors
    op_contents = op_path.read_text(encoding="utf-8")
    glossary_contents = glossary_path.read_text(encoding="utf-8")
    assert "supersecret" not in op_contents
    assert "supersecret" not in glossary_contents

    observation = json.loads(op_contents.splitlines()[1])
    assert observation == {
        "event": "glossary_checked",
        "invocation_id": ULID,
        "matched_urns": ["glossary:d93244e7"],
        "conflict_count": 1,
        "high_severity_count": 1,
        "tokens_checked": 3,
        "duration_ms": 1.4,
        "error_present": False,
    }
    candidate = json.loads(glossary_contents)
    assert candidate["term"] == REDACTED_REQUEST_SUMMARY


def test_migration_is_selected_for_a_worktree_when_root_is_already_clean(
    project: Path,
) -> None:
    """Current-version cleanup cannot depend on the root checkout being dirty."""
    ProjectMetadata(version="3.2.7", initialized_at=datetime.now()).save(project / ".kittify")
    worktree = project / ".worktrees" / "request-redaction"
    (worktree / "kitty-ops").mkdir(parents=True)
    ProjectMetadata(version="3.2.7", initialized_at=datetime.now()).save(worktree / ".kittify")
    path = _write(worktree, f"{ULID}.jsonl", [_raw_v2_started()])

    result = MigrationRunner(project).upgrade("3.2.7", include_worktrees=True)

    assert result.success, result.errors
    assert "request_text" not in path.read_text(encoding="utf-8")


def test_runner_reapplies_recorded_redaction_when_raw_record_returns(project: Path) -> None:
    metadata = ProjectMetadata(version="3.2.7", initialized_at=datetime.now())
    metadata.record_migration("3.2.7_redact_op_record_requests", "success", "previous cleanup")
    metadata.save(project / ".kittify")
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])

    result = MigrationRunner(project).upgrade("3.2.7", include_worktrees=False)

    assert result.success, result.errors
    assert "request_text" not in path.read_text(encoding="utf-8")


def test_migration_does_not_follow_a_symlinked_worktree(project: Path) -> None:
    outside = project.parent / "outside-checkout"
    (outside / "kitty-ops").mkdir(parents=True)
    outside_record = _write(outside, f"{ULID}.jsonl", [_raw_v2_started()])
    worktrees = project / ".worktrees"
    worktrees.mkdir()
    try:
        (worktrees / "outside").symlink_to(outside, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - platform privilege dependent
        pytest.skip(f"symlinks unavailable: {exc}")

    migration = OpRecordRequestRedactionMigration()

    assert migration.detect(project) is False
    assert migration.apply(project).success
    assert "request_text" in outside_record.read_text(encoding="utf-8")


def test_migration_does_not_follow_a_symlinked_worktrees_root(project: Path) -> None:
    """A symlinked ``.worktrees`` exposes lanes whose own children look ordinary."""
    outside_lane = project.parent / "outside-worktrees" / "lane-a"
    (outside_lane / "kitty-ops").mkdir(parents=True)
    outside_record = _write(outside_lane, f"{ULID}.jsonl", [_raw_v2_started()])
    try:
        (project / ".worktrees").symlink_to(outside_lane.parent, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - platform privilege dependent
        pytest.skip(f"symlinks unavailable: {exc}")

    migration = OpRecordRequestRedactionMigration()

    assert migration.detect(project) is False
    assert migration.apply(project).success
    assert "request_text" in outside_record.read_text(encoding="utf-8")


def test_glossary_observation_keeps_fields_that_are_not_request_derived(project: Path) -> None:
    """Only the request-derived detail fields are replaced by their aggregates.

    The historical producer emitted the aggregates plus ``all_conflicts``,
    ``high_severity`` and ``error_msg``, so anything else on the row came from
    elsewhere and a privacy pass must not delete it.
    """
    raw = json.loads(_raw_glossary_checked())
    raw["audit_trace_id"] = "trace-42"
    path = _write(project, f"{ULID}.jsonl", [json.dumps(raw)])
    migration = OpRecordRequestRedactionMigration()

    assert migration.apply(project).success

    observation = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert "supersecret" not in path.read_text(encoding="utf-8")
    assert observation["audit_trace_id"] == "trace-42"
    assert observation["conflict_count"] == 1
    assert "all_conflicts" not in observation
    assert "high_severity" not in observation
    assert "error_msg" not in observation
    # Convergence: an annotated row that is already clean needs no rewrite.
    assert not migration.detect(project)
    before = path.read_bytes()
    assert migration.apply(project).success
    assert path.read_bytes() == before


def test_foreign_jsonl_in_kitty_ops_is_left_intact(project: Path) -> None:
    """``backup.jsonl`` is not an Op record, even holding a started object.

    ``InvocationWriter.invocation_path()`` only ever emits
    ``<invocation-ULID>.jsonl``, so any other name in the trail directory
    belongs to whoever put it there and is not this migration's to rewrite.
    """
    foreign = _write(project, "backup.jsonl", [_raw_v2_started()])
    before = foreign.read_bytes()
    migration = OpRecordRequestRedactionMigration()

    assert migration.detect(project) is False
    assert migration.apply(project).success
    assert foreign.read_bytes() == before


def test_authored_mission_glossary_log_is_left_intact(project: Path) -> None:
    """``profile-invocation-hardening`` is a Mission handle, not an invocation ID."""
    events_dir = project / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True)
    authored = events_dir / "profile-invocation-hardening.events.jsonl"
    authored.write_text(_raw_candidate_event() + "\n", encoding="utf-8")
    migration = OpRecordRequestRedactionMigration()

    assert migration.detect(project) is False
    assert migration.apply(project).success
    assert json.loads(authored.read_text(encoding="utf-8"))["term"] == "supersecret"


@pytest.mark.parametrize("trail", ["kitty-ops", ".kittify/events/glossary"])
def test_symlinked_trail_directory_is_not_rewritten(tmp_path: Path, trail: str) -> None:
    """``glob()`` follows a symlinked trail directory straight out of the checkout."""
    project = tmp_path / "repo"
    project.mkdir()
    outside = tmp_path / "other-checkout" / trail
    outside.mkdir(parents=True)
    is_glossary = trail != "kitty-ops"
    outside_record = outside / (f"profile-invocation-{ULID}.events.jsonl" if is_glossary else f"{ULID}.jsonl")
    outside_record.write_text((_raw_candidate_event() if is_glossary else _raw_v2_started()) + "\n", encoding="utf-8")
    link = project / trail
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - platform privilege dependent
        pytest.skip(f"symlinks unavailable: {exc}")
    migration = OpRecordRequestRedactionMigration()

    assert migration.detect(project) is False
    assert migration.apply(project).success

    raw_marker = "supersecret" if is_glossary else "request_text"
    assert raw_marker in outside_record.read_text(encoding="utf-8")


def test_op_record_rewrite_retries_instead_of_dropping_a_concurrent_append(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pre-patch record writer cannot be silently overwritten by the swap."""

    record_path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    late_line = json.dumps({"event": "completed", "invocation_id": ULID, "outcome": "success"})
    original_read_text = Path.read_text
    appended = False

    def _append_between_snapshot_and_swap(candidate: Path, *args: object, **kwargs: object) -> str:
        nonlocal appended
        contents = original_read_text(candidate, *args, **kwargs)
        if candidate == record_path and not appended:
            appended = True
            with record_path.open("a", encoding="utf-8") as handle:
                handle.write(late_line + "\n")
        return contents

    monkeypatch.setattr(Path, "read_text", _append_between_snapshot_and_swap)

    result = OpRecordRequestRedactionMigration().apply(project)

    assert result.success, result.errors
    assert appended
    events = [json.loads(line) for line in record_path.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == ["started", "completed"]
    assert all("request_text" not in event for event in events)
    assert events[0]["request_summary"] == REDACTED_REQUEST_SUMMARY


def test_op_record_rewrite_fails_closed_when_appends_never_settle(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exhausted retries must not report a still-raw record as redacted."""

    record_path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    original_read_text = Path.read_text

    def _append_on_every_read(candidate: Path, *args: object, **kwargs: object) -> str:
        contents = original_read_text(candidate, *args, **kwargs)
        if candidate == record_path:
            with record_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"event": "completed", "invocation_id": ULID}) + "\n")
        return contents

    monkeypatch.setattr(Path, "read_text", _append_on_every_read)

    result = OpRecordRequestRedactionMigration().apply(project)

    assert not result.success
    assert any(str(record_path) in error for error in result.errors)


def test_glossary_rewrite_retries_instead_of_dropping_a_concurrent_append(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pre-lock glossary writer cannot be silently overwritten by the swap."""

    events_dir = project / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True)
    glossary_path = events_dir / f"profile-invocation-{ULID}.events.jsonl"
    glossary_path.write_text(_raw_candidate_event() + "\n", encoding="utf-8")

    late_event = {"event_type": "TermSenseRegistered", "term": "kept-by-retry"}
    original_read_text = Path.read_text
    appended = False

    def _append_between_snapshot_and_swap(candidate: Path, *args: object, **kwargs: object) -> str:
        nonlocal appended
        contents = original_read_text(candidate, *args, **kwargs)
        if candidate == glossary_path and not appended:
            appended = True
            with glossary_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(late_event) + "\n")
        return contents

    monkeypatch.setattr(Path, "read_text", _append_between_snapshot_and_swap)

    result = OpRecordRequestRedactionMigration().apply(project)

    assert result.success, result.errors
    events = [json.loads(line) for line in glossary_path.read_text(encoding="utf-8").splitlines()]
    assert appended
    assert [event["term"] for event in events] == [REDACTED_REQUEST_SUMMARY, "kept-by-retry"]


def test_glossary_rewrite_fails_closed_when_appends_never_settle(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exhausted retries must not report a still-raw trail as redacted."""

    events_dir = project / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True)
    glossary_path = events_dir / f"profile-invocation-{ULID}.events.jsonl"
    glossary_path.write_text(_raw_candidate_event() + "\n", encoding="utf-8")

    original_read_text = Path.read_text

    def _append_on_every_read(candidate: Path, *args: object, **kwargs: object) -> str:
        contents = original_read_text(candidate, *args, **kwargs)
        if candidate == glossary_path:
            with glossary_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"event_type": "TermSenseRegistered", "term": "noise"}) + "\n")
        return contents

    monkeypatch.setattr(Path, "read_text", _append_on_every_read)

    result = OpRecordRequestRedactionMigration().apply(project)

    assert not result.success
    assert any(str(glossary_path) in error for error in result.errors)


def test_repeatable_redaction_stays_selectable_after_the_version_advances(project: Path) -> None:
    """A stale 3.2.7 executable can write a raw record into a 3.2.8+ checkout."""
    _write(project, f"{ULID}.jsonl", [_raw_v2_started()])

    applicable = MigrationRegistry.get_applicable("3.2.8", "3.3.0", project)

    assert any(candidate.migration_id == "3.2.7_redact_op_record_requests" for candidate in applicable)


def test_migration_fails_closed_when_an_eligible_record_cannot_be_read(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    original_read_text = Path.read_text

    def _unreadable(candidate: Path, *args: object, **kwargs: object) -> str:
        if candidate == path:
            raise OSError("permission denied")
        return original_read_text(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _unreadable)
    migration = OpRecordRequestRedactionMigration()

    assert migration.detect(project)
    result = migration.apply(project)

    assert not result.success
    assert any(str(path) in error for error in result.errors)


def test_blank_separator_line_does_not_block_the_redaction(project: Path) -> None:
    """Every canonical trail reader skips blank lines; so must this pass."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started(), "", _raw_glossary_checked()])
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert result.success, result.errors
    contents = path.read_text(encoding="utf-8")
    assert "request_text" not in contents
    assert "supersecret" not in contents
    events = [json.loads(line) for line in contents.splitlines() if line.strip()]
    assert [event["event"] for event in events] == ["started", "glossary_checked"]
    assert not migration.detect(project)


def test_lone_surrogate_request_is_redacted_instead_of_crashing(project: Path) -> None:
    """A historical JSON request can hold an unpaired surrogate."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started(request_text="rotate \udcff")])
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert result.success, result.errors
    event = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert "request_text" not in event
    assert event["request_summary"] == REDACTED_REQUEST_SUMMARY
    assert event["request_digest"].startswith("sha256:")
    assert not migration.detect(project)


def test_migration_fails_closed_on_malformed_eligible_line(project: Path) -> None:
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started(), "{not-json"])
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert not result.success
    assert any(str(path) in error for error in result.errors)
    assert migration.detect(project)
    assert "request_text" in path.read_text(encoding="utf-8")


def test_migration_does_not_follow_a_precreated_temporary_symlink(project: Path) -> None:
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    outside = project / "outside.txt"
    outside.write_text("leave untouched", encoding="utf-8")
    try:
        path.with_name(path.name + ".tmp").symlink_to(outside)
    except OSError as exc:  # pragma: no cover - platform privilege dependent
        pytest.skip(f"symlinks unavailable: {exc}")

    result = OpRecordRequestRedactionMigration().apply(project)

    assert result.success, result.errors
    assert outside.read_text(encoding="utf-8") == "leave untouched"
    assert "request_text" not in path.read_text(encoding="utf-8")


def test_append_landing_after_the_snapshot_check_survives_the_swap(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An uncoordinated append past the last check must not die with the inode."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    original_replace = redaction_migration.os.replace
    appended = False

    def _append_between_check_and_replace(source: object, target: object) -> None:
        nonlocal appended
        if not appended:
            appended = True
            with path.open("a", encoding="utf-8") as handle:
                handle.write(_raw_glossary_checked() + "\n")
        original_replace(source, target)

    monkeypatch.setattr(redaction_migration.os, "replace", _append_between_check_and_replace)

    result = OpRecordRequestRedactionMigration().apply(project)

    assert result.success, result.errors
    assert appended
    contents = path.read_text(encoding="utf-8")
    assert "request_text" not in contents
    assert "supersecret" not in contents
    events = [json.loads(line) for line in contents.splitlines()]
    assert [event["event"] for event in events] == ["started", "glossary_checked"]
    assert events[0]["request_summary"] == REDACTED_REQUEST_SUMMARY
    assert events[1]["high_severity_count"] == 1
    assert not OpRecordRequestRedactionMigration().detect(project)


@pytest.mark.timing
def test_drain_waits_for_a_writer_that_had_not_written_by_the_first_read(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One empty read of the replaced file is no proof that a writer is done."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    original_replace = redaction_migration.os.replace
    original_sleep = late_append_drain.time.sleep
    # A pre-patch appender that opened the record before the swap and only
    # writes once the redacted replacement is already installed.
    stale_writer: list[TextIO] = []
    written = False

    def _open_the_record_before_replacing_it(source: object, target: object) -> None:
        if not stale_writer:
            stale_writer.append(path.open("a", encoding="utf-8"))
        original_replace(source, target)

    def _write_while_the_drain_settles(seconds: float) -> None:
        nonlocal written
        if stale_writer and not written:
            written = True
            stale_writer[0].write(_raw_glossary_checked() + "\n")
            stale_writer[0].flush()
        original_sleep(seconds)

    monkeypatch.setattr(redaction_migration.os, "replace", _open_the_record_before_replacing_it)
    monkeypatch.setattr(late_append_drain.time, "sleep", _write_while_the_drain_settles)

    try:
        result = OpRecordRequestRedactionMigration().apply(project)
    finally:
        for handle in stale_writer:
            handle.close()

    assert result.success, result.errors
    assert written, "the drain released the replaced record without waiting for a settle window"
    contents = path.read_text(encoding="utf-8")
    assert "request_text" not in contents
    assert "supersecret" not in contents
    events = [json.loads(line) for line in contents.splitlines()]
    assert [event["event"] for event in events] == ["started", "glossary_checked"]
    assert events[1]["high_severity_count"] == 1


def _own_open_handles_to(path: Path) -> int:
    """Count this process's own open handles on *path* (needs Linux ``/proc``)."""
    handles = 0
    for entry in Path("/proc/self/fd").iterdir():
        try:
            if entry.resolve() == path.resolve():
                handles += 1
        except OSError:  # pragma: no cover - fd closed while scanning
            continue
    return handles


@pytest.mark.skipif(not Path("/proc/self/fd").exists(), reason="needs /proc to count open handles")
def test_swap_holds_no_handle_on_the_record_where_the_inode_cannot_be_drained(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows refuses to replace a destination this process still holds open."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    original_replace = redaction_migration.os.replace
    handles_at_swap: list[int] = []

    def _count_handles_then_replace(source: object, target: object) -> None:
        handles_at_swap.append(_own_open_handles_to(Path(str(target))))
        original_replace(source, target)

    monkeypatch.setattr(redaction_migration, "DRAIN_SUPPORTED", False)
    monkeypatch.setattr(redaction_migration.os, "replace", _count_handles_then_replace)

    result = OpRecordRequestRedactionMigration().apply(project)

    assert result.success, result.errors
    assert handles_at_swap == [0], "the swap ran with the record still open, which Windows rejects"
    contents = path.read_text(encoding="utf-8")
    assert "request_text" not in contents
    assert json.loads(contents.splitlines()[0])["request_summary"] == REDACTED_REQUEST_SUMMARY
    assert not OpRecordRequestRedactionMigration().detect(project)


@pytest.mark.timing
def test_drain_waits_out_a_writer_descheduled_past_a_single_settle_interval(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale writer gets a quiet window, not one pause, to reach its write."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    original_replace = redaction_migration.os.replace
    original_sleep = late_append_drain.time.sleep
    stale_writer: list[TextIO] = []
    settles = 0

    def _open_the_record_before_replacing_it(source: object, target: object) -> None:
        if not stale_writer:
            stale_writer.append(path.open("a", encoding="utf-8"))
        original_replace(source, target)

    def _write_after_more_than_one_settle(seconds: float) -> None:
        nonlocal settles
        settles += 1
        # One settle interval is the whole wait a read-counted drain gave a
        # stale writer, and an ordinary scheduling delay outlasts it.
        if stale_writer and settles == 3:
            stale_writer[0].write(_raw_glossary_checked() + "\n")
            stale_writer[0].flush()
        original_sleep(seconds)

    monkeypatch.setattr(redaction_migration.os, "replace", _open_the_record_before_replacing_it)
    monkeypatch.setattr(late_append_drain.time, "sleep", _write_after_more_than_one_settle)

    try:
        result = OpRecordRequestRedactionMigration().apply(project)
    finally:
        for handle in stale_writer:
            handle.close()

    assert result.success, result.errors
    assert settles >= 3, "the drain released the replaced record after a single settle interval"
    contents = path.read_text(encoding="utf-8")
    assert "supersecret" not in contents
    events = [json.loads(line) for line in contents.splitlines()]
    assert [event["event"] for event in events] == ["started", "glossary_checked"]
    assert events[1]["high_severity_count"] == 1


def test_settled_partial_append_does_not_fail_an_installed_redaction(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A half-written trailing record must not fail a redaction that completed."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    original_replace = redaction_migration.os.replace
    appended = False

    def _append_a_truncated_line(source: object, target: object) -> None:
        nonlocal appended
        if not appended:
            appended = True
            with path.open("a", encoding="utf-8") as handle:
                handle.write('{"event": "glossary_checked"')
        original_replace(source, target)

    monkeypatch.setattr(redaction_migration.os, "replace", _append_a_truncated_line)

    result = OpRecordRequestRedactionMigration().apply(project)

    assert appended
    assert result.errors == []
    assert result.success
    contents = path.read_text(encoding="utf-8")
    assert "request_text" not in contents
    events = [json.loads(line) for line in contents.splitlines()]
    assert [event["event"] for event in events] == ["started"]
    assert events[0]["request_summary"] == REDACTED_REQUEST_SUMMARY
    assert not OpRecordRequestRedactionMigration().detect(project)


def test_symlinked_record_lock_is_reported_rather_than_raised(project: Path) -> None:
    """The lock guard refuses a symlinked lock as a reported migration failure."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    outside = project / "outside.lock"
    outside.write_text("", encoding="utf-8")
    try:
        path.with_name(f".{path.name}.lock").symlink_to(outside)
    except OSError as exc:  # pragma: no cover - platform dependent
        pytest.skip(f"symlinks unavailable: {exc}")

    result = OpRecordRequestRedactionMigration().apply(project)

    assert not result.success
    assert any("Could not rewrite" in error for error in result.errors)
    assert "request_text" in path.read_text(encoding="utf-8")


@pytest.mark.timing
def test_migration_does_not_drop_an_append_started_during_atomic_rewrite(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The migration and normal writer share one lock for an Op JSONL file."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    writer = InvocationWriter(project)
    append_started = Event()
    append_finished = Event()

    def _append_link() -> None:
        append_started.set()
        writer.append_correlation_link(ULID, ref="evidence.md")
        append_finished.set()

    append_thread = Thread(target=_append_link)
    original_replace = redaction_migration.os.replace

    def _replace_after_append_attempt(source: object, target: object) -> None:
        append_thread.start()
        assert append_started.wait(timeout=1)
        time.sleep(0.05)
        assert not append_finished.is_set()
        original_replace(source, target)

    monkeypatch.setattr(redaction_migration.os, "replace", _replace_after_append_attempt)

    result = OpRecordRequestRedactionMigration().apply(project)
    append_thread.join(timeout=1)

    assert result.success, result.errors
    assert append_finished.is_set()
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert "request_text" not in lines[0]
    assert lines[-1]["event"] == "artifact_link"


@pytest.mark.timing
def test_migration_does_not_drop_a_glossary_event_appended_during_rewrite(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    glossary_path = _write_glossary_log(project, [_glossary_event()])
    append_started = Event()
    append_finished = Event()

    def _append_scope_event() -> None:
        append_started.set()
        glossary_events.append_event(
            {"event_type": "GlossaryScopeActivated", "scope": "project"},
            glossary_path,
        )
        append_finished.set()

    append_thread = Thread(target=_append_scope_event)
    original_replace = redaction_migration.os.replace

    def _replace_after_append_attempt(source: object, target: object) -> None:
        append_thread.start()
        assert append_started.wait(timeout=1)
        time.sleep(0.05)
        assert not append_finished.is_set()
        original_replace(source, target)

    monkeypatch.setattr(glossary_events, "EVENTS_AVAILABLE", False)
    monkeypatch.setattr(redaction_migration.os, "replace", _replace_after_append_attempt)

    result = OpRecordRequestRedactionMigration().apply(project)
    append_thread.join(timeout=1)

    assert result.success, result.errors
    assert append_finished.is_set()
    events = [json.loads(line) for line in glossary_path.read_text(encoding="utf-8").splitlines()]
    assert events[0]["term"] == REDACTED_REQUEST_SUMMARY
    assert events[-1] == {"event_type": "GlossaryScopeActivated", "scope": "project"}


def test_current_version_migration_is_selected_for_upgraded_projects(project: Path) -> None:
    _write(project, f"{ULID}.jsonl", [_raw_v2_started()])

    applicable = MigrationRegistry.get_applicable("3.2.7", "3.2.7", project)

    assert any(migration.migration_id == "3.2.7_redact_op_record_requests" for migration in applicable)


def _worktree_record(project: Path) -> Path:
    ops_dir = project / ".worktrees" / "mission-lane-a" / "kitty-ops"
    ops_dir.mkdir(parents=True)
    path = ops_dir / f"{ULID}.jsonl"
    path.write_text(_raw_v2_started() + "\n", encoding="utf-8")
    return path


def test_detect_sees_records_that_only_exist_in_worktrees(project: Path) -> None:
    _worktree_record(project)
    migration = OpRecordRequestRedactionMigration()

    assert migration.detect(project)
    assert migration.can_apply(project) == (True, "")
    applicable = MigrationRegistry.get_applicable("3.2.7", "3.2.7", project)
    assert any(candidate.migration_id == migration.migration_id for candidate in applicable)


def test_worktree_records_are_redacted_when_the_worktree_is_the_target(project: Path) -> None:
    path = _worktree_record(project)
    worktree = path.parent.parent
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(worktree)

    assert result.success
    assert "request_text" not in json.loads(path.read_text(encoding="utf-8").splitlines()[0])


def test_root_pass_reports_the_lane_it_did_not_clean(project: Path) -> None:
    """The root only cleans its own checkout, so it cannot claim the lane's records."""
    path = _worktree_record(project)

    result = OpRecordRequestRedactionMigration().apply(project)

    assert result.success
    assert result.changes_made == []
    assert result.warnings == [
        "Request-derived data remains in .worktrees/mission-lane-a; it is redacted when that lane is upgraded"
    ]
    assert "request_text" in path.read_text(encoding="utf-8")


def test_no_worktrees_upgrade_does_not_claim_lane_records_are_clean(project: Path) -> None:
    """``--no-worktrees`` must not report a privacy cleanup the lane never got."""
    ProjectMetadata(version="3.2.7", initialized_at=datetime.now()).save(project / ".kittify")
    path = _worktree_record(project)

    result = MigrationRunner(project).upgrade("3.2.7", include_worktrees=False)

    assert result.success, result.errors
    assert "request_text" in path.read_text(encoding="utf-8")
    assert any("Request-derived data remains in .worktrees/mission-lane-a" in warning for warning in result.warnings)


def test_root_pass_stays_quiet_once_the_lane_is_clean(project: Path) -> None:
    """A redacted lane must not keep warning on every later upgrade."""
    path = _worktree_record(project)
    assert OpRecordRequestRedactionMigration().apply(path.parent.parent).success

    result = OpRecordRequestRedactionMigration().apply(project)

    assert result.success
    assert result.warnings == []


def test_unreadable_record_fails_instead_of_reporting_success(project: Path) -> None:
    path = project / "kitty-ops" / f"{ULID}.jsonl"
    path.write_bytes(b"\xff\xfe not utf-8\n")
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert not result.success
    assert any(str(path) in error for error in result.errors)
    assert not result.changes_made
    # An unreadable record must not be cleared as "not applicable".
    assert migration.detect(project)


def _glossary_event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        "event_type": "TermCandidateObserved",
        "term": "ghp-supersecrettoken",
        "source_step": f"profile-invocation:{ULID}",
        "actor_id": "codex",
        "confidence": 1.0,
        "extraction_method": "request_text",
        "context": "source: request_text",
        "mission_id": f"profile-invocation-{ULID}",
        "run_id": ULID,
        "timestamp": "2026-07-29T00:00:00Z",
    }
    event.update(overrides)
    return event


def _write_glossary_log(root: Path, events: list[dict[str, object]]) -> Path:
    events_dir = root / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True, exist_ok=True)
    path = events_dir / f"profile-invocation-{ULID}.events.jsonl"
    path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
    return path


def test_glossary_term_candidates_are_redacted(project: Path) -> None:
    unrelated = {
        "event_type": "GlossaryScopeActivated",
        "scope_id": "team_domain",
        "run_id": ULID,
    }
    path = _write_glossary_log(project, [_glossary_event(), unrelated])
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert result.success
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["term"] == REDACTED_REQUEST_SUMMARY
    # Correlation metadata is preserved; only the request-derived surface goes.
    assert lines[0]["run_id"] == ULID
    assert lines[0]["extraction_method"] == "request_text"
    assert lines[1] == unrelated
    assert not migration.detect(project)


@pytest.mark.parametrize("term", [["rotate", "the", "secret"], {"request": "rotate the secret"}])
def test_non_string_glossary_candidate_term_is_redacted(project: Path, term: object) -> None:
    path = _write_glossary_log(project, [_glossary_event(term=term)])
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert result.success, result.errors
    event = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert event["term"] == REDACTED_REQUEST_SUMMARY
    assert not migration.detect(project)


def test_glossary_only_project_is_detected_without_kitty_ops(tmp_path: Path) -> None:
    _write_glossary_log(tmp_path, [_glossary_event()])
    migration = OpRecordRequestRedactionMigration()

    assert not (tmp_path / "kitty-ops").exists()
    assert migration.detect(tmp_path)
    assert migration.can_apply(tmp_path) == (True, "")


def test_glossary_events_in_worktrees_are_detected(project: Path) -> None:
    worktree = project / ".worktrees" / "mission-lane-a"
    worktree.mkdir(parents=True)
    _write_glossary_log(worktree, [_glossary_event()])
    migration = OpRecordRequestRedactionMigration()

    assert migration.detect(project)
    applicable = MigrationRegistry.get_applicable("3.2.7", "3.2.7", project)
    assert any(candidate.migration_id == migration.migration_id for candidate in applicable)


def test_already_redacted_glossary_events_are_left_alone(project: Path) -> None:
    path = _write_glossary_log(project, [_glossary_event(term=REDACTED_REQUEST_SUMMARY)])
    original = path.read_text(encoding="utf-8")
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert result.success
    assert result.changes_made == []
    assert path.read_text(encoding="utf-8") == original
    assert not migration.detect(project)


def test_mission_scoped_glossary_logs_are_untouched(project: Path) -> None:
    events_dir = project / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True)
    path = events_dir / "034-some-mission.events.jsonl"
    original = json.dumps(_glossary_event(term="lane"), sort_keys=True) + "\n"
    path.write_text(original, encoding="utf-8")
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project)

    assert result.success
    # Mission logs carry authored mission text, which this policy does not cover.
    assert path.read_text(encoding="utf-8") == original
    assert not migration.detect(project)


def test_dry_run_reports_changes_without_writing(project: Path) -> None:
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    original = path.read_text(encoding="utf-8")
    migration = OpRecordRequestRedactionMigration()

    result = migration.apply(project, dry_run=True)

    assert result.success
    assert result.changes_made == [f"Would redact request-derived data in {path.name}"]
    assert path.read_text(encoding="utf-8") == original


def test_dry_run_takes_neither_rewrite_lock(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A preview must not create the adjacent .lock files in the checkout."""
    _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    _write_glossary_log(project, [_glossary_event()])
    taken: list[Path] = []

    def _spy(path: Path) -> contextlib.AbstractContextManager[None]:
        taken.append(path)
        return contextlib.nullcontext()

    monkeypatch.setattr(redaction_migration, "invocation_record_lock", _spy)
    monkeypatch.setattr(redaction_migration, "glossary_event_lock", _spy)

    result = OpRecordRequestRedactionMigration().apply(project, dry_run=True)

    assert result.success
    assert len(result.changes_made) == 2
    assert taken == []


@pytest.mark.timing
def test_dry_run_does_not_wait_on_a_held_record_lock(project: Path) -> None:
    """A preview must not stall on a live writer's lock timeout."""
    path = _write(project, f"{ULID}.jsonl", [_raw_v2_started()])
    migration = OpRecordRequestRedactionMigration()

    with FileLock(str(path.with_name(f".{path.name}.lock")), timeout=5):
        started = time.monotonic()
        result = migration.apply(project, dry_run=True)
        elapsed = time.monotonic() - started

    assert result.success
    assert result.changes_made == [f"Would redact request-derived data in {path.name}"]
    # The real path would block for the writer's full lock timeout.
    assert elapsed < invocation_writer._INVOCATION_LOCK_TIMEOUT_SECONDS
