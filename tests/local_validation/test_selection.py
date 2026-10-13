"""Discriminating local-authority controls against the existing public reader."""

import json
import subprocess
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


@pytest.mark.parametrize("version", [None, True, 1.0, 999])
def test_local_version_requires_supported_integer(tmp_path: Path, version: object) -> None:
    specification = local_specification()
    specification["schema_version"] = version
    with pytest.raises(ValueError, match="version"):
        load_router(write_local(tmp_path, specification))


@pytest.mark.parametrize(
    "routing",
    [
        None,
        {},
        {"filters": [], "job_gates": {}},
        {"filters": {"runtime": "src/runtime/**"}, "job_gates": {"lint": []}},
        {"filters": {"runtime": [3]}, "job_gates": {"lint": []}},
        {"filters": {"runtime": ["src/runtime/**"]}, "job_gates": []},
        {"filters": {"runtime": ["src/runtime/**"]}, "job_gates": {"lint": "runtime"}},
        {"filters": {"runtime": ["src/runtime/**"]}, "job_gates": {"lint": ["absent"]}},
        {"filters": {"any_src": ["src/**"]}, "job_gates": {"lint": ["any_src"]}},
    ],
)
def test_invalid_local_routing_refuses_actionably(tmp_path: Path, routing: object) -> None:
    specification = local_specification()
    specification["routing"] = routing
    with pytest.raises(ValueError, match="routing"):
        load_router(write_local(tmp_path, specification))


def test_duplicate_local_fields_refuse(tmp_path: Path) -> None:
    path = tmp_path / "gates.json"
    path.write_text('{"schema_version": 1, "schema_version": 999}')
    with pytest.raises(ValueError, match="Duplicate"):
        load_router(path)


def test_extraction_preserves_commands_and_source_identity(tmp_path: Path) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    path = directory / "quality.yml"
    path.write_text(
        "on: [push]\njobs:\n  lint:\n    runs-on: ubuntu-24.04\n    timeout-minutes: 10\n    steps:\n"
        "      - run: |\n          python -m ruff check .\n          python -m ruff format --check .\n"
    )
    result = extract_workflows(tmp_path)
    assert result["validation_performed"] is False
    workflow = result["workflows"][0]
    assert workflow["path"] == ".github/workflows/quality.yml"
    assert workflow["trigger"] == ["push"]
    assert len(workflow["sha256"]) == 64
    job = workflow["jobs"]["lint"]
    assert job["wall_ms"] == 600000
    assert job["steps"][0]["argv"] == [["python", "-m", "ruff", "check", "."], ["python", "-m", "ruff", "format", "--check", "."]]


def test_extraction_retains_untranslated_conditions_and_actions(tmp_path: Path) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "release.yml").write_text(
        "on: [push]\njobs:\n  publish:\n    if: github.ref == 'refs/heads/main'\n    needs: [build]\n"
        "    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n"
        "      - uses: pypa/gh-action-pypi-publish@v1\n      - run: echo ${{ secrets.TOKEN }}\n"
        "  build:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - run: python -m build\n"
    )
    result = extract_workflows(tmp_path)
    assert result["runnable"] is False
    job = result["workflows"][0]["jobs"]["publish"]
    assert job["needs"] == ["build"]
    assert job["condition"] == "github.ref == 'refs/heads/main'"
    assert job["steps"][0]["uses"] == "pypa/gh-action-pypi-publish@v1"
    assert job["steps"][1]["argv"] is None
    assert {entry["reason"] for entry in result["blockers"]} >= {"job_condition", "action", "shell_semantics"}
    assert "secrets.TOKEN" not in json.dumps(result)


@pytest.mark.parametrize(
    "body",
    [
        "jobs:\n  a: {}\n  a: {}\n",
        "on: [push]\njobs: []\n",
        "on: [push]\njobs:\n  a:\n    timeout-minutes: true\n    steps: []\n",
        "on: [push]\njobs:\n  a:\n    needs: [missing]\n    steps: []\n",
    ],
)
def test_extraction_refuses_ambiguous_or_invalid_workflows(tmp_path: Path, body: str) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "invalid.yml").write_text(body)
    with pytest.raises(ValueError, match="workflow"):
        extract_workflows(tmp_path)


def test_extraction_refuses_symlinked_workflow(tmp_path: Path) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    outside = tmp_path / "outside.yml"
    outside.write_text("jobs: {}\n")
    (directory / "linked.yml").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        extract_workflows(tmp_path)


@pytest.mark.parametrize(
    "command",
    [
        "if true",
        "echo hi # comment",
        "echo ~/private",
        "echo [ab]",
        "echo hi | cat",
        "echo $(id)",
        "VALUE=1 python",
        "echo 'unterminated",
        "cd docs\npython -m build",
        "export MODE=release\npython -m build",
        "source settings.env\npython -m build",
        "exec python first.py\npython second.py",
        ". settings.env\npython -m build",
        "command python -m build",
        "read answer",
        "exit 0",
        "time python first.py",
        "coproc python first.py",
    ],
)
def test_extraction_refuses_shell_translation(tmp_path: Path, command: str) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "shell.yml").write_text(yaml.safe_dump({"on": ["push"], "jobs": {"check": {"steps": [{"run": command}]}}}))
    result = extract_workflows(tmp_path)
    assert result["workflows"][0]["jobs"]["check"]["steps"][0]["argv"] is None
    assert any(item["reason"] == "shell_semantics" for item in result["blockers"])


@pytest.mark.parametrize(
    "body",
    [
        "",
        "on: [push]\njobs: {}\n",
        "on: [push]\njobs:\n  a:\n    needs: b\n  b:\n    needs: a\n",
        "on: [push]\njobs:\n  a:\n    steps: not-a-list\n",
        "on: [push]\njobs:\n  a:\n    steps: [!custom invalid]\n",
        "on: [push]\njobs:\n  a: &job {}\n  b: *job\n",
        "on: [push]\njobs:\n  a:\n    env: " + "[" * 70 + "0" + "]" * 70 + "\n",
        "#" * 1048577,
    ],
    ids=["empty", "no_jobs", "cycle", "bad_steps", "unknown_tag", "alias", "deep_input", "large_input"],
)
def test_extraction_refuses_unbounded_or_unsupported_input(tmp_path: Path, body: str) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "invalid.yml").write_text(body)
    with pytest.raises(ValueError, match="workflow"):
        extract_workflows(tmp_path)


def test_extraction_detects_source_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.validation import extract_gates

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    path = directory / "changing.yml"
    path.write_text("on: [push]\njobs:\n  a:\n    steps: []\n")
    read = extract_gates._read

    def mutate_after_read(source: Path) -> bytes:
        raw = read(source)
        source.write_bytes(raw + b"# concurrent modification\n")
        return raw

    monkeypatch.setattr(extract_gates, "_read", mutate_after_read)
    with pytest.raises(ValueError, match="Changed workflow"):
        extract_gates.extract_workflows(tmp_path)


def test_extraction_cli_never_qualifies_inventory(tmp_path: Path) -> None:
    import sys

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    path = directory / "quality.yml"
    path.write_text("on: [push]\njobs:\n  a:\n    steps:\n      - run: python -m build\n")
    script = Path(__file__).resolve().parents[2] / "scripts" / "validation" / "extract_gates.py"
    result = subprocess.run([sys.executable, str(script), "--root", str(tmp_path), "--require-runnable"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["runnable"] is False and report["validation_performed"] is False
    path.write_text("jobs: []\n")
    invalid = subprocess.run([sys.executable, str(script), "--root", str(tmp_path)], capture_output=True, text=True, timeout=10)
    assert invalid.returncode == 2
    assert not invalid.stdout
    assert "extraction refused" in invalid.stderr


def test_extraction_entry_propagates_refusals(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import sys

    from scripts.validation.extract_gates import main

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    path = directory / "quality.yml"
    path.write_text("on: [push]\njobs:\n  a:\n    steps:\n      - run: python -m build\n")
    monkeypatch.setattr(sys, "argv", ["extract_gates", "--root", str(tmp_path)])
    assert main() == 0
    inspected = capsys.readouterr()
    assert not inspected.err
    assert json.loads(inspected.out)["validation_performed"] is False
    monkeypatch.setattr(sys, "argv", ["extract_gates", "--root", str(tmp_path), "--require-runnable"])
    assert main() == 2
    refused = capsys.readouterr()
    assert not refused.err
    assert json.loads(refused.out)["runnable"] is False
    path.write_text("jobs: []\n")
    assert main() == 2
    invalid = capsys.readouterr()
    assert not invalid.out
    assert "extraction refused" in invalid.err


def test_extraction_keeps_explicit_external_time_argv(tmp_path: Path) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "external.yml").write_text("jobs:\n  check:\n    steps:\n      - run: /usr/bin/time -p python -m build\n")
    report = extract_workflows(tmp_path)
    assert report["workflows"][0]["jobs"]["check"]["steps"][0]["argv"] == [["/usr/bin/time", "-p", "python", "-m", "build"]]
    assert report["runnable"] is False


@pytest.mark.parametrize(
    "separator",
    ["\r", "\v", "\f", "\x85", "\u2028", "\u2029", "\0", "\x7f", "\u00a0", "\u200b"],
    ids=["cr", "vt", "ff", "nel", "line_separator", "paragraph_separator", "nul", "del", "nbsp", "zero_width"],
)
def test_extraction_refuses_non_lf_command_boundaries(tmp_path: Path, separator: str) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    command = f"python one.py{separator}python two.py"
    (directory / "boundary.yml").write_text(yaml.safe_dump({"jobs": {"check": {"steps": [{"run": command}]}}}))
    report = extract_workflows(tmp_path)
    assert report["workflows"][0]["jobs"]["check"]["steps"][0]["argv"] is None
    assert any(item["reason"] == "shell_semantics" for item in report["blockers"])


def test_extraction_preserves_lf_ascii_blanks_and_literal_arguments(tmp_path: Path) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    command = " \tpython\t-m tool 'café' ''\n \t\npython -m build\n"
    (directory / "literal.yml").write_text(yaml.safe_dump({"jobs": {"check": {"steps": [{"run": command}]}}}))
    report = extract_workflows(tmp_path)
    assert report["workflows"][0]["jobs"]["check"]["steps"][0]["argv"] == [["python", "-m", "tool", "café", ""], ["python", "-m", "build"]]
