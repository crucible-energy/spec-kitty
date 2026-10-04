"""Atomic ref/HEAD placement for a reused owned coordinated checkout."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from specify_cli.coordination.owned import AUTHORITY_MARKER, OwnedCoordinationError, branch_oid, owned_base, resolve_owned_coordination, validate_pins
from specify_cli.migration.owned_history_io import BoundHistoryDirectory
from specify_cli.status.locking import feature_status_lock

__all__ = ["restore_owned_coordination"]


def git_operation(root: Path, args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    """Run one bounded Git operation without environment redirects or replacement objects.

    Unlike immutable source reads, this helper also executes the creator's planned
    commit/ref transaction. Nonzero Git results become typed placement refusals.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(root), *args], input=input_bytes, capture_output=True, timeout=30, env=env)
    if result.returncode:
        raise OwnedCoordinationError("COORD_GIT_TRANSACTION_REFUSED", result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def _plan(repository: Path, checkout: Path, handle: str, target: str, coord: str) -> tuple[dict[str, Any], dict[str, Any]]:
    root, directory, meta, head, branch, snapshot = owned_base(repository, checkout, handle)
    if branch == meta["coordination_branch"]:
        context, _ = resolve_owned_coordination(repository, checkout, handle)
        if context.target_commit != target or context.coord_commit != coord:
            raise OwnedCoordinationError("COORD_AUTHORITY_BINDING_CONFLICT", "Existing authority uses different pins")
        return {"changed": False, "destination_ref": branch, "head": head}, meta
    if branch != meta["target_branch"] or head != target or branch_oid(root, branch) != target:
        raise OwnedCoordinationError("OWNED_TARGET_REF_REFUSED", "Current branch/HEAD must match the explicit target pin")
    if branch_oid(root, meta["coordination_branch"]) is not None:
        raise OwnedCoordinationError("COORD_REF_CONFLICT", "Existing coordination ref is protected from replacement")
    registrations = git_operation(root, ["worktree", "list", "--porcelain", "-z"]).decode().split("\0")
    if f"branch refs/heads/{meta['coordination_branch']}" in registrations:
        raise OwnedCoordinationError("COORD_ACTIVE_OWNERSHIP_REFUSED", "Declared coordination branch is already assigned to another checkout")
    proof = validate_pins(root, directory, meta, target, coord)
    gitdir = Path(git_operation(root, ["rev-parse", "--absolute-git-dir"]).decode().strip())
    common = Path(git_operation(root, ["rev-parse", "--path-format=absolute", "--git-common-dir"]).decode().strip())
    if gitdir.parent != common / "worktrees":
        raise OwnedCoordinationError("OWNED_LINKED_CHECKOUT_REQUIRED", "Authority placement requires a registered linked checkout; never rebind primary")
    return {
        "changed": True,
        "destination_ref": meta["coordination_branch"],
        "parents": [target, coord],
        "target_commit": target,
        "coord_commit": coord,
        "mission_id": meta["mission_id"],
        "mission_slug": directory.name,
        "owned_checkout": str(root),
        "git_dir": str(gitdir),
        "counts": proof["counts"],
        "planning": proof["planning"],
        "planning_ancestor": proof["planning_ancestor"],
        "common_ancestor": proof["common_ancestor"],
        "tree": git_operation(root, ["rev-parse", f"{target}^{{tree}}"]).decode().strip(),
        "lanes": {wp: state["lane"] for wp, state in snapshot.work_packages.items()},
    }, meta


def restore_owned_coordination(repository: Path, checkout: Path, handle: str, target: str, coord: str, *, apply: bool = False) -> dict[str, Any]:
    """Preview or establish coordination authority in a reused registered checkout.

    Apply validates immutable parents/planning and inactivity under the canonical
    lock, builds an exact-target-tree anchor and atomically creates the missing
    coordination ref plus symbolic HEAD. It allocates no workspace or DAG action.
    """
    report, meta = _plan(repository, checkout, handle, target, coord)
    if apply and report["changed"]:
        checkout = Path(report["owned_checkout"])
        version = git_operation(checkout, ["version"]).decode()
        match = re.search(r"git version (\d+)\.(\d+)", version)
        if match is None or tuple(map(int, match.groups())) < (2, 48):
            raise OwnedCoordinationError("COORD_GIT_CAPABILITY_UNSUPPORTED", "Atomic symbolic-HEAD/ref transactions require Git 2.48+")
        with feature_status_lock(checkout, meta["mission_slug"], timeout=10):
            directory = checkout / "kitty-specs" / meta["mission_slug"]
            bound = BoundHistoryDirectory(checkout, directory)
            try:
                images = bound.capture(("meta.json", "status.events.jsonl", "status.json"))
                locked, _ = _plan(repository, checkout, handle, target, coord)
                if locked != report:
                    raise OwnedCoordinationError("COORD_PLAN_CHANGED", "Authority plan changed under the canonical lock")
                backend = ["--git-dir", report["git_dir"]]
                git_operation(checkout, [*backend, "var", "GIT_AUTHOR_IDENT"])
                message = (
                    f"Restore owned coordinated authority for {meta['mission_slug']}\n\n{AUTHORITY_MARKER} {meta['mission_id']}\n"
                    + json.dumps(
                        {"mission_id": meta["mission_id"], "target_commit": target, "coord_commit": coord, "coordination_branch": meta["coordination_branch"]},
                        sort_keys=True,
                    )
                    + "\n"
                )
                commit = (
                    git_operation(checkout, [*backend, "commit-tree", report["tree"], "-p", target, "-p", coord], input_bytes=message.encode()).decode().strip()
                )
                bound.verify(images)
                locked, _ = _plan(repository, checkout, handle, target, coord)
                if locked != report:
                    raise OwnedCoordinationError("COORD_PLAN_CHANGED", "Authority plan changed before ref transaction")
                # Git's oid form verifies HEAD's current referent value within
                # the same native transaction that creates the coordination ref.
                # Branch identity has just been revalidated under the mission lock.
                # A separate target verify is forbidden by Git as a duplicate
                # update through HEAD; never split this into two ref transactions.
                transaction = (
                    f"start\noption no-deref\ncreate refs/heads/{meta['coordination_branch']} {commit}\n"
                    f"option no-deref\nsymref-update HEAD refs/heads/{meta['coordination_branch']} oid {target}\nprepare\ncommit\n"
                )
                git_operation(checkout, [*backend, "update-ref", "--stdin"], input_bytes=transaction.encode())
                report["head"] = commit
            finally:
                bound.close()
    return {**report, "dry_run": not apply, "applied": bool(apply and report["changed"]), "allocated": False, "runtime_advanced": False}
