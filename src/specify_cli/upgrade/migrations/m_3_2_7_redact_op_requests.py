"""Redact request-derived data from local profile-invocation trails.

Historical records can contain the dispatched request in three local places:
Op ``started`` records, their ``glossary_checked`` details, and unknown-term
candidate events. The migration clears all three without touching authored,
mission-scoped glossary logs.
"""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, TextIO

from filelock import Timeout

from glossary.events import glossary_event_lock
from specify_cli.invocation.writer import invocation_record_lock

from ..path_containment import contained_subdir
from ..registry import MigrationRegistry
from ._late_append_drain import DRAIN_SUPPORTED, drain_late_appends
from .base import BaseMigration, MigrationResult

_OPS_DIR = "kitty-ops"
_WORKTREES_DIR = ".worktrees"
_GLOSSARY_EVENTS_DIR = (".kittify", "events", "glossary")
_INVOCATION_LOG_PREFIX = "profile-invocation-"
_EVENTS_LOG_SUFFIX = ".events.jsonl"
_INVOCATION_EVENTS_GLOB = f"{_INVOCATION_LOG_PREFIX}*{_EVENTS_LOG_SUFFIX}"
_EXCLUDED_FILES = frozenset({"ops-index.jsonl", "lifecycle.jsonl", "propagation-errors.jsonl"})
#: ``glossary_checked`` fields derived from the request; the aggregates replace them.
_UNSAFE_GLOSSARY_DETAIL_FIELDS = frozenset({"all_conflicts", "high_severity", "error_msg"})
# A pre-patch appender that does not take this rewrite's lock — for either trail
# kind — can still be running when an upgraded process starts. Re-read and retry
# a log if such a writer changes it between the snapshot and the atomic swap.
_REWRITE_ATTEMPTS = 3

LineRedactor = Callable[[dict[str, Any]], str | None]


class _MalformedEligibleRecordError(ValueError):
    """An eligible JSONL record is not safe to declare redacted."""


def _is_op_record(path: Path) -> bool:
    """Only ``<invocation-ULID>.jsonl`` files are Op records.

    ``InvocationWriter.invocation_path()`` emits no other name, so a foreign
    JSONL parked in the trail directory (an operator backup, another tool's log)
    is not this migration's to rewrite even when it holds a ``started`` object
    with a request. The stem check subsumes the sibling trail files named in
    ``_EXCLUDED_FILES``, which stay listed to keep that guarantee explicit.
    """
    from specify_cli.invocation.record import validate_invocation_id

    try:
        validate_invocation_id(path.stem)
    except ValueError:
        return False
    return True


def _eligible_files(root: Path) -> list[Path]:
    ops_dir = contained_subdir(root, _OPS_DIR)
    if ops_dir is None:
        return []
    # A symlinked record resolves outside this directory for the same reason.
    return sorted(
        path
        for path in ops_dir.glob("*.jsonl")
        if path.name not in _EXCLUDED_FILES and _is_op_record(path) and not path.is_symlink()
    )


def _is_synthetic_invocation_log(path: Path) -> bool:
    """Only ``profile-invocation-<ULID>`` logs are synthetic dispatch trails.

    An authored Mission whose identifier merely starts with the same prefix
    (``profile-invocation-hardening``) owns mission-scoped glossary history this
    migration promises to leave intact.
    """
    from specify_cli.invocation.record import validate_invocation_id

    invocation_id = path.name[len(_INVOCATION_LOG_PREFIX) : -len(_EVENTS_LOG_SUFFIX)]
    try:
        validate_invocation_id(invocation_id)
    except ValueError:
        return False
    return True


def _glossary_event_files(root: Path) -> list[Path]:
    events_dir = contained_subdir(root, *_GLOSSARY_EVENTS_DIR)
    if events_dir is None:
        return []
    return sorted(path for path in events_dir.glob(_INVOCATION_EVENTS_GLOB) if _is_synthetic_invocation_log(path) and not path.is_symlink())


def _lane_roots(project_path: Path) -> list[Path]:
    """Return the lane worktrees beneath a checkout."""
    # A symlinked ``.worktrees`` points at lanes of another checkout, whose own
    # children are ordinary directories that the per-child guard below accepts.
    worktrees_dir = contained_subdir(project_path, _WORKTREES_DIR)
    if worktrees_dir is None:
        return []
    return sorted(child for child in worktrees_dir.iterdir() if child.is_dir() and not child.is_symlink())


def _checkout_roots(project_path: Path) -> list[Path]:
    """Return the root checkout and the lane worktrees beneath it."""
    return [project_path, *_lane_roots(project_path)]


def _redact_started_event(data: dict[str, Any]) -> str | None:
    """Return a redacted started line, including schema-invalid historical rows.

    This is a current-version migration: if a raw request is skipped because a
    later schema field is absent, it may never be revisited. Every row retains
    its original shape, except for the raw field and its safe provenance: the
    trail is append-only, so extension or audit keys the event model ignores
    must survive a privacy pass rather than be dropped by a model rebuild.
    """
    from specify_cli.invocation.record import REDACTED_REQUEST_SUMMARY, request_provenance

    if data.get("event") != "started" or "request_text" not in data:
        return None
    request_text = data["request_text"]
    if isinstance(request_text, str):
        request_summary, request_digest = request_provenance(request_text)
    else:
        # Historical JSONL can contain a non-string request payload. It may
        # still expose request content, but it has no trustworthy string form
        # from which to derive durable correlation provenance.
        request_summary = REDACTED_REQUEST_SUMMARY
        request_digest = None
    payload = {key: value for key, value in data.items() if key != "request_text"}
    payload["request_summary"] = request_summary
    if request_digest is None:
        payload.pop("request_digest", None)
    else:
        payload["request_digest"] = request_digest
    return json.dumps(payload)


def _safe_string_list(value: object) -> list[str]:
    return list(value) if isinstance(value, list) and all(isinstance(item, str) for item in value) else []


def _safe_nonnegative_int(value: object, fallback: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else fallback


def _safe_duration(value: object) -> float | int:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else 0.0


def _redact_glossary_checked_event(data: dict[str, Any]) -> str | None:
    """Replace request-derived glossary details with durable aggregate facts.

    The historical producer emitted the aggregate fields plus the three detail
    fields in ``_UNSAFE_GLOSSARY_DETAIL_FIELDS``, so dropping those by name is
    exhaustive for a real trail row. Every other key came from somewhere else
    (an operator or tooling annotation) and survives, instead of being deleted
    by a rebuild that keeps only the fields this function names.
    """
    if data.get("event") != "glossary_checked":
        return None
    all_conflicts = data.get("all_conflicts")
    high_severity = data.get("high_severity")
    safe_event = {key: value for key, value in data.items() if key not in _UNSAFE_GLOSSARY_DETAIL_FIELDS}
    safe_event |= {
        "event": "glossary_checked",
        "invocation_id": data.get("invocation_id"),
        "matched_urns": _safe_string_list(data.get("matched_urns")),
        "conflict_count": _safe_nonnegative_int(data.get("conflict_count"), len(all_conflicts) if isinstance(all_conflicts, list) else 0),
        "high_severity_count": _safe_nonnegative_int(data.get("high_severity_count"), len(high_severity) if isinstance(high_severity, list) else 0),
        "tokens_checked": _safe_nonnegative_int(data.get("tokens_checked"), 0),
        "duration_ms": _safe_duration(data.get("duration_ms")),
        "error_present": bool(data.get("error_present") or data.get("error_msg")),
    }
    return None if data == safe_event else json.dumps(safe_event)


def _redact_term_candidate(data: dict[str, Any]) -> str | None:
    """Redact unknown request tokens in profile-invocation glossary events."""
    from specify_cli.invocation.record import REDACTED_REQUEST_SUMMARY

    if data.get("event_type") != "TermCandidateObserved" or "term" not in data:
        return None
    term = data["term"]
    if term == REDACTED_REQUEST_SUMMARY:
        return None
    payload = dict(data)
    payload["term"] = REDACTED_REQUEST_SUMMARY
    return json.dumps(payload, sort_keys=True, default=str)


def _redact_lines(lines: list[str], redactors: tuple[LineRedactor, ...]) -> list[str] | None:
    """Return replacement lines, or ``None`` when no line needs redaction."""
    rewritten: list[str] = []
    changed = False
    for line in lines:
        # Every canonical trail reader tolerates a blank separator line
        # (``InvocationWriter`` and ``glossary.events`` both skip them), so
        # refusing one here would report a readable record as malformed and,
        # because this pass is repeatable and worktree-fatal, block every later
        # upgrade while its raw rows stay unredacted. Keep the line verbatim.
        if not line.strip():
            rewritten.append(line)
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise _MalformedEligibleRecordError("malformed JSONL line") from exc
        if not isinstance(data, dict):
            raise _MalformedEligibleRecordError("non-object JSONL line")
        redacted = None
        for redact in redactors:
            redacted = redact(data)
            if redacted is not None:
                break
        if redacted is None:
            rewritten.append(line)
            continue
        rewritten.append(redacted)
        changed = True
    return rewritten if changed else None


@dataclass(frozen=True)
class _RewriteOutcome:
    changed: bool = False
    error: str | None = None
    # The file moved under us between the snapshot and the swap.
    stale: bool = False


def _rewrite_file(
    path: Path,
    redactors: tuple[LineRedactor, ...],
    dry_run: bool,
    *,
    is_op_record: bool,
) -> _RewriteOutcome:
    """Rewrite one eligible trail file, retrying when an append races the swap."""
    # Current appenders of both trail kinds share this rewrite's lock. The late
    # snapshot check inside ``_install_redacted`` is a compatibility guard
    # against a pre-patch writer that does not yet honor it; retry instead of
    # discarding the append that writer just made.
    for _ in range(_REWRITE_ATTEMPTS):
        outcome = _rewrite_once(path, redactors, dry_run, is_op_record=is_op_record)
        if not outcome.stale:
            return outcome
    return _RewriteOutcome(error=f"Could not redact {path}: concurrent appends kept changing the file")


def _append_redacted(path: Path, lines: list[str], redactors: tuple[LineRedactor, ...]) -> str | None:
    """Append drained lines to the installed file, redacted."""
    try:
        redacted = _redact_lines(lines, redactors)
    except _MalformedEligibleRecordError as exc:
        return f"Could not redact {path}: {exc}"
    with path.open("a", encoding="utf-8") as installed:
        installed.write("\n".join(lines if redacted is None else redacted) + "\n")
    return None


def _drain_late_appends(source: TextIO, path: Path, redactors: tuple[LineRedactor, ...]) -> str | None:
    """Carry appends that landed on the replaced file onto the installed one.

    ``source`` still holds the file the swap unlinked open, so lines an
    uncoordinated writer appended after the snapshot check stay readable once
    the replacement is installed. Redact those lines onto the installed file
    instead of letting them die with the old inode. The settle protocol is
    shared with the schema migration; see :mod:`._late_append_drain`.
    """
    return drain_late_appends(source, path, lambda late: _append_redacted(path, late, redactors))


def _install_redacted(
    path: Path,
    lines: list[str],
    redacted: list[str],
    redactors: tuple[LineRedactor, ...],
) -> _RewriteOutcome:
    """Swap in the redacted content without losing an append that races it."""
    tmp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write("\n".join(redacted) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        # Current appenders share the caller's lock. Compare against the
        # snapshot to catch an older, uncoordinated writer's append and let the
        # caller retry rather than replace over it. An append can still land in
        # the window between that comparison and the swap, so read the
        # comparison through a handle that outlives the swap and drain whatever
        # arrived late instead of unlinking it with the file.
        with path.open("r", encoding="utf-8") as source:
            if source.read().splitlines() != lines:
                return _RewriteOutcome(stale=True)
            if DRAIN_SUPPORTED:
                os.replace(tmp_path, path)
                return _RewriteOutcome(changed=True, error=_drain_late_appends(source, path, redactors))
        # Where the inode cannot be drained (see ``DRAIN_SUPPORTED``), the swap
        # must happen after the compare handle is closed, or it fails outright.
        os.replace(tmp_path, path)
        return _RewriteOutcome(changed=True)
    except UnicodeDecodeError:
        return _RewriteOutcome(error=f"Could not read {path}; request-derived data may remain")
    finally:
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                tmp_path.unlink(missing_ok=True)


def _rewrite_once(
    path: Path,
    redactors: tuple[LineRedactor, ...],
    dry_run: bool,
    *,
    is_op_record: bool,
) -> _RewriteOutcome:
    """Rewrite one eligible trail file, reporting unreadable files as failures."""
    # A dry run only previews, so it must not create the adjacent .lock file in
    # the checkout or wait out a live writer's lock timeout.
    lock_context = (
        contextlib.nullcontext()
        if dry_run
        else (invocation_record_lock(path) if is_op_record else glossary_event_lock(path))
    )
    try:
        with lock_context:
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                return _RewriteOutcome(error=f"Could not read {path}; request-derived data may remain")
            try:
                redacted = _redact_lines(lines, redactors)
            except _MalformedEligibleRecordError as exc:
                return _RewriteOutcome(error=f"Could not redact {path}: {exc}")
            if redacted is None:
                return _RewriteOutcome()
            if dry_run:
                return _RewriteOutcome(changed=True)
            return _install_redacted(path, lines, redacted, redactors)
    except Timeout:
        return _RewriteOutcome(error=f"Timed out waiting to redact {path}; request-derived data may remain")
    except OSError:
        return _RewriteOutcome(error=f"Could not rewrite {path}; request-derived data may remain")


def _redaction_targets(root: Path) -> list[tuple[Path, tuple[LineRedactor, ...], bool]]:
    targets: list[tuple[Path, tuple[LineRedactor, ...], bool]] = [
        (path, (_redact_started_event, _redact_glossary_checked_event), True) for path in _eligible_files(root)
    ]
    targets.extend((path, (_redact_term_candidate,), False) for path in _glossary_event_files(root))
    return targets


def _root_needs_redaction(root: Path) -> bool:
    """Report whether one checkout still holds request-derived data."""
    for path, redactors, _lock in _redaction_targets(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return True
        try:
            if _redact_lines(lines, redactors) is not None:
                return True
        except _MalformedEligibleRecordError:
            return True
    return False


@MigrationRegistry.register
class OpRecordRequestRedactionMigration(BaseMigration):
    """Remove request-derived data from current and historical local trails."""

    migration_id = "3.2.7_redact_op_record_requests"
    description = "Redact request-derived data from existing profile-invocation trails"
    target_version = "3.2.7"
    runs_on_worktrees = True
    worktree_failure_is_fatal = True
    reapply_when_detected = True

    def detect(self, project_path: Path) -> bool:
        # Roots-wide on purpose: the registry only reaches a lane's records if a
        # current-version cleanup is selectable from the root checkout, so a
        # root-scoped detector would drop the migration and leave lane records
        # raw forever. ``apply()`` stays inside the checkout it is handed
        # because the runner then visits each lane itself.
        return any(_root_needs_redaction(root) for root in _checkout_roots(project_path))

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        for root in _checkout_roots(project_path):
            if contained_subdir(root, _OPS_DIR) is not None or contained_subdir(root, *_GLOSSARY_EVENTS_DIR) is not None:
                return True, ""
        return False, "kitty-ops/ directory does not exist"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        changes: list[str] = []
        errors: list[str] = []
        for path, redactors, is_op_record in _redaction_targets(project_path):
            outcome = _rewrite_file(path, redactors, dry_run, is_op_record=is_op_record)
            if outcome.error is not None:
                errors.append(outcome.error)
            elif outcome.changed:
                verb = "Would redact" if dry_run else "Redacted"
                changes.append(f"{verb} request-derived data in {path.name}")
        # This pass cleans one checkout, so a lane the runner has not reached
        # yet (or was told to skip with --no-worktrees) must not be reported as
        # cleaned by the root's success.
        warnings = [
            f"Request-derived data remains in {_WORKTREES_DIR}/{lane.name}; it is redacted when that lane is upgraded"
            for lane in _lane_roots(project_path)
            if _root_needs_redaction(lane)
        ]
        return MigrationResult(success=not errors, changes_made=changes, errors=errors, warnings=warnings)
