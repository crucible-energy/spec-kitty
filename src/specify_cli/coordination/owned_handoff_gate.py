"""Canonical transition-gate dispatch for explicit owned review submission."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from specify_cli.coordination.owned import OwnedCoordinationContext, OwnedCoordinationError, owned_base
from specify_cli.migration.owned_history import _safe_file
from specify_cli.migration.owned_history_sources import _blob
from specify_cli.migration.owned_history_sources import git_bytes
from specify_cli.review.baseline import BaselineTestResult
from specify_cli.review import gate_bindings, gate_registry
from specify_cli.review.pre_review_gate import GateAuthoritiesUnavailable, GateOutcome, _scope_result_from_source
from specify_cli.review.scope_source import UNKNOWN_SOURCE_IDENTITY, ScopeSource, empty_scope_is_coverage_gap, resolve_scope_source
from specify_cli.review.verdict_aggregation import aggregate_verdicts
from specify_cli.core.vcs.git import merge_base_changed_files
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.status.models import Lane

__all__ = ["submission_gate"]


class OwnedGateBlocked(OwnedCoordinationError):
    """Expose actual blocked/unverified gate evidence without writing a status event."""

    def __init__(self, reason: str, report: dict[str, Any]) -> None:
        super().__init__("OWNED_PRE_REVIEW_GATE_BLOCKED", reason)
        self.report = report

    def to_dict(self) -> dict[str, Any]:
        """Return structured gate truth alongside the stable refusal contract."""
        return {**super().to_dict(), "pre_review_gate": self.report, "aggregate_approval": False}


def _policy(context: OwnedCoordinationContext) -> bool:
    path = _safe_file(context.root, Path(".kittify/config.yaml"))
    raw, _ = _blob(context.root, context.head, ".kittify/config.yaml")
    if path.read_bytes() != raw:
        raise OwnedCoordinationError("OWNED_GATE_POLICY_REFUSED", "Gate policy differs from committed owned authority")
    try:
        config = YAML(typ="safe").load(raw.decode("utf-8")) or {}
    except YAMLError as exc:
        raise OwnedCoordinationError("OWNED_GATE_POLICY_REFUSED", "Committed gate policy is malformed") from exc
    if not isinstance(config, dict):
        raise OwnedCoordinationError("OWNED_GATE_POLICY_REFUSED", "Gate policy must be a mapping")
    review = config.get("review", {})
    if not isinstance(review, dict):
        raise OwnedCoordinationError("OWNED_GATE_POLICY_REFUSED", "Review policy must be a mapping")
    required = review.get("fail_on_pre_review_regression", False)
    if not isinstance(required, bool):
        raise OwnedCoordinationError("OWNED_GATE_POLICY_REFUSED", "Required pre-review policy must be boolean")
    return required


def _code_root(context: OwnedCoordinationContext, pin: str, checkout: Path | None) -> Path:
    root, _, _, head, branch, _ = owned_base(context.repository_root, checkout or context.root, context.slug)
    if head != pin or ProtectionPolicy.resolve(root).is_protected(branch):
        raise OwnedCoordinationError("OWNED_GATE_CODE_CHECKOUT_REQUIRED", "Active gates need an existing registered clean checkout at the immutable code pin")
    entries = git_bytes(root, "ls-files", "-v", "-z").decode().split("\0")
    if any(entry and (entry[0].islower() or entry[0] == "S") for entry in entries):
        raise OwnedCoordinationError("OWNED_GATE_CODE_CHECKOUT_REQUIRED", "Hidden index flags cannot qualify immutable test code")
    # Test commands/scope selection must not downgrade the status authority's policy.
    policy, _ = _blob(context.root, context.head, ".kittify/config.yaml")
    code_policy, _ = _blob(root, pin, ".kittify/config.yaml")
    if policy != code_policy:
        raise OwnedCoordinationError("OWNED_GATE_POLICY_REFUSED", "Code checkout and owned authority must share committed gate policy")
    return root


def _scope_available(source: ScopeSource, changed: tuple[str, ...], report: dict[str, Any]) -> bool:
    """Use canonical scope derivation without inventing a process run or verdict."""
    report["scope_source"] = type(source).__name__
    report["test_run"] = False
    try:
        scope = _scope_result_from_source(source, changed)
    except GateAuthoritiesUnavailable as exc:
        report.update({"outcome": str(GateOutcome.NO_COVERAGE), "reason": str(exc), "scope_coverage": "unavailable"})
        return False
    report["scope"] = list(scope.test_targets)
    if scope.is_empty and empty_scope_is_coverage_gap(source):
        report.update({"outcome": str(GateOutcome.NO_COVERAGE), "reason": scope.describe_empty_reason(), "scope_coverage": "empty"})
        return False
    report["scope_coverage"] = "resolved"
    return True


def _baseline_verified(baseline: BaselineTestResult | None, source: ScopeSource, report: dict[str, Any], *, required: bool) -> None:
    """The mandatory owned door needs known capture identity before any test run.

    The advisory engine intentionally admits legacy unknown identities; this
    stricter input requirement is local to owned mandatory submission. Actual
    parse-mode equality remains the engine's comparison after a real run.
    """
    identity = baseline.source_identity if baseline is not None else UNKNOWN_SOURCE_IDENTITY
    report["baseline_source_identity"] = identity
    known = isinstance(identity, str) and identity != UNKNOWN_SOURCE_IDENTITY and identity.strip() == identity and all(identity.partition("/"))
    capture_verified = bool(known and baseline is not None and baseline.failed >= 0)
    report["baseline_identity_verified"] = bool(capture_verified and identity.partition("/")[0] == type(source).__name__)
    if required and not capture_verified:
        report.update(
            {"outcome": str(GateOutcome.UNVERIFIED_BASELINE), "reason": "Required baseline capture source identity is missing/unknown or capture is unverified"}
        )
        raise OwnedGateBlocked(report["reason"], report)
    if required and identity.partition("/")[0] != type(source).__name__:
        report.update({"outcome": str(GateOutcome.SOURCE_MISMATCH), "reason": "Committed baseline source does not match the selected canonical scope source"})
        raise OwnedGateBlocked(report["reason"], report)


def submission_gate(context: OwnedCoordinationContext, wp_id: str, pin: str, checkout: Path | None, *, run: bool) -> dict[str, Any]:
    """Resolve canonical bindings; run real code only on apply, reporting scoped truth.

    Required policy refuses missing coverage, unverified baselines and any failures.
    Optional uncovered edges remain explicit NO_COVERAGE, never fabricated green.
    No workspace or baseline is allocated, and a supplied receipt is not executed.
    """
    required = _policy(context)
    mission_type = gate_bindings.resolve_mission_type(None, feature_dir=context.directory)
    resolution = gate_bindings.resolve_gate_bindings_for_transition(context.root, mission_type, "in_progress->for_review")
    report: dict[str, Any] = {
        "coverage": str(resolution.coverage),
        "reason": resolution.reason,
        "required": required,
        "outcome": "not_run" if resolution.active else "no_coverage",
        "aggregate_approval": False,
    }
    if not resolution.active:
        if checkout is not None:
            report["code_checkout"] = str(_code_root(context, pin, checkout))
        if run and required:
            raise OwnedGateBlocked(f"Required gate has no active coverage: {resolution.reason}", report)
        return report
    root = _code_root(context, pin, checkout)
    report["code_checkout"] = str(root)
    from specify_cli.core.wps_manifest import load_wps_manifest

    manifest = load_wps_manifest(context.directory)
    wp = next((item for item in manifest.work_packages if item.id == wp_id), None) if manifest is not None else None
    if wp is None or not wp.prompt_file:
        raise OwnedCoordinationError("OWNED_HANDOFF_WP_REFUSED", "Missing authored WP prompt")
    baseline_path = context.directory.relative_to(context.root) / "tasks" / Path(wp.prompt_file).stem / "baseline-tests.json"
    baseline_file = _safe_file(root, baseline_path)
    if baseline_file.exists():
        pinned, _ = _blob(root, pin, baseline_path.as_posix())
        if baseline_file.read_bytes() != pinned:
            raise OwnedCoordinationError("OWNED_PRE_REVIEW_GATE_BLOCKED", "Baseline differs from its committed code-pin evidence")
    baseline = BaselineTestResult.load(baseline_file)
    if baseline is not None and baseline.wp_id != wp_id:
        raise OwnedCoordinationError("OWNED_PRE_REVIEW_GATE_BLOCKED", "Baseline belongs to a different work package")
    source = resolve_scope_source(root)
    changed = merge_base_changed_files(root, context.target_commit)
    if not _scope_available(source, changed, report):
        if required:
            raise OwnedGateBlocked("Required pre-review scope authorities are unavailable", report)
        return report
    _baseline_verified(baseline, source, report, required=required)
    if not run:
        return report
    ctx = gate_registry.TransitionGateContext(changed, source, baseline, root, False, Lane.IN_PROGRESS, Lane.FOR_REVIEW)
    verdicts = [gate_registry.get_gate_handler(binding.handler).run(ctx) for binding in resolution.active]
    report["test_run"] = any(v.outcome != GateOutcome.NO_COVERAGE for v in verdicts)
    decision = aggregate_verdicts(verdicts, block_enabled=required, force=False)
    report["verdicts"] = [
        {
            "outcome": str(v.outcome),
            "reason": v.reason,
            "scope": list(v.scope.test_targets),
            "new_failures": [failure.to_dict() for failure in v.new_failures],
            "pre_existing_failures": [failure.to_dict() for failure in v.pre_existing_failures],
        }
        for v in verdicts
    ]
    report["outcome"] = str(verdicts[-1].outcome)
    report["decision"] = str(decision.decision)
    # Revalidate even when a runner creates dirt: preserve it and refuse handoff.
    _code_root(context, pin, checkout)
    not_clear = any(v.outcome != GateOutcome.NO_NEW_FAILURES or v.pre_existing_failures for v in verdicts)
    if decision.should_exit or (required and not_clear):
        raise OwnedGateBlocked("Pre-review gate did not establish required clear proof", report)
    return report
