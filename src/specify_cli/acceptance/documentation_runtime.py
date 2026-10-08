"""Read-only completion evidence for documentation missions without WPs."""

from __future__ import annotations

from pathlib import Path

import yaml

from runtime.next import runtime_bridge_engine as engine
from runtime.next.runtime_bridge_io import _FeatureRunEntry, _feature_runs_path, load_feature_runs
from runtime.next._internal_runtime.schema import MissionRunSnapshot, MissionRuntimeError
from specify_cli.core.paths import load_meta_fail_closed


def completed_documentation_runtime(repo_root: Path, mission_dir: Path) -> bool:
    """Verify a matching persisted documentation run is terminal without advancing it.

    Call only when the canonical task surface contains no WPs. Missing or invalid
    evidence refuses the empty-WP exception; normal acceptance gates still apply.
    """
    meta = load_meta_fail_closed(mission_dir) or {}
    if meta.get("mission_type") != "documentation" or meta.get("topology") != "single_branch":
        return False
    try:
        index = load_feature_runs(_feature_runs_path(repo_root))
        entry = index.get(mission_dir.name) if isinstance(index, dict) else None
        if not isinstance(entry, dict) or not _matches_index_entry(entry, mission_dir.name, meta.get("mission_id")):
            return False
        run_dir = Path(entry["run_dir"]).resolve()
        if not run_dir.is_relative_to(repo_root.resolve()):
            return False
        snapshot = engine._read_snapshot(run_dir)
        template = engine._load_frozen_template(run_dir)
        if not _matches_documentation_run(snapshot, entry["run_id"], mission_dir.name, meta.get("mission_id")):
            return False
        if template.mission.key != "documentation" or snapshot.issued_step_id is not None:
            return False
        decision = engine.plan_next(
            snapshot,
            template,
            snapshot.policy_snapshot,
            live_template_path=run_dir / "mission_template_frozen.yaml",
        )
        return bool(decision.kind == "terminal")
    except (OSError, ValueError, KeyError, TypeError, MissionRuntimeError, yaml.YAMLError):
        # Invalid runtime evidence must preserve the existing acceptance refusal.
        return False


def _matches_index_entry(entry: _FeatureRunEntry, mission_slug: str, mission_id: object) -> bool:
    """Reject foreign explicit identity fields while allowing legacy absent slots."""
    return (
        (entry.get("mission_type") or entry.get("mission_key")) == "documentation"
        and entry.get("mission_type") in (None, "documentation")
        and entry.get("mission_key") in (None, "documentation")
        and entry.get("mission_slug") in (None, mission_slug)
        and entry.get("mission_id") in (None, mission_id)
    )


def _matches_documentation_run(
    snapshot: MissionRunSnapshot,
    run_id: str,
    mission_slug: str,
    mission_id: object,
) -> bool:
    """Check legacy input identity and any newer explicit identity slots."""
    return (
        snapshot.run_id == run_id
        and snapshot.mission_key == "documentation"
        and snapshot.inputs.get("mission_slug") == mission_slug
        and snapshot.mission_slug in (None, mission_slug)
        and snapshot.mission_id in (None, mission_id)
    )
