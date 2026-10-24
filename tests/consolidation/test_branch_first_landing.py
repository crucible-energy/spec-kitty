"""PR-only primary advancement and real nonempty feature consolidation."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from tests._support.git_cli import git_out
from tests.terminus.conftest import build_coord_mission, run_terminus
from specify_cli.consolidation.preflight import _enforce_pr_only_target

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.non_sandbox]


@pytest.mark.parametrize("target", ["main", "feature/integration"])
def test_consolidation_preserves_primary_and_lands_only_on_feature(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    # The complete mock-free harness owns a disposable home, not our mission's
    # runtime. No production Store, credentials or configured account is read.
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    mission = build_coord_mission(tmp_path, wps=("WP01",), target_branch=target)
    if target != "main":
        git_out(mission.repo, "branch", "main", target)
    primary = git_out(mission.repo, "rev-parse", "main")
    git_out(mission.repo, "update-ref", "refs/remotes/origin/main", primary)
    git_out(mission.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    refs = git_out(mission.repo, "for-each-ref", "--format=%(refname) %(objectname)")
    status = git_out(mission.repo, "status", "--porcelain", "--untracked-files=all")
    target_before = git_out(mission.repo, "rev-parse", target)
    result = run_terminus(mission, ["consolidate", "--mission", mission.slug, "--yes"], env={"SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS": "1"})
    if target == "main":
        assert result.returncode != 0, result.stdout + result.stderr
        assert "PR-only" in result.stdout + result.stderr
        assert git_out(mission.repo, "for-each-ref", "--format=%(refname) %(objectname)") == refs
        assert git_out(mission.repo, "status", "--porcelain", "--untracked-files=all") == status
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert git_out(mission.repo, "rev-parse", target) != target_before
        assert git_out(mission.repo, "show", target + ":src/pkg/wp01.py")
    assert git_out(mission.repo, "rev-parse", "main") == primary


def test_symbolic_feature_alias_cannot_land_on_primary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    mission = build_coord_mission(tmp_path, wps=("WP01",), target_branch="main")
    git_out(mission.repo, "symbolic-ref", "refs/heads/feature/alias", "refs/heads/main")
    refs = git_out(mission.repo, "for-each-ref", "--format=%(refname) %(objectname) %(symref)")
    status = git_out(mission.repo, "status", "--porcelain", "--untracked-files=all")
    result = run_terminus(
        mission, ["consolidate", "--mission", mission.slug, "--target", "feature/alias", "--yes"], env={"SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS": "1"}
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "PR-only" in result.stdout + result.stderr
    assert git_out(mission.repo, "for-each-ref", "--format=%(refname) %(objectname) %(symref)") == refs
    assert git_out(mission.repo, "status", "--porcelain", "--untracked-files=all") == status


@pytest.mark.parametrize("target", ["HEAD", "main~1", "--help", "missing", "refs/heads/main"])
def test_revision_option_missing_or_primary_target_is_read_only_refusal(tmp_path: Path, target: str) -> None:
    from tests._support.feature_landing import init_feature_repo

    init_feature_repo(tmp_path)
    refs = git_out(tmp_path, "for-each-ref", "--format=%(refname) %(objectname)")
    with pytest.raises(typer.Exit) as refused:
        _enforce_pr_only_target(tmp_path, target)
    assert refused.value.exit_code == 1
    assert git_out(tmp_path, "for-each-ref", "--format=%(refname) %(objectname)") == refs


def test_custom_primary_stays_pr_only_with_empty_config_and_operator_hatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests._support.feature_landing import init_feature_repo

    init_feature_repo(tmp_path)
    git_out(tmp_path, "branch", "trunk", "main")
    git_out(tmp_path, "update-ref", "refs/remotes/origin/trunk", "trunk")
    git_out(tmp_path, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    config = tmp_path / ".kittify" / "config.yaml"
    config.parent.mkdir(exist_ok=True)
    config.write_text("protection:\n  protected_branches: []\n")
    monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
    refs = git_out(tmp_path, "for-each-ref", "--format=%(refname) %(objectname)")
    with pytest.raises(typer.Exit):
        _enforce_pr_only_target(tmp_path, "trunk")
    assert _enforce_pr_only_target(tmp_path, "refs/heads/feature/integration") == "feature/integration"
    assert git_out(tmp_path, "for-each-ref", "--format=%(refname) %(objectname)") == refs
