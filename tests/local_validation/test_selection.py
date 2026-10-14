"""Discriminating local-authority controls against the existing public reader."""

import json
import hashlib
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci.gate_selection import load_router, select_gates


def fixture_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()  # noqa: TID251 — raw staged-input checksum, not charter hashing


def result_input() -> dict[str, Any]:
    binding = {"candidate_tree": "a" * 40, "specification_sha256": "b" * 64, "invocation_id": "fixture-1"}
    return {
        "schema_version": 1,
        "kind": "results",
        "binding": binding,
        "selected": ["lint"],
        "unselected": ["test-docs"],
        "results": [
            {"id": "lint", "conclusion": "success", "binding": binding.copy()},
            {"id": "test-docs", "conclusion": "skipped", "binding": binding.copy()},
        ],
    }


def test_local_result_adapter_preserves_complete_dependency_outcomes() -> None:
    from scripts.validation.check_inputs import evaluate_results

    assert evaluate_results(result_input()) == {"blocks": False, "blocking": {}, "validation_performed": False}
    request = result_input()
    request["results"][0]["conclusion"] = "timed_out"
    assert evaluate_results(request)["blocking"] == {"lint": "timed_out"}


@pytest.mark.parametrize("fault", ["empty", "missing", "duplicate", "foreign", "skip-selected", "binding", "unknown-field"])
def test_local_result_adapter_refuses_incomplete_or_unbound_work(fault: str) -> None:
    from scripts.validation.check_inputs import evaluate_results

    request = result_input()
    if fault == "empty":
        request["selected"] = []
        request["results"] = []
    elif fault == "missing":
        request["results"].pop()
    elif fault == "duplicate":
        request["results"].append(request["results"][0].copy())
    elif fault == "foreign":
        request["results"][0]["id"] = "unknown"
    elif fault == "skip-selected":
        request["results"][0]["conclusion"] = "skipped"
    elif fault == "binding":
        request["results"][0]["binding"]["candidate_tree"] = "c" * 40
    else:
        request["unexpected"] = True
    with pytest.raises(ValueError, match="input"):
        evaluate_results(request)


def prose_input() -> tuple[dict[str, Any], bytes]:
    authority = json.dumps(local_specification()).encode()
    base = '"""Before."""\nvalue = 1\n'
    head = '"""After."""\nvalue = 1\n'
    path = "src/runtime/odd\nname.py"
    return {
        "schema_version": 1,
        "kind": "prose",
        "base_tree": "a" * 40,
        "candidate_tree": "b" * 40,
        "specification_sha256": fixture_digest(authority),
        "paths": [path],
        "blobs": [{"path": path, "base": base, "head": head, "base_sha256": fixture_digest(base.encode()), "head_sha256": fixture_digest(head.encode())}],
    }, authority


def test_local_prose_adapter_preserves_target_free_staged_base_semantics() -> None:
    from scripts.validation.check_inputs import evaluate_prose

    request, authority = prose_input()
    assert evaluate_prose(request, authority) == {"prose_only": True, "validation_performed": False}
    request["blobs"][0]["head"] = '"""After."""\nvalue = 2\n'
    request["blobs"][0]["head_sha256"] = fixture_digest(request["blobs"][0]["head"].encode())
    assert evaluate_prose(request, authority)["prose_only"] is False


@pytest.mark.parametrize("fault", ["missing-blob", "duplicate-path", "blob-drift", "authority-drift", "missing-base", "escape"])
def test_local_prose_adapter_refuses_missing_changed_or_unsafe_inputs(fault: str) -> None:
    from scripts.validation.check_inputs import evaluate_prose

    request, authority = prose_input()
    if fault == "missing-blob":
        request["blobs"] = []
    elif fault == "duplicate-path":
        request["paths"].append(request["paths"][0])
    elif fault == "blob-drift":
        request["blobs"][0]["head"] += "# drift\n"
    elif fault == "authority-drift":
        authority += b" "
    elif fault == "missing-base":
        request["base_tree"] = None
    else:
        request["paths"][0] = "../escape.py"
    with pytest.raises(ValueError, match="input"):
        evaluate_prose(request, authority)


@pytest.mark.parametrize("kind", ["prose", "results"])
def test_bound_classifier_cli_preserves_success_and_refusal_metadata(tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str) -> None:
    from scripts.validation.check_inputs import main

    source = tmp_path / "request.json"
    args = [kind, str(source)]
    if kind == "prose":
        request, raw = prose_input()
        authority = tmp_path / "authority.json"
        authority.write_bytes(raw)
        args.extend(["--authority", str(authority)])
    else:
        request = result_input()
    source.write_text(json.dumps(request))
    assert main(args) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["validation_performed"] is False
    source.write_text('{"schema_version":1,"schema_version":1}')
    assert main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Local input refused\n"


def test_result_cli_preserves_blocking_exit_and_rejects_foreign_authority(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.validation.check_inputs import main

    path = tmp_path / "results.json"
    request = result_input()
    request["results"][0]["conclusion"] = "failure"
    path.write_text(json.dumps(request))
    assert main(["results", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["blocking"] == {"lint": "failure"}
    assert main(["results", str(path), "--authority", str(path)]) == 2
    assert capsys.readouterr().out == ""
    assert main(["prose", str(path)]) == 2


@pytest.mark.parametrize("form", ["symlink", "directory", "fifo", "oversize", "invalid-json", "missing"])
def test_classifier_file_boundary_refuses_without_body_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], form: str
) -> None:
    from scripts.validation import check_inputs
    import os

    path = tmp_path / "input.json"
    if form == "symlink":
        target = tmp_path / "target.json"
        target.write_text(json.dumps(result_input()))
        path.symlink_to(target)
    elif form == "directory":
        path.mkdir()
    elif form == "fifo":
        os.mkfifo(path)
    elif form == "oversize":
        monkeypatch.setattr(check_inputs, "MAX_BYTES", 1)
        path.write_bytes(b"{}")
    elif form == "invalid-json":
        path.write_bytes(b"private-invalid-body")
    assert check_inputs.main(["results", str(path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Local input refused\n"


@pytest.mark.parametrize("fault", ["wrong-version", "wrong-kind", "empty-name", "bad-hash", "zero-tree", "overlap", "unselected-ran", "many-rows", "nul-name"])
def test_results_closed_shape_and_roster_limits_refuse(fault: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.validation import check_inputs

    request = result_input()
    if fault == "wrong-version":
        request["schema_version"] = True
    elif fault == "wrong-kind":
        request["kind"] = "prose"
    elif fault == "empty-name":
        request["selected"] = [""]
    elif fault == "bad-hash":
        request["binding"]["specification_sha256"] = "g" * 64
    elif fault == "zero-tree":
        request["binding"]["candidate_tree"] = "0" * 40
    elif fault == "overlap":
        request["unselected"] = request["selected"].copy()
    elif fault == "unselected-ran":
        request["results"][1]["conclusion"] = "success"
    elif fault == "many-rows":
        monkeypatch.setattr(check_inputs, "MAX_ROWS", 1)
    else:
        request["selected"] = ["lint\0"]
    with pytest.raises(ValueError, match="input"):
        check_inputs.evaluate_results(request)


def test_bound_prose_handles_known_absence_without_downrouting() -> None:
    from scripts.validation.check_inputs import evaluate_prose

    request, authority = prose_input()
    request["blobs"][0]["base"] = None
    request["blobs"][0]["base_sha256"] = None
    assert evaluate_prose(request, authority)["prose_only"] is False


def local_specification() -> dict[str, object]:
    def check(argv: list[str]) -> dict[str, object]:
        return {
            "argv": [argv],
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


def recipe_specification() -> dict[str, Any]:
    specification: Any = local_specification()
    specification["schema_version"] = 2
    specification["migration"] = [{"path": ".github/workflows/fixture.yml", "sha256": "a" * 64, "role": "migration-baseline"}]
    for definition in specification["checks"].values():
        definition["recipe"] = {
            "source": {"path": ".github/workflows/fixture.yml", "sha256": "a" * 64, "role": "migration-baseline"},
            "python_version": "3.12",
            "advisory": False,
            "required_inputs": ["candidate", "base", "dependencies"],
            "conditions": ["success"],
            "instances": ["default"],
        }
    return specification


def test_native_accepts_explicit_recipe_metadata_without_executing_it(tmp_path: Path, native_selector: Path) -> None:
    path = write_local(tmp_path, recipe_specification())
    result = subprocess.run([str(native_selector), str(path), "full"], check=False, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["validation_performed"] is False


@pytest.mark.parametrize("fault", ["unknown-input", "condition-count", "unknown-condition", "missing-recipe", "source-drift", "unknown-field"])
def test_native_refuses_unmapped_or_incomplete_recipe_metadata(tmp_path: Path, native_selector: Path, fault: str) -> None:
    specification = recipe_specification()
    recipe = specification["checks"]["lint"]["recipe"]
    if fault == "unknown-input":
        recipe["required_inputs"] = ["guessed-credential"]
    elif fault == "condition-count":
        recipe["conditions"] = []
    elif fault == "unknown-condition":
        recipe["conditions"] = ["guessed"]
    elif fault == "missing-recipe":
        del specification["checks"]["lint"]["recipe"]
    elif fault == "source-drift":
        recipe["source"]["sha256"] = "b" * 64
    else:
        recipe["surprise"] = True
    path = write_local(tmp_path, specification)
    result = subprocess.run([str(native_selector), str(path), "full"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert result.stdout == ""


def write_local(root: Path, specification: dict[str, object]) -> Path:
    path = root / "gates.json"
    path.write_text(json.dumps(specification))
    return path


def test_canonical_specification_binds_every_selected_check(native_selector: Path) -> None:
    """A full local proposal needs commands and bounds, beyond routing parity."""
    repository = Path(__file__).resolve().parents[2]
    authority = repository / "tools/validation/gates.json"
    result = subprocess.run(
        [str(native_selector), str(authority), "full"],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    selected = json.loads(result.stdout)["selected_jobs"]
    assert selected, "Full selection must retain required checks"
    specification = json.loads(authority.read_text(encoding="utf-8"))
    checks = specification.get("checks")
    assert isinstance(checks, dict) and checks, "Canonical authority lacks executable check definitions"
    missing = sorted(set(selected) - checks.keys())
    assert not missing, f"Selected checks lack executable definitions: {missing}"
    for check_id in selected:
        definition = checks[check_id]
        assert definition["argv"], f"Empty command recipe: {check_id}"
        assert "full" in definition["modes"], f"Required full check excluded: {check_id}"
        assert definition["platforms"], f"Missing qualification platform: {check_id}"
        assert all(type(value) is int and value > 0 for value in definition["budgets"].values())
    assert json.loads(result.stdout)["validation_performed"] is False


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


def test_native_selection_includes_transitive_check_dependencies(tmp_path: Path, native_selector: Path) -> None:
    specification: Any = local_specification()
    specification["checks"]["test-docs"]["dependencies"] = ["test-runtime"]
    specification["checks"]["test-runtime"]["dependencies"] = ["lint"]
    path = write_local(tmp_path, specification)
    result = subprocess.run([str(native_selector), str(path), "pr", "docs/operator.md"], check=True, capture_output=True, text=True, timeout=20)
    actual = json.loads(result.stdout)
    assert actual["selected_jobs"] == ["lint", "test-docs", "test-runtime"]
    assert actual["selected_code_shards"] == ["test-runtime"]


def test_checked_in_authority_matches_pinned_hosted_routing(native_selector: Path) -> None:
    """The local selector and its Python consumer preserve the pinned router answer."""
    repository = Path(__file__).resolve().parents[2]
    local_authority = repository / "tools/validation/gates.json"
    hosted_router = repository / ".github/workflows/ci-router.yml"
    specification = json.loads(local_authority.read_text(encoding="utf-8"))
    import hashlib

    assert specification["source"]["sha256"] == hashlib.sha256(hosted_router.read_bytes()).hexdigest()  # noqa: TID251 — exact source-file migration pin, not charter freshness
    local = load_router(local_authority)
    hosted = load_router(hosted_router)
    assert load_router() == local
    registry = yaml.safe_load((repository / ".github/ci-module-registry.yml").read_text(encoding="utf-8"))
    assert specification["modules"] == registry["modules"]
    paths = [
        "src/specify_cli/mission.py",
        "tests/specify_cli/test_mission.py",
        "docs/guide.md",
        "tools/zig/validation_selection.zig",
        ".github/workflows/ci-router.yml",
        "src/unmapped/new_surface.py",
    ]
    for mode in ("pr", "full"):
        expected = select_gates(paths, router=hosted, mode=mode)
        python_actual = select_gates(paths, router=local, mode=mode)
        assert python_actual == expected
        assert select_gates(paths, mode=mode) == expected
        result = subprocess.run(
            [str(native_selector), str(local_authority), mode, *paths],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        native_actual = json.loads(result.stdout)
        assert native_actual["matched_groups"] == sorted(expected.matched_groups)
        assert native_actual["unmatched_src"] == expected.unmatched_src
        assert native_actual["selected_jobs"] == sorted(expected.selected_jobs)
        assert native_actual["selected_code_shards"] == sorted(expected.selected_code_shards)


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


@pytest.mark.parametrize("section", ["root", "routing", "source", "module", "check", "budget"])
def test_native_unknown_authority_fields_refuse(tmp_path: Path, native_selector: Path, section: str) -> None:
    specification: Any = local_specification()
    if section == "root":
        specification["surprise"] = True
    elif section == "routing":
        specification["routing"]["surprise"] = []
    elif section == "source":
        specification["source"] = {"path": ".github/workflows/ci-router.yml", "sha256": "a" * 64, "role": "migration-baseline", "surprise": True}
    elif section == "module":
        specification["modules"][0]["surprise"] = True
    elif section == "check":
        specification["checks"]["lint"]["surprise"] = True
    else:
        specification["checks"]["lint"]["budgets"]["surprise"] = 1
    path = write_local(tmp_path, specification)
    result = subprocess.run([str(native_selector), str(path), "pr", "src/runtime/worker.py"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert result.stdout == ""
    assert "UnknownField" in result.stderr


@pytest.mark.parametrize("section", ["filter", "job"])
def test_native_malformed_route_identifiers_refuse(tmp_path: Path, native_selector: Path, section: str) -> None:
    specification: Any = local_specification()
    if section == "filter":
        specification["routing"]["filters"]["runtime/extra"] = ["src/extra/**"]
    else:
        specification["routing"]["job_gates"]["test runtime"] = ["runtime"]
    path = write_local(tmp_path, specification)
    result = subprocess.run([str(native_selector), str(path), "pr", "src/runtime/worker.py"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert result.stdout == ""
    assert "InvalidRouting" in result.stderr


@pytest.mark.parametrize("failure", ["argv", "platform", "missing_budget", "zero_budget", "unknown_dependency", "cycle", "environment_key", "environment_value"])
def test_native_invalid_check_specs_refuse(tmp_path: Path, native_selector: Path, failure: str) -> None:
    specification: Any = local_specification()
    if failure == "argv":
        specification["checks"]["lint"]["argv"] = ["python", "-m", "ruff"]
    elif failure == "platform":
        specification["checks"]["lint"]["platforms"] = ["plan9"]
    elif failure == "missing_budget":
        del specification["checks"]["lint"]["budgets"]["wall_ms"]
    elif failure == "zero_budget":
        specification["checks"]["lint"]["budgets"]["wall_ms"] = 0
    elif failure == "unknown_dependency":
        specification["checks"]["lint"]["dependencies"] = ["missing-check"]
    elif failure == "environment_key":
        specification["checks"]["lint"]["environment"]["BAD=NAME"] = "value"
    elif failure == "environment_value":
        specification["checks"]["lint"]["environment"]["MODE"] = "bad\u0000value"
    else:
        specification["checks"]["test-runtime"]["dependencies"] = ["test-docs"]
        specification["checks"]["test-docs"]["dependencies"] = ["test-runtime"]
    path = write_local(tmp_path, specification)
    result = subprocess.run([str(native_selector), str(path), "pr", "src/runtime/worker.py"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert result.stdout == ""
    assert "selection refused" in result.stderr


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


def test_committed_workflow_inventory_matches_all_current_sources() -> None:
    """The migration inventory stays reproducible and can never qualify checks."""
    from scripts.validation.extract_gates import extract_workflows

    repository = Path(__file__).resolve().parents[2]
    inventory_path = repository / "tools/validation/workflow-migration-inventory.json"
    committed = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert committed == extract_workflows(repository)
    assert committed["authority"] is False
    assert committed["validation_performed"] is False
    assert committed["runnable"] is False
    assert len(committed["workflows"]) == 19
    assert committed["blockers"]


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


@pytest.mark.parametrize("preamble", ["", "# Documentation only\n", "# Comment ending with a backslash \\\n"])
@pytest.mark.parametrize("joined_word", [False, True])
def test_extraction_continued_static_commands_match_bash(tmp_path: Path, preamble: str, joined_word: bool) -> None:
    """Continuation removal preserves actual argv without executing workflow data."""
    import shlex
    import sys

    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    program = tmp_path / "argv_probe.py"
    program.write_text("import json, sys\nprint(json.dumps(sys.argv[1:]))\n")
    command = preamble + f"{shlex.quote(sys.executable)} {shlex.quote(str(program))} 'first value' \\\n 'café' \\\n ''\n"
    if joined_word:
        command = command.rstrip("\n") + " left\\\nright\n"
    (directory / "continued.yml").write_text(yaml.safe_dump({"jobs": {"check": {"steps": [{"run": command}]}}}))
    report = extract_workflows(tmp_path)
    argv = report["workflows"][0]["jobs"]["check"]["steps"][0]["argv"]
    assert argv is not None
    assert argv[0][2:] == ["first value", "café", ""] + (["leftright"] if joined_word else [])
    shell = subprocess.run(["/bin/bash", "--noprofile", "--norc", "-c", command], check=True, capture_output=True, text=True, timeout=20)
    direct = subprocess.run(argv[0], check=True, capture_output=True, text=True, timeout=20)
    assert json.loads(shell.stdout) == json.loads(direct.stdout)
    assert not any(item["reason"] == "shell_semantics" for item in report["blockers"])
    assert report["runnable"] is False
    assert report["validation_performed"] is False


@pytest.mark.parametrize(
    "command",
    [
        "python -m tool 'quoted\\\ncontinuation'",
        'python -m tool "quoted\\\ncontinuation"',
        "python -m tool \\\\\nnext",
        "python -m tool \\",
        "python -m tool \\\n$(id)",
        "python -m tool \\\n# inline comment",
        "# No executable command \\",
    ],
)
def test_extraction_refuses_unqualified_continuations(tmp_path: Path, command: str) -> None:
    from scripts.validation.extract_gates import extract_workflows

    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "refused.yml").write_text(yaml.safe_dump({"jobs": {"check": {"steps": [{"run": command}]}}}))
    report = extract_workflows(tmp_path)
    assert report["workflows"][0]["jobs"]["check"]["steps"][0]["argv"] is None
    assert any(item["reason"] == "shell_semantics" for item in report["blockers"])
