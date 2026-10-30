"""Repro #4985 — an explicit ``--target`` is lost to stale meta across a crash.

The historical issue used main/develop. Under current PR-only policy, exercise
the same stale-metadata precedence using two eligible integration branches,
with a separate protected primary. An explicit target must win without changing
the stale metadata target or advancing the primary. This is not permission to
override protected bookkeeping; its refusal remains independently tested.

Use the real consolidation CLI and Git. The interrupted state is written through
``save_state``; approved SHAs come from lane-branch tips (RN-Q3).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.terminus.conftest import (
    CoordMission,
    run_terminus,
    sha_reachable,
)
from tests.terminus.conftest import _git as git
from tests._support.feature_landing import build_feature_coord_mission as build_coord_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _persist_interrupted_merge(mission: CoordMission, wp_ids: list[str], target: str) -> None:
    from specify_cli.consolidation.reconciliation import write_post_fix_marker
    from specify_cli.consolidation.state import ConsolidationState, save_state

    state = ConsolidationState(
        mission_id=mission.mission_id,
        mission_slug=mission.slug,
        target_branch=target,
        wp_order=list(wp_ids),
    )
    state.current_wp = wp_ids[0]
    state.strategy = "merge"
    save_state(state, mission.repo)
    # WP10 integration (FR-012): mark this as a POST-fix in-flight crash so the
    # resumed merge is not refused by the FR-012 legacy guard.
    write_post_fix_marker(mission.repo, mission.mission_id)


def test_4985_explicit_target_wins_over_stale_meta_on_resume(tmp_path: Path) -> None:
    mission = build_coord_mission(tmp_path, wps=("WP01",), mid8="01M4985A")
    stale_target = mission.target_branch
    stale_tip = mission.rev(stale_target)
    explicit_target = "feature/explicit-target"
    git(mission.repo, "branch", explicit_target, stale_target)
    git(mission.repo, "checkout", "-q", explicit_target)
    approved = mission.approved_shas_from_lane_tips(["WP01"])
    _persist_interrupted_merge(mission, ["WP01"], target=explicit_target)

    # The operator re-states the explicit target on resume; it must win over stale meta.
    result = run_terminus(mission, ["consolidate", "--resume", "--target", explicit_target, "--yes"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert mission.rev(stale_target) == stale_tip, "Resume moved the stale metadata target"

    for shas in approved.values():
        for sha in shas:
            assert sha_reachable(mission.repo, sha, explicit_target), (
                f"approved commit {sha[:10]} did NOT land on explicit target {explicit_target} after resume (#4985)"
            )
    # And the stale target must NOT have received the work.
    for shas in approved.values():
        for sha in shas:
            assert not sha_reachable(mission.repo, sha, stale_target), f"approved commit {sha[:10]} landed on stale target {stale_target} (#4985)"
