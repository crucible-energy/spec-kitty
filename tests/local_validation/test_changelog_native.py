"""Actual same-executable changelog component against the unchanged Python oracle."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.local_validation.test_candidate import ROOT
from tests.local_validation.test_candidate import candidate_binary as candidate_binary
from tests.local_validation.test_candidate import repository as repository
from tests.local_validation.test_execution import executor_binary as executor_binary


def test_same_native_executable_checks_an_actual_clean_changelog(executor_binary: Path, tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [Unreleased]\n### Added\n- **A useful change** (#1). Works.\n")
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"repository_root": str(ROOT), "argv": ["--changelog", str(changelog)]}))
    result = subprocess.run([str(executor_binary), "changelog-style", str(request)], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout == b"0 error(s), 0 warning(s)\n"


def oracle_cases() -> list[tuple[str, str]]:
    """Reuse real maintained positive/planted inputs without modifying their source."""
    import inspect
    from tests.docs import test_changelog_style as maintained

    original = vars(maintained)["check"]
    captured: list[tuple[str, str]] = []
    name = ""

    def collect(text: str, *args: object, **kwargs: object) -> object:
        captured.append((name, text))
        return original(text, *args, **kwargs)

    vars(maintained)["check"] = collect
    try:
        for name, function in vars(maintained).copy().items():
            if name.startswith("test_") and callable(function) and not inspect.signature(function).parameters:
                function()
    finally:
        vars(maintained)["check"] = original
    for planted in maintained.PLANTED:
        captured.append(("planted-" + planted.name, maintained.doc(*planted.body)))
    for path in [ROOT / "docs/changelog/CHANGELOG.md", *sorted((ROOT / "tests/docs/fixtures").glob("changelog*.md"))]:
        captured.append((path.name, path.read_text()))
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, text in captured:
        if text not in seen:
            seen.add(text)
            unique.append((name, text))
    return unique


def oracle_cli(argv: list[str]) -> tuple[int, bytes, bytes]:
    import contextlib
    import io
    from scripts.docs import check_changelog_style as oracle

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = oracle.main(argv)
    return code, out.getvalue().encode(), err.getvalue().encode()


def native_cli(binary: Path, tmp_path: Path, argv: list[str], root: Path = ROOT) -> subprocess.CompletedProcess[bytes]:
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"repository_root": str(root), "argv": argv}))
    result = subprocess.run([str(binary), "changelog-style", str(request)], cwd=tmp_path, capture_output=True, timeout=30)
    (tmp_path / "native.stdout.log").write_bytes(result.stdout)
    (tmp_path / "native.stderr.log").write_bytes(result.stderr)
    return result


CASES = oracle_cases()


@pytest.mark.parametrize(("name", "text"), CASES, ids=[name for name, _ in CASES])
def test_native_matches_existing_maintained_cases(executor_binary: Path, tmp_path: Path, name: str, text: str) -> None:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(text)
    argv = ["--changelog", str(path)]
    expected = oracle_cli(argv)
    result = native_cli(executor_binary, tmp_path, argv)
    (tmp_path / "oracle.stdout.log").write_bytes(expected[1])
    (tmp_path / "oracle.stderr.log").write_bytes(expected[2])
    assert (result.returncode, result.stdout, result.stderr) == expected, name


def adversarial_cases() -> list[str]:
    cases = []
    for size in [900, 901, 1200, 1201]:
        cases.append("## [Unreleased]\n### Added\n- **" + "é" * (size - 6) + "**\n")
    for neighbor in ["é", "中", "²", "_", "\u0301", "😀", "\u2003", "\u1c89"]:
        cases.append(f"##[Unreleased]\n### Internal\n- {neighbor}FR-1 FR-1{neighbor} spec-kitty merge{neighbor} DEFAULT{neighbor} #١٢ FR-١a.٢x\n")
    for separator in ["\n", "\r\n", "\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]:
        cases.append(
            separator.join(["## [Unreleased]", "### Fixed", "orphan FR-1", "- **Headline**", "  - FR-2", "    wrapped", "### Added", "### Added", "* wrong"])
        )
    for release in [
        "##1.٢.3",
        "## [1.2.3alpha]",
        "## [1.2.3rc2]",
        "## 1.2.3 - Unreleasedbogus",
        "## [Unreleaſed]",
        "## Unreleased1.2.3",
        "## [Unreleased]]",
        "## [Unreleased]]]",
        "## [Unreleased] - 1.2.3bad",
    ]:
        cases.append("## [Unreleased]\n~~~\n## [1.2.3]\n```\n" + release + "\n~~~\n### Added\n- **Real** FR-1\n" + release + "\n### Internal\n- FAIL\n")
    cases.extend(
        [
            "## [Unreleased]\n###\u2003Fixed\n####\u00a0Sub\nDEFAULT DEFAULT\n\nFR-1\n- **A #١٢**\n  - nested\n    + DEFAULT\n\t - FR-2\n### Fixed\n#### Sub\n",
            "## [Unreleased]\n### Changed\n- **Headline** (#١٢, ä/repo#٣). One. Two! Three?\n",
            "## [Unreleased]\n- spec-kitty merge\n\n- spec-kitty consolidate\n### Internal\n- `FR-1\nFAIL` FR-2 FR-2\n",
            "## [Unreleased]\n### Added\n- *****\n- **a\nb**\n### Unknown\n+ FAIL\n",
        ]
    )
    return cases


@pytest.mark.parametrize("text", adversarial_cases())
def test_native_matches_unicode_boundaries_and_parser_oddities(executor_binary: Path, tmp_path: Path, text: str) -> None:
    path = tmp_path / "CHANGELOG.md"
    path.write_bytes(text.encode())
    argv = ["--changelog", str(path)]
    expected = oracle_cli(argv)
    result = native_cli(executor_binary, tmp_path, argv)
    (tmp_path / "oracle.stdout.log").write_bytes(expected[1])
    assert (result.returncode, result.stdout, result.stderr) == expected


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--help"],
        ["-h"],
        ["--he"],
        ["--unknown"],
        ["--changelog"],
        ["--changelog", "--help"],
        ["--"],
        ["--changelog=missing.md"],
        ["--c", "missing.md"],
        ["--changelog", "-1"],
        ["--changelog", "-.2"],
        ["-hfoo"],
        ["--help=foo"],
    ],
)
def test_native_checker_flag_grammar_and_relative_resolution(executor_binary: Path, tmp_path: Path, argv: list[str]) -> None:
    expected = oracle_cli(argv)
    result = native_cli(executor_binary, tmp_path, argv)
    assert (result.returncode, result.stdout, result.stderr) == expected


@pytest.mark.parametrize("raw", [b"\xff", b"\xe1\x80", b"\xe0\x80", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xe1\x80A"])
def test_invalid_utf8_refuses_like_the_oracle(executor_binary: Path, tmp_path: Path, raw: bytes) -> None:
    path = tmp_path / "CHANGELOG.md"
    path.write_bytes(raw)
    argv = ["--changelog", str(path)]
    expected = oracle_cli(argv)
    result = native_cli(executor_binary, tmp_path, argv)
    assert (result.returncode, result.stdout, result.stderr) == expected


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"repository_root": str(ROOT)},
        {"repository_root": str(ROOT), "argv": [], "unknown": True},
        {"repository_root": str(ROOT), "argv": "--help"},
        {"repository_root": str(ROOT), "argv": [1]},
        {"repository_root": 1, "argv": []},
        {"repository_root": str(ROOT), "argv": ["--changelog", "bad\0path"]},
        {"repository_root": ".", "argv": []},
        {"repository_root": str(ROOT) + "/.", "argv": []},
        {"repository_root": str(ROOT) + "/", "argv": []},
    ],
)
def test_request_boundary_refuses_ambiguous_or_malformed_inputs(executor_binary: Path, tmp_path: Path, document: object) -> None:
    path = tmp_path / "request.json"
    path.write_text(json.dumps(document))
    result = subprocess.run([str(executor_binary), "changelog-style", str(path)], capture_output=True, timeout=30)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.startswith(b"changelog-style request refused: ")


@pytest.mark.parametrize("raw", ['{"repository_root":"a","repository_root":"b","argv":[]}', "{", "[]", "null"])
def test_request_json_is_strict(executor_binary: Path, tmp_path: Path, raw: str) -> None:
    path = tmp_path / "request.json"
    path.write_text(raw)
    result = subprocess.run([str(executor_binary), "changelog-style", str(path)], capture_output=True, timeout=30)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.startswith(b"changelog-style request refused: ")


def test_explicit_root_and_symlink_resolution_matches_oracle(executor_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.docs import check_changelog_style as oracle

    root = tmp_path / "repository"
    root.mkdir()
    (root / "nested").mkdir()
    real = root / "CHANGELOG.md"
    real.write_text("## [Unreleased]\n### Internal\n- FR-1\n")
    (root / "alias.md").symlink_to(real)
    monkeypatch.setattr(oracle, "REPO_ROOT", root)
    for path in ["CHANGELOG.md", "./CHANGELOG.md", "nested/../CHANGELOG.md", "alias.md", str(real)]:
        argv = ["--changelog=missing", "--c", path]
        result = native_cli(executor_binary, tmp_path, argv, root)
        assert (result.returncode, result.stdout, result.stderr) == oracle_cli(argv)
    alias = tmp_path / "repository-alias"
    alias.symlink_to(root, target_is_directory=True)
    result = native_cli(executor_binary, tmp_path, ["--help"], alias)
    assert result.returncode == 2
    assert b"AmbiguousRepositoryRoot" in result.stderr


def test_entire_unicode14_property_vector_matches_native(tmp_path: Path) -> None:
    import shutil
    import unicodedata

    assert unicodedata.unidata_version == "14.0.0", "this component's qualification oracle is explicitly Unicode 14"
    source = ROOT / "tools/zig/validation_unicode14.zig"
    (tmp_path / source.name).write_bytes(source.read_bytes())
    probe = tmp_path / "probe.zig"
    probe.write_text("""const std = @import("std");
const subject = @import("validation_unicode14.zig");
pub fn main(init: std.process.Init) !void {
    const output = try init.arena.allocator().alloc(u8, 0x110000);
    for (output, 0..) |*value, point| value.* = subject.properties(@intCast(point));
    try std.Io.File.stdout().writeStreamingAll(init.io, output);
}
""")
    image = tmp_path / "probe"
    built = subprocess.run(
        [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", str(probe), "-femit-bin=" + str(image)], capture_output=True, timeout=180
    )
    (tmp_path / "build.log").write_bytes(built.stdout + built.stderr)
    assert built.returncode == 0, built.stderr
    result = subprocess.run([str(image)], capture_output=True, timeout=30)
    expected = bytes(
        int(c.isalnum() or c == "_") | (2 * int(c.isdecimal())) | (4 * int(c.isspace())) | (8 * int(c.isprintable())) for c in map(chr, range(0x110000))
    )
    (tmp_path / "native-properties.bin").write_bytes(result.stdout)
    (tmp_path / "oracle-properties.bin").write_bytes(expected)
    assert result.returncode == 0
    assert result.stderr == b""
    assert result.stdout == expected


def qualified_component_inputs(candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, staged: str) -> dict[str, object]:
    """Private exact-source authority for this real component; no production routing change."""
    import os
    import platform
    from tests.local_validation.test_candidate import capture, digest, git
    from tests.local_validation.test_receipt import NATIVE_SOURCES, file_pin

    tools = repository / "tools/zig"
    tools.mkdir(parents=True)
    for source in NATIVE_SOURCES:
        (tools / source.name).write_bytes(source.read_bytes())
    changelog = repository / "CHANGELOG.md"
    changelog.write_text(staged)
    launcher = repository / "launcher.sh"
    launcher.write_text("#!/bin/sh\n# Private exact-source native component fixture.\n")
    lock = repository / "dependencies.lock"
    lock.write_text("unicode=14.0.0\n")
    destination = tmp_path / "owned evidence"
    component_request = tmp_path / "component.json"
    component_request.write_text(json.dumps({"repository_root": str(destination / "candidate"), "argv": ["--changelog", "CHANGELOG.md"]}))
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps({"scope": "private-exact-native-changelog-closure", "files": [file_pin(executor_binary), file_pin(component_request)]}))
    sources = [*NATIVE_SOURCES, runtime]
    limits = {"wall_ms": 5000, "cleanup_ms": 1000, "stdout_bytes": 65536, "stderr_bytes": 65536, "processes": 4, "resident_bytes": 268435456}
    argv = [str(executor_binary), "changelog-style", str(component_request)]
    architecture = {"arm64": "aarch64", "x86_64": "x86_64"}[platform.machine()]
    qualification = {
        "schema_version": 1,
        "scope": "exact-isolated-source-no-process-creation",
        "platform": architecture + "-macos",
        "argv": argv,
        "environment_names": [],
        "limits": limits,
        "program_path_hex": b"tools/zig/validation_changelog.zig".hex(),
        "program_sha256": digest((tools / "validation_changelog.zig").read_bytes()),
        "producer": {key: value for key, value in file_pin(executor_binary).items() if key in {"path", "sha256", "mode"}},
        "producer_sources": [file_pin(path) for path in sources],
        "producer_source_tool_sha256": digest(b"".join(path.read_bytes() for path in sources)),
        "process_source_sha256": digest((tools / "validation_process_darwin.zig").read_bytes()),
        "compiler_version": "0.16.0",
        "runtime_manifest_sha256": digest(runtime.read_bytes()),
        "runtime_files": [file_pin(executor_binary), file_pin(component_request)],
    }
    authority = repository / "gates.json"
    authority.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": {"path": "tools/zig/validation_changelog.zig", "sha256": qualification["program_sha256"], "role": "private-real-component"},
                "routing": {"filters": {"docs": ["*.md"]}, "job_gates": {"changelog": []}},
                "checks": {
                    "changelog": {
                        "argv": [argv],
                        "modes": ["full"],
                        "platforms": ["macos"],
                        "dependencies": [],
                        "environment": {},
                        "budgets": {
                            "sampled_processes" if key == "processes" else "sampled_resident_bytes" if key == "resident_bytes" else key: value
                            for key, value in limits.items()
                        },
                    }
                },
            }
        )
    )
    qualifications = repository / "qualifications.json"
    qualifications.write_text(json.dumps({"receipt_qualifications": [qualification]}))
    git(repository, "add", "--all")
    captured, _ = capture(candidate_binary, repository, tmp_path)
    assert captured.returncode == 0, captured.stderr
    manifest_path = destination / "candidate.json"
    files: list[dict[str, object]] = [
        {"role": role, "path": str(path), "candidate_path_hex": os.fsencode(path.relative_to(repository)).hex()}
        for role, path in [
            ("launcher", launcher),
            ("specification", authority),
            ("specification", qualifications),
            ("dependency_lock", lock),
            *(("native_source", tools / source.name) for source in NATIVE_SOURCES),
        ]
    ]
    files.extend({"role": "observed_dependency", "path": str(path), "candidate_path_hex": None} for path in [*sources, component_request])
    files.append({"role": "toolchain", "path": str(executor_binary), "candidate_path_hex": None})
    bind_request = tmp_path / "binding-request.json"
    bind_request.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "candidate_manifest": str(manifest_path),
                "files": files,
                "environment_names": [],
                "checks": [{"id": "changelog", "argv": [argv], "closure_proof": None}],
            }
        )
    )
    bound = subprocess.run([str(executor_binary), "bind", str(bind_request)], capture_output=True, timeout=30)
    assert bound.returncode == 0, bound.stderr
    binding = tmp_path / "binding.json"
    binding.write_bytes(bound.stdout)
    logs = tmp_path / "logs"
    logs.mkdir(mode=0o700)
    request = tmp_path / "execution.json"
    request.write_text(json.dumps({"binding": str(binding), "specification": str(authority), "mode": "full", "diagnostics": str(logs)}))
    return {"request": request, "logs": logs, "changelog": changelog, "component_request": component_request, "candidate": destination / "candidate"}


@pytest.mark.parametrize("staged_bad", [False, True])
def test_actual_component_qualification_runs_staged_changelog_and_retains_findings(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, staged_bad: bool
) -> None:
    from tests.local_validation.test_candidate import snapshot

    clean = "## [Unreleased]\n### Internal\n- Documentation corrected.\n"
    bad = "## [Unreleased]\n### Internal\n- FR-1\n"
    inputs = qualified_component_inputs(candidate_binary, executor_binary, repository, tmp_path, bad if staged_bad else clean)
    changelog = inputs["changelog"]
    assert isinstance(changelog, Path)
    changelog.write_text(clean if staged_bad else bad)
    before = snapshot(repository)
    result = subprocess.run([str(executor_binary), "execute", str(inputs["request"])], capture_output=True, timeout=30)
    assert snapshot(repository) == before
    logs = inputs["logs"]
    assert isinstance(logs, Path)
    report = json.loads((logs / "run.json").read_bytes())
    assert report["accepted"] is not staged_bad
    assert (result.returncode == 0) is not staged_bad
    row = report["results"][0]
    assert row["status"] == ("refused" if staged_bad else "passed")
    raw = Path(row["stdout_log"]["path"]).read_bytes()
    assert (b"[banned-token]" in raw) is staged_bad
    assert raw.endswith(b"1 error(s), 0 warning(s)\n" if staged_bad else b"0 error(s), 0 warning(s)\n")
    assert row["result"]["stdout_retained_bytes"] == len(raw)
    assert report["general_validator_qualification"] is False
    assert report["hook_installed"] is False


def test_actual_component_request_drift_refuses_before_effects(candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path) -> None:
    inputs = qualified_component_inputs(candidate_binary, executor_binary, repository, tmp_path, "## [Unreleased]\n")
    request = inputs["component_request"]
    assert isinstance(request, Path)
    request.write_text(request.read_text() + "\n")
    result = subprocess.run([str(executor_binary), "execute", str(inputs["request"])], capture_output=True, timeout=30)
    assert result.returncode != 0
    assert b"InputDrift" in result.stderr
    logs = inputs["logs"]
    assert isinstance(logs, Path)
    assert not list(logs.iterdir())


def test_native_component_operates_with_kernel_process_creation_denied(tmp_path: Path) -> None:
    """Real kernel denial, checked by an attempted fork, surrounds the component call."""
    import shutil
    import sys

    if sys.platform != "darwin":
        pytest.skip("this kernel-denial qualification is macOS only")
    for name in ["validation_changelog.zig", "validation_unicode14.zig"]:
        (tmp_path / name).write_bytes((ROOT / "tools/zig" / name).read_bytes())
    probe = tmp_path / "deny-process.zig"
    probe.write_text(r"""const std = @import("std");
const component = @import("validation_changelog.zig");
extern "c" fn sandbox_init([*:0]const u8, u64, *?[*:0]u8) c_int;
extern "c" fn sandbox_free_error([*:0]u8) void;
extern "c" fn fork() c_int;
extern "c" fn waitpid(c_int, *c_int, c_int) c_int;
extern "c" fn execv([*:0]const u8, [*:null]const ?[*:0]const u8) c_int;
pub fn main(init: std.process.Init) !void {
    const args = try init.minimal.args.toSlice(init.arena.allocator());
    if (args.len == 2 and std.mem.eql(u8, args[1], "baseline")) {
        const child = fork();
        if (child == 0) std.process.exit(0);
        if (child < 0) return error.BaselineForkUnavailable;
        var status: c_int = 0;
        if (waitpid(child, &status, 0) != child or status != 0) return error.BaselineJoinFailed;
        try std.Io.File.stdout().writeStreamingAll(init.io, "baseline-fork-joined\n");
        return;
    }
    const command = [_:null]?[*:0]const u8{"/usr/bin/true"};
    if (args.len == 2 and std.mem.eql(u8, args[1], "baseline-exec")) {
        _ = execv("/usr/bin/true", &command);
        return error.BaselineExecUnavailable;
    }
    var message: ?[*:0]u8 = null;
    if (sandbox_init("(version 1)(allow default)(deny process-fork)(deny process-exec)", 0, &message) != 0) {
        if (message) |value| sandbox_free_error(value);
        return error.SandboxDenialUnavailable;
    }
    const child = fork();
    if (child == 0) std.process.exit(99);
    if (child > 0) {
        var status: c_int = 0;
        _ = waitpid(child, &status, 0);
        return error.KernelForkDenialNotEffective;
    }
    if (std.c.errno(child) != .PERM) return error.UnexpectedForkFailure;
    const executed = execv("/usr/bin/true", &command);
    if (executed != -1 or std.c.errno(executed) != .PERM) return error.KernelExecDenialNotEffective;
    if (args.len != 3 or !std.mem.eql(u8, args[1], "changelog-style")) return error.InvalidArguments;
    const code = try component.command(init, args[2]);
    std.process.exit(code);
}
""")
    image = tmp_path / "deny-process"
    built = subprocess.run(
        [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", "-lsandbox", str(probe), "-femit-bin=" + str(image)],
        capture_output=True,
        timeout=180,
    )
    (tmp_path / "build.log").write_bytes(built.stdout + built.stderr)
    assert built.returncode == 0, built.stderr
    baseline = subprocess.run([str(image), "baseline"], capture_output=True, timeout=30)
    (tmp_path / "baseline.stdout.log").write_bytes(baseline.stdout)
    (tmp_path / "baseline.stderr.log").write_bytes(baseline.stderr)
    assert baseline.returncode == 0, baseline.stderr
    assert baseline.stdout == b"baseline-fork-joined\n"
    baseline_exec = subprocess.run([str(image), "baseline-exec"], capture_output=True, timeout=30)
    (tmp_path / "baseline-exec.stdout.log").write_bytes(baseline_exec.stdout)
    (tmp_path / "baseline-exec.stderr.log").write_bytes(baseline_exec.stderr)
    assert baseline_exec.returncode == 0, baseline_exec.stderr
    path = tmp_path / "CHANGELOG.md"
    path.write_text("## [Unreleased]\n### Internal\n- FR-1\n")
    argv = ["--changelog", str(path)]
    result = native_cli(image, tmp_path, argv)
    assert (result.returncode, result.stdout, result.stderr) == oracle_cli(argv)


@pytest.mark.parametrize("name", ["missing'quoted", 'missing"quoted', "both'\"quotes", "slash\\line\n\t\r", "\x01\x85\u2003\u0378\U000e0000", "x" * 300])
def test_unreadable_filename_diagnostics_match_python_repr(executor_binary: Path, tmp_path: Path, name: str) -> None:
    argv = ["--changelog", str(tmp_path / name)]
    result = native_cli(executor_binary, tmp_path, argv)
    assert (result.returncode, result.stdout, result.stderr) == oracle_cli(argv)


def test_directory_loop_and_not_directory_errors_match_oracle(executor_binary: Path, tmp_path: Path) -> None:
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    file = tmp_path / "ordinary-file"
    file.write_text("ordinary")
    for path in [tmp_path, loop, file / "child"]:
        argv = ["--changelog", str(path)]
        result = native_cli(executor_binary, tmp_path, argv)
        assert (result.returncode, result.stdout, result.stderr) == oracle_cli(argv)


def test_filesystem_root_display_path_matches_oracle(executor_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.docs import check_changelog_style as oracle

    path = tmp_path / "CHANGELOG.md"
    path.write_text("## [Unreleased]\n### Internal\n- FR-1\n")
    monkeypatch.setattr(oracle, "REPO_ROOT", Path("/"))
    argv = ["--changelog", str(path)]
    result = native_cli(executor_binary, tmp_path, argv, Path("/"))
    assert (result.returncode, result.stdout, result.stderr) == oracle_cli(argv)


@pytest.mark.parametrize("columns", ["1", "2", "3", "12", "20", "40", "55", "70", "78", "80", "100", "140", "0", "-1", "invalid"])
@pytest.mark.parametrize("argv", [["--help"], ["--unknown"]])
def test_captured_help_and_usage_wrapping_matches_python(
    executor_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, columns: str, argv: list[str]
) -> None:
    monkeypatch.setenv("COLUMNS", columns)
    expected = oracle_cli(argv)
    result = native_cli(executor_binary, tmp_path, argv)
    assert (result.returncode, result.stdout, result.stderr) == expected


@pytest.mark.parametrize("filename", ["-1\n", "-.2\n", "-1.2\n", "-1\n\n", "-1\r\n", "-1x\n"])
def test_review_final_lf_negative_number_filename_parity(executor_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str) -> None:
    from scripts.docs import check_changelog_style as oracle

    (tmp_path / filename).write_text("## [Unreleased]\n### Internal\n- Documentation corrected.\n")
    monkeypatch.setattr(oracle, "REPO_ROOT", tmp_path)
    argv = ["--changelog", filename]
    result = native_cli(executor_binary, tmp_path, argv, tmp_path)
    assert (result.returncode, result.stdout, result.stderr) == oracle_cli(argv)


@pytest.mark.parametrize("columns", [" 40", "40 ", "\t40\n", "1_00", "+40"])
def test_review_columns_integer_whitespace_parity(executor_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, columns: str) -> None:
    monkeypatch.setenv("COLUMNS", columns)
    argv = ["--help"]
    result = native_cli(executor_binary, tmp_path, argv)
    assert (result.returncode, result.stdout, result.stderr) == oracle_cli(argv)


@pytest.mark.parametrize("value", ["a'b", "line\n\\tail"])
def test_review_explicit_help_value_representation_parity(executor_binary: Path, tmp_path: Path, value: str) -> None:
    argv = ["--help=" + value]
    result = native_cli(executor_binary, tmp_path, argv)
    assert (result.returncode, result.stdout, result.stderr) == oracle_cli(argv)


@pytest.mark.parametrize("columns", ["4__0", "_40", "40_", "4_0", "1_00", "+40", "+-40", "4_a", ""])
def test_review_ascii_columns_integer_grammar(executor_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, columns: str) -> None:
    monkeypatch.setenv("COLUMNS", columns)
    argv = ["--help"]
    result = native_cli(executor_binary, tmp_path, argv)
    assert (result.returncode, result.stdout, result.stderr) == oracle_cli(argv)


@pytest.mark.parametrize("argument", ["-h=", "-h=foo", "-h==foo", "-hfoo", "-hfoo=bar"])
def test_review_short_help_equals_and_compact_neighbors(executor_binary: Path, tmp_path: Path, argument: str) -> None:
    result = native_cli(executor_binary, tmp_path, [argument])
    assert (result.returncode, result.stdout, result.stderr) == oracle_cli([argument])
