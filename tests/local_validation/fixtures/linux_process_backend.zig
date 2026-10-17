//! Actual isolated Linux process-group and sampler-worker integration probe.
//! This test-only executable is cross-built for the existing pinned Linux image.
const std = @import("std");
const process = @import("process");
const c = @cImport({
    @cInclude("sys/socket.h");
    @cInclude("sys/types.h");
    @cInclude("unistd.h");
    @cInclude("fcntl.h");
    @cInclude("poll.h");
});

fn now(io: std.Io) i96 {
    return std.Io.Clock.boot.now(io).nanoseconds;
}

fn processState(pid: i32) !?u8 {
    var path_buffer: [32]u8 = undefined;
    const path = try std.fmt.bufPrintZ(&path_buffer, "/proc/{d}/stat", .{pid});
    const fd = c.open(path.ptr, c.O_RDONLY | c.O_CLOEXEC);
    if (fd < 0) {
        if (std.c.errno(@as(c_int, -1)) == .NOENT) return null;
        return error.ProcessInspectionFailed;
    }
    defer _ = c.close(fd);
    var bytes: [4096]u8 = undefined;
    const count = c.read(fd, @ptrCast(bytes[0..].ptr), bytes.len);
    if (count <= 0 or count >= bytes.len) return error.ProcessInspectionFailed;
    const row = bytes[0..@intCast(count)];
    const close = std.mem.lastIndexOfScalar(u8, row, ')') orelse return error.ProcessInspectionFailed;
    if (close + 2 >= row.len or row[close + 1] != ' ') return error.ProcessInspectionFailed;
    return row[close + 2];
}

fn refusesRun(init: std.process.Init, options: process.Options, expected: anyerror) !bool {
    const result = process.run(init.arena.allocator(), init.io, options) catch |failure| return failure == expected;
    defer result.deinit(init.arena.allocator());
    return false;
}

fn refusesWorker(
    init: std.process.Init,
    argv: []const []const u8,
    environment: *const std.process.Environ.Map,
    socket_fd: c_int,
    expected: anyerror,
) !bool {
    var child = process.spawnSamplerWorkerLinux(init.arena.allocator(), init.io, argv, "/", environment, socket_fd, now(init.io) + 3000 * std.time.ns_per_ms, 1000) catch |failure| return failure == expected;
    defer _ = child.wait(init.io) catch {};
    return false;
}

fn writeJson(init: std.process.Init, path: []const u8, value: anytype) !void {
    const bytes = try std.json.Stringify.valueAlloc(init.arena.allocator(), value, .{});
    var file = try std.Io.Dir.cwd().createFile(init.io, path, .{ .exclusive = true, .permissions = .fromMode(0o600) });
    defer file.close(init.io);
    try file.writeStreamingAll(init.io, bytes);
    try file.writeStreamingAll(init.io, "\n");
}

fn exercise(init: std.process.Init) !void {
    var environment = std.process.Environ.Map.init(init.arena.allocator());
    try environment.put("WORKER_TEST", "yes");
    const result = try process.run(init.arena.allocator(), init.io, .{
        .argv = &.{ "/bin/sh", "-c", "sleep 5 & printf '%s' $! > /output/fixture/group-child.pid; printf linux-process-backend" },
        .cwd = .{ .path = "/" },
        .limits = .{ .wall_ms = 5000, .cleanup_ms = 1000, .stdout_bytes = 128, .stderr_bytes = 128, .processes = 8, .resident_bytes = 536870912 },
    });
    defer result.deinit(init.arena.allocator());
    const child_pid_bytes = try std.Io.Dir.cwd().readFileAlloc(init.io, "/output/fixture/group-child.pid", init.arena.allocator(), .limited(32));
    const group_child_pid = try std.fmt.parseInt(i32, child_pid_bytes, 10);
    const group_child_state = try processState(group_child_pid);
    const group_child_terminal = group_child_state == null or group_child_state.? == 'Z' or group_child_state.? == 'X' or group_child_state.? == 'x';
    if (result.failure != null or result.exit_code != 0 or !result.leader_reaped or !result.group_disposed or result.all_owned_children_terminal or !group_child_terminal or !std.mem.eql(u8, result.stdout, "linux-process-backend")) return error.LinuxProcessGroupControlFailed;
    const absent_process = try processState(-1);
    if (absent_process != null) return error.LinuxProcessGroupControlFailed;

    const denied_path = "/output/fixture/denied-image";
    const denied_image = try std.Io.Dir.cwd().createFile(init.io, denied_path, .{ .exclusive = true, .permissions = .fromMode(0o600) });
    defer denied_image.close(init.io);
    try denied_image.writeStreamingAll(init.io, "not an executable image\n");
    var invalid_environment = std.process.Environ.Map.init(init.arena.allocator());
    try invalid_environment.put("BAD", "bad\x00value");
    const invalid_argument_refused = try refusesRun(init, .{ .argv = &.{ "/bin/true", "bad\x00argument" } }, error.InvalidArguments);
    const invalid_cwd_refused = try refusesRun(init, .{ .argv = &.{"/bin/true"}, .cwd = .{ .path = "/\x00" } }, error.InvalidArguments);
    const invalid_environment_refused = try refusesRun(init, .{ .argv = &.{"/bin/true"}, .environment = &invalid_environment }, error.InvalidEnvironment);
    const missing_image_refused = try refusesRun(init, .{ .argv = &.{"/output/fixture/absent-image"} }, error.FileNotFound);
    const denied_image_refused = try refusesRun(init, .{ .argv = &.{denied_path} }, error.AccessDenied);

    var pair: [2]c_int = undefined;
    if (c.socketpair(c.AF_UNIX, c.SOCK_STREAM | c.SOCK_CLOEXEC, 0, &pair) != 0) return error.WorkerSocketFailed;
    var parent_open = true;
    var child_open = true;
    defer {
        if (parent_open) _ = c.close(pair[0]);
        if (child_open) _ = c.close(pair[1]);
    }
    const worker_invalid_argument_refused = try refusesWorker(init, &.{ "/bin/true", "bad\x00argument" }, &environment, pair[1], error.InvalidArguments);
    const worker_invalid_environment_refused = try refusesWorker(init, &.{"/bin/true"}, &invalid_environment, pair[1], error.InvalidEnvironment);
    const worker_missing_image_refused = try refusesWorker(init, &.{"/output/fixture/absent-worker"}, &environment, pair[1], error.FileNotFound);
    const worker_denied_image_refused = try refusesWorker(init, &.{denied_path}, &environment, pair[1], error.AccessDenied);
    const spawned = try process.spawnSamplerWorkerLinux(
        init.arena.allocator(),
        init.io,
        &.{ "/bin/sh", "-c", "set -e; test \"$WORKER_TEST\" = yes; printf worker-backend" },
        "/",
        &environment,
        pair[1],
        now(init.io) + 3000 * std.time.ns_per_ms,
        1000,
    );
    const worker_pid: i32 = @intCast(spawned.id.?);
    _ = c.close(pair[1]);
    child_open = false;
    const flags = c.fcntl(pair[0], c.F_GETFL);
    if (flags < 0 or c.fcntl(pair[0], c.F_SETFL, flags | c.O_NONBLOCK) != 0) return error.WorkerSocketFailed;
    var worker_output: [128]u8 = undefined;
    var worker_length: usize = 0;
    const worker_deadline = now(init.io) + 3000 * std.time.ns_per_ms;
    var worker_eof = false;
    while (!worker_eof and now(init.io) < worker_deadline) {
        var descriptor: c.struct_pollfd = .{ .fd = pair[0], .events = c.POLLIN, .revents = 0 };
        _ = c.poll(&descriptor, 1, 5);
        const count = c.recv(pair[0], @ptrCast(worker_output[worker_length..].ptr), worker_output.len - worker_length, 0);
        if (count == 0) {
            worker_eof = true;
        } else if (count < 0) {
            const problem = std.c.errno(@as(c_int, -1));
            if (problem != .AGAIN and problem != .INTR) return error.WorkerSocketFailed;
        } else {
            worker_length += @intCast(count);
            if (worker_length == worker_output.len) return error.WorkerOutputLimit;
        }
    }
    _ = c.close(pair[0]);
    parent_open = false;
    var identity = try process.DirectChild.init(worker_pid);
    defer if (identity.valid()) {
        identity.signal(true) catch {};
        var attempts: usize = 0;
        while (identity.valid() and attempts < 1000) : (attempts += 1) {
            if (identity.observe() catch false) {
                _ = identity.reap() catch false;
                break;
            }
            _ = c.poll(null, 0, 1);
        }
    };
    if (!worker_eof or !try identity.observe() or !try identity.reap() or identity.exitCode() != 0 or !std.mem.eql(u8, worker_output[0..worker_length], "worker-backend")) return error.LinuxWorkerControlFailed;

    var termination_pair: [2]c_int = undefined;
    if (c.socketpair(c.AF_UNIX, c.SOCK_STREAM | c.SOCK_CLOEXEC, 0, &termination_pair) != 0) return error.WorkerSocketFailed;
    defer {
        _ = c.close(termination_pair[0]);
        _ = c.close(termination_pair[1]);
    }
    const termination_child = try process.spawnSamplerWorkerLinux(
        init.arena.allocator(),
        init.io,
        &.{ "/bin/sleep", "5" },
        "/",
        &environment,
        termination_pair[1],
        now(init.io) + 3000 * std.time.ns_per_ms,
        1000,
    );
    var terminated = try process.DirectChild.init(@intCast(termination_child.id.?));
    defer if (terminated.valid()) {
        terminated.signal(true) catch {};
        var attempts: usize = 0;
        while (terminated.valid() and attempts < 1000) : (attempts += 1) {
            if (terminated.observe() catch false) {
                _ = terminated.reap() catch false;
                break;
            }
            _ = c.poll(null, 0, 1);
        }
    };
    const terminated_usage = try terminated.usage();
    try terminated.signal(true);
    var termination_reaped = false;
    var termination_attempts: usize = 0;
    while (!termination_reaped and termination_attempts < 1000) : (termination_attempts += 1) {
        termination_reaped = try terminated.reap();
        if (!termination_reaped) _ = c.poll(null, 0, 1);
    }
    if (!termination_reaped or !terminated.reaped() or terminated_usage.processes != 1) return error.LinuxWorkerControlFailed;

    try writeJson(init, "/output/fixture/process-backend.json", .{
        .executor_pid = c.getpid(),
        .group_child_pid = group_child_pid,
        .group_child_state = group_child_state,
        .group_child_terminal = group_child_terminal,
        .group_failure = if (result.failure) |failure| @tagName(failure) else "none",
        .group_exit_code = result.exit_code,
        .group_leader_reaped = result.leader_reaped,
        .group_disposed = result.group_disposed,
        .all_owned_children_terminal = result.all_owned_children_terminal,
        .group_stdout = result.stdout,
        .worker_pid = worker_pid,
        .worker_exit_code = identity.exitCode(),
        .worker_reaped = identity.reaped(),
        .worker_output = worker_output[0..worker_length],
        .invalid_argument_refused = invalid_argument_refused,
        .invalid_cwd_refused = invalid_cwd_refused,
        .invalid_environment_refused = invalid_environment_refused,
        .missing_image_refused = missing_image_refused,
        .denied_image_refused = denied_image_refused,
        .worker_invalid_argument_refused = worker_invalid_argument_refused,
        .worker_invalid_environment_refused = worker_invalid_environment_refused,
        .worker_missing_image_refused = worker_missing_image_refused,
        .worker_denied_image_refused = worker_denied_image_refused,
        .worker_signal_reaped = terminated.reaped(),
        .worker_usage_processes = terminated_usage.processes,
    });
}

pub fn main(init: std.process.Init) void {
    exercise(init) catch |failure| std.process.fatal("Linux process backend refused: {s}", .{@errorName(failure)});
    std.Io.File.stdout().writeStreamingAll(init.io, "linux-native-process-backend-pass\n") catch |failure| std.process.fatal("Linux process backend report failed: {s}", .{@errorName(failure)});
}
