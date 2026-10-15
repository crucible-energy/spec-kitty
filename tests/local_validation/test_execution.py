"""Actual execution controls, initially driven through the pinned foundation.

The migration oracle exposes the incomplete group-only cleanup decision; it
never presents the original helper as having promised session containment.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from tests.local_validation.test_candidate import ROOT, digest, snapshot
from tests.local_validation.test_candidate import candidate_binary as candidate_binary
from tests.local_validation.test_candidate import repository as repository
from tests.local_validation.test_receipt import bound_inputs as bound_inputs
from tests.local_validation.test_receipt import receipt_binary as receipt_binary

SOURCE = ROOT / "tools/zig/validation_process_darwin.zig"
FOUNDATION = ROOT / "tests/local_validation/fixtures/owned_process_group.zig"
FOUNDATION_SHA = "16dbf37d5d9199e61523e731cf931404e695d7a37fec463519951ba0a26fff8b"

PROBE = r"""const std = @import("std");
const owner = @import("validation_process_darwin.zig");
const c = @cImport({ @cInclude("sys/proc_info.h"); @cInclude("unistd.h"); @cInclude("fcntl.h"); });
extern "c" fn proc_pidinfo(c_int, c_int, u64, ?*anyopaque, c_int) c_int;
const EnvironmentEntry = struct { name: []const u8, value: []const u8 };
const Request = struct {
    argv: []const []const u8, limits: owner.Limits, stdout_log: []const u8, stderr_log: []const u8,
    sink_mode: []const u8 = "ordinary", display_bytes: usize = 8192,
    cwd: ?[]const u8 = null, cwd_mode: []const u8 = "path",
    environment: []const EnvironmentEntry = &.{}, extra_fd_argument: bool = false,
};
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
    if (args.len >= 3 and std.mem.eql(u8, args[1], "echo-context")) {
        var pairs: std.ArrayList(EnvironmentEntry) = .empty;
        for (init.environ_map.keys(), init.environ_map.values()) |key, value| try pairs.append(allocator, .{ .name = key, .value = value });
        var cwd: [4096]u8 = undefined;
        const cwd_len = try std.process.currentPath(init.io, &cwd);
        const fd = try std.fmt.parseInt(c_int, args[args.len - 1], 10);
        std.c._errno().* = 0;
        const inherited = c.fcntl(fd, c.F_GETFD) >= 0;
        if (!inherited and std.c.errno(@as(c_int, -1)) != .BADF) return error.ContextDescriptorInspectionFailed;
        var stdin: [1]u8 = undefined;
        const stdin_bytes = c.read(0, &stdin, stdin.len);
        if (stdin_bytes < 0) return error.ContextStdinInspectionFailed;
        try emit(init, .{ .argv = args[2 .. args.len - 1], .cwd = cwd[0..cwd_len], .environment = pairs.items,
            .stdin = stdin[0..@intCast(stdin_bytes)], .extra_fd_inherited = inherited });
        return;
    }
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
    var stdout = try std.Io.Dir.cwd().createFile(init.io, request.stdout_log, .{});
    if (std.mem.eql(u8, request.sink_mode, "readonly")) {
        stdout.close(init.io);
        stdout = try std.Io.Dir.cwd().openFile(init.io, request.stdout_log, .{});
    }
    defer stdout.close(init.io);
    var stderr = if (std.mem.eql(u8, request.sink_mode, "same-descriptor")) stdout
        else try std.Io.Dir.cwd().createFile(init.io, request.stderr_log, .{});
    if (std.mem.eql(u8, request.sink_mode, "readonly-stderr")) {
        stderr.close(init.io);
        stderr = try std.Io.Dir.cwd().openFile(init.io, request.stderr_log, .{});
    }
    defer if (stderr.handle != stdout.handle) stderr.close(init.io);
    if (std.mem.eql(u8, request.sink_mode, "nonempty")) try stdout.writeStreamingAll(init.io, "existing");
    var environment = std.process.Environ.Map.init(allocator);
    defer environment.deinit();
    for (request.environment) |entry| {
        // std.Environ.Map requires a valid key. Refuse the untrusted test
        // request before entering that typed API; this is a harness boundary.
        if (entry.name.len == 0 or std.mem.indexOfScalar(u8, entry.name, '=') != null or std.mem.indexOfScalar(u8, entry.name, 0) != null) {
            try emit(init, .{ .started = @as(?bool, null), .error_name = "InvalidEnvironment", .cleanup_complete = false });
            return;
        }
        try environment.put(entry.name, entry.value);
    }
    var argv = request.argv;
    var extra_fd: c_int = -1;
    defer if (extra_fd >= 0) { _ = c.close(extra_fd); };
    if (request.extra_fd_argument) {
        extra_fd = c.dup(stdout.handle); // Deliberately lacks close-on-exec.
        if (extra_fd < 0) return error.ExtraDescriptorFailed;
        const extended = try allocator.alloc([]const u8, argv.len + 1);
        @memcpy(extended[0..argv.len], argv);
        extended[argv.len] = try std.fmt.allocPrint(allocator, "{d}", .{extra_fd});
        argv = extended;
    }
    var directory: ?std.Io.Dir = null;
    defer if (directory) |dir| dir.close(init.io);
    var options: owner.Options = .{ .argv = argv, .environment = &environment, .limits = request.limits };
    if (request.cwd) |path| {
        if (std.mem.eql(u8, request.cwd_mode, "dir")) {
            directory = try std.Io.Dir.cwd().openDir(init.io, path, .{});
            options.cwd = .{ .dir = directory.? };
        } else options.cwd = .{ .path = path };
    }
    if (@hasField(owner.Options, "display_bytes")) options.display_bytes = request.display_bytes;
    defer if (@hasDecl(owner, "__native_cov_finish")) owner.__native_cov_finish();
    const result = (if (@hasDecl(owner, "runLogged"))
        owner.runLogged(allocator, init.io, options, .{ .stdout = stdout, .stderr = stderr })
        else owner.run(allocator, init.io, options)) catch |err| {
        try emit(init, .{ .started = @as(?bool, null), .error_name = @errorName(err), .cleanup_complete = false });
        return;
    };
    defer result.deinit(allocator);
    if (!@hasDecl(owner, "runLogged")) {
        try stdout.writeStreamingAll(init.io, result.stdout);
        try stderr.writeStreamingAll(init.io, result.stderr);
    }
    if (extra_fd >= 0 and c.fcntl(extra_fd, c.F_GETFD) < 0) return error.UnrelatedDescriptorClosed;
    const complete = if (@hasField(@TypeOf(result), "all_owned_children_terminal")) result.all_owned_children_terminal else result.group_disposed;
    try emit(init, .{ .started = true, .result = result, .cleanup_complete = complete,
        .legacy_group_only_oracle = !@hasField(@TypeOf(result), "all_owned_children_terminal") });
}
"""


# Test-only libc fault injection; never linked into a production image. The
# owner PID restricts every effect to this one native fixture, including fork.
SIGACTION_FAULT_LIBRARY = r"""#include <signal.h>
#include <errno.h>
#include <unistd.h>
#include <spawn.h>
static unsigned mask, calls, signal_call;
static pid_t owner;
void wp03_sigaction_faults(unsigned failures, unsigned trigger) {
    owner=getpid(); mask=failures; signal_call=trigger; calls=0;
}
static int wp03_sigaction(int signal, const struct sigaction *action, struct sigaction *previous) {
    if (getpid()==owner && action && (mask || signal_call) && (signal==SIGINT || signal==SIGTERM)) {
        ++calls;
        if (calls==signal_call) raise(SIGTERM);
        if (calls<=32 && (mask & (1u << (calls-1)))) { errno=EIO; return -1; }
    }
    return sigaction(signal,action,previous);
}
static unsigned spawn_mode;
void wp03_spawn_faults(unsigned mode) { owner=getpid(); spawn_mode=mode; }
static int failing(unsigned mode) { return getpid()==owner && spawn_mode==mode; }
static int actions_init(posix_spawn_file_actions_t *a) { return failing(1)?EIO:posix_spawn_file_actions_init(a); }
static int attr_init(posix_spawnattr_t *a) { return failing(2)?EIO:posix_spawnattr_init(a); }
static int setpgroup(posix_spawnattr_t *a,pid_t group) { return failing(3)?EIO:posix_spawnattr_setpgroup(a,group); }
static int addopen(posix_spawn_file_actions_t *a,int fd,const char *path,int flags,mode_t mode) {
    return failing(4)?EIO:posix_spawn_file_actions_addopen(a,fd,path,flags,mode);
}
static int addchdir(posix_spawn_file_actions_t *a,const char *path) { return failing(5)?EIO:posix_spawn_file_actions_addchdir(a,path); }
static int addfchdir(posix_spawn_file_actions_t *a,int fd) { return failing(6)?EIO:posix_spawn_file_actions_addfchdir(a,fd); }
static int adddup2(posix_spawn_file_actions_t *a,int source,int target) { return failing(7)?EIO:posix_spawn_file_actions_adddup2(a,source,target); }
// Real metadata disposal always happens. Only its reported status is injected.
static int actions_destroy(posix_spawn_file_actions_t *a) { int rc=posix_spawn_file_actions_destroy(a); return failing(8)?EIO:rc; }
static int attr_destroy(posix_spawnattr_t *a) { int rc=posix_spawnattr_destroy(a); return failing(9)?EIO:rc; }
static int setflags(posix_spawnattr_t *a,short flags) { return failing(10)?EIO:posix_spawnattr_setflags(a,flags); }
#define HOOK(replacement,original) { (const void *)(replacement), (const void *)(original) }
__attribute__((used,section("__DATA,__interpose")))
static const struct { const void *replacement; const void *original; } hooks[] = {
    HOOK(wp03_sigaction,sigaction),
    HOOK(actions_init,posix_spawn_file_actions_init), HOOK(attr_init,posix_spawnattr_init),
    HOOK(setpgroup,posix_spawnattr_setpgroup), HOOK(addopen,posix_spawn_file_actions_addopen),
    HOOK(addchdir,posix_spawn_file_actions_addchdir), HOOK(addfchdir,posix_spawn_file_actions_addfchdir),
    HOOK(adddup2,posix_spawn_file_actions_adddup2), HOOK(actions_destroy,posix_spawn_file_actions_destroy),
    HOOK(attr_destroy,posix_spawnattr_destroy), HOOK(setflags,posix_spawnattr_setflags)
};
"""

NATIVE_FAULT_CONTROLS = r"""
extern "c" fn wp03_sigaction_faults(c_uint, c_uint) void;
extern "c" fn wp03_spawn_faults(c_uint) void;

fn noRetainedChildren() !void {
    var attempts: usize = 0;
    while (attempts < 200) : (attempts += 1) {
        var children: [64]c_int = @splat(0);
        const bytes = proc_listpids(c.PROC_PPID_ONLY, @intCast(c.getpid()), &children, @sizeOf(@TypeOf(children)));
        try std.testing.expect(bytes >= 0 and bytes < @sizeOf(@TypeOf(children)) and @rem(bytes, @sizeOf(c_int)) == 0);
        var pending = false;
        for (children[0..@intCast(@divTrunc(bytes, @sizeOf(c_int)))]) |pid| {
            if (pid <= 0) continue;
            pending = true;
            var info: c.siginfo_t = std.mem.zeroes(c.siginfo_t);
            std.c._errno().* = 0;
            const rc = c.waitid(c.P_PID, @intCast(pid), &info, c.WEXITED | c.WNOHANG | c.WNOWAIT);
            // A waitable child is a real custody failure. Never sweep or reap.
            // Only an SDK-unwaitable kernel inventory remnant may settle.
            try std.testing.expect(rc < 0 and std.c.errno(rc) == .CHILD);
        }
        if (!pending) return;
        _ = c.usleep(5000);
    }
    return error.UnsettledKernelInventory;
}

fn retainedDescriptors() ![256]i32 {
    var entries: [256]c.struct_proc_fdinfo = undefined;
    const bytes = proc_pidinfo(c.getpid(), c.PROC_PIDLISTFDS, 0, &entries, @sizeOf(@TypeOf(entries)));
    try std.testing.expect(bytes >= 0 and bytes < @sizeOf(@TypeOf(entries)) and @rem(bytes, @sizeOf(c.struct_proc_fdinfo)) == 0);
    var descriptors: [256]i32 = @splat(-1);
    for (entries[0..@intCast(@divTrunc(bytes, @sizeOf(c.struct_proc_fdinfo)))], 0..) |entry, index| descriptors[index] = entry.proc_fd;
    std.mem.sort(i32, &descriptors, {}, std.sort.asc(i32));
    return descriptors;
}

test "SDK spawn metadata faults retain child and descriptor custody" {
    // Warm runtime-owned descriptors before recording this fixture's boundary.
    const warm = try fixture("printf OUT; printf ERR >&2", .{});
    warm.deinit(std.testing.allocator);
    var temporary = std.testing.tmpDir(.{});
    defer temporary.cleanup();
    const before = try retainedDescriptors();
    defer wp03_spawn_faults(0);
    for ([_]c_uint{ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 }) |mode| {
        wp03_spawn_faults(mode);
        var options: Options = .{ .argv = &.{ "/bin/sh", "-c", "printf OUT; printf ERR >&2" } };
        if (mode == 5) options.cwd = .{ .path = "/" };
        if (mode == 6) options.cwd = .{ .dir = temporary.dir };
        const expected = if (mode == 8 or mode == 9) error.SpawnMetadataCleanupFailed else error.SpawnSetupFailed;
        try std.testing.expectError(expected, run(std.testing.allocator, std.testing.io, options));
        wp03_spawn_faults(0);
        try noRetainedChildren();
        try std.testing.expectEqualSlices(i32, &before, &try retainedDescriptors());
    }
    // Clearing fault state must restore a real successful launch.
    const after = try fixture("printf OUT; printf ERR >&2", .{});
    defer after.deinit(std.testing.allocator);
    try std.testing.expect(after.failure == null and after.exit_code == 0 and after.group_disposed and after.leader_reaped);
}

fn rejectBeforeLaunch(_: ?*anyopaque) bool { return true; }

test "prelaunch cancellation and budget probes refuse without child effects" {
    const warm = try fixture("printf OUT; printf ERR >&2", .{});
    warm.deinit(std.testing.allocator);
    const before = try retainedDescriptors();
    try std.testing.expectError(error.OperationCancelled, run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ "/bin/sleep", "3" }, .cancel_probe = rejectBeforeLaunch,
    }));
    try std.testing.expectError(error.OperationBudgetExceeded, run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ "/bin/sleep", "3" }, .budget_probe = rejectBeforeLaunch,
    }));
    try noRetainedChildren();
    try std.testing.expectEqualSlices(i32, &before, &try retainedDescriptors());
}

test "signal installation and restoration faults cannot pass or leak captures" {
    var original_int: c.struct_sigaction = undefined;
    var original_term: c.struct_sigaction = undefined;
    try std.testing.expectEqual(@as(c_int, 0), c.sigaction(c.SIGINT, null, &original_int));
    try std.testing.expectEqual(@as(c_int, 0), c.sigaction(c.SIGTERM, null, &original_term));
    defer {
        wp03_sigaction_faults(0, 0);
        std.debug.assert(c.sigaction(c.SIGINT, &original_int, null) == 0);
        std.debug.assert(c.sigaction(c.SIGTERM, &original_term, null) == 0);
        signal_owner.store(0, .release);
        pending_signal.store(0, .release);
    }
    for ([_]c_uint{ 1, 2, 2 | 4, 4, 8 }) |mask| {
        wp03_sigaction_faults(mask, 0);
        const expected = error.SignalRestorationFailed;
        if (mask == 1 or mask == 2) {
            try std.testing.expectError(error.SignalInstallationFailed, fixture("printf OUT; printf ERR >&2", .{}));
        } else {
            try std.testing.expectError(expected, fixture("printf OUT; printf ERR >&2", .{}));
        }
        wp03_sigaction_faults(0, 0);
        try std.testing.expectEqual(@as(c_int, 0), c.sigaction(c.SIGINT, &original_int, null));
        try std.testing.expectEqual(@as(c_int, 0), c.sigaction(c.SIGTERM, &original_term, null));
        signal_owner.store(0, .release); // Only after both actual restorations.
        pending_signal.store(0, .release);
        try noRetainedChildren();
    }
}

test "real cancellation arriving during handler restoration overrides exit success" {
    wp03_sigaction_faults(0, 3);
    defer wp03_sigaction_faults(0, 0);
    const result = try fixture("printf OUT; printf ERR >&2", .{});
    defer result.deinit(std.testing.allocator);
    try std.testing.expect(result.failure == .cancelled);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
    try noRetainedChildren();
}

test "invalid retained ownership states refuse before a signal" {
    var invalid = Ownership{ .pid = -1, .valid = false };
    try std.testing.expectError(error.OwnershipLost, invalid.observe());
    try std.testing.expect(!invalid.dispose(std.testing.io, 1));
    var reaped = Ownership{ .pid = -1, .reaped = true };
    try std.testing.expect(try reaped.observe());
    try std.testing.expect(!reaped.dispose(std.testing.io, 1));
    var attempted = Ownership{ .pid = -1, .cleanup_attempted = true };
    try std.testing.expect(!attempted.dispose(std.testing.io, 1));
}

test "expired cleanup retains failure even if its direct child can be reaped" {
    const pid = c.fork();
    try std.testing.expect(pid >= 0);
    if (pid == 0) c._exit(0);
    var info: c.siginfo_t = std.mem.zeroes(c.siginfo_t);
    try std.testing.expectEqual(@as(c_int, 0), c.waitid(c.P_PID, @intCast(pid), &info, c.WEXITED | c.WNOWAIT));
    var owner = Ownership{ .pid = pid };
    try std.testing.expect(!owner.dispose(std.testing.io, 0));
    try std.testing.expect(owner.reaped and !owner.valid and !owner.disposed);
    try noRetainedChildren();
}

test "expired cleanup cannot release or credit a still live child" {
    const pid = c.fork();
    try std.testing.expect(pid >= 0);
    if (pid == 0) { _ = c.usleep(300000); c._exit(0); }
    // Retain the direct, unreaped leader identity and create only its group.
    try std.testing.expectEqual(@as(c_int, 0), c.setpgid(pid, pid));
    var owner = Ownership{ .pid = pid };
    defer {
        std.debug.assert(c.kill(-pid, c.SIGKILL) == 0);
        var status: c_int = 0;
        std.debug.assert(c.waitpid(pid, &status, 0) == pid);
    }
    try std.testing.expect(!owner.dispose(std.testing.io, 0));
    try std.testing.expect(owner.valid and !owner.reaped and !owner.disposed);
}

test "incomplete log pairs and invalid display bounds refuse before spawn" {
    for ([_]usize{ 0, 65537 }) |display| {
        try std.testing.expectError(error.InvalidLogSink, run(std.testing.allocator, std.testing.io, .{
            .argv = &.{ "/bin/sleep", "3" }, .stdout_sink = std.Io.File.stdout(),
            .stderr_sink = std.Io.File.stderr(), .display_bytes = display,
        }));
    }
    try std.testing.expectError(error.InvalidLogSink, run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ "/bin/sleep", "3" }, .stdout_sink = std.Io.File.stdout(),
    }));
    try noRetainedChildren();
}

fn disappearingLog(context: ?*anyopaque, file: std.Io.File) std.Io.File.StatError!std.Io.File.Stat {
    const stat = try std.testing.io.vtable.fileStat(context, file);
    std.debug.assert(c.close(file.handle) == 0);
    return stat;
}

test "log identity disappearing during preflight cannot authorize a child" {
    var temporary = std.testing.tmpDir(.{});
    defer temporary.cleanup();
    const stdout = try temporary.dir.createFile(std.testing.io, "out", .{});
    // The injected stat operation closes this exact descriptor; use the C
    // close's harmless EBADF return for final test-only fallback custody.
    defer _ = c.close(stdout.handle);
    const stderr = try temporary.dir.createFile(std.testing.io, "err", .{});
    defer stderr.close(std.testing.io);
    var table = std.testing.io.vtable.*;
    table.fileStat = disappearingLog;
    var io = std.testing.io;
    io.vtable = &table;
    try std.testing.expectError(error.InvalidLogSink, runLogged(std.testing.allocator, io, .{
        .argv = &.{ "/bin/sleep", "3" },
    }, .{ .stdout = stdout, .stderr = stderr }));
    try noRetainedChildren();
}

test "invalid capture descriptor refuses without claiming bytes" {
    var capture = try Capture.init(std.testing.allocator, 4, 4, null);
    defer capture.list.deinit(std.testing.allocator);
    try std.testing.expectError(error.CaptureFailed, capture.read(std.testing.io, -1));
    try std.testing.expectEqual(@as(u64, 0), capture.observed);
    try std.testing.expectEqual(@as(usize, 0), capture.retained);
}

var cancel_io_calls: usize = 0;
fn canceledIo(_: ?*anyopaque) std.Io.Cancelable!void {
    cancel_io_calls += 1;
    if (cancel_io_calls >= 2) return error.Canceled;
}

test "Io cancellation joins the original group" {
    var table = std.testing.io.vtable.*;
    var io = std.testing.io;
    io.vtable = &table;
    cancel_io_calls = 0;
    table.checkCancel = canceledIo;
    const result = try run(std.testing.allocator, io, .{ .argv = &.{ "/bin/sleep", "3" } });
    defer result.deinit(std.testing.allocator);
    try std.testing.expect(result.failure == .cancelled);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
    try noRetainedChildren();
}

var clock_calls: usize = 0;
var cancel_before_spawn = false;
var stop_after_clock: usize = 3;
fn preSpawnClock(_: ?*anyopaque, _: std.Io.Clock) std.Io.Timestamp {
    clock_calls += 1;
    if (clock_calls >= stop_after_clock) {
        if (cancel_before_spawn) { pending_signal.store(c.SIGTERM, .release); return .{ .nanoseconds = 0 }; }
        return .{ .nanoseconds = 2000000 };
    }
    return .{ .nanoseconds = 0 };
}

test "deadline and pending cancellation after capture allocation precede child effects" {
    var table = std.testing.io.vtable.*;
    table.now = preSpawnClock;
    var io = std.testing.io;
    io.vtable = &table;
    for ([_]usize{ 3, 4 }) |boundary| {
        stop_after_clock = boundary;
        clock_calls = 0;
        cancel_before_spawn = false;
        try std.testing.expectError(error.OperationDeadlineExceeded,
            run(std.testing.allocator, io, .{ .argv = &.{ "/bin/sleep", "3" }, .limits = .{ .wall_ms = 1 } }));
        clock_calls = 0;
        cancel_before_spawn = true;
        try std.testing.expectError(error.OperationCancelled,
            run(std.testing.allocator, io, .{ .argv = &.{ "/bin/sleep", "3" }, .limits = .{ .wall_ms = 1 } }));
    }
    try noRetainedChildren();
}

fn allocationControl(allocator: std.mem.Allocator) !void {
    const result = try run(allocator, std.testing.io, .{ .argv = &.{ "/bin/sh", "-c", "printf OUT; printf ERR >&2" } });
    defer result.deinit(allocator);
    try std.testing.expect(result.failure == null and result.exit_code == 0);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
}

test "allocation failures preserve cleanup and free all retained captures" {
    try std.testing.checkAllAllocationFailures(std.testing.allocator, allocationControl, .{});
    try noRetainedChildren();
}

"""


SPAWN_CLOSURE_PROBE = r"""const std = @import("std");
const owner = @import("validation_process_darwin.zig");
const c = @cImport({ @cInclude("sys/proc_info.h"); @cInclude("sys/wait.h"); @cInclude("unistd.h"); });
extern "c" fn proc_listpids(u32, u32, ?*anyopaque, c_int) c_int;
extern "c" fn proc_pidinfo(c_int, c_int, u64, ?*anyopaque, c_int) c_int;
const Child = struct { pid:c_int,
         wait_rc:c_int,
         wait_pid:c_int,
         wait_code:c_int,
         wait_status:c_int,
         bsd_bytes:c_int,
         parent:u32,
         start_seconds:u64,
         start_microseconds:u64 };
const Fd = struct { fd:c_int, kind:u32 };
fn children(allocator:std.mem.Allocator) ![]Child {
    var pids:[64]c_int=@splat(0);
    const bytes=proc_listpids(c.PROC_PPID_ONLY,@intCast(c.getpid()),&pids,@sizeOf(@TypeOf(pids)));
    if(bytes<0 or bytes>=@sizeOf(@TypeOf(pids)) or @rem(bytes,@sizeOf(c_int))!=0) return error.ChildInspectionFailed;
    var rows:std.ArrayList(Child)=.empty;
    for(pids[0..@intCast(@divTrunc(bytes,@sizeOf(c_int)))]) |pid| {
        if(pid<=0) continue;
        var info:c.siginfo_t=std.mem.zeroes(c.siginfo_t);
        const rc=c.waitid(c.P_PID,@intCast(pid),&info,c.WEXITED|c.WNOWAIT|c.WNOHANG);
        var bsd:c.struct_proc_bsdinfo=std.mem.zeroes(c.struct_proc_bsdinfo);
        const size=proc_pidinfo(pid,c.PROC_PIDTBSDINFO,0,&bsd,@sizeOf(@TypeOf(bsd)));
        try rows.append(allocator,
        .{.pid=pid,
        .wait_rc=rc,
        .wait_pid=info.si_pid,
        .wait_code=info.si_code,
        .wait_status=info.si_status,
        .bsd_bytes=size,
        .parent=bsd.pbi_ppid,
        .start_seconds=bsd.pbi_start_tvsec,
        .start_microseconds=bsd.pbi_start_tvusec});
    }
    return rows.toOwnedSlice(allocator);
}
fn descriptors(allocator:std.mem.Allocator) ![]Fd {
    var buffer:[256]c.struct_proc_fdinfo=undefined;
    const bytes=proc_pidinfo(c.getpid(),c.PROC_PIDLISTFDS,0,&buffer,@sizeOf(@TypeOf(buffer)));
    if(bytes<0 or bytes>=@sizeOf(@TypeOf(buffer)) or @rem(bytes,@sizeOf(c.struct_proc_fdinfo))!=0) return error.DescriptorInspectionFailed;
    var rows:std.ArrayList(Fd)=.empty;
    for(buffer[0..@intCast(@divTrunc(bytes,@sizeOf(c.struct_proc_fdinfo)))]) |fd| try rows.append(allocator,.{.fd=fd.proc_fd,.kind=fd.proc_fdtype});
    return rows.toOwnedSlice(allocator);
}
pub fn main(init:std.process.Init) !void {
    const allocator=init.arena.allocator();
    defer if (@hasDecl(owner, "__native_cov_finish")) owner.__native_cov_finish();
    const args=try init.minimal.args.toSlice(allocator);
    const executable=if(args.len==2) args[1] else "/wp03/nonexistent/executable";
    var environment=std.process.Environ.Map.init(allocator);
    defer environment.deinit();
    const warm=try owner.run(allocator,init.io,.{.argv=&.{"/bin/sh","-c","exit 0"},.environment=&environment});
    defer warm.deinit(allocator);
    if(warm.exit_code!=0 or !warm.leader_reaped or !warm.group_disposed) return error.WarmControlFailed;
    const before_children=try children(allocator);
    if(before_children.len!=0) return error.PreexistingChildren;
    const before_fds=try descriptors(allocator);
    const result=owner.run(allocator,init.io,.{.argv=&.{executable},.environment=&environment});
    var error_name:[]const u8="UnexpectedSuccess";
    if(result) |success| success.deinit(allocator) else |err| {error_name=@errorName(err);}
    const after_children=try children(allocator);
    const after_fds=try descriptors(allocator);
    var reaped:std.ArrayList(c_int)=.empty;
    var unowned:std.ArrayList(c_int)=.empty;
    var recovery:std.ArrayList(Child)=.empty;
    // Recovery is confined to newly observed terminal direct children in this
    // isolated fixture. No PID or process-group sweep, and no signal is sent.
    for(after_children) |child| {
        var terminal:c.siginfo_t=std.mem.zeroes(c.siginfo_t);
        std.c._errno().* = 0;
        const wait_rc = c.waitid(c.P_PID,@intCast(child.pid),&terminal,c.WEXITED|c.WNOWAIT);
        if(wait_rc<0 and std.c.errno(wait_rc)==.CHILD) {
            // A failed SDK posix_spawn may leave a transient kernel listing
            // for an already un-waitable task. It grants no reap/signal right.
            try unowned.append(allocator, child.pid);
            continue;
        }
        if(wait_rc!=0 or terminal.si_pid!=child.pid) return error.UnknownChildTerminal;
        try recovery.append(allocator,
        .{.pid=child.pid,
        .wait_rc=0,
        .wait_pid=terminal.si_pid,
        .wait_code=terminal.si_code,
        .wait_status=terminal.si_status,
        .bsd_bytes=child.bsd_bytes,
        .parent=child.parent,
        .start_seconds=child.start_seconds,
        .start_microseconds=child.start_microseconds});
        var status:c_int=0;
        if(c.waitpid(child.pid,&status,c.WNOHANG)!=child.pid) return error.ExactChildReapFailed;
        try reaped.append(allocator,child.pid);
    }
    var settled = try children(allocator);
    var attempts: usize = 0;
    while(settled.len != 0 and attempts < 200) : (attempts += 1) {
        _ = c.usleep(5000);
        settled = try children(allocator);
    }
    var output:std.Io.Writer.Allocating=.init(allocator);
    var encoder:std.json.Stringify=.{.writer=&output.writer};
    try encoder.write(.{.owner_pid=c.getpid(),
        .warm_exit=warm.exit_code,
        .error_name=error_name,
        .before_children=before_children,
        .after_children=after_children,
        .before_fds=before_fds,
        .after_fds=after_fds,
        .exact_terminal_children_reaped=reaped.items,
        .recovery_terminal_observations=recovery.items,
        .unwaitable_kernel_inventory_pids=unowned.items,
        .settled_children=settled,
        .inventory_settle_attempts=attempts,
        .children_after_exact_reap=try children(allocator),
        .assertion_passed=reaped.items.len==0 and settled.len==0 and after_fds.len==before_fds.len});
    try output.writer.writeByte('\n');try std.Io.File.stdout().writeStreamingAll(init.io,output.written());
    if(reaped.items.len!=0 or settled.len!=0 or after_fds.len!=before_fds.len) std.process.exit(1);
}
"""


def canonical(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode() + b"\n"


def bound_image(role: str) -> Path | None:
    name = os.environ.get("SPEC_KITTY_NATIVE_PROCESS_BINDING")
    if not name:
        return None
    binding = json.loads(Path(name).read_bytes())
    for source, expected in binding["sources"].items():
        assert digest((ROOT / source).read_bytes()) == expected
    for name, expected in binding.get("dependencies", {}).items():
        assert digest(Path(name).read_bytes()) == expected
    image = Path(binding["images"][role]["path"])
    assert digest(image.read_bytes()) == binding["images"][role]["sha256"]
    return image


def foundation_controls() -> str:
    """Pinned private-ownership regressions; real external signals run above.

    Reuse the exact test data without importing a sibling checkout. Only the
    excessive process-budget value changes from 33 to 65 for the new 64 limit.
    Forked owners in the upstream signal helper are intentionally exercised by
    the public Python controls instead, so one native trace has one owner.
    """
    source = FOUNDATION.read_text()
    controls = source[source.index("\nfn fixture(") : source.index("\n// The signal comes")]
    controls += source[source.index("\nfn priorSignal(") :]
    controls = controls.replace(".processes = 33", ".processes = 65")
    return (
        controls
        + NATIVE_FAULT_CONTROLS
        + r"""

test "external budget cancellation disposes the original group" {
    var calls: usize = 0;
    const result = try run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ "/bin/sh", "-c", "exec /bin/sleep 3" },
        .budget_probe = cancelAfterTurns, .budget_context = &calls,
    });
    defer result.deinit(std.testing.allocator);
    try std.testing.expect(result.failure == .external_budget);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
}

test "seal actual native observations after all private controls" {
    if (@hasDecl(@This(), "__native_cov_finish")) @field(@This(), "__native_cov_finish")();
}
"""
    )


def test_retained_native_ownership_and_refusal_controls(tmp_path: Path) -> None:
    if sys.platform != "darwin":
        pytest.skip("Darwin private ownership controls do not qualify another platform")
    assert digest(FOUNDATION.read_bytes()) == FOUNDATION_SHA
    image = bound_image("controls")
    if image is None:
        assert SOURCE.is_file(), "Darwin adaptation must exist before private-source controls"
        source = tmp_path / "controls.zig"
        source.write_text(SOURCE.read_text() + foundation_controls())
        image = tmp_path / "controls"
        shim = tmp_path / "sigaction-faults.c"
        shim.write_text(SIGACTION_FAULT_LIBRARY)
        library = tmp_path / "sigaction-faults.dylib"
        shim_argv = [shutil.which("zig") or "zig", "cc", "-dynamiclib", str(shim), "-o", str(library)]
        shim_build = subprocess.run(shim_argv, capture_output=True, timeout=120)
        (tmp_path / "shim-build.stdout.log").write_bytes(shim_build.stdout)
        (tmp_path / "shim-build.stderr.log").write_bytes(shim_build.stderr)
        assert shim_build.returncode == 0, shim_build.stderr
        argv = [shutil.which("zig") or "zig", "test", "-j1", "-OReleaseSafe", "-lc", str(library), str(source), "--test-no-exec", "-femit-bin=" + str(image)]
        build = subprocess.run(argv, capture_output=True, timeout=120)
        (tmp_path / "build.stdout.log").write_bytes(build.stdout)
        (tmp_path / "build.stderr.log").write_bytes(build.stderr)
        assert build.returncode == 0, build.stderr
        (tmp_path / "build.json").write_bytes(
            canonical(
                {
                    "argv": argv,
                    "source_sha256": digest(SOURCE.read_bytes()),
                    "derived_source_sha256": digest(source.read_bytes()),
                    "image_sha256": digest(image.read_bytes()),
                    "shim_argv": shim_argv,
                    "shim_source_sha256": digest(shim.read_bytes()),
                    "shim_library_sha256": digest(library.read_bytes()),
                }
            )
        )
    result = subprocess.run([str(image)], capture_output=True, timeout=30)
    (tmp_path / "native.stdout.log").write_bytes(result.stdout)
    (tmp_path / "native.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    assert ("All " + str(foundation_controls().count('\ntest "')) + " tests passed.").encode() in result.stderr


@pytest.fixture(scope="session")
def process_probe(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if sys.platform != "darwin":
        pytest.skip("Darwin foundation controls do not qualify another platform")
    assert digest(FOUNDATION.read_bytes()) == FOUNDATION_SHA
    bound = bound_image("probe")
    if bound is not None:
        return bound
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
    assert observed == {"started": None, "error_name": "FileNotFound", "cleanup_complete": False}


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


@pytest.mark.parametrize("mode", ["same-descriptor", "same-inode", "nonempty", "hardlink"])
def test_log_sinks_refuse_aliases_and_existing_bytes_before_child_effect(process_probe: Path, tmp_path: Path, mode: str) -> None:
    marker = tmp_path / "child-started"
    path = request(tmp_path, python("import pathlib,sys\npathlib.Path(sys.argv[1]).write_bytes(b'effect')", str(marker)))
    value = json.loads(path.read_bytes())
    value["sink_mode"] = mode
    if mode == "same-inode":
        value["stderr_log"] = value["stdout_log"]
    if mode == "hardlink":
        (tmp_path / "stdout.log").touch()
        (tmp_path / "alias.log").hardlink_to(tmp_path / "stdout.log")
    path.write_bytes(canonical(value))
    result = subprocess.run([str(process_probe), str(path)], capture_output=True, timeout=12)
    (tmp_path / "owner.stdout.log").write_bytes(result.stdout)
    (tmp_path / "owner.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed.get("error_name") == "InvalidLogSink", observed
    assert observed["started"] is None and not observed["cleanup_complete"]
    assert not marker.exists(), "Invalid sinks must refuse before a child effect"


def test_raw_log_and_bounded_excerpt_have_independent_byte_accounting(process_probe: Path, tmp_path: Path) -> None:
    path = request(tmp_path, python("import os\nos.write(1,b'a'*12000)"))
    value = json.loads(path.read_bytes())
    value["display_bytes"] = 17
    path.write_bytes(canonical(value))
    result = subprocess.run([str(process_probe), str(path)], capture_output=True, timeout=12)
    (tmp_path / "owner.stdout.log").write_bytes(result.stdout)
    (tmp_path / "owner.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)["result"]
    assert observed["failure"] is None and observed["exit_code"] == 0
    assert observed["stdout"] == "a" * 17
    assert observed["stdout_observed_bytes"] == observed["stdout_retained_bytes"] == 12000
    assert (tmp_path / "stdout.log").read_bytes() == b"a" * 12000


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_exact_output_quota_is_success_with_complete_raw_bytes(process_probe: Path, tmp_path: Path, stream: str) -> None:
    observed = invoke(
        process_probe, tmp_path, python("import os,sys\nos.write(int(sys.argv[1]),b'1234')", "1" if stream == "stdout" else "2"), **{stream + "_bytes": 4}
    )
    result = observed["result"]
    assert result["failure"] is None and result["exit_code"] == 0
    assert result[stream + "_observed_bytes"] == result[stream + "_retained_bytes"] == 4
    assert (tmp_path / (stream + ".log")).read_bytes() == b"1234"


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_actual_log_write_failure_is_not_output_or_cleanup_success(process_probe: Path, tmp_path: Path, stream: str) -> None:
    path = request(tmp_path, python("import os,time,sys\nos.write(int(sys.argv[1]),b'output');time.sleep(3)", "1" if stream == "stdout" else "2"))
    value = json.loads(path.read_bytes())
    value["sink_mode"] = "readonly" if stream == "stdout" else "readonly-stderr"
    path.write_bytes(canonical(value))
    result = subprocess.run([str(process_probe), str(path)], capture_output=True, timeout=12)
    (tmp_path / "owner.stdout.log").write_bytes(result.stdout)
    (tmp_path / "owner.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)["result"]
    assert observed["failure"] == "log_failed"
    assert observed[stream + "_observed_bytes"] == 6 and observed[stream + "_retained_bytes"] is None
    assert observed["leader_reaped"] and observed["group_disposed"]
    assert not observed["all_owned_children_terminal"]
    assert (tmp_path / (stream + ".log")).read_bytes() == b""


@pytest.fixture(scope="session")
def spawn_closure_probe(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if sys.platform != "darwin":
        pytest.skip("Darwin spawn custody controls do not qualify another platform")
    bound = bound_image("spawn-closure")
    if bound is not None:
        return bound
    directory = tmp_path_factory.mktemp("native-spawn-closure")
    (directory / "validation_process_darwin.zig").write_bytes(SOURCE.read_bytes())
    source = directory / "probe.zig"
    source.write_text(SPAWN_CLOSURE_PROBE)
    image = directory / "probe"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(source), "-femit-bin=" + str(image)]
    build = subprocess.run(argv, capture_output=True, timeout=120)
    (directory / "build.stdout.log").write_bytes(build.stdout)
    (directory / "build.stderr.log").write_bytes(build.stderr)
    assert build.returncode == 0, build.stderr
    (directory / "build.json").write_bytes(
        canonical(
            {"argv": argv, "source_sha256": digest(SOURCE.read_bytes()), "harness_sha256": digest(source.read_bytes()), "image_sha256": digest(image.read_bytes())}
        )
    )
    return image


@pytest.mark.parametrize("failure", ["missing", "denied", "invalid-format"])
def test_failed_spawn_retains_no_child_or_pipe_descriptors(spawn_closure_probe: Path, tmp_path: Path, failure: str) -> None:
    executable = tmp_path / "executable"
    if failure != "missing":
        executable.write_bytes(b"invalid executable format\n")
        executable.chmod(0o644 if failure == "denied" else 0o755)
    result = subprocess.run([str(spawn_closure_probe), str(executable)], capture_output=True, timeout=12)
    (tmp_path / "owner.stdout.log").write_bytes(result.stdout)
    (tmp_path / "owner.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr + result.stdout
    observed = json.loads(result.stdout)
    assert observed["warm_exit"] == 0
    assert observed["error_name"] == {"missing": "FileNotFound", "denied": "AccessDenied", "invalid-format": "SpawnFailed"}[failure]
    assert observed["before_children"] == observed["settled_children"] == []
    assert set(observed["unwaitable_kernel_inventory_pids"]) == {row["pid"] for row in observed["after_children"]}
    assert observed["recovery_terminal_observations"] == []
    assert observed["exact_terminal_children_reaped"] == [], "The adapter must join its own child, without test-harness recovery"
    assert observed["before_fds"] == observed["after_fds"]
    assert observed["assertion_passed"]


def candidate_spawn_closure_source() -> str:
    """Drive the public candidate API through the existing kernel/FD witness."""
    replacements = (
        (
            'const owner = @import("validation_process_darwin.zig");',
            'const owner = @import("validation_candidate.zig");\nconst warm_owner = @import("warm_owner.zig");\nextern "c" fn wp03_spawn_faults(c_uint) void;',
        ),
        (
            'const executable=if(args.len==2) args[1] else "/wp03/nonexistent/executable";',
            "if(args.len!=5) return error.InvalidArguments;\n    const executable=args[1];\n    const fault_mode=try std.fmt.parseInt(c_uint,args[4],10);",
        ),
        ("const warm=try owner.run(", "const warm=try warm_owner.run("),
        (
            "const result=owner.run(allocator,init.io,.{.argv=&.{executable},.environment=&environment});",
            'const request_bytes=try owner.json(allocator,.{.schema_version=1,.repository=args[2],.base="HEAD",.destination=args[3],.git_executable=executable});\n'
            "    const request=try owner.parse(allocator,request_bytes);\n"
            "    wp03_spawn_faults(fault_mode);\n    const result=owner.capture(allocator,init.io,&environment,request.value);\n    wp03_spawn_faults(0);",
        ),
        (
            "if(result) |success| success.deinit(allocator) else |err| {error_name=@errorName(err);}",
            "if(result) |_| {} else |err| {error_name=@errorName(err);}",
        ),
    )
    source = SPAWN_CLOSURE_PROBE
    for original, replacement in replacements:
        assert source.count(original) == 1, "The shared custody witness changed; review the actual API composition"
        source = source.replace(original, replacement)
    return source


@pytest.fixture(scope="session")
def candidate_spawn_closure_probe(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if sys.platform != "darwin":
        pytest.skip("Darwin candidate custody controls do not qualify another platform")
    directory = tmp_path_factory.mktemp("candidate-spawn-closure")
    # A retained baseline source can reproduce genuine RED without reverting
    # an interrupted implementation or silently substituting its new source.
    candidate = Path(os.environ.get("SPEC_KITTY_CANDIDATE_SPAWN_SOURCE", str(ROOT / "tools/zig/validation_candidate.zig")))
    # The unchanged foundation warms std.process.spawn itself, including its
    # lazy runtime descriptors, before the failed-spawn descriptor comparison.
    assert digest(FOUNDATION.read_bytes()) == FOUNDATION_SHA
    sources = [candidate, FOUNDATION]
    for source in sources:
        (directory / ("validation_candidate.zig" if source == candidate else "warm_owner.zig")).write_bytes(source.read_bytes())
    probe = directory / "probe.zig"
    probe.write_text(candidate_spawn_closure_source())
    shim = directory / "spawn-faults.c"
    shim.write_text(SIGACTION_FAULT_LIBRARY)
    library = directory / "spawn-faults.dylib"
    shim_build = subprocess.run(["cc", "-dynamiclib", str(shim), "-o", str(library)], capture_output=True, timeout=30)
    (directory / "shim.stdout.log").write_bytes(shim_build.stdout)
    (directory / "shim.stderr.log").write_bytes(shim_build.stderr)
    assert shim_build.returncode == 0, shim_build.stderr
    image = directory / "probe"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(probe), str(library), "-femit-bin=" + str(image)]
    built = subprocess.run(argv, capture_output=True, timeout=120)
    (directory / "build.stdout.log").write_bytes(built.stdout)
    (directory / "build.stderr.log").write_bytes(built.stderr)
    (directory / "build.json").write_bytes(
        canonical(
            {
                "argv": argv,
                "exit_code": built.returncode,
                "sources": {str(source): digest(source.read_bytes()) for source in sources},
                "harness_sha256": digest(probe.read_bytes()),
                "shim_sha256": digest(shim.read_bytes()),
                "shim_image_sha256": digest(library.read_bytes()),
                "image_sha256": digest(image.read_bytes()) if built.returncode == 0 else None,
            }
        )
    )
    assert built.returncode == 0, built.stderr
    return image


@pytest.mark.parametrize("failure", ["missing", "denied", "invalid-format"])
def test_candidate_failed_git_spawn_retains_no_child_or_pipe_descriptors(
    candidate_spawn_closure_probe: Path, repository: Path, tmp_path: Path, failure: str
) -> None:
    executable = tmp_path / "git executable"
    if failure != "missing":
        executable.write_bytes(b"invalid executable format\n")
        executable.chmod(0o644 if failure == "denied" else 0o755)
    destination = tmp_path / "never created candidate"
    before = snapshot(repository)
    result = subprocess.run([str(candidate_spawn_closure_probe), str(executable), str(repository), str(destination), "0"], capture_output=True, timeout=12)
    (tmp_path / "owner.stdout.log").write_bytes(result.stdout)
    (tmp_path / "owner.stderr.log").write_bytes(result.stderr)
    assert snapshot(repository) == before
    assert not destination.exists()
    assert result.returncode == 0, result.stderr + result.stdout
    observed = json.loads(result.stdout)
    assert observed["warm_exit"] == 0
    assert observed["error_name"] == {"missing": "FileNotFound", "denied": "AccessDenied", "invalid-format": "InvalidExe"}[failure]
    assert observed["before_children"] == observed["settled_children"] == []
    assert set(observed["unwaitable_kernel_inventory_pids"]) == {row["pid"] for row in observed["after_children"]}
    assert observed["recovery_terminal_observations"] == []
    assert observed["exact_terminal_children_reaped"] == [], "Candidate capture must not require test-harness child recovery"
    assert observed["before_fds"] == observed["after_fds"]
    assert observed["assertion_passed"]


@pytest.mark.parametrize("mode", [1, 2, 4, 7, 8, 9, 10])
def test_candidate_sdk_setup_and_postlaunch_failure_retains_custody(candidate_spawn_closure_probe: Path, repository: Path, tmp_path: Path, mode: int) -> None:
    """Real SDK cleanup runs even when its reported status is faulted."""
    destination = tmp_path / "never created candidate"
    before = snapshot(repository)
    executable = shutil.which("git")
    assert executable is not None
    result = subprocess.run([str(candidate_spawn_closure_probe), executable, str(repository), str(destination), str(mode)], capture_output=True, timeout=12)
    (tmp_path / "owner.stdout.log").write_bytes(result.stdout)
    (tmp_path / "owner.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr + result.stdout
    observed = json.loads(result.stdout)
    assert observed["error_name"] == ("SpawnMetadataCleanupFailed" if mode in (8, 9) else "SpawnSetupFailed")
    assert observed["before_children"] == observed["settled_children"] == []
    assert set(observed["unwaitable_kernel_inventory_pids"]) == {row["pid"] for row in observed["after_children"]}
    assert observed["recovery_terminal_observations"] == observed["exact_terminal_children_reaped"] == []
    assert observed["before_fds"] == observed["after_fds"]
    assert observed["assertion_passed"]
    assert snapshot(repository) == before
    assert not destination.exists()


@pytest.mark.parametrize("cwd_mode", ["path", "dir"])
def test_declared_argv_environment_and_cwd_are_exact_and_parent_descriptor_is_preserved(process_probe: Path, tmp_path: Path, cwd_mode: str) -> None:
    directory = tmp_path / "private candidate"
    directory.mkdir()
    arguments = ["", "space value", "line\nbreak", "é", "--flag"]
    path = request(tmp_path, [str(process_probe), "echo-context", *arguments])
    value = json.loads(path.read_bytes())
    environment = {"EXACT_VALUE": "space and\nnewline", "ZIG_PROGRESS": "literal-data", "LC_ALL": "C"}
    value.update(cwd=str(directory), cwd_mode=cwd_mode, environment=[{"name": k, "value": v} for k, v in environment.items()], extra_fd_argument=True)
    path.write_bytes(canonical(value))
    result = subprocess.run([str(process_probe), str(path)], capture_output=True, timeout=12)
    (tmp_path / "owner.stdout.log").write_bytes(result.stdout)
    (tmp_path / "owner.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)["result"]
    assert observed["failure"] is None and observed["exit_code"] == 0
    child = json.loads((tmp_path / "stdout.log").read_bytes())
    # Native child startup reports the actual received map directly.
    assert child["argv"] == arguments and child["cwd"] == str(directory.resolve())
    assert {entry["name"]: entry["value"] for entry in child["environment"]} == environment
    assert child["stdin"] == "" and child["extra_fd_inherited"] is False


@pytest.mark.parametrize("invalid", ["argv-nul", "cwd-nul", "environment-key", "environment-value"])
def test_probe_and_native_boundaries_refuse_invalid_inputs_before_effect(process_probe: Path, tmp_path: Path, invalid: str) -> None:
    marker = tmp_path / "effect"
    path = request(tmp_path, python("import pathlib,sys\npathlib.Path(sys.argv[1]).touch()", str(marker)))
    value = json.loads(path.read_bytes())
    if invalid == "argv-nul":
        value["argv"][-1] += "\0suffix"
    elif invalid == "cwd-nul":
        value["cwd"] = str(tmp_path) + "\0suffix"
    else:
        value["environment"] = [
            {"name": "BAD=KEY" if invalid == "environment-key" else "KEY", "value": "value\0suffix" if invalid == "environment-value" else "value"}
        ]
    path.write_bytes(canonical(value))
    result = subprocess.run([str(process_probe), str(path)], capture_output=True, timeout=12)
    (tmp_path / "owner.stdout.log").write_bytes(result.stdout)
    (tmp_path / "owner.stderr.log").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["error_name"] == ("InvalidEnvironment" if invalid.startswith("environment") else "InvalidArguments")
    assert observed["started"] is None and not observed["cleanup_complete"]
    assert not marker.exists()


def test_binding_cannot_omit_the_actual_process_implementation(receipt_binary: Path, bound_inputs: dict[str, Any]) -> None:
    """The public binding must carry the implementation that will own execution.

    This exercises the existing binding entry, rather than treating an absent
    executor or a compiler error as a behavioral RED.
    """
    names = {source["name"] for source in bound_inputs["binding"]["native_sources"]}
    assert "validation_process_darwin.zig" in names, names


EXECUTION_SOURCE = ROOT / "tools/zig/validation_execution.zig"

# This private fixture has no process-creation, network, dynamic-loading, or
# arbitrary-evaluation surface. Its only first-party import is copied from exact
# bytes subsequently verified against the staged Git candidate. It writes only its declared external
# marker and reads candidate app.py plus the declared dependency/release files.
SERIAL_FIXTURE = r"""const std = @import("std");
const module = @import("fixture_module.zig");
pub fn main(init: std.process.Init) !void {
    const a = init.arena.allocator();
    const args = try init.minimal.args.toSlice(a);
    if (args.len != 6) return error.InvalidArguments;
    if (init.environ_map.count() != 1 or !std.mem.eql(u8, init.environ_map.get("WP03_FLAG") orelse "", "declared value")) return error.InvalidEnvironment;
    const app = try std.Io.Dir.cwd().readFileAlloc(init.io, "app.py", a, .limited(1024));
    try std.Io.File.stdout().writeStreamingAll(init.io, module.value ++ "\n");
    if (!std.mem.eql(u8, module.value, "STAGED") or !std.mem.eql(u8, app, "PASS\n")) std.process.exit(7);
    const dependency = try std.Io.Dir.cwd().readFileAlloc(init.io, args[3], a, .limited(1024));
    if (!std.mem.eql(u8, dependency, "GOOD\n")) std.process.exit(9);
    if (std.mem.eql(u8, args[1], "consumer")) {
        const marker = try std.Io.Dir.cwd().readFileAlloc(init.io, args[2], a, .limited(1024));
        if (!std.mem.eql(u8, marker, "producer\n")) return error.RequiredProducerMissing;
    }
    const marker = try std.Io.Dir.cwd().createFile(init.io, args[2], .{});
    try marker.writeStreamingAll(init.io, if (std.mem.eql(u8, args[1], "producer")) "producer\n" else "consumer\n");
    marker.close(init.io);
    if (std.mem.eql(u8, args[4], "delay")) std.Io.sleep(init.io, .fromMilliseconds(400), .awake) catch {};
    if (std.mem.eql(u8, args[4], "wait")) {
        var count: usize = 0;
        while (count < 300) : (count += 1) {
            const release = std.Io.Dir.cwd().openFile(init.io, args[5], .{}) catch {
                std.Io.sleep(init.io, .fromMilliseconds(10), .awake) catch {};
                continue;
            };
            release.close(init.io);
            break;
        }
        if (count == 300) return error.ReleaseTimeout;
    }
    const output: [20000]u8 = @splat('O');
    const diagnostic: [9000]u8 = @splat('E');
    try std.Io.File.stdout().writeStreamingAll(init.io, &output);
    if (std.mem.eql(u8, args[4], "warning")) try std.Io.File.stderr().writeStreamingAll(init.io, "Warning: recipe step\n");
    try std.Io.File.stderr().writeStreamingAll(init.io, &diagnostic);
    if (std.mem.eql(u8, args[4], "nonzero")) std.process.exit(13);
}
"""


@pytest.fixture(scope="session")
def executor_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from tests.local_validation.test_receipt import NATIVE_SOURCES, retain_native_build_metadata

    assert EXECUTION_SOURCE.is_file(), "Missing executor is setup failure, never a behavioral RED"
    supplied = os.environ.get("SPEC_KITTY_NATIVE_EXECUTION_BINDING")
    if supplied:
        binding = json.loads(Path(supplied).read_bytes())
        for name, expected in binding["sources"].items():
            assert digest((ROOT / name).read_bytes()) == expected
        image = Path(binding["image"])
        assert digest(image.read_bytes()) == binding["image_sha256"]
        return image
    image = tmp_path_factory.mktemp("serial-executor") / "executor"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(EXECUTION_SOURCE), "-femit-bin=" + str(image)]
    compiled = subprocess.run(argv, check=True, capture_output=True, timeout=120)
    retain_native_build_metadata(image, NATIVE_SOURCES, argv, compiled)
    return image


@pytest.fixture(scope="session")
def serial_program(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    from tests.local_validation.test_receipt import file_pin, retain_native_build_metadata

    build = tmp_path_factory.mktemp("source-closed-serial-program")
    (build / "fixture.zig").write_text(SERIAL_FIXTURE)
    (build / "fixture_module.zig").write_text('pub const value = "STAGED";\n')
    image = build / "program"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(build / "fixture.zig"), "-femit-bin=" + str(image)]
    compiled = subprocess.run(argv, check=True, capture_output=True, timeout=120)
    retain_native_build_metadata(image, [build / "fixture.zig", build / "fixture_module.zig"], argv, compiled)
    runtime = build / "runtime.json"
    runtime.write_bytes(
        canonical({"schema_version": 1, "scope": "private-native-fixture-import-closure", "files": [file_pin(image), file_pin(build / "fixture_module.zig")]})
    )
    return {"image": image, "build": build, "runtime": runtime}


def execution_budget_fault(checks: dict[str, Any], qualifications: list[dict[str, Any]], fault: str | None) -> None:
    if fault == "stdout-quota":
        for check in checks.values():
            check["budgets"]["stdout_bytes"] = 4096
        for qualification in qualifications:
            qualification["limits"]["stdout_bytes"] = 4096
    if fault == "oversized-budget":
        for check in checks.values():
            check["budgets"]["stdout_bytes"] = 32 * 1024 * 1024
        for qualification in qualifications:
            qualification["limits"]["stdout_bytes"] = 32 * 1024 * 1024


def execution_policy_fault(
    checks: dict[str, Any],
    qualifications: list[dict[str, Any]],
    commands: dict[str, list[str]],
    executor_binary: Path,
    tmp_path: Path,
    fault: str | None,
) -> None:
    from tests.local_validation.test_receipt import file_pin

    if fault == "environment":
        checks["z-producer"]["environment"]["WP03_FLAG"] = "different value"
    if fault == "budget":
        checks["z-producer"]["budgets"]["wall_ms"] = 4000
    execution_budget_fault(checks, qualifications, fault)
    if fault == "platform":
        checks["z-producer"]["platforms"] = ["linux"]
    if fault == "multiple-commands":
        for name in commands:
            checks[name]["argv"] = [commands[name], commands[name]]
    if fault == "producer":
        other = tmp_path / "different-producer"
        shutil.copyfile(executor_binary, other)
        other.chmod(executor_binary.stat().st_mode)
        for qualification in qualifications:
            qualification["producer"] = {key: value for key, value in file_pin(other).items() if key in {"path", "sha256", "mode"}}
    if fault == "incomplete-source":
        for qualification in qualifications:
            qualification["producer_sources"] = [row for row in qualification["producer_sources"] if Path(row["path"]).name != "validation_selection.zig"]
            qualification["producer_source_tool_sha256"] = digest(b"".join(Path(row["path"]).read_bytes() for row in qualification["producer_sources"]))
    if fault == "omitted-command":
        for qualification in qualifications:
            qualification["runtime_files"] = [row for row in qualification["runtime_files"] if row["path"] != qualification["argv"][0]]
    if fault == "no-qualification":
        qualifications.clear()


def execution_recipe_fault(authority: Path, source: dict[str, str], fault: str | None) -> None:
    if fault in {"recipe-always", "recipe-producer-roster"}:
        document = json.loads(authority.read_bytes())
        document.update(schema_version=2, migration=[source])
        for name, check in document["checks"].items():
            check["recipe"] = {
                "source": source,
                "python_version": "3.12",
                "advisory": False,
                "required_inputs": ["candidate"],
                "conditions": ["always" if fault == "recipe-always" else "success"],
                "instances": ["native"],
                "applicability": "routing",
                "packages": {},
                "instance_environment": {},
                "observed_dependencies": ["z-producer"] if name == "a-consumer" else ["changes"],
            }
        authority.write_bytes(canonical(document))


def execution_binding_fault(bind_request: Path, fault: str | None) -> None:
    if fault in {"missing-selected", "argv", "multiple-commands", "omitted-command"}:
        value = json.loads(bind_request.read_bytes())
        if fault == "omitted-command":
            image = value["checks"][0]["argv"][0][0]
            value["files"] = [row for row in value["files"] if row["path"] != image]
            value["files"].append({"role": "toolchain", "path": str(Path(shutil.which("zig") or "zig").resolve()), "candidate_path_hex": None})
        elif fault == "missing-selected":
            value["checks"] = value["checks"][:1]
        elif fault == "argv":
            value["checks"][0]["argv"][0].append("unexpected argument")
        else:
            for check in value["checks"]:
                check["argv"] *= 2
        bind_request.write_bytes(canonical(value))


def execution_request_fault(request: dict[str, str], logs: Path, qualification_file: Path, manifest_path: Path, fault: str | None) -> None:
    if fault == "mode":
        request["mode"] = "commit"
    if fault == "specification":
        request["specification"] = str(qualification_file)
    if fault == "public-diagnostics":
        logs.chmod(0o755)
    if fault == "candidate-diagnostics":
        request["diagnostics"] = json.loads(manifest_path.read_bytes())["root"]


def configure_recipe_control(
    checks: dict[str, Any],
    qualifications: list[dict[str, Any]],
    commands: dict[str, list[str]],
    source: dict[str, str],
    tmp_path: Path,
    case: str,
) -> None:
    """Bind real source-closed argv; no callback or caller Boolean runs a step."""
    import copy

    original = {name: copy.deepcopy(q) for name, q in zip(commands, qualifications, strict=True)}
    producer = commands["z-producer"]
    second = [*producer]
    second[1] = "consumer"
    cleanup = [*producer]
    cleanup[2] = str(tmp_path / "recipe-cleanup-marker")
    steps = [[*producer], second, [*producer]]
    conditions = ["success", "success", "always"]
    if case in {"nonzero", "warning"}:
        steps[1][4] = case
        steps.insert(2, [*producer])
        steps[2][2] = str(tmp_path / "recipe-skipped-marker")
        steps[-1] = cleanup
        conditions = ["success", "success", "success", "always"]
    if case in {"quota", "deadline"}:
        steps[1][1] = "producer"
        steps[1][2] = str(tmp_path / "recipe-second-marker")
        steps[-1] = cleanup
        if case == "deadline":
            steps[0][4] = steps[1][4] = "delay"
    checks["z-producer"]["argv"] = steps
    qualifications.clear()
    seen: set[tuple[str, ...]] = set()
    for name, check in checks.items():
        check["recipe"] = {
            "source": source,
            "python_version": "3.12",
            "advisory": False,
            "required_inputs": ["candidate"],
            "conditions": conditions if name == "z-producer" else ["success"],
            "instances": ["native"] * len(check["argv"]),
            "applicability": "routing",
            "packages": {},
            "instance_environment": {},
            "observed_dependencies": check["dependencies"],
        }
        check["stderr_policy"] = ["allow"] * len(check["argv"])
        if name == "z-producer" and case == "warning":
            check["stderr_policy"][1] = "reject-warning-prefix"
        if case == "quota":
            check["budgets"]["stdout_bytes"] = 30000
        if case == "deadline":
            check["budgets"]["wall_ms"] = 700
        for argv in check["argv"]:
            if tuple(argv) in seen:
                continue
            seen.add(tuple(argv))
            q = copy.deepcopy(original[name])
            q["argv"] = argv
            if case == "quota":
                q["limits"]["stdout_bytes"] = 30000
            if case == "deadline":
                q["limits"]["wall_ms"] = 700
            qualifications.append(q)


def execution_inputs(
    candidate_binary: Path,
    executor_binary: Path,
    repository: Path,
    tmp_path: Path,
    serial_program: dict[str, Any],
    *,
    invalid_image: bool = False,
    waiting: bool = False,
    staged: bytes = b"PASS\n",
    fault: str | None = None,
    recipe_case: str | None = None,
) -> dict[str, Any]:
    from tests.local_validation.test_candidate import capture, git
    from tests.local_validation.test_receipt import NATIVE_SOURCES, file_pin, receipt_call

    tools = repository / "tools/zig"
    tools.mkdir(parents=True)
    for source in NATIVE_SOURCES:
        shutil.copyfile(source, tools / source.name)
    (repository / "fixture.zig").write_text(SERIAL_FIXTURE)
    module = repository / "fixture_module.zig"
    module.write_text('pub const value = "STAGED";\n')
    # Exact source bytes used by the compiled first-party import match staging.
    assert module.read_bytes() == (serial_program["build"] / module.name).read_bytes()
    (repository / "app.py").write_bytes(staged)
    launcher = repository / "launcher.sh"
    launcher.write_text('#!/bin/sh\nexec "$WP03_NATIVE" execute "$WP03_REQUEST"\n')
    lock = repository / "dependencies.lock"
    lock.write_bytes(b"fixture=1\n")
    observed = tmp_path / "observed-dependency"
    observed.write_bytes(b"GOOD\n")
    marker = tmp_path / "producer-marker"
    release = tmp_path / "release"
    image = tmp_path / "fixture-image"
    shutil.copyfile(serial_program["image"], image)
    image.chmod(0o700)
    if invalid_image:
        image = tmp_path / "invalid-image"
        image.write_bytes(b"unexecutable-format\n")
        image.chmod(0o700)
    q_sources = [*NATIVE_SOURCES, serial_program["build"] / "fixture.zig", serial_program["runtime"]]
    runtime_files = [file_pin(path) for path in [image, observed, serial_program["build"] / "fixture_module.zig"]]
    policy_source = {"path": "fixture.zig", "sha256": digest(SERIAL_FIXTURE.encode()), "role": "private-fixture"}
    limits = {"wall_ms": 5000, "cleanup_ms": 1000, "stdout_bytes": 65536, "stderr_bytes": 65536, "processes": 4, "resident_bytes": 268435456}
    commands = {
        "a-consumer": [str(image), "consumer", str(marker), str(observed), "ordinary", str(release)],
        "z-producer": [str(image), "producer", str(marker), str(observed), "wait" if waiting else "ordinary", str(release)],
    }
    if fault == "command-alias":
        alias = tmp_path / "command-alias"
        alias.symlink_to(image)
        for argv in commands.values():
            argv[0] = str(alias)
    import platform

    architecture = {"arm64": "aarch64", "x86_64": "x86_64"}[platform.machine()]
    qualifications = [
        {
            "schema_version": 1,
            "scope": "exact-isolated-source-no-process-creation",
            "platform": architecture + "-macos",
            "argv": argv,
            "environment_names": ["WP03_FLAG"],
            "limits": limits,
            "program_path_hex": b"fixture.zig".hex(),
            "program_sha256": digest(SERIAL_FIXTURE.encode()),
            "producer": {key: value for key, value in file_pin(executor_binary).items() if key in {"path", "sha256", "mode"}},
            "producer_sources": [file_pin(path) for path in q_sources],
            "producer_source_tool_sha256": digest(b"".join(path.read_bytes() for path in q_sources)),
            "process_source_sha256": digest(SOURCE.read_bytes()),
            "compiler_version": "0.16.0",
            "runtime_manifest_sha256": digest(serial_program["runtime"].read_bytes()),
            "runtime_files": runtime_files,
        }
        for argv in commands.values()
    ]
    authority = repository / "gates.json"
    checks = {
        name: {
            "argv": [argv],
            "modes": ["full", "commit"],
            "platforms": ["macos"],
            "dependencies": ["z-producer"] if name == "a-consumer" else [],
            "environment": {"WP03_FLAG": "declared value"},
            "budgets": {
                "sampled_processes" if key == "processes" else "sampled_resident_bytes" if key == "resident_bytes" else key: value for key, value in limits.items()
            },
        }
        for name, argv in commands.items()
    }
    execution_policy_fault(checks, qualifications, commands, executor_binary, tmp_path, fault)
    if recipe_case:
        configure_recipe_control(checks, qualifications, commands, policy_source, tmp_path, recipe_case)
    authority.write_bytes(
        canonical(
            {
                "schema_version": 2 if recipe_case else 1,
                "source": policy_source,
                **({"migration": [policy_source]} if recipe_case else {}),
                "routing": {"filters": {"core": ["src/**"]}, "job_gates": {name: [] for name in commands}},
                "checks": checks,
            }
        )
    )
    execution_recipe_fault(authority, policy_source, fault)
    qualification_file = repository / "qualifications.json"
    qualification_file.write_bytes(canonical({"receipt_qualifications": qualifications}))
    git(repository, "add", "--all")
    captured, capture_request = capture(candidate_binary, repository, tmp_path)
    assert captured.returncode == 0, captured.stderr
    manifest_path = Path(capture_request["destination"]) / "candidate.json"
    # Deliberately conflicting live import and input remain outside the candidate.
    module.write_text('pub const value = "LIVE-TRAP";\n')
    (repository / "app.py").write_bytes(b"LIVE-TRAP\n")
    files: list[dict[str, Any]] = [
        {"role": role, "path": str(path), "candidate_path_hex": os.fsencode(path.relative_to(repository)).hex()}
        for role, path in [
            ("launcher", launcher),
            ("specification", authority),
            ("specification", qualification_file),
            ("dependency_lock", lock),
            *(("native_source", tools / source.name) for source in NATIVE_SOURCES),
        ]
    ]
    files.append({"role": "toolchain", "path": str(image), "candidate_path_hex": None})
    external = [*q_sources, *[Path(row["path"]) for row in runtime_files]]
    known = {row["path"] for row in files}
    for path in external:
        resolved = str(path.resolve())
        if resolved not in known:
            files.append({"role": "observed_dependency", "path": str(path), "candidate_path_hex": None})
            known.add(resolved)
    bind_request = tmp_path / "binding-request.json"
    bind_request.write_bytes(
        canonical(
            {
                "schema_version": 1,
                "candidate_manifest": str(manifest_path),
                "files": files,
                "environment_names": ["WP03_FLAG"],
                "checks": [{"id": name, "argv": checks[name]["argv"], "closure_proof": None} for name in commands],
            }
        )
    )
    execution_binding_fault(bind_request, fault)
    environment = os.environ.copy()
    environment["WP03_FLAG"] = "declared value"
    result = receipt_call(executor_binary, "bind", bind_request, environment)
    assert result.returncode == 0, result.stderr
    binding_path = tmp_path / "binding.json"
    binding_path.write_bytes(result.stdout)
    logs = tmp_path / "logs"
    logs.mkdir(mode=0o700)
    request_path = tmp_path / "execution.json"
    request = {"binding": str(binding_path), "specification": str(authority), "mode": "full", "diagnostics": str(logs)}
    execution_request_fault(request, logs, qualification_file, manifest_path, fault)
    request_path.write_bytes(canonical(request))
    return {
        "request": request,
        "request_path": request_path,
        "bind_request": bind_request,
        "binding_path": binding_path,
        "environment": environment,
        "marker": marker,
        "observed": observed,
        "release": release,
        "logs": logs,
        "manifest_path": manifest_path,
        "repository": repository,
        "checks": checks,
        "authority": authority,
        "qualifications": qualifications,
        "qualification_file": qualification_file,
    }


def run_execution(image: Path, inputs: dict[str, Any]) -> tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]:
    result = subprocess.run([str(image), "execute", str(inputs["request_path"])], env=inputs["environment"], capture_output=True, timeout=30)
    report = json.loads((inputs["logs"] / "run.json").read_bytes()) if (inputs["logs"] / "run.json").exists() else {}
    return result, report


def test_native_recipe_preserves_declared_order_and_complete_check_logs(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, serial_program: dict[str, Any]
) -> None:
    inputs = execution_inputs(candidate_binary, executor_binary, repository, tmp_path, serial_program, recipe_case="ordinary")
    before = snapshot(repository)
    result, report = run_execution(executor_binary, inputs)
    assert snapshot(repository) == before
    assert result.returncode == 0, result.stderr
    assert report["accepted"] and report["qualified_scope_joined"]
    assert report["selected_checks"] == ["z-producer", "a-consumer"]
    producer, consumer = report["results"]
    assert producer["status"] == consumer["status"] == "passed"
    assert [row["status"] for row in producer["steps"]] == ["passed"] * 3
    assert inputs["marker"].read_bytes() == b"consumer\n"
    assert sum(Path(row["stdout_log"]["path"]).stat().st_size for row in producer["steps"]) == 3 * 20007
    assert producer["result"]["stdout_retained_bytes"] == 3 * 20007
    assert len(producer["result"]["stdout"]) == 8192
    for row in producer["steps"]:
        assert Path(row["stdout_log"]["path"]).read_bytes() == b"STAGED\n" + b"O" * 20000
        assert Path(row["stderr_log"]["path"]).read_bytes() == b"E" * 9000
        assert row["result"]["leader_reaped"] and row["result"]["group_disposed"]
        assert row["result"]["all_owned_children_terminal"] is False
    assert report["general_validator_qualification"] is False and report["hook_installed"] is False


@pytest.mark.parametrize(("failure", "reason"), [("nonzero", "nonzero-exit"), ("warning", "output-policy-refused")])
def test_native_recipe_joined_failure_runs_always_without_erasing_failure(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, serial_program: dict[str, Any], failure: str, reason: str
) -> None:
    inputs = execution_inputs(candidate_binary, executor_binary, repository, tmp_path, serial_program, recipe_case=failure)
    before = snapshot(repository)
    result, report = run_execution(executor_binary, inputs)
    assert snapshot(repository) == before
    assert report, result.stderr
    assert result.returncode != 0 and report["accepted"] is False and report["qualified_scope_joined"] is True
    producer, consumer = report["results"]
    assert producer["reason"] == reason and consumer["status"] == "blocked"
    assert [row["status"] for row in producer["steps"]] == ["passed", "refused", "blocked", "passed"]
    assert (tmp_path / "recipe-cleanup-marker").read_bytes() == b"producer\n"
    assert not (tmp_path / "recipe-skipped-marker").exists()
    if failure == "nonzero":
        assert producer["steps"][1]["result"]["exit_code"] == 13


@pytest.mark.parametrize(("case", "reason"), [("quota", "stdout_limit"), ("deadline", "wall_timeout")])
def test_native_recipe_never_resets_work_or_output_budget_for_next_argv_or_always(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, serial_program: dict[str, Any], case: str, reason: str
) -> None:
    inputs = execution_inputs(candidate_binary, executor_binary, repository, tmp_path, serial_program, recipe_case=case)
    before = snapshot(repository)
    result, report = run_execution(executor_binary, inputs)
    assert snapshot(repository) == before
    assert report, result.stderr
    assert result.returncode != 0 and report["accepted"] is False
    producer, consumer = report["results"]
    assert [row["status"] for row in producer["steps"]] == ["passed", "refused", "blocked"]
    assert producer["reason"] == reason and consumer["status"] == "blocked"
    assert not (tmp_path / "recipe-cleanup-marker").exists(), "cleanup_ms must never become executable always time"
    if case == "quota":
        raw = b"".join(Path(row["stdout_log"]["path"]).read_bytes() for row in producer["steps"] if row["stdout_log"])
        assert len(raw) == 30000 and producer["result"]["stdout_retained_bytes"] == len(raw)
    else:
        assert producer["steps"][0]["result"]["elapsed_ms"] < 700
        assert producer["steps"][1]["result"]["failure"] == "wall_timeout"


def test_native_execution_observes_dependency_order_staged_imports_and_exact_raw_logs(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, serial_program: dict[str, Any]
) -> None:
    inputs = execution_inputs(candidate_binary, executor_binary, repository, tmp_path, serial_program)
    before = snapshot(repository)
    result, report = run_execution(executor_binary, inputs)
    assert snapshot(repository) == before
    assert result.returncode == 0, result.stderr
    assert report["accepted"] is True and report["qualified_scope_joined"] is True
    assert report["selected_checks"] == ["z-producer", "a-consumer"]
    assert [row["status"] for row in report["results"]] == ["passed", "passed"]
    assert inputs["marker"].read_bytes() == b"consumer\n"
    for row in report["results"]:
        raw = Path(row["stdout_log"]["path"]).read_bytes()
        assert raw == b"STAGED\n" + b"O" * 20000
        assert digest(raw) == row["stdout_log"]["sha256"]
        assert len(row["result"]["stdout"]) == 8192
        assert row["result"]["stdout_retained_bytes"] == len(raw)
        assert Path(row["stderr_log"]["path"]).read_bytes() == b"E" * 9000
        assert row["result"]["all_owned_children_terminal"] is False
    assert report["general_validator_qualification"] is False and report["hook_installed"] is False


@pytest.mark.parametrize("failure", ["nonzero", "spawn"])
def test_native_required_producer_failure_blocks_consumer(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, serial_program: dict[str, Any], failure: str
) -> None:
    inputs = execution_inputs(
        candidate_binary,
        executor_binary,
        repository,
        tmp_path,
        serial_program,
        invalid_image=failure == "spawn",
        staged=b"FAIL\n" if failure == "nonzero" else b"PASS\n",
    )
    before = snapshot(repository)
    result, report = run_execution(executor_binary, inputs)
    assert snapshot(repository) == before
    assert result.returncode != 0, result.stdout
    assert report["accepted"] is False
    assert [row["status"] for row in report["results"]] == ["refused", "blocked"]
    assert not inputs["marker"].exists()
    if failure == "nonzero":
        assert report["results"][0]["result"]["exit_code"] == 7
        assert report["qualified_scope_joined"] is True
    else:
        assert report["results"][0]["reason"] and report["qualified_scope_joined"] is False


@pytest.mark.parametrize("drift", ["candidate", "tool", "dependency"])
def test_native_final_recheck_refuses_actual_input_drift_after_successful_producer(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, serial_program: dict[str, Any], drift: str
) -> None:
    inputs = execution_inputs(candidate_binary, executor_binary, repository, tmp_path, serial_program, waiting=True)
    before = snapshot(repository)
    stdout = tmp_path / "invocation.stdout.log"
    stderr = tmp_path / "invocation.stderr.log"
    with stdout.open("wb") as out, stderr.open("wb") as err:
        child = subprocess.Popen([str(executor_binary), "execute", str(inputs["request_path"])], env=inputs["environment"], stdout=out, stderr=err)
        try:
            deadline = time.monotonic() + 10
            while not inputs["marker"].exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            assert inputs["marker"].read_bytes() == b"producer\n", stderr.read_bytes()
            if drift == "candidate":
                root = Path(json.loads(inputs["manifest_path"].read_bytes())["root"])
                (root / "app.py").write_bytes(b"DRIFT\n")
            elif drift == "tool":
                # Change the actual private command tool's executable mode after
                # its native producer has started; never alter a shared compiler.
                bind_request = json.loads(inputs["bind_request"].read_bytes())
                tool = next(row for row in bind_request["files"] if row["role"] == "toolchain")
                Path(tool["path"]).chmod(0o600)
            else:
                inputs["observed"].write_bytes(b"DRIFT\n")
            inputs["release"].write_bytes(b"release\n")
            assert child.wait(timeout=20) != 0
        finally:
            inputs["release"].write_bytes(b"release\n")
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
    assert snapshot(repository) == before
    report = json.loads((inputs["logs"] / "run.json").read_bytes())
    assert report["accepted"] is False and report["refusal"] == "InputDrift"
    assert report["results"][0]["status"] == "passed"
    assert inputs["marker"].read_bytes() == b"producer\n"


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("mode", "UnsupportedChangedPathBinding"),
        ("missing-selected", "IncompleteSelection"),
        ("argv", "CommandBindingMismatch"),
        ("environment", "EnvironmentBindingMismatch"),
        ("budget", "BudgetBindingMismatch"),
        ("oversized-budget", "UnsupportedBudget"),
        ("producer", "UnqualifiedProducer"),
        ("incomplete-source", "IncompleteProducerClosure"),
        ("no-qualification", "UnqualifiedClosure"),
        ("multiple-commands", "UnsupportedCheckLifecycle"),
        ("platform", "UnavailableRequiredCheck"),
        ("recipe-always", "UnsupportedRecipeBinding"),
        ("recipe-producer-roster", "UnsupportedRecipeBinding"),
        ("specification", "UnknownField"),
        ("public-diagnostics", "PrivateEvidenceRequired"),
        ("candidate-diagnostics", "PrivateEvidenceRequired"),
    ],
)
def test_native_execution_refuses_unbound_context_before_any_child_effect(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, serial_program: dict[str, Any], fault: str, reason: str
) -> None:
    inputs = execution_inputs(candidate_binary, executor_binary, repository, tmp_path, serial_program, fault=fault)
    before = snapshot(repository)
    result, report = run_execution(executor_binary, inputs)
    assert snapshot(repository) == before
    assert result.returncode != 0 and reason.encode() in result.stderr, result.stderr
    assert not report and not inputs["marker"].exists()
    assert not list(inputs["logs"].iterdir())


def test_native_execution_quota_refuses_and_keeps_the_actual_raw_prefix(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, serial_program: dict[str, Any]
) -> None:
    inputs = execution_inputs(candidate_binary, executor_binary, repository, tmp_path, serial_program, fault="stdout-quota")
    before = snapshot(repository)
    result, report = run_execution(executor_binary, inputs)
    assert snapshot(repository) == before
    assert result.returncode != 0 and report["accepted"] is False
    assert [row["status"] for row in report["results"]] == ["refused", "blocked"]
    producer = report["results"][0]
    assert producer["reason"] == "stdout_limit" and producer["result"]["leader_reaped"] and producer["result"]["group_disposed"]
    assert Path(producer["stdout_log"]["path"]).read_bytes() == b"STAGED\n" + b"O" * (4096 - 7)
    assert producer["result"]["stdout_observed_bytes"] > producer["result"]["stdout_retained_bytes"] == 4096
    assert report["qualified_scope_joined"] is True


@pytest.mark.parametrize("fault", ["omitted-command", "command-alias"])
def test_native_execution_cannot_qualify_an_omitted_actual_command_image(
    candidate_binary: Path, executor_binary: Path, repository: Path, tmp_path: Path, serial_program: dict[str, Any], fault: str
) -> None:
    inputs = execution_inputs(candidate_binary, executor_binary, repository, tmp_path, serial_program, fault=fault)
    before = snapshot(repository)
    result, report = run_execution(executor_binary, inputs)
    assert snapshot(repository) == before
    assert result.returncode != 0, report
    assert b"UnboundExecutable" in result.stderr and not inputs["marker"].exists()
