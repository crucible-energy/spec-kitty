"""Discriminating local-authority controls against the existing public reader."""

import json
from pathlib import Path

import pytest
import yaml

from scripts.ci.gate_selection import load_router, select_gates


def local_specification() -> dict[str, object]:
    def check(argv: list[str]) -> dict[str, object]:
        return {
            "argv": argv,
            "modes": ["commit", "full"],
            "platforms": ["macos", "linux", "windows"],
            "dependencies": [],
            "environment": {},
            "budgets": {
                "wall_ms": 600000,
                "cleanup_ms": 5000,
                "stdout_bytes": 16777216,
                "stderr_bytes": 16777216,
                "sampled_processes": 16,
                "sampled_resident_bytes": 2147483648,
            },
        }

    return {
        "schema_version": 1,
        "routing": {
            "filters": {"runtime": ["src/runtime/**"], "docs": ["docs/**"], "any_src": ["src/**"]},
            "job_gates": {"lint": [], "test-runtime": ["runtime"], "test-docs": ["docs"]},
        },
        "modules": [{"module": "runtime", "roots": ["src/runtime/**"], "test_dirs": ["tests/runtime"]}],
        "checks": {
            "lint": check(["python", "-m", "ruff", "check", "."]),
            "test-runtime": check(["python", "-m", "pytest", "tests/runtime", "-q"]),
            "test-docs": check(["python", "-m", "pytest", "tests/docs", "-q"]),
        },
    }


def write_local(root: Path, specification: dict[str, object]) -> Path:
    path = root / "gates.json"
    path.write_text(json.dumps(specification))
    return path


def test_existing_workflow_positive_control(tmp_path: Path) -> None:
    workflow = {
        "jobs": {
            "changes": {"steps": [{"uses": "dorny/paths-filter@v3", "with": {"filters": yaml.safe_dump({"runtime": ["src/runtime/**"], "any_src": ["src/**"]})}}]},
            "lint": {"steps": []},
            "test-runtime": {"if": "needs.changes.outputs.runtime == 'true'", "steps": []},
        }
    }
    path = tmp_path / "router.yml"
    path.write_text(yaml.safe_dump(workflow))
    selection = select_gates(["src/runtime/worker.py"], router=load_router(path))
    assert selection.selected_jobs == frozenset({"lint", "test-runtime"})
    assert not selection.unmatched_src


def test_local_authority_retains_always_on_and_scoped_selection(tmp_path: Path) -> None:
    router = load_router(write_local(tmp_path, local_specification()))
    assert select_gates(["src/runtime/worker.py"], router=router).selected_jobs == frozenset({"lint", "test-runtime"})
    assert select_gates(["docs/operator.md"], router=router).selected_jobs == frozenset({"lint", "test-docs"})


def test_local_authority_unknown_source_is_conservative(tmp_path: Path) -> None:
    router = load_router(write_local(tmp_path, local_specification()))
    selection = select_gates(["src/unknown/new.py"], router=router)
    assert selection.unmatched_src
    assert selection.selected_jobs == frozenset({"lint", "test-runtime", "test-docs"})


def test_local_authority_unknown_version_refuses_usefully(tmp_path: Path) -> None:
    specification = local_specification()
    specification["schema_version"] = 999
    with pytest.raises(ValueError, match="version"):
        load_router(write_local(tmp_path, specification))
