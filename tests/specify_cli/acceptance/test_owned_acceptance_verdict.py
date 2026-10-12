"""Issue 59: the real verdict CLI commits only in the validated owning checkout."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.acceptance.matrix import AcceptanceCriterion, AcceptanceMatrix, NegativeInvariant, read_acceptance_matrix, write_acceptance_matrix
from specify_cli.cli.commands.agent.mission import app
from tests.integration.test_explicit_checkout_commands import SLUG, checkouts, git, snapshot
from tests.status.test_transition_request_owned import claim_counter

__all__ = ["checkouts", "claim_counter"]
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


@pytest.fixture
def matrix_checkouts(checkouts: tuple[Path, Path, Path]) -> tuple[Path, Path, Path]:
    _, owned, _ = checkouts
    write_acceptance_matrix(
        owned / "kitty-specs" / SLUG,
        AcceptanceMatrix(
            mission_slug=SLUG,
            criteria=[AcceptanceCriterion("FR-001", "Owned proof", "automated_test")],
            negative_invariants=[
                NegativeInvariant(
                    "NI-preserved",
                    "Established proof",
                    "custom_command",
                    "must-not-be-reexecuted",
                    result="confirmed_absent",
                    evidence="receipt://established",
                    verified_ref="original-proof-ref",
                    verified_surface_kind="primary",
                    provenance_origin="recorded",
                )
            ],
        ),
    )
    git(owned, "add", ".")
    git(owned, "commit", "-qm", "fixture: authored matrix")
    return checkouts


def verdict(owned: Path, *args: str, explicit: bool = True):
    flags = ["--owned-checkout", str(owned)] if explicit else []
    return CliRunner().invoke(app, ["acceptance-verdict", "--mission", SLUG, *flags, "--json", *args])


@pytest.mark.parametrize("caller", [0, 1, 2], ids=["primary", "owner", "sibling"])
def test_owner_only_commit_and_idempotence(matrix_checkouts, monkeypatch, claim_counter, caller):
    primary, owned, sibling = matrix_checkouts
    monkeypatch.chdir(matrix_checkouts[caller])
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(matrix_checkouts[caller]))
    before = snapshot(primary), snapshot(sibling)
    original_head = git(owned, "rev-parse", "HEAD")
    original_matrix = read_acceptance_matrix(owned / "kitty-specs" / SLUG)
    assert original_matrix is not None
    claim_counter.clear()
    result = verdict(owned, "--criterion", "FR-001", "--result", "pass", "--actor", "reviewer", "--evidence", "receipt://real")
    assert result.exit_code == 0, result.output
    assert len(claim_counter) == 1
    assert json.loads(result.output)["success"] is True
    assert git(owned, "rev-parse", "HEAD") != original_head
    assert git(owned, "show", "--format=", "--name-only", "HEAD") == f"kitty-specs/{SLUG}/acceptance-matrix.json"
    after = snapshot(owned)
    repeated = verdict(owned, "--criterion", "FR-001", "--result", "pass", "--actor", "reviewer", "--evidence", "receipt://real")
    assert repeated.exit_code == 0, repeated.output
    assert snapshot(owned) == after
    assert (snapshot(primary), snapshot(sibling)) == before
    assert git(owned, "status", "--porcelain") == ""
    actual_matrix = read_acceptance_matrix(owned / "kitty-specs" / SLUG)
    assert actual_matrix is not None and actual_matrix.negative_invariants == original_matrix.negative_invariants


def test_flagless_owner_adoption(matrix_checkouts, claim_counter):
    primary, owned, sibling = matrix_checkouts
    before = snapshot(primary), snapshot(sibling)
    claim_counter.clear()
    result = verdict(owned, "--criterion", "FR-001", "--result", "fail", explicit=False)
    assert result.exit_code == 0, result.output
    assert len(claim_counter) == 1
    matrix = read_acceptance_matrix(owned / "kitty-specs" / SLUG)
    assert matrix is not None and matrix.criteria[0].pass_fail == "fail"
    assert (snapshot(primary), snapshot(sibling)) == before


def test_invariant_executes_in_owner_not_primary(matrix_checkouts, monkeypatch):
    primary, owned, sibling = matrix_checkouts
    (owned / "owner-only.md").write_text("bound owner\n", encoding="utf-8")
    git(owned, "add", ".")
    git(owned, "commit", "-qm", "fixture: owner-only check input")
    before = snapshot(primary), snapshot(sibling)
    monkeypatch.chdir(primary)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(primary))
    result = verdict(
        owned,
        "--negative-invariant",
        "NI-001",
        "--description",
        "Owner check",
        "--verification-method",
        "custom_command",
        "--verification-command",
        "git ls-files --error-unmatch owner-only.md",
    )
    assert result.exit_code == 0, result.output
    matrix = read_acceptance_matrix(owned / "kitty-specs" / SLUG)
    assert matrix is not None
    judged = next(row for row in matrix.negative_invariants if row.invariant_id == "NI-001")
    assert judged.result == "confirmed_absent"
    assert matrix.negative_invariants[0].verified_ref == "original-proof-ref"
    assert (snapshot(primary), snapshot(sibling)) == before


@pytest.mark.parametrize("claim", [0, 2], ids=["repository-root", "non-owner-sibling"])
def test_refusal_is_structured_and_zero_write(matrix_checkouts, claim):
    before = tuple(snapshot(root) for root in matrix_checkouts)
    result = verdict(matrix_checkouts[claim], "--criterion", "FR-001", "--result", "pass")
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"]
    assert tuple(snapshot(root) for root in matrix_checkouts) == before


@pytest.mark.parametrize("topology", ["lanes", "coord", "lanes_with_coord"])
def test_unsupported_owned_topology_has_no_effects(matrix_checkouts, topology):
    _, owned, _ = matrix_checkouts
    meta = owned / "kitty-specs" / SLUG / "meta.json"
    payload = json.loads(meta.read_text())
    payload["topology"] = topology
    meta.write_text(json.dumps(payload), encoding="utf-8")
    before = tuple(snapshot(root) for root in matrix_checkouts)
    result = verdict(owned, "--criterion", "FR-001", "--result", "pass")
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_TOPOLOGY_UNSUPPORTED"
    assert tuple(snapshot(root) for root in matrix_checkouts) == before


def test_foreign_claim_refuses_before_invariant_execution(matrix_checkouts, tmp_path):
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    git(foreign, "init", "-qb", "main")
    before = tuple(snapshot(root) for root in matrix_checkouts)
    result = verdict(
        foreign,
        "--negative-invariant",
        "NI-001",
        "--description",
        "must not execute",
        "--verification-method",
        "custom_command",
        "--verification-command",
        "touch forbidden.md",
    )
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNERSHIP_FOREIGN"
    assert not (foreign / "forbidden.md").exists()
    assert tuple(snapshot(root) for root in matrix_checkouts) == before


@pytest.mark.parametrize("explicit", [True, False], ids=["explicit", "adopted"])
def test_primary_identity_conflict_follows_canonical_claim_contract(matrix_checkouts, explicit):
    primary, owned, _ = matrix_checkouts
    shadow = primary / "kitty-specs" / SLUG
    shutil.copytree(owned / "kitty-specs" / SLUG, shadow)
    meta = shadow / "meta.json"
    payload = json.loads(meta.read_text())
    payload["mission_id"] = "01M1A900000000000000000002"
    meta.write_text(json.dumps(payload), encoding="utf-8")
    before = tuple(snapshot(root) for root in matrix_checkouts)
    result = verdict(owned, "--criterion", "FR-001", "--result", "pass", explicit=explicit)
    if explicit:
        # An explicit claim chooses P's own identity; unlike adoption, it
        # does not let R's unrelated same-slug mission override the selection.
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["stale_repository_root_copy"] is None
        assert (snapshot(primary), snapshot(matrix_checkouts[2])) == (before[0], before[2])
    else:
        assert result.exit_code == 1, result.output
        assert json.loads(result.output)["error_code"] == "MISSION_CONTEXT_CONFLICT"
        assert tuple(snapshot(root) for root in matrix_checkouts) == before


def test_same_identity_shadow_is_reported_and_preserved(matrix_checkouts):
    primary, owned, sibling = matrix_checkouts
    shadow = primary / "kitty-specs" / SLUG
    shutil.copytree(owned / "kitty-specs" / SLUG, shadow)
    before = snapshot(primary), snapshot(sibling)
    result = verdict(owned, "--criterion", "FR-001", "--result", "pass")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["stale_repository_root_copy"]["path"] == str(shadow)
    assert (snapshot(primary), snapshot(sibling)) == before


@pytest.mark.parametrize("problem", ["missing-matrix", "missing-selector", "missing-criterion"])
def test_missing_inputs_fail_closed(matrix_checkouts, problem):
    _, owned, _ = matrix_checkouts
    args = ["acceptance-verdict", "--mission", SLUG, "--owned-checkout", str(owned), "--json", "--criterion", "FR-001", "--result", "pass"]
    if problem == "missing-matrix":
        (owned / "kitty-specs" / SLUG / "acceptance-matrix.json").unlink()
    elif problem == "missing-selector":
        args[2] = "absent-01M1A901"
    else:
        args[-3] = "FR-999"
    before = tuple(snapshot(root) for root in matrix_checkouts)
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["success"] is False
    assert tuple(snapshot(root) for root in matrix_checkouts) == before


@pytest.mark.parametrize("kind", ["coord", "lane"])
def test_registered_mission_worktrees_are_not_owned_claims(matrix_checkouts, kind):
    from specify_cli.lanes.models import ExecutionLane, LanesManifest
    from specify_cli.lanes.persistence import write_lanes_json
    from specify_cli.lanes.worktree_allocator import predict_lane_worktree

    primary, owned, _ = matrix_checkouts
    if kind == "coord":
        claimed = primary / ".worktrees" / f"{SLUG}-coord"
        branch = "codex/coord"
    else:
        shadow = primary / "kitty-specs" / SLUG
        shutil.copytree(owned / "kitty-specs" / SLUG, shadow)
        mission_id = json.loads((shadow / "meta.json").read_text())["mission_id"]
        write_lanes_json(
            shadow,
            LanesManifest(
                version=1,
                mission_slug=SLUG,
                mission_id=mission_id,
                mission_branch=f"kitty/mission-{SLUG}",
                target_branch="codex/owned",
                lanes=[ExecutionLane(lane_id="lane-a", wp_ids=("WP01",), write_scope=(), predicted_surfaces=(), depends_on_lanes=(), parallel_group=0)],
                computed_at="2026-10-10T00:00:00Z",
                computed_from="test",
            ),
        )
        claimed, branch = predict_lane_worktree(primary, SLUG, "lane-a")
    git(primary, "worktree", "add", "-qb", branch, str(claimed))
    before = tuple(snapshot(root) for root in (*matrix_checkouts, claimed))
    result = verdict(claimed, "--criterion", "FR-001", "--result", "pass")
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_CHECKOUT_IS_MISSION_WORKTREE"
    assert tuple(snapshot(root) for root in (*matrix_checkouts, claimed)) == before


def test_human_output_reports_stale_copy(matrix_checkouts):
    primary, owned, sibling = matrix_checkouts
    shutil.copytree(owned / "kitty-specs" / SLUG, primary / "kitty-specs" / SLUG)
    before = snapshot(primary), snapshot(sibling)
    result = CliRunner().invoke(app, ["acceptance-verdict", "--mission", SLUG, "--owned-checkout", str(owned), "--criterion", "FR-001", "--result", "pass"])
    assert result.exit_code == 0, result.output
    assert "stale copy" in result.output
    assert (snapshot(primary), snapshot(sibling)) == before
