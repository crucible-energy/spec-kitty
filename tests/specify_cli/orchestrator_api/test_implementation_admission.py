"""Normal LANES admission through the public orchestrator command boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from kernel.clock import now_utc_iso
from typer.testing import CliRunner

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.lanes.worktree_allocator import allocate_lane_worktree
from specify_cli.orchestrator_api.commands import app
from tests.specify_cli.cli.commands.test_single_branch_implement_refusals import (
    _git,
    _init_repo,
    _write_code_wp,
    _write_meta,
)
from tests.utils import _seed_canonical_wp_state

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
SLUG = "implementation-admission-01M4S13F"
MISSION_ID = "01M4S13FKF2S2SBKMYH74M6P5M"
POLICY = json.dumps(
    {
        "orchestrator_id": "acceptance",
        "orchestrator_version": "1",
        "agent_family": "codex",
        "approval_mode": "authorized",
        "sandbox_mode": "isolated",
        "network_mode": "offline",
        "dangerous_flags": [],
    }
)


@pytest.fixture()
def lane_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    _init_repo(repo)
    mission = repo / "kitty-specs" / SLUG
    _write_meta(mission, SLUG, MISSION_ID, topology="lanes")
    (mission / "tasks").mkdir()
    for wp in ("WP01", "WP02"):
        _write_code_wp(mission, wp)
        _seed_canonical_wp_state(repo, SLUG, wp, "planned", actor="codex", assignee="Owner", shell_pid="1234", timestamp="2026-10-12T21:00:00Z")
    manifest = LanesManifest(
        version=1,
        mission_slug=SLUG,
        mission_id=MISSION_ID,
        mission_branch=f"kitty/mission-{SLUG}",
        target_branch="trunk",
        lanes=[ExecutionLane(lane_id="lane-a", wp_ids=("WP01", "WP02"), write_scope=(), predicted_surfaces=(), depends_on_lanes=(), parallel_group=0)],
        computed_at=now_utc_iso(),
        computed_from="acceptance",
    )
    write_lanes_json(mission, manifest)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "admission fixture")
    lane, _ = allocate_lane_worktree(repo, SLUG, "WP01", manifest)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo))
    return repo, mission, lane


def _snapshot(repo: Path) -> dict[str, Any]:
    """Capture persistent state, registry, refs, and hook bytes without writes."""
    files = {}
    for root in (repo / ".kittify", repo / "kitty-specs", repo / ".git" / "hooks"):
        for path in sorted(root.rglob("*")):
            if path.is_file():
                files[str(path.relative_to(repo))] = path.read_bytes()
    return {
        "files": files,
        "refs": _git(repo, "show-ref"),
        "registry": _git(repo, "worktree", "list", "--porcelain"),
        "status": _git(repo, "status", "--porcelain"),
        "index": (repo / ".git" / "index").read_bytes(),
    }


def _invoke(command: str, wp: str = "WP02") -> tuple[dict[str, Any], int]:
    args = [command, "--mission", SLUG, "--wp", wp]
    if command == "start-implementation":
        args += ["--actor", "codex", "--policy", POLICY]
    result = CliRunner().invoke(app, args, catch_exceptions=False)
    return json.loads(result.stdout), result.exit_code


def test_public_start_refuses_another_active_wp_before_any_mutation(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, _, _ = lane_repo
    _seed_canonical_wp_state(repo, SLUG, "WP01", "in_progress", actor="codex", assignee="Owner", shell_pid="1234", timestamp="2026-10-12T21:01:00Z")
    before = _snapshot(repo)
    envelope, code = _invoke("start-implementation")
    after = _snapshot(repo)
    assert code != 0, {"envelope": envelope, "before": before, "after": after}
    assert envelope["data"]["error_code"] == "LANE_OCCUPIED"
    assert after == before


def test_public_start_refuses_wrong_lane_branch_before_any_mutation(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, _, lane = lane_repo
    _git(lane, "checkout", "-q", "-b", "unexpected-owner")
    before = _snapshot(repo)
    envelope, code = _invoke("start-implementation")
    assert code != 0, envelope
    assert envelope["data"]["error_code"] == "LANE_WORKSPACE_MISMATCH"
    assert _snapshot(repo) == before


def test_public_preflight_is_read_only_and_reports_reuse(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, _, lane = lane_repo
    before = _snapshot(repo)
    envelope, code = _invoke("preflight-implementation")
    assert code == 0, envelope
    assert envelope["success"] is True
    assert envelope["data"]["route"] == "reuse"
    assert envelope["data"]["workspace_path"] == str(lane)
    assert envelope["data"]["allocation_performed"] is False
    assert _snapshot(repo) == before
