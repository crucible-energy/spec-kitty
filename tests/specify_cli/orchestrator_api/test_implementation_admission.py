"""Normal LANES admission through the public orchestrator command boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
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
        "status": _git(repo, "--no-optional-locks", "status", "--porcelain"),
        "indices": {
            str(workspace): Path(_git(workspace, "rev-parse", "--path-format=absolute", "--git-path", "index")).read_bytes()
            for workspace in [
                Path(line.removeprefix("worktree ")) for line in _git(repo, "worktree", "list", "--porcelain").splitlines() if line.startswith("worktree ")
            ]
        },
    }


def _invoke(command: str, wp: str = "WP02") -> tuple[dict[str, Any], int]:
    args = [command, "--mission", SLUG, "--wp", wp]
    if command == "start-implementation":
        args += ["--actor", "codex", "--policy", POLICY]
    result = CliRunner().invoke(app, args, catch_exceptions=False)
    return json.loads(result.stdout), result.exit_code


@pytest.mark.parametrize("command", ["start-implementation", "preflight-implementation"])
@pytest.mark.parametrize("state", ["claimed", "in_progress", "for_review", "in_review", "blocked"])
def test_public_start_refuses_another_active_wp_before_any_mutation(lane_repo: tuple[Path, Path, Path], command: str, state: str) -> None:
    repo, _, _ = lane_repo
    _seed_canonical_wp_state(repo, SLUG, "WP01", state, actor="codex", assignee="Owner", shell_pid="1234", timestamp="2026-10-12T21:01:00Z")
    before = _snapshot(repo)
    envelope, code = _invoke(command)
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


def test_public_start_rechecks_occupancy_after_successful_preflight(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, _, _ = lane_repo
    envelope, code = _invoke("preflight-implementation")
    assert code == 0 and envelope["success"] is True
    _seed_canonical_wp_state(repo, SLUG, "WP01", "in_progress", actor="codex", assignee="Owner", shell_pid="1234", timestamp="2026-10-12T21:01:00Z")
    before = _snapshot(repo)
    envelope, code = _invoke("start-implementation")
    assert code != 0 and envelope["data"]["error_code"] == "LANE_OCCUPIED"
    assert _snapshot(repo) == before


def test_same_wp_resume_does_not_change_claim_or_context(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, _, _ = lane_repo
    assert _invoke("start-implementation", "WP01")[1] == 0
    envelope, code = _invoke("start-implementation", "WP01")
    assert code == 0 and envelope["data"]["no_op"] is True
    before = _snapshot(repo)
    assert _invoke("preflight-implementation", "WP01")[1] == 0
    assert _snapshot(repo) == before


def test_approved_prior_wp_allows_sequential_reuse(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, _, _ = lane_repo
    _seed_canonical_wp_state(repo, SLUG, "WP01", "approved", actor="codex", assignee="Owner", shell_pid="1234", timestamp="2026-10-12T21:01:00Z")
    assert _invoke("preflight-implementation")[1] == 0
    assert _invoke("start-implementation")[1] == 0


@pytest.mark.parametrize("command", ["start-implementation", "preflight-implementation"])
def test_foreign_repository_at_predicted_path_is_refused(lane_repo: tuple[Path, Path, Path], command: str) -> None:
    repo, _, lane = lane_repo
    expected_branch = _git(lane, "branch", "--show-current")
    _git(repo, "worktree", "move", str(lane), str(lane.with_name("retained-lane")))
    _init_repo(lane)
    _git(lane, "checkout", "-q", "-b", expected_branch)
    before = _snapshot(repo)
    foreign_before = _snapshot(lane)
    envelope, code = _invoke(command)
    assert code != 0 and envelope["data"]["error_code"] == "LANE_WORKSPACE_MISMATCH"
    assert _snapshot(repo) == before
    assert _snapshot(lane) == foreign_before


def test_dirty_preflight_does_not_refresh_worktree_index(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, _, lane = lane_repo
    (lane / "seed.txt").write_text("changed tracked content\n", encoding="utf-8")
    before = _snapshot(repo)
    envelope, code = _invoke("preflight-implementation")
    assert code != 0 and envelope["error_code"] == "LANE_ALLOCATION_FAILED"
    assert "uncommitted" in envelope["data"]["message"]
    assert _snapshot(repo) == before


def test_corrupt_status_is_an_explicit_preflight_refusal(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, mission, _ = lane_repo
    (mission / "status.events.jsonl").write_text("{broken\n", encoding="utf-8")
    before = _snapshot(repo)
    envelope, code = _invoke("preflight-implementation")
    assert code != 0 and envelope["data"]["error_code"] == "LANE_STATUS_UNREADABLE"
    assert _snapshot(repo) == before


def test_replaced_workspace_after_preflight_is_detected(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, _, lane = lane_repo
    assert _invoke("preflight-implementation")[1] == 0
    expected_branch = _git(lane, "branch", "--show-current")
    _git(repo, "worktree", "move", str(lane), str(lane.with_name("retained-lane")))
    _init_repo(lane)
    _git(lane, "checkout", "-q", "-b", expected_branch)
    before = _snapshot(repo)
    envelope, code = _invoke("start-implementation")
    assert code != 0 and envelope["data"]["error_code"] == "LANE_WORKSPACE_MISMATCH"
    assert _snapshot(repo) == before


@pytest.mark.parametrize("keep_branch,route", [(True, "crash_recovery"), (False, "fresh_legacy")])
def test_unmaterialized_preflight_does_not_create_or_recover_a_lane(lane_repo: tuple[Path, Path, Path], keep_branch: bool, route: str) -> None:
    repo, _, lane = lane_repo
    branch = _git(lane, "branch", "--show-current")
    _git(repo, "worktree", "remove", str(lane))
    if not keep_branch:
        _git(repo, "branch", "-D", branch)
    before = _snapshot(repo)
    envelope, code = _invoke("preflight-implementation")
    assert code == 0, envelope
    assert envelope["data"]["route"] == route
    assert not lane.exists()
    assert _snapshot(repo) == before


def test_malformed_manifest_returns_an_envelope_without_writes(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, mission, _ = lane_repo
    (mission / "lanes.json").write_text("{broken\n", encoding="utf-8")
    before = _snapshot(repo)
    envelope, code = _invoke("preflight-implementation")
    assert code != 0 and envelope["error_code"] == "LANE_ALLOCATION_FAILED"
    assert _snapshot(repo) == before


def test_unverifiable_git_marker_refuses_before_writes(lane_repo: tuple[Path, Path, Path]) -> None:
    repo, _, lane = lane_repo
    _git(repo, "worktree", "move", str(lane), str(lane.with_name("retained-lane")))
    lane.mkdir()
    (lane / ".git").write_text("gitdir: /nonexistent-admission-fixture\n", encoding="utf-8")
    before = _snapshot(repo)
    marker_before = (lane / ".git").read_bytes()
    envelope, code = _invoke("preflight-implementation")
    assert code != 0 and envelope["data"]["error_code"] == "LANE_WORKSPACE_MISMATCH"
    assert _snapshot(repo) == before
    assert (lane / ".git").read_bytes() == marker_before


def _start_processes(repo: Path, *, short_timeout: bool) -> list[subprocess.Popen[str]]:
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}
    script = "from specify_cli.orchestrator_api import wp_lifecycle; wp_lifecycle.CHECKOUT_CLAIM_LOCK_TIMEOUT_SECONDS = 0.2; from specify_cli import main; main()"
    prefix = [sys.executable, "-c", script] if short_timeout else [sys.executable, "-m", "specify_cli"]
    return [
        subprocess.Popen(
            [*prefix, "orchestrator-api", "start-implementation", "--mission", SLUG, "--wp", wp, "--actor", "codex", "--policy", POLICY],
            cwd=repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for wp in ("WP01", "WP02")
    ]


def _join_processes(children: list[subprocess.Popen[str]]) -> list[tuple[dict[str, Any], int | None]]:
    try:
        joined = []
        for child in children:
            stdout, stderr = child.communicate(timeout=30)
            assert stdout, stderr
            joined.append((json.loads(stdout), child.returncode))
        return joined
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                child.communicate(timeout=10)


def test_public_starts_use_the_same_checkout_lock_before_mutation(lane_repo: tuple[Path, Path, Path]) -> None:
    from specify_cli.status import write_checkout_claim_lock

    repo, _, lane = lane_repo
    before = _snapshot(repo)
    with write_checkout_claim_lock(lane, repo_root=repo):
        results = _join_processes(_start_processes(repo, short_timeout=True))
    assert all(code != 0 and envelope["error_code"] == "STATUS_LOCK_HELD" for envelope, code in results), results
    assert _snapshot(repo) == before


def test_concurrent_public_starts_admit_only_one_wp(lane_repo: tuple[Path, Path, Path]) -> None:
    from specify_cli.status import read_events, reduce

    repo, mission, _ = lane_repo
    results = _join_processes(_start_processes(repo, short_timeout=False))
    assert sum(code == 0 for _, code in results) == 1, results
    failures = [envelope for envelope, code in results if code != 0]
    assert failures[0]["data"]["error_code"] == "LANE_OCCUPIED"
    states = reduce(read_events(mission)).work_packages
    assert sum(state["lane"] == "in_progress" for state in states.values()) == 1
