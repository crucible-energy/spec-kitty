"""Read-only implementation preview proof for a planned WP and an existing registered code slot."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from specify_cli.coordination.owned import OwnedCoordinationContext, OwnedCoordinationError, owned_base, resolve_owned_coordination
from specify_cli.coordination.owned_admission_bindings import dependency_binding, dependency_proposals, immutable_commit, planning_binding
from specify_cli.core.dependency_graph import dependency_readiness_for_wp
from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.core.wps_manifest import load_wps_manifest
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.migration.owned_history import _safe_file
from specify_cli.migration.owned_history_sources import _blob, git_bytes, immutable_blob_reads, json_object
from specify_cli.status import read_event_stream_from_text

__all__ = ["preview_owned_implementation"]


def _lane(context: OwnedCoordinationContext, wp_id: str) -> ExecutionLane:
    raw = json_object(_safe_file(context.root, context.directory.relative_to(context.root) / "lanes.json").read_bytes())
    try:
        lanes = LanesManifest.from_dict(raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_MAPPING_REFUSED", f"Malformed declared lane mapping: {exc}") from exc
    roster = load_wps_manifest(context.directory)
    ids = [wp for lane in lanes.lanes for wp in lane.wp_ids]
    lane_ids = [lane.lane_id for lane in lanes.lanes]
    if (
        lanes.version != 1
        or lanes.mission_id != context.mission_id
        or lanes.mission_slug != context.slug
        or lanes.mission_branch != context.coord_branch
        or lanes.target_branch != context.target_branch
        or roster is None
        or len(ids) != len(set(ids))
        or set(ids) != {wp.id for wp in roster.work_packages}
        or len(lane_ids) != len(set(lane_ids))
        or any(not isinstance(name, str) or not re.fullmatch(r"lane-[a-z]", name) for name in lane_ids)
    ):
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_MAPPING_REFUSED", "Declared code lanes must uniquely cover the existing dossier/WP roster")
    selected = lanes.lane_for_wp(wp_id)
    if selected is None:
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_MAPPING_REFUSED", "Desired WP has no declared code lane")
    return selected


def _slot(
    context: OwnedCoordinationContext, checkout: Path, pin: str, lane: ExecutionLane, planning: dict[str, dict[str, str]]
) -> dict[str, Any]:
    root, directory, _, head, branch, _ = owned_base(context.repository_root, checkout, context.mission_id)
    if root == context.root or head != pin or branch != f"{context.coord_branch}-{lane.lane_id}":
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_SLOT_REFUSED", "Require the existing declared code lane checkout at the exact requested HEAD")
    flags = git_bytes(root, "ls-files", "-v", "-z").decode().rstrip("\0").split("\0")
    if any(entry and (entry[0].islower() or entry[0] == "S") for entry in flags):
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_HIDDEN_REFUSED", "Code slot has assume-unchanged or skip-worktree entries")
    roster = load_wps_manifest(directory)
    if roster is None:
        raise OwnedCoordinationError("OWNED_IMPLEMENTATION_ROSTER_REFUSED", "Code slot requires the authored WP roster")
    names = [*planning, "status.events.jsonl", "status.json"]
    for name in names:
        path = f"kitty-specs/{context.slug}/{name}"
        actual = _safe_file(root, Path(path)).read_bytes()
        if actual != _blob(context.root, pin, path)[0]:
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_HIDDEN_REFUSED", f"Code slot bytes differ from requested HEAD: {name}")
    return {"root": str(root), "commit": pin, "branch": branch, "tree": git_bytes(root, "rev-parse", f"{pin}^{{tree}}").decode().strip()}


def preview_owned_implementation(
    repository: Path, checkout: Path, handle: str, wp_id: str, code_checkout: Path, code_commit: str, dependency_pins: list[str]
) -> dict[str, Any]:
    """Compute bounded proof only; no allocation, locks, writes or runtime issuance."""
    with immutable_blob_reads():
        if not isinstance(wp_id, str) or not re.fullmatch(r"WP[0-9]{2,}", wp_id):
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_INPUT_REFUSED", "Desired WP requires an existing WP## identity")
        assert_safe_path_segment(handle)
        pin = immutable_commit(code_commit)
        proposals = dependency_proposals(dependency_pins)
        context, snapshot = resolve_owned_coordination(repository, checkout, handle)
        manifest = load_wps_manifest(context.directory)
        selected = next((wp for wp in manifest.work_packages if wp.id == wp_id), None) if manifest else None
        if selected is None:
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_WP_REFUSED", "Desired WP is absent from the existing roster")
        if snapshot.work_packages[wp_id]["lane"] != "planned":
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_LANE_REFUSED", "Preview requires the desired WP to remain planned")
        lanes = {wp: state["lane"] for wp, state in snapshot.work_packages.items()}
        ready = dependency_readiness_for_wp(wp_id, selected.dependencies, lanes)
        if not ready.satisfied:
            raise OwnedCoordinationError("OWNED_DEPENDENCIES_NOT_READY", f"Unsatisfied canonical dependencies: {list(ready.unsatisfied)}")
        if set(proposals) != set(selected.dependencies):
            raise OwnedCoordinationError("OWNED_DEPENDENCY_PINS_REFUSED", f"Require exactly the declared dependency proposals: {selected.dependencies}")
        lane = _lane(context, wp_id)
        code_planning = planning_binding(context, pin)
        slot = _slot(context, code_checkout, pin, lane, code_planning)
        stream = read_event_stream_from_text(context.directory, (context.directory / "status.events.jsonl").read_text(encoding="utf-8"))
        dependencies = {wp: dependency_binding(context, stream, wp, proposals[wp]) for wp in selected.dependencies}
        planning = planning_binding(context, context.planning_ancestor)
        planning_binding(context, context.coord_commit)
        current, _ = resolve_owned_coordination(repository, checkout, handle)
        if current != context or _slot(context, code_checkout, pin, lane, code_planning) != slot:
            raise OwnedCoordinationError("OWNED_IMPLEMENTATION_CONTEXT_CHANGED", "Authority or code slot changed during the read-only proof")
        return {
            "kind": "owned_implementation_preview",
            "admitted": False,
            "proof_ready": True,
            "dry_run": True,
            "applied": False,
            "write": False,
            "allocated": False,
            "runtime_advanced": False,
            "mission_id": context.mission_id,
            "mission_slug": context.slug,
            "wp_id": wp_id,
            "lane_id": lane.lane_id,
            "roots": {**context.roots(), "code_root": slot["root"]},
            "authority_commit": context.head,
            "planning_ref": context.target_branch,
            "status_ref": context.coord_branch,
            "target_commit": context.target_commit,
            "coord_commit": context.coord_commit,
            "anchor": context.anchor,
            "common_ancestor": context.common_ancestor,
            "planning_ancestor": context.planning_ancestor,
            "planning": planning,
            "slot": slot,
            "dependencies": dependencies,
            "dependency_readiness": {"satisfied": ready.satisfied, "unsatisfied": list(ready.unsatisfied)},
            "counts": dict(zip(("rows", "transitions", "annotations", "non_lane"), context.planning_counts, strict=True)),
            "profile": None,
            "tool": None,
            "model": None,
            "base_qualified": False,
            "reason": "read_only_preview",
        }
