"""ATDD: owned rework submission and independent review claim, without approval shortcuts."""

from __future__ import annotations

import json
import shlex
import sys
from dataclasses import dataclass

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
        extra = ["--code-commit", rework.pin[:8]]
    elif fault == "unknown-actor":
        extra = ["--implementer", "unknown"]
    before = a.snapshot()
    result = rework.invoke(command, *extra, "--apply")
    assert result.exit_code == 1, result.output
    assert "code" in json.loads(result.stdout)
    assert a.snapshot() == before


def test_claim_refuses_self_or_changed_submission_pin(rework: Rework):
    a = rework.authority
    _success(rework.invoke("submit-owned-review", "--apply"))
    commit(a.owned)
    before = a.snapshot()
    for args in (["--reviewer", IMPLEMENTER], ["--code-commit", a.target_pin], ["--implementer", "another actor"]):
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


def test_duplicate_event_id_and_locked_context_change_refuse(rework: Rework, monkeypatch: pytest.MonkeyPatch):
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
