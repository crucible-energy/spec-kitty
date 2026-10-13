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


def test_unknown_source_stays_conservative_when_a_known_source_is_present(tmp_path: Path) -> None:
    router = load_router(write_local(tmp_path, local_specification()))
    selection = select_gates(["src/runtime/worker.py", "src/unknown/new.py"], router=router)
    assert selection.unmatched_src
    assert selection.selected_jobs == frozenset({"lint", "test-runtime", "test-docs"})


@pytest.fixture(scope="module")
def native_selector(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repository = Path(__file__).resolve().parents[2]
    executable = tmp_path_factory.mktemp("native-selector") / "selection"
    subprocess.run(
        ["zig", "build-exe", str(repository / "tools/zig/validation_selection.zig"), "-O", "ReleaseSafe", f"-femit-bin={executable}"],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return executable


@pytest.mark.parametrize(
    ("paths", "mode"),
    [
        (["src/runtime/worker.py"], "pr"),
        (["docs/operator.md"], "pr"),
        (["src/unknown/new.py"], "pr"),
        (["src/runtime/worker.py", "src/unknown/new.py"], "pr"),
        ([], "pr"),
        (["docs/operator.md"], "full"),
    ],
)
def test_native_selection_matches_the_qualified_reader(tmp_path: Path, native_selector: Path, paths: list[str], mode: str) -> None:
    specification = write_local(tmp_path, local_specification())
    expected = select_gates(paths, router=load_router(specification), mode=mode)
    result = subprocess.run([str(native_selector), str(specification), mode, *paths], check=True, capture_output=True, text=True, timeout=20)
    actual = json.loads(result.stdout)
    assert actual["matched_groups"] == sorted(expected.matched_groups)
    assert actual["unmatched_src"] == expected.unmatched_src
    assert actual["selected_jobs"] == sorted(expected.selected_jobs)
    assert actual["selected_code_shards"] == sorted(expected.selected_code_shards)
    assert actual["selection_only"] is True
    assert actual["validation_performed"] is False


@pytest.mark.parametrize("version", [None, True, 1.0, 999])
def test_native_invalid_version_refuses(tmp_path: Path, native_selector: Path, version: object) -> None:
    specification = local_specification()
    specification["schema_version"] = version
    path = write_local(tmp_path, specification)
    result = subprocess.run([str(native_selector), str(path), "pr", "src/runtime/a.py"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert result.stdout == ""
    assert "selection refused" in result.stderr


@pytest.mark.parametrize("path", ["", "/absolute.py", "src/../escape.py"])
def test_native_invalid_path_refuses(tmp_path: Path, native_selector: Path, path: str) -> None:
    specification = write_local(tmp_path, local_specification())
    result = subprocess.run([str(native_selector), str(specification), "pr", path], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert result.stdout == ""
    assert "InvalidPath" in result.stderr


def test_native_unknown_mode_refuses(tmp_path: Path, native_selector: Path) -> None:
    specification = write_local(tmp_path, local_specification())
    result = subprocess.run([str(native_selector), str(specification), "unqualified"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert "UnsupportedMode" in result.stderr


_NATIVE_API_CONTROLS = r"""
const std = @import("std");
const selection = @import("selection");
fn allocateSelection(allocator: std.mem.Allocator, document: std.json.Value) !void {
    const selected = try selection.select(allocator, document, &.{ "src/runtime/a.py", "docs/operator.md" }, "pr");
    defer selected.deinit(allocator);
    try std.testing.expectEqual(@as(usize, 3), selected.selected_jobs.len);
}
test "selection allocation and input bounds" {
    const bytes =
        \\__FIXTURE_JSON__
    ;
    const parsed = try std.json.parseFromSlice(std.json.Value, std.testing.allocator, bytes, .{});
    defer parsed.deinit();
    try std.testing.checkAllAllocationFailures(std.testing.allocator, allocateSelection, .{parsed.value});
    var no_resize = std.testing.FailingAllocator.init(std.testing.allocator, .{ .resize_fail_index = 0 });
    try std.testing.checkAllAllocationFailures(no_resize.allocator(), allocateSelection, .{parsed.value});
    try std.testing.expectEqual(no_resize.allocated_bytes, no_resize.freed_bytes);
    const paths = try std.testing.allocator.alloc([]const u8, 32769);
    defer std.testing.allocator.free(paths);
    @memset(paths, "docs/operator.md");
    try std.testing.expectError(error.InputLimit, selection.select(std.testing.allocator, parsed.value, paths, "pr"));
}
"""


def test_native_allocation_rollback_and_api_input_bound(tmp_path: Path) -> None:
    """Exercise real native rollback at every allocation failure and the public API bound."""
    repository = Path(__file__).resolve().parents[2]
    harness = tmp_path / "allocation-controls.zig"
    harness.write_text(_NATIVE_API_CONTROLS.replace("__FIXTURE_JSON__", json.dumps(local_specification())))
    executable = tmp_path / "allocation-controls"
    subprocess.run(
        [
            "zig",
            "test",
            "--test-no-exec",
            "--test-filter",
            "selection allocation and input bounds",
            "-O",
            "ReleaseSafe",
            "--dep",
            "selection",
            f"-Mroot={harness}",
            "-O",
            "ReleaseSafe",
            f"-Mselection={repository / 'tools/zig/validation_selection.zig'}",
            f"-femit-bin={executable}",
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    result = subprocess.run([str(executable)], check=True, capture_output=True, text=True, timeout=20)
    assert "test.selection allocation and input bounds...OK" in result.stderr
    assert "All 1 tests passed." in result.stderr


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
