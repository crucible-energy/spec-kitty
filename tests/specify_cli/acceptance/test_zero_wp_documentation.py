"""Zero-WP documentation acceptance must use completed canonical runtime evidence."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.next._internal_runtime import MissionPolicySnapshot, NullEmitter, start_mission_run
from runtime.next._internal_runtime.engine import _freeze_template
from runtime.next import runtime_bridge_engine as engine
from specify_cli.acceptance import AcceptanceError, AcceptanceSummary, collect_feature_summary
from tests.specify_cli.test_canonical_acceptance import _setup_feature, _write_wp_file

pytestmark = [pytest.mark.unit, pytest.mark.fast, pytest.mark.corpus]
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
        return collect_feature_summary(root.resolve(), SLUG, strict_metadata=False, mutate_matrix=False)


def test_completed_documentation_accepts_empty_status_log(completed_documentation: tuple[Path, Path]) -> None:
    mission_dir, _ = completed_documentation
    summary = _summary(mission_dir.parents[1])
    assert summary.activity_issues == []
    assert summary.work_packages == []
    assert summary.ok


@pytest.mark.parametrize(
    "defect",
    [
        "missing_index",
        "missing_state",
        "incomplete",
        "issued",
        "blocked",
        "pending",
        "wrong_slug",
        "wrong_run",
        "wrong_type",
        "missing_template",
        "corrupt",
        "software",
        "missing_log",
        "wrong_topology",
        "foreign_run_dir",
        "corrupt_index",
        "wrong_explicit_slug",
        "wrong_mission_id",
        "template_drift",
        "index_wrong_type",
        "index_wrong_key",
        "index_wrong_slug",
        "index_wrong_identity",
        "wrong_template_type",
        "non_object_index",
    ],
)
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
    elif defect == "wrong_topology":
        path = mission_dir / "meta.json"
        meta = json.loads(path.read_text())
        meta["topology"] = "lanes"
        path.write_text(json.dumps(meta))
    elif defect == "foreign_run_dir":
        path = root / ".kittify/runtime/feature-runs.json"
        index = json.loads(path.read_text())
        foreign = root.parent / f"{root.name}-foreign-runtime"
        run_dir.rename(foreign)
        index[SLUG]["run_dir"] = str(foreign)
        path.write_text(json.dumps(index))
    elif defect == "corrupt_index":
        (root / ".kittify/runtime/feature-runs.json").write_text("{bad")
    elif defect == "template_drift":
        path = run_dir / "mission_template_frozen.yaml"
        path.write_text(path.read_text() + "\n# changed\n")
    elif defect == "wrong_template_type":
        path = run_dir / "mission_template_frozen.yaml"
        path.write_text(path.read_text().replace("key: documentation", "key: research"))
        state["template_hash"] = _freeze_template(run_dir, engine._load_frozen_template(run_dir), str(path))
        state_path.write_text(json.dumps(state))
    elif defect == "non_object_index":
        (root / ".kittify/runtime/feature-runs.json").write_text("[]")
    elif defect.startswith("index_wrong_"):
        path = root / ".kittify/runtime/feature-runs.json"
        index = json.loads(path.read_text())
        fields = {"index_wrong_type": "mission_type", "index_wrong_key": "mission_key", "index_wrong_slug": "mission_slug", "index_wrong_identity": "mission_id"}
        index[SLUG][fields[defect]] = "foreign"
        path.write_text(json.dumps(index))
    else:
        changes = {
            "incomplete": {"completed_steps": ["discover"]},
            "issued": {"issued_step_id": "accept"},
            "blocked": {"blocked_reason": "validation failed"},
            "pending": {"pending_decisions": {"publish": {}}},
            "wrong_slug": {"inputs": {"mission_slug": "another-mission"}},
            "wrong_run": {"run_id": "another-run"},
            "wrong_type": {"mission_key": "software-dev"},
            "wrong_explicit_slug": {"mission_slug": "another-mission"},
            "wrong_mission_id": {"mission_id": "another-id"},
        }
        state.update(changes[defect])
        state_path.write_text(json.dumps(state))
    summary = _summary(root)
    assert summary.activity_issues
    assert not summary.ok


def test_corrupt_status_log_still_fails(completed_documentation: tuple[Path, Path]) -> None:
    mission_dir, _ = completed_documentation
    (mission_dir / "status.events.jsonl").write_text("{bad\n")
    with pytest.raises(AcceptanceError, match="corrupted"):
        _summary(mission_dir.parents[1])


def test_completed_runtime_cannot_bypass_existing_wp_checks(completed_documentation: tuple[Path, Path]) -> None:
    mission_dir, _ = completed_documentation
    _write_wp_file(mission_dir / "tasks", "WP01")
    summary = _summary(mission_dir.parents[1])
    assert summary.activity_issues
    assert not summary.all_done


def test_runtime_proof_does_not_write_files(completed_documentation: tuple[Path, Path]) -> None:
    mission_dir, run_dir = completed_documentation
    root = mission_dir.parents[1]
    files = [root / ".kittify/runtime/feature-runs.json", run_dir / "state.json", mission_dir / "status.events.jsonl"]
    before = [path.read_bytes() for path in files]
    _summary(root)
    assert [path.read_bytes() for path in files] == before
