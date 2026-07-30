"""Migration: rewrite legacy ``kitty-ops/*.jsonl`` Op records to the v2 event schema.

This is the **sole** sanctioned in-place mutation of Op records (C-004
exception, FR-011). Per the normative mapping table in the mission data model:

- started events with ``invocation_id`` + ``profile_id`` are rewritten to
  ``OpStartedEvent`` (missing ``mode_of_work`` -> ``"task_execution"``;
  missing/empty ``actor`` / ``action`` -> the literal ``"unrecorded"`` —
  never a fabricated plausible value)
- completed events gain ``closed_by="agent"``; a null ``outcome`` (old
  auto-close artifact) becomes ``outcome="abandoned"``; a missing
  ``completed_at`` falls back to the started event's ``started_at`` and is
  flagged in the migration report
- link/glossary lines pass through byte-identical
- files with an unparseable or identity-less started event are deleted and
  reported (operator-visible: count + filenames)
- already-v2 files are skipped untouched (idempotency, NFR-004)

Excluded files (different schemas, never touched): ``ops-index.jsonl``,
``lifecycle.jsonl``, ``propagation-errors.jsonl``.

``ops-index.jsonl`` consistency: deleting a per-op file can leave a dangling
index entry. The index reader (``invocations_cmd._iter_records_from_index``)
tolerates missing files — ``_read_first_line`` / ``_read_completed_record``
catch ``OSError`` and degrade gracefully — so this migration deliberately
leaves the index alone.

Rewrites are atomic: content is written to a unique, private same-directory
temporary file and moved over the original with ``os.replace``.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any, TextIO, cast

from filelock import Timeout
from pydantic import ValidationError

from specify_cli.invocation.writer import invocation_record_lock

if TYPE_CHECKING:
    from specify_cli.invocation.record import OpStartedEvent

from ..registry import MigrationRegistry
from ._late_append_drain import DRAIN_SUPPORTED, drain_late_appends
from .base import BaseMigration, MigrationResult
from ..path_containment import contained_subdir

#: kitty-ops files with different schemas that this migration must never touch.
EXCLUDED_FILES: frozenset[str] = frozenset(
    {
        "ops-index.jsonl",
        "lifecycle.jsonl",
        "propagation-errors.jsonl",
    }
)

_OPS_DIR = "kitty-ops"
_WORKTREES_DIR = ".worktrees"
_RECORD_SUFFIX = ".jsonl"
_REWRITE_ATTEMPTS = 3
# Quarantined records keep their bytes on disk under a name that
# _eligible_files() cannot match, so they are never re-planned by accident.
_QUARANTINE_SUFFIX = ".unsalvageable"


def _is_op_record(path: Path) -> bool:
    """Only ``<invocation-ULID>.jsonl`` files are Op records.

    ``InvocationWriter.invocation_path()`` emits no other name, so a foreign
    JSONL parked in the trail directory (an operator backup, another tool's log)
    is not this migration's to plan: an unrepairable record is deleted, so
    misreading one as an Op record destroys it. The stem check subsumes the
    sibling trail files named in ``EXCLUDED_FILES``, which stay listed to keep
    that guarantee explicit.
    """
    from specify_cli.invocation.record import validate_invocation_id

    try:
        validate_invocation_id(path.stem)
    except ValueError:
        return False
    return True


def _eligible_files(root: Path) -> list[Path]:
    """Per-op JSONL files in *root*'s ``kitty-ops/``, minus the special files.

    The directory is resolved through :func:`contained_subdir` because
    ``is_dir()`` and ``glob()`` follow symlinks: a symlinked ``kitty-ops`` would
    let the rewrite replace, or the delete remove, another checkout's records.
    A symlinked record escapes the same way.
    """
    ops_dir = contained_subdir(root, _OPS_DIR)
    if ops_dir is None:
        return []
    return sorted(
        p
        for p in ops_dir.glob(f"*{_RECORD_SUFFIX}")
        if p.name not in EXCLUDED_FILES and _is_op_record(p) and not p.is_symlink()
    )


def _checkout_roots(project_path: Path) -> list[Path]:
    """Return the root checkout plus contained, non-symlink worktrees."""
    roots = [project_path]
    worktrees_dir = contained_subdir(project_path, _WORKTREES_DIR)
    if worktrees_dir is not None:
        roots.extend(sorted(child for child in worktrees_dir.iterdir() if child.is_dir() and not child.is_symlink()))
    return roots


def _read_lines(path: Path) -> list[str] | None:
    """Return the non-empty lines of *path*, or ``None`` on read failure.

    A record containing invalid UTF-8 is a read failure, not a crash: it is
    classified like any other unreadable file. ``UnicodeDecodeError`` is a
    ``ValueError``, so it would otherwise escape ``detect()`` as a traceback and
    abort the whole upgrade instead of yielding a ``MigrationResult``.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return _record_lines(text)


def _record_lines(text: str) -> list[str]:
    """Split trail text the way :func:`_read_lines` does, so both compare equal."""
    return [line for line in text.splitlines() if line.strip()]


class _FilePlan:
    """Disposition for one per-op file: skip, rewrite, or delete."""

    def __init__(
        self,
        action: str,  # "skip" | "rewrite" | "delete"
        new_lines: list[str] | None = None,
        warnings: list[str] | None = None,
        reason: str = "",
        source_lines: list[str] | None = None,
    ) -> None:
        self.action = action
        self.new_lines = new_lines or []
        self.warnings = warnings or []
        self.reason = reason
        self.source_lines = source_lines


def _is_v2_started(data: dict[str, Any]) -> bool:
    from specify_cli.invocation.record import OpStartedEvent

    # A historical v2 line may still parse because request_text is retained as
    # a transient compatibility field. It is not current/complete until the
    # migration rewrites that raw request out of the durable record.
    if "request_text" in data:
        return False
    try:
        OpStartedEvent.model_validate(data)
    except ValidationError:
        return False
    return True


def _is_v2_completed(data: dict[str, Any]) -> bool:
    from specify_cli.invocation.record import OpCompletedEvent

    try:
        OpCompletedEvent.model_validate(data)
    except ValidationError:
        return False
    return True


def _str_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _map_completed_line(
    data: dict[str, Any],
    file_name: str,
    invocation_id: str,
    started_at: str,
    warnings: list[str],
) -> str | None:
    """Map one legacy completed line to its v2 JSONL line (None = unsalvageable)."""
    from specify_cli.invocation.record import OpCompletedEvent

    completed_at = _str_or_empty(data.get("completed_at"))
    if not completed_at:
        completed_at = started_at
        warnings.append(f"{file_name}: completed_at missing; fell back to started_at")
    outcome = data.get("outcome")
    if outcome not in ("done", "failed", "abandoned"):
        outcome = "abandoned"
    try:
        event = OpCompletedEvent.model_validate(
            {
                "event": "completed",
                "invocation_id": _str_or_empty(data.get("invocation_id")) or invocation_id,
                "completed_at": completed_at,
                "outcome": outcome,
                "closed_by": "agent",
                "evidence_ref": data.get("evidence_ref"),
            }
        )
    except ValidationError:
        return None
    return event.to_jsonl_line()


def _started_provenance(started: dict[str, Any]) -> tuple[str, str | None]:
    """Return the v2 request provenance for a started row being rebuilt.

    A legacy row still carries the raw request, so provenance is derived from
    it. A row that was already redacted has no ``request_text``: digesting that
    absent field would replace its real correlation digest with the digest of
    the empty string, so the recorded digest is preserved instead.

    Key presence is what separates those two cases. A row whose ``request_text``
    is present but not a string has no verifiable string form to correlate, and
    this repair removes the field, so any digest recorded beside it would
    survive as provenance no later pass can check. Such a row keeps none.
    """
    from specify_cli.invocation.record import REDACTED_REQUEST_SUMMARY, request_provenance

    if "request_text" in started:
        request_text = started["request_text"]
        if isinstance(request_text, str):
            return cast(tuple[str, str | None], request_provenance(request_text))
        return REDACTED_REQUEST_SUMMARY, None
    existing = started.get("request_digest")
    return REDACTED_REQUEST_SUMMARY, existing if isinstance(existing, str) else None


def _validated_started(payload: dict[str, Any], file_name: str, warnings: list[str]) -> OpStartedEvent | None:
    """Validate a rebuilt started payload, dropping only a corrupt digest.

    A preserved digest is copied out of the very file being repaired, so a
    corrupt one must not cost the whole record: it is dropped with a warning
    rather than making the started event unrepresentable.
    """
    from specify_cli.invocation.record import OpStartedEvent

    try:
        return OpStartedEvent.model_validate(payload)
    except ValidationError:
        if payload.get("request_digest") is None:
            return None
        # Fall through: retry once without the digest carried over from the file.
    warnings.append(f"{file_name}: dropped an unparseable request_digest")
    try:
        return OpStartedEvent.model_validate({**payload, "request_digest": None})
    except ValidationError:
        return None


def _started_line(original: dict[str, Any], event: OpStartedEvent) -> str:
    """Serialize a repaired started row, keeping fields the schema ignores.

    A raw-v2 row (v2-shaped, but still carrying ``request_text``) is classified
    non-v2 and rebuilt here, so this pass is the only one that sees it. The
    trail is append-only and a writer may have recorded extension or audit keys
    beside the schema fields; ``to_jsonl_line()`` emits schema fields alone, so
    the repaired values are merged over the original row rather than replacing
    it. Schema fields the repaired event omits (a ``None`` default, or a digest
    :func:`_validated_started` rejected) are not carried back in from the row
    they were repaired out of.
    """
    from specify_cli.invocation.record import OpStartedEvent

    extras = {key: value for key, value in original.items() if key not in OpStartedEvent.model_fields}
    repaired: dict[str, Any] = json.loads(event.to_jsonl_line())
    return json.dumps({**extras, **repaired})


def _plan_file(path: Path) -> _FilePlan:
    """Classify one per-op file per the normative mapping table."""
    lines = _read_lines(path)
    if lines is None or not lines:
        return _FilePlan("delete", reason="unreadable or empty file")

    parsed: list[dict[str, Any]] = []
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return _FilePlan("delete", reason="unparseable JSON line")
        if not isinstance(data, dict):
            return _FilePlan("delete", reason="non-object JSONL line")
        parsed.append(data)

    started_idx = next((i for i, d in enumerate(parsed) if d.get("event") == "started"), None)
    if started_idx is None:
        return _FilePlan("delete", reason="missing started event")
    started = parsed[started_idx]

    invocation_id = _str_or_empty(started.get("invocation_id"))
    profile_id = _str_or_empty(started.get("profile_id"))
    if not invocation_id or not profile_id:
        return _FilePlan("delete", reason="started event lacks invocation_id/profile_id")

    # Already v2? Started has mode_of_work and every completed line has closed_by.
    completed_lines = [d for d in parsed if d.get("event") == "completed"]
    if _is_v2_started(started) and all(_is_v2_completed(d) for d in completed_lines):
        return _FilePlan("skip")

    warnings: list[str] = []
    started_at = _str_or_empty(started.get("started_at"))

    request_summary, request_digest = _started_provenance(started)
    started_payload: dict[str, Any] = {
        "event": "started",
        "invocation_id": invocation_id,
        "profile_id": profile_id,
        "action": _str_or_empty(started.get("action")) or "unrecorded",
        "request_summary": request_summary,
        "request_digest": request_digest,
        "actor": _str_or_empty(started.get("actor")) or "unrecorded",
        "mode_of_work": _str_or_empty(started.get("mode_of_work")) or "task_execution",
        "governance_context_hash": _str_or_empty(started.get("governance_context_hash")),
        "governance_context_available": bool(started.get("governance_context_available", True)),
        "router_confidence": started.get("router_confidence"),
        "started_at": started_at,
        "mission_id": started.get("mission_id"),
        "wp_id": started.get("wp_id"),
        "model_id": started.get("model_id"),
    }
    started_event = _validated_started(started_payload, path.name, warnings)
    if started_event is None:
        return _FilePlan("delete", reason="started event not representable as v2")

    new_lines: list[str] = []
    for i, (data, original) in enumerate(zip(parsed, lines, strict=True)):
        event = data.get("event")
        if event == "started" and i == started_idx:
            new_lines.append(_started_line(data, started_event))
            continue
        if event == "completed":
            if _is_v2_completed(data):
                new_lines.append(original)
                continue
            mapped = _map_completed_line(data, path.name, invocation_id, started_at, warnings)
            if mapped is None:
                return _FilePlan("delete", reason="completed event not representable as v2")
            new_lines.append(mapped)
            continue
        # link/glossary and any other non-lifecycle lines pass through byte-identical
        new_lines.append(original)

    return _FilePlan("rewrite", new_lines=new_lines, warnings=warnings, source_lines=lines)


def _carry_late_appends(source: TextIO, path: Path) -> bool:
    """Move appends off the replaced inode, reporting whether any were carried.

    The lines are carried **verbatim**: this migration's repair needs the whole
    record (the started event decides how completed lines map), so a late
    append is not repaired in place. Reporting it instead makes the caller
    replan, which puts the appended event through the normal schema path.
    """
    carried = False

    def _append(late: list[str]) -> str | None:
        nonlocal carried
        with path.open("a", encoding="utf-8") as installed:
            installed.write("".join(line + "\n" for line in late))
        carried = True
        return None

    return drain_late_appends(source, path, _append) is not None or carried


def _swap_and_carry(path: Path, tmp_path: Path, source_lines: list[str]) -> bool:
    """Install *tmp_path* over an unchanged *path*, keeping a racing append.

    Current writers share the record lock. Re-reading immediately before the
    swap is a compatibility guard for a stale writer that does not honor that
    lock, but comparison and replacement cannot be made one operation on POSIX,
    so an append can still land in between and would otherwise die on the inode
    ``os.replace`` unlinks. The comparison therefore reads through a handle that
    outlives the swap, and anything that arrived late is carried onto the
    installed file. Returns ``False`` when the snapshot moved or a late append
    was carried, so the caller replans rather than declaring the record settled.

    Where that inode cannot be drained (see ``DRAIN_SUPPORTED``), the swap waits
    until the compare handle is closed, because an open destination fails it.
    """
    try:
        with path.open("r", encoding="utf-8") as source:
            if _record_lines(source.read()) != source_lines:
                return False
            if DRAIN_SUPPORTED:
                os.replace(tmp_path, path)
                return not _carry_late_appends(source, path)
        os.replace(tmp_path, path)
        return True
    except UnicodeDecodeError:
        # A late append of invalid UTF-8 is a changed snapshot, classified by
        # the replan exactly as it would be had it landed before this pass.
        return False


def _atomic_rewrite(path: Path, lines: list[str], source_lines: list[str]) -> bool:
    """Replace a stable source snapshot, returning ``False`` when it changed."""
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
            handle.write("".join(line + "\n" for line in lines))
            handle.flush()
            os.fsync(handle.fileno())
        return _swap_and_carry(path, tmp_path, source_lines)
    finally:
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                tmp_path.unlink(missing_ok=True)


def _rewrite_with_retry(path: Path) -> _FilePlan | None:
    """Rewrite a schema record only after a stable snapshot, or fail closed."""
    for _ in range(_REWRITE_ATTEMPTS):
        plan = _plan_file(path)
        if plan.action != "rewrite":
            return plan
        if plan.source_lines is not None and _atomic_rewrite(path, plan.new_lines, plan.source_lines):
            return plan
    return None


def _raw_snapshot(path: Path) -> bytes | None:
    """Return the file's exact bytes, or ``None`` when they cannot be read."""
    try:
        return path.read_bytes()
    except OSError:
        return None


def _quarantine(path: Path) -> Path | None:
    """Move an unsalvageable record out of the eligible set, atomically.

    ``os.replace`` relinks the inode under a name ``_eligible_files`` cannot
    match, so the record stops being a rewrite/delete target in one step and a
    later writer opening the original path with ``open("x")`` gets a fresh file
    instead of racing this one. Returns ``None`` when the move fails, including
    when an earlier quarantined copy is still parked there: overwriting it would
    destroy the very bytes quarantine exists to preserve. The name keeps the
    record's own name intact so :func:`_quarantine_origin` can hand it back.
    """
    quarantined = path.with_name(f".{path.name}{_QUARANTINE_SUFFIX}")
    if quarantined.exists():
        return None
    try:
        os.replace(path, quarantined)
    except OSError:
        return None
    return quarantined


def _restore_held(quarantined: Path, path: Path) -> bool:
    """Put a quarantined record back while the caller holds its record lock.

    The existence check and the rename must run under that lock, because
    ``os.replace`` overwrites: a creation landing between them would be silently
    replaced by these older bytes and lose its audit event. The repair loop
    already holds the lock for the record it is repairing, so it restores
    through here; :func:`_restore` is the entry point for callers that do not.
    """
    if path.exists():
        return False
    try:
        os.replace(quarantined, path)
    except OSError:
        return False
    return True


def _restore(quarantined: Path, path: Path) -> bool:
    """Restore a quarantined record, taking the record lock around the move.

    This is the reclaim pass's entry point: it runs before the repair loop and
    holds no lock, so it takes the same one ``write_started`` takes to create a
    record. A lock it cannot take leaves the quarantine for the next run rather
    than restoring it unprotected.
    """
    try:
        with invocation_record_lock(path):
            return _restore_held(quarantined, path)
    except (OSError, Timeout):
        return False


def _is_record_quarantine(path: Path) -> bool:
    """Accept only the names :func:`_quarantine` gives an eligible record.

    The reclaim pass renames and deletes what it matches, so a hidden file that
    merely ends in the suffix must not be mistaken for an interrupted repair:
    reconstructing an origin from ``.notes.txt.unsalvageable``,
    ``.notes.jsonl.unsalvageable`` or ``.ops-index.jsonl.unsalvageable`` would
    hand a foreign file a record name, or unlink it as an invalid Op record. An
    Op record is named for its invocation ULID, so the reconstructed stem is
    validated against that contract rather than merely excluded by name.
    """
    from specify_cli.invocation.record import validate_invocation_id

    origin_name = path.name[1:].removesuffix(_QUARANTINE_SUFFIX)
    if not origin_name.endswith(_RECORD_SUFFIX):
        return False
    try:
        validate_invocation_id(origin_name[: -len(_RECORD_SUFFIX)])
    except ValueError:
        return False
    return True


def _quarantined_files(root: Path) -> list[Path]:
    """Quarantined records left behind by an interrupted repair."""
    ops_dir = contained_subdir(root, _OPS_DIR)
    if ops_dir is None:
        return []
    return sorted(p for p in ops_dir.glob(f".*{_QUARANTINE_SUFFIX}") if _is_record_quarantine(p) and not p.is_symlink())


def _quarantine_origin(quarantined: Path) -> Path:
    """The record path a quarantined file was moved away from."""
    return quarantined.with_name(quarantined.name[1:].removesuffix(_QUARANTINE_SUFFIX))


def _reclaim_quarantines(root: Path, dry_run: bool) -> tuple[list[str], list[str]]:
    """Bring quarantined records back into the repair path.

    A crash between the quarantine rename and the unlink, or a restore that lost
    the race to a freshly created record, leaves a file that ``_eligible_files``
    cannot match. Without this pass ``detect()`` would go quiet and every later
    run would report success while those bytes stay hidden, so a reclaim runs
    before the repair loop and hands each record back to it.
    """
    changes: list[str] = []
    errors: list[str] = []
    for quarantined in _quarantined_files(root):
        origin = _quarantine_origin(quarantined)
        if not origin.exists():
            if dry_run:
                changes.append(f"Would restore quarantined {origin.name} for repair")
            elif _restore(quarantined, origin):
                changes.append(f"Restored quarantined {origin.name} for repair")
            else:
                errors.append(f"Could not restore quarantined {quarantined.name}")
            continue
        # A record was recreated under that name, so these bytes cannot be
        # handed back. Discard them only while they remain unsalvageable.
        plan, outcome = _discard_with_retry(quarantined, dry_run)
        if outcome == "salvageable":
            errors.append(
                f"Quarantined {quarantined.name} is salvageable but {origin.name} was recreated; resolve it by hand"
            )
        elif plan is None:
            errors.append(f"Could not discard quarantined {quarantined.name}: concurrent writers kept changing it")
        elif dry_run:
            changes.append(f"Would discard stale quarantine {quarantined.name} ({plan.reason})")
        else:
            changes.append(f"Discarded stale quarantine {quarantined.name} ({plan.reason})")
    return changes, errors


def _discard_with_retry(quarantined: Path, dry_run: bool) -> tuple[_FilePlan | None, str]:
    """Unlink a stale quarantine only once its unsalvageable bytes prove stable.

    The pre-lock writer that made this record unsalvageable can still hold the
    inode, and the bytes cannot be handed back because the original name was
    recreated, so the discard runs the same protocol as
    :func:`_delete_with_retry`: content that moves between the plan and the
    unlink means the writer is still filling the record, and one that finished
    into a salvageable record is never unlinked at all.

    Returns the plan that was carried out plus the outcome (``salvageable``,
    ``discardable`` for a dry run, or ``discarded``), or ``None`` when the
    content never settled and the quarantine must wait for the next run.
    """
    for _ in range(_REWRITE_ATTEMPTS):
        before = _raw_snapshot(quarantined)
        plan = _plan_file(quarantined)
        if plan.action != "delete":
            return plan, "salvageable"
        if dry_run:
            return plan, "discardable"
        if _raw_snapshot(quarantined) != before:
            continue
        quarantined.unlink(missing_ok=True)
        return plan, "discarded"
    return None, "unstable"


def _delete_with_retry(path: Path) -> _FilePlan | None:
    """Delete a record only once its unsalvageable content proves stable.

    Deletion is irreversible, so it gets the same protocol as the rewrite path
    plus a quarantine step. A stale writer that predates the record lock can be
    part-way through creating the file, which classifies as unsalvageable, so:

    * re-reading after planning turns a mid-flight write into a replan rather
      than an unlink of the inode the writer is still filling;
    * the record is then renamed aside instead of unlinked, which is atomic and
      loses no bytes, and the *same inode* is re-planned under its quarantine
      name. A writer that completed the record inside that window is picked up
      there, and the file is moved back for a normal rewrite;
    * bytes that changed across the move mean a writer is still active, so the
      record is restored untouched and left for the next upgrade run.

    Only an append landing after the post-quarantine read can still be lost;
    POSIX has no compare-and-unlink, but by then the record is no longer
    reachable under its original name, so no new writer can attach to it.
    """
    for _ in range(_REWRITE_ATTEMPTS):
        before = _raw_snapshot(path)
        plan = _plan_file(path)
        if plan.action != "delete":
            return plan
        if _raw_snapshot(path) != before:
            continue
        quarantined = _quarantine(path)
        if quarantined is None:
            return None
        settled = _plan_file(quarantined)
        if settled.action != "delete":
            return settled if _restore_held(quarantined, path) else None
        if _raw_snapshot(quarantined) != before:
            _restore_held(quarantined, path)
            return None
        quarantined.unlink(missing_ok=True)
        return plan
    return None


def _settle_file(path: Path, plan: _FilePlan) -> tuple[_FilePlan, str] | None:
    """Carry out a planned repair, replanning until the record settles.

    Returns the plan that was actually executed plus what happened to the file
    (``deleted``, ``rewritten`` or ``skipped``), or ``None`` when concurrent
    writers never let the content settle and the file must be left for the next
    upgrade run.
    """
    if plan.action == "delete":
        settled = _delete_with_retry(path)
        if settled is None:
            return None
        if settled.action == "delete":
            return settled, "deleted"
        plan = settled
    if plan.action == "skip":
        return plan, "skipped"
    settled = _rewrite_with_retry(path)
    if settled is None:
        return None
    if settled.action == "rewrite":
        return settled, "rewritten"
    if settled.action == "skip":
        return settled, "skipped"
    return None


@MigrationRegistry.register
class OpRecordSchemaV2Migration(BaseMigration):
    """Rewrite legacy kitty-ops Op records to the v2 event schema."""

    migration_id = "3_3_0_op_record_schema_v2"
    description = "Migrate legacy kitty-ops/*.jsonl Op records to the v2 event schema (rewrite salvageable records, delete unsalvageable files)"
    target_version = "3.2.0rc41"
    runs_on_worktrees = True
    # A stuck lock leaves a record in the legacy schema, and apply() promises
    # the next upgrade run will retry it. Both flags are needed to keep that
    # promise: without the fatal flag the runner stamps a failed worktree at the
    # new version, and without reapply the behind-target migration is then
    # excluded from selection, so the retry never happens.
    worktree_failure_is_fatal = True
    reapply_when_detected = True

    def detect(self, project_path: Path) -> bool:
        """Return ``True`` iff a per-op file needs repair, or a quarantine waits.

        An interrupted repair leaves a quarantined record that
        ``_eligible_files`` cannot match, so it has to be reported here too or
        this repeatable migration would go quiet with those bytes still parked.
        """
        for root in _checkout_roots(project_path):
            if _quarantined_files(root):
                return True
            if any(_plan_file(path).action != "skip" for path in _eligible_files(root)):
                return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """The migration needs a readable ``kitty-ops/`` inside the checkout."""
        if not any(contained_subdir(root, _OPS_DIR) is not None for root in _checkout_roots(project_path)):
            return False, "kitty-ops/ directory does not exist"
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Rewrite or delete each eligible legacy file; skip v2 files."""
        changes: list[str] = []
        warnings: list[str] = []
        deleted: list[str] = []
        errors: list[str] = []

        # Reclaim first so a record parked by an interrupted run is repaired by
        # the loop below instead of waiting for another upgrade.
        try:
            reclaimed, reclaim_errors = _reclaim_quarantines(project_path, dry_run)
        except OSError as exc:
            reclaimed, reclaim_errors = [], [f"Could not reclaim quarantined records: {exc}"]
        changes.extend(reclaimed)
        errors.extend(reclaim_errors)

        for path in _eligible_files(project_path):
            try:
                # Building the lock can fail too (unwritable trail, rejected
                # lock path), so it belongs inside the handler.
                lock_context = invocation_record_lock(path) if not dry_run else contextlib.nullcontext()
                with lock_context:
                    plan = _plan_file(path)
                    if plan.action == "skip":
                        continue
                    if dry_run:
                        if plan.action == "delete":
                            changes.append(f"Would delete {path.name} ({plan.reason})")
                        else:
                            changes.append(f"Would rewrite {path.name} to v2 schema")
                        warnings.extend(plan.warnings)
                        continue
                    settled = _settle_file(path, plan)
                    if settled is None:
                        errors.append(f"Could not migrate {path.name}: concurrent writers kept changing the record")
                        continue
                    plan, outcome = settled
                    if outcome == "deleted":
                        deleted.append(path.name)
                        changes.append(f"Deleted unsalvageable {path.name} ({plan.reason})")
                    elif outcome == "rewritten":
                        changes.append(f"Rewrote {path.name} to v2 schema")
                    warnings.extend(plan.warnings)
            except Timeout:
                # A stuck holder must not escape as a traceback, but success
                # would record this still-legacy file as migrated and suppress
                # the retry that detect() is deliberately preserving.
                errors.append(f"Timed out waiting to migrate {path.name}; left for the next upgrade run")
            except OSError as exc:
                # A read-only kitty-ops/, a rejected lock path or a failed
                # rename must fail the migration, not abort the upgrade with a
                # traceback: neither the runner nor the CLI wraps apply(), so a
                # raise would bypass the JSON failure output and the fatal
                # worktree classification.
                errors.append(f"Could not migrate {path.name}: {exc}")

        if deleted:
            warnings.append(f"Deleted {len(deleted)} unsalvageable Op record file(s): " + ", ".join(deleted))

        return MigrationResult(success=not errors, changes_made=changes, errors=errors, warnings=warnings)
