"""Read-only plain-LANES status must not inherit mutation admission limits."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests._owned_fixtures import RSnapshotter
from tests.integration.conftest import OwnedCheckouts, _git, _write_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


@pytest.mark.parametrize("explicit", [True, False], ids=["explicit", "cwd-adopted"])
def test_plain_lanes_status_reads_selected_checkout_without_mutation(
    make_owned_checkouts: Callable[..., OwnedCheckouts],
    make_r_snapshot: Callable[[OwnedCheckouts], RSnapshotter],
    monkeypatch: pytest.MonkeyPatch,
    explicit: bool,
) -> None:
    checkouts = make_owned_checkouts(topology="lanes")
    append_event(
        checkouts.mission_dir,
        StatusEvent(
            event_id="fixture-active-wp",
            mission_slug=checkouts.mission_slug,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.IN_PROGRESS,
            at="2026-10-26T00:00:00+00:00",
            actor="fixture",
            force=False,
            execution_mode="worktree",
        ),
    )
    _write_mission(
        checkouts.repository_root / "kitty-specs" / checkouts.mission_slug,
        mission_id=checkouts.mission_id,
        slug=checkouts.mission_slug,
        topology="single_branch",
        target_branch=checkouts.target_branch,
        wp_ids=("WP99",),
    )
    _git(checkouts.repository_root, "add", ".")
    _git(checkouts.repository_root, "commit", "-qm", "primary decoy")
    snapshotter = make_r_snapshot(checkouts)
    before = snapshotter.take()
    selected_before = {path.relative_to(checkouts.mission_dir): path.read_bytes() for path in checkouts.mission_dir.rglob("*") if path.is_file()}
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    monkeypatch.chdir(checkouts.repository_root if explicit else checkouts.owned_root)
    arguments = ["status", "--mission", checkouts.mission_slug, "--json"]
    if explicit:
        arguments += ["--owned-checkout", str(checkouts.owned_root)]

    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert sorted(wp["id"] for wp in payload["work_packages"]) == ["WP01", "WP02"]
    assert next(wp for wp in payload["work_packages"] if wp["id"] == "WP01")["lane"] == "in_progress"
    assert payload["stale_repository_root_copy"] is not None
    snapshotter.assert_unchanged(before, snapshotter.take())
    assert selected_before == {path.relative_to(checkouts.mission_dir): path.read_bytes() for path in checkouts.mission_dir.rglob("*") if path.is_file()}


@pytest.mark.parametrize("topology", ["coord", "lanes_with_coord"])
def test_status_does_not_admit_coordination_topologies(
    make_owned_checkouts: Callable[..., OwnedCheckouts],
    monkeypatch: pytest.MonkeyPatch,
    topology: str,
) -> None:
    checkouts = make_owned_checkouts(topology=topology)
    monkeypatch.chdir(checkouts.repository_root)
    result = CliRunner().invoke(
        app,
        ["status", "--mission", checkouts.mission_slug, "--owned-checkout", str(checkouts.owned_root), "--json"],
    )
    assert result.exit_code != 0
    assert json.loads(result.output)["error_code"] == "OWNED_TOPOLOGY_UNSUPPORTED"


def test_plain_lanes_status_preserves_branch_validation(
    make_owned_checkouts: Callable[..., OwnedCheckouts],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkouts = make_owned_checkouts(topology="lanes")
    _git(checkouts.owned_root, "switch", "-c", "codex/unrelated")
    monkeypatch.chdir(checkouts.repository_root)
    result = CliRunner().invoke(
        app,
        ["status", "--mission", checkouts.mission_slug, "--owned-checkout", str(checkouts.owned_root), "--json"],
    )
    assert result.exit_code != 0
    assert json.loads(result.output)["error_code"] == "OWNED_BRANCH_REFUSED"
