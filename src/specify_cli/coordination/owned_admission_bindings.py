"""Immutable planning and recorded review bindings for owned admission queries."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

from specify_cli.coordination.owned import PLANNING_FILES, OwnedCoordinationContext, OwnedCoordinationError
from specify_cli.coordination.owned_status import OwnedReviewRequest, implementation_actors, validate_owned_review_code
from specify_cli.core.wps_manifest import load_wps_manifest
from specify_cli.migration.owned_history_sources import _blob, git_bytes
from specify_cli.migration.owned_history import _safe_file
from specify_cli.status import EventStream, Lane, actor_identity_str, read_authored_wp_frontmatter

__all__ = ["dependency_proposals", "immutable_commit", "planning_binding", "dependency_binding"]
MAX_PROOF_FILES = 256
_SHA = re.compile(r"[0-9a-f]{40}")
_WP = re.compile(r"WP[0-9]{2,}")


def immutable_commit(value: str) -> str:
    """Accept full immutable SHA syntax only; Git existence/type is checked separately."""
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_INPUT_REFUSED", "Require a full lowercase immutable commit SHA")
    return value


def dependency_proposals(values: list[str]) -> dict[str, str]:
    """Decode explicit proposals without duplicate ambiguity or branch-tip resolution."""
    proposals: dict[str, str] = {}
    for value in values:
        wp, separator, pin = value.partition("=")
        if not separator or not _WP.fullmatch(wp):
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_INPUT_REFUSED", "Dependency proposal requires WP##=full-commit-SHA")
        pin = immutable_commit(pin)
        if wp in proposals and proposals[wp] != pin:
            raise OwnedCoordinationError("OWNED_DEPENDENCY_PINS_REFUSED", f"Conflicting dependency proposals: {wp}")
        proposals[wp] = pin
    return proposals


def planning_binding(context: OwnedCoordinationContext, pin: str) -> dict[str, dict[str, str]]:
    """Require the original pinned planning bundle and every authored WP prompt."""
    immutable_commit(pin)
    if git_bytes(context.root, "cat-file", "-t", pin).strip() != b"commit":
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_PIN_REFUSED", "Proposed pin is not a commit object")
    manifest = load_wps_manifest(context.directory)
    if manifest is None or len(manifest.work_packages) > MAX_PROOF_FILES:
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_ROSTER_REFUSED", "Require a bounded existing WP roster")
    for wp in manifest.work_packages:
        if not wp.prompt_file:
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_PLANNING_REFUSED", f"Missing authored WP prompt: {wp.id}")
        prompt = _safe_file(context.root, context.directory.relative_to(context.root) / wp.prompt_file)
        authored, _ = read_authored_wp_frontmatter(prompt)
        if authored.work_package_id != wp.id:
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_PLANNING_REFUSED", f"Authored WP prompt identity differs: {wp.id}")
    paths = [*PLANNING_FILES, *(wp.prompt_file for wp in manifest.work_packages)]
    proof = {}
    for name in paths:
        if not name or Path(name).is_absolute() or ".." in Path(name).parts:
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_PLANNING_REFUSED", "Unsafe or missing authored planning path")
        path = f"kitty-specs/{context.slug}/{name}"
        expected, _ = _blob(context.root, context.target_commit, path)
        actual, blob = _blob(context.root, pin, path)
        if actual != expected:
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_PLANNING_REFUSED", f"Immutable planning differs at {pin}:{path}")
        proof[name] = blob
    return proof


def _owned_blobs(context: OwnedCoordinationContext, wp_id: str, pin: str) -> dict[str, dict[str, str]]:
    validate_owned_review_code(context, wp_id, pin)
    manifest = load_wps_manifest(context.directory)
    selected = next((wp for wp in manifest.work_packages if wp.id == wp_id), None) if manifest else None
    if selected is None:
        raise OwnedCoordinationError("OWNED_REVIEW_CODE_REFUSED", f"Missing authored ownership: {wp_id}")
    files = git_bytes(context.root, "ls-tree", "-r", "-z", "--name-only", pin).decode().rstrip("\0").split("\0")
    names = sorted({name for pattern in selected.owned_files for name in files if fnmatch.fnmatchcase(name, pattern)})
    if len(names) > MAX_PROOF_FILES:
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_PROOF_LIMIT", f"Owned code proof exceeds {MAX_PROOF_FILES} files: {wp_id}")
    return {name: _blob(context.root, pin, name)[1] for name in names}


def dependency_binding(context: OwnedCoordinationContext, stream: EventStream, wp_id: str, pin: str) -> dict[str, Any]:
    """Require the latest actual approval's exact WP/dossier/pin/request binding.

    A proposed pin or prose review reference supplies no machine binding. Recorded
    facts are checked, not reviewer authentication or a fresh review performance.
    """
    event = next((event for event in reversed(stream.transitions) if event.wp_id == wp_id and event.to_lane == Lane.APPROVED), None)
    metadata = (event.policy_metadata or {}) if event else {}
    if event is None or "reviewed_commit" not in metadata:
        raise OwnedCoordinationError(
            "OWNED_DEPENDENCY_BINDING_MISSING",
            f"{wp_id}: missing recorded approval reviewed_commit binding for proposed {pin}; supplemental qualification is required",
        )
    review = event.review_result
    if review is None:
        raise OwnedCoordinationError("OWNED_DEPENDENCY_BINDING_REFUSED", f"{wp_id}: recorded approval lacks canonical review_result")
    request = OwnedReviewRequest(wp_id, review.reviewer, "approved", review.reference, pin)
    if (
        metadata.get("reviewed_commit") != pin
        or metadata.get("owned_review_request") != request.key(context.mission_id)
        or metadata.get("fresh_review") is not True
        or event.force
        or event.from_lane != Lane.IN_REVIEW
        or review.verdict != "approved"
        or not review.reference.strip()
        or not review.reviewer.strip()
        or actor_identity_str(event.actor) != review.reviewer
        or event.review_ref != review.reference
        or review.reviewer in implementation_actors(stream, wp_id)
        or event.evidence is None
        or event.evidence.review.to_dict() != review.to_dict()
    ):
        raise OwnedCoordinationError("OWNED_DEPENDENCY_BINDING_REFUSED", f"{wp_id}: approval does not bind this exact independent WP/pin/request")
    planning_binding(context, pin)
    return {"commit": pin, "approval_event_id": event.event_id, "review_result": review.to_dict(), "owned_blobs": _owned_blobs(context, wp_id, pin)}
