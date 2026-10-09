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
from tests.integration.conftest import OwnedCheckouts, _git

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection]


@pytest.fixture
def recovery_owner(make_owned_checkouts: Callable[..., OwnedCheckouts], monkeypatch: pytest.MonkeyPatch) -> tuple[OwnedCheckouts, Path]:
    checkouts = make_owned_checkouts(wp_ids=("WP01", "WP02", "WP03", "WP04", "WP05"))
    root, dossier = checkouts.owned_root, checkouts.mission_dir
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    monkeypatch.chdir(root)
    (root / "src").mkdir()
    for index in range(1, 6):
        wp = f"WP{index:02}"
        source = f"src/contract{index}.py"
        (root / source).write_text("inherited source\n")
        path = dossier / "tasks" / f"{wp}-owned.md"
        path.write_text(
            path.read_text().replace("owned_files: []", f"owned_files: [{source}]").replace("authoritative_surface: app.py", f"authoritative_surface: {source}")
        )
    owned = resolve_owned_mission(checkouts.repository_root, root, checkouts.mission_slug, allowed_topologies=LIFECYCLE_OWNED_TOPOLOGIES)
    bootstrap_canonical_state(dossier, checkouts.mission_slug, repo_root=checkouts.repository_root, owned=owned)
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


def test_real_cli_dry_run_conversion_idempotency_and_plain_finalize(recovery_owner: tuple[OwnedCheckouts, Path]) -> None:
    checkouts, proof = recovery_owner
    before = state(checkouts)
    primary = _git(checkouts.repository_root, "status", "--porcelain=v1")
    dry = invoke(checkouts, proof, "--dry-run")
    assert dry.exit_code == 0, dry.output
    assert json.loads(dry.output)["result"] == "would_convert"
    assert state(checkouts) == before
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
    final = CliRunner().invoke(mission_app, ["finalize-tasks", "--mission", checkouts.mission_slug, "--owned-checkout", str(checkouts.owned_root), "--json"])
    assert final.exit_code == 0, final.output
    assert read_lanes_json(checkouts.mission_dir).planning_commit_sha == manifest.planning_commit_sha
    assert _git(checkouts.repository_root, "status", "--porcelain=v1") == primary
