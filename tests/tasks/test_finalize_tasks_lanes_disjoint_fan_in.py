"""Regression fixture for disjoint fan-in lane computation."""

from __future__ import annotations

import pytest

from specify_cli.lanes.compute import compute_lanes, is_planning_lane
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest

pytestmark = pytest.mark.fast


def _manifest(path: str) -> OwnershipManifest:
    return OwnershipManifest(
        execution_mode=ExecutionMode.CODE_CHANGE,
        owned_files=(path,),
        authoritative_surface=path,
    )


def test_disjoint_upstreams_remain_parallel_until_fan_in() -> None:
    upstreams = [f"WP{i:02d}" for i in range(1, 7)]
    graph = {wp_id: [] for wp_id in upstreams}
    graph["WP07"] = list(upstreams)
    manifests = {
        **{
            wp_id: _manifest(f"src/workstream_{index}/**")
            for index, wp_id in enumerate(upstreams, start=1)
        },
        "WP07": _manifest("src/fan_in/**"),
    }

    result = compute_lanes(graph, manifests, "fan-in-demo")

    assert len(result.lanes) == 7
    by_wp = {lane.wp_ids[0]: lane for lane in result.lanes}
    upstream_lane_ids = {by_wp[wp_id].lane_id for wp_id in upstreams}
    assert len(upstream_lane_ids) == 6  # golden-count: cardinality-is-contract (disjoint-lane assignment, not nameable lane ids)
    assert {by_wp[wp_id].parallel_group for wp_id in upstreams} == {0}
    assert by_wp["WP07"].parallel_group == 1
    assert set(by_wp["WP07"].depends_on_lanes) == upstream_lane_ids
    assert result.collapse_report is not None
    assert result.collapse_report.events == []


def test_overlapping_upstreams_still_collapse() -> None:
    graph = {"WP01": [], "WP02": [], "WP03": ["WP01", "WP02"]}
    manifests = {
        "WP01": _manifest("src/shared/**"),
        "WP02": _manifest("src/shared/api/**"),
        "WP03": _manifest("src/fan_in/**"),
    }

    result = compute_lanes(graph, manifests, "fan-in-demo")

    lane_sets = [set(lane.wp_ids) for lane in result.lanes]
    assert {"WP01", "WP02"} in lane_sets
    assert {"WP03"} in lane_sets
    assert result.collapse_report is not None
    assert result.collapse_report.events[0].rule == "write_scope_overlap"


def test_planning_artifacts_before_and_after_code_use_dependency_ordered_lanes() -> None:
    graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"]}
    manifests = {
        "WP01": OwnershipManifest(
            execution_mode=ExecutionMode.PLANNING_ARTIFACT,
            owned_files=("kitty-specs/demo/spec.md",),
            authoritative_surface="kitty-specs/demo/",
        ),
        "WP02": _manifest("src/demo.py"),
        "WP03": OwnershipManifest(
            execution_mode=ExecutionMode.PLANNING_ARTIFACT,
            owned_files=("kitty-specs/demo/acceptance.md",),
            authoritative_surface="kitty-specs/demo/",
        ),
    }

    result = compute_lanes(graph, manifests, "planning-phase-demo", target_branch="main")
    before = result.lane_for_wp("WP01")
    implementation = result.lane_for_wp("WP02")
    after = result.lane_for_wp("WP03")

    assert before is not None and is_planning_lane(before)
    assert implementation is not None and not is_planning_lane(implementation)
    assert after is not None and is_planning_lane(after)
    assert before.lane_id != after.lane_id
    assert before.lane_id in implementation.depends_on_lanes
    assert implementation.lane_id in after.depends_on_lanes
    assert before.parallel_group < implementation.parallel_group < after.parallel_group


def test_cross_phase_write_conflicts_are_serialized() -> None:
    graph = {
        "WP01": [],
        "WP02": [],
        "WP03": ["WP02"],
        "WP04": ["WP03"],
    }
    manifests = {
        "WP01": _manifest("src/shared/**"),
        "WP02": _manifest("src/foundation/**"),
        "WP03": OwnershipManifest(
            execution_mode=ExecutionMode.PLANNING_ARTIFACT,
            owned_files=("kitty-specs/demo/review.md",),
            authoritative_surface="kitty-specs/demo/",
        ),
        "WP04": _manifest("src/shared/api/**"),
    }

    result = compute_lanes(graph, manifests, "planning-phase-conflict-demo")
    by_wp = {wp_id: result.lane_for_wp(wp_id) for wp_id in graph}
    earlier = by_wp["WP01"]
    later = by_wp["WP04"]

    assert earlier is not None and later is not None
    assert earlier.lane_id in later.depends_on_lanes


def test_overlapping_non_adjacent_wps_do_not_make_a_valid_dependency_chain_cyclic() -> None:
    graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"]}
    manifests = {
        "WP01": _manifest("src/shared/**"),
        "WP02": _manifest("src/middle/**"),
        "WP03": _manifest("src/shared/api/**"),
    }

    result = compute_lanes(graph, manifests, "convex-lane-demo")
    by_wp = {wp_id: result.lane_for_wp(wp_id) for wp_id in graph}
    first, middle, last = by_wp["WP01"], by_wp["WP02"], by_wp["WP03"]

    assert first is not None and middle is not None and last is not None
    assert first.lane_id != last.lane_id
    assert first.lane_id in middle.depends_on_lanes
    assert middle.lane_id in last.depends_on_lanes
    assert first.parallel_group < middle.parallel_group < last.parallel_group
