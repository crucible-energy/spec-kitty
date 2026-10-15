"""ATDD: explicit coordinated authority in a reused registered checkout (#60)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app as migrations
from specify_cli.cli.commands.next_cmd import next_step
from specify_cli.cli.commands.agent.status import app as status_commands
from specify_cli.status.reducer import materialize
from tests.integration.test_restore_owned_mission_history import MID, SLUG, TARGET, commit, encode, git, tree

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
COORD = f"kitty/mission-{SLUG}"
PLACEMENT = "restore-owned-coordination"


def retained_history() -> list[dict]:
    rows = []
    paths = {
        "WP01": ["planned", "claimed", "in_progress", "for_review", "in_review", "in_progress", "for_review", "in_review", "approved"],
        "WP02": [
            "planned",
            "claimed",
            "in_progress",
            "blocked",
            "in_progress",
            "blocked",
            "in_progress",
            "for_review",
            "in_review",
            "in_progress",
            "for_review",
            "in_review",
        ],
        "WP03": ["planned"],
    }
    for wp, lanes in paths.items():
        previous = "genesis"
        for lane in lanes:
            n = len(rows) + 1
            row = {
                "event_id": f"01M204R7Y759H4DV93ZP8V3{n:03d}",
                "mission_id": MID,
                "mission_slug": SLUG,
                "wp_id": wp,
                "from_lane": previous,
                "to_lane": lane,
                "at": f"2026-09-08T20:00:{n:02d}+00:00",
                "actor": "historical-implementer",
                "force": False,
                "execution_mode": "worktree",
                "reason": "historical",
                "review_ref": None,
                "evidence": None,
            }
            if previous == "in_review":
                verdict = "approved" if lane == "approved" else "changes_requested"
                row["review_result"] = {"reviewer": "historical-independent-reviewer", "verdict": verdict, "reference": f"historical-cycle-{n}"}
                row["evidence"] = {"review": row["review_result"]}
            rows.append(row)
            previous = lane
    for n in range(21):
        rows.append(
            {
                "event_id": f"01M204R7Y759H4DV93ZP8V3{100 + n:03d}",
                "kind": "annotation",
                "wp_id": "WP02",
                "at": "2026-09-08T21:00:00+00:00",
                "actor": {"role": "reviewer", "profile": None, "tool": "historical-review-tool", "model": None},
                "delta": {"note": f"retained note {n}", "model": "__resolved_model_absent__"},
            }
        )
    for n in range(10):
        rows.append(
            # canonical-event-exempt(exception-flow): legacy envelopes lack actor/schema fields; recovery must preserve their original values.
            {
                "event_id": f"01M204R7Y759H4DV93ZP8V3{200 + n:03d}",
                "event_type": "TasksCompleted",
                "aggregate_type": "Mission",
                "aggregate_id": MID,
                "timestamp": "2026-09-08T19:00:00+00:00",
                "payload": {"mission_id": MID, "mission_slug": SLUG, "wp_count": 3},
            }
        )
    return rows


@dataclass
class Authority:
    primary: Path
    owned: Path
    sibling: Path
    directory: Path
    target_pin: str
    coord_pin: str
    husk: Path

    def placement(self, *extra: str, pins: tuple[str, str] | None = None):
        target, coord = pins or (self.target_pin, self.coord_pin)
        return CliRunner().invoke(
            migrations, [PLACEMENT, "--mission", SLUG, "--owned-checkout", str(self.owned), "--target-commit", target, "--coord-commit", coord, "--json", *extra]
        )

    def query(self, *extra: str):
        app = typer.Typer()
        app.command()(next_step)
        return CliRunner().invoke(app, ["--mission", SLUG, "--owned-checkout", str(self.owned), "--json", *extra])

    def snapshot(self):
        return (
            tree(self.primary),
            tree(self.owned),
            tree(self.sibling),
            git(self.owned, "show-ref"),
            git(self.owned, "symbolic-ref", "HEAD"),
            git(self.owned, "worktree", "list", "--porcelain"),
        )


@pytest.fixture
def authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Authority:
    primary = tmp_path / "primary"
    primary.mkdir()
    git(primary, "init", "-q", "-b", "main")
    (primary / ".kittify").mkdir()
    (primary / ".kittify/config.yaml").write_text("{}\n")
    (primary / ".gitignore").write_text(".worktrees/\n.kittify/runtime/\n")
    (primary / "user.txt").write_text("protected\n")
    commit(primary)
    owned, sibling = tmp_path / "external-owned", tmp_path / "external-sibling"
    git(primary, "worktree", "add", "-qb", TARGET, str(owned))
    git(primary, "worktree", "add", "-qb", "feat/protected-sibling", str(sibling))
    directory = owned / "kitty-specs" / SLUG
    (directory / "tasks").mkdir(parents=True)
    meta = {
        "mission_id": MID,
        "mission_slug": SLUG,
        "mission_number": None,
        "mission_type": "software-dev",
        "topology": "coord",
        "coordination_branch": COORD,
        "target_branch": TARGET,
        "friendly_name": "intake",
        "created_at": "2026-09-08T09:00:00+00:00",
    }
    (directory / "meta.json").write_text(json.dumps(meta))
    for name in ("spec.md", "plan.md", "tasks.md"):
        (directory / name).write_text(f"# {name}\n\nReviewed planning.\n")
    (directory / "lanes.json").write_text('{"version":1,"planning_commit_sha":null}\n')
    manifest = []
    for wp in ("WP01", "WP02", "WP03"):
        deps = ["WP01", "WP02"] if wp == "WP03" else []
        manifest.append({"id": wp, "title": wp, "dependencies": deps, "owned_files": [f"{wp}.txt"], "prompt_file": f"tasks/{wp}.md"})
        (directory / "tasks" / f"{wp}.md").write_text(f"---\nwork_package_id: {wp}\ntitle: {wp}\ndependencies: {json.dumps(deps)}\nsubtasks: []\n---\n\n# {wp}\n")
        (owned / f"{wp}.txt").write_text(f"reviewable {wp} code\n")
    (directory / "wps.yaml").write_text(json.dumps({"work_packages": manifest}))
    rows = retained_history()
    (directory / "status.events.jsonl").write_text(encode([r for r in rows if r.get("event_type")]))
    materialize(directory)
    commit(owned)
    git(owned, "switch", "-qc", "archive/coordination-pin")
    partial = [r for r in rows if r.get("wp_id") == "WP01" and r.get("to_lane") in ("planned", "claimed", "in_progress")][:3]
    (directory / "status.events.jsonl").write_text(encode(partial))
    materialize(directory)
    coord_pin = commit(owned)
    git(owned, "switch", "-q", TARGET)
    (directory / "status.events.jsonl").write_text(encode(rows))
    materialize(directory)
    target_pin = commit(owned)
    husk = owned / ".worktrees" / (SLUG + "-coord") / "kitty-specs" / SLUG
    husk.mkdir(parents=True)
    (husk / "mission-events.jsonl").write_text('{"type":"MissionNextInvoked","payload":{"mission_state":"discovery"}}\n')
    (husk / "status.json").write_text('{"work_packages":{}}\n')
    runtime = owned / ".kittify/runtime/runs/retained"
    runtime.mkdir(parents=True)
    (runtime / "state.json").write_text('{"blocked_reason":"discovery blocked","completed_steps":[]}\n')
    (owned / ".kittify/runtime/feature-runs.json").write_text(json.dumps({SLUG: {"run_dir": str(runtime), "run_id": "retained"}}))
    decoy = primary / "kitty-specs" / SLUG
    decoy.mkdir(parents=True)
    (decoy / "meta.json").write_text(json.dumps({**meta, "mission_id": "01M204R7Y759H4DV93ZP8V3TM1"}))
    (primary / "user.txt").write_text("protected dirty primary\n")
    monkeypatch.chdir(primary)
    return Authority(primary, owned, sibling, directory, target_pin, coord_pin, husk)


def test_unregistered_husk_is_typed_query_refusal(authority: Authority):
    before = authority.snapshot()
    result = authority.query()
    assert result.exit_code == 1, result.output
    data = json.loads(result.stdout)
    assert data["code"] == "COORD_AUTHORITY_HUSK_UNREGISTERED"
    assert str(authority.husk.parent.parent) in data["checked_paths"]
    assert authority.snapshot() == before


def test_placement_preview_is_immutable_and_reports_both_ancestries(authority: Authority):
    before = authority.snapshot()
    result = authority.placement()
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["dry_run"] and not data["applied"]
    assert data["parents"] == [authority.target_pin, authority.coord_pin]
    assert data["counts"] == {"rows": 53, "transitions": 22, "annotations": 21, "non_lane": 10}
    assert data["destination_ref"] == COORD
    assert authority.snapshot() == before


def test_supported_placement_reuses_checkout_then_query_is_pure(authority: Authority, monkeypatch: pytest.MonkeyPatch):
    # Test Git identity is command-local; never update repository/global config.
    from specify_cli.migration import owned_coordination

    original = owned_coordination.git_operation
    monkeypatch.setattr(
        owned_coordination,
        "git_operation",
        lambda root, args, **kw: original(root, ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args], **kw),
    )
    primary, sibling, owned = tree(authority.primary), tree(authority.sibling), tree(authority.owned)
    before_registry = git(authority.owned, "worktree", "list", "--porcelain")
    result = authority.placement("--apply")
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["applied"]
    assert git(authority.owned, "rev-list", "--parents", "-n", "1", "HEAD").split() == [data["head"], authority.target_pin, authority.coord_pin]
    assert git(authority.owned, "symbolic-ref", "--short", "HEAD") == COORD
    assert git(authority.owned, "rev-parse", f"refs/heads/{TARGET}") == authority.target_pin
    assert git(authority.owned, "rev-parse", "HEAD^{tree}") == git(authority.owned, "rev-parse", f"{authority.target_pin}^{{tree}}")
    assert len(before_registry.split("worktree ")) == len(git(authority.owned, "worktree", "list", "--porcelain").split("worktree "))
    assert tree(authority.owned) == owned
    assert tree(authority.primary) == primary and tree(authority.sibling) == sibling
    before = authority.snapshot()
    query = authority.query()
    assert query.exit_code == 0, query.output
    q = json.loads(query.stdout)
    assert q["kind"] == "query" and q["is_query"]
    assert q["progress"]["total_wps"] == 3
    assert q["lanes"] == {"WP01": "approved", "WP02": "in_review", "WP03": "planned"}
    assert q["work_packages"]["WP02"]["review_result"]["verdict"] == "changes_requested"
    assert q["readiness"]["WP03"]["code"] == "dependencies_not_satisfied"
    assert q["readiness"]["WP03"]["unsatisfied"] == ["WP02"]
    assert q["roots"]["planning_root"] == q["roots"]["status_root"] == q["roots"]["run_root"] == str(authority.owned)
    assert not q["runtime_advanced"] and q["action"] is None
    assert authority.snapshot() == before
    again = authority.placement("--apply")
    assert again.exit_code == 0, again.output
    assert not json.loads(again.stdout)["changed"]


@pytest.mark.parametrize("fault", ["wrong-pin", "foreign-pin", "dirty", "staged", "symlink", "coord-ref-conflict", "wrong-branch", "log-mismatch"])
def test_bad_placement_refuses_all_effects(authority: Authority, fault: str):
    pins = None
    if fault == "wrong-pin":
        pins = (authority.target_pin[:8], authority.coord_pin)
    elif fault == "foreign-pin":
        pins = (authority.target_pin, git(authority.primary, "rev-parse", "HEAD"))
    elif fault == "dirty":
        (authority.owned / "valuable.txt").write_text("do not overwrite")
    elif fault == "staged":
        (authority.owned / "WP01.txt").write_text("staged user work")
        git(authority.owned, "add", "WP01.txt")
    elif fault == "symlink":
        path = authority.directory / "status.events.jsonl"
        path.unlink()
        path.symlink_to(authority.primary / "user.txt")
    elif fault == "coord-ref-conflict":
        git(authority.owned, "branch", COORD, authority.coord_pin)
    elif fault == "wrong-branch":
        git(authority.owned, "switch", "-qc", "feat/unrelated")
    else:
        (authority.directory / "status.events.jsonl").write_text("{}\n")
    before = authority.snapshot()
    result = authority.placement("--apply", pins=pins)
    assert result.exit_code == 1, result.output
    assert "code" in json.loads(result.stdout)
    assert authority.snapshot() == before


@pytest.mark.parametrize("mode", ["--dry-run", "--apply"])
def test_equal_pins_refuse_before_any_mutation(authority: Authority, monkeypatch: pytest.MonkeyPatch, mode: str):
    """Duplicate parent pins must refuse before Git object/ref or checkout writes."""
    from specify_cli.migration import owned_coordination

    original = owned_coordination.git_operation
    writes = []

    def track(root, args, **kw):
        if "commit-tree" in args or "update-ref" in args:
            writes.append(args)
        return original(root, ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args], **kw)

    monkeypatch.setattr(owned_coordination, "git_operation", track)
    before = authority.snapshot()
    objects_before = git(authority.owned, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)")
    result = authority.placement(mode, pins=(authority.target_pin, authority.target_pin))
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["code"] == "COORD_EQUAL_PINS_REFUSED"
    assert not json.loads(result.stdout)["applied"] and not writes
    assert authority.snapshot() == before
    assert git(authority.owned, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)") == objects_before


@pytest.mark.parametrize("fault", ["one-parent", "reversed-parents", "extra-parent", "wrong-tree"])
def test_generated_anchor_is_verified_before_ref_or_head_activation(authority: Authority, monkeypatch: pytest.MonkeyPatch, fault: str):
    """Reject a malformed real commit-tree result before activating any authority."""
    from specify_cli.migration import owned_coordination

    original = owned_coordination.git_operation
    commits = []
    activations = []

    def malformed(root, args, **kw):
        args = ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args]
        if "commit-tree" in args:
            if fault == "one-parent":
                args = args[:-2]
            elif fault == "reversed-parents":
                args[-3], args[-1] = args[-1], args[-3]
            elif fault == "extra-parent":
                args.extend(["-p", git(authority.primary, "rev-parse", "HEAD")])
            else:
                args[args.index("commit-tree") + 1] = git(authority.primary, "rev-parse", "HEAD^{tree}")
            commits.append(args)
        if "update-ref" in args:
            activations.append(args)
        return original(root, args, **kw)

    monkeypatch.setattr(owned_coordination, "git_operation", malformed)
    before = authority.snapshot()
    result = authority.placement("--apply")
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["code"] == "COORD_AUTHORITY_BINDING_CONFLICT"
    assert commits and not activations
    assert authority.snapshot() == before


@pytest.fixture
def placed(authority: Authority, monkeypatch: pytest.MonkeyPatch) -> Authority:
    from specify_cli.migration import owned_coordination

    original = owned_coordination.git_operation

    def identity(root, args, **kw):
        return original(root, ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args], **kw)

    monkeypatch.setattr(owned_coordination, "git_operation", identity)
    result = authority.placement("--apply")
    assert result.exit_code == 0, result.output
    return authority


def _review(owned: Authority, *extra: str, reviewer: str = "independent-current-reviewer"):
    return CliRunner().invoke(
        status_commands,
        [
            "review-owned",
            "--mission",
            SLUG,
            "--owned-checkout",
            str(owned.owned),
            "--wp-id",
            "WP02",
            "--reviewer",
            reviewer,
            "--verdict",
            "approved",
            "--reference",
            "review://independent-session/WP02",
            "--reviewed-commit",
            owned.target_pin,
            "--json",
            *extra,
        ],
    )


def test_scoped_review_preview_and_real_fixture_record_route_only_to_coord(placed: Authority):
    before = placed.snapshot()
    preview = _review(placed)
    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.stdout)["dry_run"]
    assert placed.snapshot() == before
    primary, sibling = tree(placed.primary), tree(placed.sibling)
    result = _review(placed, "--apply")
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["to_lane"] == "approved" and data["applied"]
    snapshot = json.loads((placed.directory / "status.json").read_text())
    assert snapshot["work_packages"]["WP02"]["review_result"]["reviewer"] == "independent-current-reviewer"
    assert tree(placed.primary) == primary and tree(placed.sibling) == sibling
    assert git(placed.owned, "rev-parse", f"refs/heads/{TARGET}") == placed.target_pin
    commit(placed.owned)  # Operator-owned delivery, not a manufactured runtime step.
    query = placed.query()
    assert query.exit_code == 0, query.output
    assert json.loads(query.stdout)["readiness"]["WP03"]["satisfied"]
    assert json.loads(query.stdout)["action"] is None
    again = _review(placed, "--apply")
    assert again.exit_code == 0, again.output
    assert not json.loads(again.stdout)["changed"]


def test_scoped_review_refuses_implementer_self_approval(placed: Authority):
    before = placed.snapshot()
    result = _review(placed, "--apply", reviewer="historical-implementer")
    assert result.exit_code == 1
    assert "self" in json.loads(result.stdout)["error"]
    assert placed.snapshot() == before


def test_explicit_owned_materialization_migrates_projection_without_rewriting_log(placed: Authority):
    path = placed.directory / "status.json"
    old = json.loads(path.read_text())
    for state in old["work_packages"].values():
        state.pop("review_result", None)
    path.write_text(json.dumps(old))
    commit(placed.owned)
    before = placed.snapshot()
    log = (placed.directory / "status.events.jsonl").read_bytes()
    result = CliRunner().invoke(status_commands, ["materialize", "--mission", SLUG, "--owned-checkout", str(placed.owned), "--dry-run", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["changed"]
    assert placed.snapshot() == before
    applied = CliRunner().invoke(migrations, ["refresh-owned-review-projection", "--mission", SLUG, "--owned-checkout", str(placed.owned), "--apply", "--json"])
    assert applied.exit_code == 0, applied.output
    assert (placed.directory / "status.events.jsonl").read_bytes() == log
    assert json.loads(path.read_text())["work_packages"]["WP02"]["review_result"]["verdict"] == "changes_requested"
    from specify_cli.audit.classifiers.status_json import classify_status_json

    assert not any(f.code == "SNAPSHOT_DRIFT" for f in classify_status_json(placed.directory))


@pytest.mark.parametrize("args", [["--result", "success"], ["--answer", "approve"], ["--decision-id", "input:review"]])
def test_owned_query_never_advances_or_answers_runtime(placed: Authority, args: list[str]):
    before = placed.snapshot()
    result = placed.query(*args)
    assert result.exit_code == 1
    assert json.loads(result.stdout)["code"] == "OWNED_COORD_QUERY_ONLY"
    assert placed.snapshot() == before


def test_retained_blocked_runtime_is_observed_without_synthetic_success(placed: Authority):
    before = placed.snapshot()
    result = placed.query()
    assert result.exit_code == 0, result.output
    runtime = json.loads(result.stdout)["runtime"]
    assert runtime["blocked_reason"] == "discovery blocked" and runtime["completed_steps"] == []
    assert not runtime["advanced"]
    assert placed.snapshot() == before


def test_committed_coord_log_cannot_discard_restored_history(placed: Authority):
    path = placed.directory / "status.events.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text(encode([row for row in rows if row.get("event_id") != rows[-1]["event_id"]]))
    materialize(placed.directory)
    commit(placed.owned)
    before = placed.snapshot()
    result = placed.query()
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["code"] == "COORD_HISTORY_CONFLICT"
    assert placed.snapshot() == before


def test_changes_requested_records_real_rework_without_runtime_advance(placed: Authority):
    result = _review(placed, "--verdict", "changes_requested", "--apply")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["to_lane"] == "in_progress"
    commit(placed.owned)
    queried = placed.query()
    assert queried.exit_code == 0, queried.output
    data = json.loads(queried.stdout)
    assert data["work_packages"]["WP02"]["review_result"]["verdict"] == "changes_requested"
    assert data["readiness"]["WP03"]["unsatisfied"] == ["WP02"]
    assert not data["runtime_advanced"] and not data["allocated"]


@pytest.mark.parametrize("fault", ["active-lease", "active-run", "foreign-run", "hidden-log", "borrowed-git", "snapshot-symlink"])
def test_ownership_and_authority_guards_fail_closed(authority: Authority, fault: str):
    expected_codes = {
        "active-lease": "OWNED_ACTIVE_LEASE_REFUSED",
        "active-run": "OWNED_ACTIVE_RUN_REFUSED",
        "foreign-run": "OWNED_RUN_ROOT_REFUSED",
        "hidden-log": "OWNED_UNCOMMITTED_AUTHORITY_REFUSED",
        "borrowed-git": "OWNED_GIT_PATH_REFUSED",
        "snapshot-symlink": "OWNED_COORD_VALIDATION_REFUSED",
    }
    if fault == "active-lease":
        import psutil
        from specify_cli.status.models import InnerStateChanged, WPInnerStateDelta
        from specify_cli.status.store import append_annotations_atomic_verified
        from ulid import ULID

        append_annotations_atomic_verified(
            authority.directory,
            [
                InnerStateChanged(
                    str(ULID()),
                    "WP02",
                    "2026-10-04T00:00:00+00:00",
                    "test-owner",
                    WPInnerStateDelta(shell_pid=os.getpid(), shell_pid_created_at=str(psutil.Process().create_time())),
                )
            ],
        )
        materialize(authority.directory)
        authority.target_pin = commit(authority.owned)
    elif fault == "active-run":
        path = authority.owned / ".kittify/runtime/runs/retained/state.json"
        path.write_text('{"issued_step_id":"real-outstanding-step"}\n')
    elif fault == "foreign-run":
        path = authority.owned / ".kittify/runtime/feature-runs.json"
        path.write_text(json.dumps({SLUG: {"run_dir": str(authority.primary), "run_id": "foreign"}}))
    elif fault == "hidden-log":
        relative = f"kitty-specs/{SLUG}/status.events.jsonl"
        git(authority.owned, "update-index", "--assume-unchanged", relative)
        (authority.owned / relative).write_text(encode(retained_history()[:-1]))
    elif fault == "borrowed-git":
        (authority.owned / ".git").write_bytes((authority.sibling / ".git").read_bytes())
    else:
        path = authority.directory / "status.json"
        path.unlink()
        path.symlink_to(authority.primary / "user.txt")
    before = authority.snapshot()
    result = authority.placement("--apply")
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["code"] == expected_codes[fault]
    assert authority.snapshot() == before


def test_failed_native_ref_transaction_leaves_all_refs_head_and_files_unchanged(authority: Authority, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.migration import owned_coordination

    original = owned_coordination.git_operation
    attempted = False

    def failure(root, args, **kw):
        nonlocal attempted
        args = ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args]
        if "update-ref" in args:
            attempted = True
            # Real Git parser aborts the whole prepared transaction; no manual
            # rollback/ref deletion can accidentally discard another owner.
            kw["input_bytes"] = kw["input_bytes"].replace(b"prepare\n", b"invalid-command\nprepare\n")
        return original(root, args, **kw)

    monkeypatch.setattr(owned_coordination, "git_operation", failure)
    before = authority.snapshot()
    result = authority.placement("--apply")
    assert attempted and result.exit_code == 1, result.output
    assert authority.snapshot() == before


def test_ref_collision_during_atomic_prepare_preserves_other_owner(authority: Authority, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.migration import owned_coordination

    original = owned_coordination.git_operation
    raced = False

    def collision(root, args, **kw):
        nonlocal raced
        args = ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args]
        if "update-ref" in args and not raced:
            raced = True
            git(authority.owned, "branch", COORD, authority.coord_pin)
        return original(root, args, **kw)

    monkeypatch.setattr(owned_coordination, "git_operation", collision)
    files = tree(authority.owned)
    result = authority.placement("--apply")
    assert raced and result.exit_code == 1, result.output
    assert git(authority.owned, "rev-parse", f"refs/heads/{COORD}") == authority.coord_pin
    assert git(authority.owned, "symbolic-ref", "--short", "HEAD") == TARGET
    assert tree(authority.owned) == files


@pytest.mark.parametrize("fault", ["wrong-branch", "wrong-ref", "missing-log", "dirty", "symlink"])
def test_after_placement_query_revalidates_genuine_authority(placed: Authority, fault: str):
    if fault == "wrong-branch":
        git(placed.owned, "switch", "-q", TARGET)
    elif fault == "wrong-ref":
        git(placed.owned, "update-ref", f"refs/heads/{COORD}", placed.coord_pin)
    elif fault == "missing-log":
        (placed.directory / "status.events.jsonl").unlink()
    elif fault == "dirty":
        (placed.owned / "valuable.txt").write_text("protected user data")
    else:
        path = placed.directory / "status.events.jsonl"
        path.unlink()
        path.symlink_to(placed.primary / "user.txt")
    before = placed.snapshot()
    result = placed.query()
    assert result.exit_code == 1 and "code" in json.loads(result.stdout), result.output
    assert placed.snapshot() == before


@pytest.mark.parametrize("fault", ["reference", "verdict", "wp", "code-pin", "foreign-code"])
def test_review_evidence_guards_refuse_noop(placed: Authority, fault: str):
    replacements = {
        "reference": ("--reference", " "),
        "verdict": ("--verdict", "done"),
        "wp": ("--wp-id", "WP03"),
        "code-pin": ("--reviewed-commit", placed.target_pin[:8]),
        "foreign-code": ("--reviewed-commit", git(placed.primary, "rev-parse", "HEAD")),
    }
    option, value = replacements[fault]
    before = placed.snapshot()
    result = _review(placed, option, value, "--apply")
    assert result.exit_code == 1 and "code" in json.loads(result.stdout), result.output
    assert placed.snapshot() == before


def test_unsupported_git_atomic_capability_refuses_before_objects_or_refs(authority: Authority, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.migration import owned_coordination

    original = owned_coordination.git_operation
    writes = []

    def older(root, args, **kw):
        if args == ["version"]:
            return b"git version 2.43.0\n"
        if "commit-tree" in args or "update-ref" in args:
            writes.append(args)
        return original(root, args, **kw)

    monkeypatch.setattr(owned_coordination, "git_operation", older)
    before = authority.snapshot()
    result = authority.placement("--apply")
    assert result.exit_code == 1
    assert json.loads(result.stdout)["code"] == "COORD_GIT_CAPABILITY_UNSUPPORTED"
    assert not writes and authority.snapshot() == before


def test_existing_default_materialize_refreshes_old_verdict_projection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.cli.commands.agent import status
    from specify_cli.audit.classifiers.status_json import classify_status_json

    directory = tmp_path / "kitty-specs" / SLUG
    directory.mkdir(parents=True)
    (directory / "meta.json").write_text(json.dumps({"mission_id": MID, "mission_slug": SLUG, "mission_type": "software-dev", "mission_number": None}))
    log = encode(retained_history()).encode()
    (directory / "status.events.jsonl").write_bytes(log)
    snapshot = materialize(directory).to_dict()
    old = json.loads(json.dumps(snapshot))
    for state in old["work_packages"].values():
        state.pop("review_result", None)
    (directory / "status.json").write_text(json.dumps(old))
    assert any(f.code == "SNAPSHOT_DRIFT" for f in classify_status_json(directory))
    # Preserve the existing CLI's topology resolver; isolate only root selection
    # so the migration regression is about its real lock/reducer/write behavior.
    monkeypatch.setattr(status, "locate_project_root", lambda *_: tmp_path)
    monkeypatch.setattr(status, "get_main_repo_root", lambda root: root)
    monkeypatch.setattr(status, "_find_mission_slug", lambda **_: SLUG)
    monkeypatch.setattr(status, "_resolve_status_surface_for_repo", lambda *_: (directory, None, None))
    result = CliRunner().invoke(status_commands, ["materialize", "--mission", SLUG, "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads((directory / "status.json").read_text()) == snapshot
    assert (directory / "status.events.jsonl").read_bytes() == log
    assert not any(f.code == "SNAPSHOT_DRIFT" for f in classify_status_json(directory))


def test_relative_git_backlink_accepts_the_registered_owned_checkout(authority: Authority, monkeypatch: pytest.MonkeyPatch):
    git(authority.owned, "worktree", "repair", "--relative-paths", str(authority.owned))
    gitdir = Path(git(authority.owned, "rev-parse", "--absolute-git-dir"))
    assert not Path((gitdir / "gitdir").read_text(encoding="utf-8").strip()).is_absolute()
    # Caller is the primary checkout, deliberately not the admin directory.
    monkeypatch.chdir(authority.primary)
    before = authority.snapshot()
    preview = authority.placement()
    assert preview.exit_code == 0, preview.output
    assert authority.snapshot() == before
    from specify_cli.migration import owned_coordination

    original = owned_coordination.git_operation
    monkeypatch.setattr(
        owned_coordination,
        "git_operation",
        lambda root, args, **kw: original(root, ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args], **kw),
    )
    applied = authority.placement("--apply")
    assert applied.exit_code == 0, applied.output
    before_query = authority.snapshot()
    query = authority.query()
    assert query.exit_code == 0, query.output
    assert authority.snapshot() == before_query


def test_locked_review_noop_never_enters_installation(placed: Authority, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.coordination import owned_status

    original = owned_status._review_plan
    calls = []
    installs = []

    def replan(*args):
        calls.append(True)
        if len(calls) == 1:
            return original(*args)
        return {}, {"changed": False, "status_ref": COORD}

    monkeypatch.setattr(owned_status, "_review_plan", replan)
    monkeypatch.setattr(owned_status, "_replace_batch", lambda *args: installs.append(args))
    before = placed.snapshot()
    result = _review(placed, "--apply")
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert not data["changed"] and not data["applied"] and not data["commit_required"]
    assert not installs and placed.snapshot() == before


def test_locked_projection_noop_uses_final_bytes_and_does_not_install(placed: Authority, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.coordination import owned_status

    original = owned_status.materialize_to_json
    calls = []
    installs = []

    def serialize(snapshot):
        calls.append(True)
        # A stale preflight serialization differs; the locked serialization is
        # already installed. The final report must describe that locked state.
        return original(snapshot) + ("\n" if len(calls) == 1 else "")

    monkeypatch.setattr(owned_status, "materialize_to_json", serialize)
    monkeypatch.setattr(owned_status, "_replace_batch", lambda *args: installs.append(args))
    before = placed.snapshot()
    report = owned_status.refresh_owned_projection(placed.primary, placed.owned, SLUG, apply=True)
    assert not report["changed"] and not report["applied"] and not report["commit_required"]
    assert not installs and placed.snapshot() == before


def test_owned_materialize_default_preview_and_exclusive_flags(placed: Authority):
    before = placed.snapshot()
    args = ["materialize", "--mission", SLUG, "--owned-checkout", str(placed.owned), "--json"]
    preview = CliRunner().invoke(status_commands, args)
    assert preview.exit_code == 0, preview.output
    assert json.loads(preview.stdout)["dry_run"] and not json.loads(preview.stdout)["applied"]
    refused = CliRunner().invoke(status_commands, [*args, "--apply", "--dry-run"])
    assert refused.exit_code == 1
    assert "mutually exclusive" in json.loads(refused.stdout)["error"]
    assert placed.snapshot() == before
