"""Scoped projection refresh and real reviewer disposition in owned coordination."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
import fnmatch

from specify_cli.coordination.owned import OwnedCoordinationError, resolve_owned_coordination
from specify_cli.migration.owned_history import _replace_batch
from specify_cli.migration.owned_history_io import BoundHistoryDirectory
from specify_cli.migration.owned_history_sources import _blob, git_bytes, load_source, sha256
from specify_cli.core.wps_manifest import load_wps_manifest
from specify_cli.status.emit import build_status_event
from specify_cli.status.locking import feature_status_lock
from specify_cli.status.models import DoneEvidence, GuardContext, Lane, ReviewResult, StatusSnapshot, actor_identity_str
from specify_cli.status.reducer import materialize_snapshot, materialize_to_json, reduce
from specify_cli.status.store import read_event_stream_from_text
from specify_cli.status.transitions import validate_transition

__all__ = ["OwnedReviewRequest", "record_owned_review", "refresh_owned_projection"]


@dataclass(frozen=True)
class OwnedReviewRequest:
    """Operator-supplied real review facts; this record does not authenticate a reviewer."""

    wp_id: str
    reviewer: str
    verdict: str
    reference: str
    reviewed_commit: str

    def key(self, mission_id: str) -> str:
        """Bind an idempotent recorded-review request to the mission and all supplied facts."""
        return cast(str, sha256(json.dumps({"mission_id": mission_id, **self.__dict__}, sort_keys=True).encode()))


def _review_plan(repository: Path, checkout: Path, handle: str, request: OwnedReviewRequest) -> tuple[dict[Path, bytes], dict[str, Any]]:
    """Build, without persisting, a canonical disposition or exact-request no-op."""
    context, snapshot = resolve_owned_coordination(repository, checkout, handle)
    if not request.reviewer.strip() or not request.reference.strip() or request.verdict not in ("approved", "changes_requested"):
        raise OwnedCoordinationError("OWNED_REVIEW_INPUT_REFUSED", "Real reviewer, reference and supported verdict are required")
    state = snapshot.work_packages.get(request.wp_id)
    if state is None:
        raise OwnedCoordinationError("OWNED_REVIEW_WP_REFUSED", "Selected WP has no canonical history")
    log_path = context.directory / "status.events.jsonl"
    text = log_path.read_text(encoding="utf-8")
    stream = read_event_stream_from_text(context.directory, text)
    key = request.key(context.mission_id)
    for event in stream.transitions:
        if (event.policy_metadata or {}).get("owned_review_request") == key:
            return {}, {
                "changed": False,
                "event_id": event.event_id,
                "from_lane": str(event.from_lane),
                "to_lane": str(event.to_lane),
                "status_ref": context.coord_branch,
            }
    implementers = {
        actor_identity_str(event.actor).strip()
        for event in stream.transitions
        if event.wp_id == request.wp_id and event.from_lane in (Lane.PLANNED, Lane.CLAIMED) and event.to_lane in (Lane.CLAIMED, Lane.IN_PROGRESS)
    }
    if request.reviewer.strip() in implementers:
        raise OwnedCoordinationError("OWNED_SELF_REVIEW_REFUSED", "Implementer self-review is refused")
    if state.get("lane") != "in_review":
        raise OwnedCoordinationError("OWNED_REVIEW_LANE_REFUSED", "Real disposition requires the existing in_review lane; no claim or force is synthesized")
    # A code pin must be a real immutable commit in this repository carrying the
    # same dossier identity. Source snapshots/provenance are verified, not inferred.
    meta = json.loads((context.directory / "meta.json").read_text(encoding="utf-8"))
    _, reviewed = load_source(context.root, context.directory, request.reviewed_commit, meta)
    manifest = load_wps_manifest(context.directory)
    selected = next((wp for wp in manifest.work_packages if wp.id == request.wp_id), None) if manifest is not None else None
    if selected is None or not selected.owned_files:
        raise OwnedCoordinationError("OWNED_REVIEW_CODE_REFUSED", "Selected WP requires its authored code ownership declaration")
    files = cast(bytes, git_bytes(context.root, "ls-tree", "-r", "--name-only", request.reviewed_commit)).decode().splitlines()
    for pattern in selected.owned_files:
        matches = [name for name in files if fnmatch.fnmatchcase(name, pattern)]
        if not matches or pattern.startswith("/") or ".." in Path(pattern).parts:
            raise OwnedCoordinationError("OWNED_REVIEW_CODE_REFUSED", f"Reviewed commit does not carry safe WP-owned code: {pattern}")
        for name in matches:
            _blob(context.root, request.reviewed_commit, name)  # Refuse symlink blobs too.
    result = ReviewResult(request.reviewer, request.verdict, request.reference)
    evidence = DoneEvidence.from_dict({"review": result.to_dict()})
    to_lane = "approved" if request.verdict == "approved" else "in_progress"
    guard = GuardContext(actor=request.reviewer, review_ref=request.reference, review_result=result, evidence=evidence, force=False)
    ok, reason = validate_transition("in_review", to_lane, guard)
    if not ok:
        raise OwnedCoordinationError("OWNED_REVIEW_TRANSITION_REFUSED", reason or "Canonical FSM refused review disposition")
    event = build_status_event(
        mission_slug=context.slug,
        mission_id=context.mission_id,
        wp_id=request.wp_id,
        from_lane="in_review",
        to_lane=to_lane,
        actor=request.reviewer,
        force=False,
        execution_mode="worktree",
        reason="independent reviewer disposition",
        review_ref=request.reference,
        review_result=result,
        evidence=evidence,
        policy_metadata={"owned_review_request": key, "reviewed_commit": reviewed["commit"], "fresh_review": True},
    )
    updated_text = text + ("" if not text or text.endswith("\n") else "\n") + json.dumps(event.to_dict(), sort_keys=True) + "\n"
    updated_stream = read_event_stream_from_text(context.directory, updated_text)
    updated = reduce(updated_stream.transitions, updated_stream.annotations)
    updated.mission_type, updated.mission_number = snapshot.mission_type, snapshot.mission_number
    outputs = {log_path: updated_text.encode(), context.directory / "status.json": materialize_to_json(updated).encode()}
    return outputs, {
        "changed": True,
        "event_id": event.event_id,
        "from_lane": "in_review",
        "to_lane": to_lane,
        "review_result": result.to_dict(),
        "reviewed_commit": request.reviewed_commit,
        "status_ref": context.coord_branch,
        "planning_ref": context.target_branch,
        "runtime_advanced": False,
        "allocated": False,
    }


def record_owned_review(repository: Path, checkout: Path, handle: str, request: OwnedReviewRequest, *, apply: bool = False) -> dict[str, Any]:
    """Preview or record supplied independent-review evidence on owned coordination.

    Apply revalidates authority under the canonical lock and installs the log and
    snapshot through creator-owned IO. It performs no review, commit or runtime
    advancement; callers must commit/push real applied dispositions themselves.
    """
    context, _ = resolve_owned_coordination(repository, checkout, handle)
    outputs, report = _review_plan(repository, checkout, handle, request)
    if apply and report["changed"]:
        with feature_status_lock(context.root, context.slug, timeout=10):
            bound = BoundHistoryDirectory(context.root, context.directory)
            try:
                originals = bound.capture(("meta.json", "status.events.jsonl", "status.json"))
                current, _ = resolve_owned_coordination(repository, checkout, handle)
                if current != context:
                    raise OwnedCoordinationError("OWNED_REVIEW_CONTEXT_CHANGED", "Review authority changed under the canonical lock")
                # Re-plan current state, but the actual event is issued once in
                # this locked call. Preview IDs never become fresh approvals.
                outputs, report = _review_plan(repository, checkout, handle, request)
                bound.verify(originals)
                if report["changed"]:
                    _replace_batch(outputs, bound, originals, context.slug)
            finally:
                bound.close()
    applied = bool(apply and report["changed"])
    return {**report, "dry_run": not apply, "applied": applied, "commit_required": applied}


def refresh_owned_projection(repository: Path, checkout: Path, handle: str, *, apply: bool = False) -> dict[str, Any]:
    """Explicitly preview or refresh the derived snapshot without changing events.

    Apply requires the same clean committed owned coordination authority as query
    and review, rechecked under the canonical lock; the operator commits its output.
    """
    context, snapshot = resolve_owned_coordination(repository, checkout, handle)
    raw = materialize_to_json(snapshot).encode()
    path = context.directory / "status.json"
    changed = path.read_bytes() != raw
    if apply and changed:
        with feature_status_lock(context.root, context.slug, timeout=10):
            bound = BoundHistoryDirectory(context.root, context.directory)
            try:
                originals = bound.capture(("meta.json", "status.events.jsonl", "status.json"))
                current, _ = resolve_owned_coordination(repository, checkout, handle)
                if current != context:
                    raise OwnedCoordinationError("OWNED_PROJECTION_CONTEXT_CHANGED", "Projection authority changed under the canonical lock")
                projected: StatusSnapshot = materialize_snapshot(current.directory)
                projected_raw = materialize_to_json(projected).encode()
                bound.verify(originals)
                changed = originals["status.json"].data != projected_raw
                snapshot = projected
                if changed:
                    _replace_batch({path: projected_raw}, bound, originals, context.slug)
            finally:
                bound.close()
    return {
        "changed": changed,
        "dry_run": not apply,
        "applied": bool(apply and changed),
        "status_ref": context.coord_branch,
        "event_log_unchanged": True,
        "snapshot": snapshot.to_dict(),
        "commit_required": bool(apply and changed),
    }
