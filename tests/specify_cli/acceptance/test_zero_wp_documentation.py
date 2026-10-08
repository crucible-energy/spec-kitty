"""Zero-WP documentation acceptance must use completed canonical runtime evidence."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.next._internal_runtime import MissionPolicySnapshot, NullEmitter, start_mission_run
from runtime.next import runtime_bridge_engine as engine
from specify_cli.acceptance import AcceptanceError, AcceptanceSummary, collect_feature_summary
from tests.specify_cli.test_canonical_acceptance import _setup_feature

pytestmark = [pytest.mark.unit, pytest.mark.corpus]
SLUG = "099-test-feature"


@pytest.fixture
def completed_documentation(tmp_path: Path) -> tuple[Path, Path]:
    mission_dir = _setup_feature(tmp_path, wp_ids=[])
    (mission_dir / "tasks").mkdir(exist_ok=True)
    meta_path = mission_dir / "meta.json"
    meta = json.loads(meta_path.read_text())
    meta["mission_type"] = "documentation"
    meta["topology"] = "single_branch"
    meta_path.write_text(json.dumps(meta))
    (mission_dir / "status.events.jsonl").write_text("")
    template_path = Path(__file__).parents[3] / "packs/built-in/missions/documentation/mission-runtime.yaml"
    run = start_mission_run(
        str(template_path),
        inputs={"mission_slug": SLUG},
        policy_snapshot=MissionPolicySnapshot(),
        run_store=tmp_path / ".kittify/runtime/runs",
        emitter=NullEmitter(),
    )
    run_dir = Path(run.run_dir)
    state_path = run_dir / "state.json"
    state = json.loads(state_path.read_text())
    template = engine._load_frozen_template(run_dir)
    state["completed_steps"] = [step.id for step in template.steps]
    state_path.write_text(json.dumps(state))
    index_path = tmp_path / ".kittify/runtime/feature-runs.json"
    index_path.write_text(json.dumps({SLUG: {"run_id": run.run_id, "run_dir": str(run_dir), "mission_type": "documentation"}}))
    return mission_dir, run_dir


def _summary(root: Path) -> AcceptanceSummary:
    with patch("specify_cli.acceptance.run_git") as git, patch("specify_cli.acceptance.git_status_lines", return_value=[]):
        git.return_value.stdout = "main\n"
        return collect_feature_summary(root, SLUG, strict_metadata=False, mutate_matrix=False)


def test_completed_documentation_accepts_empty_status_log(completed_documentation: tuple[Path, Path]) -> None:
    mission_dir, _ = completed_documentation
    summary = _summary(mission_dir.parents[1])
    assert summary.activity_issues == []
    assert summary.work_packages == []


@pytest.mark.parametrize("defect", ["missing_index", "missing_state", "incomplete", "issued", "blocked", "pending", "wrong_slug", "wrong_run", "wrong_type", "missing_template", "corrupt", "software", "missing_log"])
def test_documentation_requires_complete_matching_evidence(completed_documentation: tuple[Path, Path], defect: str) -> None:
    mission_dir, run_dir = completed_documentation
    root = mission_dir.parents[1]
    state_path = run_dir / "state.json"
    state = json.loads(state_path.read_text())
    if defect == "missing_index":
        (root / ".kittify/runtime/feature-runs.json").unlink()
    elif defect == "missing_state":
        state_path.unlink()
    elif defect == "missing_template":
        (run_dir / "mission_template_frozen.yaml").unlink()
    elif defect == "corrupt":
        state_path.write_text("{bad")
    elif defect == "software":
        path = mission_dir / "meta.json"
        meta = json.loads(path.read_text())
        meta["mission_type"] = "software-dev"
        path.write_text(json.dumps(meta))
    elif defect == "missing_log":
        (mission_dir / "status.events.jsonl").unlink()
    else:
        changes = {
            "incomplete": {"completed_steps": ["discover"]},
            "issued": {"issued_step_id": "accept"},
            "blocked": {"blocked_reason": "validation failed"},
            "pending": {"pending_decisions": {"publish": {}}},
            "wrong_slug": {"inputs": {"mission_slug": "another-mission"}},
            "wrong_run": {"run_id": "another-run"},
            "wrong_type": {"mission_key": "software-dev"},
        }
        state.update(changes[defect])
        state_path.write_text(json.dumps(state))
    summary = _summary(root)
    assert summary.activity_issues


def test_corrupt_status_log_still_fails(completed_documentation: tuple[Path, Path]) -> None:
    mission_dir, _ = completed_documentation
    (mission_dir / "status.events.jsonl").write_text("{bad\n")
    with pytest.raises(AcceptanceError, match="corrupted"):
        _summary(mission_dir.parents[1])
