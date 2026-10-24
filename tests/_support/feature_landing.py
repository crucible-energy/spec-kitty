"""Opt-in real feature landing fixtures; primary history stays separate.

Existing protected-primary and low-level recovery fixtures keep their defaults.
Only full successful consolidation fixtures opt into this adapter.
"""

from pathlib import Path
from typing import Any

from tests._support.git_cli import git_out

TARGET = "feature/integration"


def pin_primary(repo: Path) -> str:
    """Pin a separate real default branch without relaxing protection policy."""
    head = git_out(repo, "rev-parse", "HEAD")
    # Callers initialize a feature branch; never overwrite an existing primary.
    existing = "refs/heads/main" in git_out(repo, "for-each-ref", "--format=%(refname)", "refs/heads/main").splitlines()
    if not existing:
        git_out(repo, "branch", "main", head)
    primary = git_out(repo, "rev-parse", "main")
    git_out(repo, "update-ref", "refs/remotes/origin/main", primary)
    git_out(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    return primary


def build_feature_coord_mission(tmp_path: Path, **kwargs: Any) -> Any:
    from tests.terminus.conftest import build_coord_mission

    mission = build_coord_mission(tmp_path, target_branch=TARGET, **kwargs)
    pin_primary(mission.repo)
    return mission


def build_feature_lanes_mission(tmp_path: Path, **kwargs: Any) -> Any:
    from tests.terminus.lanes_fixture import build_lanes_mission

    mission = build_lanes_mission(tmp_path, target_branch=TARGET, **kwargs)
    pin_primary(mission.repo)
    return mission


def init_feature_repo(repo: Path) -> None:
    from tests.integration.test_merge_lane_planning_data_loss import _init_git_repo

    _init_git_repo(repo)
    git_out(repo, "checkout", "-qb", TARGET)
    pin_primary(repo)


def write_feature_meta(feature_dir: Path, slug: str, **kwargs: Any) -> None:
    from tests.integration.test_merge_lane_planning_data_loss import _write_meta

    _write_meta(feature_dir, slug, target_branch=TARGET, **kwargs)


def write_feature_lanes_manifest(feature_dir: Path, slug: str, **kwargs: Any) -> Any:
    from tests.integration.test_merge_lane_planning_data_loss import _write_lanes_manifest

    return _write_lanes_manifest(feature_dir, slug, target_branch=TARGET, **kwargs)
