"""The engine is the single authority for "apply the result and plan the next
step" (owned-checkout-lifecycle-authority WP11, review cycle 1 findings 3/4).

``plan_advance`` computes what ``next_step`` will issue -- including the
audit-significance LOW re-plan -- WITHOUT writing anything, so the bridge can
resolve a planned WP-iteration step's workspace BEFORE the advance is
persisted. ``next_step`` is plan + commit over the same plan, so the two can
never diverge. These tests use the REAL engine and planner (no stubs).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from runtime.next._internal_runtime import (
    DiscoveryContext,
    MissionPolicySnapshot,
    NullEmitter,
    next_step,
    start_mission_run,
)
from runtime.next._internal_runtime.engine import _read_snapshot, apply_result, commit_advance, existing_template_path, plan_advance
from runtime.next._internal_runtime.schema import MissionRunSnapshot

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_LOW_DIMENSIONS = {
    "user_customer_impact": 0,
    "architectural_system_impact": 0,
    "data_security_compliance_impact": 0,
    "operational_reliability_impact": 0,
    "financial_commercial_impact": 0,
    "cross_team_blast_radius": 0,
}


def _start_run(tmp_path: Path, *, low_significance_gate: bool) -> Any:
    steps: list[dict[str, Any]] = [
        {"id": "lead_in", "title": "Lead-in", "description": "before the gate", "prompt": "Do the lead-in."},
    ]
    raw: dict[str, Any] = {"mission": {"key": "plan-advance", "name": "Plan advance", "version": "1.0.0"}}
    if low_significance_gate:
        raw["audit_steps"] = [
            {
                "id": "review_gate",
                "title": "Review gate",
                "audit": {"trigger_mode": "manual", "enforcement": "blocking"},
                "depends_on": ["lead_in"],
                "significance": {"dimensions": _LOW_DIMENSIONS, "hard_triggers": []},
            }
        ]
        steps.append({"id": "after_gate", "title": "After the gate", "description": "x", "prompt": "Go on.", "depends_on": ["review_gate"]})
    else:
        steps.append({"id": "second", "title": "Second", "description": "x", "prompt": "Go on.", "depends_on": ["lead_in"]})
    raw["steps"] = steps
    mission_dir = tmp_path / "missions" / "plan-advance"
    mission_dir.mkdir(parents=True)
    yaml_path = mission_dir / "mission.yaml"
    yaml_path.write_text(yaml.safe_dump(raw, sort_keys=True), encoding="utf-8")
    ctx = DiscoveryContext(explicit_paths=[yaml_path], builtin_roots=[yaml_path], user_home=tmp_path / "home")
    run_ref = start_mission_run(
        template_key=str(yaml_path),
        inputs={"mission_owner_id": "owner-1"},
        policy_snapshot=MissionPolicySnapshot(),
        context=ctx,
        run_store=tmp_path / "runs",
        emitter=NullEmitter(),
    )
    first = next_step(run_ref, agent_id="agent-1", emitter=NullEmitter())
    assert first.step_id == "lead_in"
    return run_ref


def _run_files(run_ref: Any) -> dict[str, bytes]:
    run_dir = Path(run_ref.run_dir)
    return {path.name: path.read_bytes() for path in sorted(run_dir.iterdir()) if path.is_file()}


def test_plan_advance_writes_nothing(tmp_path: Path) -> None:
    run_ref = _start_run(tmp_path, low_significance_gate=False)
    before = _run_files(run_ref)

    plan = plan_advance(run_ref, "agent-1", "success")

    assert plan.decision.kind == "step"
    assert _run_files(run_ref) == before, "planning must not write or emit anything"


def test_plan_advance_is_exactly_what_next_step_then_issues(tmp_path: Path) -> None:
    run_ref = _start_run(tmp_path, low_significance_gate=False)

    plan = plan_advance(run_ref, "agent-1", "success")
    issued = next_step(run_ref, agent_id="agent-1", emitter=NullEmitter())

    assert (plan.decision.kind, plan.decision.step_id) == (issued.kind, issued.step_id) == ("step", "second")
    assert plan.completed_step_id == "lead_in"


def test_plan_advance_includes_the_significance_low_replan(tmp_path: Path) -> None:
    """The divergence the review found in the bridge's mirror: an audit gate
    whose significance band is LOW auto-proceeds and the engine re-plans to
    the NEXT step. The plan must already contain that re-plan."""
    run_ref = _start_run(tmp_path, low_significance_gate=True)
    before = _run_files(run_ref)

    plan = plan_advance(run_ref, "agent-1", "success")

    assert _run_files(run_ref) == before
    assert (plan.decision.kind, plan.decision.step_id) == ("step", "after_gate")
    assert {"lead_in", "review_gate"} <= set(plan.snapshot.completed_steps)
    assert plan.significance is not None

    issued = next_step(run_ref, agent_id="agent-1", emitter=NullEmitter())
    assert (issued.kind, issued.step_id) == ("step", "after_gate")
    assert _read_snapshot(Path(run_ref.run_dir)).issued_step_id == "after_gate"


@pytest.mark.parametrize("result", ["failed", "blocked"])
def test_apply_result_records_a_non_success_result_as_blocked(tmp_path: Path, result: Any) -> None:
    run_ref = _start_run(tmp_path, low_significance_gate=False)
    snapshot = _read_snapshot(Path(run_ref.run_dir))

    applied, completed_step_id = apply_result(snapshot, result)

    assert completed_step_id == "lead_in"
    assert applied.issued_step_id is None
    assert "lead_in" not in applied.completed_steps
    assert applied.blocked_reason is not None and "lead_in" in applied.blocked_reason
    assert plan_advance(run_ref, "agent-1", result).decision.kind == "blocked"


def test_apply_result_success_completes_the_issued_step_and_is_pure(tmp_path: Path) -> None:
    run_ref = _start_run(tmp_path, low_significance_gate=False)
    snapshot = _read_snapshot(Path(run_ref.run_dir))

    applied, completed_step_id = apply_result(snapshot, "success")

    assert completed_step_id == "lead_in"
    assert applied.issued_step_id is None
    assert applied.completed_steps == ["lead_in"]
    assert snapshot.issued_step_id == "lead_in", "the input snapshot is frozen and untouched"
    assert apply_result(applied, "success") == (applied, None), "nothing issued -> nothing to complete"


def test_commit_advance_issues_the_plan_it_is_given_without_replanning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A caller that pre-planned commits THAT plan: the engine does not plan again."""
    from runtime.next._internal_runtime import engine

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    plan = plan_advance(run_ref, "agent-1", "success")

    def _no_replan(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("commit_advance must not plan again")

    monkeypatch.setattr(engine, "plan_advance", _no_replan)

    issued = commit_advance(run_ref, plan, "agent-1", NullEmitter())

    assert issued is plan.decision
    assert (issued.kind, issued.step_id) == ("step", "second")
    assert _read_snapshot(Path(run_ref.run_dir)).issued_step_id == "second"


def test_commit_advance_leaves_the_same_run_state_and_events_as_next_step(tmp_path: Path) -> None:
    """``next_step`` stays plan + commit: pre-planning changes nothing durable."""
    import json

    committed = _start_run(tmp_path / "a", low_significance_gate=True)
    stepped = _start_run(tmp_path / "b", low_significance_gate=True)

    commit_advance(committed, plan_advance(committed, "agent-1", "success"), "agent-1", NullEmitter())
    next_step(stepped, agent_id="agent-1", emitter=NullEmitter())

    def _event_types(run_ref: Any) -> list[str]:
        lines = (Path(run_ref.run_dir) / "run.events.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line)["event_type"] for line in lines]

    def _state(run_ref: Any) -> tuple[Any, ...]:
        snap = _read_snapshot(Path(run_ref.run_dir))
        return (snap.issued_step_id, sorted(snap.completed_steps), sorted(snap.decisions), sorted(snap.pending_decisions), snap.blocked_reason)

    assert _event_types(committed) == _event_types(stepped)
    assert _state(committed) == _state(stepped)


@pytest.mark.parametrize("on_disk", ["blank", "missing", "present"])
def test_existing_template_path_is_the_live_template_only_while_it_exists(tmp_path: Path, on_disk: str) -> None:
    """The plan hands the planner a live template path for drift detection only when the file still exists."""
    template_file = tmp_path / "template.yaml"
    template_path = {"blank": "", "missing": str(tmp_path / "does-not-exist.yaml"), "present": str(template_file)}[on_disk]
    template_file.write_text("x", encoding="utf-8")
    snapshot = MissionRunSnapshot(run_id="r", mission_key="m", template_path=template_path, template_hash="h")

    assert existing_template_path(snapshot) == (template_file if on_disk == "present" else None)


@pytest.mark.parametrize("result", ["failed", "blocked"])
def test_retry_preserves_failed_attempt_and_reissues_original_step(tmp_path: Path, result: str) -> None:
    """A deliberate retry never treats the failed attempt as success."""
    from runtime.next._internal_runtime import engine

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    failed = next_step(run_ref, agent_id="agent-1", result=result, emitter=NullEmitter())
    assert failed.kind == "blocked"
    run_dir = Path(run_ref.run_dir)
    original_events = (run_dir / "run.events.jsonl").read_bytes()
    original_state = _read_snapshot(run_dir)
    assert original_state.issued_step_id is None and "lead_in" not in original_state.completed_steps
    retry = getattr(engine, "plan_retry_failed_step", None)
    assert callable(retry), "No supported retry exists for a persisted unsuccessful step"
    before = _run_files(run_ref)
    plan = retry(run_ref, agent_id="agent-1", expected_step_id="lead_in", expected_result=result)
    assert _run_files(run_ref) == before, "retry planning must not mutate the original run"
    decision = commit_advance(run_ref, plan, "agent-1", NullEmitter())
    after = _read_snapshot(run_dir)
    assert (decision.kind, decision.step_id) == ("step", "lead_in")
    assert after.run_id == original_state.run_id and after.issued_step_id == "lead_in"
    assert "lead_in" not in after.completed_steps and after.blocked_reason is None
    events = (run_dir / "run.events.jsonl").read_bytes()
    assert events.startswith(original_events)
    import json

    issued = json.loads(events.splitlines()[-1])
    assert issued["event_type"] == "NextStepIssued"
    assert issued["payload"]["actor"]["tool"] == "spec-kitty next retry-failed-step"


@pytest.mark.parametrize("corruption", ["wrong_step", "wrong_result", "audit_rejection", "pending_decision", "journal_tail", "template_change"])
def test_retry_refuses_mismatched_or_ambiguous_authority_without_mutation(tmp_path: Path, corruption: str) -> None:
    from runtime.next._internal_runtime import engine
    from runtime.next._internal_runtime.schema import MissionRuntimeError

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    next_step(run_ref, agent_id="agent-1", result="failed", emitter=NullEmitter())
    run_dir = Path(run_ref.run_dir)
    kwargs = {"expected_step_id": "lead_in", "expected_result": "failed"}
    if corruption == "wrong_step":
        kwargs["expected_step_id"] = "second"
    elif corruption == "wrong_result":
        kwargs["expected_result"] = "blocked"
    elif corruption in ("audit_rejection", "pending_decision"):
        state = _read_snapshot(run_dir)
        update = {"blocked_reason": "Audit step 'review' rejected by owner"} if corruption == "audit_rejection" else {"pending_decisions": {"audit:review": {}}}
        engine._write_snapshot(run_dir, state.model_copy(update=update))
    elif corruption == "journal_tail":
        with (run_dir / "run.events.jsonl").open("ab") as handle:
            handle.write(b'{"event_type":"unrelated","payload":{}}\n')
    else:
        with (run_dir / "mission_template_frozen.yaml").open("ab") as handle:
            handle.write(b"\n# changed\n")
    before = _run_files(run_ref)
    with pytest.raises(MissionRuntimeError):
        engine.plan_retry_failed_step(run_ref, "agent-1", **kwargs)
    assert _run_files(run_ref) == before


def test_retry_rejects_stale_history_and_forged_unblock_without_writing(tmp_path: Path) -> None:
    from runtime.next._internal_runtime import engine
    from runtime.next._internal_runtime.schema import MissionRuntimeError

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    next_step(run_ref, agent_id="agent-1", result="failed", emitter=NullEmitter())
    run_dir = Path(run_ref.run_dir)
    plan = engine.plan_retry_failed_step(run_ref, "agent-1", expected_step_id="lead_in", expected_result="failed")
    with (run_dir / "run.events.jsonl").open("ab") as handle:
        handle.write(b'{"event_type":"unrelated","payload":{}}\n')
    before = _run_files(run_ref)
    with pytest.raises(engine.StaleAdvancePlan):
        commit_advance(run_ref, plan, "agent-1", NullEmitter())
    assert _run_files(run_ref) == before
    normal = plan_advance(run_ref, "agent-1", "success")
    forged = normal.model_copy(update={"snapshot": normal.snapshot.model_copy(update={"blocked_reason": None})})
    with pytest.raises(MissionRuntimeError):
        commit_advance(run_ref, forged, "agent-1", NullEmitter())
    assert _run_files(run_ref) == before


def test_retry_parses_the_checked_template_bytes_without_reopening(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.next._internal_runtime import engine

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    next_step(run_ref, agent_id="agent-1", result="failed", emitter=NullEmitter())

    def reject_reopen(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("retry must parse the bytes it checked")

    monkeypatch.setattr(engine, "_load_frozen_template", reject_reopen)
    plan = engine.plan_retry_failed_step(run_ref, "agent-1", expected_step_id="lead_in", expected_result="failed")
    assert (plan.decision.kind, plan.decision.step_id) == ("step", "lead_in")


def test_retry_refuses_a_symlinked_frozen_template(tmp_path: Path) -> None:
    from runtime.next._internal_runtime import engine
    from runtime.next._internal_runtime.schema import MissionRuntimeError

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    next_step(run_ref, agent_id="agent-1", result="failed", emitter=NullEmitter())
    run_dir = Path(run_ref.run_dir)
    frozen = run_dir / "mission_template_frozen.yaml"
    other = run_dir / "template-copy.yaml"
    other.write_bytes(frozen.read_bytes())
    frozen.unlink()
    frozen.symlink_to(other)
    before = (run_dir / "run.events.jsonl").read_bytes()
    with pytest.raises((MissionRuntimeError, OSError)):
        engine.plan_retry_failed_step(run_ref, "agent-1", expected_step_id="lead_in", expected_result="failed")
    assert (run_dir / "run.events.jsonl").read_bytes() == before


def test_interrupted_retry_retains_history_and_refuses_ambiguous_reissue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.next._internal_runtime import engine
    from runtime.next._internal_runtime.schema import MissionRuntimeError

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    next_step(run_ref, agent_id="agent-1", result="failed", emitter=NullEmitter())
    run_dir = Path(run_ref.run_dir)
    original = (run_dir / "run.events.jsonl").read_bytes()
    plan = engine.plan_retry_failed_step(run_ref, "agent-1", expected_step_id="lead_in", expected_result="failed")

    def fail_write(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("injected snapshot failure")

    monkeypatch.setattr(engine, "_write_snapshot", fail_write)
    with pytest.raises(OSError, match="injected snapshot failure"):
        commit_advance(run_ref, plan, "agent-1", NullEmitter())
    assert (run_dir / "run.events.jsonl").read_bytes().startswith(original)
    assert _read_snapshot(run_dir).blocked_reason is not None
    before = _run_files(run_ref)
    with pytest.raises(MissionRuntimeError):
        engine.plan_retry_failed_step(run_ref, "agent-1", expected_step_id="lead_in", expected_result="failed")
    assert _run_files(run_ref) == before


def test_competing_retry_commits_issue_the_step_at_most_once(tmp_path: Path) -> None:
    import json
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from kernel.locks import LockNotAcquired
    from runtime.next._internal_runtime import engine

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    next_step(run_ref, agent_id="agent-1", result="failed", emitter=NullEmitter())
    plan = engine.plan_retry_failed_step(run_ref, "agent-1", expected_step_id="lead_in", expected_result="failed")
    barrier = threading.Barrier(2)

    def commit() -> str:
        barrier.wait(timeout=5)
        try:
            commit_advance(run_ref, plan, "agent-1", NullEmitter())
            return "issued"
        except (LockNotAcquired, engine.StaleAdvancePlan):
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result(timeout=15) for future in (pool.submit(commit), pool.submit(commit))]
    assert sorted(results) == ["issued", "refused"]
    run_dir = Path(run_ref.run_dir)
    events = [json.loads(line) for line in (run_dir / "run.events.jsonl").read_text(encoding="utf-8").splitlines()]
    retries = [
        event
        for event in events
        if event.get("event_type") == "NextStepIssued" and event.get("payload", {}).get("actor", {}).get("tool") == "spec-kitty next retry-failed-step"
    ]
    assert len(retries) == 1
    assert _read_snapshot(run_dir).issued_step_id == "lead_in"


def test_retry_shares_the_published_run_cursor_lock(tmp_path: Path) -> None:
    """An installed current runtime must exclude this Source retry writer."""
    from kernel.locks import LockNotAcquired, machine_file_lock
    from runtime.next._internal_runtime import engine

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    published_lock = Path(run_ref.run_dir) / "state.json.lock"
    with engine._run_write_lock(run_ref), pytest.raises(LockNotAcquired), machine_file_lock(published_lock):
        pass


def test_run_cursor_lock_refuses_hardlinked_sentinel(tmp_path: Path) -> None:
    import os

    from runtime.next._internal_runtime import engine

    run_ref = _start_run(tmp_path, low_significance_gate=False)
    sidecar = Path(run_ref.run_dir) / "state.json.lock"
    sidecar.unlink()  # This disposable fixture has no holder after _start_run.
    victim = tmp_path / "sentinel"
    victim.write_bytes(b"preserve this evidence\n")
    try:
        os.link(victim, sidecar)
    except OSError as exc:
        pytest.skip(f"Hard links unavailable on this filesystem: {exc}")
    with pytest.raises(OSError, match="single-link regular"), engine._run_write_lock(run_ref):
        pytest.fail("A hard-linked run cursor must not be acquired")
    assert victim.read_bytes() == b"preserve this evidence\n"
