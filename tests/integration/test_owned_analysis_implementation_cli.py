"""#5882: real owner-local recording and implementation over a dirty primary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands._owned_checkout import resolve_owned_or_adopt
from specify_cli.cli.commands.agent.mission import app as mission_app
from specify_cli.cli.commands.agent.workflow import app as action_app
from specify_cli.core.owned_mission import LIFECYCLE_OWNED_TOPOLOGIES
from specify_cli.status.bootstrap import bootstrap_canonical_state
from tests.integration.conftest import OwnedCheckouts, _git

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection, pytest.mark.real_drain_posture]
BODY = "---\nschema: analysis-findings/v1\nfindings: []\n---\n\n# Analysis\nFR-001 is covered by WP01.\n"


@pytest.fixture
def prepared_owner(owned_checkouts: OwnedCheckouts, monkeypatch: pytest.MonkeyPatch, canonical_home: None) -> OwnedCheckouts:
    checkouts = owned_checkouts
    root = checkouts.owned_root
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    monkeypatch.delenv("SPEC_KITTY_PACKS_ROOT", raising=False)
    monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
    monkeypatch.chdir(root)
    charter = root / ".kittify/charter"
    charter.mkdir()
    (charter / "charter.yaml").write_text("mission_type_activations: [software-dev]\n")
    (charter / "charter.md").write_text("# Owner charter\nImplement FR-001 in this checkout.\n")
    (root / ".kittify/config.yaml").write_text("agents:\n  available: [codex]\nmission_type_activations: [software-dev]\n")
    (checkouts.mission_dir / "tasks.md").write_text("# Tasks\n\n## WP01\n- [ ] T001 Implement FR-001 in app.py\n\n## WP02\n- [ ] T002 Verify FR-001\n")
    for wp_id in ("WP01", "WP02"):
        path = checkouts.mission_dir / "tasks" / f"{wp_id}-owned.md"
        path.write_text(path.read_text().replace("owned_files: []", "owned_files: [app.py]") + "\nImplement and verify the owner-local FR-001 contract.\n")
    owned = resolve_owned_or_adopt(checkouts.repository_root, root, checkouts.mission_slug, cwd=root, allowed_topologies=LIFECYCLE_OWNED_TOPOLOGIES)
    assert owned is not None
    seeded = bootstrap_canonical_state(checkouts.mission_dir, checkouts.mission_slug, repo_root=checkouts.repository_root, owned=owned)
    assert seeded.newly_seeded == 2
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "prepare substantive owner planning and status")
    # Partially staged, unstaged and untracked primary work must survive every command.
    primary = checkouts.repository_root
    (primary / "README.md").write_text("staged\n")
    _git(primary, "add", "README.md")
    (primary / "README.md").write_text("staged\nunstaged\n")
    (primary / "untracked-sentinel").write_bytes(b"untracked\x00sentinel")
    return checkouts


def record(checkouts: OwnedCheckouts, *, report_only: bool = False) -> Any:
    args = ["record-analysis", "--mission", checkouts.mission_slug, "--owned-checkout", str(checkouts.owned_root), "--json"]
    if report_only:
        args.append("--report-only")
    return CliRunner().invoke(mission_app, args, input=BODY)


def implement(checkouts: OwnedCheckouts, *extra: str) -> Any:
    return CliRunner().invoke(
        action_app, ["implement", "WP01", "--mission", checkouts.mission_slug, "--owned-checkout", str(checkouts.owned_root), "--agent", "codex", *extra]
    )


def primary_state(checkouts: OwnedCheckouts) -> tuple[str, str, str, bytes, bytes, bytes]:
    root = checkouts.repository_root
    return (
        _git(root, "rev-parse", "HEAD"),
        _git(root, "ls-files", "--stage", "-v"),
        _git(root, "status", "--porcelain=v1"),
        (root / "README.md").read_bytes(),
        (root / "untracked-sentinel").read_bytes(),
        (root / ".git/index").read_bytes(),
    )


@pytest.mark.parametrize("report_only", [False, True])
def test_owned_record_then_implement_reuses_exact_checkout(prepared_owner: OwnedCheckouts, report_only: bool) -> None:
    checkouts = prepared_owner
    before = primary_state(checkouts)
    branches = _git(checkouts.repository_root, "for-each-ref", "--format=%(refname)", "refs/heads")
    worktrees = _git(checkouts.repository_root, "worktree", "list", "--porcelain")
    result = record(checkouts, report_only=report_only)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["stale_repository_root_copy"] is None
    assert payload["path"] == str(checkouts.mission_dir / "analysis-report.md")
    assert payload["input_artifacts"]["charter"]["path"] == ".kittify/charter/charter.yaml"
    from specify_cli.analysis_report import _sha256_file

    assert payload["input_artifacts"]["charter"]["sha256"] == _sha256_file(checkouts.owned_root / ".kittify/charter/charter.yaml")
    assert _git(checkouts.owned_root, "show", "--format=", "--name-only", "HEAD").splitlines() == [f"kitty-specs/{checkouts.mission_slug}/analysis-report.md"]
    result = implement(checkouts)
    assert result.exit_code == 0, result.output
    assert f"Workspace: cd {checkouts.owned_root}" in result.output
    from runtime.next._tmp_namespace import prompt_tmp_dir

    prompt = (prompt_tmp_dir(checkouts.repository_root) / f"spec-kitty-implement-{checkouts.mission_slug}-WP01.md").read_text()
    assert f"Workspace: {checkouts.owned_root}" in prompt
    assert f"Source: {checkouts.owned_root}/.kittify/charter/charter.md" in prompt
    assert f"{checkouts.owned_root}/kitty-specs/{checkouts.mission_slug}" in prompt
    assert f"{checkouts.repository_root}/kitty-specs/{checkouts.mission_slug}" not in prompt
    assert "Workspace contract: owned single_branch write checkout" in prompt
    from specify_cli.status import get_wp_lane, Lane

    assert get_wp_lane(checkouts.mission_dir, "WP01") == Lane.IN_PROGRESS
    assert _git(checkouts.owned_root, "show", "--format=", "--name-only", "HEAD").splitlines() == [
        f"kitty-specs/{checkouts.mission_slug}/status.events.jsonl",
        f"kitty-specs/{checkouts.mission_slug}/status.json",
    ]
    assert _git(checkouts.owned_root, "branch", "--show-current") == checkouts.target_branch
    assert primary_state(checkouts) == before
    assert _git(checkouts.repository_root, "for-each-ref", "--format=%(refname)", "refs/heads") == branches
    assert _git(checkouts.repository_root, "worktree", "list", "--porcelain").replace(
        _git(checkouts.owned_root, "rev-parse", "HEAD"), "OWNER_HEAD"
    ) == worktrees.replace(_git(checkouts.owned_root, "rev-parse", "HEAD~2"), "OWNER_HEAD")


@pytest.mark.parametrize("path", ["spec.md", "plan.md", "tasks.md", "analysis-report.md", "../../.kittify/charter/charter.yaml", "tasks/WP01-owned.md"])
@pytest.mark.parametrize("mutation", ["missing", "stale"])
def test_owned_input_and_report_guard_refuses(prepared_owner: OwnedCheckouts, path: str, mutation: str) -> None:
    checkouts = prepared_owner
    result = record(checkouts, report_only=True)
    assert result.exit_code == 0, result.output
    before = primary_state(checkouts)
    target = checkouts.mission_dir / path
    if mutation == "missing":
        target.unlink()
    else:
        target.write_text(target.read_text() + "\nChanged material requirement.\n")
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    if path == "tasks/WP01-owned.md" and mutation == "missing":
        assert "Work package 'WP01' not found" in result.output, result.output
    else:
        assert "analysis_report_required" in result.output, result.output
    assert primary_state(checkouts) == before


def test_missing_owned_report_cannot_use_primary_copy(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    result = record(checkouts, report_only=True)
    assert result.exit_code == 0, result.output
    report = checkouts.mission_dir / "analysis-report.md"
    primary_report = checkouts.repository_root / "kitty-specs" / checkouts.mission_slug / report.name
    primary_report.parent.mkdir(parents=True)
    primary_report.write_bytes(report.read_bytes())
    report.unlink()
    before = primary_state(checkouts)
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert "missing" in result.output.lower() and "analysis_report_required" in result.output
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("report_only", [False, True])
def test_failed_owned_report_transaction_cannot_unlock(prepared_owner: OwnedCheckouts, report_only: bool) -> None:
    checkouts = prepared_owner
    before = primary_state(checkouts)
    hook = Path(_git(checkouts.owned_root, "rev-parse", "--git-common-dir")) / "hooks/pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    result = record(checkouts, report_only=report_only)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["commit_status"] == "written_uncommitted"
    hook.unlink()
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert "unqualified_report_transaction" in result.output
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("report_only", [False, True])
def test_owned_report_post_commit_index_race_stays_unqualified(prepared_owner: OwnedCheckouts, report_only: bool) -> None:
    checkouts = prepared_owner
    before = primary_state(checkouts)
    hook = Path(_git(checkouts.owned_root, "rev-parse", "--git-common-dir")) / "hooks/post-commit"
    hook.write_text("#!/bin/sh\nprintf 'concurrent\\n' > concurrent.txt\ngit add concurrent.txt\n")
    hook.chmod(0o755)
    result = record(checkouts, report_only=report_only)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["commit_status"] == "committed_unqualified"
    hook.unlink()
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert "unqualified_report_transaction" in result.output
    assert _git(checkouts.owned_root, "show", ":concurrent.txt") == "concurrent"
    assert primary_state(checkouts) == before


def test_raw_owned_carrier_refuses_without_claim(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    (checkouts.mission_dir / "analysis-report.md").write_text(BODY)
    before = primary_state(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert "carrier format" in result.output
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("path", ["spec.md", "plan.md", "tasks.md", "../../.kittify/charter/charter.yaml", "tasks/WP01-owned.md"])
def test_dirty_owned_material_refuses_recording(prepared_owner: OwnedCheckouts, path: str) -> None:
    checkouts = prepared_owner
    target = checkouts.mission_dir / path
    target.write_text(target.read_text() + "\n# changed\n")
    before = primary_state(checkouts)
    head = _git(checkouts.owned_root, "rev-parse", "HEAD")
    result = record(checkouts, report_only=True)
    assert result.exit_code == 1, result.output
    assert "DIRTY_ANALYSIS_INPUT" in result.output
    assert not (checkouts.mission_dir / "analysis-report.md").exists()
    assert _git(checkouts.owned_root, "rev-parse", "HEAD") == head
    assert primary_state(checkouts) == before


def test_owned_missing_report_refuses_without_claim(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    before = primary_state(checkouts)
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert "analysis_report_required" in result.output and "Missing:" in result.output
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


def test_owned_dependency_and_dispatch_guards_remain(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    wp = checkouts.mission_dir / "tasks/WP01-owned.md"
    wp.write_text(wp.read_text().replace("dependencies: []", "dependencies: [WP02]"))
    _git(checkouts.owned_root, "add", str(wp))
    _git(checkouts.owned_root, "commit", "-qm", "declare dependency")
    assert record(checkouts, report_only=True).exit_code == 0
    before = primary_state(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert "dependencies_not_satisfied" in result.output
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


def test_owned_dispatch_requires_correlated_model(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    assert record(checkouts, report_only=True).exit_code == 0
    before = primary_state(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    result = implement(checkouts, "--model", "invented-model")
    assert result.exit_code == 1, result.output
    assert "--invocation-id" in result.output
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


def test_owned_checkout_occupancy_blocks_second_wp(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    assert record(checkouts, report_only=True).exit_code == 0
    first = implement(checkouts)
    assert first.exit_code == 0, first.output
    before = primary_state(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    result = CliRunner().invoke(
        action_app, ["implement", "WP02", "--mission", checkouts.mission_slug, "--owned-checkout", str(checkouts.owned_root), "--agent", "codex"]
    )
    assert result.exit_code == 1, result.output
    assert "WRITE_CHECKOUT_OCCUPIED" in result.output, result.output
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


def test_owned_resume_keeps_checkout_and_claim_provenance(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    assert record(checkouts, report_only=True).exit_code == 0
    first = implement(checkouts)
    assert first.exit_code == 0, first.output
    from specify_cli.status import read_events, Lane

    claimed = [event.event_id for event in read_events(checkouts.mission_dir) if event.to_lane == Lane.CLAIMED]
    before = primary_state(checkouts)
    (checkouts.owned_root / "app.py").write_text("# legitimate work in progress\n")
    resumed = implement(checkouts)
    assert resumed.exit_code == 0, resumed.output
    assert [event.event_id for event in read_events(checkouts.mission_dir) if event.to_lane == Lane.CLAIMED] == claimed
    assert (checkouts.owned_root / "app.py").read_text() == "# legitimate work in progress\n"
    assert primary_state(checkouts) == before


def test_owned_claim_commit_failure_rolls_back(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    assert record(checkouts, report_only=True).exit_code == 0
    before = primary_state(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    head = _git(checkouts.owned_root, "rev-parse", "HEAD")
    hook = Path(_git(checkouts.owned_root, "rev-parse", "--git-common-dir")) / "hooks/pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert _git(checkouts.owned_root, "rev-parse", "HEAD") == head
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("report_only", [False, True])
def test_record_uses_owner_with_stale_primary_mission(
    prepared_owner: OwnedCheckouts, stale_root_copy: Any, monkeypatch: pytest.MonkeyPatch, report_only: bool
) -> None:
    checkouts = prepared_owner
    # Preserve the partial index while installing a committed stale primary copy.
    root = checkouts.repository_root
    _git(root, "reset", "--", "README.md")
    stale = stale_root_copy()
    (stale / "analysis-report.md").write_text("# Stale primary report\n")
    (root / "README.md").write_text("staged\n")
    _git(root, "add", "README.md")
    (root / "README.md").write_text("staged\nunstaged\n")
    before = primary_state(checkouts)
    monkeypatch.chdir(root)
    result = record(checkouts, report_only=report_only)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["stale_repository_root_copy"]["path"] == str(stale)
    monkeypatch.chdir(checkouts.owned_root)
    result = implement(checkouts)
    assert result.exit_code == 0, result.output
    assert (stale / "analysis-report.md").read_text() == "# Stale primary report\n"
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("report_only", [False, True])
def test_owned_record_preserves_or_refuses_owner_partial_staging(prepared_owner: OwnedCheckouts, report_only: bool) -> None:
    checkouts = prepared_owner
    root = checkouts.owned_root
    (root / "README.md").write_text("owner staged\n")
    _git(root, "add", "README.md")
    (root / "README.md").write_text("owner staged\nowner unstaged\n")
    (root / "owner-sentinel").write_bytes(b"owner\x00untracked")
    index = _git(root, "ls-files", "--stage", "-v", "--", "README.md")
    before = primary_state(checkouts)
    result = record(checkouts, report_only=report_only)
    assert result.exit_code == (0 if report_only else 1), result.output
    if not report_only:
        assert "DIRTY_WORKTREE" in result.output
        assert not (checkouts.mission_dir / "analysis-report.md").exists()
    else:
        claimed = implement(checkouts)
        assert claimed.exit_code == 1, claimed.output
        assert "WRITE_CHECKOUT_DIRTY" in claimed.output
    assert _git(root, "ls-files", "--stage", "-v", "--", "README.md") == index
    assert (root / "README.md").read_text() == "owner staged\nowner unstaged\n"
    assert (root / "owner-sentinel").read_bytes() == b"owner\x00untracked"
    assert primary_state(checkouts) == before


def test_owned_profile_access_uses_owner_charter(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    wp = checkouts.mission_dir / "tasks/WP01-owned.md"
    wp.write_text(wp.read_text().replace("title: Owned fixture task", "title: Owned fixture task\nagent_profile: python-pedro"))
    config = checkouts.owned_root / ".kittify/config.yaml"
    config.write_text(config.read_text() + "activated_agent_profiles: [python-pedro]\n")
    primary_config = checkouts.repository_root / ".kittify/config.yaml"
    primary_config.write_text(primary_config.read_text() + "activated_agent_profiles: []\n")
    _git(checkouts.owned_root, "add", str(wp), str(config))
    _git(checkouts.owned_root, "commit", "-qm", "assign owner-accessible implementation profile")
    assert record(checkouts, report_only=True).exit_code == 0
    before = primary_state(checkouts)
    result = implement(checkouts, "--profile", "python-pedro")
    assert result.exit_code == 0, result.output
    from specify_cli.status import read_event_stream, reduce

    stream = read_event_stream(checkouts.mission_dir)
    snapshot = reduce(stream.transitions, stream.annotations)
    assert snapshot.work_packages["WP01"]["agent_profile"] == "python-pedro"
    assert primary_state(checkouts) == before


def test_owned_claim_holds_checkout_then_mission_lock(prepared_owner: OwnedCheckouts, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.cli.commands.agent import workflow, workflow_executor
    from specify_cli.status import locking

    checkouts = prepared_owner
    assert record(checkouts, report_only=True).exit_code == 0
    guard = workflow._guard_repo_root_claim
    start = workflow_executor._implement_start_claim
    observed: list[str] = []

    def observe_guard(*args: Any, **kwargs: Any) -> Any:
        assert locking.holds_status_lock(locking._checkout_claim_lock_path(checkouts.owned_root))
        observed.append("checkout")
        return guard(*args, **kwargs)

    def observe_start(*args: Any, **kwargs: Any) -> Any:
        assert locking.holds_status_lock(locking._checkout_claim_lock_path(checkouts.owned_root))
        assert locking.holds_status_lock(locking.feature_status_lock_path(checkouts.repository_root, checkouts.mission_slug))
        observed.append("mission")
        return start(*args, **kwargs)

    # Observers call the real guarded paths; no ownership or source path is replaced.
    monkeypatch.setattr(workflow, "_guard_repo_root_claim", observe_guard)
    monkeypatch.setattr(workflow_executor, "_implement_start_claim", observe_start)
    result = implement(checkouts)
    assert result.exit_code == 0, result.output
    assert observed == ["checkout", "mission"]


@pytest.mark.parametrize("feedback_exists", [False, True])
def test_owned_canonical_feedback_uses_owner_with_stale_primary(prepared_owner: OwnedCheckouts, stale_root_copy: Any, feedback_exists: bool) -> None:
    from specify_cli.coordination.status_transition import emit_status_transition_transactional
    from specify_cli.status import TransitionRequest, Lane

    checkouts = prepared_owner
    _git(checkouts.repository_root, "reset", "--", "README.md")
    stale_root_copy()
    owned = resolve_owned_or_adopt(
        checkouts.repository_root, checkouts.owned_root, checkouts.mission_slug, cwd=checkouts.owned_root, allowed_topologies=LIFECYCLE_OWNED_TOPOLOGIES
    )
    assert owned is not None
    if feedback_exists:
        from specify_cli.review.cycle import create_rejected_review_cycle

        source = checkouts.owned_root / "reviewer-feedback.md"
        source.write_text("# Reviewer findings\n\nOwner-local FR-001 needs an explicit null-input check.\n")
        created = create_rejected_review_cycle(
            main_repo_root=checkouts.repository_root,
            mission_slug=checkouts.mission_slug,
            wp_id="WP01",
            wp_slug="WP01-owned",
            feedback_source=source,
            reviewer_agent="claude",
            owned=owned,
        )
        assert created.artifact_path.parent == checkouts.mission_dir / "tasks/WP01-owned"
        _git(checkouts.owned_root, "add", ".")
        _git(checkouts.owned_root, "commit", "-qm", "retain genuine owner feedback fixture")
    emit_status_transition_transactional(
        TransitionRequest(
            feature_dir=checkouts.mission_dir,
            mission_slug=checkouts.mission_slug,
            wp_id="WP01",
            to_lane=Lane.CLAIMED,
            actor="codex",
            review_ref=f"review-cycle://{checkouts.mission_slug}/WP01-owned/review-cycle-1.md",
            repo_root=checkouts.repository_root,
            owned=owned,
        )
    )
    assert record(checkouts, report_only=True).exit_code == 0
    before = primary_state(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    result = implement(checkouts)
    assert result.exit_code == (0 if feedback_exists else 1), result.output
    if feedback_exists:
        assert "Fix mode" in result.output
        from runtime.next._tmp_namespace import prompt_tmp_dir

        prompt = (prompt_tmp_dir(checkouts.repository_root) / f"spec-kitty-implement-{checkouts.mission_slug}-WP01.md").read_text()
        assert "Owner-local FR-001 needs an explicit null-input check" in prompt
    else:
        assert "review feedback artifact is missing or unreadable" in result.output
        assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


def test_owned_implementation_retains_write_intent_refusal(prepared_owner: OwnedCheckouts, monkeypatch: pytest.MonkeyPatch) -> None:
    checkouts = prepared_owner
    assert record(checkouts, report_only=True).exit_code == 0
    before = primary_state(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    monkeypatch.chdir(checkouts.repository_root)
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert "There is no repository-root allowance for an owned checkout" in result.output
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


def test_owned_implementation_retains_sparse_preflight(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    assert record(checkouts, report_only=True).exit_code == 0
    _git(checkouts.owned_root, "config", "extensions.worktreeConfig", "true")
    _git(checkouts.owned_root, "config", "--worktree", "core.sparseCheckout", "true")
    before = primary_state(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert "legacy sparse-checkout state detected" in result.output
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


def test_owned_record_requires_owner_charter(prepared_owner: OwnedCheckouts) -> None:
    checkouts = prepared_owner
    for name in ("charter.yaml", "charter.md"):
        (checkouts.owned_root / ".kittify/charter" / name).unlink()
    _git(checkouts.owned_root, "add", ".kittify/charter")
    _git(checkouts.owned_root, "commit", "-qm", "fixture without charter")
    before = primary_state(checkouts)
    result = record(checkouts, report_only=True)
    assert result.exit_code == 1, result.output
    assert "Required owned charter missing" in result.output
    assert not (checkouts.mission_dir / "analysis-report.md").exists()
    assert primary_state(checkouts) == before


def _assert_owned_analysis_refused_without_claim(checkouts: OwnedCheckouts) -> None:
    before = primary_state(checkouts)
    owner_head = _git(checkouts.owned_root, "rev-parse", "HEAD")
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    status = (checkouts.mission_dir / "status.json").read_bytes()
    result = implement(checkouts)
    assert result.exit_code == 1, result.output
    assert "analysis_report_required" in result.output, result.output
    assert _git(checkouts.owned_root, "rev-parse", "HEAD") == owner_head
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert (checkouts.mission_dir / "status.json").read_bytes() == status
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("committed_wp_change", [False, True])
def test_b1_tokenless_canonical_owned_wrapper_refuses(prepared_owner: OwnedCheckouts, committed_wp_change: bool) -> None:
    from specify_cli.analysis_report import write_analysis_report

    checkouts = prepared_owner
    owned = resolve_owned_or_adopt(
        checkouts.repository_root,
        checkouts.owned_root,
        checkouts.mission_slug,
        cwd=checkouts.owned_root,
        allowed_topologies=LIFECYCLE_OWNED_TOPOLOGIES,
    )
    assert owned is not None
    # The public canonical renderer intentionally remains usable without a
    # transaction. Admission must enforce qualification on the read side.
    result = write_analysis_report(feature_dir=checkouts.mission_dir, repo_root=checkouts.owned_root, body=BODY, owned=owned)
    if committed_wp_change:
        wp = checkouts.mission_dir / "tasks/WP01-owned.md"
        wp.write_text(wp.read_text() + "\nSubstantive new FR-001 null-input requirement.\n")
        _git(checkouts.owned_root, "add", str(wp))
    _git(checkouts.owned_root, "add", str(result.path))
    _git(checkouts.owned_root, "commit", "-qm", "retain tokenless owner wrapper fixture")
    _assert_owned_analysis_refused_without_claim(checkouts)


def test_b1_stripped_failed_owned_wrapper_refuses(prepared_owner: OwnedCheckouts) -> None:
    from specify_cli.frontmatter import FrontmatterManager

    checkouts = prepared_owner
    hook = Path(_git(checkouts.owned_root, "rev-parse", "--git-common-dir")) / "hooks/pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    recorded = record(checkouts, report_only=True)
    assert recorded.exit_code == 1, recorded.output
    assert json.loads(recorded.output)["commit_status"] == "written_uncommitted"
    hook.unlink()
    report = checkouts.mission_dir / "analysis-report.md"
    manager = FrontmatterManager()
    metadata, body = manager.read(report)
    metadata.pop("report_transaction")
    metadata.pop("material_manifest_version")
    manager.write(report, metadata, body)
    _git(checkouts.owned_root, "add", str(report))
    _git(checkouts.owned_root, "commit", "-qm", "retain stripped failed report fixture")
    _assert_owned_analysis_refused_without_claim(checkouts)


@pytest.mark.parametrize("mutation", ["missing_version", "unsupported_version", "boolean_version", "missing_wp", "missing_hash", "wrong_path"])
def test_b1_qualified_receipt_requires_complete_owned_manifest(prepared_owner: OwnedCheckouts, mutation: str) -> None:
    from specify_cli.analysis_report import _sha256_file
    from specify_cli.frontmatter import FrontmatterManager
    from specify_cli.git.report_transaction import _receipt_path, report_is_qualified

    checkouts = prepared_owner
    recorded = record(checkouts, report_only=True)
    assert recorded.exit_code == 0, recorded.output
    report = checkouts.mission_dir / "analysis-report.md"
    manager = FrontmatterManager()
    metadata, body = manager.read(report)
    token = metadata["report_transaction"]
    wp_key = f"material:kitty-specs/{checkouts.mission_slug}/tasks/WP01-owned.md"
    if mutation == "missing_version":
        metadata.pop("material_manifest_version")
    elif mutation == "unsupported_version":
        metadata["material_manifest_version"] = 2
    elif mutation == "boolean_version":
        metadata["material_manifest_version"] = True
    elif mutation == "missing_wp":
        metadata["input_artifacts"].pop(wp_key)
    elif mutation == "missing_hash":
        metadata["input_artifacts"]["material:.kittify/missions"].pop("sha256")
    else:
        metadata["input_artifacts"][wp_key]["path"] = "unrelated.md"
    manager.write(report, metadata, body)
    _git(checkouts.owned_root, "add", str(report))
    _git(checkouts.owned_root, "commit", "-qm", "retain malformed manifest fixture")
    # Adversarial local receipt store: make its byte/commit checks genuinely
    # pass, so the read-side manifest requirement is tested independently.
    receipt = _receipt_path(checkouts.owned_root, token)
    receipt.write_text(
        json.dumps(
            {
                "state": "qualified",
                "report": report.relative_to(checkouts.owned_root).as_posix(),
                "sha256": _sha256_file(report),
                "commit": _git(checkouts.owned_root, "rev-parse", "HEAD"),
            }
        )
    )
    assert report_is_qualified(checkouts.owned_root, report, token)
    _assert_owned_analysis_refused_without_claim(checkouts)
