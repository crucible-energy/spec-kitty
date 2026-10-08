"""Local single-branch completion uses genuine owned approval and acceptance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.acceptance.matrix import (
    NegativeInvariant,
    read_acceptance_matrix,
    write_and_commit_acceptance_matrix,
)
from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.cli.commands.merge import merge
from specify_cli.coordination.transaction import BookkeepingTransaction
from tests.integration.test_explicit_checkout_commands import (
    SLUG,
    TARGET,
    checkouts,
    git,
    invoke,
    mission_app,
    run_owned_accept,
    snapshot,
)
from tests.specify_cli.cli.commands.agent.test_owned_checkout_move_task import finalized_checkouts

__all__ = ["checkouts", "finalized_checkouts"]
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
merge_app = typer.Typer()
merge_app.command("merge")(merge)


def _accept_mission(checkouts: tuple[Path, Path, Path], wp_ids: tuple[str, ...], *, with_invariant: bool = False):
    primary, owned, _sibling = checkouts
    meta_path = owned / "kitty-specs" / SLUG / "meta.json"
    meta = json.loads(meta_path.read_text())
    meta.update(created_at="2026-10-08T18:00:00Z", friendly_name="Owned completion fixture")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    git(owned, "add", str(meta_path))
    git(owned, "commit", "-qm", "fixture: complete mission identity")
    mission = meta_path.parent
    (mission / "contracts").mkdir()
    (mission / "contracts/.gitkeep").touch()
    for directory in ("src", "tests", "docs"):
        (owned / directory).mkdir()
        (owned / directory / ".gitkeep").touch()
    git(owned, "add", ".")
    git(owned, "commit", "-qm", "fixture: completed contract inputs")
    for wp in wp_ids:
        file = "app.py" if wp == "WP01" else "app2.py"
        for lane, extra in (
            ("doing", ["--agent", "implementer"]),
            ("for_review", ["--agent", "implementer"]),
            ("in_review", ["--reviewer", "reviewer"]),
            ("approved", ["--reviewer", "reviewer", "--approval-ref", "local-review"]),
        ):
            if lane == "for_review":
                (owned / file).write_text("VALUE = 4\n", encoding="utf-8")
            result = CliRunner().invoke(tasks_app, [
                "move-task", wp, "--to", lane, "--mission", SLUG,
                "--owned-checkout", str(owned), "--json", *extra,
            ])
            assert result.exit_code == 0, result.output
    matrix = read_acceptance_matrix(mission)
    assert matrix is not None and matrix.criteria
    if with_invariant:
        matrix.negative_invariants.append(NegativeInvariant(
            "NI-FIXTURE", "Forbidden fixture file must be absent", "custom_command",
            verification_command="test ! -e forbidden.fixture",
        ))
    for criterion in matrix.criteria:
        criterion.pass_fail = "pass"
        criterion.evidence = "Public fixture asserts selected-checkout preservation"
        criterion.verified_by = "reviewer"
        criterion.verified_at = "2026-10-08T18:00:00Z"
    write_and_commit_acceptance_matrix(
        primary, SLUG, mission, matrix, entry_id="fixture-owned-acceptance",
        message="fixture: reviewed acceptance evidence", effective_root=owned,
    )
    accepted = run_owned_accept(owned, SLUG, "--actor", "fixture-operator", "--mode", "pr")
    assert accepted.exit_code == 0, accepted.output
    assert git(owned, "status", "--porcelain") == ""
    return checkouts


@pytest.fixture
def accepted_checkouts(finalized_checkouts, request):
    return _accept_mission(finalized_checkouts, ("WP01",), with_invariant=getattr(request, "param", None) == "invariant")


def invoke_merge(owned: Path, *extra: str, agent: bool = False):
    app = mission_app if agent else merge_app
    return CliRunner().invoke(app, [
        *(["merge"] if agent else []),
        "--mission", SLUG, "--owned-checkout", str(owned), "--json", *extra,
    ])


def test_owned_preview_is_read_only_and_binds_real_target(accepted_checkouts):
    _primary, owned, _sibling = accepted_checkouts
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned, "--dry-run")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["integration"] == {
        "branch": TARGET, "commit": before[1][0], "kind": "local_target_ref",
    }
    assert payload["consolidation"] == "already_on_target"
    assert payload["remote_delivery"] == "separate_operator_gate"
    assert tuple(snapshot(root) for root in accepted_checkouts) == before


@pytest.mark.parametrize("agent", [False, True])
def test_owned_completion_retains_review_and_preserves_dirty_other_checkouts(accepted_checkouts, agent):
    primary, owned, sibling = accepted_checkouts
    for other in (primary, sibling):
        (other / "app.py").write_text("protected dirty sentinel\n", encoding="utf-8")
    before = snapshot(primary), snapshot(sibling)
    source_commit = git(owned, "rev-parse", "HEAD")
    refs = git(owned, "for-each-ref", "--format=%(refname)")
    result = invoke_merge(owned, agent=agent)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["completed_wps"] == ["WP01"]
    assert payload["integration"]["commit"] == source_commit
    state = json.loads((owned / "kitty-specs" / SLUG / "status.json").read_text())["work_packages"]["WP01"]
    assert state["lane"] == "done"
    assert state["review_result"]["reviewer"] == "reviewer"
    event = json.loads((owned / "kitty-specs" / SLUG / "status.events.jsonl").read_text().splitlines()[-1])
    assert event["evidence"]["repos"][0]["commit"] == source_commit
    assert event["evidence"]["review"]["reference"] == state["review_result"]["reference"]
    assert git(owned, "status", "--porcelain") == ""
    assert git(owned, "for-each-ref", "--format=%(refname)") == refs
    assert (snapshot(primary), snapshot(sibling)) == before
    completed = tuple(snapshot(root) for root in accepted_checkouts)
    repeated = invoke_merge(owned, agent=agent)
    assert repeated.exit_code == 0, repeated.output
    assert json.loads(repeated.output)["integration"]["commit"] == source_commit
    assert tuple(snapshot(root) for root in accepted_checkouts) == completed


@pytest.mark.parametrize("extra", [
    ["--push"], ["--resume"], ["--abort"], ["--delete-branch"], ["--remove-worktree"],
    ["--strategy", "rebase"], ["--skip-review-artifact-check", "--note", "bypass"],
    ["--allow-sparse-checkout"],
])
def test_owned_options_cannot_publish_cleanup_or_relax_guards(checkouts, extra):
    before = tuple(snapshot(root) for root in checkouts)
    result = invoke_merge(checkouts[1], *extra)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_OPTION_UNSUPPORTED"
    assert tuple(snapshot(root) for root in checkouts) == before


@pytest.mark.parametrize("case,code", [
    ("staged", "OWNED_INDEX_REFUSED"), ("dirty", "OWNED_DIRTY_REFUSED"),
    ("wrong_branch", "OWNED_BRANCH_REFUSED"), ("protected", "OWNED_BRANCH_REFUSED"),
    ("target_override", "OWNED_BRANCH_REFUSED"), ("topology", "OWNED_TOPOLOGY_UNSUPPORTED"),
    ("unaccepted", "OWNED_ACCEPTANCE_REFUSED"), ("nested", "OWNERSHIP_NESTED"),
])
def test_owned_owner_and_acceptance_preconditions_refuse_without_effects(checkouts, case, code):
    primary, owned, _sibling = checkouts
    checkout, extra = owned, []
    if case in {"staged", "dirty"}:
        (owned / "app.py").write_text("unaccepted work\n", encoding="utf-8")
        if case == "staged":
            git(owned, "add", "app.py")
    elif case == "wrong_branch":
        git(owned, "checkout", "-qb", "codex/other")
    elif case == "protected":
        (primary / ".kittify/config.yaml").write_text(
            "protection:\n  protected_branches: [main, codex/owned]\n", encoding="utf-8",
        )
    elif case == "target_override":
        extra = ["--target", "main"]
    elif case == "topology":
        path = owned / "kitty-specs" / SLUG / "meta.json"
        meta = json.loads(path.read_text())
        meta["topology"] = "lanes"
        path.write_text(json.dumps(meta), encoding="utf-8")
    elif case == "nested":
        checkout = owned / "kitty-specs"
    before = tuple(snapshot(root) for root in checkouts)
    result = invoke_merge(checkout, *extra)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == code
    assert tuple(snapshot(root) for root in checkouts) == before


@pytest.mark.parametrize("case", ["code", "contract", "matrix", "meta", "event", "snapshot"])
def test_owned_committed_drift_is_not_an_accepted_source(accepted_checkouts, case):
    _primary, owned, _sibling = accepted_checkouts
    mission = owned / "kitty-specs" / SLUG
    if case == "code":
        (owned / "app.py").write_text("VALUE = 999\n", encoding="utf-8")
    elif case == "contract":
        (mission / "spec.md").write_text("# A different source contract\n", encoding="utf-8")
    elif case == "matrix":
        path = mission / "acceptance-matrix.json"
        matrix = json.loads(path.read_text())
        matrix["criteria"][0]["evidence"] = "A later unaccepted claim"
        path.write_text(json.dumps(matrix), encoding="utf-8")
    elif case == "meta":
        path = mission / "meta.json"
        meta = json.loads(path.read_text())
        meta["purpose_tldr"] = "A later unaccepted purpose"
        path.write_text(json.dumps(meta), encoding="utf-8")
    elif case == "event":
        path = mission / "status.events.jsonl"
        path.write_text(path.read_text().replace('"verdict":"approved"', '"verdict":"changes_requested"')
                        .replace('"verdict": "approved"', '"verdict": "changes_requested"'), encoding="utf-8")
    else:
        path = mission / "status.json"
        snapshot_data = json.loads(path.read_text())
        snapshot_data["work_packages"]["WP01"]["lane"] = "done"
        path.write_text(json.dumps(snapshot_data), encoding="utf-8")
    git(owned, "add", ".")
    git(owned, "commit", "-qm", "fixture: post-acceptance drift")
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] in {
        "OWNED_SOURCE_DRIFT", "OWNED_APPROVAL_REFUSED", "OWNED_ACCEPTANCE_REFUSED",
    }
    assert tuple(snapshot(root) for root in accepted_checkouts) == before


def test_owned_source_is_revalidated_under_lock(accepted_checkouts, monkeypatch):
    primary, owned, sibling = accepted_checkouts
    other_before = snapshot(primary), snapshot(sibling)
    events = (owned / "kitty-specs" / SLUG / "status.events.jsonl").read_bytes()
    acquire = BookkeepingTransaction.acquire
    arrived: list[str] = []

    def concurrent_arrival(**kwargs):
        (owned / "app.py").write_text("VALUE = 777\n", encoding="utf-8")
        git(owned, "add", "app.py")
        git(owned, "commit", "-qm", "fixture: source arrived between inspection and lock")
        arrived.append(git(owned, "rev-parse", "HEAD"))
        return acquire(**kwargs)

    monkeypatch.setattr(BookkeepingTransaction, "acquire", concurrent_arrival)
    result = invoke_merge(owned)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_SOURCE_DRIFT"
    assert arrived == [git(owned, "rev-parse", "HEAD")]
    assert (owned / "kitty-specs" / SLUG / "status.events.jsonl").read_bytes() == events
    assert git(owned, "status", "--porcelain") == ""
    assert (snapshot(primary), snapshot(sibling)) == other_before


def test_owned_hook_refusal_rolls_back_terminal_unit(accepted_checkouts):
    primary, owned, sibling = accepted_checkouts
    hooks = Path(git(owned, "rev-parse", "--git-common-dir")) / "hooks"
    hooks.mkdir(exist_ok=True)
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "BOOKKEEPING_COMMIT_FAILED"
    assert tuple(snapshot(root) for root in (primary, owned, sibling)) == before


@pytest.mark.parametrize("accepted_checkouts", ["invariant"], indirect=True)
def test_owned_completion_consumes_real_acceptance_residual_results(accepted_checkouts):
    _primary, owned, _sibling = accepted_checkouts
    matrix = read_acceptance_matrix(owned / "kitty-specs" / SLUG)
    assert matrix is not None and matrix.overall_verdict == "pass"
    assert matrix.negative_invariants[0].result == "confirmed_absent"
    result = invoke_merge(owned)
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("accepted_checkouts", ["invariant"], indirect=True)
def test_producer_commit_label_cannot_authorize_changed_verification_input(accepted_checkouts):
    _primary, owned, _sibling = accepted_checkouts
    path = owned / "kitty-specs" / SLUG / "acceptance-matrix.json"
    data = json.loads(path.read_text())
    data["negative_invariants"][0]["verification_command"] = "a different verification input"
    path.write_text(json.dumps(data), encoding="utf-8")
    git(owned, "add", str(path))
    # Rewrite only a disposable fixture's residual commit to retain a genuine
    # producer label with changed inputs. No owner checkout history is rewritten.
    git(owned, "commit", "--amend", "--no-edit", "-q")
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_SOURCE_DRIFT"
    assert tuple(snapshot(root) for root in accepted_checkouts) == before


def test_owned_multiple_wps_complete_as_one_canonical_transaction(checkouts):
    primary, owned, sibling = checkouts
    mission = owned / "kitty-specs" / SLUG
    task = (mission / "tasks/WP01-test.md").read_text()
    (mission / "tasks/WP02-test.md").write_text(task.replace("WP01", "WP02").replace("app.py", "app2.py"), encoding="utf-8")
    with (mission / "tasks.md").open("a", encoding="utf-8") as outline:
        outline.write("\n## Work Package WP02\n\n**Dependencies**: None\n")
    (owned / "app2.py").write_text("VALUE = 1\n", encoding="utf-8")
    (owned / ".gitignore").write_text(".kittify/sync-state.json\n", encoding="utf-8")
    git(owned, "add", ".")
    git(owned, "commit", "-qm", "fixture: two real single-branch code work packages")
    finalized = invoke("finalize-tasks", owned)
    assert finalized.exit_code == 0, finalized.output
    _accept_mission(checkouts, ("WP01", "WP02"))
    before = snapshot(primary), snapshot(sibling)
    integrated = git(owned, "rev-parse", "HEAD")
    result = invoke_merge(owned)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["completed_wps"] == ["WP01", "WP02"]
    assert git(owned, "rev-parse", "HEAD^") == integrated
    tail = [json.loads(row) for row in (mission / "status.events.jsonl").read_text().splitlines()[-2:]]
    assert [(row["wp_id"], row["from_lane"], row["to_lane"]) for row in tail] == [
        ("WP01", "approved", "done"), ("WP02", "approved", "done"),
    ]
    assert {row["evidence"]["repos"][0]["commit"] for row in tail} == {integrated}
    assert (snapshot(primary), snapshot(sibling)) == before


@pytest.mark.parametrize("case", ["code", "contract", "matrix", "meta"])
@pytest.mark.parametrize("agent,dry_run", [(False, True), (True, True), (False, False), (True, False)])
def test_reverted_post_acceptance_history_is_refused(accepted_checkouts, case, agent, dry_run):
    _primary, owned, _sibling = accepted_checkouts
    mission = owned / "kitty-specs" / SLUG
    path = {"code": owned / "app.py", "contract": mission / "spec.md",
            "matrix": mission / "acceptance-matrix.json", "meta": mission / "meta.json"}[case]
    original = path.read_bytes()
    if case in {"code", "contract"}:
        path.write_text("unaccepted intervening source\n", encoding="utf-8")
    else:
        changed = json.loads(original)
        if case == "matrix":
            changed["criteria"][0]["description"] = "unaccepted criterion"
        else:
            changed["purpose_tldr"] = "unaccepted purpose"
        path.write_text(json.dumps(changed), encoding="utf-8")
    git(owned, "add", str(path))
    git(owned, "commit", "-qm", "fixture: unaccepted intervening change")
    path.write_bytes(original)
    git(owned, "add", str(path))
    git(owned, "commit", "-qm", "fixture: restore accepted endpoint bytes")
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned, *(["--dry-run"] if dry_run else []), agent=agent)
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_SOURCE_DRIFT"
    assert tuple(snapshot(root) for root in accepted_checkouts) == before


@pytest.mark.parametrize("agent", [False, True])
def test_completed_source_cannot_reuse_proof_after_reverted_history(accepted_checkouts, agent):
    _primary, owned, _sibling = accepted_checkouts
    completed = invoke_merge(owned, agent=agent)
    assert completed.exit_code == 0, completed.output
    path = owned / "app.py"
    original = path.read_bytes()
    path.write_text("VALUE = 999\n", encoding="utf-8")
    git(owned, "add", str(path))
    git(owned, "commit", "-qm", "fixture: later unaccepted change")
    path.write_bytes(original)
    git(owned, "add", str(path))
    git(owned, "commit", "-qm", "fixture: restore previously completed bytes")
    before = tuple(snapshot(root) for root in accepted_checkouts)
    repeated = invoke_merge(owned, agent=agent)
    assert repeated.exit_code == 1, repeated.output
    assert json.loads(repeated.output)["error_code"] == "OWNED_SOURCE_DRIFT"
    assert tuple(snapshot(root) for root in accepted_checkouts) == before


def test_producer_sequence_cannot_restore_intermediate_metadata_drift(accepted_checkouts):
    _primary, owned, _sibling = accepted_checkouts
    mission = owned / "kitty-specs" / SLUG
    final_files = {name: (mission / name).read_bytes() for name in (
        "meta.json", "status.json", "status.events.jsonl", "acceptance-matrix.json",
    )}
    accepted = json.loads(final_files["meta.json"])["accept_commit"]
    # Rebuild only this disposable fixture's two producer follow-ups. Their
    # labels and final bytes are genuine; the intermediate purpose is not.
    git(owned, "reset", "--hard", accepted)
    meta = json.loads((mission / "meta.json").read_text())
    meta["accept_commit"] = accepted
    meta["acceptance_history"][-1]["accept_commit"] = accepted
    meta["purpose_tldr"] = "An unaccepted purpose concealed by later restoration"
    (mission / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    git(owned, "add", str(mission / "meta.json"))
    git(owned, "commit", "-qm", f"Record acceptance commit for {SLUG}")
    for name, contents in final_files.items():
        (mission / name).write_bytes(contents)
    git(owned, "add", ".")
    git(owned, "commit", "-qm", f"Finalize acceptance artifacts for {SLUG}")
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned, "--dry-run")
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_SOURCE_DRIFT"
    assert tuple(snapshot(root) for root in accepted_checkouts) == before


def test_empty_post_acceptance_commit_is_not_integration_proof(accepted_checkouts):
    _primary, owned, _sibling = accepted_checkouts
    git(owned, "commit", "--allow-empty", "-qm", "fixture: arbitrary later head")
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned, "--dry-run")
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_SOURCE_DRIFT"
    assert tuple(snapshot(root) for root in accepted_checkouts) == before


@pytest.mark.parametrize("accepted_checkouts", ["invariant"], indirect=True)
def test_acceptance_residual_cannot_rewrite_canonical_event_inputs(accepted_checkouts):
    _primary, owned, _sibling = accepted_checkouts
    path = owned / "kitty-specs" / SLUG / "status.events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events[-1]["reason"] = "An unaccepted replacement of the canonical review input"
    path.write_text("\n".join(json.dumps(row) for row in events) + "\n", encoding="utf-8")
    git(owned, "add", str(path))
    # Amend only the disposable fixture's genuine final acceptance residual.
    git(owned, "commit", "--amend", "--no-edit", "-q")
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned, "--dry-run")
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_SOURCE_DRIFT"
    assert tuple(snapshot(root) for root in accepted_checkouts) == before


def test_status_formatting_commit_is_not_canonical_completion(accepted_checkouts):
    _primary, owned, _sibling = accepted_checkouts
    mission = owned / "kitty-specs" / SLUG
    snapshot_path = mission / "status.json"
    snapshot_path.write_text(json.dumps(json.loads(snapshot_path.read_text()), indent=4) + "\n", encoding="utf-8")
    events_path = mission / "status.events.jsonl"
    with events_path.open("a", encoding="utf-8") as stream:
        stream.write("\n")
    git(owned, "add", str(snapshot_path), str(events_path))
    git(owned, "commit", "-qm", "fixture: status formatting without terminal events")
    before = tuple(snapshot(root) for root in accepted_checkouts)
    result = invoke_merge(owned, "--dry-run")
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["error_code"] == "OWNED_SOURCE_DRIFT"
    assert tuple(snapshot(root) for root in accepted_checkouts) == before
