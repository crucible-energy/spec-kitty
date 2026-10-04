"""Explicit coordinated authority; repository identity and owned partitions stay separate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

from specify_cli.context.mission_resolver import AmbiguousHandleError, MissionNotFoundError, resolve_mission
from specify_cli.core.dependency_graph import build_dependency_graph, dependency_readiness_for_wp, detect_cycles
from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.core.wps_manifest import load_wps_manifest
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.migration.owned_history import _dirty_paths, _ownership, _safe_file
from specify_cli.migration.owned_history_io import BoundHistoryDirectory
from specify_cli.migration.owned_history_sources import _blob, git_bytes, json_object, load_source, validate_meta
from specify_cli.status.models import StatusSnapshot
from specify_cli.status.reducer import materialize_snapshot

__all__ = [
    "OwnedCoordinationError",
    "OwnedCoordinationContext",
    "owned_base",
    "validate_pins",
    "validate_anchor_shape",
    "resolve_owned_coordination",
    "query_owned_coordination",
]

PLANNING_FILES = ("meta.json", "spec.md", "plan.md", "tasks.md", "wps.yaml", "lanes.json")
AUTHORITY_MARKER = "Spec-Kitty-Owned-Coordination: v1"


class OwnedCoordinationError(ValueError):
    """Stable refusal with the actual checked authority paths."""

    def __init__(self, code: str, message: str, paths: tuple[Path, ...] = ()) -> None:
        super().__init__(message)
        self.code = code
        self.paths = paths

    def to_dict(self) -> dict[str, Any]:
        """Return the stable refusal code, actual checked paths and applied=False."""
        return {"code": self.code, "error": str(self), "checked_paths": [str(path) for path in self.paths], "applied": False}


def _git(root: Path, *args: str) -> str:
    return git_bytes(root, *args).decode("utf-8").strip()


def branch_oid(root: Path, branch: str) -> str | None:
    """Read an exact local branch oid without resolving a prefix or writing refs."""
    refs = _git(root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/")
    return dict(line.split(" ", 1) for line in refs.splitlines()).get(f"refs/heads/{branch}")


def _backlink(root: Path) -> None:
    marker = root / ".git"
    if marker.is_symlink():
        raise OwnedCoordinationError("OWNED_GIT_PATH_REFUSED", "Symbolic-link Git marker refused", (marker,))
    gitdir = Path(_git(root, "rev-parse", "--absolute-git-dir"))
    if marker.is_file():
        backlink = gitdir / "gitdir"
        if backlink.is_symlink() or (gitdir / backlink.read_text(encoding="utf-8").strip()).resolve() != marker:
            raise OwnedCoordinationError("OWNED_GIT_PATH_REFUSED", "Git registration backlink does not name this checkout", (marker, backlink))


def _snapshot(root: Path, directory: Path, meta: dict[str, Any]) -> StatusSnapshot:
    bound = BoundHistoryDirectory(root, directory)
    try:
        before = bound.capture(("meta.json", "status.events.jsonl", "status.json"))
        snapshot = materialize_snapshot(directory)  # Public PURE source; never materialize().
        log = directory / "status.events.jsonl"
        if not before["status.events.jsonl"].data or not snapshot.work_packages:
            raise OwnedCoordinationError("COORD_CANONICAL_LOG_MISSING", "Coordination requires real canonical WP history", (log,))
        if snapshot.mission_slug != meta["mission_slug"]:
            raise OwnedCoordinationError("COORD_LOG_IDENTITY_REFUSED", "Canonical log identity differs from the selected mission", (log,))
        bound.verify(before)
        return snapshot
    finally:
        bound.close()


def _idle(snapshot: StatusSnapshot) -> None:
    for wp, state in snapshot.work_packages.items():
        pid = state.get("shell_pid")
        if not isinstance(pid, int) or pid <= 0:
            continue
        try:
            process = psutil.Process(pid)
            created = state.get("shell_pid_created_at")
            if created is None or abs(process.create_time() - float(created)) < 0.01:
                raise OwnedCoordinationError("OWNED_ACTIVE_LEASE_REFUSED", f"Recorded {wp} process ownership is still active")
        except psutil.NoSuchProcess:
            continue
        except (psutil.AccessDenied, ValueError) as exc:
            raise OwnedCoordinationError("OWNED_ACTIVE_LEASE_REFUSED", f"Cannot disprove recorded {wp} ownership") from exc


def runtime_evidence(root: Path, slug: str, mission_id: str) -> dict[str, Any]:
    """Inspect only retained owned run state; never bootstrap/rekey/advance it."""
    index_path = _safe_file(root, Path(".kittify/runtime/feature-runs.json"))
    if not index_path.exists():
        return {"present": False, "advanced": False}
    index = json_object(index_path.read_bytes())
    entry = index.get(mission_id) or index.get(slug)
    if entry is None:
        return {"present": False, "advanced": False}
    if not isinstance(entry, dict) or not isinstance(entry.get("run_dir"), str):
        raise OwnedCoordinationError("OWNED_RUN_STATE_REFUSED", "Retained run entry is malformed")
    run_dir = Path(entry["run_dir"])
    run_dir = run_dir if run_dir.is_absolute() else root / run_dir
    try:
        relative = (run_dir / "state.json").relative_to(root)
    except ValueError as exc:
        raise OwnedCoordinationError("OWNED_RUN_ROOT_REFUSED", "Retained run path escapes the owned checkout") from exc
    state = json_object(_safe_file(root, relative).read_bytes())
    return {
        "present": True,
        "run_id": entry.get("run_id"),
        "blocked_reason": state.get("blocked_reason"),
        "completed_steps": state.get("completed_steps", []),
        "issued_step_id": state.get("issued_step_id"),
        "advanced": False,
    }


def owned_base(repository: Path, checkout: Path, handle: str) -> tuple[Path, Path, dict[str, Any], str, str, StatusSnapshot]:
    """Resolve only this registered root, never a primary or shape-based fallback."""
    assert_safe_path_segment(handle)
    ownership = _ownership(repository, checkout)
    root = ownership.root
    _backlink(root)
    try:
        mission = resolve_mission(handle, root)
    except (AmbiguousHandleError, MissionNotFoundError) as exc:
        raise OwnedCoordinationError("OWNED_MISSION_REFUSED", str(exc)) from exc
    directory = root / "kitty-specs" / assert_safe_path_segment(mission.feature_dir.name)
    meta = json_object(_safe_file(root, directory.relative_to(root) / "meta.json").read_bytes())
    validate_meta(meta, directory.name)
    for name in (*PLANNING_FILES, "status.events.jsonl", "status.json"):
        _safe_file(root, directory.relative_to(root) / name)
    _git(root, "check-ref-format", f"refs/heads/{meta['coordination_branch']}")
    _git(root, "check-ref-format", f"refs/heads/{meta['target_branch']}")
    if meta["coordination_branch"] == meta["target_branch"]:
        raise OwnedCoordinationError("COORD_BRANCH_IDENTITY_REFUSED", "Planning and coordination refs must be distinct")
    policy = ProtectionPolicy.resolve(root)
    if any(policy.is_protected(meta[key]) for key in ("target_branch", "coordination_branch")):
        raise OwnedCoordinationError("OWNED_PROTECTED_REF_REFUSED", "Protected planning or coordination branch refused")
    if _dirty_paths(root):
        raise OwnedCoordinationError("OWNED_DIRTY_REFUSED", "The explicitly owned checkout must be clean")
    # Git index assume-unchanged/skip flags must not hide an alternate status
    # authority. Bind actual bytes to this checked-out immutable commit too.
    for name in ("meta.json", "status.events.jsonl", "status.json"):
        pinned, _ = _blob(root, ownership.head, f"kitty-specs/{directory.name}/{name}")
        if (directory / name).read_bytes() != pinned:
            raise OwnedCoordinationError("OWNED_UNCOMMITTED_AUTHORITY_REFUSED", f"Actual authority differs from its committed source: {name}")
    snapshot = _snapshot(root, directory, meta)
    _idle(snapshot)
    run = runtime_evidence(root, directory.name, meta["mission_id"])
    if run.get("issued_step_id") is not None:
        raise OwnedCoordinationError("OWNED_ACTIVE_RUN_REFUSED", "An issued retained runtime step still owns this checkout")
    branch = _git(root, "symbolic-ref", "--short", "HEAD")
    return root, directory, meta, ownership.head, branch, snapshot


def validate_pins(root: Path, directory: Path, meta: dict[str, Any], target: str, coord: str) -> dict[str, Any]:
    """Verify immutable history parity, original planning and the authored WP graph.

    Return source/blob/count/ancestry evidence for explicit placement or query;
    operator-selected pins establish content integrity, not signed approval.
    """
    target_rows, target_source = load_source(root, directory, target, meta)
    coord_rows, coord_source = load_source(root, directory, coord, meta)
    common_ancestor = _git(root, "merge-base", target, coord)
    if not common_ancestor:
        raise OwnedCoordinationError("COORD_PLANNING_ANCESTRY_REFUSED", "Planning and coordination pins have unrelated Git ancestry")
    bundle_paths = [f"kitty-specs/{directory.name}/{name}" for name in PLANNING_FILES]
    planning_ancestor = _git(root, "log", coord, "-1", "--format=%H", "--", *bundle_paths)
    if not planning_ancestor:
        raise OwnedCoordinationError("COORD_PLANNING_ANCESTRY_REFUSED", "Original coordination pin has no recorded planning ancestor")
    target_by_id = {row["event_id"]: row for row in target_rows}
    if any(target_by_id.get(row["event_id"]) != row for row in coord_rows):
        raise OwnedCoordinationError("COORD_HISTORY_CONFLICT", "Coordination-pin records are not preserved in the target history")
    planning = {}
    for name in PLANNING_FILES:
        path = f"kitty-specs/{directory.name}/{name}"
        target_raw, target_blob = _blob(root, target, path)
        coord_raw, _ = _blob(root, coord, path)
        ancestor_raw, _ = _blob(root, planning_ancestor, path)
        working = _safe_file(root, Path(path)).read_bytes()
        if target_raw != coord_raw or coord_raw != ancestor_raw or working != target_raw:
            raise OwnedCoordinationError("OWNED_PLANNING_DRIFT", f"Pinned/current planning disagrees: {name}", (root / path,))
        planning[name] = target_blob
    manifest = load_wps_manifest(directory)
    if manifest is None or {wp.id for wp in manifest.work_packages} != set(materialize_snapshot(directory).work_packages):
        raise OwnedCoordinationError("COORD_WP_COVERAGE_REFUSED", "Authored WP roster and canonical history must match")
    for wp in manifest.work_packages:
        path = wp.prompt_file
        if not path:
            raise OwnedCoordinationError("OWNED_PLANNING_DRIFT", "Every WP requires its existing prompt path")
        absolute = _safe_file(root, directory.relative_to(root) / Path(path))
        pinned, _ = _blob(root, target, absolute.relative_to(root).as_posix())
        if absolute.read_bytes() != pinned:
            raise OwnedCoordinationError("OWNED_PLANNING_DRIFT", f"WP planning differs from its target pin: {wp.id}")
    graph = build_dependency_graph(directory)
    if graph != {wp.id: wp.dependencies for wp in manifest.work_packages} or detect_cycles(graph):
        raise OwnedCoordinationError("OWNED_DEPENDENCY_GRAPH_REFUSED", "WP prompts and roster must agree on a valid dependency graph")
    return {
        "target_source": target_source,
        "coord_source": coord_source,
        "planning": planning,
        "counts": target_source["counts"],
        "common_ancestor": common_ancestor,
        "planning_ancestor": planning_ancestor,
    }


def validate_anchor_shape(root: Path, anchor: str, target: str, coord: str) -> None:
    """Require exact ordered recovery parents and the target tree before activation/read."""
    parents = _git(root, "rev-list", "--parents", "-n", "1", anchor).split()
    if parents != [anchor, target, coord] or _git(root, "rev-parse", f"{anchor}^{{tree}}") != _git(root, "rev-parse", f"{target}^{{tree}}"):
        raise OwnedCoordinationError("COORD_AUTHORITY_BINDING_CONFLICT", "Recovery anchor must preserve both parents and the target tree")


def _anchor(root: Path, meta: dict[str, Any]) -> tuple[str, str, str]:
    candidates = _git(root, "log", "--first-parent", "--format=%H", "--fixed-strings", f"--grep={AUTHORITY_MARKER} {meta['mission_id']}", "-n", "2").splitlines()
    if len(candidates) != 1:
        raise OwnedCoordinationError("COORD_AUTHORITY_BINDING_MISSING", "A unique supported coordination recovery anchor is required")
    anchor = candidates[0]
    body = _git(root, "show", "-s", "--format=%B", anchor).splitlines()
    data = json_object(body[-1])
    if data.get("mission_id") != meta["mission_id"] or data.get("coordination_branch") != meta["coordination_branch"]:
        raise OwnedCoordinationError("COORD_AUTHORITY_BINDING_CONFLICT", "Recovery anchor identity differs from the dossier")
    target, coord = str(data.get("target_commit", "")), str(data.get("coord_commit", ""))
    validate_anchor_shape(root, anchor, target, coord)
    return anchor, target, coord


@dataclass(frozen=True)
class OwnedCoordinationContext:
    repository_root: Path
    root: Path
    directory: Path
    mission_id: str
    slug: str
    target_branch: str
    coord_branch: str
    target_commit: str
    coord_commit: str
    anchor: str
    head: str
    event_counts: tuple[int, int, int, int]

    def roots(self) -> dict[str, str]:
        """Expose logical partition roots while retaining repository identity separately."""
        return {"repository_root": str(self.repository_root), "planning_root": str(self.root), "status_root": str(self.root), "run_root": str(self.root)}


def resolve_owned_coordination(repository: Path, checkout: Path, handle: str) -> tuple[OwnedCoordinationContext, StatusSnapshot]:
    """Bind a clean inactive registered checkout to genuine declared coordination.

    Require the supported recovery anchor, unchanged target planning and retained
    historical records; never substitute a primary surface or an unregistered husk.
    """
    root, directory, meta, head, branch, snapshot = owned_base(repository, checkout, handle)
    coord = meta["coordination_branch"]
    if branch != coord or branch_oid(root, coord) != head:
        from specify_cli.missions._read_path_resolver import coord_feature_dir

        husk = coord_feature_dir(root, directory.name, meta["mission_id"][:8]).parent.parent
        registered = _git(root, "worktree", "list", "--porcelain", "-z").split("\0")
        if husk.exists() and f"worktree {husk}" not in registered:
            raise OwnedCoordinationError("COORD_AUTHORITY_HUSK_UNREGISTERED", "An existing directory is not Git coordination authority", (husk,))
        raise OwnedCoordinationError("COORD_AUTHORITY_UNAVAILABLE", "Checkout must be registered on its declared coordination ref; run restore-owned-coordination")
    anchor, target, pin = _anchor(root, meta)
    if branch_oid(root, meta["target_branch"]) != target:
        raise OwnedCoordinationError("OWNED_PLANNING_DRIFT", "Target ref advanced beyond the explicit planning binding")
    validate_pins(root, directory, meta, target, pin)
    current_rows, current_source = load_source(root, directory, head, meta)  # Validate current coord log, no husk fallback.
    target_rows, _ = load_source(root, directory, target, meta)
    current_by_id = {row["event_id"]: row for row in current_rows}
    if any(current_by_id.get(row["event_id"]) != row for row in target_rows):
        raise OwnedCoordinationError("COORD_HISTORY_CONFLICT", "Current coordination history must preserve every restored target record")
    counts = current_source["counts"]
    return OwnedCoordinationContext(
        repository,
        root,
        directory,
        meta["mission_id"],
        directory.name,
        meta["target_branch"],
        coord,
        target,
        pin,
        anchor,
        head,
        (counts["rows"], counts["transitions"], counts["annotations"], counts["non_lane"]),
    ), snapshot


def query_owned_coordination(repository: Path, checkout: Path, handle: str) -> dict[str, Any]:
    """Return validated status, dependency readiness and retained runtime evidence.

    This is a pure query of the committed owned authority: no runtime bootstrap,
    lane allocation, review disposition, snapshot write or DAG advancement.
    """
    context, snapshot = resolve_owned_coordination(repository, checkout, handle)
    manifest = load_wps_manifest(context.directory)
    if manifest is None:
        raise OwnedCoordinationError("COORD_WP_COVERAGE_REFUSED", "Missing existing WP roster")
    lanes = {wp: state["lane"] for wp, state in snapshot.work_packages.items()}
    readiness = {}
    for wp in manifest.work_packages:
        ready = dependency_readiness_for_wp(wp.id, wp.dependencies, lanes)
        readiness[wp.id] = {
            "satisfied": ready.satisfied,
            "unsatisfied": list(ready.unsatisfied),
            "code": "ready" if ready.satisfied else "dependencies_not_satisfied",
        }
    return {
        "kind": "query",
        "is_query": True,
        "mission_id": context.mission_id,
        "mission_slug": context.slug,
        "mission_state": "coordinated_evidence",
        "action": None,
        "reason": "review_in_progress" if "in_review" in lanes.values() else "query_only",
        "lanes": lanes,
        "work_packages": snapshot.work_packages,
        "readiness": readiness,
        "roots": context.roots(),
        "planning_ref": context.target_branch,
        "status_ref": context.coord_branch,
        "authority_commit": context.head,
        "progress": {
            "total_wps": len(lanes),
            "approved_wps": snapshot.summary.get("approved", 0),
            "planned_wps": snapshot.summary.get("planned", 0),
            "for_review_wps": snapshot.summary.get("in_review", 0) + snapshot.summary.get("for_review", 0),
        },
        "runtime": runtime_evidence(context.root, context.slug, context.mission_id),
        "runtime_advanced": False,
        "counts": dict(zip(("rows", "transitions", "annotations", "non_lane"), context.event_counts, strict=True)),
        "allocated": False,
        "accept": False,
        "merge": False,
    }
