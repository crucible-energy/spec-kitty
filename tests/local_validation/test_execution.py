"""Actual execution controls, initially driven through the pinned foundation.

The migration oracle exposes the incomplete group-only cleanup decision; it
never presents the original helper as having promised session containment.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from typing import Any

import pytest

from tests.local_validation.test_candidate import ROOT, digest

SOURCE = ROOT / "tools/zig/validation_process_darwin.zig"
FOUNDATION = ROOT / "tests/local_validation/fixtures/owned_process_group.zig"
FOUNDATION_SHA = "16dbf37d5d9199e61523e731cf931404e695d7a37fec463519951ba0a26fff8b"

PROBE = r"""const std = @import("std");
const owner = @import("validation_process_darwin.zig");
const c = @cImport({ @cInclude("sys/proc_info.h"); });
extern "c" fn proc_pidinfo(c_int, c_int, u64, ?*anyopaque, c_int) c_int;
const Request = struct { argv: []const []const u8, limits: owner.Limits, stdout_log: []const u8, stderr_log: []const u8 };
fn emit(init: std.process.Init, value: anytype) !void {
    var output: std.Io.Writer.Allocating = .init(init.arena.allocator());
    var encoder: std.json.Stringify = .{ .writer = &output.writer };
    try encoder.write(value);
    try output.writer.writeByte('\n');
    try std.Io.File.stdout().writeStreamingAll(init.io, output.written());
}
pub fn main(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len == 3 and std.mem.eql(u8, args[1], "inspect")) {
        const pid = try std.fmt.parseInt(c_int, args[2], 10);
        var info: c.struct_proc_bsdinfo = std.mem.zeroes(c.struct_proc_bsdinfo);
        std.c._errno().* = 0;
        const rc = proc_pidinfo(pid, c.PROC_PIDTBSDINFO, 0, &info, @sizeOf(@TypeOf(info)));
        if (rc != @sizeOf(@TypeOf(info))) {
            if (std.c.errno(@as(c_int, -1)) != .SRCH) return error.KernelInspectionFailed;
            try emit(init, .{ .pid = pid, .live = false, .inspection_bytes = rc });
        } else try emit(init, .{ .pid = pid, .live = true, .parent = info.pbi_ppid, .group = info.pbi_pgid,
            .status = info.pbi_status, .start_seconds = info.pbi_start_tvsec, .start_microseconds = info.pbi_start_tvusec });
        return;
    }
    if (args.len != 2) return error.InvalidArguments;
    const raw = try std.Io.Dir.cwd().readFileAlloc(init.io, args[1], allocator, .limited(65536));
    const request = (try std.json.parseFromSlice(Request, allocator, raw, .{ .duplicate_field_behavior = .@"error" })).value;
    // Precreate diagnostics before any child effect. The legacy fallback only
    // writes its capture at return; the live-sink control must discriminate it.
    const stdout = try std.Io.Dir.cwd().createFile(init.io, request.stdout_log, .{});
    defer stdout.close(init.io);
    const stderr = try std.Io.Dir.cwd().createFile(init.io, request.stderr_log, .{});
    defer stderr.close(init.io);
    var environment = std.process.Environ.Map.init(allocator);
    defer environment.deinit();
    const options: owner.Options = .{ .argv = request.argv, .environment = &environment, .limits = request.limits };
    const result = (if (@hasDecl(owner, "runLogged"))
        owner.runLogged(allocator, init.io, options, .{ .stdout = stdout, .stderr = stderr })
        else owner.run(allocator, init.io, options)) catch |err| {
        try emit(init, .{ .started = false, .error_name = @errorName(err), .cleanup_complete = false });
        return;
    };
    defer result.deinit(allocator);
    if (!@hasDecl(owner, "runLogged")) {
        try stdout.writeStreamingAll(init.io, result.stdout);
        try stderr.writeStreamingAll(init.io, result.stderr);
    }
    const complete = if (@hasField(@TypeOf(result), "all_owned_children_terminal")) result.all_owned_children_terminal else result.group_disposed;
    try emit(init, .{ .started = true, .result = result, .cleanup_complete = complete,
        .legacy_group_only_oracle = !@hasField(@TypeOf(result), "all_owned_children_terminal") });
}
"""


def canonical(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode() + b"\n"


@pytest.fixture(scope="session")
def process_probe(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if sys.platform != "darwin":
        pytest.skip("Darwin foundation controls do not qualify another platform")
    assert digest(FOUNDATION.read_bytes()) == FOUNDATION_SHA
    directory = tmp_path_factory.mktemp("native-process-probe")
    source = SOURCE if SOURCE.is_file() else FOUNDATION
    (directory / "validation_process_darwin.zig").write_bytes(source.read_bytes())
    for name in ["validation_process.zig", "validation_process_linux.zig", "validation_process_windows.zig"]:
        path = ROOT / "tools/zig" / name
        if path.is_file():
            shutil.copyfile(path, directory / name)
    (directory / "probe.zig").write_text(PROBE)
    image = directory / "probe"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(directory / "probe.zig"), "-femit-bin=" + str(image)]
    result = subprocess.run(argv, capture_output=True, timeout=120)
    (directory / "build.stdout.log").write_bytes(result.stdout)
    (directory / "build.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    (directory / "build.json").write_bytes(
        canonical(
            {
                "argv": argv,
                "source": str(source),
                "source_sha256": digest(source.read_bytes()),
                "image_sha256": digest(image.read_bytes()),
                "foundation_only": not SOURCE.is_file(),
            }
        )
    )
    return image


def inspect(probe: Path, pid: int) -> dict[str, Any]:
    result = subprocess.run([str(probe), "inspect", str(pid)], capture_output=True, check=True, timeout=10)
    value: dict[str, Any] = json.loads(result.stdout)
    return value


def wait_identity_terminal(probe: Path, identity: dict[str, Any]) -> list[dict[str, Any]]:
    observations = []
    deadline = time.monotonic() + 7
    while time.monotonic() < deadline:
        current = inspect(probe, identity["pid"])
        observations.append(current)
        if not current["live"] or any(current[k] != identity[k] for k in ["start_seconds", "start_microseconds"]):
            return observations
        time.sleep(0.025)
    raise AssertionError(("Owned finite fixture identity remains live", identity, observations[-1]))


def request(tmp_path: Path, argv: list[str], **limits: int) -> Path:
    bounds = {"wall_ms": 3000, "cleanup_ms": 1000, "stdout_bytes": 65536, "stderr_bytes": 65536, "processes": 8, "resident_bytes": 536870912}
    bounds.update(limits)
    path = tmp_path / "request.json"
    path.write_bytes(canonical({"argv": argv, "limits": bounds, "stdout_log": str(tmp_path / "stdout.log"), "stderr_log": str(tmp_path / "stderr.log")}))
    return path


def invoke(probe: Path, tmp_path: Path, argv: list[str], **limits: int) -> dict[str, Any]:
    path = request(tmp_path, argv, **limits)
    result = subprocess.run([str(probe), str(path)], capture_output=True, timeout=12)
    (tmp_path / "owner.stdout.log").write_bytes(result.stdout)
    (tmp_path / "owner.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    value: dict[str, Any] = json.loads(result.stdout)
    return value


def python(source: str, *args: str) -> list[str]:
    return [str(Path(sys.executable).resolve()), "-I", "-S", "-B", "-c", source, *args]


@pytest.mark.parametrize("exit_code", [0, 7])
def test_actual_success_and_failure_are_distinct(process_probe: Path, tmp_path: Path, exit_code: int) -> None:
    observed = invoke(process_probe, tmp_path, python("import sys\nprint('OUT')\nprint('ERR',file=sys.stderr)\nsys.exit(int(sys.argv[1]))", str(exit_code)))
    assert observed["started"] and observed["result"]["exit_code"] == exit_code
    assert observed["result"]["failure"] is None
    assert observed["result"]["leader_reaped"] and observed["result"]["group_disposed"]
    assert (tmp_path / "stdout.log").read_bytes() == b"OUT\n"
    assert (tmp_path / "stderr.log").read_bytes() == b"ERR\n"


def test_actual_spawn_failure_cannot_be_success(process_probe: Path, tmp_path: Path) -> None:
    observed = invoke(process_probe, tmp_path, [str(tmp_path / "absent-executable")])
    assert observed == {"started": False, "error_name": "FileNotFound", "cleanup_complete": False}


def test_actual_timeout_retains_diagnostics_and_disposes_group(process_probe: Path, tmp_path: Path) -> None:
    observed = invoke(process_probe, tmp_path, python("import time\nprint('READY',flush=True)\ntime.sleep(3)"), wall_ms=300)
    assert observed["result"]["failure"] == "wall_timeout"
    assert observed["result"]["leader_reaped"] and observed["result"]["group_disposed"]
    assert (tmp_path / "stdout.log").read_bytes() == b"READY\n"


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_over_quota_retains_every_byte_up_to_the_execution_limit(process_probe: Path, tmp_path: Path, stream: str) -> None:
    observed = invoke(
        process_probe, tmp_path, python("import os,sys\nos.write(int(sys.argv[1]),b'12345')", "1" if stream == "stdout" else "2"), **{stream + "_bytes": 4}
    )
    assert observed["result"]["failure"] == stream + "_limit"
    assert observed["result"]["leader_reaped"] and observed["result"]["group_disposed"]
    assert (tmp_path / (stream + ".log")).read_bytes() == b"1234", (
        "Execution quota must retain the produced prefix; no empty diagnostic on a first overflowing read"
    )


@pytest.mark.parametrize("mode", ["same-group", "changed-group", "session"])
def test_descendant_scope_uses_actual_kernel_identity_and_preserves_unrelated_process(process_probe: Path, tmp_path: Path, mode: str) -> None:
    ready = tmp_path / "descendant.json"
    script = """import json,os,pathlib,sys,time
mode,path=sys.argv[1:]
pid=os.fork()
if pid==0:
 if mode=='changed-group':os.setpgid(0,0)
 if mode=='session':os.setsid()
 os.close(1);os.close(2)
 pathlib.Path(path).write_text(json.dumps({'pid':os.getpid(),'group':os.getpgrp(),'session':os.getsid(0)}))
 time.sleep(3)
 os._exit(0)
while not pathlib.Path(path).exists():time.sleep(.002)
print(json.dumps({'leader':os.getpid(),'descendant':pid}),flush=True)
os._exit(0)
"""
    unrelated = subprocess.Popen(["/bin/sleep", "10"])
    before = inspect(process_probe, unrelated.pid)
    observations: list[dict[str, Any]] = []
    identity: dict[str, Any] | None = None
    try:
        observed = invoke(process_probe, tmp_path, python(script, mode, str(ready)))
        child = json.loads(ready.read_bytes())
        returned = inspect(process_probe, child["pid"])
        (tmp_path / "kernel-at-owner-return.json").write_bytes(canonical({"fixture": child, "observation": returned, "result": observed}))
        assert observed["result"]["leader_reaped"] and observed["result"]["group_disposed"]
        if mode == "same-group":
            assert not returned["live"], "Original-group descendant must be terminal before the owner returns"
        else:
            # The exact imported foundation can return while this identity is
            # alive. That is a real group-only cleanup counterexample, not a
            # claim that the helper's documented original-group scope is wrong.
            if returned["live"]:
                identity = returned
                observations = wait_identity_terminal(process_probe, identity)
            assert not observed["cleanup_complete"], "An escaped child cannot be credited as globally cleaned solely from original-group disposal"
        assert unrelated.poll() is None
        assert inspect(process_probe, unrelated.pid) == before
    finally:
        if identity and not observations:
            observations = wait_identity_terminal(process_probe, identity)
        (tmp_path / "terminal-observations.json").write_bytes(canonical(observations))
        assert unrelated.poll() is None, "Native owner disturbed the unrelated retained child"
        unrelated.terminate()
        unrelated.wait(timeout=3)


def test_logs_stream_while_the_real_child_is_still_running(process_probe: Path, tmp_path: Path) -> None:
    ready, finish = tmp_path / "ready", tmp_path / "finish"
    script = """import pathlib,sys,time
ready,finish=map(pathlib.Path,sys.argv[1:])
print('first',flush=True)
ready.write_bytes(b'ready')
deadline=time.monotonic()+3
while not finish.exists() and time.monotonic()<deadline:time.sleep(.005)
print('last',flush=True)
"""
    path = request(tmp_path, python(script, str(ready), str(finish)), wall_ms=4000)
    owner = subprocess.Popen([str(process_probe), str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    during = b""
    try:
        deadline = time.monotonic() + 2
        while not ready.exists() and owner.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists() and owner.poll() is None
        # Give the native reader several turns without releasing the child.
        deadline = time.monotonic() + 0.2
        while time.monotonic() < deadline:
            during = (tmp_path / "stdout.log").read_bytes()
            if during == b"first\n":
                break
            time.sleep(0.01)
    finally:
        finish.write_bytes(b"finish")
        stdout, stderr = owner.communicate(timeout=7)
        (tmp_path / "owner.stdout.log").write_bytes(stdout)
        (tmp_path / "owner.stderr.log").write_bytes(stderr)
    assert owner.returncode == 0, stderr
    observed = json.loads(stdout)
    assert observed["result"]["exit_code"] == 0 and observed["result"]["group_disposed"]
    assert (tmp_path / "stdout.log").read_bytes() == b"first\nlast\n"
    assert during == b"first\n", "Raw diagnostics must be visible before completion, independently of a final capture"


@pytest.mark.parametrize("budget", ["processes", "resident_bytes"])
def test_sampled_usage_quota_refuses_with_original_group_cleanup(process_probe: Path, tmp_path: Path, budget: str) -> None:
    script = "import os,time\nif os.fork()==0:time.sleep(3);os._exit(0)\ntime.sleep(3)"
    observed = invoke(process_probe, tmp_path, python(script), **{budget: 1})
    result = observed["result"]
    assert result["failure"] == ("process_limit" if budget == "processes" else "resident_limit")
    assert result["leader_reaped"] and result["group_disposed"]
    assert result["max_sampled_processes" if budget == "processes" else "max_sampled_resident_bytes"] > 1


def test_real_signal_cancellation_after_eof_observes_child_terminal_identity(process_probe: Path, tmp_path: Path) -> None:
    ready = tmp_path / "cancel-ready.json"
    script = "import json,os,pathlib,sys,time\npathlib.Path(sys.argv[1]).write_text(json.dumps({'pid':os.getpid()}))\nos.close(1);os.close(2)\ntime.sleep(3)"
    path = request(tmp_path, python(script, str(ready)))
    owner = subprocess.Popen([str(process_probe), str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    identity: dict[str, Any] | None = None
    try:
        deadline = time.monotonic() + 2
        while not ready.exists() and owner.poll() is None and time.monotonic() < deadline:
            time.sleep(0.005)
        assert ready.exists() and owner.poll() is None
        identity = inspect(process_probe, json.loads(ready.read_bytes())["pid"])
        assert identity["live"]
    finally:
        if owner.poll() is None:
            owner.send_signal(signal.SIGTERM)
        stdout, stderr = owner.communicate(timeout=7)
        (tmp_path / "owner.stdout.log").write_bytes(stdout)
        (tmp_path / "owner.stderr.log").write_bytes(stderr)
    assert owner.returncode == 0, stderr
    observed = json.loads(stdout)
    assert observed["result"]["failure"] == "cancelled"
    assert observed["result"]["leader_reaped"] and observed["result"]["group_disposed"]
    assert identity is not None
    terminal = wait_identity_terminal(process_probe, identity)
    (tmp_path / "kernel-cancel-observations.json").write_bytes(canonical({"initial": identity, "terminal": terminal}))
