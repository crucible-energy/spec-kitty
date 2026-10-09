"""Issue 85: explicit recovery preserves source, state and distinct review bases."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app as mission_app
from specify_cli.cli.commands.migrate_cmd import app as migrate_app
from specify_cli.core.owned_mission import LIFECYCLE_OWNED_TOPOLOGIES, resolve_owned_mission
from specify_cli.lanes.persistence import read_lanes_json, write_lanes_json
from specify_cli.status.bootstrap import bootstrap_canonical_state
from specify_cli.status import TransitionRequest, emit_status_transition, write_checkout_claim_lock
from tests._owned_fixtures import RSnapshotter
from tests.integration.conftest import OwnedCheckouts, _git

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


@pytest.mark.parametrize("branch", ["kitty/mission-example-01M1ZYYJ", "kitty/mission-007-example", "kitty/mission-example"])
@pytest.mark.parametrize("namespace", ["refs/heads/", "refs/remotes/origin/", "refs/spec-kitty/lane-tip/"])
def test_historical_ref_recognition_uses_canonical_identity(branch: str, namespace: str) -> None:
    from specify_cli.migration.owned_single_branch_proof import _mission_ref

    assert _mission_ref(namespace + branch, branch)
    assert _mission_ref(namespace + branch + "-lane-a", branch)
    assert not _mission_ref(namespace + branch + "-lane-a-extra", branch)
    assert not _mission_ref(namespace + branch + "-other-lane-a", branch)
    assert not _mission_ref("refs/tags/" + branch, branch)
    assert not _mission_ref(namespace + branch, branch + "-lane-a")


@pytest.fixture
def recovery_owner(make_owned_checkouts: Callable[..., OwnedCheckouts], monkeypatch: pytest.MonkeyPatch) -> tuple[OwnedCheckouts, Path]:
    checkouts = make_owned_checkouts(wp_ids=("WP01", "WP02", "WP03", "WP04", "WP05"))
    root, dossier = checkouts.owned_root, checkouts.mission_dir
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    monkeypatch.chdir(root)
    _git(root, "worktree", "add", "--detach", str(root.parent / "unrelated-detached"), _git(checkouts.repository_root, "rev-parse", "HEAD"))
    (root / "src").mkdir()
    (dossier / "tasks.md").write_text("# Tasks\n\n" + "\n".join(f"## WP{i:02}\n\nNo dependencies.\n" for i in range(1, 6)))
    for index in range(1, 6):
        wp = f"WP{index:02}"
        source = f"src/contract{index}.py"
        (root / source).write_text("inherited source\n")
        path = dossier / "tasks" / f"{wp}-owned.md"
        path.write_text(
            path.read_text().replace("owned_files: []", f"owned_files: [{source}]").replace("authoritative_surface: app.py", f"authoritative_surface: {source}")
        )
    owned = resolve_owned_mission(checkouts.repository_root, root, checkouts.mission_slug, allowed_topologies=LIFECYCLE_OWNED_TOPOLOGIES)
    with write_checkout_claim_lock(root):
        pass  # Current WP claim serialization already exists in the real recovery case.
    bootstrap_canonical_state(dossier, checkouts.mission_slug, repo_root=checkouts.repository_root, owned=owned)
    for lane in ("claimed", "in_progress"):
        emit_status_transition(
            TransitionRequest(
                mission_dir=dossier,
                mission_slug=checkouts.mission_slug,
                repo_root=checkouts.repository_root,
                wp_id="WP01",
                to_lane=lane,
                actor="test-implementer",
                execution_mode="direct_repo",
                owned=owned,
            ),
            fan_out=False,
        )
    manifest = read_lanes_json(dossier)
    assert manifest is not None
    manifest.lanes[0] = replace(manifest.lanes[0], lane_id="lane-a", write_scope=tuple(f"src/contract{i}.py" for i in range(1, 6)))
    write_lanes_json(dossier, manifest)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "historical execution base")
    historical_base = _git(root, "rev-parse", "HEAD")
    (dossier / "historical-planning.md").write_text("historical planning and review state\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "historical state only")
    historical_tip = _git(root, "rev-parse", "HEAD")
    branch = manifest.mission_branch
    historical_ref = f"refs/remotes/origin/{branch}-lane-a"
    _git(root, "update-ref", historical_ref, historical_tip)
    # Current reviewed source intentionally differs from the inherited snapshot.
    (root / "src/contract1.py").write_text("current reviewed source\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "current reviewed planning baseline")
    planning_pin = _git(root, "rev-parse", "HEAD")
    manifest.planning_commit_sha = planning_pin
    write_lanes_json(dossier, manifest)
    archive = dossier / "research/historical-status.jsonl"
    archive.parent.mkdir()
    archive.write_bytes((dossier / "status.events.jsonl").read_bytes())
    claim_ref = f"refs/spec-kitty/wp-base/{checkouts.mission_slug}/WP01"
    _git(root, "update-ref", claim_ref, planning_pin)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "preserved recovery evidence")
    proof = dossier / "recovery-proof.json"
    proof.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "owner_head": _git(root, "rev-parse", "HEAD"),
                "planning_commit_sha": planning_pin,
                "historical_base": historical_base,
                "historical_refs": [{"ref": historical_ref, "sha": historical_tip}],
                "archived_status": {"ref": historical_ref, "path": "research/historical-status.jsonl"},
                "claim_refs": {claim_ref: planning_pin},
            }
        )
    )
    # Proof is an explicit input; keeping it outside the checkout avoids a self-pinning HEAD.
    external = root.parent / "recovery-proof.json"
    external.write_bytes(proof.read_bytes())
    proof.unlink()
    return checkouts, external


def invoke(checkouts: OwnedCheckouts, proof: Path, *args: str) -> Any:
    return CliRunner().invoke(
        migrate_app,
        ["owned-single-branch", "--mission", checkouts.mission_slug, "--owned-checkout", str(checkouts.owned_root), "--proof", str(proof), "--json", *args],
    )


def state(checkouts: OwnedCheckouts) -> tuple[str, str, bytes, bytes]:
    root, dossier = checkouts.owned_root, checkouts.mission_dir
    return (
        _git(root, "rev-parse", "HEAD"),
        _git(root, "for-each-ref", "--format=%(refname) %(objectname)"),
        (dossier / "lanes.json").read_bytes(),
        (dossier / "status.events.jsonl").read_bytes(),
    )


def test_real_cli_dry_run_conversion_idempotency_and_plain_finalize(
    recovery_owner: tuple[OwnedCheckouts, Path], make_r_snapshot: Callable[[OwnedCheckouts], RSnapshotter]
) -> None:
    checkouts, proof = recovery_owner
    before = state(checkouts)
    snapshotter = make_r_snapshot(checkouts)
    shared_before = snapshotter.take()
    sibling_before = (
        _git(checkouts.sibling, "rev-parse", "HEAD"),
        _git(checkouts.sibling, "ls-files", "--stage"),
        _git(checkouts.sibling, "status", "--porcelain=v1"),
    )
    primary = _git(checkouts.repository_root, "status", "--porcelain=v1")
    dry = invoke(checkouts, proof, "--dry-run")
    assert dry.exit_code == 0, dry.output
    assert json.loads(dry.output)["result"] == "would_convert"
    assert state(checkouts) == before
    snapshotter.assert_unchanged(shared_before, snapshotter.take())
    result = invoke(checkouts, proof)
    assert result.exit_code == 0, result.output
    manifest = read_lanes_json(checkouts.mission_dir)
    assert manifest is not None
    assert manifest.lanes[0].lane_id == "lane-planning"
    assert manifest.lanes[0].wp_ids == ("WP01", "WP02", "WP03", "WP04", "WP05")
    assert manifest.planning_commit_sha == json.loads(proof.read_text())["planning_commit_sha"]
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == before[3]
    after = state(checkouts)
    repeated = invoke(checkouts, proof)
    assert repeated.exit_code == 0, repeated.output
    assert json.loads(repeated.output)["result"] == "already_converted"
    assert state(checkouts) == after
    snapshotter.assert_unchanged(shared_before, snapshotter.take(), tolerate_status_mutex_for=checkouts.mission_slug)
    assert (
        _git(checkouts.sibling, "rev-parse", "HEAD"),
        _git(checkouts.sibling, "ls-files", "--stage"),
        _git(checkouts.sibling, "status", "--porcelain=v1"),
    ) == sibling_before
    final = CliRunner().invoke(mission_app, ["finalize-tasks", "--mission", checkouts.mission_slug, "--owned-checkout", str(checkouts.owned_root), "--json"])
    assert final.exit_code == 0, final.output
    assert read_lanes_json(checkouts.mission_dir).planning_commit_sha == manifest.planning_commit_sha
    assert _git(checkouts.repository_root, "status", "--porcelain=v1") == primary


@pytest.mark.parametrize(
    "mutation", ["source_commit", "archive", "unknown_ref", "workspace", "detached_workspace", "process", "proof", "branch", "planning_pin", "claim_ref"]
)
def test_refusal_preserves_owner_and_shared_refs(recovery_owner: tuple[OwnedCheckouts, Path], mutation: str) -> None:
    checkouts, proof_path = recovery_owner
    root, dossier = checkouts.owned_root, checkouts.mission_dir
    proof = json.loads(proof_path.read_text())
    historical = proof["historical_refs"][0]
    if mutation in {"source_commit", "process"}:
        _git(root, "checkout", "--detach", historical["sha"])
        if mutation == "source_commit":
            (root / "src/contract1.py").write_text("unabsorbed historical source\n")
        else:
            import os

            events = dossier / "status.events.jsonl"
            rows = [json.loads(row) for row in events.read_text().splitlines()]
            rows[0]["policy_metadata"] = {"shell_pid": os.getpid()}
            events.write_text("".join(json.dumps(row) + "\n" for row in rows))
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "unsafe historical evidence")
        historical["sha"] = _git(root, "rev-parse", "HEAD")
        _git(root, "update-ref", historical["ref"], historical["sha"])
        content = _git(root, "show", historical["sha"] + ":" + dossier.relative_to(root).as_posix() + "/status.events.jsonl") + "\n"
        _git(root, "checkout", checkouts.target_branch)
        (dossier / proof["archived_status"]["path"]).write_text(content)
        if _git(root, "status", "--porcelain=v1"):
            _git(root, "add", ".")
            _git(root, "commit", "-qm", "preserve unsafe historical evidence")
        proof["owner_head"] = _git(root, "rev-parse", "HEAD")
    elif mutation == "archive":
        (dossier / proof["archived_status"]["path"]).write_text("incomplete archive\n")
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "incomplete archive")
        proof["owner_head"] = _git(root, "rev-parse", "HEAD")
    elif mutation == "unknown_ref":
        _git(root, "update-ref", historical["ref"].replace("-lane-a", "-lane-b"), historical["sha"])
    elif mutation == "workspace":
        branch = historical["ref"].removeprefix("refs/remotes/origin/")
        _git(root, "branch", branch, historical["sha"])
        proof["historical_refs"].append({"ref": "refs/heads/" + branch, "sha": historical["sha"]})
        _git(root, "worktree", "add", str(root.parent / "historical-active"), branch)
    elif mutation == "detached_workspace":
        _git(root, "worktree", "add", "--detach", str(root.parent / "historical-detached"), historical["sha"])
    elif mutation == "proof":
        proof["invented_approval"] = True
    elif mutation == "branch":
        _git(root, "checkout", "-b", "codex/wrong")
    elif mutation == "planning_pin":
        proof["planning_commit_sha"] = proof["historical_base"]
    else:
        claim = next(iter(proof["claim_refs"]))
        _git(root, "update-ref", claim, proof["historical_base"])
    proof_path.write_text(json.dumps(proof))
    before = state(checkouts)
    result = invoke(checkouts, proof_path, "--dry-run")
    assert result.exit_code == 1, result.output
    assert state(checkouts) == before
    assert not (dossier / "recovery/owned-single-branch.json").exists()


def test_proof_change_under_locks_refuses_before_writes(recovery_owner: tuple[OwnedCheckouts, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.migration import owned_single_branch as recovery

    checkouts, proof = recovery_owner
    original_plan = recovery._plan
    calls = 0

    def change_proof(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        plan = original_plan(*args, **kwargs)
        calls += 1
        if calls == 2:
            proof.write_text(proof.read_text() + " ")
        return plan

    monkeypatch.setattr(recovery, "_plan", change_proof)
    before = state(checkouts)
    result = invoke(checkouts, proof)
    assert result.exit_code == 1
    assert state(checkouts) == before
    assert not (checkouts.mission_dir / "recovery/owned-single-branch.json").exists()


def test_transaction_failure_rolls_back_exact_bytes(recovery_owner: tuple[OwnedCheckouts, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.coordination.transaction import BookkeepingTransaction

    checkouts, proof = recovery_owner
    before = state(checkouts)

    def refuse_commit(self: BookkeepingTransaction, message: str) -> None:
        raise RuntimeError("injected commit failure after artifact writes")

    monkeypatch.setattr(BookkeepingTransaction, "commit", refuse_commit)
    result = invoke(checkouts, proof)
    assert result.exit_code == 1, result.output
    assert state(checkouts) == before
    assert not (checkouts.mission_dir / "recovery/owned-single-branch.json").exists()


@pytest.mark.parametrize("mutation", ["duplicate", "nested_duplicate", "secret", "boolean_version", "nonfinite", "oversized_proof"])
def test_closed_proof_refusal_never_echoes_input(recovery_owner: tuple[OwnedCheckouts, Path], mutation: str) -> None:
    checkouts, proof = recovery_owner
    text = proof.read_text()
    sentinel = "SECRET_SENTINEL_MUST_NOT_APPEAR"
    if mutation == "duplicate":
        text = text.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
    elif mutation == "nested_duplicate":
        text = text.replace('"path":', '"path": "' + sentinel + '", "path":')
    elif mutation == "boolean_version":
        text = text.replace('"schema_version": 1', '"schema_version": true')
    elif mutation == "nonfinite":
        text = text.replace('"schema_version": 1', '"schema_version": NaN')
    elif mutation == "oversized_proof":
        text += " " * 65_537
    else:
        text = text[:-1] + ', "unknown": "' + sentinel + '"}'
    proof.write_text(text)
    before = state(checkouts)
    result = invoke(checkouts, proof, "--dry-run")
    assert result.exit_code == 1
    assert sentinel not in result.output
    assert json.loads(result.output)["error_code"] == "OWNED_RECOVERY_REFUSED"
    assert state(checkouts) == before


@pytest.mark.parametrize("mutation", ["owner_head", "dirty", "membership", "manifest_target", "duplicate_wp", "ownership"])
def test_frozen_ownership_refusals_preserve_work(recovery_owner: tuple[OwnedCheckouts, Path], mutation: str) -> None:
    checkouts, proof_path = recovery_owner
    root, dossier = checkouts.owned_root, checkouts.mission_dir
    proof = json.loads(proof_path.read_text())
    if mutation == "owner_head":
        proof["owner_head"] = proof["historical_base"]
    elif mutation == "dirty":
        (root / "untracked-user-work").write_text("preserve this work\n")
    else:
        if mutation in {"membership", "manifest_target"}:
            manifest = read_lanes_json(dossier)
            assert manifest is not None
            if mutation == "membership":
                manifest.lanes[0] = replace(manifest.lanes[0], wp_ids=("WP01", "WP02", "WP03", "WP04"))
            else:
                manifest.target_branch = "codex/wrong-target"
            write_lanes_json(dossier, manifest)
        elif mutation == "duplicate_wp":
            path = dossier / "tasks/WP05-owned.md"
            path.write_text(path.read_text().replace("work_package_id: WP05", "work_package_id: WP01"))
        else:
            path = dossier / "tasks/WP01-owned.md"
            path.write_text(path.read_text().replace("owned_files: [src/contract1.py]", "owned_files: [src/missing.py]"))
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "unsafe ownership evidence")
        proof["owner_head"] = _git(root, "rev-parse", "HEAD")
    proof_path.write_text(json.dumps(proof))
    before = state(checkouts)
    result = invoke(checkouts, proof_path, "--dry-run")
    assert result.exit_code == 1
    assert state(checkouts) == before


@pytest.mark.parametrize("mutation", ["unqualified", "proof_identity", "manifest", "dirty"])
def test_idempotency_requires_qualified_unchanged_receipt(recovery_owner: tuple[OwnedCheckouts, Path], mutation: str) -> None:
    checkouts, proof = recovery_owner
    result = invoke(checkouts, proof)
    assert result.exit_code == 0, result.output
    root, dossier = checkouts.owned_root, checkouts.mission_dir
    receipt_path = dossier / "recovery/owned-single-branch.json"
    if mutation == "unqualified":
        receipt_path.write_text(receipt_path.read_text() + " ")
    elif mutation == "proof_identity":
        receipt = json.loads(receipt_path.read_text())
        receipt["proof_sha256"] = "wrong qualification"
        receipt_path.write_text(json.dumps(receipt))
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "altered receipt qualification")
    elif mutation == "manifest":
        manifest = read_lanes_json(dossier)
        assert manifest is not None
        manifest.computed_from = "changed after conversion"
        write_lanes_json(dossier, manifest)
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "changed converted manifest")
    else:
        (root / "untracked-user-work").write_text("preserve this work\n")
    before = state(checkouts)
    result = invoke(checkouts, proof)
    assert result.exit_code == 1
    assert state(checkouts) == before


def test_merge_hidden_source_commit_refuses(recovery_owner: tuple[OwnedCheckouts, Path]) -> None:
    checkouts, proof_path = recovery_owner
    root = checkouts.owned_root
    proof = json.loads(proof_path.read_text())
    historical = proof["historical_refs"][0]
    _git(root, "checkout", "-b", "historical-source", historical["sha"])
    (root / "src/contract1.py").write_text("source commit hidden by ours merge\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "post-base historical source work")
    source_tip = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--detach", historical["sha"])
    _git(root, "merge", "--no-ff", "-s", "ours", source_tip, "-m", "merge hides source in final tree")
    historical["sha"] = _git(root, "rev-parse", "HEAD")
    _git(root, "update-ref", historical["ref"], historical["sha"])
    _git(root, "checkout", checkouts.target_branch)
    proof_path.write_text(json.dumps(proof))
    assert _git(root, "diff", "--quiet", proof["historical_base"], historical["sha"], "--", "src/contract1.py") == ""
    assert _git(root, "log", "--format=%H", proof["historical_base"] + ".." + historical["sha"], "--", "src/contract1.py") == ""
    before = state(checkouts)
    result = invoke(checkouts, proof_path, "--dry-run")
    assert result.exit_code == 1
    assert state(checkouts) == before


def test_oversized_immutable_blob_refuses_before_content_read(recovery_owner: tuple[OwnedCheckouts, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel.git import listing

    checkouts, proof_path = recovery_owner
    root, dossier = checkouts.owned_root, checkouts.mission_dir
    proof = json.loads(proof_path.read_text())
    historical = proof["historical_refs"][0]
    _git(root, "checkout", "--detach", historical["sha"])
    (dossier / "status.events.jsonl").write_bytes(b"x" * (8_388_608 + 1))
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "oversized historical state")
    historical["sha"] = _git(root, "rev-parse", "HEAD")
    source = dossier.relative_to(root).as_posix() + "/status.events.jsonl"
    oversized_oid = _git(root, "rev-parse", historical["sha"] + ":" + source)
    _git(root, "update-ref", historical["ref"], historical["sha"])
    _git(root, "checkout", checkouts.target_branch)
    proof_path.write_text(json.dumps(proof))
    original = listing.run_git
    content_reads: list[str] = []

    def observe(cwd: Path, *args: str, **kwargs: Any) -> Any:
        if args[:3] == ("cat-file", "blob", oversized_oid):
            content_reads.append(oversized_oid)
        return original(cwd, *args, **kwargs)

    monkeypatch.setattr(listing, "run_git", observe)
    before = state(checkouts)
    result = invoke(checkouts, proof_path, "--dry-run")
    assert result.exit_code == 1
    assert content_reads == []
    assert state(checkouts) == before
