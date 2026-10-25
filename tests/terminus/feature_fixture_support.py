"""Opt-in feature targets for specialized real consolidation scenarios.

Generic/frozen builders keep their original defaults. Only tests that need to
reach content, rollback, or attestation gates import these named adapters.
"""

from pathlib import Path
from typing import Any
from tests._support.feature_landing import TARGET, pin_primary


def feature_build_coord_mission_mixed_lane(tmp_path: Path, **kwargs: Any) -> Any:
    from tests.terminus.conftest import build_coord_mission_mixed_lane

    result = build_coord_mission_mixed_lane(tmp_path, target_branch=TARGET, **kwargs)
    pin_primary(result.repo)
    return result


def feature_build_coord_mission_shared_file(tmp_path: Path, **kwargs: Any) -> Any:
    from tests.terminus.conftest import build_coord_mission_shared_file

    result = build_coord_mission_shared_file(tmp_path, target_branch=TARGET, **kwargs)
    pin_primary(result.repo)
    return result


def feature_build_coord_mission_mixed_lane_canceled(tmp_path: Path, **kwargs: Any) -> Any:
    from tests.terminus.conftest import build_coord_mission_mixed_lane_canceled

    result = build_coord_mission_mixed_lane_canceled(tmp_path, target_branch=TARGET, **kwargs)
    pin_primary(result.repo)
    return result


def feature_build_coord_mission_mixed_lane_with_dependency(tmp_path: Path, **kwargs: Any) -> Any:
    from tests.terminus.conftest import build_coord_mission_mixed_lane_with_dependency

    result = build_coord_mission_mixed_lane_with_dependency(tmp_path, target_branch=TARGET, **kwargs)
    pin_primary(result.repo)
    return result


def feature_build_lanes_mission_canceled_dependency(tmp_path: Path, **kwargs: Any) -> Any:
    from tests.terminus.lanes_fixture import build_lanes_mission_canceled_dependency

    result = build_lanes_mission_canceled_dependency(tmp_path, target_branch=TARGET, **kwargs)
    pin_primary(result.repo)
    return result


def feature_build_canceled_dependency_mission(tmp_path: Path, **kwargs: Any) -> Any:
    from tests.terminus.canceled_dependency_support import build_canceled_dependency_mission

    result = build_canceled_dependency_mission(tmp_path, target_branch=TARGET, **kwargs)
    pin_primary(result.mission.repo)
    return result


def feature_build_post_approval_mission(tmp_path: Path, topology: str) -> Any:
    from tests.terminus.post_approval_support import build_post_approval_coord_mission, build_post_approval_lanes_mission

    if topology not in ("coord", "lanes"):
        raise ValueError("Unknown post-approval topology")
    builder = build_post_approval_coord_mission if topology == "coord" else build_post_approval_lanes_mission
    result = builder(tmp_path, target_branch=TARGET)
    pin_primary(result.repo)
    return result
