"""Input-bound evidence controls; actual execution/reuse controls follow binding."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.local_validation.test_candidate import ROOT, capture, digest, git, require_candidate_capture_profile, snapshot
from tests.local_validation.test_candidate import candidate_binary as candidate_binary
from tests.local_validation.test_candidate import repository as repository

SOURCE = ROOT / "tools/zig/validation_receipt.zig"
CANDIDATE_SOURCE = ROOT / "tools/zig/validation_candidate.zig"
NATIVE_SOURCES = [
    ROOT / "tools/zig" / name
    for name in [
        "validation_candidate.zig",
        "validation_receipt.zig",
        "validation_execution.zig",
        "validation_selection.zig",
        "validation_process_darwin.zig",
        "validation_changelog.zig",
        "validation_unicode14.zig",
        "validation_memory_sampler.zig",
        "validation_sampler_lifetime.zig",
    ]
]


def retain_native_build_metadata(image: Path, sources: list[Path], argv: list[str], completed: subprocess.CompletedProcess[bytes]) -> None:
    # Existing pytest --basetemp and tmp_path_retention_policy controls retain
    # these ordinary build artifacts when the validation caller requests it.
    target = image.parent
    for source in sources:
        destination = target / source.name
        if source.resolve() != destination.resolve():
            shutil.copyfile(source, destination)
    (target / "build.stdout.log").write_bytes(completed.stdout)
    (target / "build.stderr.log").write_bytes(completed.stderr)
    (target / "build.json").write_bytes(
        canonical({"argv": argv, "exit_code": completed.returncode, "image": file_pin(image), "sources": [file_pin(path) for path in sources]})
    )


@pytest.fixture(scope="session")
def receipt_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    assert SOURCE.is_file(), "Receipt module is absent; this setup failure is not binding or reuse proof"
    binding_name = os.environ.get("SPEC_KITTY_NATIVE_RECEIPT_BINDING")
    if binding_name:
        binding = json.loads(Path(binding_name).read_text())
        for name, expected in binding["sources"].items():
            assert digest((ROOT / name).read_bytes()) == expected
        image = Path(binding["image"])
        assert digest(image.read_bytes()) == binding["image_sha256"]
        return image
    image = tmp_path_factory.mktemp("native-receipt") / "receipt"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(SOURCE), "-femit-bin=" + str(image)]
    compiled = subprocess.run(argv, check=True, capture_output=True, timeout=90)
    retain_native_build_metadata(image, NATIVE_SOURCES, argv, compiled)
    return image


def receipt_call(binary: Path, operation: str, path: Path, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([str(binary), operation, str(path)], env=environment, capture_output=True, timeout=40)


@pytest.fixture
def bound_inputs(candidate_binary: Path, receipt_binary: Path, repository: Path, tmp_path: Path) -> dict[str, Any]:
    require_candidate_capture_profile()
    tools = repository / "tools/zig"
    tools.mkdir(parents=True)
    for source in NATIVE_SOURCES:
        shutil.copyfile(source, tools / source.name)
    launcher = repository / "launcher.sh"
    launcher.write_text('#!/bin/sh\nexec "$WP02_NATIVE_RECEIPT" verify "$WP02_BINDING"\n')
    authority = repository / "gates.json"
    authority.write_text(json.dumps({"schema_version": 6, "fixture": "bounded inert check; not a production authority qualification"}))
    lock = repository / "dependencies.lock"
    lock.write_text("fixture-dependency=good\n")
    observed = tmp_path / "observed-dependency"
    observed.write_text("good\n")
    package = repository / "src/staged_package"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 'PASS'\n")
    (repository / "import_validator.py").write_text("from staged_package import VALUE\nimport sys\nprint(VALUE)\nsys.exit(0 if VALUE == 'PASS' else 7)\n")
    git(repository, "add", "--all")
    response, capture_request = capture(candidate_binary, repository, tmp_path)
    assert response.returncode == 0, response.stderr
    manifest_path = Path(capture_request["destination"]) / "candidate.json"
    bindings: list[dict[str, Any]] = []
    for role, path in [
        ("launcher", launcher),
        ("specification", authority),
        *(("native_source", tools / source.name) for source in NATIVE_SOURCES),
        ("dependency_lock", lock),
    ]:
        bindings.append({"role": role, "path": str(path), "candidate_path_hex": os.fsencode(path.relative_to(repository)).hex()})
    bindings.extend(
        [
            {"role": "toolchain", "path": sys.executable, "candidate_path_hex": None},
            {"role": "observed_dependency", "path": str(observed), "candidate_path_hex": None},
        ]
    )
    request = {
        "schema_version": 1,
        "candidate_manifest": str(manifest_path),
        "files": bindings,
        "environment_names": ["WP02_FLAG"],
        "checks": [
            {"id": "inert", "argv": [[sys.executable, "-I", "-S", "-B", "validator.py"]], "closure_proof": None},
            {"id": "import", "argv": [[sys.executable, "-I", "-S", "-B", "import_validator.py"]], "closure_proof": None},
        ],
    }
    request_path = tmp_path / "binding-request.json"
    request_path.write_text(json.dumps(request))
    environment = {name: os.environ[name] for name in ["PATH", "HOME", "TMPDIR", "LANG", "LC_ALL"] if name in os.environ}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    environment["WP02_FLAG"] = "fixture value, never raw receipt data"
    before = snapshot(repository)
    result = receipt_call(receipt_binary, "bind", request_path, environment)
    assert snapshot(repository) == before
    assert result.returncode == 0, result.stderr
    binding = json.loads(result.stdout)
    binding_path = tmp_path / "current-binding.json"
    binding_path.write_bytes(result.stdout)
    return {
        "repository": repository,
        "request": request,
        "request_path": request_path,
        "environment": environment,
        "binding": binding,
        "binding_path": binding_path,
        "observed": observed,
        "manifest_path": manifest_path,
    }


def test_actual_native_binding_has_complete_current_identities_and_no_environment_values(receipt_binary: Path, bound_inputs: dict[str, Any]) -> None:
    binding = bound_inputs["binding"]
    assert binding["schema_version"] == 1 and binding["binding_only"] is True and binding["acceptance_performed"] is False
    assert binding["candidate_manifest_sha256"] == digest(bound_inputs["manifest_path"].read_bytes())
    assert binding["native_executable"]["sha256"] == digest(receipt_binary.read_bytes())
    assert {row["role"] for row in binding["files"]} == {"launcher", "specification", "native_source", "toolchain", "dependency_lock", "observed_dependency"}
    assert len(binding["native_sources"]) == len(NATIVE_SOURCES)
    assert "fixture value, never raw receipt data" not in json.dumps(binding)
    result = receipt_call(receipt_binary, "verify", bound_inputs["binding_path"], bound_inputs["environment"])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"binding_current": True, "acceptance_performed": False}


@pytest.mark.parametrize("role", ["launcher", "specification", "native_source", "dependency_lock", "observed_dependency"])
def test_each_actual_file_drift_invalidates_existing_binding(receipt_binary: Path, bound_inputs: dict[str, Any], role: str) -> None:
    row = next(item for item in bound_inputs["request"]["files"] if item["role"] == role)
    path = Path(row["path"])
    path.write_bytes(path.read_bytes() + b"\nchanged input\n")
    before = snapshot(bound_inputs["repository"])
    result = receipt_call(receipt_binary, "verify", bound_inputs["binding_path"], bound_inputs["environment"])
    assert snapshot(bound_inputs["repository"]) == before
    assert result.returncode != 0 and result.stdout == b"" and b"InputDrift" in result.stderr


def test_actual_environment_drift_invalidates_without_leaking_value(receipt_binary: Path, bound_inputs: dict[str, Any]) -> None:
    environment = bound_inputs["environment"].copy()
    environment["WP02_FLAG"] = "new-private-value"
    result = receipt_call(receipt_binary, "verify", bound_inputs["binding_path"], environment)
    assert result.returncode != 0 and b"InputDrift" in result.stderr
    assert b"new-private-value" not in result.stdout + result.stderr


@pytest.mark.parametrize("fault", ["incomplete", "unknown", "global-old", "tampered"])
def test_old_global_or_incomplete_and_tampered_binding_refuses(receipt_binary: Path, bound_inputs: dict[str, Any], tmp_path: Path, fault: str) -> None:
    value = bound_inputs["binding"].copy()
    if fault == "incomplete":
        value.pop("files")
    elif fault == "unknown":
        value["invented_acceptance"] = True
    elif fault == "global-old":
        value = {"schema_version": 0, "passed": True, "tree": bound_inputs["binding"]["candidate_manifest_sha256"]}
    else:
        value["checks"] = []
    path = tmp_path / "invalid-binding.json"
    path.write_text(json.dumps(value))
    result = receipt_call(receipt_binary, "verify", path, bound_inputs["environment"])
    assert result.returncode != 0 and result.stdout == b"" and result.stderr


@pytest.mark.parametrize(("staged", "live", "expected"), [("FAIL", "PASS", 7), ("PASS", "FAIL", 0)])
def test_actual_imports_use_staged_package_with_live_editable_path_trap(
    candidate_binary: Path, receipt_binary: Path, bound_inputs: dict[str, Any], tmp_path: Path, staged: str, live: str, expected: int
) -> None:
    repo = bound_inputs["repository"]
    package = repo / "src/staged_package/__init__.py"
    package.write_text(f"VALUE = {staged!r}\n")
    git(repo, "add", "src/staged_package/__init__.py")
    result, request = capture(candidate_binary, repo, tmp_path, destination=str(tmp_path / "import candidate"))
    assert result.returncode == 0, result.stderr
    request_path = bound_inputs["request_path"]
    binding_request = bound_inputs["request"].copy()
    binding_request["candidate_manifest"] = str(Path(request["destination"]) / "candidate.json")
    request_path.write_text(json.dumps(binding_request))
    result = receipt_call(receipt_binary, "bind", request_path, bound_inputs["environment"])
    assert result.returncode == 0, result.stderr
    bound_inputs["binding_path"].write_bytes(result.stdout)
    package.write_text(f"VALUE = {live!r}\n")
    environment = bound_inputs["environment"].copy()
    environment["PYTHONPATH"] = str(repo / "src")
    before = snapshot(repo)
    if os.environ.get("SPEC_KITTY_IMPORT_MIGRATION_ORACLE") == "direct-live-import":
        # Historical command, explicitly selected only for retained paired RED.
        argv = [sys.executable, "-B", str(repo / "import_validator.py")]
        cwd = repo
    else:
        plan_path = tmp_path / "python-plan-request.json"
        plan_path.write_text(json.dumps({"binding": str(bound_inputs["binding_path"]), "check_id": "import"}))
        plan = receipt_call(receipt_binary, "python-plan", plan_path, environment)
        assert plan.returncode == 0, plan.stderr
        value = json.loads(plan.stdout)
        assert value["execution_performed"] is False and value["dependency_context"] == "isolated-stdlib-and-candidate"
        argv, cwd = value["argv"], value["cwd"]
    observed = subprocess.run(argv, cwd=cwd, env=environment, capture_output=True, timeout=20)
    assert snapshot(repo) == before
    assert observed.returncode == expected, (observed.stdout, observed.stderr)
    assert observed.stdout == (staged + "\n").encode()


def test_isolated_python_plan_preserves_script_argv_including_empty_argument(
    candidate_binary: Path, receipt_binary: Path, bound_inputs: dict[str, Any], tmp_path: Path
) -> None:
    repo = bound_inputs["repository"]
    (repo / "argv_validator.py").write_text("import json,sys\nprint(json.dumps(sys.argv))\n")
    git(repo, "add", "argv_validator.py")
    captured, request = capture(candidate_binary, repo, tmp_path, destination=str(tmp_path / "argv candidate"))
    assert captured.returncode == 0, captured.stderr
    arguments = ["", "space value", "tab\tline\n"]
    value = bound_inputs["request"].copy()
    value["candidate_manifest"] = str(Path(request["destination"]) / "candidate.json")
    value["checks"] = [{"id": "argv", "argv": [[sys.executable, "-I", "-S", "-B", "argv_validator.py", *arguments]], "closure_proof": None}]
    bound_inputs["request_path"].write_text(json.dumps(value))
    result = receipt_call(receipt_binary, "bind", bound_inputs["request_path"], bound_inputs["environment"])
    assert result.returncode == 0, result.stderr
    bound_inputs["binding_path"].write_bytes(result.stdout)
    plan_request = tmp_path / "argv-plan-request.json"
    plan_request.write_text(json.dumps({"binding": str(bound_inputs["binding_path"]), "check_id": "argv"}))
    result = receipt_call(receipt_binary, "python-plan", plan_request, bound_inputs["environment"])
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    actual = subprocess.run(plan["argv"], cwd=plan["cwd"], env=bound_inputs["environment"], capture_output=True, timeout=20)
    assert actual.returncode == 0, actual.stderr
    assert json.loads(actual.stdout) == ["argv_validator.py", *arguments]


# Committed harness source: imports only the exact pinned test fixture in its
# temporary build directory. It is not an installed or production supervisor.
PRODUCER_SOURCE = (
    "//! External WP02 evidence fixture, using the unchanged reviewed owner.\n"
    'const std = @import("std");\n'
    'const owned = @import("owned_process_group.zig");\n'
    "const Request = struct { argv: []const []const u8, cwd: []const u8, environment_names: []const []const u8"
    ", limits: owned.Limits, binding_sha256: []const u8, check_id: []const u8, run_id: []const u8 };\n"
    "const Environment = struct { name: []const u8, present: bool, sha256: ?[]const u8 };\n"
    "const RuntimeFile = struct { path: []const u8, resolved: []const u8, sha256: []const u8, mode: u32 };\n"
    "const Runtime = struct { schema_version: u8, interpreter: []const u8, files: []const RuntimeFile, scope: "
    "[]const u8 };\n"
    "fn hash(allocator: std.mem.Allocator, bytes: []const u8) ![]const u8 {\n"
    "    var digest: [32]u8 = undefined;\n"
    "    std.crypto.hash.sha2.Sha256.hash(bytes, &digest, .{});\n"
    "    return allocator.dupe(u8, &std.fmt.bytesToHex(digest, .lower));\n"
    "}\n"
    "pub fn main(init: std.process.Init) !void {\n"
    "    const allocator = init.arena.allocator();\n"
    "    const args = try init.minimal.args.toSlice(allocator);\n"
    "    if (args.len != 2) return error.InvalidArguments;\n"
    "    const raw = try std.Io.Dir.cwd().readFileAlloc(init.io, args[1], allocator, .limited(65536));\n"
    "    const request = (try std.json.parseFromSlice(Request, allocator, raw, .{ .duplicate_field_behavior = "
    '.@"error" })).value;\n'
    "    // This fixture qualifies precisely one source-closed, non-spawning program.\n"
    "    // Arbitrary argv and arbitrary source cannot inherit its cleanup meaning.\n"
    '    const runtime = (try std.json.parseFromSlice(Runtime, allocator, @embedFile("runtime.json"), .{})).va'
    "lue;\n"
    "    if (request.argv.len != 5 or !std.mem.eql(u8, request.argv[0], runtime.interpreter) or !std.mem.eql(u"
    '8, request.argv[1], "-I") or !std.mem.eql(u8, request.argv[2], "-S") or !std.mem.eql(u8, request.argv[3],'
    ' "-B") or !std.mem.eql(u8, request.argv[4], "validator.py")) return error.UnqualifiedProgram;\n'
    "    for (runtime.files) |file| {\n"
    "        const resolved = try std.Io.Dir.cwd().realPathFileAlloc(init.io, file.path, allocator);\n"
    "        const bytes = try std.Io.Dir.cwd().readFileAlloc(init.io, file.path, allocator, .limited(64 * 102"
    "4 * 1024));\n"
    "        if (!std.mem.eql(u8, resolved, file.resolved) or !std.mem.eql(u8, file.sha256, try hash(allocator"
    ", bytes))) return error.RuntimeDrift;\n"
    "    }\n"
    '    const program_path = try std.fs.path.join(allocator, &.{ request.cwd, "validator.py" });\n'
    "    const program = try std.Io.Dir.cwd().readFileAlloc(init.io, program_path, allocator, .limited(65536))"
    ";\n"
    '    if (!std.mem.eql(u8, program, @embedFile("validator.py"))) return error.UnqualifiedProgram;\n'
    "    var environment = std.process.Environ.Map.init(allocator);\n"
    "    defer environment.deinit();\n"
    "    var observations: std.ArrayList(Environment) = .empty;\n"
    "    for (request.environment_names) |name| {\n"
    '        if (!std.mem.eql(u8, name, "WP02_FLAG")) return error.UnqualifiedEnvironment;\n'
    "        const value = init.environ_map.get(name);\n"
    "        var digest: ?[]const u8 = null;\n"
    "        if (value) |bytes| {\n"
    "            try environment.put(name, bytes);\n"
    "            digest = try hash(allocator, bytes);\n"
    "        }\n"
    "        try observations.append(allocator, .{ .name = name, .present = value != null, .sha256 = digest })"
    ";\n"
    "    }\n"
    "    const result = try owned.run(allocator, init.io, .{ .argv = request.argv, .cwd = .{ .path = request.c"
    "wd }, .environment = &environment, .limits = request.limits });\n"
    "    defer result.deinit(allocator);\n"
    "    const executable = try std.process.executablePathAlloc(init.io, allocator);\n"
    "    const executable_bytes = try std.Io.Dir.cwd().readFileAlloc(init.io, executable, allocator, .limited("
    "64 * 1024 * 1024));\n"
    "    const output = .{\n"
    "        .schema_version = 1,\n"
    "        .run_id = request.run_id,\n"
    "        .binding_sha256 = request.binding_sha256,\n"
    "        .check_id = request.check_id,\n"
    "        .producer = .{ .executable_path = executable, .executable_sha256 = try hash(allocator, executable"
    '_bytes), .source_tool_sha256 = try hash(allocator, @embedFile("producer.zig") ++ @embedFile("owned_proces'
    's_group.zig") ++ @embedFile("validator.py") ++ @embedFile("runtime.json")), .process_source_sha256 = try '
    'hash(allocator, @embedFile("owned_process_group.zig")), .compiler_version = @import("builtin").zig_versio'
    "n_string },\n"
    "        .program_qualification = .{ .source_sha256 = try hash(allocator, program), .runtime_manifest_sha2"
    '56 = try hash(allocator, @embedFile("runtime.json")), .scope = "exact-isolated-source-no-process-creation'
    '", .runtime_files = runtime.files },\n'
    "        .argv = request.argv,\n"
    "        .cwd = request.cwd,\n"
    "        .environment = observations.items,\n"
    "        .limits = request.limits,\n"
    "        .result = result,\n"
    '        .ownership_scope = "original-posix-group",\n'
    "        .session_escape_containment_qualified = false,\n"
    '        .usage_measurement = "sampled-not-hard-peaks",\n'
    "    };\n"
    "    var buffer: std.Io.Writer.Allocating = .init(allocator);\n"
    "    var stringify: std.json.Stringify = .{ .writer = &buffer.writer };\n"
    "    try stringify.write(output);\n"
    "    try buffer.writer.writeByte('\\n');\n"
    "    try std.Io.File.stdout().writeStreamingAll(init.io, buffer.written());\n"
    "}\n"
)

INERT_PROGRAM = (
    b"from pathlib import Path\nimport sys\nactual = Path('app.py').read_bytes()\nsys.stdout.buffer.write(actual)\nsys.exit(0 if actual == b'PASS\\n' else 7)\n"
)
OWNER_SOURCE = ROOT / "tests/local_validation/fixtures/owned_process_group.zig"
OWNER_SHA256 = "16dbf37d5d9199e61523e731cf931404e695d7a37fec463519951ba0a26fff8b"


def canonical(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"


def file_pin(path: Path) -> dict[str, Any]:
    return {"path": str(path), "resolved": str(path.resolve()), "sha256": digest(path.read_bytes()), "mode": path.stat().st_mode}


@pytest.fixture(scope="session")
def qualified_producer(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    if sys.platform != "darwin":
        pytest.skip("This producer pins Darwin dyld and process-group observations; not Linux producer qualification")
    assert digest(OWNER_SOURCE.read_bytes()) == OWNER_SHA256
    directory = tmp_path_factory.mktemp("closed-native-producer")
    (directory / "owned_process_group.zig").write_bytes(OWNER_SOURCE.read_bytes())
    (directory / "producer.zig").write_text(PRODUCER_SOURCE)
    expected = directory / "expected-data"
    expected.write_bytes(b"PASS\n")
    program = INERT_PROGRAM.replace(b"actual = ", ("expected = Path(" + repr(str(expected)) + ").read_bytes()\nactual = ").encode())
    program = program.replace(b"actual == b'PASS\\n'", b"actual == expected")
    assert b"actual == expected" in program
    (directory / "validator.py").write_bytes(program)
    # Observe a conservative superset of this exact isolated standard-library
    # program's imported module/cache files; no ambient site or editable imports.
    probe = """import ctypes,hashlib,json,pathlib,sys
pathlib.Path('/dev/null').read_bytes()
paths={sys.executable,'/System/Library/CoreServices/SystemVersion.plist'}
# Pin readable loaded native images as well as Python module/cache files.
# System shared-cache images have no individual readable file; this is a local
# fixture epoch, not a whole-OS or general platform qualification.
loader=ctypes.CDLL(None)
loader._dyld_image_count.restype=ctypes.c_uint32
loader._dyld_get_image_name.argtypes=[ctypes.c_uint32]
loader._dyld_get_image_name.restype=ctypes.c_char_p
for index in range(loader._dyld_image_count()):
 name=loader._dyld_get_image_name(index)
 if name:
  path=name.decode()
  if pathlib.Path(path).is_file(): paths.add(path)
for module in list(sys.modules.values()):
 for field in ('__file__','__cached__'):
  value=getattr(module,field,None)
  if value and pathlib.Path(value).is_file(): paths.add(value)
rows=[]
for p in sorted(paths):
 row={'path':p,'resolved':str(pathlib.Path(p).resolve())}
 row.update({'sha256':hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest(),'mode':pathlib.Path(p).stat().st_mode})
 rows.append(row)
print(json.dumps({'schema_version':1,'interpreter':sys.executable,'files':rows,'scope':'isolated-source-closed-stdlib'}))
"""
    runtime = subprocess.run([str(Path(sys.executable).resolve()), "-I", "-S", "-B", "-c", probe], capture_output=True, check=True, timeout=20)
    runtime_path = directory / "runtime.json"
    runtime_value = json.loads(runtime.stdout)
    runtime_value["files"].append(file_pin(expected))
    runtime_path.write_bytes(canonical(runtime_value))
    image = directory / "producer"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(directory / "producer.zig"), "-femit-bin=" + str(image)]
    compiled = subprocess.run(argv, capture_output=True, check=True, timeout=120)
    sources = [directory / name for name in ["producer.zig", "owned_process_group.zig", "validator.py", "runtime.json"]]
    retain_native_build_metadata(image, sources, argv, compiled)
    return {
        "directory": directory,
        "image": image,
        "runtime": runtime_value,
        "program": program,
        "expected": expected,
        "runtime_path": runtime_path,
        "sources": sources,
    }


@pytest.fixture
def qualified_inputs(
    candidate_binary: Path, receipt_binary: Path, bound_inputs: dict[str, Any], qualified_producer: dict[str, Any], tmp_path: Path
) -> dict[str, Any]:
    repo = bound_inputs["repository"]
    (repo / "validator.py").write_bytes(qualified_producer["program"])
    (repo / "app.py").write_bytes(b"PASS\n")
    producer = qualified_producer
    argv = [producer["runtime"]["interpreter"], "-I", "-S", "-B", "validator.py"]
    version = subprocess.run([shutil.which("zig") or "zig", "version"], capture_output=True, check=True, timeout=10).stdout.decode().strip()
    import platform

    architecture = {"arm64": "aarch64", "x86_64": "x86_64"}[platform.machine()]
    q = {
        "schema_version": 1,
        "scope": "exact-isolated-source-no-process-creation",
        "platform": architecture + "-macos",
        "argv": argv,
        "environment_names": ["WP02_FLAG"],
        "limits": {"wall_ms": 3000, "cleanup_ms": 1000, "stdout_bytes": 4096, "stderr_bytes": 4096, "processes": 4, "resident_bytes": 268435456},
        "program_path_hex": b"validator.py".hex(),
        "program_sha256": digest(producer["program"]),
        "producer": {"path": str(producer["image"]), "sha256": digest(producer["image"].read_bytes()), "mode": producer["image"].stat().st_mode},
        "producer_sources": [file_pin(path) for path in producer["sources"]],
        "producer_source_tool_sha256": digest(b"".join(path.read_bytes() for path in producer["sources"])),
        "process_source_sha256": OWNER_SHA256,
        "compiler_version": version,
        "runtime_manifest_sha256": digest(producer["runtime_path"].read_bytes()),
        "runtime_files": producer["runtime"]["files"],
    }
    (repo / "gates.json").write_bytes(canonical({"schema_version": 1, "receipt_qualifications": [q]}))
    git(repo, "add", "--all")
    result, capture_request = capture(candidate_binary, repo, tmp_path, destination=str(tmp_path / "qualified candidate"))
    assert result.returncode == 0, result.stderr
    request = bound_inputs["request"].copy()
    request["candidate_manifest"] = str(Path(capture_request["destination"]) / "candidate.json")
    # The closure is deliberately conservative: the complete candidate binding,
    # all transitive observed dependencies, specification, and environment match.
    request["checks"] = [
        {"id": "closed", "argv": [argv], "closure_proof": {"qualification_sha256": digest(canonical(q))}},
        {"id": "fresh", "argv": [argv], "closure_proof": None},
    ]
    request["files"] = list(request["files"])
    known = {str(Path(row["path"]).resolve()) for row in request["files"]}
    request["files"].append({"role": "toolchain", "path": str(Path(shutil.which("zig") or "zig").resolve()), "candidate_path_hex": None})
    extra = [file_pin(path) for path in [producer["image"], *producer["sources"]]]
    for row in [*q["runtime_files"], *extra]:
        if row["resolved"] not in known:
            request["files"].append({"role": "observed_dependency", "path": row["path"], "candidate_path_hex": None})
            known.add(row["resolved"])
    bound_inputs["request_path"].write_bytes(canonical(request))
    # Retained historical oracle runs actual fresh producers twice. A missing
    # native feature is never counted as a proof of failed suppression.
    if os.environ.get("SPEC_KITTY_RECEIPT_MIGRATION_ORACLE") == "always-fresh":
        legacy = request.copy()
        legacy["checks"] = [{**check, "closure_proof": None} for check in request["checks"]]
        bound_inputs["request_path"].write_bytes(canonical(legacy))
    result = receipt_call(receipt_binary, "bind", bound_inputs["request_path"], bound_inputs["environment"])
    assert result.returncode == 0, result.stderr
    bound_inputs["binding_path"].write_bytes(result.stdout)
    binding = json.loads(result.stdout)
    binding.pop("sha256")
    return {
        **bound_inputs,
        "request": request,
        "qualification": q,
        "producer": producer,
        "binding_sha256": digest(canonical(binding)),
        "manifest": json.loads(Path(request["candidate_manifest"]).read_bytes()),
        "runs": [],
        "tmp": tmp_path,
    }


def produce(receipt_binary: Path, inputs: dict[str, Any], check: str, suffix: str) -> Path:
    directory = Path(inputs["tmp"]) / ("run-" + suffix)
    directory.mkdir(mode=0o700)
    q = inputs["qualification"]
    request = {
        "argv": q["argv"],
        "cwd": inputs["manifest"]["root"],
        "environment_names": q["environment_names"],
        "limits": q["limits"],
        "binding_sha256": inputs["binding_sha256"],
        "check_id": check,
        "run_id": suffix,
    }
    path = directory / "request.json"
    path.write_bytes(canonical(request))
    result = subprocess.run([str(inputs["producer"]["image"]), str(path)], env=inputs["environment"], capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    witness = directory / "witness.json"
    witness.write_bytes(result.stdout)
    value = json.loads(result.stdout)
    inputs["runs"].append(value)
    assert value["result"]["leader_reaped"] is True and value["result"]["group_disposed"] is True
    stdout, stderr = directory / "stdout.log", directory / "stderr.log"
    stdout.write_bytes(value["result"]["stdout"].encode())
    stderr.write_bytes(value["result"]["stderr"].encode())
    request_path = directory / "record-request.json"
    request_path.write_bytes(
        canonical({"binding": str(inputs["binding_path"]), "check_id": check, "witness": str(witness), "stdout_log": str(stdout), "stderr_log": str(stderr)})
    )
    if os.environ.get("SPEC_KITTY_RECEIPT_MIGRATION_ORACLE") == "always-fresh":
        return witness
    result = receipt_call(receipt_binary, "record", request_path, inputs["environment"])
    assert result.returncode == 0, result.stderr
    evidence = directory / "evidence.json"
    evidence.write_bytes(result.stdout)
    return evidence


def decide(receipt_binary: Path, inputs: dict[str, Any], check: str, evidence: Path | None) -> dict[str, Any]:
    if os.environ.get("SPEC_KITTY_RECEIPT_MIGRATION_ORACLE") == "always-fresh":
        return {"action": "fresh"}
    request = inputs["tmp"] / "reuse-request.json"
    request.write_bytes(canonical({"binding": str(inputs["binding_path"]), "check_id": check, "evidence": str(evidence) if evidence else None}))
    result = receipt_call(receipt_binary, "reuse", request, inputs["environment"])
    assert result.returncode == 0, result.stderr
    value: dict[str, Any] = json.loads(result.stdout)
    return value


def test_actual_per_check_reuse_suppresses_one_producer_while_unproved_check_runs_fresh(receipt_binary: Path, qualified_inputs: dict[str, Any]) -> None:
    inputs = qualified_inputs
    before = snapshot(inputs["repository"])
    evidence: dict[str, Path] = {}
    for round_number in [1, 2]:
        for check in ["closed", "fresh"]:
            plan = decide(receipt_binary, inputs, check, evidence.get(check))
            if plan["action"] == "fresh":
                evidence[check] = produce(receipt_binary, inputs, check, f"{check}-{round_number}")
    assert snapshot(inputs["repository"]) == before
    assert len(inputs["runs"]) == 3, "Matching qualified check must suppress an actual producer run; unproved closure must execute fresh"
    assert [run["check_id"] for run in inputs["runs"]] == ["closed", "fresh", "fresh"]
    assert all(run["result"]["exit_code"] == 0 and run["result"]["stdout"] == "PASS\n" for run in inputs["runs"])
    # Direct fresh baseline on the SAME source/candidate/tool/dependency/env
    # binding. Retain all seven real native witnesses; no time/cost claim.
    baseline_start = len(inputs["runs"])
    for round_number in [1, 2]:
        for check in ["closed", "fresh"]:
            produce(receipt_binary, inputs, check, f"fresh-baseline-{check}-{round_number}")
    baseline = inputs["runs"][baseline_start:]
    assert len(baseline) == 4
    assert all(run["binding_sha256"] == inputs["binding_sha256"] for run in inputs["runs"])
    assert all(run["result"]["exit_code"] == 0 and run["result"]["stdout"] == "PASS\n" for run in baseline)
    request = inputs["tmp"] / "accept-request.json"
    request.write_bytes(canonical({"binding": str(inputs["binding_path"]), "evidence": [str(evidence[check]) for check in ["closed", "fresh"]]}))
    result = receipt_call(receipt_binary, "accept", request, inputs["environment"])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["accepted"] is True


def consumer_request(
    receipt_binary: Path, inputs: dict[str, Any], operation: str, value: dict[str, Any], suffix: str = "control"
) -> subprocess.CompletedProcess[bytes]:
    path = inputs["tmp"] / (suffix + "-request.json")
    path.write_bytes(canonical(value))
    return receipt_call(receipt_binary, operation, path, inputs["environment"])


@pytest.mark.parametrize(
    "fault",
    [
        "index",
        "parent",
        "launcher",
        "native_source",
        "specification",
        "dependency_lock",
        "observed_dependency",
        "environment",
        "native_executable",
        "argv",
        "producer",
        "producer_source",
        "producer-mode",
        "native-mode",
    ],
)
def test_actual_completed_evidence_refuses_each_relevant_drift(receipt_binary: Path, qualified_inputs: dict[str, Any], tmp_path: Path, fault: str) -> None:
    inputs = qualified_inputs
    evidence = produce(receipt_binary, inputs, "closed", "before-" + fault)
    assert decide(receipt_binary, inputs, "closed", evidence)["action"] == "reuse"
    fresh = produce(receipt_binary, inputs, "fresh", "baseline-fresh-" + fault)
    complete = {"binding": str(inputs["binding_path"]), "evidence": [str(evidence), str(fresh)]}
    baseline = consumer_request(receipt_binary, inputs, "accept", complete, "baseline")
    assert baseline.returncode == 0 and json.loads(baseline.stdout)["accepted"] is True, baseline.stderr
    restore: tuple[Path, bytes] | None = None
    restore_mode: tuple[Path, int] | None = None
    executable = receipt_binary
    try:
        if fault in {"producer-mode", "native-mode"}:
            path = inputs["producer"]["image"] if fault == "producer-mode" else receipt_binary
            restore_mode = (path, path.stat().st_mode)
            path.chmod(0o700 if path.stat().st_mode & 0o077 else 0o755)
        elif fault == "index":
            (inputs["repository"] / "app.py").write_bytes(b"changed staged bytes\n")
            git(inputs["repository"], "add", "app.py")
        elif fault == "parent":
            parent = git(inputs["repository"], "rev-parse", "HEAD").stdout.strip()
            tree = git(inputs["repository"], "rev-parse", "HEAD^{tree}").stdout.strip()
            commit = git(inputs["repository"], "commit-tree", tree.decode(), "-p", parent.decode(), "-m", "different parent identity").stdout.strip()
            git(inputs["repository"], "update-ref", "HEAD", commit.decode())
        elif fault == "environment":
            inputs["environment"]["WP02_FLAG"] += " changed"
        elif fault == "native_executable":
            executable = tmp_path / "same-native-image-different-identity"
            shutil.copyfile(receipt_binary, executable)
            executable.chmod(0o700)
        elif fault == "argv":
            request = inputs["request"].copy()
            request["checks"] = [{**check, "argv": [check["argv"][0] + ["new-argument"]]} for check in request["checks"]]
            inputs["request_path"].write_bytes(canonical(request))
            result = receipt_call(receipt_binary, "bind", inputs["request_path"], inputs["environment"])
            assert result.returncode == 0, result.stderr
            inputs["binding_path"].write_bytes(result.stdout)
        else:
            if fault == "producer":
                path = inputs["producer"]["image"]
            elif fault == "producer_source":
                path = inputs["producer"]["sources"][0]
            elif fault == "observed_dependency":
                path = inputs["producer"]["expected"]
            else:
                path = Path(next(row["path"] for row in inputs["request"]["files"] if row["role"] == fault))
            restore = (path, path.read_bytes())
            path.write_bytes(path.read_bytes() + b"\nchanged identity\n")
        result = consumer_request(executable, inputs, "accept", {"binding": str(inputs["binding_path"]), "evidence": [str(evidence), str(fresh)]})
        assert result.returncode != 0 and result.stdout == b"", (fault, result.stdout, result.stderr)
    finally:
        if restore is not None:
            restore[0].write_bytes(restore[1])
        if restore_mode is not None:
            restore_mode[0].chmod(restore_mode[1])


@pytest.mark.parametrize(
    "fault",
    [
        "stdout-log",
        "stderr-log",
        "witness",
        "evidence",
        "missing",
        "duplicate",
        "wrong-check",
        "old-global",
        "cleanup",
        "exit",
        "quota",
        "scope",
        "environment",
        "producer",
        "program",
        "binding",
    ],
)
def test_missing_tampered_failed_or_unqualified_terminal_evidence_refuses(receipt_binary: Path, qualified_inputs: dict[str, Any], fault: str) -> None:
    inputs = qualified_inputs
    evidence_path = produce(receipt_binary, inputs, "closed", "terminal-" + fault)
    evidence = json.loads(evidence_path.read_bytes())
    request: dict[str, Any] = {"binding": str(inputs["binding_path"]), "evidence": [str(evidence_path), str(evidence_path)]}
    operation = "accept"
    if fault in {"stdout-log", "stderr-log"}:
        path = Path(evidence[fault.replace("-", "_")]["path"])
        path.write_bytes(path.read_bytes() + b"altered retained diagnostic\n")
    elif fault == "witness":
        Path(evidence["witness"]["path"]).write_bytes(b"{}")
    elif fault == "evidence":
        evidence["run_id"] = "invented"
        evidence_path.write_bytes(canonical(evidence))
    elif fault == "missing":
        request["evidence"] = []
    elif fault == "wrong-check":
        operation = "reuse"
        request = {"binding": str(inputs["binding_path"]), "check_id": "unknown-check", "evidence": str(evidence_path)}
    elif fault == "old-global":
        evidence_path.write_bytes(canonical({"passed": True, "tree": inputs["binding_sha256"]}))
    elif fault != "duplicate":
        witness_path = Path(evidence["witness"]["path"])
        witness = json.loads(witness_path.read_bytes())
        if fault == "cleanup":
            witness["result"]["group_disposed"] = False
        elif fault == "exit":
            witness["result"]["exit_code"] = 7
        elif fault == "quota":
            witness["result"]["elapsed_ms"] = 50000
        elif fault == "scope":
            witness["session_escape_containment_qualified"] = True
        elif fault == "environment":
            witness["environment"] = []
        elif fault == "producer":
            witness["producer"]["source_tool_sha256"] = "0" * 64
        elif fault == "program":
            witness["program_qualification"]["source_sha256"] = "0" * 64
        else:
            witness["binding_sha256"] = "0" * 64
        witness_path.write_bytes(canonical(witness))
        operation = "record"
        request = {
            "binding": str(inputs["binding_path"]),
            "check_id": "closed",
            "witness": str(witness_path),
            "stdout_log": evidence["stdout_log"]["path"],
            "stderr_log": evidence["stderr_log"]["path"],
        }
    result = consumer_request(receipt_binary, inputs, operation, request)
    assert result.returncode != 0 and result.stdout == b"", (fault, result.stdout, result.stderr)


@pytest.mark.parametrize(
    "fault",
    [
        "absent",
        "boolean",
        "unknown-scope",
        "different-argv",
        "drifted-runtime",
        "unknown-field",
        "zero-budget",
        "overflow-budget",
        "unbound-runtime",
        "duplicate",
        "program-mismatch",
        "source-mismatch",
        "empty-runtime",
    ],
)
def test_unknown_or_incomplete_closure_never_authorizes_reuse(candidate_binary: Path, receipt_binary: Path, qualified_inputs: dict[str, Any], fault: str) -> None:
    inputs = qualified_inputs
    # The unchanged corresponding policy is recognized before each mutation.
    initial = decide(receipt_binary, inputs, "closed", None)
    assert initial["action"] == "fresh" and initial["reason"] == "evidence-missing"
    request = inputs["request"].copy()
    checks = [dict(check) for check in request["checks"]]
    if fault == "absent":
        checks[0]["closure_proof"] = None
    elif fault == "boolean":
        checks[0]["closure_proof"] = True
    else:
        q = dict(inputs["qualification"])
        if fault == "unknown-scope":
            q["scope"] = "unknown-program-may-escape"
        elif fault == "different-argv":
            q["argv"] = q["argv"] + ["different"]
        elif fault == "drifted-runtime":
            q["runtime_files"] = [{**q["runtime_files"][0], "sha256": "0" * 64}]
        elif fault == "unknown-field":
            q["invented_approval"] = True
        elif fault in {"zero-budget", "overflow-budget"}:
            q["limits"] = {**q["limits"], "wall_ms": 0 if fault == "zero-budget" else 2**64 - 1}
        elif fault == "unbound-runtime":
            extra = inputs["tmp"] / "not-declared-runtime"
            extra.write_bytes(b"new actual unbound dependency\n")
            q["runtime_files"] = [*q["runtime_files"], file_pin(extra)]
        elif fault == "program-mismatch":
            q["program_path_hex"] = b"app.py".hex()
        elif fault == "source-mismatch":
            q["process_source_sha256"] = "0" * 64
        elif fault == "empty-runtime":
            q["runtime_files"] = []
        documents = [q, q] if fault == "duplicate" else [q]
        checks[0]["closure_proof"] = {"qualification_sha256": digest(canonical(q))}
        (inputs["repository"] / "gates.json").write_bytes(canonical({"schema_version": 1, "receipt_qualifications": documents}))
        git(inputs["repository"], "add", "gates.json")
        captured, capture_request = capture(candidate_binary, inputs["repository"], inputs["tmp"], destination=str(inputs["tmp"] / ("policy-" + fault)))
        assert captured.returncode == 0, captured.stderr
        request["candidate_manifest"] = str(Path(capture_request["destination"]) / "candidate.json")
    request["checks"] = checks
    inputs["request_path"].write_bytes(canonical(request))
    result = receipt_call(receipt_binary, "bind", inputs["request_path"], inputs["environment"])
    assert result.returncode == 0, result.stderr
    inputs["binding_path"].write_bytes(result.stdout)
    result = consumer_request(receipt_binary, inputs, "reuse", {"binding": str(inputs["binding_path"]), "check_id": "closed", "evidence": None})
    if fault == "boolean":
        assert result.returncode != 0 and result.stdout == b""
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["action"] == "fresh" and json.loads(result.stdout)["reason"] == "closure-unproved"


@pytest.mark.parametrize("fault", ["omitted", "duplicated"])
def test_declared_runtime_must_match_actual_producer_observation(
    candidate_binary: Path, receipt_binary: Path, qualified_inputs: dict[str, Any], fault: str
) -> None:
    inputs = qualified_inputs
    evidence = produce(receipt_binary, inputs, "closed", "complete-observed-closure")
    assert decide(receipt_binary, inputs, "closed", evidence)["action"] == "reuse"
    original_runtime = inputs["qualification"]["runtime_files"]
    dependency = inputs["producer"]["expected"]
    q = dict(inputs["qualification"])
    q["runtime_files"] = (
        [row for row in original_runtime if row["resolved"] != str(dependency.resolve())] if fault == "omitted" else [*original_runtime, original_runtime[-1]]
    )
    assert q["runtime_files"] != original_runtime
    repo = inputs["repository"]
    (repo / "gates.json").write_bytes(canonical({"schema_version": 1, "receipt_qualifications": [q]}))
    git(repo, "add", "gates.json")
    captured, capture_request = capture(candidate_binary, repo, inputs["tmp"], destination=str(inputs["tmp"] / "incomplete-observed-candidate"))
    assert captured.returncode == 0, captured.stderr
    request = inputs["request"].copy()
    request["candidate_manifest"] = str(Path(capture_request["destination"]) / "candidate.json")
    if fault == "omitted":
        request["files"] = [row for row in request["files"] if str(Path(row["path"]).resolve()) != str(dependency.resolve())]
    request["checks"] = [
        {**check, "closure_proof": {"qualification_sha256": digest(canonical(q))} if check["id"] == "closed" else None} for check in request["checks"]
    ]
    inputs["request_path"].write_bytes(canonical(request))
    bound = receipt_call(receipt_binary, "bind", inputs["request_path"], inputs["environment"])
    assert bound.returncode == 0, bound.stderr
    inputs["binding_path"].write_bytes(bound.stdout)
    binding = json.loads(bound.stdout)
    binding.pop("sha256")
    directory = inputs["tmp"] / "actual-observed-closure"
    directory.mkdir(mode=0o700)
    producer_request = json.loads((evidence.parent / "request.json").read_bytes())
    producer_request["binding_sha256"] = digest(canonical(binding))
    producer_request["cwd"] = json.loads(Path(request["candidate_manifest"]).read_bytes())["root"]
    producer_request["run_id"] = "observed-closure-" + fault
    request_path = directory / "producer-request.json"
    request_path.write_bytes(canonical(producer_request))
    actual = subprocess.run([str(inputs["producer"]["image"]), str(request_path)], env=inputs["environment"], capture_output=True, timeout=15)
    assert actual.returncode == 0, actual.stderr
    witness = directory / "witness.json"
    witness.write_bytes(actual.stdout)
    value = json.loads(actual.stdout)
    assert value["result"]["exit_code"] == 0 and value["result"]["group_disposed"] is True
    assert value["program_qualification"]["runtime_files"] == original_runtime
    stdout, stderr = directory / "stdout.log", directory / "stderr.log"
    stdout.write_bytes(value["result"]["stdout"].encode())
    stderr.write_bytes(value["result"]["stderr"].encode())
    recorded = consumer_request(
        receipt_binary,
        inputs,
        "record",
        {"binding": str(inputs["binding_path"]), "check_id": "closed", "witness": str(witness), "stdout_log": str(stdout), "stderr_log": str(stderr)},
        "observed-closure-" + fault,
    )
    (directory / "record.stdout.log").write_bytes(recorded.stdout)
    (directory / "record.stderr.log").write_bytes(recorded.stderr)
    assert recorded.returncode != 0 and recorded.stdout == b"", "A declared closure must match the producer's actual complete observation"
    # The omitted input really affects the actual producer, rather than being a
    # decorative policy entry. Restore this session fixture even on refusal.
    before = dependency.read_bytes()
    try:
        dependency.write_bytes(b"CHANGED ACTUAL DEPENDENCY\n")
        drifted = subprocess.run([str(inputs["producer"]["image"]), str(request_path)], env=inputs["environment"], capture_output=True, timeout=15)
        (directory / "fresh-drift.stderr.log").write_bytes(drifted.stderr)
        assert drifted.returncode != 0 and b"RuntimeDrift" in drifted.stderr
    finally:
        dependency.write_bytes(before)


# A disposable repository hook exercises Git's actual acceptance boundary.
# This never installs or changes an operational checkout's hooks.
GIT_ACCEPTANCE_HOOK = r"""import json,os,pathlib,subprocess,sys
config=json.loads(pathlib.Path(sys.argv[1]).read_bytes())
root=pathlib.Path(config['root'])
evidence=pathlib.Path(config['evidence'])
def call(argv,input_bytes=None):
 result=subprocess.run(argv,input=input_bytes,capture_output=True,timeout=40)
 if result.returncode:
  sys.stderr.buffer.write(result.stderr)
  raise SystemExit(result.returncode)
 return result.stdout
if config['legacy']:
 raise SystemExit(subprocess.run([config['python'],'-I','-S','-B','validator.py'],cwd=root,timeout=15).returncode)
evidence.mkdir(mode=0o700)
capture={'schema_version':1,'repository':str(root),'base':'HEAD','destination':str(evidence/'candidate'),'git_executable':'/usr/bin/git'}
path=evidence/'capture.json'
path.write_text(json.dumps(capture))
manifest=json.loads(call([config['candidate'],'capture',str(path)]))
request=config['request']
request['candidate_manifest']=str(evidence/'candidate/candidate.json')
path=evidence/'binding-request.json'
path.write_text(json.dumps(request))
binding_path=evidence/'binding.json'
binding_path.write_bytes(call([config['receipt'],'bind',str(path)]))
binding=json.loads(binding_path.read_bytes())
sha=binding.pop('sha256')
receipts=[]
for check in request['checks']:
 run=evidence/check['id']
 run.mkdir(mode=0o700)
 q=config['qualification']
 producer_request={'argv':q['argv'],'cwd':manifest['root'],'environment_names':q['environment_names'],'limits':q['limits'],'binding_sha256':sha,'check_id':check['id'],'run_id':check['id']+'-git-hook'}
 path=run/'producer-request.json'
 path.write_text(json.dumps(producer_request))
 witness=run/'witness.json'
 witness.write_bytes(call([config['producer'],str(path)]))
 result=json.loads(witness.read_bytes())['result']
 stdout,stderr=run/'stdout.log',run/'stderr.log'
 stdout.write_bytes(result['stdout'].encode())
 stderr.write_bytes(result['stderr'].encode())
 path=run/'record-request.json'
 path.write_text(json.dumps({'binding':str(binding_path),'check_id':check['id'],'witness':str(witness),'stdout_log':str(stdout),'stderr_log':str(stderr)}))
 receipt=run/'receipt.json'
 receipt.write_bytes(call([config['receipt'],'record',str(path)]))
 receipts.append(str(receipt))
if config.get('drift_after_checks'):
 oid=call(['/usr/bin/git','-C',str(root),'hash-object','-w','--stdin'],b'CHANGED AFTER CHECKS\n').decode().strip()
 call(['/usr/bin/git','-C',str(root),'update-index','--cacheinfo','100644',oid,'app.py'])
path=evidence/'accept-request.json'
path.write_text(json.dumps({'binding':str(binding_path),'evidence':receipts}))
accepted=json.loads(call([config['receipt'],'accept',str(path)]))
if not accepted['accepted'] or accepted['external_write_reservation']:
 raise SystemExit(8)
"""


def install_fixture_acceptance_hook(candidate_binary: Path, receipt_binary: Path, inputs: dict[str, Any], drift_after_checks: bool = False) -> None:
    repo, tmp = inputs["repository"], inputs["tmp"]
    script = tmp / "acceptance-hook.py"
    script.write_text(GIT_ACCEPTANCE_HOOK)
    config = tmp / "hook-configuration.json"
    config.write_bytes(
        canonical(
            {
                "root": str(repo),
                "evidence": str(tmp / "git-hook-evidence"),
                "python": str(Path(sys.executable).resolve()),
                "candidate": str(candidate_binary),
                "receipt": str(receipt_binary),
                "producer": str(inputs["producer"]["image"]),
                "request": inputs["request"],
                "qualification": inputs["qualification"],
                "legacy": os.environ.get("SPEC_KITTY_GIT_ACCEPTANCE_ORACLE") == "direct-live",
                "drift_after_checks": drift_after_checks,
            }
        )
    )
    # Paths are passed as literal shell single-quoted words; fixture paths never
    # become command text. No operational hook is touched.
    import shlex

    hook = repo / ".git/hooks/pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text("#!/bin/sh\nexec " + " ".join(shlex.quote(word) for word in [sys.executable, "-I", "-S", "-B", str(script), str(config)]) + "\n")
    hook.chmod(0o700)


@pytest.mark.parametrize(("staged", "live", "accepted"), [(b"FAIL\n", b"PASS\n", False), (b"PASS\n", b"FAIL\n", True)])
def test_real_git_commit_accepts_only_exact_staged_candidate_and_preserves_live_work(
    candidate_binary: Path, receipt_binary: Path, qualified_inputs: dict[str, Any], staged: bytes, live: bytes, accepted: bool
) -> None:
    inputs = qualified_inputs
    repo, tmp = inputs["repository"], inputs["tmp"]
    install_fixture_acceptance_hook(candidate_binary, receipt_binary, inputs)
    (repo / "app.py").write_bytes(staged)
    git(repo, "add", "app.py")
    (repo / "app.py").write_bytes(live)
    before = snapshot(repo)
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(repo), "commit", "-qm", "actual staged acceptance"], env=inputs["environment"], capture_output=True, timeout=60
    )
    after = snapshot(repo)
    assert (result.returncode == 0) is accepted, (result.stdout, result.stderr)
    assert after["files"] == before["files"] and after["hooks"] == before["hooks"]
    assert git(repo, "show", ":app.py").stdout == staged and (repo / "app.py").read_bytes() == live
    normalized_before = [b"HEAD @CURRENT@" if row.startswith(b"HEAD ") else row for row in before["registry"].split(b"\0")]
    normalized_after = [b"HEAD @CURRENT@" if row.startswith(b"HEAD ") else row for row in after["registry"].split(b"\0")]
    assert normalized_after == normalized_before
    if accepted:
        assert after["head"] != before["head"]
        assert git(repo, "show", "HEAD:app.py").stdout == staged
        assert json.loads((tmp / "git-hook-evidence/closed/receipt.json").read_bytes())["acceptance_performed"] is False
    else:
        assert after["head"] == before["head"] and after["refs"] == before["refs"]


def test_real_git_refuses_actual_index_drift_after_successful_native_checks(candidate_binary: Path, receipt_binary: Path, qualified_inputs: dict[str, Any]) -> None:
    inputs = qualified_inputs
    repo, tmp = inputs["repository"], inputs["tmp"]
    install_fixture_acceptance_hook(candidate_binary, receipt_binary, inputs, drift_after_checks=True)
    before = snapshot(repo)
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(repo), "commit", "-qm", "must refuse post-check index drift"], env=inputs["environment"], capture_output=True, timeout=60
    )
    assert result.returncode != 0 and b"InputDrift" in result.stderr, (result.stdout, result.stderr)
    after = snapshot(repo)
    assert after["head"] == before["head"] and after["refs"] == before["refs"] and after["files"] == before["files"]
    assert after["hooks"] == before["hooks"] and after["registry"] == before["registry"]
    assert git(repo, "show", ":app.py").stdout == b"CHANGED AFTER CHECKS\n"
    for check in ["closed", "fresh"]:
        witness = json.loads((tmp / "git-hook-evidence" / check / "witness.json").read_bytes())
        assert witness["result"]["exit_code"] == 0 and witness["result"]["leader_reaped"] is True and witness["result"]["group_disposed"] is True


@pytest.mark.parametrize("fault", ["public-parent", "symlink-log", "hardlink-log"])
def test_completed_diagnostics_require_private_unaliased_regular_paths(receipt_binary: Path, qualified_inputs: dict[str, Any], fault: str) -> None:
    inputs = qualified_inputs
    evidence_path = produce(receipt_binary, inputs, "closed", "valid-private-baseline")
    original = json.loads(evidence_path.read_bytes())
    directory = inputs["tmp"] / ("invalid-private-" + fault)
    directory.mkdir(mode=0o700)
    for field, name in [("witness", "witness.json"), ("stdout_log", "stdout.log"), ("stderr_log", "stderr.log")]:
        shutil.copyfile(original[field]["path"], directory / name)
    if fault == "public-parent":
        directory.chmod(0o755)
    else:
        external = inputs["tmp"] / (fault + "-outside.log")
        shutil.copyfile(directory / "stdout.log", external)
        (directory / "stdout.log").unlink()
        if fault == "symlink-log":
            (directory / "stdout.log").symlink_to(external)
        else:
            os.link(external, directory / "stdout.log")
    result = consumer_request(
        receipt_binary,
        inputs,
        "record",
        {
            "binding": str(inputs["binding_path"]),
            "check_id": "closed",
            "witness": str(directory / "witness.json"),
            "stdout_log": str(directory / "stdout.log"),
            "stderr_log": str(directory / "stderr.log"),
        },
    )
    assert result.returncode != 0 and result.stdout == b"" and b"PrivateEvidenceRequired" in result.stderr


@pytest.mark.parametrize("fault", ["no-checks", "duplicate-check", "empty-id", "no-program", "no-words", "empty-executable", "relative-executable", "nul-argument"])
def test_invalid_selected_command_bindings_refuse_without_execution(receipt_binary: Path, bound_inputs: dict[str, Any], fault: str) -> None:
    request = json.loads(canonical(bound_inputs["request"]))
    check = request["checks"][0]
    if fault == "no-checks":
        request["checks"] = []
    elif fault == "duplicate-check":
        request["checks"].append(dict(check))
    elif fault == "empty-id":
        check["id"] = ""
    elif fault == "no-program":
        check["argv"] = []
    elif fault == "no-words":
        check["argv"] = [[]]
    elif fault == "empty-executable":
        check["argv"][0][0] = ""
    elif fault == "relative-executable":
        check["argv"][0][0] = "python"
    else:
        check["argv"][0].append("invalid\0argument")
    bound_inputs["request_path"].write_bytes(canonical(request))
    before = snapshot(bound_inputs["repository"])
    result = receipt_call(receipt_binary, "bind", bound_inputs["request_path"], bound_inputs["environment"])
    assert result.returncode != 0 and result.stdout == b"" and result.stderr
    assert snapshot(bound_inputs["repository"]) == before


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate-file",
        "unknown-role",
        "relative-file",
        "missing-role",
        "missing-source",
        "unstaged-launcher",
        "mislabeled-source",
        "duplicate-environment",
        "invalid-environment",
        "empty-environment",
    ],
)
def test_incomplete_or_ambiguous_input_identity_bindings_refuse(receipt_binary: Path, bound_inputs: dict[str, Any], fault: str) -> None:
    request = json.loads(canonical(bound_inputs["request"]))
    if fault == "duplicate-file":
        request["files"].append(next(row for row in request["files"] if row["role"] == "toolchain"))
    elif fault == "unknown-role":
        request["files"][0]["role"] = "caller-claims-approved"
    elif fault == "relative-file":
        request["files"][0]["path"] = "launcher.sh"
    elif fault == "missing-role":
        request["files"] = [row for row in request["files"] if row["role"] != "observed_dependency"]
    elif fault == "missing-source":
        request["files"] = [row for row in request["files"] if not row["path"].endswith("/validation_candidate.zig")]
    elif fault == "unstaged-launcher":
        request["files"][0]["candidate_path_hex"] = None
    elif fault == "mislabeled-source":
        index = next(index for index, row in enumerate(request["files"]) if row["role"] == "native_source")
        request["files"][index] = {**request["files"][0], "role": "native_source"}
    elif fault == "duplicate-environment":
        request["environment_names"] = ["WP02_FLAG", "WP02_FLAG"]
    else:
        request["environment_names"] = ["INVALID=NAME" if fault == "invalid-environment" else ""]
    bound_inputs["request_path"].write_bytes(canonical(request))
    result = receipt_call(receipt_binary, "bind", bound_inputs["request_path"], bound_inputs["environment"])
    assert result.returncode != 0 and result.stdout == b"" and result.stderr


@pytest.mark.parametrize("fault", ["old-schema", "unknown-field", "missing-field", "renamed-field"])
def test_binding_request_schema_cannot_supply_missing_or_invented_authority(receipt_binary: Path, bound_inputs: dict[str, Any], fault: str) -> None:
    request = json.loads(canonical(bound_inputs["request"]))
    if fault == "old-schema":
        request["schema_version"] = 0
    elif fault == "unknown-field":
        request["approved"] = True
    else:
        value = request.pop("schema_version")
        if fault == "renamed-field":
            request["invented_schema"] = value
    bound_inputs["request_path"].write_bytes(canonical(request))
    result = receipt_call(receipt_binary, "bind", bound_inputs["request_path"], bound_inputs["environment"])
    assert result.returncode != 0 and result.stdout == b"" and result.stderr


@pytest.mark.parametrize("fault", ["unknown-check", "multiple-commands", "unsafe-script", "unbound-script", "unbound-executable", "wrong-flags"])
def test_unsupported_isolated_import_context_refuses_a_plan(receipt_binary: Path, bound_inputs: dict[str, Any], tmp_path: Path, fault: str) -> None:
    request = json.loads(canonical(bound_inputs["request"]))
    check = request["checks"][1]
    if fault == "multiple-commands":
        check["argv"].append(check["argv"][0].copy())
    elif fault == "unsafe-script":
        check["argv"][0][4] = "../import_validator.py"
    elif fault == "unbound-script":
        check["argv"][0][4] = "absent-script.py"
    elif fault == "unbound-executable":
        check["argv"][0][0] = "/bin/echo"
    elif fault == "wrong-flags":
        check["argv"][0][1] = "-E"
    bound_inputs["request_path"].write_bytes(canonical(request))
    result = receipt_call(receipt_binary, "bind", bound_inputs["request_path"], bound_inputs["environment"])
    assert result.returncode == 0, result.stderr
    bound_inputs["binding_path"].write_bytes(result.stdout)
    path = tmp_path / "unsupported-plan.json"
    path.write_bytes(canonical({"binding": str(bound_inputs["binding_path"]), "check_id": "unknown" if fault == "unknown-check" else "import"}))
    result = receipt_call(receipt_binary, "python-plan", path, bound_inputs["environment"])
    assert result.returncode != 0 and result.stdout == b"" and result.stderr


def test_valid_other_check_evidence_cannot_supply_this_checks_reuse(receipt_binary: Path, qualified_inputs: dict[str, Any]) -> None:
    inputs = qualified_inputs
    other = produce(receipt_binary, inputs, "fresh", "real-other-check")
    result = consumer_request(receipt_binary, inputs, "reuse", {"binding": str(inputs["binding_path"]), "check_id": "closed", "evidence": str(other)})
    assert result.returncode != 0 and result.stdout == b"" and b"InvalidEvidence" in result.stderr


def test_recomputed_checksum_cannot_replace_actual_native_run_identity(receipt_binary: Path, qualified_inputs: dict[str, Any]) -> None:
    inputs = qualified_inputs
    evidence = produce(receipt_binary, inputs, "closed", "real-original-run")
    value = json.loads(evidence.read_bytes())
    value.pop("sha256")
    value["run_id"] = "caller-invented-run"
    value["sha256"] = digest(canonical(value))
    evidence.write_bytes(canonical(value))
    result = consumer_request(receipt_binary, inputs, "reuse", {"binding": str(inputs["binding_path"]), "check_id": "closed", "evidence": str(evidence)})
    assert result.returncode != 0 and result.stdout == b"" and b"InvalidEvidence" in result.stderr
