"""Closed custody failures remain visible and have zero owned/shared effects."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from kernel.content_digest import sha256_digest
from tests.integration.conftest import OwnedCheckouts, _git
from tests.integration.test_owned_single_branch_recovery_cli import (
    custody_manifest,
    invoke_root,
    preserved_owner as preserved_owner,
    recovery_owner as recovery_owner,
    state,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.git_repo,
    pytest.mark.real_worktree_detection,
    pytest.mark.parametrize("recovery_owner", ["custody"], indirect=True),
]


def bind(proof_path: Path, manifest: Path, data: dict[str, Any] | None = None) -> None:
    if data is not None:
        manifest.write_text(json.dumps(data, sort_keys=True))
    proof = json.loads(proof_path.read_text())
    proof["custody"]["sha256"] = sha256_digest(manifest.read_bytes()).removeprefix("sha256:")
    proof_path.write_text(json.dumps(proof))


@pytest.mark.parametrize(
    "mutation",
    [
        "scope_missing",
        "scope_extra",
        "ref_missing",
        "commit_missing",
        "commit_extra",
        "edge_missing",
        "merge_edge",
        "tip_missing",
        "blob_missing",
        "blob_extra",
        "blob_identity",
        "owner_root",
        "owner_branch",
        "owner_head",
        "planning_pin",
        "base",
        "secret",
        "duplicate",
        "boolean",
        "path_escape",
    ],
)
def test_closed_custody_census_refusals(preserved_owner: tuple[OwnedCheckouts, Path, Path], mutation: str) -> None:
    checkouts, proof_path, manifest = preserved_owner
    data = json.loads(manifest.read_text())
    field_mutations = {
        "owner_root": ("owner_root", str(checkouts.sibling)),
        "owner_branch": ("owner_branch", "codex/other-owner"),
        "owner_head": ("owner_head", data["historical_base"]),
        "planning_pin": ("planning_commit_sha", data["owner_head"]),
        "base": ("historical_base", data["owner_head"]),
        "secret": ("approved_by", "SYNTHETIC_SECRET_SENTINEL"),
        "boolean": ("schema_version", True),
    }
    if mutation in field_mutations:
        field, value = field_mutations[mutation]
        data[field] = value
    elif mutation == "scope_missing":
        data["scope"].pop()
    elif mutation == "scope_extra":
        data["scope"].append("src/undeclared.py")
    elif mutation == "ref_missing":
        data["refs"].pop()
    elif mutation == "commit_missing":
        data["refs"][0]["commits"].pop()
    elif mutation == "commit_extra":
        data["refs"][0]["commits"].append(data["historical_base"])
    elif mutation == "edge_missing":
        data["edges"].pop()
    elif mutation == "merge_edge":
        multiple = next(row["commit"] for row in data["edges"] if sum(edge["commit"] == row["commit"] for edge in data["edges"]) > 1)
        data["edges"] = [row for row in data["edges"] if not (row["commit"] == multiple and row["changes"])]
    elif mutation == "tip_missing":
        data["tips"].pop()
    elif mutation == "blob_missing":
        data["blobs"].pop()
    elif mutation == "blob_extra":
        data["blobs"].append({**data["blobs"][0], "oid": "f" * 40})
    elif mutation == "blob_identity":
        data["blobs"][0]["sha256"] = "f" * 64
    elif mutation == "path_escape":
        data["blobs"][0]["file"] = "../outside-owned-custody"
    else:
        manifest.write_text('{"schema_version": 1,' + json.dumps(data)[1:])
        bind(proof_path, manifest)
        data = None
    if data is not None:
        bind(proof_path, manifest, data)
    before = state(checkouts)
    result = invoke_root(checkouts, proof_path, "--dry-run")
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_RECOVERY_REFUSED"
    assert "SYNTHETIC_SECRET_SENTINEL" not in result.output
    assert state(checkouts) == before
    assert not (checkouts.mission_dir / "recovery/owned-single-branch.json").exists()


@pytest.mark.parametrize(
    "mutation", ["corrupt", "missing", "oversized", "symlink_blob", "symlink_directory", "symlink_manifest", "manifest_hash", "manifest_oversized"]
)
def test_raw_custody_refusals(preserved_owner: tuple[OwnedCheckouts, Path, Path], mutation: str) -> None:
    checkouts, proof_path, manifest = preserved_owner
    data = json.loads(manifest.read_text())
    blob = manifest.parent / data["blobs"][0]["file"]
    if mutation == "corrupt":
        blob.write_bytes(b"different raw bytes")
    elif mutation == "missing":
        blob.unlink()
    elif mutation == "oversized":
        blob.write_bytes(b"x" * 8_388_609)
    elif mutation == "symlink_blob":
        other = blob.with_name("external-copy")
        blob.rename(other)
        blob.symlink_to(other)
    elif mutation == "symlink_directory":
        directory = manifest.parent / "blobs"
        other = manifest.parent / "moved-blobs"
        directory.rename(other)
        directory.symlink_to(other)
    elif mutation == "symlink_manifest":
        other = manifest.with_name("external-manifest.json")
        manifest.rename(other)
        manifest.symlink_to(other)
    elif mutation == "manifest_oversized":
        manifest.write_bytes(b" " * 1_048_577)
    else:
        manifest.write_text(manifest.read_text() + " ")
    before = state(checkouts)
    result = invoke_root(checkouts, proof_path, "--dry-run")
    assert result.exit_code == 1, result.output
    assert state(checkouts) == before


@pytest.mark.parametrize("mutation", ["custody", "source", "source_revert", "authored_scope"])
def test_repeat_requalifies_source_and_custody(preserved_owner: tuple[OwnedCheckouts, Path, Path], mutation: str) -> None:
    checkouts, proof_path, manifest = preserved_owner
    applied = invoke_root(checkouts, proof_path)
    assert applied.exit_code == 0, applied.output
    root = checkouts.owned_root
    if mutation == "custody":
        blob = manifest.parent / json.loads(manifest.read_text())["blobs"][0]["file"]
        blob.write_bytes(b"changed after conversion")
    elif mutation == "source_revert":
        path = root / "data/performance-manifest.json"
        original = path.read_bytes()
        path.write_bytes(b"intermediate post-conversion source edit")
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "post-conversion source edit")
        path.write_bytes(original)
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "restore source tree; retain actual source history")
    elif mutation == "authored_scope":
        path = checkouts.mission_dir / "tasks/WP01-owned.md"
        path.write_text(path.read_text().replace("data/performance-manifest.json", "src/contract1.py"))
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "changed authored ownership")
    else:
        path = root / "data/performance-manifest.json"
        path.write_bytes(b"source corruption after conversion")
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "post-conversion source drift")
    before = state(checkouts)
    refused = invoke_root(checkouts, proof_path)
    assert refused.exit_code == 1, refused.output
    assert state(checkouts) == before


@pytest.mark.parametrize("mutation", ["under_lock", "during_write", "source", "refs", "proof", "rollback"])
def test_apply_requalifies_and_rolls_back(preserved_owner: tuple[OwnedCheckouts, Path, Path], monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    from specify_cli.coordination.transaction import BookkeepingTransaction
    from specify_cli.migration import owned_single_branch as recovery

    checkouts, proof_path, manifest = preserved_owner
    before = state(checkouts)
    if mutation == "under_lock":
        original = recovery._plan
        calls = 0

        def change_under_lock(*args: Any, **kwargs: Any) -> Any:
            nonlocal calls
            calls += 1
            if calls == 2:
                manifest.write_text(manifest.read_text() + " ")
            return original(*args, **kwargs)

        monkeypatch.setattr(recovery, "_plan", change_under_lock)
    elif mutation in {"source", "refs", "proof"}:
        original = recovery._plan
        calls = 0

        def change_pinned_input(*args: Any, **kwargs: Any) -> Any:
            nonlocal calls
            calls += 1
            if calls == 2:
                if mutation == "source":
                    (checkouts.owned_root / "data/performance-manifest.json").write_bytes(b"concurrent source change")
                elif mutation == "refs":
                    historical = json.loads(proof_path.read_text())["historical_refs"][0]
                    _git(checkouts.owned_root, "update-ref", historical["ref"], json.loads(proof_path.read_text())["historical_base"])
                else:
                    proof_path.write_text(proof_path.read_text() + " ")
            return original(*args, **kwargs)

        monkeypatch.setattr(recovery, "_plan", change_pinned_input)
    elif mutation == "during_write":
        write = BookkeepingTransaction.write_artifact

        def change_during_write(self: BookkeepingTransaction, path: Path, content: bytes) -> None:
            write(self, path, content)
            manifest.write_text(manifest.read_text() + " ")

        monkeypatch.setattr(BookkeepingTransaction, "write_artifact", change_during_write)
    else:

        def fail_commit(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("injected transaction failure")

        monkeypatch.setattr(BookkeepingTransaction, "commit", fail_commit)
    result = invoke_root(checkouts, proof_path)
    assert result.exit_code == 1, result.output
    after = state(checkouts)
    assert after[0] == before[0] and after[2:] == before[2:]
    if mutation != "refs":
        assert after[1] == before[1]
    assert not (checkouts.mission_dir / "recovery/owned-single-branch.json").exists()


def test_assume_unchanged_source_does_not_bypass_raw_qualification(preserved_owner: tuple[OwnedCheckouts, Path, Path]) -> None:
    checkouts, proof_path, _manifest = preserved_owner
    root = checkouts.owned_root
    _git(root, "update-index", "--assume-unchanged", "src/contract1.py")
    path = root / "src/contract1.py"
    path.write_bytes(b"hidden working source mutation")
    assert _git(root, "status", "--porcelain=v1") == ""
    before = state(checkouts)
    result = invoke_root(checkouts, proof_path, "--dry-run")
    assert result.exit_code == 1, result.output
    assert state(checkouts) == before
    assert path.read_bytes() == b"hidden working source mutation"


@pytest.mark.parametrize("mutation", ["workspace", "detached", "pid", "unknown_tip"])
def test_historical_activity_and_unknown_tip_refuse(preserved_owner: tuple[OwnedCheckouts, Path, Path], mutation: str) -> None:
    checkouts, proof_path, manifest = preserved_owner
    root = checkouts.owned_root
    proof = json.loads(proof_path.read_text())
    historical = proof["historical_refs"][0]
    if mutation == "detached":
        _git(root, "worktree", "add", "--detach", str(root.parent / "custody-active-detached"), historical["sha"])
    elif mutation == "unknown_tip":
        _git(root, "update-ref", historical["ref"].replace("-lane-a", "-lane-b"), historical["sha"])
    elif mutation == "workspace":
        branch = historical["ref"].removeprefix("refs/remotes/origin/")
        _git(root, "branch", branch, historical["sha"])
        proof["historical_refs"].append({"ref": "refs/heads/" + branch, "sha": historical["sha"]})
        _git(root, "worktree", "add", str(root.parent / "custody-historical-active"), branch)
        custody_manifest(checkouts, proof, manifest.parent)
        proof_path.write_text(json.dumps(proof))
        bind(proof_path, manifest)
    else:
        _git(root, "checkout", "--detach", historical["sha"])
        events = checkouts.mission_dir / "status.events.jsonl"
        rows = [json.loads(line) for line in events.read_text().splitlines()]
        rows[0]["policy_metadata"] = {"shell_pid": os.getpid()}
        events.write_text("".join(json.dumps(row) + "\n" for row in rows))
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "retained active historical process")
        historical["sha"] = _git(root, "rev-parse", "HEAD")
        _git(root, "update-ref", historical["ref"], historical["sha"])
        raw = events.read_bytes()
        _git(root, "checkout", checkouts.target_branch)
        (checkouts.mission_dir / proof["archived_status"]["path"]).write_bytes(raw)
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "preserve historical raw process state")
        proof["owner_head"] = _git(root, "rev-parse", "HEAD")
        custody_manifest(checkouts, proof, manifest.parent)
        proof_path.write_text(json.dumps(proof))
        bind(proof_path, manifest)
    before = state(checkouts)
    result = invoke_root(checkouts, proof_path, "--dry-run")
    assert result.exit_code == 1, result.output
    assert state(checkouts) == before


@pytest.mark.parametrize("history", ["merge_hidden", "intermediate_revert"])
@pytest.mark.parametrize("omission", ["none", "edge", "blob"])
def test_hidden_and_reverted_work_requires_complete_raw_custody(preserved_owner: tuple[OwnedCheckouts, Path, Path], history: str, omission: str) -> None:
    checkouts, proof_path, manifest = preserved_owner
    root = checkouts.owned_root
    proof = json.loads(proof_path.read_text())
    historical = proof["historical_refs"][0]
    tip = historical["sha"]
    _git(root, "checkout", "-b", "codex/fixture-intermediate", tip)
    path = root / "data/performance-manifest.json"
    original = path.read_bytes()
    path.write_bytes(b"intermediate historical version retained in custody\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "intermediate source work")
    intermediate = _git(root, "rev-parse", "HEAD")
    intermediate_oid = _git(root, "rev-parse", intermediate + ":data/performance-manifest.json")
    if history == "merge_hidden":
        _git(root, "checkout", "--detach", tip)
        _git(root, "merge", "--no-ff", "-s", "ours", "-m", "retain hidden history with unchanged final tree", "codex/fixture-intermediate")
    else:
        path.write_bytes(original)
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "restore final tree without losing history")
    historical["sha"] = _git(root, "rev-parse", "HEAD")
    _git(root, "update-ref", historical["ref"], historical["sha"])
    _git(root, "checkout", checkouts.target_branch)
    assert _git(root, "diff", "--quiet", tip, historical["sha"], "--", "data/performance-manifest.json") == ""
    custody_manifest(checkouts, proof, manifest.parent)
    proof_path.write_text(json.dumps(proof))
    data = json.loads(manifest.read_text())
    assert intermediate_oid in {row["oid"] for row in data["blobs"]}
    if omission == "edge":
        data["edges"] = [row for row in data["edges"] if row["commit"] != intermediate]
    elif omission == "blob":
        data["blobs"] = [row for row in data["blobs"] if row["oid"] != intermediate_oid]
    bind(proof_path, manifest, data)
    before = state(checkouts)
    result = invoke_root(checkouts, proof_path, "--dry-run")
    assert result.exit_code == (0 if omission == "none" else 1), result.output
    assert state(checkouts) == before


@pytest.mark.parametrize("mutation", ["mode", "symlink", "delete", "rename", "copy", "add"])
def test_unsupported_historical_source_changes_refuse(preserved_owner: tuple[OwnedCheckouts, Path, Path], mutation: str) -> None:
    checkouts, proof_path, manifest = preserved_owner
    root = checkouts.owned_root
    proof = json.loads(proof_path.read_text())
    historical = proof["historical_refs"][0]
    _git(root, "checkout", "--detach", historical["sha"])
    path = root / "data/performance-manifest.json"
    if mutation == "mode":
        path.chmod(0o755)
    elif mutation == "symlink":
        path.unlink()
        path.symlink_to("../src/contract1.py")
    elif mutation == "delete":
        path.unlink()
    elif mutation == "rename":
        _git(root, "mv", "data/performance-manifest.json", "data/renamed-projection.json")
    elif mutation == "copy":
        (root / "data/new-projection.json").write_bytes(path.read_bytes())
    else:
        (root / "data/new-projection.json").write_bytes(b"added source projection\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "unsupported historical change")
    historical["sha"] = _git(root, "rev-parse", "HEAD")
    _git(root, "update-ref", historical["ref"], historical["sha"])
    _git(root, "checkout", checkouts.target_branch)
    data = json.loads(manifest.read_text())
    if mutation in {"copy", "add"}:
        wp = checkouts.mission_dir / "tasks/WP01-owned.md"
        wp.write_text(wp.read_text().replace("data/performance-manifest.json", "data/performance-manifest.json, data/new-projection.json"))
        (root / "data/new-projection.json").write_bytes(b"current owned version\n")
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "explicit current ownership of added path")
        proof["owner_head"] = _git(root, "rev-parse", "HEAD")
        data["owner_head"] = proof["owner_head"]
        data["scope"] = sorted([*data["scope"], "data/new-projection.json"])
    if mutation == "mode":
        custody_manifest(checkouts, proof, manifest.parent)
        data = json.loads(manifest.read_text())
    proof_path.write_text(json.dumps(proof))
    bind(proof_path, manifest, data)
    before = state(checkouts)
    result = invoke_root(checkouts, proof_path, "--dry-run")
    assert result.exit_code == 1, result.output
    assert state(checkouts) == before
