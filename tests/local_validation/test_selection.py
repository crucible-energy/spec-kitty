"""Discriminating local-authority controls against the existing public reader."""

import json
import hashlib
from fnmatch import fnmatch
import os
import subprocess
from pathlib import Path
from typing import Any
from types import SimpleNamespace

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


def test_local_result_adapter_retains_advisory_failure_without_hiding_timeout() -> None:
    from scripts.validation.check_inputs import evaluate_results

    request = result_input()
    request["advisory"] = ["markdownlint"]
    request["results"].append({"id": "markdownlint", "conclusion": "failure", "binding": request["binding"].copy()})
    result = evaluate_results(request)
    assert result["blocks"] is False
    assert result["advisory_outcomes"] == {"markdownlint": "failure"}
    request["results"][-1]["conclusion"] = "timed_out"
    assert evaluate_results(request)["blocking"] == {"markdownlint": "timed_out"}


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
            "applicability": "routing",
            "packages": {},
            "instance_environment": {},
            "observed_dependencies": [],
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


@pytest.mark.parametrize(
    "fault",
    [
        "packages",
        "instance-count",
        "instance-name",
        "instance-env",
        "missing-platform",
        "missing-migration",
        "duplicate-source",
        "foreign-observation",
        "legacy-recipe",
    ],
)
def test_native_refuses_ambiguous_recipe_bindings(tmp_path: Path, native_selector: Path, fault: str) -> None:
    specification = recipe_specification()
    check = specification["checks"]["lint"]
    recipe = check["recipe"]
    if fault == "packages":
        recipe["packages"] = {"PyYAML": 6}
    elif fault == "instance-count":
        recipe["instances"] = []
    elif fault == "instance-name":
        recipe["instances"] = ["../escape"]
    elif fault == "instance-env":
        recipe["instance_environment"] = {"unknown": {"X": "value"}}
    elif fault == "missing-platform":
        del check["platforms"]
    elif fault == "missing-migration":
        del specification["migration"]
    elif fault == "duplicate-source":
        specification["migration"].append(specification["migration"][0].copy())
    elif fault == "foreign-observation":
        recipe["observed_dependencies"] = ["absent"]
    else:
        specification["schema_version"] = 1
    result = subprocess.run([str(native_selector), str(write_local(tmp_path, specification)), "full"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert result.stdout == ""


@pytest.mark.parametrize("field", ["source", "python_version", "advisory", "applicability", "packages", "instance_environment", "observed_dependencies"])
def test_native_recipe_refuses_missing_required_context(tmp_path: Path, native_selector: Path, field: str) -> None:
    specification = recipe_specification()
    del specification["checks"]["lint"]["recipe"][field]
    result = subprocess.run([str(native_selector), str(write_local(tmp_path, specification)), "full"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert result.stdout == ""


@pytest.mark.parametrize(
    "fault",
    [
        "python-version",
        "advisory-type",
        "applicability",
        "command-phase-count",
        "environment-name",
        "environment-nul",
        "migration-shape",
        "no-checks",
        "self-observation",
        "legacy-with-recipe",
    ],
)
def test_native_recipe_refuses_incompatible_execution_declarations(tmp_path: Path, native_selector: Path, fault: str) -> None:
    specification = recipe_specification()
    recipe = specification["checks"]["lint"]["recipe"]
    if fault == "python-version":
        recipe["python_version"] = "unavailable"
    elif fault == "advisory-type":
        recipe["advisory"] = "false"
    elif fault == "applicability":
        recipe["applicability"] = "guessed"
    elif fault == "command-phase-count":
        recipe["conditions"] = ["success", "always"]
    elif fault == "environment-name":
        recipe["instance_environment"] = {"default": {"INVALID-NAME": "value"}}
    elif fault == "environment-nul":
        recipe["instance_environment"] = {"default": {"X": "a\0b"}}
    elif fault == "migration-shape":
        specification["migration"] = {}
    elif fault == "no-checks":
        del specification["checks"]
    elif fault == "self-observation":
        recipe["observed_dependencies"] = ["lint"]
    else:
        specification["schema_version"] = 1
        del specification["migration"]
    result = subprocess.run([str(native_selector), str(write_local(tmp_path, specification)), "full"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert result.stdout == ""


class SimulatedWindowsInputIO:
    """Exercise I/O decisions on real local descriptors, not Windows qualification."""

    def __init__(self, attributes: int = 0x80, kind: int = 1) -> None:
        self.attributes = attributes
        self.file_kind = kind
        self.descriptors: list[int] = []
        self.content_opens = 0

    def open(self, path: Path, content: bool) -> int:
        if content:
            self.content_opens += 1
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        self.descriptors.append(descriptor)
        return descriptor

    def info(self, descriptor: int) -> tuple[int, ...]:
        info = os.fstat(descriptor)
        return (self.attributes, info.st_dev, info.st_ino >> 32, info.st_ino & 0xFFFFFFFF, info.st_size, info.st_ctime_ns, info.st_mtime_ns)

    def kind(self, descriptor: int) -> int:
        return self.file_kind

    def close(self, descriptor: int) -> None:
        os.close(descriptor)

    def read(self, handle: int, size: int) -> bytes:
        return os.read(handle, size)


def windows_input_seam(monkeypatch: pytest.MonkeyPatch, api: SimulatedWindowsInputIO) -> None:
    from scripts.validation import check_inputs

    # Replace only the adapter's os reference: no shared process/module flag mutation.
    proxy = SimpleNamespace(name="nt", O_RDONLY=os.O_RDONLY, open=os.open, fstat=os.fstat, close=os.close, fdopen=os.fdopen)
    monkeypatch.setattr(check_inputs, "os", proxy)
    monkeypatch.setattr(check_inputs, "_windows_api", lambda: api, raising=False)


@pytest.mark.skipif(os.name != "posix", reason="POSIX-hosted I/O capability simulation; not Windows qualification")
@pytest.mark.parametrize("kind", ["results", "prose"])
def test_windows_missing_posix_flags_supports_bounded_regular_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    from scripts.validation.check_inputs import main

    path = tmp_path / "result.json"
    arguments = [kind, str(path)]
    if kind == "prose":
        request, raw = prose_input()
        authority = tmp_path / "authority.json"
        authority.write_bytes(raw)
        arguments.extend(["--authority", str(authority)])
    else:
        request = result_input()
    path.write_text(json.dumps(request))
    api = SimulatedWindowsInputIO()
    windows_input_seam(monkeypatch, api)
    assert main(arguments) == 0
    output = json.loads(capsys.readouterr().out)
    assert output.get("prose_only", not output.get("blocks")) is True
    assert api.content_opens == (2 if kind == "prose" else 1)
    for descriptor in api.descriptors:
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(descriptor)


@pytest.mark.parametrize("attributes", [0x10, 0x400])
@pytest.mark.skipif(os.name != "posix", reason="POSIX-hosted I/O capability simulation; not Windows qualification")
def test_windows_unsafe_attributes_refuse_before_content_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], attributes: int
) -> None:
    from scripts.validation.check_inputs import main

    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps(result_input()))
    api = SimulatedWindowsInputIO(attributes=attributes)
    windows_input_seam(monkeypatch, api)
    assert main(["results", str(path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "Local input refused\n"
    assert api.content_opens == 0
    for descriptor in api.descriptors:
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(descriptor)


class SimulatedNativeCall:
    def __init__(self, callback: Any) -> None:
        self.callback = callback
        self.argtypes: list[Any] = []
        self.restype: Any = None

    def __call__(self, *args: Any) -> Any:
        return self.callback(*args)


class SimulatedWindowsKernel:
    """Assert real adapter ABI/flags and cleanup using local descriptors."""

    def __init__(self, fault: str) -> None:
        self.fault = fault
        self.handles: list[int] = []
        self.content: set[int] = set()
        self.CreateFileW = SimulatedNativeCall(self.create)
        self.GetFileInformationByHandle = SimulatedNativeCall(self.information)
        self.GetFileInformationByHandleEx = SimulatedNativeCall(self.identity)
        self.GetFileType = SimulatedNativeCall(lambda handle: 2 if fault == "pipe" else 1)
        self.CloseHandle = SimulatedNativeCall(self.close)
        self.ReadFile = SimulatedNativeCall(self.read)

    def create(self, path: str, access: int, share: int, security: Any, disposition: int, flags: int, template: Any) -> int:
        import ctypes

        assert share == 1 and security is None and disposition == 3 and flags == 0x00200000 and template is None
        assert access in (0x80, 0x80000000)
        if self.fault == "open":
            return int(ctypes.c_void_p(-1).value)
        handle = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        self.handles.append(handle)
        if access == 0x80000000:
            self.content.add(handle)
        return handle

    def information(self, handle: int, target: Any) -> int:
        if self.fault == "information":
            return 0
        info = os.fstat(handle)
        record = target._obj
        record.attributes = 0x400 if self.fault == "reparse" else 0x80
        record.size_low, record.size_high = info.st_size & 0xFFFFFFFF, info.st_size >> 32
        record.creation_low, record.creation_high = info.st_ctime_ns & 0xFFFFFFFF, info.st_ctime_ns >> 32
        record.write_low, record.write_high = info.st_mtime_ns & 0xFFFFFFFF, info.st_mtime_ns >> 32
        if self.fault == "oversized":
            record.size_low = 16 * 1024 * 1024 + 1
        return 1

    def identity(self, handle: int, kind: int, target: Any, size: int) -> int:
        assert kind == 18 and size == 24
        if self.fault == "identity":
            return 0
        info = os.fstat(handle)
        record = target._obj
        record.volume = info.st_dev
        value = info.st_ino + (1 if self.fault == "drift" and handle in self.content else 0)
        record.identifier[:] = value.to_bytes(16, "little")
        if self.fault == "unknown-id":
            record.volume = 0
        return 1

    def close(self, handle: int) -> int:
        os.close(handle)
        return 1

    def read(self, handle: int, buffer: Any, size: int, count: Any, overlapped: Any) -> int:
        assert overlapped is None and handle in self.content
        if self.fault == "read":
            return 0
        raw = os.read(handle, size)
        buffer._obj.raw = raw
        count._obj.value = len(raw) if self.fault != "count" else size + 1
        return 1


@pytest.mark.parametrize("fault", ["none", "open", "information", "identity", "pipe", "reparse", "oversized", "unknown-id", "drift", "read", "count"])
@pytest.mark.skipif(os.name != "posix", reason="POSIX-hosted I/O capability simulation; not Windows qualification")
def test_windows_native_binding_contract_and_joined_handles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fault: str
) -> None:
    import ctypes
    from scripts.validation import check_inputs

    path = tmp_path / "native.json"
    path.write_text(json.dumps(result_input()))
    kernel = SimulatedWindowsKernel(fault)
    monkeypatch.setattr(ctypes, "WinDLL", lambda name, use_last_error: kernel, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    proxy = SimpleNamespace(name="nt")
    monkeypatch.setattr(check_inputs, "os", proxy)
    assert check_inputs.main(["results", str(path)]) == (0 if fault == "none" else 2)
    captured = capsys.readouterr()
    if fault == "none":
        assert json.loads(captured.out)["blocks"] is False and captured.err == ""
        assert kernel.content
    else:
        assert captured.out == "" and captured.err == "Local input refused\n"
        if fault in {"open", "information", "identity", "pipe", "reparse", "oversized", "unknown-id"}:
            assert not kernel.content
    assert len(kernel.CreateFileW.argtypes) == 7
    for handle in kernel.handles:
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(handle)


@pytest.mark.skipif(os.name != "posix", reason="POSIX-hosted I/O capability simulation; not Windows qualification")
def test_missing_native_io_capabilities_refuse_without_traceback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import ctypes
    from scripts.validation import check_inputs

    path = tmp_path / "native.json"
    path.write_text(json.dumps(result_input()))
    monkeypatch.setattr(ctypes, "WinDLL", None, raising=False)
    proxy = SimpleNamespace(name="nt", O_RDONLY=os.O_RDONLY, close=os.close, fdopen=os.fdopen)
    monkeypatch.setattr(check_inputs, "os", proxy)
    assert check_inputs.main(["results", str(path)]) == 2
    assert capsys.readouterr().err == "Local input refused\n"


@pytest.mark.parametrize("fault", ["symlink", "directory", "fifo", "oversized"])
@pytest.mark.skipif(os.name != "posix", reason="POSIX-hosted I/O capability simulation; not Windows qualification")
def test_platform_file_refusals_precede_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    from scripts.validation import check_inputs

    path = tmp_path / "unsafe"
    if fault == "symlink":
        target = tmp_path / "target"
        target.write_bytes(b"{}")
        path.symlink_to(target)
    elif fault == "directory":
        path.mkdir()
    elif fault == "fifo":
        os.mkfifo(path)
    else:
        with path.open("wb") as stream:
            stream.truncate(check_inputs.MAX_BYTES + 1)
    monkeypatch.setattr(check_inputs, "_windows_api", lambda: pytest.fail("unsafe Windows input reached native open"))
    proxy = SimpleNamespace(name="nt")
    monkeypatch.setattr(check_inputs, "os", proxy)
    with pytest.raises(ValueError, match="input"):
        check_inputs._read(path)


@pytest.mark.skipif(os.name != "posix", reason="POSIX-hosted I/O capability simulation; not Windows qualification")
def test_posix_identity_change_refuses_before_content_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.validation import check_inputs

    path = tmp_path / "changed.json"
    path.write_bytes(b"{}")
    opened: list[int] = []
    real_open = os.open

    def changed(*args: Any, **kwargs: Any) -> int:
        replacement = tmp_path / "replacement"
        replacement.write_bytes(b"{}")
        replacement.replace(path)
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(check_inputs.os, "open", changed)
    with pytest.raises(ValueError, match="input"):
        check_inputs._read(path)
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(opened[0])


@pytest.mark.skipif(os.name != "nt", reason="Requires a genuine Windows kernel and CRT; unqualified on this host")
def test_windows_actual_regular_input_and_directory_refusal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.validation.check_inputs import main

    path = tmp_path / "actual.json"
    path.write_text(json.dumps(result_input()))
    assert main(["results", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["blocks"] is False
    assert main(["results", str(tmp_path)]) == 2
    assert capsys.readouterr().err == "Local input refused\n"


def test_input_descriptor_is_closed_if_stream_construction_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.validation import check_inputs

    path = tmp_path / "input.json"
    path.write_bytes(b"{}")
    descriptors: list[int] = []
    real_open = os.open

    def opened(*args: Any, **kwargs: Any) -> int:
        descriptor = real_open(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor

    def refused(*args: Any, **kwargs: Any) -> Any:
        raise OSError("synthetic stream construction refusal")

    monkeypatch.setattr(check_inputs.os, "open", opened)
    monkeypatch.setattr(check_inputs.os, "fdopen", refused)
    with pytest.raises(OSError, match="synthetic stream construction refusal"):
        check_inputs._read(path)
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(descriptors[0])


def test_router_recipe_cli_emits_exact_authority_and_refuses_qualification(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.validation import extract_gates

    monkeypatch.setattr("sys.argv", ["extract_gates", "--router-specification"])
    assert extract_gates.main() == 0
    assert json.loads(capsys.readouterr().out) == json.loads((Path(__file__).resolve().parents[2] / "tools/validation/gates.json").read_text())
    monkeypatch.setattr("sys.argv", ["extract_gates", "--router-specification", "--require-runnable"])
    assert extract_gates.main() == 2
    assert "not execution qualification" in capsys.readouterr().err


def test_current_router_recipes_preserve_static_commands_and_dynamic_contracts() -> None:
    from scripts.validation.extract_gates import _commands, executable_router_specification

    repository = Path(__file__).resolve().parents[2]
    proposal = executable_router_specification(repository)
    workflow = yaml.safe_load((repository / ".github/workflows/ci-router.yml").read_text())
    checks = proposal["checks"]
    assert set(workflow["jobs"]) - {"changes"} <= set(checks)
    for name, job in workflow["jobs"].items():
        if name in {"changes", "architectural-heavy", "prose-scan", "router-gate", "commit-msg", "markdownlint"}:
            continue
        for step in job["steps"]:
            commands = _commands(step.get("run"))
            for command in commands or []:
                assert command in checks[name]["argv"]
    heavy = checks["architectural-heavy"]
    assert set(heavy["recipe"]["instances"]) == {"1-of-2", "2-of-2"}
    for shard in ("1/2", "2/2"):
        assert any("--battery-part" in command and shard in command for command in heavy["argv"])
    assert "universe" in heavy["recipe"]["conditions"]
    assert "universe-always" in heavy["recipe"]["conditions"]
    assert heavy["recipe"]["applicability"] == "routing-and-not-prose"
    assert checks["tests-docs"]["recipe"]["applicability"] == "routing-or-prose"
    assert checks["prose-scan"]["recipe"]["packages"] == {"PyYAML": "6.0.2"}
    assert checks["commit-msg"]["recipe"]["advisory"] is True
    assert checks["markdownlint"]["recipe"]["advisory"] is True
    assert "@commit_range" in checks["commit-msg"]["argv"][0]
    assert "scripts.validation.check_inputs" in checks["router-gate"]["argv"][0]
    assert not any(command[0] == "gh" for command in checks["router-gate"]["argv"])
    assert checks["router-gate"]["dependencies"] == []
    assert checks["router-gate"]["recipe"]["observed_dependencies"] == workflow["jobs"]["router-gate"]["needs"]
    assert set(heavy["recipe"]["instance_environment"]) == {"1-of-2", "2-of-2"}


def test_canonical_workflow_contracts_preserve_every_original_definition() -> None:
    from scripts.validation.extract_gates import _load, _read

    root = Path(__file__).resolve().parents[2]
    authority = json.loads((root / "tools/validation/gates.json").read_text())
    contracts = authority.get("workflow_contracts")
    assert isinstance(contracts, list) and len(contracts) == 19, "Full workflow contracts are missing from the canonical authority"
    assert {row["source"]["path"] for row in contracts} == {row["path"] for row in authority["migration"]}
    for row in contracts:
        source = root / row["source"]["path"]
        original = _load(_read(source))
        assert row["definition"] == original, "Triggers, conditions, shell bodies, matrices, setup, artifacts or publication changed"
        assert row["source"]["sha256"] == fixture_digest(source.read_bytes())
        assert set(row["jobs"]) == set(original["jobs"])
        for name, job in original["jobs"].items():
            mapping = row["jobs"][name]
            assert mapping["wall_ms"] == job.get("timeout-minutes", 360) * 60000
            assert mapping["budget_scope"] == "per-job-instance"
            assert mapping["binding_required"] is True
            assert mapping["check_id"] is None or mapping["check_id"] in authority["checks"]


@pytest.mark.parametrize(
    ("workflow", "job"),
    [
        ("ci-quality", "lint"),
        ("ci-quality", "build-wheel"),
        ("ci-quality", "uv-lock-check"),
        ("ci-nightly", "universe-equivalence"),
        ("ci-shard-recapture", "strict-shard-timings-check"),
        ("contracts", "verify-pins"),
    ],
)
def test_canonical_static_workflow_recipes_are_actual_complete_source_argv(workflow: str, job: str) -> None:
    from scripts.validation.extract_gates import _commands, _load, _read

    root = Path(__file__).resolve().parents[2]
    authority = json.loads((root / "tools/validation/gates.json").read_text())
    name = f"{workflow}.{job}"
    assert name in authority["checks"], "A compatible actual workflow recipe is missing"
    definition = _load(_read(root / f".github/workflows/{workflow}.yml"))["jobs"][job]
    expected = [command for step in definition["steps"] if "run" in step for command in _commands(step["run"])]
    check = authority["checks"][name]
    assert check["argv"] == expected and expected
    assert check["budgets"]["wall_ms"] == definition["timeout-minutes"] * 60000
    assert check["recipe"]["workflow_job"] == job
    assert "workflow_context" in check["recipe"]["required_inputs"]
    assert check["recipe"]["source"]["path"] == f".github/workflows/{workflow}.yml"


def test_workflow_contracts_preserve_publication_and_administration_boundaries() -> None:
    root = Path(__file__).resolve().parents[2]
    authority = json.loads((root / "tools/validation/gates.json").read_text())
    contracts = authority.get("workflow_contracts")
    assert isinstance(contracts, list), "Missing actual workflow contracts"
    rows = {row["source"]["path"]: row for row in contracts}
    assert "ci-shard-recapture.recapture-shard-timings" not in authority["checks"]
    assert rows[".github/workflows/contracts-release.yml"]["definition"]["jobs"]["publish"]["permissions"] == {"contents": "write"}
    assert rows[".github/workflows/docs-pages.yml"]["definition"]["jobs"]["deploy"]["needs"] == "build"
    assert rows[".github/workflows/ci-aggregate.yml"]["definition"]["jobs"]["aggregate-gate"]["needs"] == ["collect", "diff-cover"]


def test_native_full_inspection_discloses_all_unresolved_workflow_jobs(native_selector: Path) -> None:
    authority = Path(__file__).resolve().parents[2] / "tools/validation/gates.json"
    result = subprocess.run([str(native_selector), str(authority), "full"], capture_output=True, text=True, timeout=20, check=True)
    selected = json.loads(result.stdout)
    assert "unbound_workflow_jobs" in selected, "Native preview hides the remaining workflow bindings"
    assert selected["unbound_workflow_jobs"]
    assert "release.build-release" in selected["unbound_workflow_jobs"]
    assert "ci-windows.windows-critical" in selected["unbound_workflow_jobs"]
    assert selected["selection_only"] is True and selected["execution_supported"] is False


@pytest.mark.parametrize("fault", ["missing-contract", "source-pin", "budget", "binding-marker", "cycle", "orphan-check"])
def test_native_workflow_contract_refuses_missing_or_false_bindings(tmp_path: Path, native_selector: Path, fault: str) -> None:
    root = Path(__file__).resolve().parents[2]
    proposal = json.loads((root / "tools/validation/gates.json").read_text())
    row = next(item for item in proposal["workflow_contracts"] if item["id"] == "ci-quality")
    if fault == "missing-contract":
        proposal["workflow_contracts"].pop()
    elif fault == "source-pin":
        row["source"]["sha256"] = "0" * 64
    elif fault == "budget":
        row["jobs"]["lint"]["wall_ms"] = 1
    elif fault == "binding-marker":
        row["jobs"]["lint"]["binding_required"] = False
    elif fault == "cycle":
        row["definition"]["jobs"]["lint"]["needs"] = ["uv-lock-check"]
        row["definition"]["jobs"]["uv-lock-check"]["needs"] = ["lint"]
    else:
        row["jobs"]["lint"]["check_id"] = None
    result = subprocess.run([str(native_selector), str(write_local(tmp_path, proposal)), "full"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and result.stdout == ""
    assert "selection refused" in result.stderr


def test_native_workflow_target_refuses_actual_unbound_context(native_selector: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [str(native_selector), str(root / "tools/validation/gates.json"), "--platform", "linux", "full"], capture_output=True, text=True, timeout=20
    )
    assert result.returncode != 0 and result.stdout == ""
    assert "UnboundWorkflowContext" in result.stderr


def test_workflow_regeneration_refuses_changed_other_source(tmp_path: Path) -> None:
    from scripts.validation.extract_gates import executable_router_specification
    import shutil

    root = Path(__file__).resolve().parents[2]
    (tmp_path / "tools/validation").mkdir(parents=True)
    shutil.copy2(root / "tools/validation/gates.json", tmp_path / "tools/validation/gates.json")
    shutil.copytree(root / ".github/workflows", tmp_path / ".github/workflows")
    with (tmp_path / ".github/workflows/ci-quality.yml").open("a") as stream:
        stream.write("\n# source epoch changed\n")
    with pytest.raises(ValueError, match="Pinned workflow roster changed"):
        executable_router_specification(tmp_path)


def test_router_recipe_construction_refuses_changed_source_epoch(tmp_path: Path) -> None:
    from scripts.validation.extract_gates import executable_router_specification

    root = Path(__file__).resolve().parents[2]
    authority = json.loads((root / "tools/validation/gates.json").read_text())
    (tmp_path / "tools/validation").mkdir(parents=True)
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "tools/validation/gates.json").write_text(json.dumps(authority))
    (tmp_path / ".github/workflows/ci-router.yml").write_text("name: changed\njobs: {}\n")
    with pytest.raises(ValueError, match="Pinned router changed"):
        executable_router_specification(tmp_path)


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


def retained_native_selector(binding: Path, repository: Path) -> Path:
    """Reuse one physically pinned completed build; this is not attestation."""
    record = json.loads(binding.read_text())
    assert set(record) == {"image", "source_sha256", "image_sha256", "compiler", "compiler_sha256", "receipt", "receipt_sha256"}
    source = repository / "tools/zig/validation_selection.zig"
    image, compiler, receipt = (Path(record[name]) for name in ("image", "compiler", "receipt"))
    for name, path in (("source", source), ("image", image), ("compiler", compiler), ("receipt", receipt)):
        assert fixture_digest(path.read_bytes()) == record[f"{name}_sha256"], f"Changed retained native {name}"
    completed = json.loads(receipt.read_text())
    assert completed["exit_code"] == 0 and completed["failure"] is None
    assert completed["leader_reaped"] and completed["group_disposed_observed"] and completed["remaining_group_pids"] == []
    assert completed["cwd"] == str(repository) and completed["wall_seconds"] <= 60
    assert completed["argv"] == [str(compiler), "build-exe", str(source), "-j1", "-lc", "-O", "ReleaseSafe", f"-femit-bin={image}"]
    return image


@pytest.fixture(scope="module")
def native_selector(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repository = Path(__file__).resolve().parents[2]
    binding = os.environ.get("SPEC_KITTY_NATIVE_SELECTOR_BINDING")
    if binding:
        return retained_native_selector(Path(binding), repository)
    executable = tmp_path_factory.mktemp("native-selector") / "selection"
    subprocess.run(
        ["zig", "build-exe", str(repository / "tools/zig/validation_selection.zig"), "-j1", "-lc", "-O", "ReleaseSafe", f"-femit-bin={executable}"],
        check=True,
        capture_output=True,
        timeout=60,
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
    packs = load_router(repository / ".github/workflows/packs.yml")
    from scripts.ci.gate_selection import Router

    source_filters = {**hosted.filters, **{"packs_" + name: patterns for name, patterns in packs.filters.items()}}
    source_gates = {
        **hosted.job_gates,
        **{name: frozenset("corpus" if group == "corpus" else "packs_" + group for group in groups) for name, groups in packs.job_gates.items()},
    }
    # Packs jobs are data lanes; unknown-source fan-out reaches their corpus predicate, never the unrelated lanes.
    non_conservative = frozenset(name for name, groups in packs.job_gates.items() if groups and "corpus" not in groups)
    hosted = Router(source_filters, source_gates, frozenset("packs_" + name for name in packs.filters), non_conservative)
    additions = frozenset(
        {
            "ci-quality.lint",
            "ci-quality.build-wheel",
            "ci-quality.uv-lock-check",
            "ci-nightly.universe-equivalence",
            "ci-shard-recapture.strict-shard-timings-check",
            "contracts.verify-pins",
            "contracts.python-checks",
            "contracts.validate-bundle",
            "contracts.resolver-parity",
            "contracts.negative-tests",
        }
    )
    assert local.workflow_jobs == additions
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
    unknown = [
        path
        for path in paths
        if not path.startswith("src/") and not any(fnmatch(path, pattern) for group in local.routing_groups for pattern in local.filters[group])
    ]
    for mode in ("pr", "full"):
        supported = paths
        if mode != "full" and unknown:
            # The current policy deliberately refuses formerly unclassified paths.
            with pytest.raises(ValueError, match="Unsupported changed surface"):
                select_gates(paths, router=local, mode=mode)
            refused = subprocess.run([str(native_selector), str(local_authority), mode, *paths], capture_output=True, text=True, timeout=20)
            assert refused.returncode != 0 and refused.stdout == ""
            assert "UnsupportedChangedSurface" in refused.stderr
            supported = [path for path in paths if path not in unknown]
        expected = select_gates(supported, router=hosted, mode=mode)
        python_actual = select_gates(supported, router=local, mode=mode)
        # Preserve every old source-oracle assertion, while explaining the
        # whole-workflow additions from their canonical declarations.
        assert python_actual.selected_jobs - additions == expected.selected_jobs
        assert python_actual.matched_groups == expected.matched_groups
        assert python_actual.unmatched_src == expected.unmatched_src
        assert python_actual.selected_code_shards == expected.selected_code_shards
        assert select_gates(supported, mode=mode) == python_actual
        expected_additions = additions if mode == "full" else frozenset({"ci-quality.lint", "ci-quality.build-wheel", "ci-quality.uv-lock-check"})
        assert python_actual.selected_jobs & additions == expected_additions
        result = subprocess.run(
            [str(native_selector), str(local_authority), mode, *supported],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        native_actual = json.loads(result.stdout)
        assert native_actual["matched_groups"] == sorted(expected.matched_groups)
        assert native_actual["unmatched_src"] == expected.unmatched_src
        assert native_actual["selected_jobs"] == sorted(expected.selected_jobs | expected_additions)
        assert native_actual["selected_code_shards"] == sorted(expected.selected_code_shards)
        assert native_actual["unbound_workflow_jobs"] == sorted(python_actual.unbound_workflow_jobs)


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
fn allocateTargetSelection(allocator: std.mem.Allocator, document: std.json.Value) !void {
    const selected = try selection.selectForTarget(allocator, document, &.{ "docs/operator.md" }, "commit", "windows");
    defer selected.deinit(allocator);
    try std.testing.expect(selected.target_checked);
}
fn allocateQualificationSelection(allocator: std.mem.Allocator, document: std.json.Value) !void {
    const selected = try selection.selectForTarget(allocator, document, &.{}, "docs", "windows");
    defer selected.deinit(allocator);
    try std.testing.expectEqual(@as(usize, 3), selected.selected_jobs.len);
}
fn allocateWorkflowSelection(allocator: std.mem.Allocator, document: std.json.Value) !void {
    const selected = try selection.select(allocator, document, &.{}, "full");
    defer selected.deinit(allocator);
    try std.testing.expectEqual(@as(usize, 92), selected.unbound_workflow_jobs.len);
}
fn allocateBoundProgram(allocator: std.mem.Allocator, document: std.json.Value) !void {
    var environment: std.process.Environ.Map = .init(std.testing.allocator);
    defer environment.deinit();
    try environment.put("RUNNER_TEMP", "/private/synthetic native temp");
    try environment.put("CONTRACTS_ROOT", "contracts");
    const bound = try selection.bindWorkflowProgram(allocator, document, "contracts.validate-bundle", &environment);
    defer bound.deinit(allocator);
    try std.testing.expectEqual(@as(usize, 5), bound.argv.len);
}
test "selection allocation and input bounds" {
    const bytes =
        \\__FIXTURE_JSON__
    ;
    const parsed = try std.json.parseFromSlice(std.json.Value, std.testing.allocator, bytes, .{});
    defer parsed.deinit();
    try std.testing.checkAllAllocationFailures(std.testing.allocator, allocateSelection, .{parsed.value});
    try std.testing.checkAllAllocationFailures(std.testing.allocator, allocateTargetSelection, .{parsed.value});
    try std.testing.checkAllAllocationFailures(std.testing.allocator, allocateQualificationSelection, .{parsed.value});
    var no_resize = std.testing.FailingAllocator.init(std.testing.allocator, .{ .resize_fail_index = 0 });
    try std.testing.checkAllAllocationFailures(no_resize.allocator(), allocateSelection, .{parsed.value});
    try std.testing.checkAllAllocationFailures(no_resize.allocator(), allocateQualificationSelection, .{parsed.value});
    try std.testing.expectEqual(no_resize.allocated_bytes, no_resize.freed_bytes);
    const workflow_bytes =
        \\__WORKFLOW_JSON__
    ;
    const workflow = try std.json.parseFromSlice(std.json.Value, std.testing.allocator, workflow_bytes, .{});
    defer workflow.deinit();
    try std.testing.checkAllAllocationFailures(std.testing.allocator, allocateWorkflowSelection, .{workflow.value});
    try std.testing.checkAllAllocationFailures(no_resize.allocator(), allocateWorkflowSelection, .{workflow.value});
    try std.testing.checkAllAllocationFailures(std.testing.allocator, allocateBoundProgram, .{workflow.value});
    try std.testing.checkAllAllocationFailures(no_resize.allocator(), allocateBoundProgram, .{workflow.value});
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
    specification: Any = local_specification()
    for check in specification["checks"].values():
        check["modes"].append("docs")
    harness.write_text(
        _NATIVE_API_CONTROLS.replace("__FIXTURE_JSON__", json.dumps(specification)).replace(
            "__WORKFLOW_JSON__", json.dumps(json.loads((repository / "tools/validation/gates.json").read_text()))
        )
    )
    executable = tmp_path / "allocation-controls"
    subprocess.run(
        [
            "zig",
            "test",
            "--test-no-exec",
            "-j1",
            "-lc",
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
        timeout=60,
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


@pytest.mark.parametrize(
    ("mode", "paths", "expected"),
    [
        ("pr", ["docs/operator.md"], [("lint", "always_on", ""), ("test-docs", "matched_group", "docs"), ("test-runtime", "dependency", "test-docs")]),
        ("full", [], [("lint", "always_on", ""), ("test-docs", "full", ""), ("test-runtime", "dependency", "test-docs"), ("test-runtime", "full", "")]),
        (
            "pr",
            ["src/new/unmapped.py"],
            [
                ("lint", "always_on", ""),
                ("test-docs", "unmatched_source", ""),
                ("test-runtime", "dependency", "test-docs"),
                ("test-runtime", "unmatched_source", ""),
            ],
        ),
    ],
)
def test_native_selection_explains_every_selected_check(
    tmp_path: Path, native_selector: Path, mode: str, paths: list[str], expected: list[tuple[str, str, str]]
) -> None:
    specification: Any = local_specification()
    specification["checks"]["test-docs"]["dependencies"] = ["test-runtime"]
    result = subprocess.run([str(native_selector), str(write_local(tmp_path, specification)), mode, *paths], check=True, capture_output=True, text=True, timeout=20)
    actual = json.loads(result.stdout)
    assert [(row["check"], row["kind"], row["reference"]) for row in actual["selected_reasons"]] == expected
    assert {row["check"] for row in actual["selected_reasons"]} == set(actual["selected_jobs"])
    assert actual["target_checked"] is False
    assert actual["validation_performed"] is False


@pytest.mark.parametrize("platform", ["macos", "linux", "windows"])
def test_native_commit_target_uses_declared_mode_and_platform(tmp_path: Path, native_selector: Path, platform: str) -> None:
    result = subprocess.run(
        [str(native_selector), str(write_local(tmp_path, local_specification())), "--platform", platform, "commit", "docs/operator.md"],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    actual = json.loads(result.stdout)
    assert actual["selected_jobs"] == ["lint", "test-docs"]
    assert actual["requested_platform"] == platform and actual["target_checked"] is True
    assert actual["selection_only"] is True and actual["execution_supported"] is False


@pytest.mark.parametrize("mode", ["platform", "release", "package", "docs"])
def test_native_qualification_mode_selects_declared_checks_and_dependencies(tmp_path: Path, native_selector: Path, mode: str) -> None:
    """Mode inspection follows the same commands/graph, without executing them."""
    specification: Any = local_specification()
    specification["checks"]["test-docs"]["modes"] = [mode]
    specification["checks"]["test-docs"]["dependencies"] = ["lint"]
    specification["checks"]["lint"]["modes"] = ["commit", "full", mode]
    # Runtime remains unrelated even though its path group exists. No path is
    # invented to activate qualification, and no recipe or tool is executed.
    path = write_local(tmp_path, specification)
    result = subprocess.run([str(native_selector), str(path), "--platform", "linux", mode], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    actual = json.loads(result.stdout)
    assert actual["selected_jobs"] == ["lint", "test-docs"]
    assert actual["matched_groups"] == [] and actual["unmatched_src"] is False
    assert {row["check"] for row in actual["selected_reasons"]} == {"lint", "test-docs"}
    assert {tuple(row[key] for key in ("check", "kind", "reference")) for row in actual["selected_reasons"]} == {
        ("lint", "mode", mode),
        ("test-docs", "mode", mode),
        ("lint", "dependency", "test-docs"),
    }
    assert actual["target_checked"] is True and actual["requested_platform"] == "linux"
    assert actual["selection_only"] is True and actual["validation_performed"] is False and actual["execution_supported"] is False


@pytest.mark.parametrize("mode", ["platform", "release", "package", "docs"])
def test_python_qualification_mode_preserves_the_same_declared_roster(mode: str) -> None:
    from scripts.ci.gate_selection import router_from_local_document

    specification: Any = local_specification()
    specification["checks"]["test-docs"]["modes"] = [mode]
    specification["checks"]["test-docs"]["dependencies"] = ["lint"]
    specification["checks"]["lint"]["modes"] = ["commit", "full", mode]
    selected = select_gates([], router=router_from_local_document(specification), mode=mode)
    assert selected.selected_jobs == {"lint", "test-docs"}
    assert selected.matched_groups == frozenset() and selected.unmatched_src is False


@pytest.mark.parametrize("mode", ["platform", "release", "package", "docs", "unqualified"])
def test_python_qualification_mode_refuses_unmapped_current_requirements(mode: str) -> None:
    with pytest.raises(ValueError, match="mode|applicable|Unbound workflow context"):
        select_gates([], mode=mode)


@pytest.mark.parametrize("fault", ["mode", "cycle", "paths", "edge"])
def test_python_qualification_mode_preserves_required_dependency_refusal(fault: str) -> None:
    from scripts.ci.gate_selection import router_from_local_document

    specification: Any = local_specification()
    specification["checks"]["test-docs"]["modes"] = ["docs"]
    specification["checks"]["test-docs"]["dependencies"] = ["lint"]
    specification["checks"]["lint"]["modes"] = ["commit"] if fault == "mode" else ["docs"]
    if fault == "cycle":
        specification["checks"]["lint"]["dependencies"] = ["test-docs"]
    elif fault == "edge":
        specification["checks"]["lint"]["dependencies"] = ["missing"]
    with pytest.raises(ValueError, match="mode|cycle|dependencies"):
        select_gates(["docs/operator.md"] if fault == "paths" else [], router=router_from_local_document(specification), mode="docs")


@pytest.mark.parametrize("field", ["modes", "dependencies"])
def test_python_qualification_mode_refuses_malformed_declarations(field: str) -> None:
    from scripts.ci.gate_selection import router_from_local_document

    specification: Any = local_specification()
    specification["checks"]["lint"][field] = ["unqualified"]
    with pytest.raises(ValueError, match="modes|dependencies"):
        router_from_local_document(specification)


def test_native_qualification_mode_refuses_missing_check_definitions(tmp_path: Path, native_selector: Path) -> None:
    specification: Any = local_specification()
    del specification["checks"]
    result = subprocess.run([str(native_selector), str(write_local(tmp_path, specification)), "docs"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and result.stdout == ""
    assert "MissingCheck" in result.stderr


@pytest.mark.parametrize("mode", ["platform", "release", "package", "docs"])
def test_native_qualification_mode_refuses_empty_current_recipe_roster(native_selector: Path, mode: str) -> None:
    """Missing current recipes or their genuine context cannot qualify a mode."""
    authority = Path(__file__).resolve().parents[2] / "tools/validation/gates.json"
    result = subprocess.run([str(native_selector), str(authority), mode], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and result.stdout == ""
    assert ("UnboundWorkflowContext" if mode in {"package", "release"} else "NoApplicableChecks") in result.stderr


@pytest.mark.parametrize("fault", ["mode", "platform", "paths"])
def test_native_qualification_mode_refuses_incompatible_required_work(tmp_path: Path, native_selector: Path, fault: str) -> None:
    specification: Any = local_specification()
    specification["checks"]["test-docs"]["modes"] = ["docs"]
    specification["checks"]["test-docs"]["dependencies"] = ["lint"]
    specification["checks"]["lint"]["modes"] = ["docs"] if fault != "mode" else ["commit"]
    if fault == "platform":
        specification["checks"]["lint"]["platforms"] = ["windows"]
    arguments = [str(native_selector), str(write_local(tmp_path, specification)), "--platform", "linux", "docs"]
    if fault == "paths":
        arguments.append("docs/operator.md")
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and result.stdout == ""
    assert ("UnexpectedChangedPaths" if fault == "paths" else "UnavailableRequiredCheck") in result.stderr


@pytest.mark.parametrize("fault", ["platform", "mode", "dependency-platform", "unknown-platform", "missing-platform", "routing-only"])
def test_native_target_refuses_unavailable_required_checks(tmp_path: Path, native_selector: Path, fault: str) -> None:
    specification: Any = local_specification()
    target = "windows"
    if fault == "platform":
        specification["checks"]["test-docs"]["platforms"] = ["linux"]
    elif fault == "mode":
        specification["checks"]["test-docs"]["modes"] = ["full"]
    elif fault == "dependency-platform":
        specification["checks"]["test-docs"]["dependencies"] = ["test-runtime"]
        specification["checks"]["test-runtime"]["platforms"] = ["linux"]
    elif fault == "unknown-platform":
        target = "unqualified"
    elif fault == "missing-platform":
        del specification["checks"]["lint"]["platforms"]
    else:
        del specification["checks"]
    result = subprocess.run(
        [str(native_selector), str(write_local(tmp_path, specification)), "--platform", target, "commit", "docs/operator.md"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0 and result.stdout == ""
    assert "selection refused" in result.stderr


@pytest.mark.parametrize("mode", ["pr", "full"])
def test_native_target_preserves_preview_roster(tmp_path: Path, native_selector: Path, mode: str) -> None:
    specification: Any = local_specification()
    specification["checks"]["lint"]["platforms"] = ["all"]
    path = write_local(tmp_path, specification)
    preview = subprocess.run([str(native_selector), str(path), mode, "docs/operator.md"], check=True, capture_output=True, text=True, timeout=20)
    target = subprocess.run(
        [str(native_selector), str(path), "--platform", "windows", mode, "docs/operator.md"], check=True, capture_output=True, text=True, timeout=20
    )
    before, after = json.loads(preview.stdout), json.loads(target.stdout)
    assert before["selected_jobs"] == after["selected_jobs"]
    assert before["selected_reasons"] == after["selected_reasons"]
    assert after["target_checked"] is True and after["validation_performed"] is False


def test_native_missing_explicit_target_refuses_before_selection(tmp_path: Path, native_selector: Path) -> None:
    result = subprocess.run([str(native_selector), str(write_local(tmp_path, local_specification())), "--platform"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and result.stdout == ""
    assert "InvalidArguments" in result.stderr


def test_native_preview_keeps_option_like_git_paths_literal(tmp_path: Path, native_selector: Path) -> None:
    path = write_local(tmp_path, local_specification())
    paths = ["--platform", "windows", "docs/operator.md"]
    expected = select_gates(paths, router=load_router(path))
    result = subprocess.run([str(native_selector), str(path), "pr", *paths], check=True, capture_output=True, text=True, timeout=20)
    actual = json.loads(result.stdout)
    assert actual["selected_jobs"] == sorted(expected.selected_jobs)
    assert actual["target_checked"] is False


def packs_source_selection(paths: list[str], mode: str) -> set[str]:
    """Derive the independent Packs oracle from its actual source predicates."""
    import fnmatch
    import re
    from scripts.ci.corpus_select import corpus_selected

    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/packs.yml").read_text())
    filters = next(yaml.safe_load(step["with"]["filters"]) for step in workflow["jobs"]["changes"]["steps"] if "dorny/paths-filter" in step.get("uses", ""))
    selected = {name for name, patterns in filters.items() if mode == "full" or any(fnmatch.fnmatch(path, pattern) for path in paths for pattern in patterns)}
    if corpus_selected(paths, router=load_router(root / ".github/workflows/ci-router.yml"), mode=mode):
        selected.add("corpus")
    result = set()
    for name, job in workflow["jobs"].items():
        if name == "changes":
            continue
        groups = set(re.findall(r"needs\.changes\.outputs\.([a-z_]+)", job.get("if", "")))
        if not groups or groups & selected:
            result.add(name)
    return result


@pytest.mark.parametrize(
    ("paths", "mode"),
    [
        (["packs/built-in/profiles/fixture.md"], "pr"),
        (["packs/internal/profiles/fixture.md"], "pr"),
        (["tests/doctrine/fixture.py"], "pr"),
        (["src/charter/offering/schemas/fixture.py"], "pr"),
        (["src/unmapped/new.py"], "pr"),
        (["docs/fixture.md"], "pr"),
        ([], "full"),
    ],
)
def test_canonical_native_and_python_preserve_packs_selection(tmp_path: Path, native_selector: Path, paths: list[str], mode: str) -> None:
    root = Path(__file__).resolve().parents[2]
    authority = root / "tools/validation/gates.json"
    jobs = set(yaml.safe_load((root / ".github/workflows/packs.yml").read_text())["jobs"]) - {"changes"}
    expected = packs_source_selection(paths, mode)
    python_actual = select_gates(paths, router=load_router(authority), mode=mode)
    result = subprocess.run([str(native_selector), str(authority), mode, *paths], check=True, capture_output=True, text=True, timeout=20)
    native_actual = json.loads(result.stdout)
    assert set(native_actual["selected_jobs"]) & jobs == expected
    assert python_actual.selected_jobs & jobs == expected
    assert not set(native_actual["selected_code_shards"]) & jobs
    assert not python_actual.selected_code_shards & jobs
    assert native_actual["execution_supported"] is False


@pytest.mark.parametrize(
    ("stderr", "allowed"),
    [
        ("", True),
        ("ordinary diagnostic\n", True),
        ("Warning: missing validator\n", False),
        ("wArNiNg: strict validation skipped\n", False),
        ("ok\nWarning: source warning\n", False),
        (" Warning: not a line prefix\n", True),
    ],
)
def test_native_warning_output_guard_is_not_validator_execution(tmp_path: Path, native_selector: Path, stderr: str, allowed: bool) -> None:
    specification: Any = local_specification()
    specification["checks"]["lint"]["stderr_policy"] = ["reject-warning-prefix"]
    authority = write_local(tmp_path, specification)
    result = subprocess.run([str(native_selector), str(authority), "output-policy", "lint", "0"], input=stderr, capture_output=True, text=True, timeout=20)
    assert result.returncode == (0 if allowed else 1)
    assert json.loads(result.stdout) == {"policy_allows_output": allowed, "check_validation_performed": False, "execution_supported": False}
    assert stderr not in result.stdout if stderr else True


def test_packs_recipe_has_genuine_source_guard_and_advisory_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    specification = json.loads((root / "tools/validation/gates.json").read_text())
    checks = specification["checks"]
    jobs = yaml.safe_load((root / ".github/workflows/packs.yml").read_text())["jobs"]
    assert set(jobs) - {"changes"} <= set(checks)
    for name in set(jobs) - {"changes"}:
        assert checks[name]["recipe"]["source"]["sha256"] == fixture_digest((root / ".github/workflows/packs.yml").read_bytes())
        assert checks[name]["budgets"]["wall_ms"] == jobs[name]["timeout-minutes"] * 60000
    assert checks["built-in-corpus-suite"]["recipe"]["advisory"] is True
    assert checks["built-in-plugin-validate"]["stderr_policy"] == ["allow", "reject-warning-prefix"]
    assert "claude_cli_2_1_270" in checks["built-in-plugin-validate"]["recipe"]["required_inputs"]
    assert checks["packs-gate"]["dependencies"] == []
    assert checks["packs-gate"]["recipe"]["observed_dependencies"] == jobs["packs-gate"]["needs"]
    assert "built-in-corpus-suite" not in checks["packs-gate"]["recipe"]["observed_dependencies"]


@pytest.mark.parametrize("fault", ["code-optout", "unknown-data-group", "duplicate-data-group", "nonboolean-optout"])
def test_native_and_python_refuse_weakened_code_selection(tmp_path: Path, native_selector: Path, fault: str) -> None:
    specification: Any = local_specification()
    specification["routing"]["non_source_groups"] = []
    if fault == "code-optout":
        specification["checks"]["test-runtime"]["unmatched_source"] = False
    elif fault == "unknown-data-group":
        specification["routing"]["non_source_groups"] = ["foreign"]
    elif fault == "duplicate-data-group":
        specification["routing"]["non_source_groups"] = ["docs", "docs"]
    else:
        specification["checks"]["test-runtime"]["unmatched_source"] = "false"
    path = write_local(tmp_path, specification)
    with pytest.raises(ValueError, match="routing"):
        load_router(path)
    result = subprocess.run([str(native_selector), str(path), "pr", "src/unmapped/file.py"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and result.stdout == ""


@pytest.mark.parametrize(
    "fault", ["missing-index", "unknown-check", "negative-index", "index-overflow", "quota", "unknown-policy", "missing-policy-row", "zero-quota"]
)
def test_native_output_policy_refuses_unbound_or_overflowing_input(tmp_path: Path, native_selector: Path, fault: str) -> None:
    specification: Any = local_specification()
    check = specification["checks"]["lint"]
    check["stderr_policy"] = ["reject-warning-prefix"]
    name, index, data = "lint", "0", "ordinary"
    if fault == "unknown-check":
        name = "foreign"
    elif fault == "negative-index":
        index = "-1"
    elif fault == "index-overflow":
        index = "99999999999999999999999999999999"
    elif fault == "quota":
        check["budgets"]["stderr_bytes"] = 4
    elif fault == "unknown-policy":
        check["stderr_policy"] = ["invented"]
    elif fault == "missing-policy-row":
        check["stderr_policy"] = []
    elif fault == "zero-quota":
        check["budgets"]["stderr_bytes"] = 0
    args = [str(native_selector), str(write_local(tmp_path, specification)), "output-policy", name, index]
    if fault == "missing-index":
        args.pop()
    result = subprocess.run(args, input=data, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and result.stdout == ""
    assert data not in result.stderr


@pytest.mark.parametrize(
    ("data", "allowed"),
    [
        ("Warning: example\n", False),
        ("warning: example\r\n", False),
        ("embedded Warning: example\n", True),
        ("\nWARNING: example\n", False),
        ("diagnostic without a final newline", True),
    ],
)
def test_native_warning_policy_matches_pinned_ascii_grep_rule(tmp_path: Path, native_selector: Path, data: str, allowed: bool) -> None:
    specification: Any = local_specification()
    specification["checks"]["lint"]["stderr_policy"] = ["reject-warning-prefix"]
    authority = write_local(tmp_path, specification)
    oracle = subprocess.run(["/usr/bin/grep", "-qi", "^Warning:"], input=data, capture_output=True, text=True, timeout=20)
    assert (oracle.returncode != 0) == allowed
    result = subprocess.run([str(native_selector), str(authority), "output-policy", "lint", "0"], input=data, capture_output=True, text=True, timeout=20)
    assert json.loads(result.stdout)["policy_allows_output"] is allowed


@pytest.mark.parametrize("consumer", ["python", "native"])
@pytest.mark.parametrize("mode", ["pr", "commit"])
@pytest.mark.parametrize(
    "paths",
    [
        ["future-native/worker.zig"],
        ["docs/guide.md", "future-native/worker.zig"],
        ["tools/zig/validation_selection.zig"],
        ["future-native/odd\nname.zig"],
        [".github/CODEOWNERS"],
    ],
)
def test_canonical_unknown_surface_refuses_instead_of_always_on_preview(native_selector: Path, consumer: str, mode: str, paths: list[str]) -> None:
    """Unmapped non-src work cannot silently credit only the always-on roster."""
    authority = Path(__file__).resolve().parents[2] / "tools/validation/gates.json"
    if consumer == "python":
        with pytest.raises(ValueError, match="Unsupported changed surface"):
            select_gates(paths, router=load_router(authority), mode=mode)
    else:
        result = subprocess.run([str(native_selector), str(authority), mode, *paths], capture_output=True, text=True, timeout=20)
        assert result.returncode != 0 and result.stdout == ""
        assert "UnsupportedChangedSurface" in result.stderr


@pytest.mark.parametrize("paths", [["scripts/ci/gate_selection.py"], ["src/new/unmapped.py"], ["docs/guide.md", "src/new/unmapped.py"]])
def test_canonical_known_or_conservative_source_path_remains_supported(native_selector: Path, paths: list[str]) -> None:
    authority = Path(__file__).resolve().parents[2] / "tools/validation/gates.json"
    expected = select_gates(paths, router=load_router(authority))
    result = subprocess.run([str(native_selector), str(authority), "pr", *paths], check=True, capture_output=True, text=True, timeout=20)
    assert json.loads(result.stdout)["selected_jobs"] == sorted(expected.selected_jobs)


def test_explicit_full_inspection_remains_conservative_for_unknown_surface(native_selector: Path) -> None:
    authority = Path(__file__).resolve().parents[2] / "tools/validation/gates.json"
    paths = ["future-native/worker.zig"]
    expected = select_gates(paths, router=load_router(authority), mode="full")
    result = subprocess.run([str(native_selector), str(authority), "full", *paths], check=True, capture_output=True, text=True, timeout=20)
    actual = json.loads(result.stdout)
    assert set(actual["selected_jobs"]) == set(json.loads(authority.read_text())["checks"])
    assert actual["selected_jobs"] == sorted(expected.selected_jobs)
    assert actual["execution_supported"] is False


@pytest.mark.parametrize("policy", [None, "accept-always-on", ["refuse-path-sensitive"]])
def test_schema_four_refuses_missing_or_weakened_unknown_policy(tmp_path: Path, native_selector: Path, policy: object) -> None:
    authority: Any = json.loads((Path(__file__).resolve().parents[2] / "tools/validation/gates.json").read_text())
    if policy is None:
        authority["routing"].pop("unknown_surface_policy")
    else:
        authority["routing"]["unknown_surface_policy"] = policy
    path = write_local(tmp_path, authority)
    with pytest.raises(ValueError, match="unknown-surface routing policy"):
        load_router(path)
    result = subprocess.run([str(native_selector), str(path), "pr", "docs/guide.md"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and result.stdout == ""
    assert "InvalidRouting" in result.stderr


@pytest.mark.parametrize("field", ["non_source_groups", "stderr_policy"])
def test_schema_four_missing_required_native_binding_refuses(tmp_path: Path, native_selector: Path, field: str) -> None:
    authority: Any = json.loads((Path(__file__).resolve().parents[2] / "tools/validation/gates.json").read_text())
    if field == "non_source_groups":
        authority["routing"].pop(field)
    else:
        next(iter(authority["checks"].values())).pop(field)
    result = subprocess.run([str(native_selector), str(write_local(tmp_path, authority)), "pr", "docs/guide.md"], capture_output=True, text=True, timeout=20)
    assert result.returncode != 0 and result.stdout == ""
    assert ("InvalidRouting" if field == "non_source_groups" else "InvalidChecks") in result.stderr


def test_partial_classification_cannot_replace_complete_surface_selection() -> None:
    from scripts.ci.gate_selection import classify_paths

    router = load_router()
    assert classify_paths(["future-native/worker.zig"], router=router) == (frozenset(), False)
    with pytest.raises(ValueError, match="Unsupported changed surface"):
        select_gates(["future-native/worker.zig"], router=router)
    assert classify_paths(["src/new/unmapped.py"], router=router)[1] is True


@pytest.mark.parametrize(("name", "commands"), [("python-checks", 11), ("validate-bundle", 5), ("resolver-parity", 2), ("negative-tests", 3)])
def test_contract_command_program_preserves_complete_source_control(name: str, commands: int) -> None:
    authority = json.loads((Path(__file__).resolve().parents[2] / "tools/validation/gates.json").read_text())
    contract = next(row for row in authority["workflow_contracts"] if row["id"] == "contracts")
    program = contract["jobs"][name].get("program")
    assert isinstance(program, dict) and program.get("status") == "normalized"
    assert len(program["argv"]) == commands
    assert program["context_required"] is True
    if name == "python-checks":
        assert program["controls"] == [
            {"step": 2, "start": 0, "count": 1, "failure": "fail-fast"},
            {"step": 3, "start": 1, "count": 10, "failure": "collect-failures"},
        ]
        assert [argv[-1] for argv in program["argv"][1:]] == [
            "contracts/tools/" + filename + ".py"
            for filename in [
                "layout_check",
                "citation_check",
                "provisional_check",
                "example_check",
                "event_mapping_check",
                "enum_pin_check",
                "leak_scan",
                "structure_check",
                "codeowners_check",
                "no_pytest_scan",
            ]
        ]
    else:
        assert all(row["failure"] == "fail-fast" for row in program["controls"])
        assert {row["variable"] for row in program["argument_bindings"]} == ({"RUNNER_TEMP"} if name == "negative-tests" else {"RUNNER_TEMP", "CONTRACTS_ROOT"})


def test_native_inspects_source_command_program_without_granting_context(native_selector: Path) -> None:
    authority = Path(__file__).resolve().parents[2] / "tools/validation/gates.json"
    result = subprocess.run([str(native_selector), str(authority), "inspect-program", "contracts.python-checks"], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    inspected = json.loads(result.stdout)
    assert inspected["program"]["controls"][-1]["failure"] == "collect-failures"
    assert inspected["workflow_context_complete"] is False and inspected["execution_supported"] is False


def test_native_binds_actual_process_environment_without_execution(tmp_path: Path, native_selector: Path) -> None:
    authority = Path(__file__).resolve().parents[2] / "tools/validation/gates.json"
    environment = os.environ | {"RUNNER_TEMP": str(tmp_path), "CONTRACTS_ROOT": "contracts"}
    result = subprocess.run(
        [str(native_selector), str(authority), "bind-program-environment", "contracts.validate-bundle"], env=environment, capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
    inspected = json.loads(result.stdout)
    assert inspected["argv"][1][-3] == str(tmp_path / "tools")
    assert inspected["argv"][2][-3] == "contracts"
    assert inspected["argument_binding_only"] is True
    assert inspected["workflow_context_complete"] is False and inspected["execution_supported"] is False


@pytest.mark.parametrize(
    "body",
    [
        "echo ignored",
        "python tool.py $VALUE",
        'python tool.py "$VALUE"tail',
        'python tool.py "$VALUE/$OTHER"',
        "python tool.py @environment.0",
        "set -u\nstatus=0\npython first.py || status=1\npython second.py\nexit $status",
        "set -u\nstatus=0\npython first.py || status=2\nexit $status",
    ],
)
def test_program_normalization_refuses_different_shell_control(body: str) -> None:
    from scripts.validation.extract_gates import _step_program

    assert _step_program(body) is None


@pytest.mark.parametrize(
    "body",
    [
        "python one.py\npython two.py",
        "set -euo pipefail\npython one.py\npython two.py",
        "set -u\nstatus=0\npython one.py || status=1\npython two.py || status=1\nexit $status",
    ],
)
def test_program_normalization_preserves_failure_class_and_order(body: str) -> None:
    from scripts.validation.extract_gates import _step_program

    result = _step_program(body)
    assert result is not None
    commands, arguments, failure = result
    assert commands == [["python", "one.py"], ["python", "two.py"]] and arguments == []
    assert failure == ("collect-failures" if "status=0" in body else "fail-fast")


def test_every_source_job_has_deterministic_program_or_exact_refusal() -> None:
    from scripts.validation.extract_gates import _workflow_program

    authority = json.loads((Path(__file__).resolve().parents[2] / "tools/validation/gates.json").read_text())
    for contract in authority["workflow_contracts"]:
        for name, mapping in contract["jobs"].items():
            assert mapping["program"] == _workflow_program(contract["definition"]["jobs"][name])
            assert mapping["binding_required"] is True and mapping["program"]["context_required"] is True
    contracts = next(row for row in authority["workflow_contracts"] if row["id"] == "contracts")
    assert authority["checks"]["contracts.validate-bundle"]["dependencies"] == ["contracts.verify-pins"]
    assert authority["checks"]["contracts.resolver-parity"]["dependencies"] == ["contracts.validate-bundle"]
    assert contracts["jobs"]["contracts-gate"]["program"]["status"] == "unsupported"


@pytest.mark.parametrize(
    ("subject", "variables", "error"),
    [
        ("contracts.validate-bundle", {"CONTRACTS_ROOT": "contracts"}, "MissingEnvironmentBinding"),
        ("contracts.validate-bundle", {"RUNNER_TEMP": "/private/synthetic", "CONTRACTS_ROOT": "other"}, "EnvironmentBindingMismatch"),
        ("ci-fleet-verdict.identify", {"REPORT_REPOSITORY": "private-credential-body"}, "UnboundEnvironmentVariable"),
        ("contracts.contracts-gate", {}, "UnsupportedWorkflowProgram"),
        ("unrecognized.job", {}, "MissingWorkflowProgram"),
    ],
)
def test_actual_environment_program_binding_refuses_incomplete_or_unauthorized_context(
    native_selector: Path, subject: str, variables: dict[str, str], error: str
) -> None:
    authority = Path(__file__).resolve().parents[2] / "tools/validation/gates.json"
    environment = {key: value for key, value in os.environ.items() if key not in {"RUNNER_TEMP", "CONTRACTS_ROOT"}}
    environment.update(variables)
    result = subprocess.run(
        [str(native_selector), str(authority), "bind-program-environment", subject], env=environment, capture_output=True, text=True, timeout=20
    )
    assert result.returncode != 0 and result.stdout == "" and error in result.stderr
    assert "private-credential-body" not in result.stderr


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "status",
        "context",
        "step",
        "count",
        "failure",
        "binding-command",
        "binding-executable",
        "binding-variable",
        "duplicate-binding",
        "orphan-marker",
        "unknown-field",
    ],
)
def test_native_program_catalog_refuses_malformed_control_or_argument_binding(tmp_path: Path, native_selector: Path, fault: str) -> None:
    authority = json.loads((Path(__file__).resolve().parents[2] / "tools/validation/gates.json").read_text())
    contract = next(row for row in authority["workflow_contracts"] if row["id"] == "contracts")
    mapping = contract["jobs"]["validate-bundle"]
    program = mapping["program"]
    if fault == "missing":
        del mapping["program"]
    elif fault == "status":
        program["status"] = "accepted"
    elif fault == "context":
        program["context_required"] = False
    elif fault == "step":
        program["controls"][0]["step"] = -1
    elif fault == "count":
        program["controls"][0]["count"] = 0
    elif fault == "failure":
        program["controls"][0]["failure"] = "ignore"
    elif fault == "binding-command":
        program["argument_bindings"][0]["command"] = 999
    elif fault == "binding-executable":
        program["argument_bindings"][0]["argument"] = 0
    elif fault == "binding-variable":
        program["argument_bindings"][0]["variable"] = "BAD=NAME"
    elif fault == "duplicate-binding":
        program["argument_bindings"].append(program["argument_bindings"][0].copy())
    elif fault == "orphan-marker":
        program["argument_bindings"] = []
    elif fault == "argv-crosslink":
        authority["checks"]["contracts.validate-bundle"]["argv"][0][-1] = "--unreviewed"
    else:
        program["unrecognized"] = True
    result = subprocess.run(
        [str(native_selector), str(write_local(tmp_path, authority)), "inspect-program", "contracts.validate-bundle"], capture_output=True, text=True, timeout=20
    )
    assert result.returncode != 0 and result.stdout == "" and "selection refused" in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="Actual Bash source semantics need a Bash platform; Windows remains unqualified")
@pytest.mark.parametrize("collect", [False, True])
def test_normalized_failure_class_matches_actual_bash_control(tmp_path: Path, collect: bool) -> None:
    import shlex
    from scripts.validation.extract_gates import _step_program

    marker = tmp_path / "second command completed"
    command = "touch " + shlex.quote(str(marker))
    body = "set -u\nstatus=0\nfalse || status=1\n" + command + " || status=1\nexit $status" if collect else "false\n" + command
    # The source grammar refuses shell builtins; use actual external tools in
    # both source and inspection without introducing an execution engine.
    body = body.replace("false", "/usr/bin/false").replace("touch ", "/usr/bin/touch ")
    program = _step_program(body)
    assert program is not None and program[2] == ("collect-failures" if collect else "fail-fast")
    result = subprocess.run(["/bin/bash", "-e", "-c", body], capture_output=True, text=True, timeout=5)
    assert result.returncode == 1 and marker.exists() is collect


@pytest.mark.parametrize("fault", ["source-expression", "required-source-env", "oversized-variable"])
def test_program_actual_environment_rejects_unbound_values(tmp_path: Path, native_selector: Path, fault: str) -> None:
    authority = json.loads((Path(__file__).resolve().parents[2] / "tools/validation/gates.json").read_text())
    contract = next(row for row in authority["workflow_contracts"] if row["id"] == "contracts")
    environment = os.environ | {"RUNNER_TEMP": str(tmp_path), "CONTRACTS_ROOT": "contracts"}
    expected = "UnboundEnvironmentExpression"
    if fault == "source-expression":
        contract["definition"]["env"]["CONTRACTS_ROOT"] = "${{ secrets.SYNTHETIC }}"
    elif fault == "required-source-env":
        environment.pop("CONTRACTS_ROOT")
        expected = "MissingEnvironmentBinding"
    else:
        environment["RUNNER_TEMP"] = "a" * 4097
        expected = "InputLimit"
    result = subprocess.run(
        [str(native_selector), str(write_local(tmp_path, authority)), "bind-program-environment", "contracts.validate-bundle"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode != 0 and result.stdout == "" and expected in result.stderr
