"""Issue 59: the real verdict CLI commits only in the validated owning checkout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.acceptance.matrix import AcceptanceCriterion, AcceptanceMatrix, read_acceptance_matrix, write_acceptance_matrix
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
        AcceptanceMatrix(mission_slug=SLUG, criteria=[AcceptanceCriterion("FR-001", "Owned proof", "automated_test")]),
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
    assert matrix.negative_invariants[0].result == "confirmed_absent"
    assert (snapshot(primary), snapshot(sibling)) == before


@pytest.mark.parametrize("claim", [0, 2], ids=["repository-root", "non-owner-sibling"])
def test_refusal_is_structured_and_zero_write(matrix_checkouts, claim):
    before = tuple(snapshot(root) for root in matrix_checkouts)
    result = verdict(matrix_checkouts[claim], "--criterion", "FR-001", "--result", "pass")
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"]
    assert tuple(snapshot(root) for root in matrix_checkouts) == before
