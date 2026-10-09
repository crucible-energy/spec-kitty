"""Verify exact external custody; this never issues a source-review verdict."""

from __future__ import annotations

import json
from pathlib import Path

from kernel.git import TreeEntry, blob_at, changed_entries, run_git
from mission_runtime import OwnedCheckout
from specify_cli.migration.owned_single_branch_proof import CustodyRecoveryProof, RecoveryError, digest, read_closed_object, read_regular
from specify_cli.migration.owned_source_custody_models import CustodyManifest
from specify_cli.migration.owned_source_history import reconstruct_source_history, source_history_env

__all__ = ["verify_source_custody"]


def _raw_digest(content: bytes) -> str:
    return digest(content).removeprefix("sha256:")


def _load_manifest(owned: OwnedCheckout, proof: CustodyRecoveryProof) -> tuple[Path, bytes, CustodyManifest]:
    path = Path(proof.custody.path)
    if not path.is_absolute() or path.is_relative_to(owned.owned_root) or path.is_relative_to(owned.repository_root):
        raise RecoveryError("Custody must be an explicit external store")
    content = read_regular(path, limit=1_048_576)
    if _raw_digest(content) != proof.custody.sha256:
        raise RecoveryError("Custody manifest identity changed")
    try:
        manifest = CustodyManifest.model_validate(read_closed_object(content))
    except ValueError:
        raise RecoveryError("Invalid closed custody manifest") from None
    return path, content, manifest


def _verify_catalog(owned: OwnedCheckout, directory: Path, manifest: CustodyManifest, objects: dict[str, tuple[str, str]]) -> None:
    catalog = {row.oid: row for row in manifest.blobs}
    if len(catalog) != len(manifest.blobs) or set(catalog) != set(objects) or sum(row.bytes for row in catalog.values()) > 67_108_864:
        raise RecoveryError("Custody blob census is incomplete, duplicated or oversized")
    for oid, row in catalog.items():
        if row.file != "blobs/" + row.sha256:
            raise RecoveryError("Custody blob path must be its exact content identity")
        raw = read_regular(directory / row.file, limit=row.bytes)
        revision, path = objects[oid]
        immutable = blob_at(owned.owned_root, revision, path, env=source_history_env(), timeout=15, max_bytes=8_388_608)
        if len(raw) != row.bytes or _raw_digest(raw) != row.sha256 or raw != immutable:
            raise RecoveryError("Custody raw bytes differ from the pinned object")


def _verify_current_source(owned: OwnedCheckout, owner_head: str, scope: list[str], owner_tree: dict[str, TreeEntry]) -> str:
    head = run_git(owned.owned_root, "rev-parse", "HEAD", timeout=15).stdout.decode("ascii").strip()
    run_git(owned.owned_root, "merge-base", "--is-ancestor", owner_head, head, env=source_history_env(), timeout=15)
    if changed_entries(owned.owned_root, owner_head, head, pathspecs=scope, env=source_history_env(), timeout=15):
        raise RecoveryError("Current scoped source changed after the pinned owner")
    touched = run_git(
        owned.owned_root,
        "--literal-pathspecs",
        "log",
        "--full-history",
        "--max-count=1",
        "--format=%H",
        owner_head + ".." + head,
        "--",
        *scope,
        env=source_history_env(),
        timeout=15,
    ).stdout
    if touched.strip():
        raise RecoveryError("Post-owner history contains scoped source work")
    snapshot: dict[str, dict[str, str]] = {}
    budget = 67_108_864
    for row in owner_tree.values():
        if row.type != "blob" or row.mode not in ("100644", "100755"):
            raise RecoveryError("Current source is not a supported regular file")
        raw = read_regular(owned.owned_root / str(row.path), limit=min(budget, 8_388_608), executable=row.mode == "100755")
        immutable = blob_at(owned.owned_root, owner_head, str(row.path), env=source_history_env(), timeout=15, max_bytes=min(budget, 8_388_608))
        if raw != immutable:
            raise RecoveryError("Current working source differs from its pinned object")
        budget -= len(raw)
        snapshot[str(row.path)] = {"oid": row.oid, "mode": row.mode, "sha256": digest(raw)}
    return digest(json.dumps(snapshot, sort_keys=True).encode())


def verify_source_custody(owned: OwnedCheckout, proof: CustodyRecoveryProof, refs: dict[str, str], scope: list[str], mission_id: str | None) -> dict[str, str]:
    """Reconstruct complete history and compare every closed custody identity."""
    path, content, manifest = _load_manifest(owned, proof)
    branch = run_git(owned.owned_root, "branch", "--show-current", timeout=15).stdout.decode("utf-8").strip()
    if (
        manifest.mission_id != mission_id
        or manifest.mission_slug != owned.mission_slug
        or manifest.owner_root != str(owned.owned_root)
        or manifest.owner_branch != branch
        or manifest.owner_head != proof.owner_head
        or manifest.planning_commit_sha != proof.planning_commit_sha
        or manifest.historical_base != proof.historical_base
        or manifest.scope != scope
    ):
        raise RecoveryError("Custody identity or full scope differs from the pinned owner")
    census = reconstruct_source_history(owned, proof.historical_base, proof.owner_head, refs, scope)
    recorded = {
        "refs": [row.model_dump() for row in manifest.refs],
        "edges": [row.model_dump() for row in manifest.edges],
        "tips": [row.model_dump() for row in manifest.tips],
    }
    observed = {"refs": census.refs, "edges": census.edges, "tips": census.tips}
    if not census.objects or recorded != observed:
        raise RecoveryError("Custody omits or adds retained history identities")
    _verify_catalog(owned, path.parent, manifest, census.objects)
    current_source = _verify_current_source(owned, proof.owner_head, scope, census.owner_tree)
    if read_regular(path, limit=1_048_576) != content:
        raise RecoveryError("Custody manifest changed during qualification")
    return {
        "source_disposition": proof.source_disposition,
        "custody_manifest_sha256": _raw_digest(content),
        "current_source_sha256": current_source,
        "source_census_sha256": digest(json.dumps({"refs": census.refs, "edges": census.edges, "tips": census.tips}, sort_keys=True).encode()),
    }
