"""Real-CLI repro for #5721: a forced re-approval with a git-detected reviewer must not restamp the approval bound.

``move-task <WP> --to approved --force`` fills the event's reviewer from ``git config user.name``
and an ``auto-approval:`` reference, so a reviewer name is no evidence of a review.
"""

from __future__ import annotations

from tests.terminus.feature_fixture_support import feature_build_coord_mission_mixed_lane_canceled as build_coord_mission_mixed_lane_canceled

import subprocess
from pathlib import Path

import pytest

from tests.terminus.conftest import _git as git
from tests.terminus.conftest import CoordMission, blob_present_at, git_rev, run_terminus
from tests.terminus.mixed_lane_support import ATTEST_FLAG, collapse

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_LATE = "src/pkg/late.py"


@pytest.mark.regression
def test_bare_forced_reapproval_with_a_git_identity_still_refuses_a_late_commit(tmp_path: Path) -> None:
    """#5721: review approved WP01, a commit landed on the lane, the operator forces WP01 to approved again."""
    mission = build_coord_mission_mixed_lane_canceled(tmp_path, canceled_changes=(), stamp_attribution=True, mid8="01M5721X")
    repo = mission.repo
    git(repo, "config", "user.name", "Real Operator")
    git(repo, "checkout", "-q", mission.lane_branches["WP02"])
    (repo / _LATE).parent.mkdir(parents=True, exist_ok=True)
    (repo / _LATE).write_text("x\n", encoding="utf-8")
    git(repo, "add", _LATE)
    git(repo, "commit", "-qm", "late")
    git_rev(repo, "HEAD")
    git(repo, "checkout", "-q", mission.target_branch)

    moved = run_terminus(
        mission,
        ["agent", "tasks", "move-task", "WP01", "--to", "approved", "--force", "--note", "restamp", "--no-auto-commit", "--mission", mission.slug],
    )
    consolidated = run_terminus(mission, ["consolidate", "--mission", mission.slug, "--yes", ATTEST_FLAG, "WP02", "--attest-reason", "checked"])

    assert "forced approval of WP01 is not a review approval" in collapse(moved.stderr)
    flat = collapse(consolidated.stdout + "\n" + consolidated.stderr)
    assert consolidated.returncode != 0 and "LANE_MOVED_AFTER_APPROVAL" in flat, flat[-1500:]
    assert _LATE in flat, flat[-1500:]  # the refusal names the late commit's path
    assert not blob_present_at(repo, mission.target_branch, _LATE)


def _mission_with_late_commit(tmp_path: Path) -> CoordMission:
    mission = build_coord_mission_mixed_lane_canceled(tmp_path, canceled_changes=(), stamp_attribution=True, mid8="01M5721X")
    repo = mission.repo
    git(repo, "config", "user.name", "Real Operator")
    git(repo, "checkout", "-q", mission.lane_branches["WP02"])
    (repo / _LATE).parent.mkdir(parents=True, exist_ok=True)
    (repo / _LATE).write_text("x\n", encoding="utf-8")
    git(repo, "add", _LATE)
    git(repo, "commit", "-qm", "late")
    git(repo, "checkout", "-q", mission.target_branch)
    return mission


def _move(mission: CoordMission, *args: str) -> subprocess.CompletedProcess[str]:
    """``move-task`` with auto-commit on (the default), run from an operator branch: the protected target refuses metadata writes."""
    git(mission.repo, "checkout", "-q", "-B", "operator")
    try:
        return run_terminus(mission, ["agent", "tasks", "move-task", "WP01", *args, "--mission", mission.slug])
    finally:
        git(mission.repo, "checkout", "-q", mission.target_branch)


def _consolidate(mission: CoordMission) -> subprocess.CompletedProcess[str]:
    return run_terminus(mission, ["consolidate", "--mission", mission.slug, "--yes", ATTEST_FLAG, "WP02", "--attest-reason", "checked"])


@pytest.mark.regression
def test_bare_forced_reapproval_with_auto_commit_still_refuses_a_late_commit(tmp_path: Path) -> None:
    """#5721: with auto-commit on (the default) the forced approval writes its own review-cycle artifact; that is no review."""
    mission = _mission_with_late_commit(tmp_path)

    moved = _move(mission, "--to", "approved", "--force", "--note", "restamp")
    consolidated = _consolidate(mission)

    assert moved.returncode == 0, collapse(moved.stdout + moved.stderr)[-800:]
    assert "forced approval of WP01 is not a review approval" in collapse(moved.stderr)
    flat = collapse(consolidated.stdout + "\n" + consolidated.stderr)
    assert consolidated.returncode != 0 and "LANE_MOVED_AFTER_APPROVAL" in flat, flat[-1500:]
    assert not blob_present_at(mission.repo, mission.target_branch, _LATE)


@pytest.mark.regression
def test_forced_in_review_then_forced_approval_still_refuses_a_late_commit(tmp_path: Path) -> None:
    """#5721: forcing WP01 into in_review and then into approved is no review claim, so its review_result is no review."""
    mission = _mission_with_late_commit(tmp_path)

    entered = _move(mission, "--to", "in_review", "--force", "--note", "x")
    moved = _move(mission, "--to", "approved", "--force", "--note", "restamp")
    consolidated = _consolidate(mission)

    assert entered.returncode == 0, collapse(entered.stdout + entered.stderr)[-800:]
    assert moved.returncode == 0, collapse(moved.stdout + moved.stderr)[-800:]
    assert "forced approval of WP01 is not a review approval" in collapse(moved.stderr)
    flat = collapse(consolidated.stdout + "\n" + consolidated.stderr)
    assert consolidated.returncode != 0 and "LANE_MOVED_AFTER_APPROVAL" in flat, flat[-1500:]
    assert not blob_present_at(mission.repo, mission.target_branch, _LATE)
