"""Read-only safety prerequisites for a normal execution lane.

Canonical status determines occupancy. Workspace context is a historical pointer,
not a second claim authority. Allocation and preflight consume these checks.
"""

from __future__ import annotations

from pathlib import Path
from collections.abc import Iterator
from contextlib import contextmanager

from kernel.git_topology import GitTopologyError, clear_caches, git_common_dir, git_toplevel
from specify_cli.core.errors import StructuredError
from specify_cli.core.git_ops import get_current_branch
from specify_cli.lanes.checkout_occupancy import lane_workspace_claimants
from specify_cli.lanes.models import ExecutionLane
from specify_cli.status import CHECKOUT_CLAIM_LOCK_TIMEOUT_SECONDS


class LaneOccupiedError(StructuredError):
    """Another nonterminal implementation/review claim owns this execution lane."""

    error_code = "LANE_OCCUPIED"


class LaneWorkspaceMismatchError(StructuredError):
    """The predicted path is not this repository's expected lane worktree."""

    error_code = "LANE_WORKSPACE_MISMATCH"


class LaneStatusUnreadableError(StructuredError):
    """Canonical status cannot establish whether the execution lane is occupied."""

    error_code = "LANE_STATUS_UNREADABLE"


def ensure_lane_unoccupied(repo_root: Path, mission_slug: str, wp_id: str, lane: ExecutionLane) -> None:
    """Refuse another outstanding claim in the same lane; allow same-WP resume."""
    from specify_cli.status import StoreError

    try:
        occupied = lane_workspace_claimants(repo_root, mission_slug, wp_id, lane.wp_ids)
    except StoreError as exc:
        raise LaneStatusUnreadableError(f"Cannot read canonical status for lane {lane.lane_id}: {exc}") from exc
    if occupied:
        raise LaneOccupiedError(
            f"Lane {lane.lane_id} has outstanding claims: {', '.join(claim.wp_id for claim in occupied)}. "
            "Finish or explicitly resolve those claims through the normal lifecycle before starting another WP."
        )


def ensure_lane_workspace_identity(repo_root: Path, workspace: Path, branch: str) -> None:
    """Verify toplevel, common repository identity, and current branch before reuse."""
    # Topology primitives memoize reads; start must observe replacement since preflight.
    clear_caches()
    try:
        valid = (
            git_toplevel(workspace) == workspace.resolve() and git_common_dir(workspace) == git_common_dir(repo_root) and get_current_branch(workspace) == branch
        )
    except GitTopologyError as exc:
        raise LaneWorkspaceMismatchError(f"Cannot verify lane workspace {workspace}: {exc}") from exc
    if not valid:
        raise LaneWorkspaceMismatchError(
            f"Workspace {workspace} is not the expected {branch} worktree in this repository. "
            "Preserve its contents, and recover the correct lane through the workspace lifecycle."
        )


@contextmanager
def execution_lane_claim_lock(repo_root: Path, mission_slug: str, wp_id: str, *, timeout: float = CHECKOUT_CLAIM_LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    """Hold the existing checkout lock for a normal lane through admission and claim.

    Repository-root and legacy placement retain their existing lock authority.
    The lock is keyed by the canonical predicted path, including before creation.
    """
    from mission_runtime import MissionArtifactKind, placement_seam
    from specify_cli.lanes.compute import is_repo_root_lane
    from specify_cli.lanes.persistence import read_lanes_json
    from specify_cli.lanes.worktree_allocator import predict_lane_worktree
    from specify_cli.status import write_checkout_claim_lock

    manifest = read_lanes_json(placement_seam(repo_root, mission_slug).read_dir(MissionArtifactKind.LANE_STATE))
    lane = manifest.lane_for_wp(wp_id) if manifest is not None else None
    if lane is None or is_repo_root_lane(lane):
        yield
        return
    workspace, branch = predict_lane_worktree(repo_root, mission_slug, lane.lane_id)
    if workspace.exists():
        ensure_lane_workspace_identity(repo_root, workspace, branch)
    with write_checkout_claim_lock(workspace, timeout=timeout, repo_root=repo_root):
        yield
