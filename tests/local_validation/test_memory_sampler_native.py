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
