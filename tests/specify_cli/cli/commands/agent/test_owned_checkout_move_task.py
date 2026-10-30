"""Explicit move-task writes only the selected single-branch checkout."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks_move_task as move_task_module
from specify_cli.cli.commands.agent import tasks_move_task_gates
from specify_cli.cli.commands.agent.tasks import app as tasks_app
from tests.integration.test_explicit_checkout_commands import (
    SLUG,
    TARGET,
    checkouts,
    git,
    invoke,
    snapshot,
)
from tests.status.test_transition_request_owned import claim_counter
from specify_cli.workspace.context import clear_workspace_resolution_caches

__all__ = ["checkouts", "claim_counter"]
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def test_owned_gate_baseline_reads_selected_mission_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mission = tmp_path / "kitty-specs" / SLUG
    wp = mission / "tasks" / "WP01-test.md"
    captured: list[Path] = []
    monkeypatch.setattr(
        tasks_move_task_gates.BaselineTestResult,
        "load",
        lambda path: captured.append(path),
    )
    state = SimpleNamespace(
        owned=SimpleNamespace(owned_root=tmp_path),
        wp=SimpleNamespace(path=wp),
        feature_dir=mission,
    )

    move_task_module._mt_resolve_gate_baseline(state)

    assert captured == [mission / "tasks" / "WP01-test" / "baseline-tests.json"]


@pytest.fixture
def finalized_checkouts(checkouts: tuple[Path, Path, Path]) -> tuple[Path, Path, Path]:
    primary, owned, sibling = checkouts
    before = snapshot(primary), snapshot(sibling)
    # Mirror the ``spec-kitty init`` ignore contract: the derived execution-state
    # projection (#4971) lands under ``.kittify/derived/`` and is never tracked.
    (owned / ".gitignore").write_text(".kittify/sync-state.json\n.kittify/derived/\n", encoding="utf-8")
    git(owned, "add", ".gitignore")
    git(owned, "commit", "-qm", "fixture: ignore checkout-local sync bookkeeping and derived views")
    result = invoke("finalize-tasks", owned)
    assert result.exit_code == 0, result.output
    mission = owned / "kitty-specs" / SLUG
    events = [json.loads(line) for line in (mission / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["to_lane"] for row in events if row.get("wp_id") == "WP01"] == ["planned"]
    assert git(owned, "branch", "--show-current") == TARGET
    assert git(owned, "status", "--porcelain") == ""
    assert not (primary / "kitty-specs" / SLUG).exists()
    assert not (sibling / "kitty-specs" / SLUG).exists()
    assert (snapshot(primary), snapshot(sibling)) == before
    return checkouts


def test_finalized_work_is_readable_in_selected_checkout(finalized_checkouts):
    primary, owned, sibling = finalized_checkouts
    before = tuple(snapshot(root) for root in finalized_checkouts)
    result = invoke("check-prerequisites", owned, "--include-tasks")
    assert result.exit_code == 0, result.output
    assert Path(json.loads(result.output)["paths"]["feature_dir"]) == owned / "kitty-specs" / SLUG
    assert tuple(snapshot(root) for root in (primary, owned, sibling)) == before


def test_flagless_move_task_preserves_primary_lookup(finalized_checkouts, monkeypatch):
    """FR-022 control: flagless from the repository root checkout has nothing to adopt."""
    monkeypatch.chdir(finalized_checkouts[0])
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(finalized_checkouts[0]))
    before = tuple(snapshot(root) for root in finalized_checkouts)
    result = CliRunner().invoke(
        tasks_app,
        ["move-task", "WP01", "--to", "doing", "--agent", "codex", "--mission", SLUG, "--json"],
    )
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["error_code"] == "MISSION_NOT_FOUND"
    assert payload["handle"] == SLUG
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


def test_flagless_move_task_from_inside_owned_checkout_adopts_with_one_validation(finalized_checkouts, claim_counter):
    """FR-021 adoption row: flagless from inside the owned checkout adopts it, validating once."""
    _primary, owned, _sibling = finalized_checkouts
    clear_workspace_resolution_caches()
    claim_counter.clear()
    result = CliRunner().invoke(
        tasks_app,
        ["move-task", "WP01", "--to", "doing", "--agent", "codex", "--mission", SLUG, "--json"],
    )
    assert result.exit_code == 0, result.output
    assert len(claim_counter) == 1, claim_counter
    events = [json.loads(line) for line in (owned / "kitty-specs" / SLUG / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["to_lane"] for row in events if row.get("wp_id") == "WP01" and "to_lane" in row][-1] == "in_progress"


@pytest.mark.parametrize("caller", ["owned", "primary", "sibling"])
@pytest.mark.parametrize("shadow", [False, True], ids=["unique", "same_slug"])
def test_move_task_starts_work_finalized_in_linked_checkout(finalized_checkouts, monkeypatch, caller, shadow):
    primary, owned, sibling = finalized_checkouts
    if shadow:
        for other in (primary, sibling):
            mission = other / "kitty-specs" / SLUG
            shutil.copytree(owned / "kitty-specs" / SLUG, mission)
            events_path = mission / "status.events.jsonl"
            events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
            for event in events:
                if event.get("wp_id") == "WP01" and "to_lane" in event:
                    event["wp_id"] = "WP99"
            events_path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
            # A same-slug SHADOW work package on the non-selected partition. It
            # must be a READABLE WP file (valid frontmatter, no dependencies), not
            # a malformed stub: the in-lock dependency gate resolves WP readiness
            # from the primary partition, and the fail-closed policy (mission
            # fsm-write-path-integrity-01M1TZV6) refuses the transition when it
            # meets an unparseable WP file. The point of the fixture is that
            # move-task still resolves the OWNED checkout's WP over this shadow —
            # not that a corrupt shadow blocks the move.
            (mission / "tasks/WP01-test.md").write_text(
                "---\nwork_package_id: WP01\ntitle: not the selected work package\n"
                "dependencies: []\nrequirement_refs: []\nsubtasks: []\nowned_files: []\n"
                "authoritative_surface: app.py\nexecution_mode: code_change\n---\n\n"
                "# not the selected work package\n",
                encoding="utf-8",
            )
    cwd = {"owned": owned, "primary": primary, "sibling": sibling}[caller]
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(cwd))
    before = tuple(snapshot(root) for root in finalized_checkouts)
    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "codex",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--note",
            "owned note",
            "--assignee",
            "worker",
            "--tracker-ref",
            "test-123",
            "--json",
        ],
    )
    assert (snapshot(primary), snapshot(sibling)) == (before[0], before[2])
    if result.exit_code:
        # A failed lookup must not seed status or stage/commit anything.
        assert snapshot(owned) == before[1]
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert Path(payload["path"]) == owned / "kitty-specs" / SLUG / "tasks/WP01-test.md"
    assert Path(payload["status_events_path"]) == owned / "kitty-specs" / SLUG / "status.events.jsonl"
    mission = owned / "kitty-specs" / SLUG
    events = [json.loads(line) for line in (mission / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
    transitions = [row for row in events if row.get("wp_id") == "WP01" and "to_lane" in row]
    assert transitions[-1]["to_lane"] == "in_progress"
    assert transitions[-1]["actor"] == "codex"
    assert git(owned, "branch", "--show-current") == TARGET
    assert git(owned, "rev-parse", "HEAD") != before[1][0]
    assert git(owned, "status", "--porcelain") == ""
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["agent"] == "codex"
    assert state["assignee"] == "worker"
    assert state["tracker_refs"] == ["test-123"]
    committed = git(owned, "show", f"HEAD:kitty-specs/{SLUG}/status.events.jsonl")
    assert json.loads(committed.splitlines()[-1])["delta"]["note"] == "owned note"


def test_owned_move_task_completes_with_sync_active(finalized_checkouts, monkeypatch):
    """#3980: the ``OWNED_SYNC_UNSUPPORTED`` refusal is gone — an owned
    ``move-task --to doing`` completes with hosted sync on (the fan-out
    handlers on the emit seam are bounded and non-raising, and the Zeitgeist
    moment handler no-ops without a session/team)."""
    primary, owned, sibling = finalized_checkouts
    monkeypatch.chdir(owned)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(owned))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    before = tuple(snapshot(root) for root in finalized_checkouts)

    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "codex",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (snapshot(primary), snapshot(sibling)) == (before[0], before[2])
    mission = owned / "kitty-specs" / SLUG
    events = [json.loads(line) for line in (mission / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
    transitions = [row for row in events if row.get("wp_id") == "WP01" and "to_lane" in row]
    assert transitions[-1]["to_lane"] == "in_progress"


@pytest.mark.parametrize("explicit_auto_commit", [False, True])
def test_owned_status_commit_override_preserves_project_preference(finalized_checkouts, monkeypatch, explicit_auto_commit):
    """An atomic status commit need not enable automatic commits project-wide."""
    from specify_cli.core.agent_config import load_agent_config, save_agent_config

    primary, owned, sibling = finalized_checkouts
    config = load_agent_config(owned)
    config.auto_commit = False
    save_agent_config(owned, config)
    git(owned, "add", ".kittify/config.yaml")
    git(owned, "commit", "-qm", "fixture: preserve manual commit preference")
    config_bytes = (owned / ".kittify/config.yaml").read_bytes()
    monkeypatch.chdir(owned)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(owned))
    before = tuple(snapshot(root) for root in finalized_checkouts)
    args = [
        "move-task",
        "WP01",
        "--to",
        "doing",
        "--agent",
        "codex",
        "--mission",
        SLUG,
        "--owned-checkout",
        str(owned),
        "--json",
    ]
    if explicit_auto_commit:
        args.append("--auto-commit")
    result = CliRunner().invoke(tasks_app, args)
    assert (snapshot(primary), snapshot(sibling)) == (before[0], before[2])
    assert (owned / ".kittify/config.yaml").read_bytes() == config_bytes
    assert load_agent_config(owned).auto_commit is False
    if not explicit_auto_commit:
        assert result.exit_code != 0
        assert "OWNED_OPTION_UNSUPPORTED" in result.output
        assert snapshot(owned) == before[1]
        return
    assert result.exit_code == 0, result.output
    assert git(owned, "rev-parse", "HEAD") != before[1][0]
    assert git(owned, "status", "--porcelain") == ""
    committed = git(owned, "show", f"HEAD:kitty-specs/{SLUG}/status.events.jsonl")
    events = [json.loads(line) for line in committed.splitlines()]
    transitions = [row for row in events if row.get("wp_id") == "WP01" and "to_lane" in row]
    assert transitions[-1]["to_lane"] == "in_progress"


@pytest.mark.parametrize(
    "case,code",
    [
        ("nested", "OWNERSHIP_NESTED"),
        ("foreign", "OWNERSHIP_FOREIGN"),
        ("missing_mission", "FEATURE_CONTEXT_UNRESOLVED"),
        ("protected", "OWNED_BRANCH_REFUSED"),
        ("wrong_branch", "OWNED_BRANCH_REFUSED"),
        ("staged", "OWNED_INDEX_REFUSED"),
        ("topology", "OWNED_TOPOLOGY_UNSUPPORTED"),
        ("done", "OWNED_TRANSITION_UNSUPPORTED"),
        ("force", "OWNED_OPTION_UNSUPPORTED"),
        ("skip", "OWNED_OPTION_UNSUPPORTED"),
        ("no_commit", "OWNED_OPTION_UNSUPPORTED"),
        ("bad_pid", "OWNED_INPUT_INVALID"),
    ],
)
def test_owned_preflight_refuses_before_effects(checkouts, tmp_path, monkeypatch, case, code):
    primary, owned, sibling = checkouts
    checkout = owned
    target = "doing"
    extra = []
    if case == "nested":
        checkout = owned / "kitty-specs"
    elif case == "foreign":
        checkout = tmp_path / "foreign"
        checkout.mkdir()
        git(checkout, "init", "-q", "-b", "main")
    elif case == "protected":
        with (primary / ".kittify/config.yaml").open("a", encoding="utf-8") as config:
            config.write("\nprotection:\n  protected_branches: [main, codex/owned]\n")
    elif case == "wrong_branch":
        git(owned, "checkout", "-qb", "codex/wrong")
    elif case == "staged":
        (owned / "app.py").write_text("VALUE = 999\n", encoding="utf-8")
        git(owned, "add", "app.py")
    elif case == "topology":
        path = owned / "kitty-specs" / SLUG / "meta.json"
        meta = json.loads(path.read_text(encoding="utf-8"))
        meta["topology"] = "coord"
        path.write_text(json.dumps(meta), encoding="utf-8")
    elif case in ("review", "done"):
        target = "for_review" if case == "review" else "done"
    elif case in ("force", "skip", "no_commit"):
        extra = [{"force": "--force", "skip": "--skip-pre-review-gate", "no_commit": "--no-auto-commit"}[case]]
    elif case == "bad_pid":
        extra = ["--shell-pid", "not-a-number"]
    args = ["move-task", "WP01", "--to", target, "--owned-checkout", str(checkout), "--json", *extra]
    if case != "missing_mission":
        args += ["--mission", SLUG]
    before = tuple(snapshot(root) for root in checkouts)
    result = CliRunner().invoke(tasks_app, args)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == code
    assert tuple(snapshot(root) for root in (primary, owned, sibling)) == before


@pytest.mark.parametrize("explicit", [False, True])
def test_context_error_envelope_is_opt_in(checkouts, monkeypatch, explicit):
    from mission_runtime import ActionContextError
    from specify_cli.cli.commands.agent import tasks_move_task

    def fail_context(*args):
        raise ActionContextError("TEST_CONTEXT", "context refused")

    monkeypatch.setattr(tasks_move_task, "_mt_resolve_targets", fail_context)
    args = ["move-task", "WP01", "--to", "doing", "--json"]
    if explicit:
        # WP16: ownership is validated at the Typer edge before the command body
        # runs, so an explicit opt-in must name its mission (the body is what the
        # patched ``_mt_resolve_targets`` replaces).
        args += ["--mission", SLUG, "--owned-checkout", str(checkouts[1])]
    before = tuple(snapshot(root) for root in checkouts)
    result = CliRunner().invoke(tasks_app, args)
    assert result.exit_code == 1, result.output
    expected = {"error": "context refused"}
    if explicit:
        expected["error_code"] = "TEST_CONTEXT"
    assert json.loads(result.output) == expected
    assert tuple(snapshot(root) for root in checkouts) == before


def test_claim_start_with_pid_and_repeated_start_refused(finalized_checkouts):
    primary, owned, sibling = finalized_checkouts
    before = snapshot(primary), snapshot(sibling)
    mission = owned / "kitty-specs" / SLUG
    for target, expected_lane, assignee in [
        ("claimed", "claimed", "first"),
        ("doing", "in_progress", "second"),
    ]:
        result = CliRunner().invoke(
            tasks_app,
            [
                "move-task",
                "WP01",
                "--to",
                target,
                "--agent",
                "codex",
                "--shell-pid",
                str(os.getpid()),
                "--assignee",
                assignee,
                "--mission",
                SLUG,
                "--owned-checkout",
                str(owned),
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
        assert state["lane"] == expected_lane
        assert state["assignee"] == assignee
        assert state["agent"] == "codex"
        assert state["shell_pid"] == os.getpid()
        assert git(owned, "status", "--porcelain") == ""
        assert (snapshot(primary), snapshot(sibling)) == before
    owned_before = snapshot(owned)
    repeated = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "codex",
            "--assignee",
            "third",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert repeated.exit_code == 1, repeated.output
    assert json.loads(repeated.output)["code"] == "invalid_transition"
    assert snapshot(owned) == owned_before
    assert (snapshot(primary), snapshot(sibling)) == before


@pytest.mark.parametrize("advance_planning", [False, True])
def test_move_task_enters_review_against_selected_checkout_planning_commit(finalized_checkouts, monkeypatch, advance_planning):
    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    mission = owned / "kitty-specs" / SLUG

    started = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "codex",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert started.exit_code == 0, started.output

    # The allocator's implement/claim seam records this canonical immutable ref.
    # move-task alone changes status; it does not allocate the workspace.
    from specify_cli.lanes.claim_base import read_claim_base, record_claim_base

    claim_base = record_claim_base(primary, owned, SLUG, "WP01")
    assert read_claim_base(primary, SLUG, "WP01") == claim_base

    manifest = json.loads((mission / "lanes.json").read_text(encoding="utf-8"))
    planning_commit = manifest["planning_commit_sha"]
    assert len(planning_commit) == 40
    git(owned, "cat-file", "-e", f"{planning_commit}^{{commit}}")

    (owned / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    git(owned, "add", "app.py")
    git(owned, "commit", "-qm", "test: implement owned work package")
    implementation_commit = git(owned, "rev-parse", "HEAD")
    assert implementation_commit != planning_commit
    assert git(owned, "merge-base", planning_commit, implementation_commit) == planning_commit

    if advance_planning:
        plan = mission / "plan.md"
        plan.write_text(plan.read_text(encoding="utf-8") + "\nGenuine later planning amendment.\n", encoding="utf-8")
        git(owned, "add", str(plan.relative_to(owned)))
        git(owned, "commit", "-qm", "test: amend planning after implementation")
        refreshed = invoke("finalize-tasks", owned)
        assert refreshed.exit_code == 0, refreshed.output
        latest = json.loads((mission / "lanes.json").read_text(encoding="utf-8"))["planning_commit_sha"]
        assert latest != planning_commit
        assert git(owned, "diff", "--name-only", f"{latest}..HEAD", "--", "app.py") == ""

    monkeypatch.chdir(primary)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(primary))
    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "for_review",
            "--agent",
            "codex",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["new_lane"] == "for_review"
    assert Path(payload["path"]) == mission / "tasks/WP01-test.md"
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["lane"] == "for_review"
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_owned_review_auto_commits_selected_checkout_deliverables(finalized_checkouts):
    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    started = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "codex",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert started.exit_code == 0, started.output

    (owned / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "for_review",
            "--agent",
            "codex",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert git(owned, "show", "HEAD:app.py") == "VALUE = 3"
    messages = git(owned, "log", "--format=%s", "--all").splitlines()
    assert "chore(WP01): commit lane deliverables for review" in messages
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_owned_review_refuses_status_only_commits(finalized_checkouts):
    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    started = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "implementer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert started.exit_code == 0, started.output
    before_review = git(owned, "rev-parse", "HEAD")

    submitted = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "for_review",
            "--agent",
            "implementer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert submitted.exit_code == 1, submitted.output
    assert json.loads(submitted.output)["error_code"] == "OWNED_IMPLEMENTATION_MISSING"
    assert git(owned, "rev-parse", "HEAD") == before_review
    mission = owned / "kitty-specs" / SLUG
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["lane"] == "in_progress"
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == other_before


def _squashed_review_source(
    finalized_checkouts: tuple[Path, Path, Path], *, implementation: bool = True, second_owned_path: bool = False, preclaim_implementation: bool = False
) -> tuple[str, str]:
    """Deliver a real source tree by squash, then use the public pin refresh."""
    _primary, owned, _sibling = finalized_checkouts
    if second_owned_path:
        from specify_cli.frontmatter import FrontmatterManager

        FrontmatterManager().update_fields(owned / "kitty-specs" / SLUG / "tasks/WP01-test.md", {"owned_files": ["app.py", "other.py"]})
        (owned / "other.py").write_text("VALUE = 1\n", encoding="utf-8")
        git(owned, "add", "kitty-specs", "other.py")
        git(owned, "commit", "-qm", "declare and seed the second owned fixture path")
    # The original immutable planning base must already carry the canonical
    # authored contract, rather than pre-finalization fixture text.
    prepared = invoke("finalize-tasks", owned, "--refresh-planning-commit")
    assert prepared.exit_code == 0, prepared.output
    if preclaim_implementation:
        (owned / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        git(owned, "add", "app.py")
        git(owned, "commit", "-qm", "implementation before this task claim")
    parent = git(owned, "rev-parse", "HEAD")
    started = CliRunner().invoke(
        tasks_app,
        ["move-task", "WP01", "--to", "doing", "--agent", "implementer", "--mission", SLUG, "--owned-checkout", str(owned), "--json"],
    )
    assert started.exit_code == 0, started.output
    if preclaim_implementation:
        from specify_cli.lanes.claim_base import record_claim_base

        parent = record_claim_base(_primary, owned, SLUG, "WP01")
        plan = owned / "kitty-specs" / SLUG / "plan.md"
        plan.write_text(plan.read_text(encoding="utf-8") + "\nPost-claim planning clarification.\n", encoding="utf-8")
        git(owned, "add", "kitty-specs")
        git(owned, "commit", "-qm", "planning-only change after the claim")
    if implementation:
        (owned / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        git(owned, "add", "app.py")
        if second_owned_path:
            (owned / "other.py").write_text("VALUE = 2\n", encoding="utf-8")
            git(owned, "add", "other.py")
        git(owned, "commit", "-qm", "implement the declared task")
    source = git(owned, "rev-parse", "HEAD")
    git(owned, "branch", "recovery/original-review-source", source)
    tree = git(owned, "rev-parse", f"{source}^{{tree}}")
    delivery = git(owned, "commit-tree", tree, "-p", parent, "-m", "squash delivery")
    assert source != delivery
    git(owned, "reset", "--hard", delivery)
    refreshed = invoke("finalize-tasks", owned, "--refresh-planning-commit")
    assert refreshed.exit_code == 0, refreshed.output
    manifest = json.loads((owned / "kitty-specs" / SLUG / "lanes.json").read_text(encoding="utf-8"))
    assert manifest["planning_commit_sha"] == delivery
    assert git(owned, "rev-parse", f"{delivery}^{{tree}}") == tree
    assert git(owned, "status", "--porcelain") == ""
    return source, delivery


def _source_review_args(owned: Path, source: str | None = None, delivery: str | None = None) -> list[str]:
    args = [
        "move-task",
        "WP01",
        "--to",
        "for_review",
        "--agent",
        "implementer",
        "--mission",
        SLUG,
        "--owned-checkout",
        str(owned),
        "--json",
    ]
    if source is not None:
        args.extend(["--review-source-commit", source])
    if delivery is not None:
        args.extend(["--review-delivery-commit", delivery])
    return args


def test_squash_then_planning_refresh_still_requires_explicit_review_source(finalized_checkouts):
    _squashed_review_source(finalized_checkouts)
    _primary, owned, _sibling = finalized_checkouts
    before = tuple(snapshot(root) for root in finalized_checkouts)
    refused = CliRunner().invoke(tasks_app, _source_review_args(owned))
    assert refused.exit_code == 1, refused.output
    assert json.loads(refused.output)["error_code"] == "OWNED_IMPLEMENTATION_MISSING"
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


def test_explicit_review_source_reconciles_identical_squash_after_real_pin_refresh(finalized_checkouts):
    source, delivery = _squashed_review_source(finalized_checkouts)
    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    submitted = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert submitted.exit_code == 0, submitted.output
    mission = owned / "kitty-specs" / SLUG
    events = [json.loads(line) for line in (mission / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["to_lane"] for row in events if row.get("wp_id") == "WP01" and "to_lane" in row][-1] == "for_review"
    assert git(owned, "show", "HEAD:app.py") == "VALUE = 2"
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_explicit_review_source_does_not_turn_status_history_into_implementation(finalized_checkouts):
    source, delivery = _squashed_review_source(finalized_checkouts, implementation=False)
    _primary, owned, _sibling = finalized_checkouts
    before = tuple(snapshot(root) for root in finalized_checkouts)
    refused = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert refused.exit_code == 1, refused.output
    assert json.loads(refused.output)["error_code"] == "OWNED_REVIEW_SOURCE_INVALID"
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


@pytest.mark.parametrize("authority", ["wp", "meta", "lanes"])
@pytest.mark.parametrize("staged", [False, True], ids=["worktree", "index"])
def test_review_source_minter_refuses_dirty_authored_authority(finalized_checkouts, authority, staged):
    from mission_runtime import ActionContextError
    from specify_cli.core.owned_mission import resolve_owned_mission, resolve_owned_review_source
    from specify_cli.frontmatter import FrontmatterManager

    source, delivery = _squashed_review_source(finalized_checkouts, second_owned_path=True)
    primary, owned, _sibling = finalized_checkouts
    mission = owned / "kitty-specs" / SLUG
    wp = mission / "tasks/WP01-test.md"
    fact = resolve_owned_mission(primary, owned, SLUG)
    if authority == "wp":
        path = wp
        FrontmatterManager().update_fields(path, {"owned_files": ["other.py"]})
    else:
        path = mission / ("meta.json" if authority == "meta" else "lanes.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        if authority == "meta":
            data["purpose_context"] = "changed uncommitted authority"
        else:
            data["computed_from"] = "changed uncommitted authority"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if staged:
        git(owned, "add", path.relative_to(owned).as_posix())
    before = tuple(snapshot(root) for root in finalized_checkouts)
    with pytest.raises(ActionContextError) as failure:
        resolve_owned_review_source(fact, wp, source, delivery, TARGET)
    assert failure.value.code == "OWNED_REVIEW_SOURCE_INVALID"
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


def test_narrowed_dirty_scope_cannot_approve_changed_delivered_code(finalized_checkouts):
    from specify_cli.frontmatter import FrontmatterManager

    source, delivery = _squashed_review_source(finalized_checkouts, second_owned_path=True)
    _primary, owned, _sibling = finalized_checkouts
    submitted = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert submitted.exit_code == 0, submitted.output
    claimed = CliRunner().invoke(
        tasks_app,
        ["move-task", "WP01", "--to", "in_review", "--reviewer", "reviewer", "--mission", SLUG, "--owned-checkout", str(owned), "--json"],
    )
    assert claimed.exit_code == 0, claimed.output
    (owned / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    git(owned, "add", "app.py")
    git(owned, "commit", "-qm", "change delivered implementation after review started")
    FrontmatterManager().update_fields(owned / "kitty-specs" / SLUG / "tasks/WP01-test.md", {"owned_files": ["other.py"]})
    before = tuple(snapshot(root) for root in finalized_checkouts)
    approved = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "approved",
            "--reviewer",
            "reviewer",
            "--approval-ref",
            "local-review",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--review-source-commit",
            source,
            "--review-delivery-commit",
            delivery,
            "--json",
        ],
    )
    assert approved.exit_code == 1, approved.output
    assert "OWNED_REVIEW_SOURCE_INVALID" in approved.output, approved.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


@pytest.mark.parametrize(
    "mutation",
    ["missing-source", "missing-delivery", "same-commit", "different-tree", "changed-owned", "entry-mode", "scope", "mission", "new-attempt", "shallow"],
)
def test_review_source_rejects_changed_identity_history_and_attempt(finalized_checkouts, mutation):
    from specify_cli.frontmatter import FrontmatterManager

    source, delivery = _squashed_review_source(finalized_checkouts)
    _primary, owned, _sibling = finalized_checkouts
    mission = owned / "kitty-specs" / SLUG
    if mutation == "missing-source":
        source = "0" * 40
    elif mutation == "missing-delivery":
        delivery = "0" * 40
    elif mutation == "same-commit":
        delivery = source
    elif mutation == "different-tree":
        (owned / "unrelated.md").write_text("different tree\n", encoding="utf-8")
        git(owned, "add", "unrelated.md")
        git(owned, "commit", "-qm", "different delivered tree")
        delivery = git(owned, "rev-parse", "HEAD")
    elif mutation == "changed-owned":
        (owned / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
        git(owned, "add", "app.py")
        git(owned, "commit", "-qm", "different current implementation")
    elif mutation == "entry-mode":
        (owned / "app.py").chmod(0o755)
        git(owned, "update-index", "--chmod=+x", "--", "app.py")
        git(owned, "commit", "-qm", "same blob with a different executable mode")
        assert git(owned, "rev-parse", "HEAD:app.py") == git(owned, "rev-parse", source + ":app.py")
        assert git(owned, "ls-tree", "HEAD", "app.py").startswith("100755 ")
    elif mutation == "scope":
        FrontmatterManager().update_fields(mission / "tasks/WP01-test.md", {"owned_files": ["app.py", "unadmitted.py"]})
        git(owned, "add", "kitty-specs")
        git(owned, "commit", "-qm", "different authored scope")
    elif mutation == "mission":
        path = mission / "meta.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["purpose_context"] = "different committed mission authority"
        path.write_text(json.dumps(data), encoding="utf-8")
        git(owned, "add", "kitty-specs")
        git(owned, "commit", "-qm", "different mission contract")
    elif mutation == "new-attempt":
        feedback = owned.parent / "different-attempt-feedback.md"
        feedback.write_text("Restore the scoped implementation before another review.\n", encoding="utf-8")
        for lane in ["planned", "doing"]:
            actor = ["--reviewer", "reviewer", "--review-feedback-file", str(feedback)] if lane == "planned" else ["--agent", "implementer"]
            result = CliRunner().invoke(
                tasks_app,
                [
                    "move-task",
                    "WP01",
                    "--to",
                    lane,
                    *actor,
                    "--note",
                    "start a different attempt",
                    "--mission",
                    SLUG,
                    "--owned-checkout",
                    str(owned),
                    "--json",
                ],
            )
            assert result.exit_code == 0, result.output
    else:
        common = Path(git(owned, "rev-parse", "--git-common-dir"))
        if not common.is_absolute():
            common = owned / common
        (common / "shallow").write_text(source + "\n", encoding="ascii")
        assert git(owned, "rev-parse", "--is-shallow-repository") == "true"
    before = tuple(snapshot(root) for root in finalized_checkouts)
    refused = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert refused.exit_code == 1, refused.output
    assert "OWNED_REVIEW_SOURCE_INVALID" in refused.output, refused.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
@pytest.mark.parametrize("boundary", ["minter", "public"])
def test_review_source_refuses_hidden_owned_working_changes(finalized_checkouts, flag, boundary):
    from mission_runtime import ActionContextError
    from specify_cli.core.owned_mission import resolve_owned_mission, resolve_owned_review_source

    source, delivery = _squashed_review_source(finalized_checkouts)
    primary, owned, _sibling = finalized_checkouts
    fact = resolve_owned_mission(primary, owned, SLUG)
    (owned / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    git(owned, "update-index", flag, "--", "app.py")
    assert git(owned, "status", "--porcelain") == ""
    assert (owned / "app.py").read_text(encoding="utf-8") != git(owned, "show", "HEAD:app.py") + "\n"
    before = tuple(snapshot(root) for root in finalized_checkouts)
    if boundary == "minter":
        with pytest.raises(ActionContextError) as failure:
            resolve_owned_review_source(fact, owned / "kitty-specs" / SLUG / "tasks/WP01-test.md", source, delivery, TARGET)
        assert failure.value.code == "OWNED_REVIEW_SOURCE_INVALID"
    else:
        refused = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
        assert refused.exit_code == 1, refused.output
        assert "OWNED_REVIEW_SOURCE_INVALID" in refused.output, refused.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


def test_review_source_does_not_credit_implementation_before_immutable_claim(finalized_checkouts):
    from specify_cli.lanes.claim_base import read_claim_base

    source, delivery = _squashed_review_source(finalized_checkouts, implementation=False, preclaim_implementation=True)
    primary, owned, _sibling = finalized_checkouts
    claim = read_claim_base(primary, SLUG, "WP01", strict=True)
    assert claim is not None and claim != source
    assert git(owned, "diff", "--name-only", claim, source, "--", "app.py") == ""
    before = tuple(snapshot(root) for root in finalized_checkouts)
    refused = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert refused.exit_code == 1, refused.output
    assert "OWNED_REVIEW_SOURCE_INVALID" in refused.output, refused.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


def test_review_source_inspects_normalized_authored_patterns(finalized_checkouts):
    from specify_cli.frontmatter import FrontmatterManager

    _primary, owned, _sibling = finalized_checkouts
    FrontmatterManager().update_fields(owned / "kitty-specs" / SLUG / "tasks/WP01-test.md", {"owned_files": ["./app.py"], "authoritative_surface": "./app.py"})
    git(owned, "add", "kitty-specs")
    git(owned, "commit", "-qm", "declare equivalent relative owned path")
    source, delivery = _squashed_review_source(finalized_checkouts)
    (owned / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    git(owned, "update-index", "--assume-unchanged", "--", "app.py")
    assert git(owned, "status", "--porcelain") == ""
    before = tuple(snapshot(root) for root in finalized_checkouts)
    refused = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert refused.exit_code == 1, refused.output
    assert "OWNED_REVIEW_SOURCE_INVALID" in refused.output, refused.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


def test_explicit_review_source_retains_normal_reviewer_and_durable_verdict(finalized_checkouts):
    source, delivery = _squashed_review_source(finalized_checkouts)
    primary, owned, sibling = finalized_checkouts
    others = snapshot(primary), snapshot(sibling)
    submitted = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert submitted.exit_code == 0, submitted.output
    common = ["move-task", "WP01", "--reviewer", "reviewer", "--mission", SLUG, "--owned-checkout", str(owned), "--json"]
    claimed = CliRunner().invoke(tasks_app, [*common, "--to", "in_review"])
    assert claimed.exit_code == 0, claimed.output
    approved = CliRunner().invoke(
        tasks_app,
        [*common, "--to", "approved", "--approval-ref", "local-review", "--review-source-commit", source, "--review-delivery-commit", delivery],
    )
    assert approved.exit_code == 0, approved.output
    assert json.loads(approved.output)["verdict_durably_persisted"] is True
    mission = owned / "kitty-specs" / SLUG
    assert (mission / "tasks/WP01-test/review-cycle-1.md").is_file()
    assert json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]["lane"] == "approved"
    assert git(owned, "show", "HEAD:app.py") == "VALUE = 2"
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == others


def test_owned_approved_squash_can_complete_only_with_exact_delivery(finalized_checkouts):
    """Post-delivery completion uses the approved attempt, never a primary copy."""
    source, delivery = _squashed_review_source(finalized_checkouts)
    primary, owned, sibling = finalized_checkouts
    others = snapshot(primary), snapshot(sibling)
    submitted = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert submitted.exit_code == 0, submitted.output
    common = ["move-task", "WP01", "--reviewer", "reviewer", "--mission", SLUG, "--owned-checkout", str(owned), "--json"]
    proof = ["--review-source-commit", source, "--review-delivery-commit", delivery]
    before_review = tuple(snapshot(root) for root in finalized_checkouts)
    premature = CliRunner().invoke(tasks_app, [*common, "--to", "done", *proof])
    assert premature.exit_code == 1, premature.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before_review
    claimed = CliRunner().invoke(tasks_app, [*common, "--to", "in_review"])
    assert claimed.exit_code == 0, claimed.output
    approved = CliRunner().invoke(tasks_app, [*common, "--to", "approved", "--approval-ref", "local-review", *proof])
    assert approved.exit_code == 0, approved.output
    before = tuple(snapshot(root) for root in finalized_checkouts)
    refused = CliRunner().invoke(tasks_app, [*common, "--to", "done"])
    assert refused.exit_code == 1, refused.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before
    mismatch = CliRunner().invoke(tasks_app, [*common, "--to", "done", "--review-source-commit", source, "--review-delivery-commit", source])
    assert mismatch.exit_code == 1, mismatch.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before
    forced = CliRunner().invoke(tasks_app, [*common, "--to", "done", "--force", *proof])
    assert forced.exit_code == 1, forced.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before
    (owned / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    dirty_before = tuple(snapshot(root) for root in finalized_checkouts)
    dirty = CliRunner().invoke(tasks_app, [*common, "--to", "done", *proof])
    assert dirty.exit_code == 1, dirty.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == dirty_before
    (owned / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    completed = CliRunner().invoke(tasks_app, [*common, "--to", "done", *proof])
    assert completed.exit_code == 0, completed.output
    mission = owned / "kitty-specs" / SLUG
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["lane"] == "done"
    assert git(owned, "show", "HEAD:app.py") == "VALUE = 2"
    assert git(owned, "status", "--porcelain") == ""
    assert not (primary / "kitty-specs" / SLUG).exists()
    assert (snapshot(primary), snapshot(sibling)) == others


@pytest.mark.parametrize("initial_phase", [None, 0])
@pytest.mark.parametrize("accepted_before_publication", [False, True])
@pytest.mark.parametrize("authored_scope_change", [False, True])
def test_owned_completion_consumes_reviewed_source_published_after_approval(finalized_checkouts, accepted_before_publication, authored_scope_change, initial_phase):
    """Real ordering: implement, review, optionally accept, publish, complete."""
    from specify_cli.acceptance.matrix import AcceptanceCriterion, AcceptanceMatrix, write_acceptance_matrix
    from specify_cli.mission_metadata import write_meta
    from tests.integration.test_explicit_checkout_commands import run_owned_accept

    primary, owned, sibling = finalized_checkouts
    mission = owned / "kitty-specs" / SLUG
    meta = json.loads((mission / "meta.json").read_text(encoding="utf-8"))
    meta.update(created_at="2026-10-30T00:00:00Z", friendly_name="Disposable owned completion")
    if initial_phase is not None:
        meta["status_phase"] = initial_phase
    write_meta(mission, meta)
    for name in ("src", "tests", "docs"):
        (owned / name).mkdir()
        (owned / name / ".gitkeep").touch()
    (mission / "contracts").mkdir()
    (mission / "contracts/.gitkeep").touch()
    write_acceptance_matrix(
        mission,
        AcceptanceMatrix(
            mission_slug=SLUG,
            criteria=[
                AcceptanceCriterion(criterion_id="AC1", description="The owned app contains its validated value", proof_type="automated_test", pass_fail="pass")
            ],
        ),
    )
    git(owned, "add", "kitty-specs", "src", "tests", "docs")
    git(owned, "commit", "-qm", "declare disposable acceptance inputs")
    prepared = invoke("finalize-tasks", owned, "--refresh-planning-commit")
    assert prepared.exit_code == 0, prepared.output
    parent = git(owned, "rev-parse", "HEAD")
    others = snapshot(primary), snapshot(sibling)
    common = ["move-task", "WP01", "--mission", SLUG, "--owned-checkout", str(owned), "--json"]
    started = CliRunner().invoke(tasks_app, [*common, "--to", "doing", "--agent", "implementer"])
    assert started.exit_code == 0, started.output
    (owned / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    git(owned, "add", "app.py")
    git(owned, "commit", "-qm", "implement before review and publication")
    submitted = CliRunner().invoke(tasks_app, [*common, "--to", "for_review", "--agent", "implementer"])
    assert submitted.exit_code == 0, submitted.output
    claimed = CliRunner().invoke(tasks_app, [*common, "--to", "in_review", "--reviewer", "reviewer"])
    assert claimed.exit_code == 0, claimed.output
    approved = CliRunner().invoke(tasks_app, [*common, "--to", "approved", "--reviewer", "reviewer", "--approval-ref", "local-review"])
    assert approved.exit_code == 0, approved.output
    assert (owned / "app.py").read_text(encoding="utf-8") == "VALUE = 2\n"
    if authored_scope_change:
        meta = json.loads((mission / "meta.json").read_text(encoding="utf-8"))
        meta["purpose_context"] = "Unreviewed authored scope change is not acceptance bookkeeping."
        write_meta(mission, meta)
        git(owned, "add", "kitty-specs")
        git(owned, "commit", "-qm", "adversarial authored change before publication")
    if accepted_before_publication:
        accepted = run_owned_accept(owned, SLUG, "--mode", "local", "--actor", "reviewer")
        assert accepted.exit_code == 0, accepted.output
        meta = json.loads((mission / "meta.json").read_text(encoding="utf-8"))
        assert meta["acceptance_history"] and meta["accept_commit"] and meta["status_phase"] == "1"
    source = git(owned, "rev-parse", "HEAD")
    git(owned, "branch", "recovery/approved-original-source", source)
    delivery = git(owned, "commit-tree", git(owned, "rev-parse", source + "^{tree}"), "-p", parent, "-m", "publish approved source by squash")
    git(owned, "reset", "--hard", delivery)
    prepared = invoke("finalize-tasks", owned, "--refresh-planning-commit")
    assert prepared.exit_code == 0, prepared.output
    before_completion = snapshot(owned)
    ordinary_review = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert ordinary_review.exit_code == 1, ordinary_review.output
    assert json.loads(ordinary_review.stdout)["error_code"] == "OWNED_REVIEW_SOURCE_INVALID"
    assert snapshot(owned) == before_completion
    completed = CliRunner().invoke(
        tasks_app,
        [*common, "--to", "done", "--reviewer", "reviewer", "--review-source-commit", source, "--review-delivery-commit", delivery],
    )
    if authored_scope_change:
        assert completed.exit_code == 1, completed.output
        assert json.loads(completed.stdout)["error_code"] == "OWNED_REVIEW_SOURCE_INVALID"
        assert snapshot(owned) == before_completion
    else:
        assert completed.exit_code == 0, completed.output
        assert json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]["lane"] == "done"
    assert not (primary / "kitty-specs" / SLUG).exists()
    assert (snapshot(primary), snapshot(sibling)) == others


@pytest.mark.parametrize("replace_link", [False, True])
def test_review_source_preserves_link_entry_identity_without_reading_target(finalized_checkouts, replace_link):
    from mission_runtime import ActionContextError
    from specify_cli.core.owned_mission import resolve_owned_mission, resolve_owned_review_source
    from specify_cli.frontmatter import FrontmatterManager

    primary, owned, _sibling = finalized_checkouts
    link = owned / "reference"
    # Target content deliberately differs from the stored link text. The
    # positive case cannot pass by comparing dereferenced file bytes.
    (owned / "unowned-source-target").write_text("different target bytes\n", encoding="utf-8")
    link.symlink_to("unowned-source-target")
    FrontmatterManager().update_fields(owned / "kitty-specs" / SLUG / "tasks/WP01-test.md", {"owned_files": ["app.py", "reference"]})
    git(owned, "add", "reference", "unowned-source-target", "kitty-specs")
    git(owned, "commit", "-qm", "declare owned link identity")
    source, delivery = _squashed_review_source(finalized_checkouts)
    fact = resolve_owned_mission(primary, owned, SLUG)
    if replace_link:
        link.unlink()
        link.write_text("unowned-source-target", encoding="utf-8")
        git(owned, "add", "reference")
        assert git(owned, "rev-parse", ":reference") == git(owned, "rev-parse", "HEAD:reference")
    before = tuple(snapshot(root) for root in finalized_checkouts)
    args = (fact, owned / "kitty-specs" / SLUG / "tasks/WP01-test.md", source, delivery, TARGET)
    if replace_link:
        with pytest.raises(ActionContextError) as failure:
            resolve_owned_review_source(*args)
        assert failure.value.code == "OWNED_REVIEW_SOURCE_INVALID"
    else:
        proof = resolve_owned_review_source(*args)
        assert proof.owned_files == ("app.py", "reference")
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


@pytest.mark.parametrize("mutation", ["dirty", "staged", "working-mode", "untracked"])
def test_review_source_refuses_owned_working_drift_without_effects(finalized_checkouts, mutation):
    source, delivery = _squashed_review_source(finalized_checkouts)
    _primary, owned, _sibling = finalized_checkouts
    if mutation == "untracked":
        # The existing directory-prefix ownership convention includes this path.
        (owned / "app.py").unlink()
        (owned / "app.py").mkdir()
        (owned / "app.py" / "untracked.md").write_text("uncommitted implementation\n", encoding="utf-8")
    elif mutation == "working-mode":
        git(owned, "config", "core.filemode", "false")
        (owned / "app.py").chmod(0o755)
        assert git(owned, "status", "--porcelain") == ""
    else:
        (owned / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
        if mutation == "staged":
            git(owned, "add", "app.py")
    before = tuple(snapshot(root) for root in finalized_checkouts)
    refused = CliRunner().invoke(tasks_app, _source_review_args(owned, source, delivery))
    assert refused.exit_code == 1, refused.output
    expected = "OWNED_INDEX_REFUSED" if mutation == "staged" else "OWNED_REVIEW_SOURCE_INVALID"
    assert expected in refused.output, refused.output
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


def test_owned_review_refuses_auto_commit_outside_owned_files(finalized_checkouts):
    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    started = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "implementer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert started.exit_code == 0, started.output
    before_review = git(owned, "rev-parse", "HEAD")
    (owned / "app.py").write_text("VALUE = 5\n", encoding="utf-8")
    (owned / "unrelated.txt").write_text("private draft\n", encoding="utf-8")

    submitted = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "for_review",
            "--agent",
            "implementer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert submitted.exit_code == 1, submitted.output
    assert json.loads(submitted.output)["error_code"] == "OWNED_DELIVERABLE_SCOPE_REFUSED"
    assert git(owned, "rev-parse", "HEAD") == before_review
    assert git(owned, "status", "--porcelain").splitlines() == ["M app.py", "?? unrelated.txt"]
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_owned_review_refuses_a_rename_from_outside_owned_files(finalized_checkouts):
    """Intended behaviour change (git-paths-are-data): a rename stages its source too.

    Moving ``other.py`` onto ``app.py`` deletes ``other.py``, which is outside
    ``owned_files``, so the owned auto-commit refuses rather than committing that
    deletion. The move is unstaged (``mv`` + intent-to-add, a worktree rename):
    a staged ``git mv`` is refused earlier by the clean-index precondition.
    """
    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    started = CliRunner().invoke(
        tasks_app,
        ["move-task", "WP01", "--to", "doing", "--agent", "implementer", "--mission", SLUG, "--owned-checkout", str(owned), "--json"],
    )
    assert started.exit_code == 0, started.output
    git(owned, "rm", "-q", "app.py")
    (owned / "other.py").write_text("VALUE = 7\nOTHER = True\n", encoding="utf-8")
    git(owned, "add", "other.py")
    git(owned, "commit", "-qm", "fixture: move the value into other.py")
    (owned / "other.py").rename(owned / "app.py")
    git(owned, "add", "--intent-to-add", "app.py")
    before_review = git(owned, "rev-parse", "HEAD")

    submitted = CliRunner().invoke(
        tasks_app,
        ["move-task", "WP01", "--to", "for_review", "--agent", "implementer", "--mission", SLUG, "--owned-checkout", str(owned), "--json"],
    )

    assert submitted.exit_code == 1, submitted.output
    payload = json.loads(submitted.output)
    assert payload["error_code"] == "OWNED_DELIVERABLE_SCOPE_REFUSED"
    assert "other.py" in json.dumps(payload)
    assert git(owned, "rev-parse", "HEAD") == before_review
    assert git(owned, "status", "--porcelain").splitlines() == ["R other.py -> app.py"]  # git() strips the leading worktree-column space
    assert (snapshot(primary), snapshot(sibling)) == other_before


@pytest.mark.parametrize("invalid_base", [None, "f" * 40, "HEAD"])
def test_owned_review_refuses_invalid_planning_commit_before_effects(finalized_checkouts, monkeypatch, invalid_base):
    primary, owned, _sibling = finalized_checkouts
    started = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "codex",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert started.exit_code == 0, started.output

    lanes_path = owned / "kitty-specs" / SLUG / "lanes.json"
    manifest = json.loads(lanes_path.read_text(encoding="utf-8"))
    manifest["planning_commit_sha"] = git(owned, "rev-parse", "HEAD") if invalid_base == "HEAD" else invalid_base
    lanes_path.write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.chdir(primary)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(primary))
    before = tuple(snapshot(root) for root in finalized_checkouts)
    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "for_review",
            "--agent",
            "codex",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_REVIEW_BASE_INVALID"
    assert tuple(snapshot(root) for root in finalized_checkouts) == before


def _advance_owned_work_to_review(owned: Path) -> Path:
    mission = owned / "kitty-specs" / SLUG
    started = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "implementer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert started.exit_code == 0, started.output
    (owned / "app.py").write_text("VALUE = 4\n", encoding="utf-8")
    submitted = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "for_review",
            "--agent",
            "implementer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert submitted.exit_code == 0, submitted.output
    return mission


def test_owned_review_and_approval_write_only_selected_checkout(finalized_checkouts):
    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    mission = _advance_owned_work_to_review(owned)

    claimed = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "in_review",
            "--reviewer",
            "reviewer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert claimed.exit_code == 0, claimed.output
    approved = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "approved",
            "--reviewer",
            "reviewer",
            "--approval-ref",
            "local-review",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert approved.exit_code == 0, approved.output
    payload = json.loads(approved.output)
    assert payload["new_lane"] == "approved"
    assert payload["verdict_durably_persisted"] is True
    cycle = mission / "tasks" / "WP01-test" / "review-cycle-1.md"
    assert cycle.is_file()
    assert "reviewer_agent: reviewer" in cycle.read_text(encoding="utf-8")
    events = [json.loads(line) for line in (mission / "status.events.jsonl").read_text(encoding="utf-8").splitlines()]
    transitions = [row for row in events if row.get("wp_id") == "WP01" and "to_lane" in row]
    assert [row["to_lane"] for row in transitions] == ["planned", "claimed", "in_progress", "for_review", "in_review", "approved"]
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["lane"] == "approved"
    assert state["agent"] == "implementer"
    assert state["role"] == "reviewer"
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_owned_approval_emit_failure_compensates_selected_verdict(finalized_checkouts, monkeypatch):
    from specify_cli.cli.commands.agent import tasks_move_task

    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    mission = _advance_owned_work_to_review(owned)
    claimed = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "in_review",
            "--reviewer",
            "reviewer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert claimed.exit_code == 0, claimed.output

    def fail_after_verdict(*args, **kwargs):
        raise RuntimeError("injected owned transition failure")

    monkeypatch.setattr(tasks_move_task, "_mt_execute", fail_after_verdict)
    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "approved",
            "--reviewer",
            "reviewer",
            "--approval-ref",
            "local-review",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert result.exit_code == 1, result.output
    cycle_rel = f"kitty-specs/{SLUG}/tasks/WP01-test/review-cycle-1.md"
    assert not (owned / cycle_rel).exists()
    assert cycle_rel not in git(owned, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["lane"] == "in_review"
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_owned_failed_compensation_reports_durable_selected_verdict(finalized_checkouts, monkeypatch):
    from specify_cli.cli.commands.agent import tasks_move_task
    from specify_cli.cli.commands.agent.tasks_verdict_persistence import VerdictRevertError

    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    mission = _advance_owned_work_to_review(owned)
    claimed = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "in_review",
            "--reviewer",
            "reviewer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert claimed.exit_code == 0, claimed.output

    def fail_after_verdict(*args, **kwargs):
        raise RuntimeError("injected owned transition failure")

    def fail_compensation(*args, **kwargs):
        raise VerdictRevertError("injected owned compensation failure")

    monkeypatch.setattr(tasks_move_task, "_mt_execute", fail_after_verdict)
    monkeypatch.setattr(tasks_move_task, "revert_committed_verdict_write", fail_compensation)
    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "approved",
            "--reviewer",
            "reviewer",
            "--approval-ref",
            "local-review",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["result"] == "error"
    assert payload["verdict_durably_persisted"] is True
    assert payload["durability_classification"] == "durable"
    assert "injected owned transition failure" in payload["error"]
    assert "injected owned compensation failure" in payload["error"]
    cycle_rel = f"kitty-specs/{SLUG}/tasks/WP01-test/review-cycle-1.md"
    assert (owned / cycle_rel).is_file()
    assert cycle_rel in git(owned, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    assert payload["evidence_ref"] == cycle_rel
    assert payload["destination_ref"] == TARGET
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["lane"] == "in_review"
    assert state["agent"] == "implementer"
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_owned_rejection_writes_review_and_releases_runtime_claim(finalized_checkouts, tmp_path):
    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    mission = _advance_owned_work_to_review(owned)
    claimed = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "in_review",
            "--reviewer",
            "reviewer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert claimed.exit_code == 0, claimed.output
    feedback = tmp_path / "review-feedback.md"
    feedback.write_text("Нужно исправить реализацию.\n", encoding="utf-8")

    rejected = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "planned",
            "--reviewer",
            "reviewer",
            "--review-feedback-file",
            str(feedback),
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert rejected.exit_code == 0, rejected.output
    payload = json.loads(rejected.output)
    assert payload["new_lane"] == "planned"
    assert payload["runtime_claim_released"] is True
    cycle = mission / "tasks" / "WP01-test" / "review-cycle-1.md"
    assert cycle.is_file()
    assert "reviewer_agent: reviewer" in cycle.read_text(encoding="utf-8")
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["lane"] == "planned"
    assert state.get("agent") is None
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_annotation_failure_does_not_report_success(finalized_checkouts, monkeypatch):
    from mission_runtime import ActionContextError
    from specify_cli.coordination import status_transition

    primary, owned, sibling = finalized_checkouts
    before = snapshot(primary), snapshot(sibling)

    def unavailable(*args, **kwargs):
        raise ActionContextError("OWNED_TRANSACTION_UNAVAILABLE", "annotation unavailable")

    monkeypatch.setattr(status_transition, "emit_inner_state_changed_transactional", unavailable)
    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "doing",
            "--agent",
            "codex",
            "--note",
            "not saved",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["result"] == "error"
    assert payload["error_code"] == "OWNED_TRANSACTION_UNAVAILABLE"
    assert payload["transition_applied"] is True
    assert payload["verdict_durably_persisted"] is False
    mission = owned / "kitty-specs" / SLUG
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["lane"] == "in_progress"
    committed = git(owned, "show", f"HEAD:kitty-specs/{SLUG}/status.events.jsonl")
    assert not any(json.loads(line).get("delta", {}).get("note") == "not saved" for line in committed.splitlines())
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == before


def test_owned_rejection_annotation_failure_retains_durable_evidence(finalized_checkouts, monkeypatch, tmp_path):
    from mission_runtime import ActionContextError
    from specify_cli.coordination import status_transition

    primary, owned, sibling = finalized_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    mission = _advance_owned_work_to_review(owned)
    claimed = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "in_review",
            "--reviewer",
            "reviewer",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )
    assert claimed.exit_code == 0, claimed.output
    feedback = tmp_path / "review-feedback.md"
    feedback.write_text("Нужно исправить реализацию.\n", encoding="utf-8")

    def unavailable(*args, **kwargs):
        raise ActionContextError("OWNED_TRANSACTION_UNAVAILABLE", "annotation unavailable")

    monkeypatch.setattr(status_transition, "emit_inner_state_changed_transactional", unavailable)
    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "planned",
            "--reviewer",
            "reviewer",
            "--review-feedback-file",
            str(feedback),
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned),
            "--json",
        ],
    )

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["result"] == "error"
    assert payload["error_code"] == "OWNED_TRANSACTION_UNAVAILABLE"
    assert payload["transition_applied"] is True
    assert payload["verdict_durably_persisted"] is True
    cycle_rel = f"kitty-specs/{SLUG}/tasks/WP01-test/review-cycle-1.md"
    assert (owned / cycle_rel).is_file()
    assert cycle_rel in git(owned, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    state = json.loads((mission / "status.json").read_text(encoding="utf-8"))["work_packages"]["WP01"]
    assert state["lane"] == "planned"
    assert state["review_result"]["reference"].endswith("review-cycle-1.md")
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_owned_ports_read_and_commit_only_selected_mission(checkouts):
    from mission_runtime import MissionArtifactKind
    from specify_cli.agent_tasks_ports import MissionHandle, RealCoordCommitRouter, RealFsReader
    from specify_cli.core.owned_mission import resolve_owned_mission
    from specify_cli.git.protection_policy import ProtectionPolicy

    primary, owned, sibling = checkouts
    mission = owned / "kitty-specs" / SLUG
    handle = MissionHandle(primary, SLUG, owned=resolve_owned_mission(primary, owned, SLUG))
    reader = RealFsReader()
    before = snapshot(primary), snapshot(sibling)
    assert reader.planning_read_dir(handle, kind=MissionArtifactKind.TASKS_INDEX) == mission
    assert reader.wp_tasks_dir(handle) == mission / "tasks"
    assert reader.primary_anchor_dir(handle) == mission
    spec = mission / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8") + "\nOwned port edit.\n", encoding="utf-8")
    result = RealCoordCommitRouter().commit_artifact(
        handle,
        [spec],
        "owned artifact",
        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
        policy=ProtectionPolicy.resolve(primary),
    )
    assert result.status == "committed"
    assert result.placement_ref == TARGET
    assert "Owned port edit." in git(owned, "show", f"HEAD:kitty-specs/{SLUG}/spec.md")
    assert (snapshot(primary), snapshot(sibling)) == before


# ---------------------------------------------------------------------------
# WP16/T089 (FR-003 / NFR-002): exactly one ownership validation per owned
# ``move-task`` invocation, counted at the ownership-claim primitive so a
# re-introduced local validator call (the #3866 class) goes red.
# ---------------------------------------------------------------------------


def _counted_move_task(claim_counter: list[Path | None], *args: str):
    """Run ``move-task`` after clearing the process-global resolution caches and the counter."""
    clear_workspace_resolution_caches()
    claim_counter.clear()
    return CliRunner().invoke(tasks_app, ["move-task", "WP01", *args, "--mission", SLUG, "--json"])


def test_move_task_claim_validates_ownership_exactly_once(finalized_checkouts, claim_counter):
    _primary, owned, _sibling = finalized_checkouts

    result = _counted_move_task(claim_counter, "--to", "claimed", "--agent", "codex", "--owned-checkout", str(owned))

    assert result.exit_code == 0, result.output
    assert len(claim_counter) == 1, claim_counter


def test_move_task_for_review_validates_ownership_exactly_once(finalized_checkouts, claim_counter):
    """The review hop triggers the most readers (workspace, verdict, readiness); still one validation."""
    _primary, owned, _sibling = finalized_checkouts
    started = CliRunner().invoke(
        tasks_app,
        ["move-task", "WP01", "--to", "doing", "--agent", "implementer", "--mission", SLUG, "--owned-checkout", str(owned), "--json"],
    )
    assert started.exit_code == 0, started.output
    (owned / "app.py").write_text("VALUE = 4\n", encoding="utf-8")

    result = _counted_move_task(claim_counter, "--to", "for_review", "--agent", "implementer", "--owned-checkout", str(owned))

    assert result.exit_code == 0, result.output
    assert len(claim_counter) == 1, claim_counter


def test_move_task_refusal_still_validates_exactly_once(checkouts, claim_counter):
    _primary, owned, _sibling = checkouts

    result = _counted_move_task(claim_counter, "--to", "doing", "--owned-checkout", str(owned / "kitty-specs"))

    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNERSHIP_NESTED"
    assert len(claim_counter) == 1, claim_counter


def test_flagless_move_task_from_repository_root_checkout_validates_nothing(finalized_checkouts, claim_counter, monkeypatch):
    primary, _owned, _sibling = finalized_checkouts
    monkeypatch.chdir(primary)
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(primary))

    result = _counted_move_task(claim_counter, "--to", "claimed", "--agent", "codex")

    assert result.exit_code == 1, result.output
    assert claim_counter == []


def test_owned_move_task_threads_the_fact_and_never_consults_get_main_repo_root(finalized_checkouts, monkeypatch):
    """The owned arm reads the validated fact directly: the annotation emitter receives
    ``owned=`` (never a bare root), and the ``tasks`` namespace's ``get_main_repo_root``
    seam is never consulted for the whole review hop (WP16)."""
    from mission_runtime import OwnedCheckout
    from specify_cli.cli.commands.agent import tasks
    from specify_cli.coordination import status_transition

    _primary, owned, _sibling = finalized_checkouts
    started = CliRunner().invoke(
        tasks_app,
        ["move-task", "WP01", "--to", "doing", "--agent", "implementer", "--mission", SLUG, "--owned-checkout", str(owned), "--json"],
    )
    assert started.exit_code == 0, started.output
    (owned / "app.py").write_text("VALUE = 4\n", encoding="utf-8")

    seen: list[dict[str, object]] = []
    real_emit = status_transition.emit_inner_state_changed_transactional

    def _recording(*args, **kwargs):
        seen.append(kwargs)
        return real_emit(*args, **kwargs)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("an owned run must not consult get_main_repo_root")

    monkeypatch.setattr(status_transition, "emit_inner_state_changed_transactional", _recording)
    monkeypatch.setattr(tasks, "get_main_repo_root", _forbidden)
    clear_workspace_resolution_caches()

    result = CliRunner().invoke(
        tasks_app,
        ["move-task", "WP01", "--to", "for_review", "--agent", "implementer", "--shell-pid", "4242", "--mission", SLUG, "--owned-checkout", str(owned), "--json"],
    )

    assert result.exit_code == 0, result.output
    assert seen, "the runtime-state annotation was never emitted"
    for kwargs in seen:
        assert isinstance(kwargs["owned"], OwnedCheckout)
        assert kwargs["owned"].owned_root == owned.resolve()
        assert "effective_root" not in kwargs


@pytest.mark.parametrize("invalid_claim", ["head", "orphan", "blob", "broken"])
def test_owned_review_refuses_invalid_claim_base_without_planning_fallback(finalized_checkouts, invalid_claim):
    primary, owned, sibling = finalized_checkouts
    args = ["move-task", "WP01", "--agent", "codex", "--mission", SLUG, "--owned-checkout", str(owned), "--json"]
    started = CliRunner().invoke(tasks_app, [*args, "--to", "doing"])
    assert started.exit_code == 0, started.output
    (owned / "app.py").write_text("VALUE = 73\n", encoding="utf-8")
    git(owned, "add", "app.py")
    git(owned, "commit", "-qm", "test: real owned implementation")
    ref = f"refs/spec-kitty/wp-base/{SLUG}/WP01"
    if invalid_claim == "head":
        value = git(owned, "rev-parse", "HEAD")
    elif invalid_claim == "orphan":
        value = git(owned, "commit-tree", "HEAD^{tree}", "-m", "unrelated claim")
    elif invalid_claim == "blob":
        value = git(owned, "rev-parse", "HEAD:app.py")
    else:
        common = Path(git(owned, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        path = common / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("malformed claim ref\n", encoding="utf-8")
        value = None
    if value is not None:
        git(owned, "update-ref", ref, value)
    before = tuple(snapshot(root) for root in (primary, owned, sibling))
    result = CliRunner().invoke(tasks_app, [*args, "--to", "for_review"])
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_REVIEW_BASE_INVALID"
    assert tuple(snapshot(root) for root in (primary, owned, sibling)) == before
