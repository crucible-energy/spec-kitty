"""``resolve_partition_read_dir``: the single handed-dir partition read authority (#5180).

Each cell of the resolver's contract, on real git fixtures:

* no workspace root → the handed dir (flat self-home);
* a phantom resolved partition (foreign ambient anchor, #154) → the handed dir;
* phantom resolved partition AND missing handed dir → the resolved path, unguessed;
* flat / single-branch topology → the primary dir;
* materialised coord → the coord husk, never the PRIMARY decoy log;
* unmaterialised / deleted coord → the seam's typed error propagates.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import ActionContextError, MissionArtifactKind, OwnedCheckout
from specify_cli.core.owned_mission import resolve_owned_mission
from specify_cli.review.artifacts import ReviewCycleArtifact
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from specify_cli.coordination.surface_resolver import (
    CoordinationBranchDeleted,
    CoordinationWorktreeUnmaterialized,
)
from specify_cli.missions._read_path_resolver import resolve_partition_read_dir
from tests.integration.coord_topology_fixture import (  # noqa: F401 -- pytest fixtures
    CoordTopologyContext,
    FlatTopologyContext,
    coord_topology_mission,
    flat_topology_mission,
)

# Re-export the fixtures so pytest discovers them in this module.
__all__ = ["coord_topology_mission", "flat_topology_mission"]

pytestmark = pytest.mark.git_repo

_STATUS = MissionArtifactKind.STATUS_STATE


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _foreign_anchor_dir(tmp_path: Path, *, create: bool) -> Path:
    ambient = tmp_path / "ambient-checkout"
    ambient.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(ambient)], check=True)
    feature_dir = ambient / "repo" / "kitty-specs" / "001-foreign-anchor"
    if create:
        feature_dir.mkdir(parents=True)
    return feature_dir


def test_no_workspace_root_returns_handed_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.core.paths import WorkspaceRootNotFound
    from specify_cli.missions import _read_path_resolver

    def _no_root(_path: Path) -> Path:
        raise WorkspaceRootNotFound("no git ancestor")

    monkeypatch.setattr(_read_path_resolver, "resolve_canonical_root", _no_root)
    feature_dir = tmp_path / "kitty-specs" / "001-bare"

    assert resolve_partition_read_dir(feature_dir, _STATUS) == feature_dir


def test_phantom_partition_degrades_to_existing_handed_dir(tmp_path: Path) -> None:
    feature_dir = _foreign_anchor_dir(tmp_path, create=True)

    assert resolve_partition_read_dir(feature_dir, _STATUS) == feature_dir


def test_phantom_partition_with_missing_handed_dir_returns_resolved_path(tmp_path: Path) -> None:
    feature_dir = _foreign_anchor_dir(tmp_path, create=False)

    resolved = resolve_partition_read_dir(feature_dir, _STATUS)

    assert resolved != feature_dir
    assert resolved == tmp_path / "ambient-checkout" / "kitty-specs" / "001-foreign-anchor"
    assert not resolved.exists()


def test_flat_topology_resolves_primary(flat_topology_mission: FlatTopologyContext) -> None:
    ctx = flat_topology_mission

    assert resolve_partition_read_dir(ctx.primary_feature_dir, _STATUS) == ctx.primary_feature_dir


def test_materialised_coord_resolves_husk_not_primary_decoy(
    coord_topology_mission: CoordTopologyContext,
) -> None:
    ctx = coord_topology_mission

    resolved = resolve_partition_read_dir(ctx.primary_feature_dir, _STATUS)

    assert resolved == ctx.coord_feature_dir
    assert (resolved / "status.events.jsonl").read_text(encoding="utf-8") == ctx.status_events_path.read_text(encoding="utf-8")
    assert resolved != ctx.decoy_events_path.parent


def test_primary_kind_on_coord_topology_resolves_primary(
    coord_topology_mission: CoordTopologyContext,
) -> None:
    ctx = coord_topology_mission

    resolved = resolve_partition_read_dir(ctx.primary_feature_dir, MissionArtifactKind.PRIMARY_METADATA)

    assert resolved == ctx.primary_feature_dir


def test_unmaterialised_coord_raises(coord_topology_mission: CoordTopologyContext) -> None:
    ctx = coord_topology_mission
    _git(ctx.repo, "worktree", "remove", "--force", str(ctx.coord_feature_dir.parent.parent))

    with pytest.raises(CoordinationWorktreeUnmaterialized):
        resolve_partition_read_dir(ctx.primary_feature_dir, _STATUS)


def test_deleted_coord_branch_raises(coord_topology_mission: CoordTopologyContext) -> None:
    ctx = coord_topology_mission
    _git(ctx.repo, "worktree", "remove", "--force", str(ctx.coord_feature_dir.parent.parent))
    _git(ctx.repo, "branch", "-D", ctx.coord_branch)

    with pytest.raises(CoordinationBranchDeleted):
        resolve_partition_read_dir(ctx.primary_feature_dir, _STATUS)


def test_retrospective_kind_is_refused(tmp_path: Path) -> None:
    """RETROSPECTIVE has its own home authority; the handed-dir resolver must not mint a second one."""
    with pytest.raises(ValueError, match="RETROSPECTIVE"):
        resolve_partition_read_dir(tmp_path, MissionArtifactKind.RETROSPECTIVE)


@pytest.fixture
def owned_partition_mission(tmp_path: Path) -> tuple[Path, OwnedCheckout]:
    """A validated linked checkout with readable same-slug primary decoys."""
    repository = tmp_path / "primary"
    repository.mkdir()
    _git(repository, "init", "-q", "-b", "main")
    _git(repository, "config", "user.name", "Test")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "commit.gpgsign", "false")
    (repository / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-qm", "seed")

    checkout = tmp_path / "owned"
    _git(repository, "worktree", "add", "-qb", "work", str(checkout))
    slug = "owned-read-01M2A900"
    mission = checkout / "kitty-specs" / slug
    mission.mkdir(parents=True)
    (mission / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01M2A900000000000000000001",
                "mission_slug": slug,
                "slug": slug,
                "mission_type": "software-dev",
                "topology": "single_branch",
                "target_branch": "work",
                "flattened": False,
            }
        ),
        encoding="utf-8",
    )
    _git(checkout, "add", "kitty-specs")
    _git(checkout, "commit", "-qm", "owned mission")
    owned = resolve_owned_mission(repository, checkout, slug)
    primary = repository / "kitty-specs" / slug
    primary.mkdir(parents=True)
    (primary / "meta.json").write_text('{"mission_id": "PRIMARY_DECOY"}', encoding="utf-8")

    for directory, cycle in ((mission, 1), (primary, 2)):
        feedback = directory / "tasks" / "WP01-core" / f"review-cycle-{cycle}.md"
        feedback.parent.mkdir(parents=True)
        ReviewCycleArtifact(
            cycle_number=cycle,
            wp_id="WP01",
            mission_slug=slug,
            reviewer_agent="reviewer",
            reviewed_at="2026-10-09T00:00:00Z",
            affected_files=[],
            reproduction_command="pytest tests/specify_cli/missions/test_partition_read_dir.py -q",
            body=f"Review from {directory.parent.parent.name}\n",
        ).write(feedback)
        append_event(
            directory,
            StatusEvent(
                event_id=f"review-{cycle}",
                mission_slug=slug,
                wp_id="WP01",
                from_lane=Lane.IN_REVIEW,
                to_lane=Lane.IN_PROGRESS,
                at="2026-10-09T00:00:00+00:00",
                actor="reviewer",
                force=False,
                execution_mode="worktree",
                review_ref=f"review-cycle://{slug}/WP01-core/review-cycle-{cycle}.md",
            ),
        )
    return primary, owned


@pytest.mark.parametrize("selector", ["owned", "primary"])
@pytest.mark.parametrize("kind", [_STATUS, MissionArtifactKind.PRIMARY_METADATA])
def test_owned_partition_reads_selected_checkout(
    owned_partition_mission: tuple[Path, OwnedCheckout],
    selector: str,
    kind: MissionArtifactKind,
) -> None:
    primary, owned = owned_partition_mission
    handed_dir = owned.mission_dir if selector == "owned" else primary

    resolved = resolve_partition_read_dir(handed_dir, kind, owned=owned)

    assert resolved == owned.mission_dir
    filename = "status.events.jsonl" if kind is _STATUS else "meta.json"
    assert (resolved / filename).read_text(encoding="utf-8") != (primary / filename).read_text(encoding="utf-8")


def test_owned_partition_refuses_other_mission(
    owned_partition_mission: tuple[Path, OwnedCheckout],
) -> None:
    primary, owned = owned_partition_mission
    other_mission = primary.with_name("other-mission-01M2B900")
    other_mission.mkdir()

    with pytest.raises(ActionContextError, match="owned fact is for mission"):
        resolve_partition_read_dir(other_mission, _STATUS, owned=owned)


def test_owned_partition_refuses_retrospective(
    owned_partition_mission: tuple[Path, OwnedCheckout],
) -> None:
    _, owned = owned_partition_mission

    with pytest.raises(ValueError, match="RETROSPECTIVE"):
        resolve_partition_read_dir(owned.mission_dir, MissionArtifactKind.RETROSPECTIVE, owned=owned)


@pytest.mark.parametrize("selector", ["owned", "primary"])
def test_owned_review_feedback_reads_selected_log_and_artifact(
    owned_partition_mission: tuple[Path, OwnedCheckout],
    selector: str,
) -> None:
    from specify_cli.cli.commands.agent.workflow_cores import resolve_review_feedback_context

    primary, owned = owned_partition_mission
    handed_dir = owned.mission_dir if selector == "owned" else primary

    result = resolve_review_feedback_context(handed_dir, "WP01", "", owned=owned)

    expected_file = owned.mission_dir / "tasks" / "WP01-core" / "review-cycle-1.md"
    assert result == (
        True,
        f"review-cycle://{owned.mission_slug}/WP01-core/review-cycle-1.md",
        expected_file,
        "canonical",
    )
    assert ReviewCycleArtifact.from_file(expected_file).body == "Review from owned\n"
