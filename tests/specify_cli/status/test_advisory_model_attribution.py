"""A profile dispatch recommendation is never evidence of model execution."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from charter.offering.model_task_routing.evaluator import RoutingCandidate, RoutingRecommendation
from specify_cli.cli.commands.agent.workflow import _resolve_dispatch_binding
from specify_cli.invocation.executor import ProfileInvocationExecutor
from specify_cli.invocation.writer import EVENTS_DIR
from specify_cli.status import ResolvedBinding, emit_resolved_binding
from specify_cli.status.resolved_binding import RESOLVED_MODEL_ABSENT, RESOLVED_PROVIDER_ABSENT
from tests.specify_cli.invocation.test_executor import _COMPACT_CTX, _setup_fixture_profiles
from tests.specify_cli.status.test_resolved_binding_linkage import (
    _INVOCATION_ID,
    _MISSION_ID,
    _MISSION_SLUG,
    _WP_ID,
    _make_feature_dir,
    _resolved_slots,
    _write_dispatch_op,
    _write_wp_file,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_real_dispatch_preserves_advice_without_claiming_model_execution(tmp_path: Path) -> None:
    _setup_fixture_profiles(tmp_path)
    recommendation = RoutingRecommendation(
        task_type="implementation",
        objective="quality_first",
        override_mode="advisory",
        candidates=(RoutingCandidate(model_id="claude-opus-4-6", source="catalog", score=0.99),),
    )
    with (
        patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX),
        patch("specify_cli.invocation.executor._compute_recommendation", return_value=recommendation),
    ):
        payload = ProfileInvocationExecutor(tmp_path).invoke(
            "implement WP01",
            profile_hint="implementer-fixture",
            action_hint="implement",
            mission_id=_MISSION_ID,
            wp_id=_WP_ID,
        )
    assert payload.recommendation == recommendation
    record_path = tmp_path / EVENTS_DIR / f"{payload.invocation_id}.jsonl"
    record = json.loads(record_path.read_text().splitlines()[0])
    assert "model_id" not in record, "a recommendation cannot be persisted as actual execution"
    assert record["recommended_model_id"] == "claude-opus-4-6"
    before = record_path.read_bytes()
    binding = _resolve_dispatch_binding(
        model=None,
        profile=None,
        invocation_id=payload.invocation_id,
        repo_root=tmp_path,
        mission_id=_MISSION_ID,
        wp_id=_WP_ID,
        action="implement",
    )
    assert binding.agent_profile == "implementer-fixture"
    assert binding.model is None and binding.provider is None
    assert record_path.read_bytes() == before


def test_historical_model_id_does_not_purchase_actual_binding(tmp_path: Path) -> None:
    _write_dispatch_op(tmp_path)
    record_path = tmp_path / EVENTS_DIR / f"{_INVOCATION_ID}.jsonl"
    before = record_path.read_bytes()
    binding = _resolve_dispatch_binding(
        model=None,
        profile=None,
        invocation_id=_INVOCATION_ID,
        repo_root=tmp_path,
        mission_id=_MISSION_ID,
        wp_id=_WP_ID,
        action="implement",
    )
    assert binding.agent_profile == "python-pedro"
    assert binding.model is None and binding.provider is None
    assert record_path.read_bytes() == before


def test_matching_advisory_model_argument_is_still_unproven(tmp_path: Path) -> None:
    _write_dispatch_op(tmp_path)
    with pytest.raises(ValueError, match="execution"):
        _resolve_dispatch_binding(
            model="claude-opus-4-6",
            profile=None,
            invocation_id=_INVOCATION_ID,
            repo_root=tmp_path,
            mission_id=_MISSION_ID,
            wp_id=_WP_ID,
            action="implement",
        )


def test_dispatch_claim_reconstruction_clears_stale_model_without_rewriting_history(tmp_path: Path) -> None:
    feature_dir = _make_feature_dir(tmp_path)
    wp_file = _write_wp_file(feature_dir)
    before = wp_file.read_bytes()
    _write_dispatch_op(tmp_path)
    emit_resolved_binding(
        feature_dir,
        _WP_ID,
        mission_slug=_MISSION_SLUG,
        actor="claude",
        role="implementer",
        binding=ResolvedBinding(model="historical-model", provider="historical-provider"),
        tool="claude",
        repo_root=tmp_path,
    )
    assert _resolved_slots(feature_dir)["model"] == "historical-model"
    binding = _resolve_dispatch_binding(
        model=None,
        profile=None,
        invocation_id=_INVOCATION_ID,
        repo_root=tmp_path,
        mission_id=_MISSION_ID,
        wp_id=_WP_ID,
        action="implement",
    )
    emit_resolved_binding(
        feature_dir,
        _WP_ID,
        mission_slug=_MISSION_SLUG,
        actor="claude",
        role="implementer",
        binding=binding,
        tool="claude",
        repo_root=tmp_path,
    )
    slots = _resolved_slots(feature_dir)
    assert slots["model"] == RESOLVED_MODEL_ABSENT
    assert slots["provider"] == RESOLVED_PROVIDER_ABSENT
    assert slots["agent_profile"] == "python-pedro"
    assert wp_file.read_bytes() == before
