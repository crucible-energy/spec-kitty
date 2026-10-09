"""Explicit transactional conversion of an archived legacy owned code lane (#85)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kernel.git import blob_at, run_git, status_entries
from mission_runtime import MissionTopology, OwnedCheckout
from specify_cli.coordination.transaction import BookkeepingTransaction
from specify_cli.core.owned_mission import require_unstaged_index
from specify_cli.core.paths import load_meta_fail_closed
from specify_cli.lanes.compute import compute_lanes, is_repo_root_lane
from specify_cli.lanes.branch_naming import resolve_mid8
from specify_cli.lanes.models import LanesManifest
from specify_cli.lanes.persistence import lanes_json_lock, read_lanes_json
from specify_cli.migration.owned_single_branch_proof import RecoveryError, RecoveryProof, digest, load_proof, read_regular, verify_history
from specify_cli.ownership.validation import build_wp_manifests, validate_all, validate_glob_matches
from specify_cli.status import read_authored_wp_frontmatter, read_events_from_text, wp_task_files, write_checkout_claim_lock

__all__ = ["recover_owned_single_branch"]

_RECEIPT = "recovery/owned-single-branch.json"


@dataclass(frozen=True)
class _Plan:
    previous: LanesManifest
    replacement: bytes
    receipt: bytes
    snapshot: dict[str, str]


def _git(owned: OwnedCheckout, *args: str) -> str:
    return run_git(owned.owned_root, *args, timeout=15).stdout.decode("utf-8").strip()


def _snapshot(owned: OwnedCheckout) -> dict[str, str]:
    paths = [owned.mission_dir / name for name in ("meta.json", "lanes.json", "status.events.jsonl")]
    paths.extend(wp_task_files(owned.mission_dir / "tasks"))
    return {path.relative_to(owned.owned_root).as_posix(): digest(read_regular(path)) for path in paths}


def _plan(owned: OwnedCheckout, proof: RecoveryProof, proof_bytes: bytes) -> _Plan:
    require_unstaged_index(owned)
    if _git(owned, "rev-parse", "HEAD") != proof.owner_head or _git(owned, "branch", "--show-current") != owned.write_branch:
        raise RecoveryError("Owner HEAD or branch differs from the pinned proof")
    if status_entries(owned.owned_root, untracked="all", timeout=15):
        raise RecoveryError("Owned checkout must be clean before explicit conversion")
    meta = load_meta_fail_closed(owned.mission_dir)
    if not meta or meta.get("coordination_branch") or meta.get("topology") != "single_branch":
        raise RecoveryError("Recovery requires a single_branch mission without coordination")
    previous = read_lanes_json(owned.mission_dir)
    if previous is None or len(previous.lanes) != 1 or is_repo_root_lane(previous.lanes[0]):
        raise RecoveryError("Recovery requires exactly one legacy code lane")
    if previous.mission_id != meta.get("mission_id") or previous.mission_slug != owned.mission_slug or previous.target_branch != meta.get("target_branch"):
        raise RecoveryError("Legacy manifest identity or target differs from the owned mission")
    if previous.planning_commit_sha != proof.planning_commit_sha:
        raise RecoveryError("Original planning pin differs from the proof; refresh is forbidden")
    run_git(owned.owned_root, "merge-base", "--is-ancestor", proof.planning_commit_sha, proof.owner_head, timeout=15)
    frontmatters = {}
    for path in wp_task_files(owned.mission_dir / "tasks"):
        read_regular(path)
        frontmatter, _body = read_authored_wp_frontmatter(path)
        wp_id = frontmatter.work_package_id
        if not wp_id or wp_id in frontmatters:
            raise RecoveryError("WP identity is missing or duplicated")
        frontmatters[wp_id] = frontmatter
    membership = previous.lanes[0].wp_ids
    if len(membership) != len(set(membership)) or set(membership) != set(frontmatters):
        raise RecoveryError("Legacy lane must cover the complete unchanged WP membership")
    ownership = build_wp_manifests(frontmatters)
    dependencies = {wp_id: list(fm.dependencies) for wp_id, fm in frontmatters.items()}
    errors = validate_all(ownership, dependencies).errors
    errors.extend(validate_glob_matches(ownership, owned.owned_root, create_intent={wp: list(fm.create_intent) for wp, fm in frontmatters.items()}).errors)
    if errors:
        raise RecoveryError("Ownership validation failed: " + "; ".join(errors))
    scope = sorted(set(previous.lanes[0].write_scope) | {path for manifest in ownership.values() for path in manifest.owned_files})
    for path in scope:
        if Path(path).is_absolute() or ".." in Path(path).parts or path.startswith(":"):
            raise RecoveryError("Production scope is ambiguous or escapes the owner")
    preserved = verify_history(owned, proof, previous.mission_branch, scope)
    # Parse current state too; conversion never rewrites or repairs event envelopes.
    read_events_from_text(owned.mission_dir, read_regular(owned.mission_dir / "status.events.jsonl").decode("utf-8"))
    replacement = compute_lanes(
        dependencies,
        ownership,
        owned.mission_slug,
        previous.target_branch,
        mission_id=previous.mission_id,
        topology=MissionTopology.SINGLE_BRANCH,
        mission_branch=meta.get("mission_branch"),
    )
    replacement.planning_commit_sha = previous.planning_commit_sha
    if set(replacement.lanes[0].wp_ids) != set(membership):
        raise RecoveryError("Canonical computation changed WP membership")
    replacement_bytes = (json.dumps(replacement.to_dict(), indent=2) + "\n").encode()
    original = read_regular(owned.mission_dir / "lanes.json")
    snapshot = _snapshot(owned)
    receipt = {
        "schema_version": 1,
        "proof": proof.model_dump(),
        "proof_sha256": digest(proof_bytes),
        "original_lanes": previous.to_dict(),
        "original_lanes_sha256": digest(original),
        "converted_lanes_sha256": digest(replacement_bytes),
        "snapshot": snapshot,
        "preserved": preserved,
        "scope": scope,
        "membership": list(membership),
        "lane_mapping": {previous.lanes[0].lane_id: replacement.lanes[0].lane_id},
        "uncommitted_historical_work": "unknown",
    }
    return _Plan(previous, replacement_bytes, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(), snapshot)


def _already_converted(owned: OwnedCheckout, proof: RecoveryProof, proof_bytes: bytes) -> bool:
    manifest = read_lanes_json(owned.mission_dir)
    if manifest is None or len(manifest.lanes) != 1 or not is_repo_root_lane(manifest.lanes[0]):
        return False
    path = owned.mission_dir / _RECEIPT
    receipt_bytes = read_regular(path)
    relative = path.relative_to(owned.owned_root).as_posix()
    if blob_at(owned.owned_root, "HEAD", relative, timeout=15, max_bytes=8_388_608) != receipt_bytes:
        raise RecoveryError("Recovery receipt is not qualified by HEAD")
    receipt: dict[str, Any] = json.loads(receipt_bytes)
    if receipt.get("schema_version") != 1 or receipt.get("proof_sha256") != digest(proof_bytes) or receipt.get("proof") != proof.model_dump():
        raise RecoveryError("Recovery receipt does not qualify this proof")
    if receipt.get("converted_lanes_sha256") != digest(read_regular(owned.mission_dir / "lanes.json")):
        raise RecoveryError("Converted manifest differs from the qualifying receipt")
    if status_entries(owned.owned_root, untracked="all", timeout=15):
        raise RecoveryError("Owned checkout is dirty")
    verify_history(owned, proof, str(receipt["original_lanes"]["mission_branch"]), receipt["scope"])
    if manifest.planning_commit_sha != proof.planning_commit_sha:
        raise RecoveryError("Original planning pin changed after conversion")
    return True


def recover_owned_single_branch(owned: OwnedCheckout, proof_path: Path, *, dry_run: bool) -> dict[str, object]:
    """Qualify evidence, preview without effects, or atomically convert and commit.

    Lock order: checkout claim, Mission transaction, manifest. Apply requalifies
    every proof inside that serialization boundary before writing any artifact.
    """
    proof_bytes = read_regular(proof_path, limit=65_536)
    proof = load_proof(proof_bytes)
    if _already_converted(owned, proof, proof_bytes):
        return {"success": True, "result": "already_converted", "receipt": str(owned.mission_dir / _RECEIPT)}
    preview = _plan(owned, proof, proof_bytes)
    if dry_run:
        return {"success": True, "result": "would_convert", "lane_mapping": json.loads(preview.receipt)["lane_mapping"]}
    with (
        write_checkout_claim_lock(owned.owned_root),
        BookkeepingTransaction.acquire(
            repo_root=owned.repository_root,
            mission_id=preview.previous.mission_id or "",
            mission_slug=owned.mission_slug,
            mid8=resolve_mid8(owned.mission_slug, mission_id=preview.previous.mission_id),
            destination_ref=owned.write_branch,
            operation="owned single branch recovery",
            owned=owned,
        ) as transaction,
        lanes_json_lock(owned.mission_dir),
    ):
        if read_regular(proof_path, limit=65_536) != proof_bytes:
            raise RecoveryError("Proof changed before apply")
        plan = _plan(owned, proof, proof_bytes)
        if plan.snapshot != preview.snapshot or _snapshot(owned) != plan.snapshot or read_regular(proof_path, limit=65_536) != proof_bytes:
            raise RecoveryError("Frozen inputs changed before apply")
        if _git(owned, "rev-parse", "HEAD") != proof.owner_head or _git(owned, "branch", "--show-current") != owned.write_branch:
            raise RecoveryError("Owner HEAD or branch changed before apply")
        transaction.write_artifact(owned.mission_dir / "lanes.json", plan.replacement)
        transaction.write_artifact(owned.mission_dir / _RECEIPT, plan.receipt)
        receipt = transaction.commit("Recover legacy owned lane as explicit single branch")
    return {"success": True, "result": "converted", "commit_sha": receipt.commit_sha, "receipt": str(owned.mission_dir / _RECEIPT)}
