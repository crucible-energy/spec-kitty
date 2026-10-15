"""Finite native foreground sampler; existing Python state consumer is authority.

The public operation is deliberately narrower than the Python CLI. It neither
starts a detached process nor adopts the original Linux check recipe.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import sys
import time
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts.ci import memory_sampler as oracle
from tests.local_validation.test_candidate import ROOT, digest
from tests.local_validation.test_receipt import NATIVE_SOURCES, retain_native_build_metadata


@pytest.fixture(scope="session")
def sampler_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    supplied = os.environ.get("SPEC_KITTY_NATIVE_EXECUTION_BINDING")
    if supplied:
        binding = json.loads(Path(supplied).read_bytes())
        for name, expected in binding["sources"].items():
            assert digest((ROOT / name).read_bytes()) == expected
        image = Path(binding["image"])
        assert digest(image.read_bytes()) == binding["image_sha256"]
        return image
    image = tmp_path_factory.mktemp("native-memory-sampler") / "executor"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(ROOT / "tools/zig/validation_execution.zig"), "-femit-bin=" + str(image)]
    compiled = subprocess.run(argv, check=True, capture_output=True, timeout=120)
    retain_native_build_metadata(image, NATIVE_SOURCES, argv, compiled)
    return image


def invoke(image: Path, operation: str, path: Path, directory: Path) -> subprocess.CompletedProcess[bytes]:
    argv = [str(image), operation, str(path)]
    stdout, stderr = directory / "invocation.stdout.log", directory / "invocation.stderr.log"
    with stdout.open("wb") as out, stderr.open("wb") as err:
        child = subprocess.Popen(argv, stdout=out, stderr=err)
        try:
            code = child.wait(timeout=15)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
    (directory / "invocation.json").write_text(json.dumps({"argv": argv, "pid": child.pid, "joined": True, "exact_exit_code": code}))
    return subprocess.CompletedProcess(argv, code, stdout.read_bytes(), stderr.read_bytes())


def request(directory: Path, **changes: Any) -> tuple[Path, dict[str, Any]]:
    proc = directory / "proc"
    proc.mkdir()
    (proc / "meminfo").write_bytes(b"MemTotal: 16384 kB\nMemAvailable: 8192 kB\n")
    value = {
        "schema_version": 1,
        "destination": str(directory / "new-state"),
        "proc_root": str(proc.resolve()),
        "interval_ms": 0,
        "max_samples": 3,
        "wall_ms": 5000,
        **changes,
    }
    path = directory / "request.json"
    path.write_text(json.dumps(value, sort_keys=True))
    return path, value


def test_existing_native_entry_and_bound_image_are_usable(sampler_binary: Path, tmp_path: Path) -> None:
    path = tmp_path / "help.json"
    path.write_text(json.dumps({"repository_root": str(ROOT), "argv": ["--help"]}))
    result = invoke(sampler_binary, "changelog-style", path, tmp_path)
    assert result.returncode == 0 and b"usage:" in result.stdout and result.stderr == b""


def test_native_memory_sample_produces_state_for_existing_python_consumer(sampler_binary: Path, tmp_path: Path) -> None:
    path, value = request(tmp_path)
    result = invoke(sampler_binary, "memory-sample", path, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == b""
    output = Path(value["destination"]) / "state.json"
    raw = output.read_text()
    state = oracle.from_json(raw)
    assert state is not None
    assert set(json.loads(raw)) == {"baseline_bytes", "elapsed_seconds", "peak_bytes", "pid", "samples", "source"}
    assert state.baseline_bytes == state.peak_bytes == 8192 * 1024
    assert state.samples == value["max_samples"] == 3 and state.source == "meminfo"
    assert state.pid == json.loads((tmp_path / "invocation.json").read_bytes())["pid"]
    assert 0 <= state.elapsed_seconds <= value["wall_ms"] / 1000
    assert oracle.render_report(state, None, warn_bytes=10 * oracle.GIB, error_bytes=12 * oracle.GIB)[0].startswith(
        "peak_rss_bytes=8388608 source=meminfo baseline_bytes=8388608 delta_bytes=0 samples=3 elapsed_s="
    )
    assert Path(value["destination"]).stat().st_mode & 0o777 == 0o700 and output.stat().st_mode & 0o777 == 0o600
    assert not list(Path(value["destination"]).glob("*.tmp")) and not list(Path(value["destination"]).glob("*.pid"))


@pytest.mark.parametrize(
    "body",
    [
        b"MemTotal: 1 kB\nMemAvailable: 5 kB\n",
        b" MemTotal \t: 10 ignored\x1eMemTotal: 12 kB\x1dMemTotal: bad kB\r\nMemAvailable:\x1f2 ignored\r\n",
        b"MemTotal: 18446744073709551615 kB\nMemAvailable: 0 kB\n",
        b"MemTotal: 00000000000000000100\vMemAvailable: 00004\fUnrelated: 5 weird units\n",
        b"MemTotal: 5 kB\nMemAvailable: +1 kB\n",
        b"MemTotal: 10 kB\nMemAvailable: 5 kB\nMemTotal: 1_2 kB\n",
        b"MemTotal: 10 kB\nMemAvailable: 5 kB\n" + b"x" * (65536 - len(b"MemTotal: 10 kB\nMemAvailable: 5 kB\n")),
        b"",
    ],
)
def test_ascii_state_matches_unchanged_python_fold(sampler_binary: Path, tmp_path: Path, body: bytes) -> None:
    path, value = request(tmp_path)
    (Path(value["proc_root"]) / "meminfo").write_bytes(body)
    result = invoke(sampler_binary, "memory-sample", path, tmp_path)
    assert result.returncode == 0, result.stderr
    state = oracle.from_json((Path(value["destination"]) / "state.json").read_text())
    assert state is not None
    info = oracle.parse_meminfo(body.decode("ascii"))
    if info is None:
        assert (state.baseline_bytes, state.peak_bytes, state.samples, state.elapsed_seconds, state.source) == (0, 0, 0, 0.0, "unavailable")
    else:
        used = oracle.used_bytes(info)
        assert state.baseline_bytes == state.peak_bytes == used
        assert state.samples == 3 and state.source == "meminfo"
    assert state.pid == json.loads((tmp_path / "invocation.json").read_bytes())["pid"]
    assert len(oracle.render_report(state, None, warn_bytes=10 * oracle.GIB, error_bytes=12 * oracle.GIB)) in {1, 2}


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (b"MemTotal: 18446744073709551616\nMemAvailable: 0\n", b"UnsupportedSamplerValue"),
        (b"Unrelated: 18446744073709551616\n", b"UnsupportedSamplerValue"),
        ("MemTotal: １２\nMemAvailable: 0\n".encode(), b"UnsupportedSamplerEncoding"),
        (b"MemTotal: \xff\nMemAvailable: 0\n", b"UnsupportedSamplerEncoding"),
        (b"X" * 65537, b"SamplerInputLimit"),
    ],
)
def test_unsupported_data_refuses_instead_of_becoming_unavailable(sampler_binary: Path, tmp_path: Path, body: bytes, reason: bytes) -> None:
    path, value = request(tmp_path)
    source = Path(value["proc_root"]) / "meminfo"
    source.write_bytes(body)
    result = invoke(sampler_binary, "memory-sample", path, tmp_path)
    assert result.returncode == 1 and reason in result.stderr
    assert source.read_bytes() == body and not (Path(value["destination"]) / "state.json").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"schema_version": True},
        {"max_samples": 0},
        {"max_samples": -1},
        {"max_samples": 10001},
        {"max_samples": 1.0},
        {"max_samples": "1"},
        {"max_samples": None},
        {"interval_ms": -1},
        {"interval_ms": 60001},
        {"wall_ms": 0},
        {"wall_ms": 3600001},
        {"extra": "unsupported"},
    ],
)
def test_closed_request_refuses_invalid_types_and_ranges(sampler_binary: Path, tmp_path: Path, change: dict[str, Any]) -> None:
    path, value = request(tmp_path, **change)
    result = invoke(sampler_binary, "memory-sample", path, tmp_path)
    assert result.returncode == 1 and b"InvalidSamplerRequest" in result.stderr
    assert not Path(value["destination"]).exists()


@pytest.mark.parametrize("raw", [b'{"schema_version":1,"schema_version":1}', b"[]", b'{"interval_ms":NaN}', b"{}", b'"x"', b"\xff", b" " * 65537])
def test_request_wire_errors_have_no_output_effects(sampler_binary: Path, tmp_path: Path, raw: bytes) -> None:
    path, value = request(tmp_path)
    path.write_bytes(raw)
    result = invoke(sampler_binary, "memory-sample", path, tmp_path)
    assert result.returncode == 1
    assert not Path(value["destination"]).exists()


@pytest.mark.parametrize("kind", ["fifo", "symlink", "directory"])
def test_nonregular_meminfo_refuses_without_opening_a_stream(sampler_binary: Path, tmp_path: Path, kind: str) -> None:
    path, value = request(tmp_path)
    source = Path(value["proc_root"]) / "meminfo"
    source.unlink()
    if kind == "fifo":
        os.mkfifo(source, 0o600)
    elif kind == "symlink":
        target = tmp_path / "unrelated-source"
        target.write_bytes(b"preserve\n")
        source.symlink_to(target)
    else:
        source.mkdir()
    result = invoke(sampler_binary, "memory-sample", path, tmp_path)
    assert result.returncode == 1 and b"UnsafeSamplerInput" in result.stderr
    assert not (Path(value["destination"]) / "state.json").exists()
    if kind == "symlink":
        assert source.is_symlink() and target.read_bytes() == b"preserve\n"


def wait_state(child: subprocess.Popen[bytes], output: Path, predicate: Any, timeout: float = 10) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if output.exists():
            state = oracle.from_json(output.read_text())
            assert state is not None, "atomic state must always be complete"
            if predicate(state):
                return state
        assert child.poll() is None, "sampler ended before the observed state boundary"
        time.sleep(0.002)
    raise AssertionError("owned sampler did not produce the expected bounded state")


def replace_meminfo(proc: Path, body: bytes, record: Path) -> None:
    record.write_bytes(body)
    record.chmod(0o400)
    temporary = proc / "next-meminfo"
    temporary.write_bytes(body)
    temporary.replace(proc / "meminfo")


def test_attempts_include_missing_reads_and_first_valid_sample_sets_baseline(sampler_binary: Path, tmp_path: Path) -> None:
    path, value = request(tmp_path, interval_ms=500)
    proc, output = Path(value["proc_root"]), Path(value["destination"]) / "state.json"
    (proc / "meminfo").unlink()
    stdout, stderr = tmp_path / "invocation.stdout.log", tmp_path / "invocation.stderr.log"
    with stdout.open("wb") as out, stderr.open("wb") as err:
        child = subprocess.Popen([str(sampler_binary), "memory-sample", str(path)], stdout=out, stderr=err)
        try:
            missing = wait_state(child, output, lambda state: state.source == "unavailable")
            assert missing.samples == 0 and missing.elapsed_seconds == 0.0
            replace_meminfo(proc, b"MemTotal: 10 kB\nMemAvailable: 2 kB\n", tmp_path / "first-valid.meminfo")
            first = wait_state(child, output, lambda state: state.samples == 1)
            replace_meminfo(proc, b"MemTotal: 10 kB\nMemAvailable: 6 kB\n", tmp_path / "lower.meminfo")
            code = child.wait(timeout=10)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
    final = oracle.from_json(output.read_text())
    assert final is not None and code == 0, stderr.read_bytes()
    assert final.samples == 2 and final.baseline_bytes == final.peak_bytes == 8192
    assert first.elapsed_seconds <= final.elapsed_seconds <= value["wall_ms"] / 1000
    assert final.pid == missing.pid == first.pid == child.pid
    (tmp_path / "observed-states.json").write_text(
        json.dumps(
            {
                "pid": child.pid,
                "exact_exit_code": code,
                "first_elapsed": first.elapsed_seconds,
                "final_elapsed": final.elapsed_seconds,
                "successful_samples": final.samples,
            }
        )
    )


@pytest.mark.parametrize("backend", ["native", "python"])
def test_sigterm_during_wait_writes_a_final_sample(backend: str, sampler_binary: Path, tmp_path: Path) -> None:
    path, value = request(tmp_path, interval_ms=2000, max_samples=10)
    proc, destination = Path(value["proc_root"]), Path(value["destination"])
    output = destination / "state.json"
    argv = [str(sampler_binary), "memory-sample", str(path)]
    if backend == "python":
        destination.mkdir(mode=0o700)
        argv = [
            sys.executable,
            str(Path(oracle.__file__).resolve()),
            "sample",
            "--out",
            str(output),
            "--proc-root",
            str(proc),
            "--interval",
            "2.0",
            "--max-samples",
            "10",
        ]
    stdout, stderr = tmp_path / "invocation.stdout.log", tmp_path / "invocation.stderr.log"
    with stdout.open("wb") as out, stderr.open("wb") as err:
        child = subprocess.Popen(argv, stdout=out, stderr=err)
        try:
            first = wait_state(child, output, lambda state: state.samples == 1)
            replace_meminfo(proc, b"MemTotal: 16384 kB\nMemAvailable: 4096 kB\n", tmp_path / "final.meminfo")
            child.send_signal(signal.SIGTERM)
            code = child.wait(timeout=10)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
    final = oracle.from_json(output.read_text())
    assert final is not None
    assert final.pid == first.pid == child.pid and final.samples == 2
    assert final.baseline_bytes == 8388608 and final.peak_bytes == 12582912
    assert first.elapsed_seconds <= final.elapsed_seconds <= value["wall_ms"] / 1000
    assert code == (1 if backend == "native" else 0)
    if backend == "native":
        assert b"Cancelled" in stderr.read_bytes()
    (tmp_path / "signal-result.json").write_text(
        json.dumps(
            {
                "argv": argv,
                "pid": child.pid,
                "signal": int(signal.SIGTERM),
                "exact_exit_code": code,
                "first_elapsed": first.elapsed_seconds,
                "final_elapsed": final.elapsed_seconds,
                "source_compatible_final_samples": final.samples,
            }
        )
    )


def test_deadline_prevents_another_sample_and_preserves_complete_state(sampler_binary: Path, tmp_path: Path) -> None:
    path, value = request(tmp_path, interval_ms=2000, max_samples=10, wall_ms=500)
    result = invoke(sampler_binary, "memory-sample", path, tmp_path)
    assert result.returncode == 1 and b"OperationDeadlineExceeded" in result.stderr
    state = oracle.from_json((Path(value["destination"]) / "state.json").read_text())
    assert state is not None and state.samples == 1 and state.baseline_bytes == state.peak_bytes == 8388608
    assert state.pid == json.loads((tmp_path / "invocation.json").read_bytes())["pid"]


@pytest.mark.parametrize("kind", ["existing-file", "existing-directory", "destination-symlink", "proc-symlink", "public-parent", "dot-path", "relative"])
def test_initial_path_custody_refuses_without_overwriting_existing_data(sampler_binary: Path, tmp_path: Path, kind: str) -> None:
    path, value = request(tmp_path)
    destination = Path(value["destination"])
    sentinel = tmp_path / "preserved"
    sentinel.write_bytes(b"preserve\n")
    if kind == "existing-file":
        destination.write_bytes(b"preserve\n")
    elif kind == "existing-directory":
        destination.mkdir()
        (destination / "keep").write_bytes(b"preserve\n")
    elif kind == "destination-symlink":
        destination.symlink_to(sentinel)
    elif kind == "proc-symlink":
        alias = tmp_path / "proc-alias"
        alias.symlink_to(value["proc_root"], target_is_directory=True)
        value["proc_root"] = str(alias)
    elif kind == "public-parent":
        parent = tmp_path / "public"
        parent.mkdir(mode=0o755)
        parent.chmod(0o755)
        value["destination"] = str(parent / "new-state")
    elif kind == "dot-path":
        value["destination"] = str(tmp_path) + "/./new-state"
    else:
        value["destination"] = "relative-state"
    path.write_text(json.dumps(value))
    result = invoke(sampler_binary, "memory-sample", path, tmp_path)
    reasons = {
        "existing-file": b"SamplerDestinationExists",
        "existing-directory": b"SamplerDestinationExists",
        "destination-symlink": b"SamplerDestinationExists",
        "proc-symlink": b"UnsafeSamplerPath",
        "public-parent": b"UnsafeSamplerDirectory",
        "dot-path": b"InvalidSamplerPath",
        "relative": b"InvalidSamplerPath",
    }
    assert result.returncode == 1 and reasons[kind] in result.stderr and sentinel.read_bytes() == b"preserve\n"
    if kind == "existing-file":
        assert destination.read_bytes() == b"preserve\n"
    if kind == "existing-directory":
        assert (destination / "keep").read_bytes() == b"preserve\n"
    if kind == "destination-symlink":
        assert destination.is_symlink()


@pytest.mark.parametrize(
    "kind",
    ["input-fifo", "input-symlink", "output-symlink", "output-hardlink", "output-edited", "foreign-temp", "destination-swap", "proc-root-swap", "parent-public"],
)
def test_between_sample_substitution_refuses_and_preserves_unowned_data(sampler_binary: Path, tmp_path: Path, kind: str) -> None:
    path, value = request(tmp_path, interval_ms=500, max_samples=10)
    proc, destination = Path(value["proc_root"]), Path(value["destination"])
    output = destination / "state.json"
    sentinel = tmp_path / "preserved"
    sentinel.write_bytes(b"preserve\n")
    stdout, stderr = tmp_path / "invocation.stdout.log", tmp_path / "invocation.stderr.log"
    with stdout.open("wb") as out, stderr.open("wb") as err:
        child = subprocess.Popen([str(sampler_binary), "memory-sample", str(path)], stdout=out, stderr=err)
        try:
            first = wait_state(child, output, lambda state: state.samples == 1)
            prior = output.read_bytes()
            if kind.startswith("input-"):
                (proc / "meminfo").unlink()
                if kind == "input-fifo":
                    os.mkfifo(proc / "meminfo", 0o600)
                else:
                    (proc / "meminfo").symlink_to(sentinel)
            elif kind == "output-symlink":
                output.unlink()
                output.symlink_to(sentinel)
            elif kind == "output-hardlink":
                os.link(output, destination / "unowned-link")
            elif kind == "output-edited":
                output.write_bytes(b"preserve\n")
            elif kind == "foreign-temp":
                (destination / "state.tmp").write_bytes(b"preserve\n")
            elif kind == "destination-swap":
                destination.rename(tmp_path / "original-destination")
                destination.mkdir()
                (destination / "keep").write_bytes(b"preserve\n")
            elif kind == "proc-root-swap":
                proc.rename(tmp_path / "original-proc")
                proc.mkdir()
                (proc / "meminfo").write_bytes(b"preserve\n")
            else:
                tmp_path.chmod(0o755)
            code = child.wait(timeout=10)
        finally:
            tmp_path.chmod(0o700)
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
    reasons = {
        "input-fifo": b"UnsafeSamplerInput",
        "input-symlink": b"UnsafeSamplerInput",
        "output-symlink": b"SamplerOutputDrift",
        "output-hardlink": b"SamplerOutputDrift",
        "output-edited": b"SamplerOutputDrift",
        "foreign-temp": b"SamplerOutputDrift",
        "destination-swap": b"SamplerDirectoryDrift",
        "proc-root-swap": b"SamplerDirectoryDrift",
        "parent-public": b"SamplerDirectoryDrift",
    }
    assert code == 1 and reasons[kind] in stderr.read_bytes() and sentinel.read_bytes() == b"preserve\n", stderr.read_bytes()
    assert first.pid == child.pid
    if kind == "destination-swap":
        assert (destination / "keep").read_bytes() == b"preserve\n" and (tmp_path / "original-destination/state.json").read_bytes() == prior
    elif kind == "output-edited":
        assert output.read_bytes() == b"preserve\n"
    elif kind == "output-symlink":
        assert output.is_symlink()
    else:
        assert output.read_bytes() == prior
    if kind == "foreign-temp":
        assert (destination / "state.tmp").read_bytes() == b"preserve\n"


@pytest.mark.parametrize("primary", ["encoding", "deadline", "encoding-sigterm"])
@pytest.mark.parametrize("custody", ["destination", "state"])
def test_final_custody_failure_outranks_primary_data_signal_or_deadline_failure(sampler_binary: Path, tmp_path: Path, primary: str, custody: str) -> None:
    path, value = request(tmp_path, interval_ms=2000 if primary != "encoding" else 300, max_samples=10, wall_ms=500 if primary == "deadline" else 5000)
    proc, destination = Path(value["proc_root"]), Path(value["destination"])
    output = destination / "state.json"
    argv = [str(sampler_binary), "memory-sample", str(path)]
    stdout, stderr = tmp_path / "invocation.stdout.log", tmp_path / "invocation.stderr.log"
    with stdout.open("wb") as out, stderr.open("wb") as err:
        child = subprocess.Popen(argv, stdout=out, stderr=err)
        try:
            first = wait_state(child, output, lambda state: state.samples == 1)
            prior = output.read_bytes()
            if custody == "destination":
                destination.rename(tmp_path / "original-destination")
                destination.mkdir(mode=0o700)
                foreign = destination / "keep"
                foreign.write_bytes(b"foreign marker\n")
                retained = tmp_path / "original-destination/state.json"
                expected = b"SamplerDirectoryDrift"
            else:
                retained = destination / "retained-state"
                output.rename(retained)
                output.write_bytes(b"foreign marker\n")
                foreign = output
                expected = b"SamplerOutputDrift"
            if primary.startswith("encoding"):
                replace_meminfo(proc, b"\xff", tmp_path / "unsupported.meminfo")
            if primary == "encoding-sigterm":
                child.send_signal(signal.SIGTERM)
            code = child.wait(timeout=10)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
    diagnostic = stderr.read_bytes()
    (tmp_path / "combined-result.json").write_text(
        json.dumps(
            {
                "argv": argv,
                "pid": child.pid,
                "joined": True,
                "exact_exit_code": code,
                "first_state_pid": first.pid,
                "first_state_samples": first.samples,
                "primary": primary,
                "custody": custody,
                "expected_custody_reason": expected.decode(),
                "actual_diagnostic": diagnostic.decode(),
                "prior_state_preserved": retained.read_bytes() == prior,
                "foreign_object_preserved": foreign.read_bytes() == b"foreign marker\n",
                "signal": int(signal.SIGTERM) if primary == "encoding-sigterm" else None,
            }
        )
    )
    assert first.pid == child.pid and first.samples == 1
    assert retained.read_bytes() == prior and foreign.read_bytes() == b"foreign marker\n"
    assert code == 1 and expected in diagnostic and stdout.read_bytes() == b"", diagnostic


OWNERSHIP_PROBE = r"""const std = @import("std");
const component = @import("validation_memory_sampler.zig");
const owner = @import("validation_process_darwin.zig");
const c = @cImport({ @cInclude("signal.h"); });
extern "c" fn sandbox_init([*:0]const u8, u64, *?[*:0]u8) c_int;
extern "c" fn sandbox_free_error([*:0]u8) void;
extern "c" fn fork() c_int;
extern "c" fn waitpid(c_int, *c_int, c_int) c_int;
extern "c" fn execv([*:0]const u8, [*:null]const ?[*:0]const u8) c_int;
var received = std.atomic.Value(u32).init(0);
fn prior(signal: c_int) callconv(.c) void {
    _ = received.fetchOr(if (signal == c.SIGINT) 1 else 2, .monotonic);
}
fn require(value: bool) !void { if (!value) return error.ActualOwnershipControlFailed; }
fn checkPrior() !void {
    try require(c.raise(c.SIGINT) == 0 and c.raise(c.SIGTERM) == 0);
    try require(received.load(.monotonic) == 3);
    var next = try owner.beginSamplingSignals();
    try require(owner.samplingSignal() == 0);
    try require(try owner.restoreSamplingSignals(&next) == 0);
}
pub fn main(init: std.process.Init) !void {
    const a = init.arena.allocator();
    const args = try init.minimal.args.toSlice(a);
    if (args.len < 2) return error.InvalidArguments;
    const command = [_:null]?[*:0]const u8{"/usr/bin/true"};
    if (std.mem.eql(u8, args[1], "baseline-fork")) {
        const child = fork();
        if (child == 0) std.process.exit(0);
        if (child < 0) return error.BaselineForkUnavailable;
        var status: c_int = 0;
        try require(waitpid(child, &status, 0) == child and status == 0);
        try std.Io.File.stdout().writeStreamingAll(init.io, "baseline-fork-joined\n");
        return;
    }
    if (std.mem.eql(u8, args[1], "baseline-exec")) {
        _ = execv("/usr/bin/true", &command);
        return error.BaselineExecUnavailable;
    }
    if (args.len < 3) return error.InvalidArguments;
    if (std.mem.eql(u8, args[1], "deny")) {
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
        try require(std.c.errno(child) == .PERM);
        const executed = execv("/usr/bin/true", &command);
        try require(executed == -1 and std.c.errno(executed) == .PERM);
        try require(try component.command(init, args[2]) == 0);
        try std.Io.File.stdout().writeStreamingAll(init.io, "fork-and-exec-denied;sampler-completed\n");
        return;
    }
    var action = std.mem.zeroes(c.struct_sigaction);
    action.__sigaction_u.__sa_handler = prior;
    try require(c.sigemptyset(&action.sa_mask) == 0);
    var previous_int: c.struct_sigaction = undefined;
    var previous_term: c.struct_sigaction = undefined;
    try require(c.sigaction(c.SIGINT, &action, &previous_int) == 0);
    defer _ = c.sigaction(c.SIGINT, &previous_int, null);
    try require(c.sigaction(c.SIGTERM, &action, &previous_term) == 0);
    defer _ = c.sigaction(c.SIGTERM, &previous_term, null);
    if (std.mem.eql(u8, args[1], "busy")) {
        var scope = try owner.CheckScope.begin(a, init.io, .{ .wall_ms = 5000 }, 64);
        defer scope.deinit(a);
        var refusal: ?anyerror = null;
        _ = component.command(init, args[2]) catch |failure| blk: { refusal = failure; break :blk 1; };
        try require(refusal != null and std.mem.eql(u8, @errorName(refusal.?), "SignalBridgeBusy"));
        try require(c.raise(c.SIGTERM) == 0);
        scope.ready(init.io) catch |failure| { try require(failure == error.OperationCancelled); };
        const result = try scope.finish(a, init.io);
        defer result.deinit(a);
        try require(result.failure == .cancelled);
    } else {
        if (args.len != 4) return error.InvalidArguments;
        var refusal: ?anyerror = null;
        _ = component.command(init, args[2]) catch |failure| blk: { refusal = failure; break :blk 1; };
        if (std.mem.eql(u8, args[3], "success")) try require(refusal == null)
        else try require(refusal != null and std.mem.eql(u8, @errorName(refusal.?), args[3]));
    }
    try checkPrior();
    try std.Io.File.stdout().writeStreamingAll(init.io, "prior-signals-restored;owner-released\n");
}
"""


@pytest.fixture(scope="session")
def ownership_probe(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if sys.platform != "darwin":
        pytest.skip("actual signal/kernel-denial component controls are Darwin only")
    build = tmp_path_factory.mktemp("sampler-ownership-probe")
    for source in NATIVE_SOURCES:
        shutil.copyfile(source, build / source.name)
    source = build / "main.zig"
    source.write_text(OWNERSHIP_PROBE)
    image = build / "probe"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", "-lsandbox", str(source), "-femit-bin=" + str(image)]
    compiled = subprocess.run(argv, capture_output=True, timeout=120)
    (build / "build.stdout.log").write_bytes(compiled.stdout)
    (build / "build.stderr.log").write_bytes(compiled.stderr)
    assert compiled.returncode == 0, compiled.stderr
    retain_native_build_metadata(image, [source, *NATIVE_SOURCES], argv, compiled)
    return image


def test_active_check_scope_cannot_be_replaced_by_a_sampler_owner(ownership_probe: Path, tmp_path: Path) -> None:
    path, value = request(tmp_path)
    result = invoke(ownership_probe, "busy", path, tmp_path)
    assert result.returncode == 0 and result.stdout == b"prior-signals-restored;owner-released\n", result.stderr
    assert not Path(value["destination"]).exists()


@pytest.mark.parametrize("failure", ["success", "UnsafeSamplerInput", "UnsupportedSamplerEncoding", "SamplerDestinationExists", "OperationDeadlineExceeded"])
def test_prior_signal_handlers_are_restored_after_real_completion_or_failure(ownership_probe: Path, tmp_path: Path, failure: str) -> None:
    path, value = request(
        tmp_path, interval_ms=2000 if failure == "OperationDeadlineExceeded" else 0, wall_ms=500 if failure == "OperationDeadlineExceeded" else 5000
    )
    if failure == "UnsafeSamplerInput":
        source = Path(value["proc_root"]) / "meminfo"
        source.unlink()
        os.mkfifo(source, 0o600)
    elif failure == "UnsupportedSamplerEncoding":
        (Path(value["proc_root"]) / "meminfo").write_bytes(b"\xff")
    elif failure == "SamplerDestinationExists":
        Path(value["destination"]).mkdir()
    argv = [str(ownership_probe), "restore", str(path), failure]
    result = subprocess.run(argv, capture_output=True, timeout=15)
    (tmp_path / "invocation.stdout.log").write_bytes(result.stdout)
    (tmp_path / "invocation.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0 and result.stdout == b"prior-signals-restored;owner-released\n", result.stderr


def test_actual_native_sampling_works_with_fork_and_exec_denied(ownership_probe: Path, tmp_path: Path) -> None:
    path, value = request(tmp_path)
    for operation, expected in [("baseline-fork", b"baseline-fork-joined\n"), ("baseline-exec", b"")]:
        directory = tmp_path / operation
        directory.mkdir()
        baseline = invoke(ownership_probe, operation, path, directory)
        assert baseline.returncode == 0 and baseline.stdout == expected, baseline.stderr
    result = invoke(ownership_probe, "deny", path, tmp_path)
    assert result.returncode == 0 and result.stdout == b"fork-and-exec-denied;sampler-completed\n", result.stderr
    state = oracle.from_json((Path(value["destination"]) / "state.json").read_text())
    assert state is not None and state.samples == 3 and state.baseline_bytes == 8388608
    assert state.pid == json.loads((tmp_path / "invocation.json").read_bytes())["pid"]


@pytest.mark.integration
def test_existing_public_sampler_cross_builds_for_linux(tmp_path: Path) -> None:
    """Build the actual public executable, keeping portability RED separate from runtime proof."""
    build = tmp_path / "linux-source"
    build.mkdir()
    for source in NATIVE_SOURCES:
        shutil.copyfile(source, build / source.name)
    image = build / "executor"
    compiler = shutil.which("zig") or "zig"
    argv = [
        compiler,
        "build-exe",
        "-j1",
        "-OReleaseSafe",
        "-target",
        "aarch64-linux-musl",
        "-static",
        "-lc",
        str(build / "validation_execution.zig"),
        "-femit-bin=" + str(image),
    ]
    compiled = subprocess.run(argv, capture_output=True, timeout=180)
    (build / "build.stdout.log").write_bytes(compiled.stdout)
    (build / "build.stderr.log").write_bytes(compiled.stderr)
    (build / "build-result.json").write_text(
        json.dumps(
            {
                "argv": argv,
                "joined": True,
                "exact_exit_code": compiled.returncode,
                "compiler_sha256": digest(Path(compiler).read_bytes()),
                "sources": {source.name: digest(source.read_bytes()) for source in NATIVE_SOURCES},
                "scope": "Actual public Linux cross-build; no Linux runtime outcome is inferred from compilation.",
            }
        )
    )
    assert compiled.returncode == 0, compiled.stderr.decode()
    retain_native_build_metadata(image, [build / source.name for source in NATIVE_SOURCES], argv, compiled)


LINUX_IMAGE = "sha256:6b13e377e404ac4a3e8f307f79fa0621893d931bbd73d6c3116bc4a1556e0b2c"


LINUX_PROBE = r"""
// Test-only appended entry point; the preceding sampler bytes remain exact.
fn projectionMain(init: std.process.Init) !void {
    const args = try init.minimal.args.toSlice(init.arena.allocator());
    if (args.len != 3) return error.InvalidArguments;
    const path_z = try init.arena.allocator().dupeZ(u8, args[2]);
    var raw = std.mem.zeroes(LinuxStatx);
    const wanted: std.os.linux.STATX = .{ .TYPE = true, .MODE = true, .NLINK = true, .UID = true, .INO = true, .SIZE = true, .MTIME = true, .CTIME = true };
    const raw_rc = std.c.statx(c.AT_FDCWD, path_z, std.os.linux.AT.SYMLINK_NOFOLLOW, wanted, &raw);
    const raw_errno: u32 = @intFromEnum(std.c.errno(raw_rc));
    var value: Stat = undefined;
    const rc = pathnameStat(path_z, &value) catch |failure| {
        const diagnostic = try std.json.Stringify.valueAlloc(init.arena.allocator(), .{
            .projection_error=@errorName(failure), .raw_rc=raw_rc,.raw_errno=raw_errno,
            .required_mask=@as(u32,@bitCast(wanted)),.actual_mask=@as(u32,@bitCast(raw.mask)),
        }, .{});
        try std.Io.File.stdout().writeStreamingAll(init.io, diagnostic);
        return;
    };
    if (rc != 0) {
        const diagnostic = try std.json.Stringify.valueAlloc(init.arena.allocator(), .{
            .projection_errno=@as(u32,@intFromEnum(std.c.errno(rc))),.raw_rc=raw_rc,.raw_errno=raw_errno,
        }, .{});
        try std.Io.File.stdout().writeStreamingAll(init.io, diagnostic);
        return;
    }
    if (value.st_mode & c.S_IFMT != c.S_IFLNK) {
        const fd = c.open(path_z, c.O_RDONLY | c.O_NOFOLLOW | c.O_NONBLOCK | c.O_CLOEXEC);
        if (fd < 0) return error.ProbeOpenFailed;
        defer _ = c.close(fd);
        var held: Stat = undefined;
        if (try descriptorStat(fd, &held) != 0 or !same(value, held)) return error.DescriptorProjectionMismatch;
        const relative = (try statAt(c.AT_FDCWD, path_z)) orelse return error.RelativeProjectionMissing;
        if (!same(value, relative)) return error.RelativeProjectionMismatch;
    }
    const encoded = try std.json.Stringify.valueAlloc(init.arena.allocator(), .{
        .major=value.st_dev.major, .minor=value.st_dev.minor, .inode=value.st_ino,
        .mode=value.st_mode, .nlink=value.st_nlink, .uid=value.st_uid, .size=value.st_size,
        .mtime_sec=value.st_mtime.sec, .mtime_nsec=value.st_mtime.nsec,
        .ctime_sec=value.st_ctime.sec, .ctime_nsec=value.st_ctime.nsec,
        .required_mask=@as(u32,@bitCast(wanted)), .actual_mask=@as(u32,@bitCast(raw.mask)),
    }, .{});
    try std.Io.File.stdout().writeStreamingAll(init.io, encoded);
    try std.Io.File.stdout().writeStreamingAll(init.io, "\n");
}

const probe_c = @cImport({ @cInclude("signal.h"); });
var probe_received = std.atomic.Value(u32).init(0);
fn probePrior(signal: c_int) callconv(.c) void {
    _ = probe_received.fetchOr(if (signal == probe_c.SIGINT) 1 else 2, .monotonic);
}
fn probeRequire(value: bool) !void { if (!value) return error.ActualOwnershipControlFailed; }
pub fn main(init: std.process.Init) !void {
    const args = try init.minimal.args.toSlice(init.arena.allocator());
    if (args.len < 3) return error.InvalidArguments;
    if (std.mem.eql(u8,args[1],"stat")) return projectionMain(init);
    var action = std.mem.zeroes(probe_c.struct_sigaction);
    action.__sa_handler.sa_handler = probePrior;
    try probeRequire(probe_c.sigemptyset(&action.sa_mask) == 0);
    var previous_int: probe_c.struct_sigaction = undefined;
    var previous_term: probe_c.struct_sigaction = undefined;
    try probeRequire(probe_c.sigaction(probe_c.SIGINT, &action, &previous_int) == 0);
    defer _ = probe_c.sigaction(probe_c.SIGINT, &previous_int, null);
    try probeRequire(probe_c.sigaction(probe_c.SIGTERM, &action, &previous_term) == 0);
    defer _ = probe_c.sigaction(probe_c.SIGTERM, &previous_term, null);
    var failure: ?anyerror = null;
    if (std.mem.eql(u8,args[1],"busy")) {
        var held = try owner.beginSamplingSignals();
        _ = command(init,args[2]) catch |problem| blk: {failure=problem;break :blk 1;};
        try probeRequire(failure != null and failure.? == error.SignalBridgeBusy);
        try probeRequire(probe_c.raise(probe_c.SIGTERM) == 0);
        try probeRequire(try owner.restoreSamplingSignals(&held) == probe_c.SIGTERM);
    } else {
        if(args.len != 4) return error.InvalidArguments;
        _ = command(init,args[2]) catch |problem| blk: {failure=problem;break :blk 1;};
        if(std.mem.eql(u8,args[3],"success")) try probeRequire(failure == null)
        else try probeRequire(failure != null and std.mem.eql(u8,@errorName(failure.?),args[3]));
    }
    try probeRequire(probe_c.raise(probe_c.SIGINT) == 0 and probe_c.raise(probe_c.SIGTERM) == 0);
    try probeRequire(probe_received.load(.monotonic) == 3);
    var next = try owner.beginSamplingSignals();
    try probeRequire(owner.samplingSignal() == 0);
    try probeRequire(try owner.restoreSamplingSignals(&next) == 0);
    try std.Io.File.stdout().writeStreamingAll(init.io,"prior-signals-restored;owner-released\n");
}
"""


LINUX_PROJECTION_READER = r"""import os, sys, json, subprocess, errno
from pathlib import Path

root = Path("/output/fixture")
rows = []
for name, path in [
    ("file", root / "proc/meminfo"),
    ("hardlink", root / "hardlink"),
    ("directory", root / "proc"),
    ("symlink", root / "alias"),
    ("missing", root / "missing"),
    ("denied", root / "denied"),
    ("actual-proc", Path("/proc/meminfo")),
]:
    try:
        s = os.lstat(path)
        expected = {
            "major": os.major(s.st_dev),
            "minor": os.minor(s.st_dev),
            "inode": s.st_ino,
            "mode": s.st_mode,
            "nlink": s.st_nlink,
            "uid": s.st_uid,
            "size": s.st_size,
            "mtime_sec": s.st_mtime_ns // 10**9,
            "mtime_nsec": s.st_mtime_ns % 10**9,
            "ctime_sec": s.st_ctime_ns // 10**9,
            "ctime_nsec": s.st_ctime_ns % 10**9,
        }
        before = {"value": expected}
    except OSError as e:
        before = {"errno": e.errno}
    argv = ["/input/executor", "stat", str(path)]
    p = subprocess.run(argv, env={"PATH": "/usr/bin:/bin"}, capture_output=True, timeout=5)
    assert p.returncode == 0 and not p.stderr, (name, p.returncode, p.stderr)
    observed = json.loads(p.stdout)
    row = {
        "name": name,
        "path": str(path),
        "argv": argv,
        "exact_exit_code": p.returncode,
        "stdout_hex": p.stdout.hex(),
        "stderr_hex": p.stderr.hex(),
        "python_before": before,
        "native": observed,
    }
    if name == "missing":
        assert before == {"errno": errno.ENOENT} and observed == {"projection_errno": errno.ENOENT, "raw_rc": -1, "raw_errno": errno.ENOENT}
    elif "projection_error" in observed:
        assert name == "denied" and observed["projection_error"] == "SamplerPathObservationFailed" and observed["raw_rc"] == 0
        assert observed["actual_mask"] & observed["required_mask"] != observed["required_mask"]
        row["scope"] = "actual incomplete statx mask refused; os.lstat availability is separate"
    elif "projection_errno" in observed:
        assert name == "denied" and observed["projection_errno"] == observed["raw_errno"] and observed["raw_rc"] == -1
        row["scope"] = "actual statx metadata refusal; no unavailable-read or field-parity claim"
    else:
        assert {k: observed[k] for k in expected} == expected, (name, expected, observed)
        assert observed["actual_mask"] & observed["required_mask"] == observed["required_mask"]
        after = os.lstat(path)
        assert (after.st_dev, after.st_ino, after.st_mode, after.st_nlink, after.st_uid, after.st_size, after.st_mtime_ns, after.st_ctime_ns) == (
            s.st_dev,
            s.st_ino,
            s.st_mode,
            s.st_nlink,
            s.st_uid,
            s.st_size,
            s.st_mtime_ns,
            s.st_ctime_ns,
        )
        row["python_after_equal"] = True
    rows.append(row)
(root / "projection-results.json").write_text(json.dumps({"python_version": sys.version, "rows": rows}, indent=2) + "\n")
print("independent-linux-fields-matched;explicit-denied-state-retained")
"""


LINUX_PROC_READER = r"""import os, sys, json, stat, subprocess, hashlib, time
from pathlib import Path

root = Path("/output/fixture")


def snapshot(name, path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        metadata = os.fstat(fd)
        assert stat.S_ISREG(metadata.st_mode) and metadata.st_size <= 65536
        body = bytearray()
        while len(body) <= 65536:
            part = os.read(fd, 65537 - len(body))
            if not part:
                break
            body.extend(part)
        assert len(body) <= 65536
    finally:
        os.close(fd)
    destination = root / name
    destination.write_bytes(body)
    return {
        "path": path,
        "snapshot": str(destination),
        "sha256": hashlib.sha256(body).hexdigest(),
        "size": len(body),
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mode": metadata.st_mode,
    }


before = snapshot("proc-before.log", "/proc/meminfo")
context = [snapshot("self-mountinfo.log", "/proc/self/mountinfo"), snapshot("self-cgroup.log", "/proc/self/cgroup")]
argv = ["/input/executor", "memory-sample", "/input/request.json"]
started = time.monotonic()
with (root / "native.stdout.log").open("wb") as out, (root / "native.stderr.log").open("wb") as err:
    child = subprocess.Popen(argv, env={"PATH": "/usr/bin:/bin"}, stdout=out, stderr=err)
    try:
        code = child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=2)
after = snapshot("proc-after.log", "/proc/meminfo")
state = json.loads((root / "new-state/state.json").read_bytes())
result = {
    "argv": argv,
    "python_version": sys.version,
    "context_pid": os.getpid(),
    "actual_native_pid": child.pid,
    "joined": True,
    "exact_exit_code": code,
    "elapsed_seconds": time.monotonic() - started,
    "before": before,
    "after": after,
    "context": context,
    "state": state,
}
(root / "proc-result.json").write_text(json.dumps(result, indent=2) + "\n")
assert code == 0 and (root / "native.stdout.log").read_bytes() == (root / "native.stderr.log").read_bytes() == b""
assert state["pid"] == child.pid and state["samples"] == 3 and state["source"] == "meminfo"
assert state["baseline_bytes"] > 0 and state["peak_bytes"] >= state["baseline_bytes"] and 0 <= state["elapsed_seconds"] <= 5
print("actual-linux-proc-samples;owned-native-child-joined")
"""


LINUX_OWNED_FIXTURE = r"""import os, sys, json, stat, subprocess, hashlib
from pathlib import Path

# Closed two-case fixture transport, not a launcher or signal backend.
source = Path("/output/fixture")
root = Path("/owned")
assert os.getpid() == 1 and os.getuid() != 0
assert root.lstat().st_uid == os.getuid() and root.lstat().st_gid == os.getgid() and stat.S_IMODE(root.lstat().st_mode) == 0o700


def snapshot(path):
    try:
        before = path.lstat()
    except FileNotFoundError:
        return {"path": str(path), "state": "absent"}
    row = {"path": str(path), "mode": before.st_mode, "uid": before.st_uid,
           "gid": before.st_gid, "device": before.st_dev, "inode": before.st_ino,
           "nlink": before.st_nlink, "size": before.st_size,
           "mtime_ns": before.st_mtime_ns, "ctime_ns": before.st_ctime_ns}
    if stat.S_ISDIR(before.st_mode):
        return row | {"state": "directory"}
    assert stat.S_ISREG(before.st_mode) and before.st_size <= 65536
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        assert os.fstat(fd) == before
        body = bytearray()
        while len(body) <= 65536:
            part = os.read(fd, 65537 - len(body))
            if not part:
                break
            body.extend(part)
        assert len(body) <= 65536 and os.fstat(fd) == before and path.lstat() == before
    finally:
        os.close(fd)
    return row | {"state": "regular", "sha256": hashlib.sha256(body).hexdigest(), "body_hex": body.hex()}


original_request = snapshot(Path("/input/request.json"))
request = json.loads(bytes.fromhex(original_request["body_hex"]))
assert set(request) == {"schema_version", "destination", "proc_root", "interval_ms", "max_samples", "wall_ms"}
assert request["schema_version"] == 1 and request["destination"] == "/output/fixture/new-state" and request["proc_root"] == "/output/fixture/proc"
sample = snapshot(source / "proc/meminfo")
case = "directory" if sample["state"] == "directory" else "deadline"
if case == "directory":
    assert (request["interval_ms"], request["max_samples"], request["wall_ms"]) == (0, 3, 5000)
else:
    assert sample["state"] == "regular" and bytes.fromhex(sample["body_hex"]) == b"MemTotal: 16384 kB\nMemAvailable: 8192 kB\n"
    assert (request["interval_ms"], request["max_samples"], request["wall_ms"]) == (2000, 3, 500)
fixture = root / "fixture"
fixture.mkdir(mode=0o700)
proc = fixture / "proc"
proc.mkdir(mode=0o755)
if case == "directory":
    (proc / "meminfo").mkdir(mode=stat.S_IMODE(sample["mode"]))
else:
    (proc / "meminfo").write_bytes(bytes.fromhex(sample["body_hex"]))
    (proc / "meminfo").chmod(stat.S_IMODE(sample["mode"]))
request = request | {"destination": str(fixture / "new-state"), "proc_root": str(proc)}
request_path = root / "request.json"
request_path.write_text(json.dumps(request))
request_path.chmod(0o600)
paths = [root, fixture, proc, proc / "meminfo", request_path, fixture / "new-state",
         fixture / "new-state/state.json", fixture / "new-state/state.tmp"]
before = [snapshot(path) for path in paths]
argv = ["/input/executor", "memory-sample", str(request_path)]
out_path, err_path = source / "native.stdout.log", source / "native.stderr.log"
with out_path.open("xb") as out, err_path.open("xb") as err:
    child = subprocess.Popen(argv, env={"PATH": "/usr/bin:/bin"}, stdout=out, stderr=err)
    try:
        code = child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=2)
after = [snapshot(path) for path in paths]
assert all(before[index] == after[index] for index in [0, 2, 3, 4])
assert all(before[1][key] == after[1][key] for key in ["device", "inode", "mode", "uid", "gid"])
assert snapshot(Path("/input/request.json"))["body_hex"] == original_request["body_hex"]
assert code == 1 and out_path.stat().st_size == 0 and err_path.stat().st_size <= 1024 * 1024
state = after[-2]
if case == "deadline":
    assert state["state"] == "regular" and after[-1]["state"] == "absent"
    value = json.loads(bytes.fromhex(state["body_hex"]))
    assert value["pid"] == child.pid and value["samples"] == 1
    (source / "new-state").mkdir(mode=0o700)
    (source / "new-state/state.json").write_bytes(bytes.fromhex(state["body_hex"]))
    (source / "new-state/state.json").chmod(0o600)
else:
    assert after[-3]["state"] == "directory" and after[-3]["uid"] == os.getuid()
    assert stat.S_IMODE(after[-3]["mode"]) == 0o700
    assert after[-2]["state"] == after[-1]["state"] == "absent"
receipt = {"case": case, "argv": argv, "actual_native_pid": child.pid, "joined": True,
           "exact_native_exit_code": code, "before": before, "after": after,
           "source_input": sample, "original_request": original_request,
           "scope": "Two synthetic fixtures on owned Linux tmpfs; host bind output is evidence transport only."}
(source / "owned-fixture-result.json").write_text(json.dumps(receipt, indent=2) + "\n")
sys.stdout.buffer.write(out_path.read_bytes())
sys.stderr.buffer.write(err_path.read_bytes())
sys.exit(code)
"""


def linux_probe_operation(inputs: Path, fixture: Path, mode: str | None, expected: str) -> tuple[str, list[str]]:
    if mode is None:
        return "/input/executor", ["memory-sample", "/input/request.json"]
    if mode == "proc":
        (inputs / "proc-reader.py").write_text(LINUX_PROC_READER)
        return "/usr/local/bin/python3", ["/input/proc-reader.py"]
    if mode == "owned-fixture":
        (inputs / "owned-fixture.py").write_text(LINUX_OWNED_FIXTURE)
        return "/usr/local/bin/python3", ["/input/owned-fixture.py"]
    if mode == "projection":
        (inputs / "projection-reader.py").write_text(LINUX_PROJECTION_READER)
        (fixture / "hardlink").hardlink_to(fixture / "proc/meminfo")
        (fixture / "alias").symlink_to("proc/meminfo")
        (fixture / "denied").write_bytes(b"metadata only\n")
        (fixture / "denied").chmod(0)
        return "/usr/local/bin/python3", ["/input/projection-reader.py"]
    assert mode in {"restore", "busy"}
    return "/input/executor", [mode, "/input/request.json", expected]


def linux_input_fixture(proc: Path, body: bytes | None, control: str) -> None:
    if control in {"fifo", "symlink", "directory", "denied"}:
        sample = proc / "meminfo"
        sample.unlink(missing_ok=True)
        if control == "fifo":
            os.mkfifo(sample, 0o600)
        elif control == "symlink":
            (proc / "target").write_bytes(body or b"fixture")
            sample.symlink_to("target")
        elif control == "directory":
            sample.mkdir()
        else:
            sample.write_bytes(body or b"fixture")
            sample.chmod(0)


def linux_fixture_mode(owned: bool, mode: str | None, control: str, changes: dict[str, Any] | None) -> str | None:
    if not owned:
        return mode
    assert mode is None and (control == "directory" or (control == "normal" and changes == {"interval_ms": 2000, "max_samples": 3, "wall_ms": 500}))
    return "owned-fixture"


def linux_fixture_metadata(initial: dict[str, Any], owned: bool) -> None:
    if owned:
        assert initial["tmpfs"] == {"/owned": f"rw,noexec,nosuid,nodev,size=1048576,uid={os.getuid()},gid={os.getgid()},mode=0700"}
    else:
        assert initial["tmpfs"] in [None, {}]


def linux_actual_pid(fixture: Path, terminal: dict[str, Any], owned: bool) -> int:
    if not owned:
        return 1
    retained = json.loads((fixture / "owned-fixture-result.json").read_bytes())
    assert retained["joined"] and retained["exact_native_exit_code"] == terminal["state"]["ExitCode"]
    pid = retained["actual_native_pid"]
    assert type(pid) is int and pid > 1
    return pid


def linux_public_call(
    image: Path,
    directory: Path,
    *,
    body: bytes | None = b"MemTotal: 16384 kB\nMemAvailable: 8192 kB\n",
    changes: dict[str, Any] | None = None,
    control: str = "normal",
    probe_mode: str | None = None,
    probe_expectation: str = "success",
    owned_fixture: bool = False,
) -> dict[str, Any]:
    """Own exactly one bounded foreground container; never inspect its arguments or environment."""
    import pwd

    docker = shutil.which("docker")
    assert docker is not None, "Linux runtime setup requires the existing Docker CLI; never install or pull"
    # pytest isolates HOME. Use only the already-verified account-owned Desktop
    # socket, without importing operator Docker config or changing that isolation.
    socket = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".docker/run/docker.sock"
    assert socket.is_socket() and socket.stat().st_uid == os.getuid(), "Existing owned local Desktop socket is required"
    config = directory / "empty-docker-config"
    config.mkdir(mode=0o700)
    prefix = [docker, "--config", str(config), "--host", "unix://" + str(socket)]
    calls: list[dict[str, Any]] = []

    def call(arguments: list[str], name: str) -> subprocess.CompletedProcess[bytes]:
        argv = [*prefix, *arguments]
        stdout, stderr = directory / (name + ".stdout.log"), directory / (name + ".stderr.log")
        expired = False
        started_at = time.monotonic()
        with stdout.open("wb") as out, stderr.open("wb") as err:
            child = subprocess.Popen(argv, env={"PATH": "/usr/bin:/bin"}, stdout=out, stderr=err)
            try:
                if name == "start" and control in {"sigint", "sigterm", "custody-data"}:
                    state_path = fixture / "new-state/state.json"
                    first = None
                    while time.monotonic() - started_at < 5 and child.poll() is None:
                        if state_path.is_file() and not state_path.is_symlink() and state_path.stat().st_size <= 65536:
                            first = oracle.from_json(state_path.read_text())
                            if first is not None and first.samples == 1:
                                break
                        time.sleep(0.01)
                    assert first is not None and first.samples == 1 and first.pid == 1, "No qualified first-sample effect"
                    original_state = state_path.read_bytes()
                    if control == "custody-data":
                        (fixture / "new-state").rename(fixture / "retained-state")
                        (fixture / "new-state").mkdir(mode=0o700)
                        (fixture / "new-state/foreign").write_bytes(b"foreign marker\n")
                        (proc / "meminfo").write_bytes(b"\xff")
                    else:
                        (proc / "meminfo").write_bytes(b"MemTotal: 16384 kB\nMemAvailable: 4096 kB\n")
                        signalled = call(["kill", "--signal", "SIGINT" if control == "sigint" else "SIGTERM", container], "signal")
                        assert signalled.returncode == 0, signalled.stderr
                    (directory / "phase.json").write_text(
                        json.dumps(
                            {"control": control, "first": json.loads(original_state), "retained_first_sha256": digest(original_state), "intentional_mutation": True}
                        )
                    )
                code = child.wait(timeout=max(0.1, 15 - (time.monotonic() - started_at)))
            except subprocess.TimeoutExpired:
                expired = True
            finally:
                if child.poll() is None:
                    child.kill()
                code = child.wait(timeout=5)
                calls.append({"argv": argv, "pid": child.pid, "joined": True, "exact_exit_code": code, "timed_out": expired})
                (directory / "docker-invocations.json").write_text(json.dumps(calls))
        assert not expired, "Original Docker invocation timed out; retain logs and dispose only the owned container"
        assert stdout.stat().st_size <= 1024 * 1024 and stderr.stat().st_size <= 1024 * 1024
        return subprocess.CompletedProcess(argv, code, stdout.read_bytes(), stderr.read_bytes())

    executor = call(
        ["info", "--format", '{"os":{{json .OSType}},"architecture":{{json .Architecture}},"version":{{json .ServerVersion}}}'],
        "executor",
    )
    assert executor.returncode == 0 and json.loads(executor.stdout) == {"os": "linux", "architecture": "aarch64", "version": "29.8.0"}, (
        "Only the reviewed existing Linux executor is admitted"
    )
    inspected = call(["image", "inspect", LINUX_IMAGE, "--format", "{{.Id}}"], "image")
    assert inspected.returncode == 0 and inspected.stdout.decode().strip() == LINUX_IMAGE, "Pinned image must already exist; no pull"
    inputs, output = directory / "input", directory / "output"
    inputs.mkdir(mode=0o700)
    output.mkdir(mode=0o700)
    fixture = output / "fixture"
    fixture.mkdir(mode=0o700)
    proc = fixture / "proc"
    proc.mkdir()
    if body is not None:
        (proc / "meminfo").write_bytes(body)
    shutil.copyfile(image, inputs / "executor")
    (inputs / "executor").chmod(0o500)
    value = {
        "schema_version": 1,
        "destination": "/output/fixture/new-state",
        "proc_root": "/output/fixture/proc",
        "interval_ms": 0,
        "max_samples": 3,
        "wall_ms": 5000,
        **(changes or {}),
    }
    assert control in {"normal", "fifo", "symlink", "directory", "denied", "sigint", "sigterm", "custody-data"}
    linux_input_fixture(proc, body, control)
    entrypoint, operation = linux_probe_operation(inputs, fixture, linux_fixture_mode(owned_fixture, probe_mode, control, changes), probe_expectation)
    request_bytes = json.dumps(value).encode()
    (inputs / "request.json").write_bytes(request_bytes)
    owner = os.urandom(12).hex()
    for path in [inputs, output]:
        assert "," not in str(path), "The finite Docker bind fixture excludes commas"
    created = call(
        [
            "create",
            "--name",
            "spec-kitty-linux-sampler-" + owner,
            "--label",
            "spec-kitty-native-owner=" + owner,
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges=true",
            "--pids-limit",
            "64",
            "--cpus",
            "1",
            "--memory",
            "256m",
            "--memory-swap",
            "256m",
            "--ulimit",
            "nofile=128:128",
            "--mount",
            f"type=bind,src={inputs},dst=/input,readonly",
            "--mount",
            f"type=bind,src={output},dst=/output",
            *(["--tmpfs", f"/owned:rw,noexec,nosuid,nodev,size=1048576,uid={os.getuid()},gid={os.getgid()},mode=0700"] if owned_fixture else []),
            "--entrypoint",
            entrypoint,
            LINUX_IMAGE,
            *operation,
        ],
        "create",
    )
    assert created.returncode == 0, created.stderr
    container = created.stdout.decode().strip()
    assert len(container) == 64 and all(c in "0123456789abcdef" for c in container), "Unknown created handle must not be guessed"
    template = (
        '{"id":{{json .Id}},"image":{{json .Image}},"owner":{{json (index .Config.Labels "spec-kitty-native-owner")}},'
        '"state":{{json .State}},"user":{{json .Config.User}},"network":{{json .HostConfig.NetworkMode}},'
        '"readonly":{{json .HostConfig.ReadonlyRootfs}},"privileged":{{json .HostConfig.Privileged}},'
        '"memory":{{json .HostConfig.Memory}},"swap":{{json .HostConfig.MemorySwap}},'
        '"cpu":{{json .HostConfig.NanoCpus}},"pids":{{json .HostConfig.PidsLimit}},"mounts":{{json .Mounts}},'
        '"cap_drop":{{json .HostConfig.CapDrop}},"security":{{json .HostConfig.SecurityOpt}},'
        '"ulimits":{{json .HostConfig.Ulimits}},"pid_mode":{{json .HostConfig.PidMode}},"tmpfs":{{json .HostConfig.Tmpfs}}}'
    )

    def metadata(name: str) -> dict[str, Any]:
        result = call(["inspect", container, "--format", template], name)
        assert result.returncode == 0, "Owned container identity is unknown; no guessed cleanup"
        data: dict[str, Any] = json.loads(result.stdout)
        assert data["id"] == container and data["owner"] == owner and data["image"] == LINUX_IMAGE
        return data

    terminal: dict[str, Any] = {}
    cleanup_complete = False
    try:
        initial = metadata("created-state")
        assert initial["user"] == f"{os.getuid()}:{os.getgid()}" and os.getuid() != 0
        assert initial["network"] == "none" and initial["readonly"] and not initial["privileged"]
        assert initial["memory"] == initial["swap"] == 256 * 1024 * 1024 and initial["cpu"] == 1000000000 and initial["pids"] == 64
        assert initial["cap_drop"] == ["ALL"] and any(item in ["no-new-privileges", "no-new-privileges=true"] for item in initial["security"])
        assert initial["pid_mode"] in ["", "private"] and initial["ulimits"] == [{"Name": "nofile", "Soft": 128, "Hard": 128}]
        linux_fixture_metadata(initial, owned_fixture)
        assert len(initial["mounts"]) == 2
        assert {item["Destination"]: (item["Source"], item["RW"], item["Type"]) for item in initial["mounts"]} == {
            "/input": (str(inputs), False, "bind"),
            "/output": (str(output), True, "bind"),
        }
        started = call(["start", "--attach", container], "start")
        terminal = metadata("terminal-state")
        assert not terminal["state"]["Running"] and not terminal["state"]["OOMKilled"], "No completion inferred from attach exit"
    finally:
        current = metadata("cleanup-state")
        if current["state"]["Running"]:
            stopped = call(["stop", "--time", "2", container], "stop")
            assert stopped.returncode == 0
            current = metadata("stopped-state")
        assert not current["state"]["Running"], "Unknown cleanup retains the owned container handle"
        removed = call(["rm", container], "remove")
        cleanup_complete = removed.returncode == 0 and removed.stdout.decode().strip() == container
        (directory / "cleanup.json").write_text(json.dumps({"container": container, "owner": owner, "terminal": current, "removed": cleanup_complete}))
        assert cleanup_complete, "Owned container removal failed; preserve the exact handle"
    if control == "normal":
        if body is None:
            assert not (proc / "meminfo").exists()
        else:
            assert (proc / "meminfo").read_bytes() == body
    assert (inputs / "request.json").read_bytes() == request_bytes
    assert digest((inputs / "executor").read_bytes()) == digest(image.read_bytes())
    result = {
        "container": container,
        "joined": True,
        "native_exit_code": terminal["state"]["ExitCode"],
        "docker_attach_exit_code": started.returncode,
        "stdout": started.stdout.decode(),
        "stderr": started.stderr.decode(),
        "cleanup_complete": cleanup_complete,
        "state_path": str(fixture / "new-state/state.json"),
        "actual_native_pid": linux_actual_pid(fixture, terminal, owned_fixture),
    }
    (directory / "linux-public-result.json").write_text(json.dumps(result))
    return result


@pytest.mark.integration
def test_actual_linux_foreground_public_entry_is_usable(sampler_binary: Path, tmp_path: Path) -> None:
    if sampler_binary.read_bytes()[:4] != b"\x7fELF":
        pytest.skip("Finite Linux runtime control requires an explicitly bound actual Linux cross-build")
    result = linux_public_call(sampler_binary, tmp_path)
    assert result["native_exit_code"] == 0 and result["stdout"] == result["stderr"] == "", result
    state = oracle.from_json(Path(result["state_path"]).read_text())
    assert state is not None and state.pid == 1 and state.samples == 3
    assert state.source == "meminfo" and state.baseline_bytes == state.peak_bytes == 8388608


@pytest.mark.integration
@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (b"MemTotal: 0 kB\nMemAvailable: 0 kB\n", 0),
        (b"MemTotal: 1 kB\nMemAvailable: 2 kB\n", -1024),
        (b"MemTotal: 10 kB\nMemAvailable: 8 kB\nMemAvailable: 6 kB\nMemAvailable: nope\n", 4096),
        (b"MemTotal: 18446744073709551615 kB\nMemAvailable: 0 kB\n", 18446744073709551615 * 1024),
        (None, None),
        (b"MemTotal: invalid\n", None),
    ],
)
def test_actual_linux_private_state_semantics(sampler_binary: Path, tmp_path: Path, body: bytes | None, expected: int | None) -> None:
    if sampler_binary.read_bytes()[:4] != b"\x7fELF":
        pytest.skip("Requires explicitly bound actual Linux image")
    result = linux_public_call(sampler_binary, tmp_path, body=body)
    assert result["native_exit_code"] == 0 and result["stdout"] == result["stderr"] == "", result
    state = oracle.from_json(Path(result["state_path"]).read_text())
    assert state is not None and state.pid == 1
    if expected is None:
        assert state.samples == 0 and state.source == "unavailable"
        assert state.elapsed_seconds == 0 and state.baseline_bytes == state.peak_bytes == 0
    else:
        assert state.samples == 3 and state.source == "meminfo"
        assert state.baseline_bytes == state.peak_bytes == expected
        assert oracle.render_report(state, None, warn_bytes=10 * oracle.GIB, error_bytes=12 * oracle.GIB)[0].startswith(
            f"peak_rss_bytes={expected} source=meminfo baseline_bytes={expected}"
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("control", "body", "reason"),
    [
        ("fifo", None, "UnsafeSamplerInput"),
        ("symlink", None, "UnsafeSamplerInput"),
        ("directory", None, "UnsafeSamplerInput"),
        ("normal", b"\xff", "UnsupportedSamplerEncoding"),
        ("normal", b"x" * 65537, "SamplerInputLimit"),
        ("normal", b"MemTotal: 18446744073709551616 kB\nMemAvailable: 0 kB\n", "UnsupportedSamplerValue"),
    ],
)
def test_actual_linux_input_refusal(sampler_binary: Path, tmp_path: Path, control: str, body: bytes | None, reason: str) -> None:
    if sampler_binary.read_bytes()[:4] != b"\x7fELF":
        pytest.skip("Requires explicitly bound actual Linux image")
    result = linux_public_call(sampler_binary, tmp_path, body=body, control=control, owned_fixture=control == "directory")
    assert result["native_exit_code"] == 1 and result["stdout"] == "", result
    assert result["stderr"] == f"error: execution refused: {reason}\n"


@pytest.mark.integration
@pytest.mark.parametrize("control", ["sigint", "sigterm", "custody-data", "deadline", "denied"])
def test_actual_linux_signal_deadline_and_custody(sampler_binary: Path, tmp_path: Path, control: str) -> None:
    if sampler_binary.read_bytes()[:4] != b"\x7fELF":
        pytest.skip("Requires explicitly bound actual Linux image")
    changes = {"interval_ms": 2000, "max_samples": 3, "wall_ms": 500 if control == "deadline" else 10000}
    result = linux_public_call(
        sampler_binary, tmp_path, changes=changes, control="normal" if control == "deadline" else control, owned_fixture=control == "deadline"
    )
    assert result["stdout"] == "", result
    if control == "denied":
        # The reviewed Desktop bind filesystem denies metadata itself (EACCES),
        # independently reproduced by Linux os.lstat and native libc statx.
        # Unknown metadata must refuse; it cannot become an unavailable read.
        assert result["native_exit_code"] == 1 and result["stderr"] == "error: execution refused: SamplerPathObservationFailed\n", result
        assert not Path(result["state_path"]).exists()
    else:
        reason = "Cancelled" if control in {"sigint", "sigterm"} else "SamplerDirectoryDrift" if control == "custody-data" else "OperationDeadlineExceeded"
        assert result["native_exit_code"] == 1 and result["stderr"] == f"error: execution refused: {reason}\n", result
        if control == "custody-data":
            retained = tmp_path / "output/fixture/retained-state/state.json"
            phase = json.loads((tmp_path / "phase.json").read_bytes())
            assert digest(retained.read_bytes()) == phase["retained_first_sha256"]
            assert (tmp_path / "output/fixture/new-state/foreign").read_bytes() == b"foreign marker\n"
        else:
            state = oracle.from_json(Path(result["state_path"]).read_text())
            assert state is not None and state.pid == result["actual_native_pid"]
            assert state.samples == (2 if control in {"sigint", "sigterm"} else 1)
            assert state.baseline_bytes == 8388608 and state.peak_bytes == (12582912 if control in {"sigint", "sigterm"} else 8388608)


@pytest.fixture(scope="session")
def linux_sampler_probe(tmp_path_factory: pytest.TempPathFactory) -> Path:
    supplied = os.environ.get("SPEC_KITTY_LINUX_SAMPLER_PROBE_BINDING")
    if supplied:
        binding = json.loads(Path(supplied).read_bytes())
        for name, expected in binding["sources"].items():
            assert digest((ROOT / name).read_bytes()) == expected
        assert digest(LINUX_PROBE.encode()) == binding["appendix"]["sha256"]
        image = Path(binding["image"]["path"])
        assert digest(image.read_bytes()) == binding["image"]["sha256"]
        return image
    pytest.skip("Linux probe controls require an explicitly bound native test-only cross-build")


@pytest.mark.integration
def test_actual_linux_stat_projection_matches_independent_reader(linux_sampler_probe: Path, tmp_path: Path) -> None:
    result = linux_public_call(linux_sampler_probe, tmp_path, probe_mode="projection")
    assert result["native_exit_code"] == 0 and result["stderr"] == "", result
    assert result["stdout"] == "independent-linux-fields-matched;explicit-denied-state-retained\n"
    report = json.loads((tmp_path / "output/fixture/projection-results.json").read_bytes())
    assert len(report["rows"]) == 7
    assert {row["name"] for row in report["rows"]} == {"file", "hardlink", "directory", "symlink", "missing", "denied", "actual-proc"}


@pytest.mark.integration
@pytest.mark.parametrize("failure", ["success", "UnsafeSamplerInput", "UnsupportedSamplerEncoding", "OperationDeadlineExceeded", "busy"])
def test_actual_linux_prior_handlers_and_exclusive_lease(linux_sampler_probe: Path, tmp_path: Path, failure: str) -> None:
    body = b"\xff" if failure == "UnsupportedSamplerEncoding" else b"MemTotal: 16384 kB\nMemAvailable: 8192 kB\n"
    changes = {"interval_ms": 2000 if failure == "OperationDeadlineExceeded" else 0, "wall_ms": 500 if failure == "OperationDeadlineExceeded" else 5000}
    result = linux_public_call(
        linux_sampler_probe,
        tmp_path,
        body=body,
        changes=changes,
        control="fifo" if failure == "UnsafeSamplerInput" else "normal",
        probe_mode="busy" if failure == "busy" else "restore",
        probe_expectation=failure,
    )
    assert result["native_exit_code"] == 0 and result["stderr"] == "", result
    assert result["stdout"] == "prior-signals-restored;owner-released\n"


@pytest.mark.integration
def test_actual_linux_proc_sample_and_context(sampler_binary: Path, tmp_path: Path) -> None:
    if sampler_binary.read_bytes()[:4] != b"\x7fELF":
        pytest.skip("Requires explicitly bound actual Linux image")
    result = linux_public_call(sampler_binary, tmp_path, changes={"proc_root": "/proc"}, probe_mode="proc")
    assert result["native_exit_code"] == 0 and result["stderr"] == "", result
    assert result["stdout"] == "actual-linux-proc-samples;owned-native-child-joined\n"
    report = json.loads((tmp_path / "output/fixture/proc-result.json").read_bytes())
    state = oracle.from_json(json.dumps(report["state"]))
    assert report["joined"] and report["exact_exit_code"] == 0 and report["context_pid"] == 1
    assert state is not None and state.pid == report["actual_native_pid"] and state.samples == 3 and state.source == "meminfo"
    assert state.peak_bytes >= state.baseline_bytes > 0 and 0 <= state.elapsed_seconds <= 5
    assert {item["path"] for item in report["context"]} == {"/proc/self/mountinfo", "/proc/self/cgroup"}
    assert all(0 < report[key]["size"] <= 65536 for key in ["before", "after"])
