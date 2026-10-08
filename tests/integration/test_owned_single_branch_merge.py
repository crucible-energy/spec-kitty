"""Local single-branch completion uses genuine owned approval and acceptance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.acceptance.matrix import (
    read_acceptance_matrix,
    write_and_commit_acceptance_matrix,
)
from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.cli.commands.merge import merge
from tests.integration.test_explicit_checkout_commands import (
    SLUG,
    TARGET,
    checkouts,
    git,
    mission_app,
    run_owned_accept,
    snapshot,
)
from tests.specify_cli.cli.commands.agent.test_owned_checkout_move_task import (
    _advance_owned_work_to_review,
    finalized_checkouts,
)

__all__ = ["checkouts", "finalized_checkouts"]
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
merge_app = typer.Typer()
merge_app.command("merge")(merge)


@pytest.fixture
def accepted_checkouts(finalized_checkouts: tuple[Path, Path, Path]) -> tuple[Path, Path, Path]:
    primary, owned, _sibling = finalized_checkouts
    meta_path = owned / "kitty-specs" / SLUG / "meta.json"
    meta = json.loads(meta_path.read_text())
    meta.update(created_at="2026-10-08T18:00:00Z", friendly_name="Owned completion fixture")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    git(owned, "add", str(meta_path))
    git(owned, "commit", "-qm", "fixture: complete mission identity")
    mission = _advance_owned_work_to_review(owned)
    (mission / "contracts").mkdir()
    (mission / "contracts/.gitkeep").touch()
    for directory in ("src", "tests", "docs"):
        (owned / directory).mkdir()
        (owned / directory / ".gitkeep").touch()
    git(owned, "add", ".")
    git(owned, "commit", "-qm", "fixture: completed contract inputs")
    for lane, extra in (
        ("in_review", []),
        ("approved", ["--approval-ref", "local-review"]),
    ):
        result = CliRunner().invoke(tasks_app, [
            "move-task", "WP01", "--to", lane, "--reviewer", "reviewer",
            "--mission", SLUG, "--owned-checkout", str(owned), "--json", *extra,
        ])
        assert result.exit_code == 0, result.output
    matrix = read_acceptance_matrix(mission)
    assert matrix is not None and matrix.criteria
    for criterion in matrix.criteria:
        criterion.pass_fail = "pass"
        criterion.evidence = "Public fixture asserts selected-checkout preservation"
        criterion.verified_by = "reviewer"
        criterion.verified_at = "2026-10-08T18:00:00Z"
    write_and_commit_acceptance_matrix(
        primary, SLUG, mission, matrix, entry_id="fixture-owned-acceptance",
        message="fixture: reviewed acceptance evidence", effective_root=owned,
    )
    accepted = run_owned_accept(owned, SLUG, "--actor", "fixture-operator", "--mode", "pr")
    assert accepted.exit_code == 0, accepted.output
    assert git(owned, "status", "--porcelain") == ""
    return finalized_checkouts


def invoke_merge(owned: Path, *extra: str, agent: bool = False):
    app = mission_app if agent else merge_app
    return CliRunner().invoke(app, [
        "merge", "--mission", SLUG, "--owned-checkout", str(owned), "--json", *extra,
    ])


def test_owned_preview_is_read_only_and_binds_real_target(accepted_checkouts):
    _primary, owned, _sibling = accepted_checkouts
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned, "--dry-run")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["integration"] == {
        "branch": TARGET, "commit": before[1][0], "kind": "local_target_ref",
    }
    assert payload["consolidation"] == "already_on_target"
    assert payload["remote_delivery"] == "separate_operator_gate"
    assert tuple(snapshot(root) for root in accepted_checkouts) == before


@pytest.mark.parametrize("agent", [False, True])
def test_owned_completion_retains_review_and_preserves_dirty_other_checkouts(accepted_checkouts, agent):
    primary, owned, sibling = accepted_checkouts
    for other in (primary, sibling):
        (other / "app.py").write_text("protected dirty sentinel\n", encoding="utf-8")
    before = snapshot(primary), snapshot(sibling)
    source_commit = git(owned, "rev-parse", "HEAD")
    refs = git(owned, "for-each-ref", "--format=%(refname)")
    result = invoke_merge(owned, agent=agent)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["completed_wps"] == ["WP01"]
    assert payload["integration"]["commit"] == source_commit
    state = json.loads((owned / "kitty-specs" / SLUG / "status.json").read_text())["work_packages"]["WP01"]
    assert state["lane"] == "done"
    assert state["review_result"]["reviewer"] == "reviewer"
    assert state["evidence"]["repos"][0]["commit"] == source_commit
    assert state["evidence"]["review"]["reference"] == state["review_result"]["reference"]
    assert git(owned, "status", "--porcelain") == ""
    assert git(owned, "for-each-ref", "--format=%(refname)") == refs
    assert (snapshot(primary), snapshot(sibling)) == before
