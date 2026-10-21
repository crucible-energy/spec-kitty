"""Owned acceptance must classify the admitted checkout, never its primary decoy."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from specify_cli.acceptance.gates_core import (
    PLANNING_ARTIFACT_ONLY_SKIP_REASON,
    AcceptanceCheckDiagnostic,
    LaneGateOutcome,
    _check_lane_gates,
)
from specify_cli.acceptance.matrix import AcceptanceCriterion, AcceptanceMatrix, write_acceptance_matrix
from specify_cli.core.owned_mission import resolve_owned_mission
from tests.integration.conftest import make_owned_checkouts, make_r_snapshot, owned_checkouts, r_snapshot, stale_root_copy

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests._owned_fixtures import RSnapshotter
    from tests.integration.conftest import OwnedCheckouts

__all__ = ["make_owned_checkouts", "make_r_snapshot", "owned_checkouts", "r_snapshot", "stale_root_copy"]
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _planning_only(feature_dir: Path) -> None:
    for prompt in (feature_dir / "tasks").glob("WP*.md"):
        text = prompt.read_text(encoding="utf-8")
        assert text.count("execution_mode: code_change") == 1
        prompt.write_text(text.replace("execution_mode: code_change", "execution_mode: planning_artifact"), encoding="utf-8")


def _check(checkouts: OwnedCheckouts) -> tuple[LaneGateOutcome, list[str], list[AcceptanceCheckDiagnostic], list[AcceptanceCheckDiagnostic]]:
    owned = resolve_owned_mission(checkouts.repository_root, checkouts.owned_root, checkouts.mission_slug)
    issues: list[str] = []
    skipped: list[AcceptanceCheckDiagnostic] = []
    blocked: list[AcceptanceCheckDiagnostic] = []
    outcome = _check_lane_gates(
        checkouts.repository_root,
        checkouts.mission_dir,
        checkouts.target_branch,
        issues,
        skipped,
        blocked,
        mutate_matrix=False,
        owned=owned,
    )
    return outcome, issues, skipped, blocked


@pytest.mark.parametrize("decoy", [False, True], ids=["owned-only", "primary-planning-decoy"])
def test_owned_code_missing_matrix_is_blocked(owned_checkouts: OwnedCheckouts, stale_root_copy: Callable[..., Path], r_snapshot: RSnapshotter, decoy: bool) -> None:
    if decoy:
        _planning_only(stale_root_copy(with_lanes=False))
    before = r_snapshot.take()
    outcome, issues, _, blocked = _check(owned_checkouts)
    assert outcome.skip_reason is None
    assert outcome.matrix_dir is None
    assert any(item.check == "acceptance_matrix" for item in blocked)
    assert any("required" in issue and "matrix" in issue for issue in issues)
    r_snapshot.assert_unchanged(before, r_snapshot.take())


def test_owned_planning_preserves_legitimate_skip_despite_primary_code(
    owned_checkouts: OwnedCheckouts, stale_root_copy: Callable[..., Path], r_snapshot: RSnapshotter
) -> None:
    stale_root_copy(with_lanes=False)
    _planning_only(owned_checkouts.mission_dir)
    before = r_snapshot.take()
    outcome, issues, _, blocked = _check(owned_checkouts)
    assert outcome.skip_reason == PLANNING_ARTIFACT_ONLY_SKIP_REASON
    assert outcome.matrix_dir is None
    assert not issues
    assert not blocked
    r_snapshot.assert_unchanged(before, r_snapshot.take())


@pytest.mark.parametrize("verdict", ["pass", "fail", "pending"])
def test_owned_code_evaluates_actual_matrix(owned_checkouts: OwnedCheckouts, stale_root_copy: Callable[..., Path], r_snapshot: RSnapshotter, verdict: str) -> None:
    _planning_only(stale_root_copy(with_lanes=False))
    write_acceptance_matrix(
        owned_checkouts.mission_dir,
        AcceptanceMatrix(
            mission_slug=owned_checkouts.mission_slug,
            criteria=[
                AcceptanceCriterion(
                    criterion_id="owned-proof", description="Actual owned matrix judgement", proof_type="automated_test", evidence="fixture-only", pass_fail=verdict
                )
            ],
        ),
    )
    before = r_snapshot.take()
    outcome, issues, _, blocked = _check(owned_checkouts)
    assert outcome.skip_reason is None
    assert outcome.matrix_dir == owned_checkouts.mission_dir
    assert not blocked
    assert bool(issues) == (verdict != "pass")
    r_snapshot.assert_unchanged(before, r_snapshot.take())
