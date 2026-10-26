"""Existing work must not disappear behind a planned-only claim preview."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from mission_runtime import OwnedCheckout
from runtime.next.runtime_bridge import query_current_state
from runtime.next.runtime_bridge_decision_mapping import _resolve_wp_board_action
from specify_cli.core.owned_mission import NEXT_OWNED_TOPOLOGIES, resolve_owned_mission
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests._owned_fixtures import RSnapshotter
from tests.integration.conftest import OwnedCheckouts, _git, _write_mission

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _active_board(checkouts: OwnedCheckouts, *, owner: str = "codex", active_lane: Lane = Lane.IN_PROGRESS) -> OwnedCheckout:
    for wp, dependency in [("WP09", "WP01"), ("WP02", "WP09")]:
        p = checkouts.mission_dir / "tasks" / f"{wp}-owned.md"
        p.write_text(p.read_text().replace("dependencies: []", f"dependencies: [{dependency}]"))
    for wp, lane, actor in [("WP01", Lane.APPROVED, "codex"), ("WP09", active_lane, owner), ("WP02", Lane.PLANNED, "finalize-tasks")]:
        append_event(
            checkouts.mission_dir,
            StatusEvent(
                event_id=f"fixture-{wp}-{lane}",
                mission_slug=checkouts.mission_slug,
                wp_id=wp,
                from_lane=Lane.PLANNED,
                to_lane=lane,
                at="2026-10-26T00:00:00+00:00",
                actor=actor,
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
    for root in [checkouts.owned_root, checkouts.repository_root]:
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "synthetic current and primary-decoy boards")
    return resolve_owned_mission(checkouts.repository_root, checkouts.owned_root, checkouts.mission_slug, allowed_topologies=NEXT_OWNED_TOPOLOGIES)


@pytest.mark.parametrize("lane", [Lane.CLAIMED, Lane.IN_PROGRESS])
def test_named_query_resumes_current_owner_without_new_claim(
    make_owned_checkouts: Callable[..., OwnedCheckouts],
    make_r_snapshot: Callable[[OwnedCheckouts], RSnapshotter],
    lane: Lane,
) -> None:
    checkouts = make_owned_checkouts(topology="lanes", wp_ids=("WP01", "WP09", "WP02"))
    owned = _active_board(checkouts, active_lane=lane)
    snapshotter = make_r_snapshot(checkouts)
    before = snapshotter.take()
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()

    decision = query_current_state("codex", checkouts.mission_slug, checkouts.repository_root, owned=owned)

    assert decision.wp_id == "WP09"
    assert decision.preview_step == "implement"
    assert decision.reason != "dependencies_not_satisfied"
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    snapshotter.assert_unchanged(before, snapshotter.take())


def test_step_selection_consumes_existing_workspace_and_owner(
    make_owned_checkouts: Callable[..., OwnedCheckouts],
) -> None:
    checkouts = make_owned_checkouts(topology="lanes", wp_ids=("WP01", "WP09", "WP02"))
    owned = _active_board(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()

    selected = _resolve_wp_board_action(mission_slug=checkouts.mission_slug, repo_root=checkouts.repository_root, owned=owned, agent="codex")

    assert selected.wp_id == "WP09"
    assert selected.action == "implement"
    assert selected.workspace_path == str(checkouts.owned_root)
    assert selected.blocked_reason is None
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events


@pytest.mark.parametrize("owner", ["other-agent", "unknown"])
def test_named_query_does_not_take_over_another_or_unproved_owner(make_owned_checkouts: Callable[..., OwnedCheckouts], owner: str) -> None:
    checkouts = make_owned_checkouts(topology="lanes", wp_ids=("WP01", "WP09", "WP02"))
    owned = _active_board(checkouts, owner=owner)
    original = (checkouts.mission_dir / "status.events.jsonl").read_bytes()

    decision = query_current_state("codex", checkouts.mission_slug, checkouts.repository_root, owned=owned)

    assert decision.wp_id is None
    assert "owner" in (decision.reason or "")
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == original
