"""Issue #60: preview retained runtime history without adopting or rewriting it."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app
from specify_cli.core.owned_mission import NEXT_OWNED_TOPOLOGIES, resolve_owned_mission
from specify_cli.migration.backfill_runtime_state import backfill_runtime_state
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests._owned_tree_hash import hash_tree
from tests.integration.conftest import OwnedCheckouts, _git
from tests.unit.migration._backfill_fixture import corrupt_seed_value

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def test_preview_help_does_not_claim_exit_zero_proves_verification() -> None:
    result = CliRunner().invoke(app, ["backfill-runtime-state", "--help"])
    assert result.exit_code == 0
    help_text = " ".join(result.output.split())
    assert "completed dry-run" in help_text
    assert "inspect its result payload for failures" in help_text


def _prepare(checkouts: OwnedCheckouts) -> None:
    """Give the retained dossier legacy state, independently of any live coord surface."""
    meta_path = checkouts.mission_dir / "meta.json"
    meta = json.loads(meta_path.read_text())
    meta["coordination_branch"] = f"kitty/mission-{checkouts.mission_slug}"
    meta_path.write_text(json.dumps(meta))
    for path in (checkouts.mission_dir / "tasks").glob("WP*.md"):
        path.write_text(path.read_text().replace("title: Owned fixture task", "title: Owned fixture task\nlane: planned\nassignee: synthetic-operator"))
        append_event(
            checkouts.mission_dir,
            StatusEvent(
                event_id=f"synthetic-preview-{path.stem}",
                mission_slug=checkouts.mission_slug,
                mission_id=checkouts.mission_id,
                wp_id=path.stem.split("-", 1)[0],
                from_lane=Lane.GENESIS,
                to_lane=Lane.PLANNED,
                at="2026-01-01T00:00:00+00:00",
                actor="synthetic-fixture",
                force=True,
                execution_mode="worktree",
            ),
        )
    _git(checkouts.owned_root, "add", ".")
    _git(checkouts.owned_root, "commit", "-qm", "retain synthetic coordinated runtime history")


@pytest.mark.parametrize("topology", ["coord", "lanes_with_coord"])
def test_owned_preview_reads_only_selected_retained_dossier(make_owned_checkouts, monkeypatch, topology: str) -> None:
    checkouts = make_owned_checkouts(topology=topology)
    _prepare(checkouts)
    (checkouts.repository_root / "active-owner.md").write_text("Preserve unrelated primary work.\n")
    (checkouts.sibling / "active-owner.md").write_text("Preserve unrelated sibling work.\n")
    monkeypatch.chdir(checkouts.repository_root)
    before = [hash_tree(root) for root in (checkouts.repository_root, checkouts.owned_root, checkouts.sibling)]
    heads = [_git(root, "rev-parse", "HEAD") for root in (checkouts.repository_root, checkouts.owned_root, checkouts.sibling)]
    indexes = [_git(root, "ls-files", "--stage") for root in (checkouts.repository_root, checkouts.owned_root, checkouts.sibling)]

    result = CliRunner().invoke(
        app,
        [
            "backfill-runtime-state",
            "--mission",
            checkouts.mission_slug,
            "--owned-checkout",
            str(checkouts.owned_root),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["dry_run"] is True
    assert payload["owned_checkout"] == str(checkouts.owned_root)
    assert payload["read_scope"] == "retained_checkout"
    assert payload["canonical_status_adopted"] is False
    assert len(payload["results"]) == 1
    assert payload["results"][0]["slug"] == checkouts.mission_slug
    assert payload["summary"]["seeded"] > 0
    assert payload["retained_verification"]["stage"] == "before_seeding"
    assert payload["retained_verification"]["ok"] is False
    assert payload["retained_verification"]["runtime_wp_count"] == 2
    assert payload["retained_verification"]["mismatches"]
    assert [hash_tree(root) for root in (checkouts.repository_root, checkouts.owned_root, checkouts.sibling)] == before
    assert [_git(root, "rev-parse", "HEAD") for root in (checkouts.repository_root, checkouts.owned_root, checkouts.sibling)] == heads
    assert [_git(root, "ls-files", "--stage") for root in (checkouts.repository_root, checkouts.owned_root, checkouts.sibling)] == indexes


def test_owned_preview_cannot_apply_or_walk_an_implicit_corpus(owned_checkouts, monkeypatch) -> None:
    monkeypatch.chdir(owned_checkouts.repository_root)
    before = hash_tree(owned_checkouts.owned_root)
    cases = [(["--mission", owned_checkouts.mission_slug], "OWNED_OPTION_UNSUPPORTED"), (["--dry-run"], "FEATURE_CONTEXT_UNRESOLVED")]
    for extra, code in cases:
        result = CliRunner().invoke(
            app,
            [
                "backfill-runtime-state",
                "--owned-checkout",
                str(owned_checkouts.owned_root),
                "--json",
                *extra,
            ],
        )
        assert result.exit_code != 0
        payload = json.loads(result.output)
        assert payload["error_code"] == code
    assert hash_tree(owned_checkouts.owned_root) == before


def test_owned_preview_reports_unreadable_history_without_replacing_it(make_owned_checkouts, monkeypatch) -> None:
    checkouts = make_owned_checkouts(topology="coord")
    _prepare(checkouts)
    (checkouts.mission_dir / "status.events.jsonl").write_text("{invalid-history}\n")
    monkeypatch.chdir(checkouts.repository_root)
    before = hash_tree(checkouts.owned_root)
    result = CliRunner().invoke(
        app,
        [
            "backfill-runtime-state",
            "--mission",
            checkouts.mission_slug,
            "--owned-checkout",
            str(checkouts.owned_root),
            "--dry-run",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output  # Existing dry-run contract reports failures in the payload.
    payload = json.loads(result.output)
    assert payload["summary"]["failed"] == 1
    assert payload["results"][0]["failed"] is True
    assert "event log unreadable" in payload["results"][0]["error"]
    assert payload["retained_verification"] is None
    assert payload["canonical_status_adopted"] is False
    assert hash_tree(checkouts.owned_root) == before


def test_owned_preview_preserves_exact_existing_seed_conflict(make_owned_checkouts, monkeypatch) -> None:
    checkouts = make_owned_checkouts(topology="coord")
    _prepare(checkouts)
    owned = resolve_owned_mission(checkouts.repository_root, checkouts.owned_root, checkouts.mission_slug, allowed_topologies=NEXT_OWNED_TOPOLOGIES)
    assert backfill_runtime_state(checkouts.mission_dir, owned=owned).seeded_count > 0
    corrupt_seed_value(checkouts.mission_dir, field_name="assignee", slot_name="assignee", value="altered-synthetic-value")
    before = hash_tree(checkouts.owned_root)
    monkeypatch.chdir(checkouts.repository_root)
    result = CliRunner().invoke(
        app,
        [
            "backfill-runtime-state",
            "--mission",
            checkouts.mission_slug,
            "--owned-checkout",
            str(checkouts.owned_root),
            "--dry-run",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["results"][0]["verify_ok"] is False
    assert payload["retained_verification"]["ok"] is False
    assert payload["retained_verification"]["mismatches"]
    assert payload["canonical_status_adopted"] is False
    assert hash_tree(checkouts.owned_root) == before
