"""Explicit owned submission/claim, using the canonical FSM and creator-owned IO."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from specify_cli.coordination.owned import OwnedCoordinationContext, OwnedCoordinationError, resolve_owned_coordination
from specify_cli.coordination.owned_handoff_gate import submission_gate
from specify_cli.coordination.owned_status import implementation_actors, validate_owned_review_code
from specify_cli.migration.owned_history import _replace_batch
from specify_cli.migration.owned_history_io import BoundHistoryDirectory
from specify_cli.migration.owned_history_sources import _blob, git_bytes, sha256
from specify_cli.status.emit import build_status_event, _infer_subtasks_complete, _infer_implementation_evidence_from_event_stream
from specify_cli.status.locking import feature_status_lock
from specify_cli.status.models import EventStream, GuardContext, StatusEvent, StatusSnapshot
from specify_cli.status.reducer import materialize_to_json, reduce
from specify_cli.status.store import read_event_stream_from_text
from specify_cli.status.transitions import validate_transition

__all__ = ["OwnedHandoffRequest", "record_owned_handoff"]


@dataclass(frozen=True)
class OwnedHandoffRequest:
    """Actual caller identities and immutable evidence; never inferred role bindings."""

    kind: str
    wp_id: str
    implementer: str
    code_commit: str
    reference: str
    reviewer: str | None = None
    scope_proof: str | None = None

    def key(self, mission_id: str) -> str:
        """Stable exact-request idempotency independent of generated event IDs."""
        return sha256(json.dumps({"mission_id": mission_id, **asdict(self)}, sort_keys=True).encode())


def _inputs(context: OwnedCoordinationContext, request: OwnedHandoffRequest) -> None:
    """Bind caller facts to a real local code object and its origin commit reference."""
    identities = [request.implementer] + ([request.reviewer] if request.kind == "claim" else [])
    if request.kind not in ("submit", "claim") or any(not value or not value.strip() or value.strip().lower() in ("unknown", "none") for value in identities):
        raise OwnedCoordinationError("OWNED_HANDOFF_ACTOR_REFUSED", "Actual known implementer/reviewer identities are required")
    url = urlsplit(request.reference)
    origin = git_bytes(context.root, "config", "--get", "remote.origin.url").decode().strip()
    repo = origin.removeprefix("git@github.com:").removeprefix("https://github.com/").removesuffix(".git")
    if url.scheme != "https" or url.netloc != "github.com" or url.path != f"/{repo}/commit/{request.code_commit}":
        raise OwnedCoordinationError("OWNED_HANDOFF_REFERENCE_REFUSED", "Reference must name the real code commit on this repository's public GitHub origin")


def _claim_guard(stream: EventStream, request: OwnedHandoffRequest, state: dict[str, Any]) -> None:
    """Require the current submission and independent actor without lease reassignment."""
    if request.reviewer is None:
        raise OwnedCoordinationError("OWNED_HANDOFF_ACTOR_REFUSED", "Actual reviewer identity is required")
    submitted = next((event for event in reversed(stream.transitions) if event.wp_id == request.wp_id), None)
    if submitted is None:
        raise OwnedCoordinationError("OWNED_HANDOFF_SUBMISSION_REFUSED", "No current owned submission exists")
    metadata = submitted.policy_metadata or {}
    if metadata.get("owned_handoff_kind") != "submit" or metadata.get("code_commit") != request.code_commit or metadata.get("implementer") != request.implementer:
        raise OwnedCoordinationError("OWNED_HANDOFF_SUBMISSION_REFUSED", "Claim must match the current owned submission's implementer and code pin")
    if request.reviewer.strip() in implementation_actors(stream, request.wp_id) or request.reviewer.strip() == request.implementer.strip():
        raise OwnedCoordinationError("OWNED_SELF_REVIEW_REFUSED", "Implementer cannot claim independent review")
    if submitted.event_id != state["last_event_id"]:
        raise OwnedCoordinationError("OWNED_HANDOFF_SUBMISSION_REFUSED", "Submitted review authority changed")


def _outputs(context: OwnedCoordinationContext, snapshot: StatusSnapshot, text: str, event: StatusEvent) -> dict[Path, bytes]:
    """Append one fresh canonical event and derive its snapshot without file writes."""
    ids = {json.loads(line)["event_id"] for line in text.splitlines() if line.strip()}
    if event.event_id in ids:
        raise OwnedCoordinationError("OWNED_HANDOFF_EVENT_CONFLICT", "Generated event ID duplicates retained authority")
    updated = text + ("" if text.endswith("\n") else "\n") + json.dumps(event.to_dict(), sort_keys=True) + "\n"
    stream = read_event_stream_from_text(context.directory, updated)
    projected = reduce(stream.transitions, stream.annotations)
    projected.mission_type, projected.mission_number = snapshot.mission_type, snapshot.mission_number
    return {context.directory / "status.events.jsonl": updated.encode(), context.directory / "status.json": materialize_to_json(projected).encode()}


def _plan(
    repository: Path, checkout: Path, handle: str, request: OwnedHandoffRequest, *, gate: dict[str, Any] | None = None, code_checkout: Path | None = None
) -> tuple[dict[Path, bytes], dict[str, Any]]:
    """Produce a guarded pure preview or exact recorded-request no-op."""
    context, snapshot = resolve_owned_coordination(repository, checkout, handle)
    _inputs(context, request)
    state = snapshot.work_packages.get(request.wp_id)
    if state is None:
        raise OwnedCoordinationError("OWNED_HANDOFF_WP_REFUSED", "WP requires existing canonical history")
    validate_owned_review_code(context, request.wp_id, request.code_commit)
    text = (context.directory / "status.events.jsonl").read_text(encoding="utf-8")
    stream = read_event_stream_from_text(context.directory, text)
    matches = [event for event in stream.transitions if (event.policy_metadata or {}).get("owned_handoff_request") == request.key(context.mission_id)]
    if len(matches) > 1:
        raise OwnedCoordinationError("OWNED_HANDOFF_EVENT_CONFLICT", "Multiple records claim the same handoff request")
    if matches:
        event = matches[0]
        return {}, {
            "changed": False,
            "event_id": event.event_id,
            "from_lane": str(event.from_lane),
            "to_lane": str(event.to_lane),
            "current_lane": state["lane"],
            "status_ref": context.coord_branch,
            "code_commit": request.code_commit,
            "pre_review_gate": (event.policy_metadata or {}).get("pre_review_gate"),
            "aggregate_approval": False,
            "allocated": False,
            "runtime_advanced": False,
        }
    from_lane, to_lane = ("in_progress", "for_review") if request.kind == "submit" else ("for_review", "in_review")
    if state["lane"] != from_lane:
        raise OwnedCoordinationError("OWNED_HANDOFF_LANE_REFUSED", f"{request.kind} requires {from_lane}; current phase is {state['lane']}")
    actor = request.implementer
    metadata: dict[str, Any] = {
        "owned_handoff_request": request.key(context.mission_id),
        "owned_handoff_kind": request.kind,
        "code_commit": request.code_commit,
        "implementer": request.implementer,
        "reference": request.reference,
    }
    complete = _infer_subtasks_complete(context.directory, request.wp_id, event_stream=stream)
    evidence = _infer_implementation_evidence_from_event_stream(stream, request.wp_id)
    if request.kind == "claim":
        _claim_guard(stream, request, state)
        assert request.reviewer is not None
        actor = request.reviewer
    else:
        metadata["pre_review_gate"] = gate or submission_gate(context, request.wp_id, request.code_commit, code_checkout, run=False)
        if request.scope_proof:
            _, proof = _blob(context.root, request.code_commit, request.scope_proof)
            metadata["scope_proof"] = {"path": request.scope_proof, **proof, "interpretation": "opaque pinned operator evidence; not aggregate approval"}
    ok, reason = validate_transition(
        from_lane, to_lane, GuardContext(actor=actor, force=False, subtasks_complete=complete, implementation_evidence_present=evidence)
    )
    if not ok:
        raise OwnedCoordinationError("OWNED_HANDOFF_TRANSITION_REFUSED", reason or "Canonical FSM refused handoff")
    event = build_status_event(
        mission_slug=context.slug,
        mission_id=context.mission_id,
        wp_id=request.wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        actor=actor,
        force=False,
        execution_mode="worktree",
        reason="owned independent review handoff",
        review_ref=request.reference,
        policy_metadata=metadata,
    )
    return _outputs(context, snapshot, text, event), {
        "changed": True,
        "event_id": event.event_id,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "status_ref": context.coord_branch,
        "code_commit": request.code_commit,
        "pre_review_gate": metadata.get("pre_review_gate"),
        "aggregate_approval": False,
        "allocated": False,
        "runtime_advanced": False,
    }


def record_owned_handoff(
    repository: Path, checkout: Path, handle: str, request: OwnedHandoffRequest, *, apply: bool = False, code_checkout: Path | None = None
) -> dict[str, Any]:
    """Preview or persist only a guarded submission/claim; caller commits real outputs."""
    context, _ = resolve_owned_coordination(repository, checkout, handle)
    outputs, report = _plan(repository, checkout, handle, request, code_checkout=code_checkout)
    if apply and report["changed"]:
        with feature_status_lock(context.root, context.slug, timeout=10):
            bound = BoundHistoryDirectory(context.root, context.directory)
            try:
                originals = bound.capture(("meta.json", "status.events.jsonl", "status.json"))
                current, _ = resolve_owned_coordination(repository, checkout, handle)
                if current != context:
                    raise OwnedCoordinationError("OWNED_HANDOFF_CONTEXT_CHANGED", "Owned handoff authority changed under the lock")
                gate = submission_gate(context, request.wp_id, request.code_commit, code_checkout, run=True) if request.kind == "submit" else None
                outputs, report = _plan(repository, checkout, handle, request, gate=gate, code_checkout=code_checkout)
                bound.verify(originals)
                if report["changed"]:
                    _replace_batch(outputs, bound, originals, context.slug)
            finally:
                bound.close()
    applied = bool(apply and report["changed"])
    return {**report, "dry_run": not apply, "applied": applied, "commit_required": applied}
