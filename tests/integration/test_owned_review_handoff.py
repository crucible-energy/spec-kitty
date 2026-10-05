"""ATDD: owned rework submission and independent review claim, without approval shortcuts."""

from __future__ import annotations

import json
import shlex
import sys
import subprocess
from dataclasses import dataclass
from contextlib import contextmanager

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.status import app
from specify_cli.review.gate_bindings import GateBindingResolution, GateCoverage
from tests.integration.test_owned_coordinated_authority import Authority, COORD, SLUG, _review, authority as authority, placed as placed
from tests.integration.test_restore_owned_mission_history import commit, git

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
IMPLEMENTER = "node-norris/OpenCode independent implementation"
REVIEWER = "reviewer-renata/OpenCode independent AI"
PROOF = "evidence/wp02-scope.json"


@dataclass
class Rework:
    authority: Authority
    pin: str

    @property
    def reference(self):
        return f"https://github.com/fixture-org/mission/commit/{self.pin}"

    def invoke(self, command, *extra):
        args = [
            command,
            "--mission",
            SLUG,
            "--owned-checkout",
            str(self.authority.owned),
            "--wp-id",
            "WP02",
            "--implementer",
            IMPLEMENTER,
            "--code-commit",
            self.pin,
            "--reference",
            self.reference,
            "--json",
        ]
        if command == "claim-owned-review":
            args += ["--reviewer", REVIEWER]
        else:
            args += ["--scope-proof", PROOF]
        return CliRunner().invoke(app, [*args, *extra])


@pytest.fixture
def rework(placed: Authority, monkeypatch: pytest.MonkeyPatch):
    git(placed.owned, "remote", "add", "origin", "https://github.com/fixture-org/mission.git")
    rejected = _review(placed, "--verdict", "changes_requested", "--apply", reviewer=REVIEWER)
    assert rejected.exit_code == 0, rejected.output
    (placed.owned / "evidence").mkdir()
    (placed.owned / PROOF).write_text(json.dumps({"scope": "WP02", "scoped_checks": "passed", "aggregate_gate": "baseline_blocked"}))
    pin = commit(placed.owned)
    # Controlled policy coverage only: no gate result is mocked or fabricated.
    monkeypatch.setattr(
        "specify_cli.review.gate_bindings.resolve_gate_bindings_for_transition",
        lambda *_: GateBindingResolution(
            GateCoverage.NO_BINDING, "in_progress->for_review", "mission_step_contract:software-dev/review", "NO_COVERAGE: no binding in this fixture"
        ),
    )
    return Rework(placed, pin)


def _success(result):
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def test_rework_submit_claim_and_actual_review_preserve_history_and_roots(rework: Rework):
    a = rework.authority
    before = a.snapshot()
    log_before = (a.directory / "status.events.jsonl").read_bytes()
    old = json.loads((a.directory / "status.json").read_text())["work_packages"]["WP02"]
    preview = _success(rework.invoke("submit-owned-review"))
    assert preview["dry_run"] and preview["to_lane"] == "for_review"
    assert a.snapshot() == before
    applied = _success(rework.invoke("submit-owned-review", "--apply"))
    assert applied["applied"] and applied["status_ref"] == COORD and not applied["runtime_advanced"]
    assert applied["pre_review_gate"]["outcome"] == "no_coverage"
    assert applied["aggregate_approval"] is False
    commit(a.owned)
    assert not _success(rework.invoke("submit-owned-review", "--apply"))["changed"]
    state = json.loads((a.directory / "status.json").read_text())["work_packages"]["WP02"]
    assert state["review_result"] == old["review_result"]
    assert state["model"] == old["model"]
    queued = a.snapshot()
    claim_preview = _success(rework.invoke("claim-owned-review"))
    assert claim_preview["to_lane"] == "in_review" and a.snapshot() == queued
    _success(rework.invoke("claim-owned-review", "--apply"))
    commit(a.owned)
    assert not _success(rework.invoke("claim-owned-review", "--apply"))["changed"]
    assert _success(a.query())["lanes"]["WP02"] == "in_review"
    result = _review(a, "--reviewed-commit", rework.pin, "--reference", rework.reference, "--apply", reviewer=REVIEWER)
    assert _success(result)["to_lane"] == "approved"
    assert (a.directory / "status.events.jsonl").read_bytes().startswith(log_before)
    commit(a.owned)
    q = _success(a.query())
    assert q["readiness"]["WP03"]["satisfied"] and not q["allocated"] and q["action"] is None
    assert a.snapshot()[0] == before[0] and a.snapshot()[2] == before[2]


@pytest.mark.parametrize("command", ["submit-owned-review", "claim-owned-review"])
@pytest.mark.parametrize("fault", ["phase", "unknown-wp", "staged", "reference", "code-pin", "unknown-actor"])
def test_bad_handoff_refuses_without_writes(rework: Rework, command: str, fault: str):
    a = rework.authority
    extra = []
    if command == "claim-owned-review" and fault != "phase":
        _success(rework.invoke("submit-owned-review", "--apply"))
        commit(a.owned)
    if fault == "phase" and command == "submit-owned-review":
        _success(rework.invoke(command, "--apply"))
        commit(a.owned)
        extra = ["--reference", rework.reference + "#different-request"]
    elif fault == "unknown-wp":
        extra = ["--wp-id", "WP99"]
    elif fault == "staged":
        (a.owned / "WP02.txt").write_text("preserve staged operator work")
        git(a.owned, "add", "WP02.txt")
    elif fault == "reference":
        extra = ["--reference", "review://invented"]
    elif fault == "code-pin":
        extra = ["--code-commit", rework.pin[:8], "--reference", rework.reference.replace(rework.pin, rework.pin[:8])]
    elif fault == "unknown-actor":
        extra = ["--implementer", "unknown"]
    before = a.snapshot()
    result = rework.invoke(command, *extra, "--apply")
    assert result.exit_code == 1, result.output
    expected = {
        "phase": "OWNED_HANDOFF_LANE_REFUSED",
        "unknown-wp": "OWNED_HANDOFF_WP_REFUSED",
        "staged": "OWNED_COORD_VALIDATION_REFUSED",
        "reference": "OWNED_HANDOFF_REFERENCE_REFUSED",
        "code-pin": "OWNED_COORD_VALIDATION_REFUSED",
        "unknown-actor": "OWNED_HANDOFF_ACTOR_REFUSED",
    }
    assert json.loads(result.stdout)["code"] == expected[fault]
    assert a.snapshot() == before


def test_claim_refuses_self_or_changed_submission_pin(rework: Rework):
    a = rework.authority
    _success(rework.invoke("submit-owned-review", "--apply"))
    commit(a.owned)
    before = a.snapshot()
    for args in (
        ["--reviewer", IMPLEMENTER],
        ["--code-commit", a.target_pin, "--reference", rework.reference.replace(rework.pin, a.target_pin)],
        ["--implementer", "another actor"],
    ):
        result = rework.invoke("claim-owned-review", *args, "--apply")
        assert result.exit_code == 1 and a.snapshot() == before, result.output


def test_review_owned_still_requires_claimed_phase_and_matching_reviewer(rework: Rework):
    a = rework.authority
    assert _review(a, "--apply", reviewer=REVIEWER).exit_code == 1
    _success(rework.invoke("submit-owned-review", "--apply"))
    commit(a.owned)
    assert _review(a, "--apply", reviewer=REVIEWER).exit_code == 1
    _success(rework.invoke("claim-owned-review", "--apply"))
    commit(a.owned)
    before = a.snapshot()
    wrong = _review(a, "--reviewed-commit", rework.pin, "--apply", reviewer="another reviewer")
    assert wrong.exit_code == 1 and a.snapshot() == before


@pytest.fixture
def gated(rework: Rework, monkeypatch: pytest.MonkeyPatch):
    from doctrine.missions.step_contracts import GateBinding

    a = rework.authority
    (a.owned / ".kittify/config.yaml").write_text(
        json.dumps(
            {"review": {"test_command": shlex.join([sys.executable, "-B", "gate_check.py"]), "test_output_format": "text", "fail_on_pre_review_regression": True}}
        )
    )
    (a.owned / "gate_check.py").write_text("from pathlib import Path\nassert 'reviewable WP02' in Path('WP02.txt').read_text()\nprint('1 passed')\n")
    folder = a.directory / "tasks/WP02"
    folder.mkdir()
    (folder / "baseline-tests.json").write_text(
        json.dumps(
            {
                "wp_id": "WP02",
                "captured_at": "2026-09-08T00:00:00+00:00",
                "base_branch": "fixture",
                "base_commit": a.target_pin,
                "test_runner": "custom",
                "total": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "failures": [],
                "source_identity": "DeclaredCommandScopeSource/text",
            }
        )
    )
    rework.pin = commit(a.owned)
    binding = GateBinding(on_transition="in_progress->for_review", handler="spec-kitty-pre-review", schema_version="1")
    monkeypatch.setattr(
        "specify_cli.review.gate_bindings.resolve_gate_bindings_for_transition",
        lambda *_: GateBindingResolution(
            GateCoverage.ACTIVE, "in_progress->for_review", "mission_step_contract:software-dev/review", "fixture active binding", (binding,)
        ),
    )
    return rework


def test_required_gate_runs_real_command_only_on_apply(gated: Rework):
    before = gated.authority.snapshot()
    preview = _success(gated.invoke("submit-owned-review"))
    assert preview["pre_review_gate"]["outcome"] == "not_run" and gated.authority.snapshot() == before
    report = _success(gated.invoke("submit-owned-review", "--apply"))
    assert report["pre_review_gate"]["outcome"] == "no_new_failures"
    assert report["aggregate_approval"] is False


@pytest.mark.parametrize("identity", ["unknown", None])
def test_required_unknown_or_missing_baseline_source_refuses_before_run(gated: Rework, monkeypatch: pytest.MonkeyPatch, identity: str | None):
    """Change only the committed capture identity; a real passing command is not proof."""
    from specify_cli.review import pre_review_gate

    a = gated.authority
    baseline = a.directory / "tasks/WP02/baseline-tests.json"
    payload = json.loads(baseline.read_text())
    assert payload["wp_id"] == "WP02" and payload["failed"] == 0
    if identity is None:
        payload.pop("source_identity")
    else:
        payload["source_identity"] = identity
    baseline.write_text(json.dumps(payload))
    gated.pin = commit(a.owned)
    original = pre_review_gate._run_raw_command
    runs = []

    def observe(*args, **kwargs):
        runs.append(args)
        return original(*args, **kwargs)  # Never substitute a process verdict.

    monkeypatch.setattr(pre_review_gate, "_run_raw_command", observe)
    before = a.snapshot()
    result = gated.invoke("submit-owned-review", "--apply")
    assert result.exit_code == 1, result.output
    data = json.loads(result.stdout)
    assert data["code"] == "OWNED_PRE_REVIEW_GATE_BLOCKED"
    assert data["pre_review_gate"]["outcome"] == "unverified_baseline"
    assert data["pre_review_gate"]["baseline_source_identity"] == "unknown"
    assert not data["pre_review_gate"]["test_run"] and not runs
    assert not data["applied"] and not data["aggregate_approval"]
    assert a.snapshot() == before


@pytest.mark.parametrize("required", [False, True])
def test_consumer_without_declared_command_reports_actual_missing_coverage(gated: Rework, monkeypatch: pytest.MonkeyPatch, required: bool):
    from specify_cli.review import pre_review_gate

    a = gated.authority
    (a.owned / ".kittify/config.yaml").write_text(json.dumps({"review": {"fail_on_pre_review_regression": required}}))
    (a.directory / "tasks/WP02/baseline-tests.json").unlink()
    gated.pin = commit(a.owned)
    original = pre_review_gate._run_raw_command
    runs = []

    def observe(*args, **kwargs):
        runs.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(pre_review_gate, "_run_raw_command", observe)
    before = a.snapshot()
    result = gated.invoke("submit-owned-review", "--apply")
    assert result.exit_code == (1 if required else 0), result.output
    data = json.loads(result.stdout)
    assert data["pre_review_gate"]["outcome"] == "no_coverage"
    assert data["pre_review_gate"]["scope_source"] == "GateCoverageScopeSource"
    assert not data["pre_review_gate"]["test_run"] and not runs
    assert not data["aggregate_approval"]
    if required:
        assert data["code"] == "OWNED_PRE_REVIEW_GATE_BLOCKED" and a.snapshot() == before
    else:
        assert data["to_lane"] == "for_review" and data["applied"]
        assert a.snapshot()[0] == before[0] and a.snapshot()[2] == before[2]


def test_required_gate_failure_and_missing_baseline_do_not_submit(gated: Rework):
    a = gated.authority
    for fault in ("failed-command", "missing-baseline"):
        if fault == "failed-command":
            (a.owned / "gate_check.py").write_text("raise AssertionError('genuine gate regression')\n")
        else:
            (a.owned / "gate_check.py").write_text("print('1 passed')\n")
            (a.directory / "tasks/WP02/baseline-tests.json").unlink()
        gated.pin = commit(a.owned)
        before = a.snapshot()
        result = gated.invoke("submit-owned-review", "--apply")
        assert result.exit_code == 1 and a.snapshot() == before, result.output
        assert json.loads(result.stdout)["code"] == "OWNED_PRE_REVIEW_GATE_BLOCKED"


def test_baseline_other_wp_and_hidden_test_inputs_cannot_qualify_gate(gated: Rework):
    a = gated.authority
    baseline = a.directory / "tasks/WP02/baseline-tests.json"
    payload = json.loads(baseline.read_text())
    payload["wp_id"] = "WP99"
    baseline.write_text(json.dumps(payload))
    gated.pin = commit(a.owned)
    before = a.snapshot()
    result = gated.invoke("submit-owned-review", "--apply")
    assert result.exit_code == 1 and a.snapshot() == before
    assert json.loads(result.stdout)["code"] == "OWNED_PRE_REVIEW_GATE_BLOCKED"
    payload["wp_id"] = "WP02"
    baseline.write_text(json.dumps(payload))
    gated.pin = commit(a.owned)
    git(a.owned, "update-index", "--assume-unchanged", "WP02.txt")
    (a.owned / "WP02.txt").write_text("hidden unqualified input")
    before = a.snapshot()
    hidden = gated.invoke("submit-owned-review", "--apply")
    assert hidden.exit_code == 1 and a.snapshot() == before
    assert json.loads(hidden.stdout)["code"] == "OWNED_GATE_CODE_CHECKOUT_REQUIRED"


def test_duplicate_event_id_refuses(rework: Rework, monkeypatch: pytest.MonkeyPatch):
    # Implementation seams are loaded only after the CLI has a supported entrypoint.
    from specify_cli.coordination import owned_handoff
    from specify_cli.status.models import StatusEvent

    a = rework.authority
    first = json.loads((a.directory / "status.events.jsonl").read_text().splitlines()[0])
    before = a.snapshot()
    monkeypatch.setattr(owned_handoff, "build_status_event", lambda **_: StatusEvent.from_dict(first))
    result = rework.invoke("submit-owned-review", "--apply")
    assert result.exit_code == 1 and a.snapshot() == before
    assert json.loads(result.stdout)["code"] == "OWNED_HANDOFF_EVENT_CONFLICT"


def test_locked_context_change_preserves_other_owners_commit(rework: Rework, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.coordination import owned_handoff

    a = rework.authority
    original = owned_handoff.feature_status_lock
    advanced = []
    before_files = a.snapshot()[:3]

    @contextmanager
    def advance(*args, **kwargs):
        with original(*args, **kwargs) as held:
            git(a.owned, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "--allow-empty", "-qm", "other admitted owner")
            advanced.append(git(a.owned, "rev-parse", "HEAD"))
            yield held

    monkeypatch.setattr(owned_handoff, "feature_status_lock", advance)
    result = rework.invoke("submit-owned-review", "--apply")
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["code"] == "OWNED_HANDOFF_CONTEXT_CHANGED"
    assert advanced and git(a.owned, "rev-parse", "HEAD") == advanced[0]
    assert a.snapshot()[:3] == before_files


def test_required_uncovered_gate_and_stale_code_checkout_refuse(gated: Rework, monkeypatch: pytest.MonkeyPatch):
    before = gated.authority.snapshot()
    stale = gated.invoke("submit-owned-review", "--code-checkout", str(gated.authority.sibling), "--apply")
    assert stale.exit_code == 1 and gated.authority.snapshot() == before
    monkeypatch.setattr(
        "specify_cli.review.gate_bindings.resolve_gate_bindings_for_transition",
        lambda *_: GateBindingResolution(
            GateCoverage.NO_BINDING, "in_progress->for_review", "mission_step_contract:software-dev/review", "NO_COVERAGE: required binding absent"
        ),
    )
    result = gated.invoke("submit-owned-review", "--apply")
    assert result.exit_code == 1 and gated.authority.snapshot() == before
    assert json.loads(result.stdout)["code"] == "OWNED_PRE_REVIEW_GATE_BLOCKED"


def test_canonical_subtask_completion_is_not_invented(authority: Authority, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.migration import owned_coordination
    from specify_cli.review import gate_bindings

    a = authority
    wp = a.directory / "tasks/WP02.md"
    wp.write_text(wp.read_text().replace("subtasks: []", "subtasks: [T123]"))
    a.target_pin = commit(a.owned)
    original = owned_coordination.git_operation
    monkeypatch.setattr(
        owned_coordination,
        "git_operation",
        lambda root, args, **kw: original(root, ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args], **kw),
    )
    _success(a.placement("--apply"))
    git(a.owned, "remote", "add", "origin", "https://github.com/fixture-org/mission.git")
    _success(_review(a, "--verdict", "changes_requested", "--apply", reviewer=REVIEWER))
    (a.owned / "evidence").mkdir()
    (a.owned / PROOF).write_text("{}")
    pin = commit(a.owned)
    monkeypatch.setattr(
        gate_bindings,
        "resolve_gate_bindings_for_transition",
        lambda *_: GateBindingResolution(GateCoverage.NO_BINDING, "in_progress->for_review", "mission_step_contract:software-dev/review", "NO_COVERAGE: fixture"),
    )
    before = a.snapshot()
    result = Rework(a, pin).invoke("submit-owned-review", "--apply")
    assert result.exit_code == 1 and a.snapshot() == before, result.output
    assert json.loads(result.stdout)["code"] == "OWNED_HANDOFF_TRANSITION_REFUSED"


def test_gate_policy_invalid_shapes_and_hidden_changes_refuse(rework: Rework):
    a = rework.authority
    policy = a.owned / ".kittify/config.yaml"
    for bad, expected in (
        ("{", "OWNED_COORD_VALIDATION_REFUSED"),
        ('["not a policy"]', "OWNED_COORD_VALIDATION_REFUSED"),
        ('{"review":"not a mapping"}', "OWNED_GATE_POLICY_REFUSED"),
        ('{"review":{"fail_on_pre_review_regression":"yes"}}', "OWNED_GATE_POLICY_REFUSED"),
    ):
        policy.write_text(bad)
        rework.pin = commit(a.owned)
        before = a.snapshot()
        result = rework.invoke("submit-owned-review", "--apply")
        assert result.exit_code == 1 and a.snapshot() == before, result.output
        assert json.loads(result.stdout)["code"] == expected
    policy.write_text("{}")
    rework.pin = commit(a.owned)
    git(a.owned, "update-index", "--assume-unchanged", ".kittify/config.yaml")
    policy.write_text('{"review":{"fail_on_pre_review_regression":true}}')
    before = a.snapshot()
    result = rework.invoke("submit-owned-review", "--apply")
    assert result.exit_code == 1 and a.snapshot() == before
    assert json.loads(result.stdout)["code"] == "OWNED_GATE_POLICY_REFUSED"


def test_baseline_failures_are_reported_blocked_without_aggregate_green(gated: Rework):
    from specify_cli.review.scope_source import RawRunResult, resolve_scope_source

    a = gated.authority
    baseline = a.directory / "tasks/WP02/baseline-tests.json"
    payload = json.loads(baseline.read_text())
    (a.owned / "gate_check.py").write_text("raise AssertionError('actual failure remains')\n")
    captured = subprocess.run([sys.executable, "-B", "gate_check.py"], cwd=a.owned, capture_output=True, text=True, check=False)
    failures = resolve_scope_source(a.owned).parse_results(RawRunResult(captured.returncode, captured.stdout, captured.stderr))
    assert failures
    payload.update({"failed": len(failures), "passed": 0, "failures": [f.to_dict() for f in failures]})
    baseline.write_text(json.dumps(payload))
    gated.pin = commit(a.owned)
    before = a.snapshot()
    result = gated.invoke("submit-owned-review", "--apply")
    assert result.exit_code == 1 and a.snapshot() == before
    data = json.loads(result.stdout)
    assert data["code"] == "OWNED_PRE_REVIEW_GATE_BLOCKED" and not data["aggregate_approval"]
    assert data["pre_review_gate"]["required"]
    assert data["pre_review_gate"]["outcome"] == "no_new_failures"
    assert data["pre_review_gate"]["verdicts"][0]["pre_existing_failures"]
