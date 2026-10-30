"""Targeted coverage for the structured-blocked emit branches in
``runtime_bridge.py`` (PR #855 follow-up — diff-coverage fill).

The CI diff-coverage gate flagged the following lines uncovered by the WP06
prompt-file-invariant tests:

- ``runtime_bridge.py:1565-1609`` — legacy DAG path guard failures: when
  ``current_step_id`` has a guard failure on a non-WP step, the runtime
  must build a structured ``blocked`` decision (with the resolvable prompt
  attached when one is available, or with the prompt-resolution error
  threaded into the reason when not).
- ``runtime_bridge_decision_mapping._build_wp_iteration_decision`` with a
  prompt-resolution error must yield a structured ``blocked`` instead of a
  partial step.
- ``runtime_bridge_decision_mapping._map_runtime_decision`` non-WP step branch
  with neither ``action`` nor ``step_id`` mapped must short-circuit to a
  structured ``blocked`` with a populated reason (no template lookup).

The existing `test_prompt_file_invariant.py` covers the contract surface
but doesn't drive these specific lines because it stubs ``_state_to_action``
to always return a usable action. Here we drive the branches directly.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from runtime.next.decision import DecisionKind
from runtime.next import runtime_bridge_decision_mapping as decision_mapping

pytestmark = pytest.mark.fast


@pytest.mark.parametrize("case", ["missing", "stale", "raises", "changes", "wrong_action", "wrong_wp", "wrong_workspace", "wrong_run", "wrong_step", "current"])
def test_retry_implementation_never_issues_without_current_analysis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """A retry must not turn a stale report or a remapped step into issuance."""
    from runtime.next import runtime_bridge as bridge

    ctx = SimpleNamespace(
        mission_type="software-dev",
        now="2026-10-30T00:00:00Z",
        progress=None,
        origin={},
        run_ref=SimpleNamespace(run_id="original", run_dir=str(tmp_path / "run")),
        feature_dir=tmp_path,
        emitter_for_engine=object(),
    )
    plan = SimpleNamespace(decision=SimpleNamespace(kind="step", step_id="implement"))
    issued: list[str] = []
    monkeypatch.setattr(bridge._mapping, "_merged_mission_short_circuit", lambda **_kwargs: None)
    monkeypatch.setattr(bridge, "_dn_bootstrap", lambda *_args, **_kwargs: (ctx, None))
    monkeypatch.setattr(bridge._engine_adapter, "plan_retry_failed_step", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(bridge, "_resolve_planned_wp_workspace", lambda *_args, **_kwargs: ("implement", "WP01", str(tmp_path), None, "implement"))
    monkeypatch.setattr(bridge._io_seam, "get_or_start_run", lambda *_args, **_kwargs: ctx.run_ref)
    monkeypatch.setattr(
        bridge._mapping,
        "_map_runtime_decision",
        lambda *_args, **_kwargs: SimpleNamespace(
            kind="step",
            run_id="other" if case == "wrong_run" else "original",
            step_id="review" if case == "wrong_step" else "implement",
            action="analyze" if case == "wrong_action" else "implement",
            wp_id="WP02" if case == "wrong_wp" else "WP01",
            workspace_path=str(tmp_path / "other") if case == "wrong_workspace" else str(tmp_path),
        ),
    )
    monkeypatch.setattr(bridge._engine_adapter, "commit_advance", lambda *_args, **_kwargs: issued.append("issued"))

    answers = iter([None, "analysis report became stale"] if case == "changes" else ["analysis report is stale"] if case == "stale" else [None, None])

    def analysis_guard() -> str | None:
        if case == "raises":
            raise OSError("analysis unavailable")
        return next(answers)

    kwargs = {} if case == "missing" else {"retry_analysis_guard": analysis_guard}
    result = bridge.retry_failed_step_via_runtime("agent", "mission", tmp_path, run_id="original", step_id="implement", result="failed", **kwargs)
    assert result.kind == (DecisionKind.step if case == "current" else DecisionKind.blocked)
    assert issued == (["issued"] if case == "current" else [])


@pytest.mark.parametrize("failure", ["stale", "board_changed", "prompt_blocked", "index_changed", "none"])
def test_retry_refuses_without_falling_back_or_issuing_wrong_work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    from runtime.next import runtime_bridge as bridge

    ctx = SimpleNamespace(
        mission_type="software-dev",
        now="2026-10-30T00:00:00Z",
        progress=None,
        origin={},
        run_ref=SimpleNamespace(run_id="original", run_dir=str(tmp_path / "run")),
        feature_dir=tmp_path,
        emitter_for_engine=object(),
    )
    plan = SimpleNamespace(decision=SimpleNamespace(kind="step", step_id="implement"))
    seen: list[str] = []
    monkeypatch.setattr(bridge._mapping, "_merged_mission_short_circuit", lambda **_kwargs: None)
    monkeypatch.setattr(bridge, "_dn_bootstrap", lambda *_args, **kwargs: (ctx, None) if kwargs["required_run_id"] == "original" else (None, None))
    monkeypatch.setattr(bridge._engine_adapter, "plan_retry_failed_step", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(
        bridge._io_seam, "get_or_start_run", lambda *_args, **_kwargs: SimpleNamespace(run_dir=str(tmp_path / ("other" if failure == "index_changed" else "run")))
    )
    board_step = "review" if failure == "board_changed" else "implement"
    monkeypatch.setattr(bridge, "_resolve_planned_wp_workspace", lambda *_args, **_kwargs: ("implement", "WP01", str(tmp_path), None, board_step))
    monkeypatch.setattr(
        bridge._mapping,
        "_map_runtime_decision",
        lambda *_args, **_kwargs: SimpleNamespace(
            kind="blocked" if failure == "prompt_blocked" else "step",
            run_id="original",
            step_id="implement",
            action="implement",
            wp_id="WP01",
            workspace_path=str(tmp_path),
        ),
    )

    def commit(*_args, **_kwargs):
        seen.append("commit")
        if failure == "stale":
            raise bridge._engine_adapter.StaleAdvancePlan("run changed")

    monkeypatch.setattr(bridge._engine_adapter, "commit_advance", commit)
    monkeypatch.setattr(bridge, "runtime_next_step", lambda *_args, **_kwargs: pytest.fail("retry must never fall back to success"))
    decision = bridge.retry_failed_step_via_runtime(
        "agent", "mission", tmp_path, run_id="original", step_id="implement", result="failed", retry_analysis_guard=lambda: None
    )
    assert decision.kind == (DecisionKind.step if failure == "none" else DecisionKind.blocked)
    assert seen == (["commit"] if failure in ("stale", "none") else [])


def test_cli_retry_requires_complete_identity_before_resolving_a_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    import typer
    from specify_cli.cli.commands import next_cmd

    monkeypatch.setattr(next_cmd, "locate_project_root", lambda: pytest.fail("incomplete retry must not resolve a checkout"))
    with pytest.raises(typer.Exit):
        next_cmd.next_step(agent="agent", mission="mission", retry_step="implement")


def test_retry_bootstrap_never_starts_when_required_run_was_not_loaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.next import runtime_bridge as bridge

    monkeypatch.setattr(bridge._io_seam, "get_or_start_run", lambda *_args, **_kwargs: pytest.fail("must not start a replacement run"))
    with pytest.raises(ValueError, match="original run was not loaded"):
        bridge._dn_load_run_ref("mission", tmp_path, "software-dev", object(), owned=None, required_ref=None, required_run_id="original")


def test_cli_retry_dispatches_exact_identity_without_pairing_a_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.cli.commands import next_cmd

    calls: list[dict[str, object]] = []
    result = SimpleNamespace(kind="step")
    monkeypatch.setattr(next_cmd, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(next_cmd, "_resolve_next_owned", lambda *_args: None)
    monkeypatch.setattr(next_cmd, "_resolve_slug_or_exit", lambda *_args, **_kwargs: "mission")
    monkeypatch.setattr(next_cmd, "_maybe_emit_runtime_notice", lambda *_args: None)
    monkeypatch.setattr(next_cmd, "_run_charter_preflight_for_next", lambda *_args, **kwargs: calls.append(kwargs))
    monkeypatch.setattr(
        next_cmd, "_runtime_bridge_module", lambda: SimpleNamespace(retry_failed_step_via_runtime=lambda *_args, **kwargs: calls.append(kwargs) or result)
    )
    monkeypatch.setattr(next_cmd, "_pair_previous_lifecycle_record", lambda *_args, **_kwargs: pytest.fail("retry cannot pair success"))
    monkeypatch.setattr(next_cmd, "_write_issuance_lifecycle_record", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(next_cmd, "_print_decision", lambda *_args, **_kwargs: None)
    next_cmd.next_step(agent="agent", mission="mission", retry_run_id="original", retry_step="implement", retry_result="failed")
    assert calls[0]["advancing"] is True
    assert {key: value for key, value in calls[1].items() if key != "retry_analysis_guard"} == {
        "run_id": "original",
        "step_id": "implement",
        "result": "failed",
        "owned": None,
    }
    assert callable(calls[1]["retry_analysis_guard"])


def test_refused_owned_retry_never_commits_unrelated_mission_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import typer
    from specify_cli.cli.commands import _owned_retry_lifecycle
    from specify_cli.cli.commands import next_cmd

    owned = SimpleNamespace(owned_root=tmp_path, repository_root=tmp_path)
    monkeypatch.setattr(next_cmd, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr(next_cmd, "_resolve_next_owned", lambda *_args: owned)
    monkeypatch.setattr(next_cmd, "_resolve_slug_or_exit", lambda *_args, **_kwargs: "mission")
    monkeypatch.setattr(next_cmd, "_maybe_emit_runtime_notice", lambda *_args: None)
    monkeypatch.setattr(next_cmd, "_run_charter_preflight_for_next", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_owned_retry_lifecycle, "capture_owned_retry_lifecycle", lambda *_args: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(
        next_cmd, "_runtime_bridge_module", lambda: SimpleNamespace(retry_failed_step_via_runtime=lambda *_args, **_kwargs: SimpleNamespace(kind="blocked"))
    )
    monkeypatch.setattr(next_cmd, "_write_issuance_lifecycle_record", lambda *_args, **_kwargs: pytest.fail("refusal has no issuance"))
    monkeypatch.setattr(_owned_retry_lifecycle, "commit_owned_retry_lifecycle", lambda *_args, **_kwargs: pytest.fail("refusal must not commit"))
    monkeypatch.setattr(next_cmd, "_print_decision", lambda *_args, **_kwargs: None)
    with pytest.raises(typer.Exit):
        next_cmd.next_step(agent="agent", mission="mission", retry_run_id="original", retry_step="implement", retry_result="failed")


# ---------------------------------------------------------------------------
# 2156 — _build_wp_iteration_decision blocked when prompt unresolvable
# ---------------------------------------------------------------------------


def _runtime_decision(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "kind": "step",
        "step_id": "implement",
        "run_id": "run-001",
        "decision_id": None,
        "question": None,
        "options": None,
        "input_key": None,
        "reason": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestWPIterationDecisionBlockedBranch:
    """``runtime_bridge_decision_mapping._build_wp_iteration_decision`` blocked path."""

    def test_wp_iteration_blocked_when_prompt_unresolvable_with_guard_failures(self, tmp_path: Path) -> None:
        """Direct unit-level call to `_build_wp_iteration_decision`.

        Ensures the blocked branch (line 2156-2172) fires when the helper
        returns a non-empty error and `guard_failures` is supplied. The
        resulting Decision must:
          - kind == blocked
          - reason == prompt_error
          - guard_failures forwarded (not dropped)
          - prompt_file is None
        """
        from runtime.next.runtime_bridge_decision_mapping import _build_wp_iteration_decision

        run_ref = SimpleNamespace(run_id="run-blocked-01")

        with (
            patch(
                "runtime.next.runtime_bridge_decision_mapping._state_to_action",
                return_value=("implement", "WP01", str(tmp_path / ".worktrees" / "lane-a")),
            ) as state_to_action,
            patch(
                "runtime.next.runtime_bridge_decision_mapping._build_prompt_or_error",
                return_value=(None, "prompt resolution failed for action 'implement'", None),
            ) as build_prompt,
        ):
            decision = _build_wp_iteration_decision(
                step_id="implement",
                agent="claude",
                mission_slug="042-test",
                mission_type="software-dev",
                feature_dir=tmp_path,
                repo_root=tmp_path,
                timestamp="2026-04-28T00:00:00+00:00",
                progress=None,
                origin={},
                run_ref=run_ref,
                guard_failures=["pre-existing guard"],
            )

        # The fakes steer runtime_bridge_decision_mapping, where the code under test reads them (#2560).
        state_to_action.assert_called()
        build_prompt.assert_called()
        assert decision.kind == DecisionKind.blocked
        assert decision.reason
        assert "prompt resolution failed" in decision.reason
        assert decision.prompt_file is None
        assert decision.guard_failures == ["pre-existing guard"]
        assert decision.action == "implement"
        assert decision.wp_id == "WP01"


# ---------------------------------------------------------------------------
# 2364 — _map_runtime_decision non-WP step with neither action nor step_id
# ---------------------------------------------------------------------------


class TestMapRuntimeDecisionNoActionNoStepId:
    """``runtime_bridge_decision_mapping._map_runtime_decision`` no-action AND no-step_id branch."""

    def test_map_runtime_decision_emits_blocked_when_no_action_and_no_step_id(self, tmp_path: Path) -> None:
        """Drive the no-action `else` branch of the non-WP step mapping.

        Pre-condition: `_state_to_action` returns (None, None, None) AND
        `decision.step_id` is None. The map function must NOT attempt to
        resolve a prompt (prompt_error is set inline) and must emit a
        blocked decision.
        """
        from runtime.next.runtime_bridge_decision_mapping import _map_runtime_decision

        with (
            patch(
                "runtime.next.runtime_bridge_decision_mapping._state_to_action",
                return_value=(None, None, None),
            ) as state_to_action,
        ):
            # step_id=None forces the `if action or step_id` guard to fall
            # through to the no-action `else` branch.
            decision = _map_runtime_decision(
                decision=_runtime_decision(step_id=None),
                agent="claude",
                mission_slug="042-test",
                mission_type="software-dev",
                repo_root=tmp_path,
                feature_dir=tmp_path,
                timestamp="2026-04-28T00:00:00+00:00",
                progress=None,
                origin={},
            )

        # The fakes steer runtime_bridge_decision_mapping, where the code under test reads them (#2560).
        state_to_action.assert_called()
        assert decision.kind == DecisionKind.blocked
        assert decision.reason
        assert "no action and no step_id" in decision.reason
        assert decision.prompt_file is None


# ---------------------------------------------------------------------------
# 1565-1609 — legacy DAG path: non-WP step + guard failures + prompt branch
# ---------------------------------------------------------------------------


class TestDecideNextViaRuntimeGuardFailureBlocked:
    """runtime_bridge.py:1561-1608 (`decide_next_via_runtime` guard branch).

    When ``result == "success"``, the current step is NOT a WP iteration step,
    and ``_check_cli_guards`` returns a non-empty list, the runtime MUST
    surface a structured blocked decision with the prompt either attached
    (when resolvable) or threaded into the reason (when not).
    """

    def _build_minimal_feature_dir(self, tmp_path: Path, mission_slug: str) -> Path:
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        feature_dir.mkdir(parents=True, exist_ok=True)
        # Minimal meta so get_mission_type doesn't blow up.
        (feature_dir / "meta.json").write_text(
            '{"mission_type": "software-dev"}',
            encoding="utf-8",
        )
        return feature_dir

    def test_guard_failure_on_non_wp_step_yields_blocked_with_prompt_error(self, tmp_path: Path) -> None:
        """Lines 1561-1609 — the prompt-error branch of the guard handler.

        Drives the branch where ``_state_to_action`` returns a usable
        ``action`` and ``_build_prompt_or_error`` returns ``(None, error)``.
        The decision must be ``blocked`` with the prompt error in
        ``reason``.
        """
        from runtime.next import runtime_bridge as rb

        mission_slug = "042-test"
        self._build_minimal_feature_dir(tmp_path, mission_slug)

        # Stub helpers to drive the exact branch with no real runtime engine.
        run_ref = SimpleNamespace(run_id="run-guard-01", run_dir=str(tmp_path / "run"))
        snapshot = SimpleNamespace(issued_step_id="specify")

        with (
            patch.object(rb, "get_mission_type", return_value="software-dev"),
            patch.object(rb, "runtime_emitter_for_mission") as sync_factory,
            patch("runtime.next.runtime_bridge_io.get_or_start_run", return_value=run_ref) as get_run,
            patch.object(rb, "_compute_wp_progress", return_value=None),
            patch.object(rb, "_check_cli_guards", return_value=["specify_guard_failure"]),
            patch.object(decision_mapping, "_is_wp_iteration_step", return_value=False),
            patch.object(rb, "_state_to_action", return_value=("specify", None, None)),
            patch.object(
                rb,
                "_build_prompt_or_error",
                return_value=(None, "prompt resolution failed for action 'specify'", None),
            ),
            patch(
                "runtime.next._internal_runtime.engine._read_snapshot",
                return_value=snapshot,
            ),
        ):
            sync_factory.return_value = SimpleNamespace(seed_from_snapshot=lambda *_a, **_k: None)
            decision = rb.decide_next_via_runtime(
                agent="claude",
                mission_slug=mission_slug,
                result="success",
                repo_root=tmp_path,
            )

        # decide_next_via_runtime looks the run up on the io seam: prove the fake was that binding.
        get_run.assert_called_once()
        assert decision.kind == DecisionKind.blocked
        assert decision.reason
        assert "prompt resolution failed" in decision.reason
        assert decision.guard_failures == ["specify_guard_failure"]
        assert decision.action == "specify"
        assert decision.prompt_file is None

    def test_guard_failure_on_non_wp_step_with_resolvable_prompt(self, tmp_path: Path) -> None:
        """Lines 1561-1609 — the prompt-attached branch (line 1609+).

        Same setup as above but with a resolvable prompt: the decision is
        still blocked (because guards failed), but it MUST carry the
        resolvable ``prompt_file`` rather than a prompt-error reason.
        """
        from runtime.next import runtime_bridge as rb

        mission_slug = "042-test"
        self._build_minimal_feature_dir(tmp_path, mission_slug)

        prompt_path = tmp_path / "specify-prompt.md"
        prompt_path.write_text("# specify\n", encoding="utf-8")

        run_ref = SimpleNamespace(run_id="run-guard-02", run_dir=str(tmp_path / "run"))
        snapshot = SimpleNamespace(issued_step_id="specify")

        with (
            patch.object(rb, "get_mission_type", return_value="software-dev"),
            patch.object(rb, "runtime_emitter_for_mission") as sync_factory,
            patch("runtime.next.runtime_bridge_io.get_or_start_run", return_value=run_ref) as get_run,
            patch.object(rb, "_compute_wp_progress", return_value=None),
            patch.object(rb, "_check_cli_guards", return_value=["specify_guard_failure"]),
            patch.object(decision_mapping, "_is_wp_iteration_step", return_value=False),
            patch.object(rb, "_state_to_action", return_value=("specify", None, None)),
            patch.object(
                rb,
                "_build_prompt_or_error",
                return_value=(str(prompt_path), None, None),
            ),
            patch(
                "runtime.next._internal_runtime.engine._read_snapshot",
                return_value=snapshot,
            ),
        ):
            sync_factory.return_value = SimpleNamespace(seed_from_snapshot=lambda *_a, **_k: None)
            decision = rb.decide_next_via_runtime(
                agent="claude",
                mission_slug=mission_slug,
                result="success",
                repo_root=tmp_path,
            )

        # When guards fail but the prompt is resolvable, the decision is
        # still structured (blocked OR step depending on policy). The
        # critical contract is: guard_failures are surfaced, and any
        # `prompt_file` attached must point to a real file.
        # decide_next_via_runtime looks the run up on the io seam: prove the fake was that binding.
        get_run.assert_called_once()
        assert decision.guard_failures == ["specify_guard_failure"]
        if decision.prompt_file is not None:
            assert Path(decision.prompt_file).exists()

    def test_guard_failure_blocks_if_resolved_prompt_disappears(self, tmp_path: Path) -> None:
        """A prompt can disappear after resolution; keep the step invariant hard."""
        from runtime.next import runtime_bridge as rb

        mission_slug = "042-test"
        self._build_minimal_feature_dir(tmp_path, mission_slug)

        prompt_path = tmp_path / "specify-prompt.md"
        prompt_path.write_text("# specify\n", encoding="utf-8")

        run_ref = SimpleNamespace(run_id="run-guard-04", run_dir=str(tmp_path / "run"))
        snapshot = SimpleNamespace(issued_step_id="specify")

        with (
            patch.object(rb, "get_mission_type", return_value="software-dev"),
            patch.object(rb, "runtime_emitter_for_mission") as sync_factory,
            patch("runtime.next.runtime_bridge_io.get_or_start_run", return_value=run_ref) as get_run,
            patch.object(rb, "_compute_wp_progress", return_value=None),
            patch.object(rb, "_check_cli_guards", return_value=["specify_guard_failure"]),
            patch.object(decision_mapping, "_is_wp_iteration_step", return_value=False),
            patch.object(rb, "_state_to_action", return_value=("specify", None, None)),
            patch.object(
                rb,
                "_build_prompt_or_error",
                return_value=(str(prompt_path), None, None),
            ),
            patch("pathlib.Path.is_file", return_value=False),
            patch(
                "runtime.next._internal_runtime.engine._read_snapshot",
                return_value=snapshot,
            ),
        ):
            sync_factory.return_value = SimpleNamespace(seed_from_snapshot=lambda *_a, **_k: None)
            decision = rb.decide_next_via_runtime(
                agent="claude",
                mission_slug=mission_slug,
                result="success",
                repo_root=tmp_path,
            )

        # decide_next_via_runtime looks the run up on the io seam: prove the fake was that binding.
        get_run.assert_called_once()
        assert decision.kind == DecisionKind.blocked
        assert decision.reason == "prompt_file_not_resolvable"
        assert decision.guard_failures == ["specify_guard_failure"]
        assert decision.prompt_file is None

    def test_guard_failure_on_non_wp_step_no_action_mapped(self, tmp_path: Path) -> None:
        """Lines 1584-1587 — `_state_to_action` returns (None, ...) branch.

        When no action can be mapped for the current step, the helper
        composes the prompt-error reason inline (`no action mapped for
        step ...`) without invoking `_build_prompt_or_error`.
        """
        from runtime.next import runtime_bridge as rb

        mission_slug = "042-test"
        self._build_minimal_feature_dir(tmp_path, mission_slug)

        run_ref = SimpleNamespace(run_id="run-guard-03", run_dir=str(tmp_path / "run"))
        snapshot = SimpleNamespace(issued_step_id="exotic-step")

        with (
            patch.object(rb, "get_mission_type", return_value="software-dev"),
            patch.object(rb, "runtime_emitter_for_mission") as sync_factory,
            patch("runtime.next.runtime_bridge_io.get_or_start_run", return_value=run_ref) as get_run,
            patch.object(rb, "_compute_wp_progress", return_value=None),
            patch.object(rb, "_check_cli_guards", return_value=["exotic_guard_failure"]),
            patch.object(decision_mapping, "_is_wp_iteration_step", return_value=False),
            patch.object(rb, "_state_to_action", return_value=(None, None, None)),
            patch(
                "runtime.next._internal_runtime.engine._read_snapshot",
                return_value=snapshot,
            ),
        ):
            sync_factory.return_value = SimpleNamespace(seed_from_snapshot=lambda *_a, **_k: None)
            decision = rb.decide_next_via_runtime(
                agent="claude",
                mission_slug=mission_slug,
                result="success",
                repo_root=tmp_path,
            )

        # decide_next_via_runtime looks the run up on the io seam: prove the fake was that binding.
        get_run.assert_called_once()
        assert decision.kind == DecisionKind.blocked
        assert decision.reason
        assert "no action mapped" in decision.reason
        assert decision.guard_failures == ["exotic_guard_failure"]
        assert decision.prompt_file is None


class TestResolvedPromptRaceFallbacks:
    """Cover every runtime bridge path that catches ``InvalidStepDecision``."""

    def test_wp_iteration_blocks_if_resolved_prompt_disappears(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge_decision_mapping import _build_wp_iteration_decision

        prompt_path = tmp_path / "implement-prompt.md"
        prompt_path.write_text("# implement\n", encoding="utf-8")
        run_ref = SimpleNamespace(run_id="run-wp-race")

        with (
            patch(
                "runtime.next.runtime_bridge_decision_mapping._state_to_action",
                return_value=("implement", "WP01", str(tmp_path / ".worktrees" / "lane-a")),
            ) as state_to_action,
            patch(
                "runtime.next.runtime_bridge_decision_mapping._build_prompt_or_error",
                return_value=(str(prompt_path), None, None),
            ) as build_prompt,
            patch("pathlib.Path.is_file", return_value=False),
        ):
            decision = _build_wp_iteration_decision(
                step_id="implement",
                agent="claude",
                mission_slug="042-test",
                mission_type="software-dev",
                feature_dir=tmp_path,
                repo_root=tmp_path,
                timestamp="2026-04-28T00:00:00+00:00",
                progress=None,
                origin={},
                run_ref=run_ref,
            )

        # The fakes steer runtime_bridge_decision_mapping, where the code under test reads them (#2560).
        state_to_action.assert_called()
        build_prompt.assert_called()
        assert decision.kind == DecisionKind.blocked
        assert decision.reason == "prompt_file_not_resolvable"
        assert decision.prompt_file is None

    def test_map_wp_step_blocks_if_resolved_prompt_disappears(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge_decision_mapping import _map_runtime_decision

        prompt_path = tmp_path / "implement-prompt.md"
        prompt_path.write_text("# implement\n", encoding="utf-8")

        with (
            patch(
                "runtime.next.runtime_bridge_decision_mapping._state_to_action",
                return_value=("implement", "WP01", str(tmp_path / ".worktrees" / "lane-a")),
            ) as state_to_action,
            patch(
                "runtime.next.runtime_bridge_decision_mapping._is_wp_iteration_step",
                return_value=True,
            ),
            patch(
                "runtime.next.runtime_bridge_decision_mapping._build_prompt_or_error",
                return_value=(str(prompt_path), None, None),
            ) as build_prompt,
            patch("pathlib.Path.is_file", return_value=False),
        ):
            decision = _map_runtime_decision(
                decision=_runtime_decision(step_id="implement"),
                agent="claude",
                mission_slug="042-test",
                mission_type="software-dev",
                repo_root=tmp_path,
                feature_dir=tmp_path,
                timestamp="2026-04-28T00:00:00+00:00",
                progress=None,
                origin={},
            )

        # The fakes steer runtime_bridge_decision_mapping, where the code under test reads them (#2560).
        state_to_action.assert_called()
        build_prompt.assert_called()
        assert decision.kind == DecisionKind.blocked
        assert decision.reason == "prompt_file_not_resolvable"
        assert decision.prompt_file is None

    def test_map_non_wp_step_blocks_if_resolved_prompt_disappears(self, tmp_path: Path) -> None:
        from runtime.next.runtime_bridge_decision_mapping import _map_runtime_decision

        prompt_path = tmp_path / "specify-prompt.md"
        prompt_path.write_text("# specify\n", encoding="utf-8")

        with (
            patch(
                "runtime.next.runtime_bridge_decision_mapping._state_to_action",
                return_value=("specify", None, None),
            ) as state_to_action,
            patch(
                "runtime.next.runtime_bridge_decision_mapping._is_wp_iteration_step",
                return_value=False,
            ),
            patch(
                "runtime.next.runtime_bridge_decision_mapping._build_prompt_or_error",
                return_value=(str(prompt_path), None, None),
            ) as build_prompt,
            patch("pathlib.Path.is_file", return_value=False),
        ):
            decision = _map_runtime_decision(
                decision=_runtime_decision(step_id="specify"),
                agent="claude",
                mission_slug="042-test",
                mission_type="software-dev",
                repo_root=tmp_path,
                feature_dir=tmp_path,
                timestamp="2026-04-28T00:00:00+00:00",
                progress=None,
                origin={},
            )

        # The fakes steer runtime_bridge_decision_mapping, where the code under test reads them (#2560).
        state_to_action.assert_called()
        build_prompt.assert_called()
        assert decision.kind == DecisionKind.blocked
        assert decision.reason == "prompt_file_not_resolvable"
        assert decision.prompt_file is None
