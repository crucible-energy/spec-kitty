//! Bounded Darwin child-group ownership. Never signals a reaped/reused leader.
//! Memory-safety contract: the synchronous owner retains child, pipes and
//! callback contexts until terminal disposition; no borrowed pointer escapes.
//! Capture reserves bounded buffers before spawn and checks lengths before copy.
//! Returned captures belong to the caller; Result.deinit releases exactly once.
//! Leader identity is retained before every signal and invalidated before return.
//! Allocation/read/cancel failures still take one bounded cleanup allowance.
const std = @import("std");
const builtin = @import("builtin");
const c = if (builtin.os.tag == .macos) @cImport({
    @cInclude("sys/wait.h");
    @cInclude("sys/proc_info.h");
    @cInclude("unistd.h");
    @cInclude("fcntl.h");
    @cInclude("poll.h");
    @cInclude("signal.h");
}) else struct {};
// SDK types/constants above; libproc.h itself brings Mach packed-descriptor
// static assertions that Zig 0.16 cannot translate. These public ABI declarations
// use the SDK-owned struct layouts, never a locally guessed layout.
extern "c" fn proc_listpids(u32, u32, ?*anyopaque, c_int) c_int;
extern "c" fn proc_pidinfo(c_int, c_int, u64, ?*anyopaque, c_int) c_int;

pub const Limits = struct {
    wall_ms: u32 = 1000,
    cleanup_ms: u32 = 1000,
    stdout_bytes: usize = 1024,
    stderr_bytes: usize = 1024,
    processes: u16 = 8,
    resident_bytes: u64 = 512 * 1024 * 1024,
};
pub const Failure = enum { wall_timeout, stdout_limit, stderr_limit, process_limit, resident_limit, cancelled, external_budget, inspection_failed, ownership_lost, cleanup_failed };
pub const Options = struct {
    argv: []const []const u8,
    cwd: std.process.Child.Cwd = .inherit,
    environment: ?*const std.process.Environ.Map = null,
    limits: Limits = .{},
    cancel_probe: ?*const fn (?*anyopaque) bool = null,
    cancel_context: ?*anyopaque = null,
    budget_probe: ?*const fn (?*anyopaque) bool = null,
    budget_context: ?*anyopaque = null,
    absolute_deadline_ns: ?i96 = null,
};
pub const Result = struct {
    stdout: []u8,
    stderr: []u8,
    failure: ?Failure,
    exit_code: ?u8,
    leader_reaped: bool,
    group_disposed: bool,
    elapsed_ms: u64,
    max_sampled_processes: usize,
    max_sampled_resident_bytes: u64,
    pub fn deinit(self: Result, allocator: std.mem.Allocator) void {
        allocator.free(self.stdout);
        allocator.free(self.stderr);
    }
};

pub fn run(allocator: std.mem.Allocator, io: std.Io, options: Options) !Result {
    if (builtin.os.tag != .macos) return error.PlatformUnsupported;
    const limits = options.limits;
    if (options.argv.len == 0 or !std.fs.path.isAbsolute(options.argv[0]) or limits.wall_ms == 0 or limits.wall_ms > 3_600_000 or limits.cleanup_ms == 0 or limits.cleanup_ms > 5000 or limits.stdout_bytes > 16 * 1024 * 1024 or limits.stderr_bytes > 16 * 1024 * 1024 or limits.processes == 0 or limits.processes > 32 or limits.resident_bytes == 0) return error.InvalidProcessBudget;
    const started = now(io);
    var signals = try SignalBridge.install();
    var result = runOwned(allocator, io, options, started) catch |failure| {
        _ = try signals.restore();
        return failure;
    };
    errdefer result.deinit(allocator);
    const received_signal = try signals.restore();
    if (received_signal != 0 and result.failure == null) result.failure = .cancelled;
    return result;
}

// Process-wide handlers have a single synchronous owner. They perform only a
// native lock-free atomic store; allocation, inspection and signals stay here.
var signal_owner = std.atomic.Value(u32).init(0);
var pending_signal = std.atomic.Value(u32).init(0);
fn cancellationSignal(signal: c_int) callconv(.c) void {
    pending_signal.store(@intCast(signal), .monotonic);
}
const SignalBridge = struct {
    previous_int: c.struct_sigaction,
    previous_term: c.struct_sigaction,
    active: bool = true,

    fn install() !SignalBridge {
        if (signal_owner.cmpxchgStrong(0, 1, .acquire, .monotonic) != null) return error.SignalBridgeBusy;
        var release_owner = true;
        errdefer if (release_owner) signal_owner.store(0, .release);
        pending_signal.store(0, .monotonic);
        var action = std.mem.zeroes(c.struct_sigaction);
        action.__sigaction_u.__sa_handler = cancellationSignal;
        if (c.sigemptyset(&action.sa_mask) != 0 or c.sigaddset(&action.sa_mask, c.SIGINT) != 0 or c.sigaddset(&action.sa_mask, c.SIGTERM) != 0) return error.SignalInstallationFailed;
        var previous_int: c.struct_sigaction = undefined;
        var previous_term: c.struct_sigaction = undefined;
        if (c.sigaction(c.SIGINT, &action, &previous_int) != 0) return error.SignalInstallationFailed;
        if (c.sigaction(c.SIGTERM, &action, &previous_term) != 0) {
            if (c.sigaction(c.SIGINT, &previous_int, null) != 0) {
                release_owner = false; // Poison ownership if a handler remains.
                return error.SignalRestorationFailed;
            }
            return error.SignalInstallationFailed;
        }
        return .{ .previous_int = previous_int, .previous_term = previous_term };
    }
    fn restore(self: *SignalBridge) !u32 {
        if (!self.active) return 0;
        self.active = false;
        // Both restoration attempts are made, even if the first one refuses.
        const int_rc = c.sigaction(c.SIGINT, &self.previous_int, null);
        const term_rc = c.sigaction(c.SIGTERM, &self.previous_term, null);
        if (int_rc != 0 or term_rc != 0) return error.SignalRestorationFailed;
        const received = pending_signal.load(.monotonic);
        signal_owner.store(0, .release);
        return received;
    }
};

fn runOwned(allocator: std.mem.Allocator, io: std.Io, options: Options, started: i96) !Result {
    const limits = options.limits;
    const deadline = @min(started + @as(i96, limits.wall_ms) * std.time.ns_per_ms, options.absolute_deadline_ns orelse std.math.maxInt(i96));
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
    var out: std.ArrayList(u8) = .empty;
    defer out.deinit(allocator);
    var err: std.ArrayList(u8) = .empty;
    defer err.deinit(allocator);
    // Reserve capture before the first child effect; bounded reads never allocate.
    try out.ensureTotalCapacity(allocator, limits.stdout_bytes);
    try err.ensureTotalCapacity(allocator, limits.stderr_bytes);
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
    if (pending_signal.load(.monotonic) != 0) return error.OperationCancelled;
    var child = try std.process.spawn(io, .{ .argv = options.argv, .cwd = options.cwd, .environ_map = options.environment, .pgid = 0, .stdin = .ignore, .stdout = .pipe, .stderr = .pipe });
    var owner = Ownership{ .pid = child.id.? };
    defer {
        if (owner.valid and !owner.reaped) _ = owner.dispose(io, limits.cleanup_ms);
        if (child.stdout) |file| file.close(io);
        if (child.stderr) |file| file.close(io);
        child.id = null;
    }
    for ([_]?std.Io.File{ child.stdout, child.stderr }) |file| {
        if (c.fcntl(file.?.handle, c.F_SETFL, @as(c_int, c.O_NONBLOCK)) != 0) return error.PipeConfigurationFailed;
    }
    var failure: ?Failure = null;
    var out_open = true;
    var err_open = true;
    var max_processes: usize = 0;
    var max_resident: u64 = 0;
    while (true) {
        if (pending_signal.load(.monotonic) != 0) {
            failure = .cancelled;
            break;
        }
        io.checkCancel() catch {
            failure = .cancelled;
            break;
        };
        if (options.cancel_probe) |probe| if (probe(options.cancel_context)) {
            failure = .cancelled;
            break;
        };
        if (options.budget_probe) |probe| if (probe(options.budget_context)) {
            failure = .external_budget;
            break;
        };
        if (now(io) >= deadline) {
            failure = .wall_timeout;
            break;
        }
        if (!owner.reaped) {
            const terminal = owner.observe() catch {
                failure = if (owner.valid) .inspection_failed else .ownership_lost;
                break;
            };
            const usage = groupUsage(owner.pid, terminal) catch {
                failure = .inspection_failed;
                break;
            };
            max_processes = @max(max_processes, usage.processes);
            max_resident = @max(max_resident, usage.resident_bytes);
            if (usage.processes > limits.processes) {
                failure = .process_limit;
                break;
            }
            if (usage.resident_bytes > limits.resident_bytes) {
                failure = .resident_limit;
                break;
            }
            // A terminal leader remains WNOWAIT-owned while its entire original
            // group is disposed. Pipe EOF is never used as process completion.
            if (terminal) {
                if (!owner.dispose(io, limits.cleanup_ms)) failure = if (!owner.valid and !owner.reaped) .ownership_lost else .cleanup_failed;
            }
        }
        if (out_open) capture(child.stdout.?.handle, &out, limits.stdout_bytes, &out_open) catch |e| {
            failure = if (e == error.OutputLimit) .stdout_limit else .inspection_failed;
            break;
        };
        if (err_open) capture(child.stderr.?.handle, &err, limits.stderr_bytes, &err_open) catch |e| {
            failure = if (e == error.OutputLimit) .stderr_limit else .inspection_failed;
            break;
        };
        if (failure != null or (owner.reaped and !out_open and !err_open)) break;
        var fds = [_]c.struct_pollfd{ .{ .fd = if (out_open) child.stdout.?.handle else -1, .events = c.POLLIN, .revents = 0 }, .{ .fd = if (err_open) child.stderr.?.handle else -1, .events = c.POLLIN, .revents = 0 } };
        const remaining_ms: c_int = @intCast(@min(5, @max(0, @divTrunc(deadline - now(io), std.time.ns_per_ms))));
        if (c.poll(&fds, fds.len, remaining_ms) < 0 and std.c.errno(@as(c_int, -1)) != .INTR) {
            failure = .inspection_failed;
            break;
        }
    }
    if (!owner.reaped and owner.valid and !owner.dispose(io, limits.cleanup_ms)) failure = if (!owner.valid and !owner.reaped) .ownership_lost else .cleanup_failed;
    const stdout = try allocator.dupe(u8, out.items);
    errdefer allocator.free(stdout);
    return .{ .stdout = stdout, .stderr = try allocator.dupe(u8, err.items), .failure = failure, .exit_code = owner.exit_code, .leader_reaped = owner.reaped, .group_disposed = owner.disposed, .elapsed_ms = @intCast(@divTrunc(now(io) - started, std.time.ns_per_ms)), .max_sampled_processes = max_processes, .max_sampled_resident_bytes = max_resident };
}

const Ownership = struct {
    pid: i32,
    valid: bool = true,
    reaped: bool = false,
    disposed: bool = false,
    cleanup_attempted: bool = false,
    exit_code: ?u8 = null,

    fn observe(self: *Ownership) !bool {
        if (!self.valid) return error.OwnershipLost;
        if (self.reaped) return true;
        var info: c.siginfo_t = std.mem.zeroes(c.siginfo_t);
        const rc = c.waitid(c.P_PID, @intCast(self.pid), &info, c.WEXITED | c.WNOHANG | c.WNOWAIT);
        if (rc != 0) {
            if (std.c.errno(rc) == .CHILD) self.valid = false;
            if (std.c.errno(rc) == .INTR) return false;
            return error.ExitObservationFailed;
        }
        if (info.si_pid == 0) return false;
        if (info.si_pid != self.pid) {
            self.valid = false;
            return error.OwnershipLost;
        }
        // Darwin can report a stopped child even with WEXITED. Its matching
        // identity is still owned, but skipping it as a terminal leader would
        // falsely empty the group and attempt a premature nonblocking reap.
        if (!try terminalEvent(info.si_code)) return false;
        if (info.si_code == c.CLD_EXITED) self.exit_code = @intCast(info.si_status);
        return true;
    }

    fn dispose(self: *Ownership, io: std.Io, cleanup_ms: u32) bool {
        if (!self.valid) return false;
        if (self.reaped) return self.disposed;
        if (self.cleanup_attempted) return false;
        self.cleanup_attempted = true;
        const deadline = now(io) + @as(i96, cleanup_ms) * std.time.ns_per_ms;
        while (now(io) < deadline) {
            // Check ownership immediately before every group signal. The leader
            // is intentionally not reaped, reserving its PID/PGID against reuse.
            const terminal = self.observe() catch break;
            if (!self.valid) break;
            const rc = c.kill(-self.pid, c.SIGKILL);
            const kill_errno = std.c.errno(rc);
            if (rc != 0 and kill_errno != .SRCH and kill_errno != .PERM) break;
            const usage = groupUsage(self.pid, terminal) catch {
                _ = c.poll(null, 0, 2);
                continue;
            };
            if (rc != 0 and kill_errno == .PERM and usage.processes != 0) break;
            if (terminal and usage.processes == 0) {
                var status: c_int = 0;
                const reaped_pid = c.waitpid(self.pid, &status, c.WNOHANG);
                if (reaped_pid != self.pid) {
                    if (reaped_pid < 0 and std.c.errno(reaped_pid) == .CHILD) self.valid = false;
                    break;
                }
                self.reaped = true;
                self.valid = false; // No signal operation after releasing identity.
                self.disposed = true;
                return true;
            }
            // Uncancelable bounded cleanup must finish even when caller canceled.
            _ = c.poll(null, 0, 2);
        }
        // A terminal owned leader can still be reaped after failed group proof.
        // No later signal is permitted and disposal remains false.
        if (self.observe() catch false) {
            var status: c_int = 0;
            const pid = c.waitpid(self.pid, &status, c.WNOHANG);
            if (pid == self.pid) {
                self.reaped = true;
                self.valid = false;
            } else if (pid < 0 and std.c.errno(pid) == .CHILD) self.valid = false;
        }
        return false;
    }
};

fn terminalEvent(code: c_int) !bool {
    return switch (code) {
        c.CLD_EXITED, c.CLD_KILLED, c.CLD_DUMPED => true,
        c.CLD_STOPPED, c.CLD_CONTINUED, c.CLD_TRAPPED => false,
        else => error.ExitObservationFailed,
    };
}

fn now(io: std.Io) i96 {
    return std.Io.Clock.boot.now(io).nanoseconds;
}
const Usage = struct { processes: usize = 0, resident_bytes: u64 = 0 };
const ListProcesses = *const fn (u32, u32, ?*anyopaque, c_int) callconv(.c) c_int;
fn groupUsage(pgid: i32, terminal_leader: bool) !Usage {
    return groupUsageUsing(pgid, terminal_leader, proc_listpids);
}
fn groupUsageUsing(pgid: i32, terminal_leader: bool, list: ListProcesses) !Usage {
    var pids: [65]c_int = @splat(0);
    std.c._errno().* = 0;
    const bytes = list(c.PROC_PGRP_ONLY, @intCast(pgid), &pids, @sizeOf(@TypeOf(pids)));
    if (bytes <= 0 or bytes >= @sizeOf(@TypeOf(pids)) or @rem(bytes, @sizeOf(c_int)) != 0) return error.GroupInspectionFailed;
    var usage: Usage = .{};
    var leader_present = false;
    for (pids[0..@intCast(@divTrunc(bytes, @sizeOf(c_int)))]) |pid| {
        if (pid == pgid) leader_present = true;
        if (pid <= 0 or (terminal_leader and pid == pgid)) continue;
        var bsd: c.struct_proc_bsdinfo = std.mem.zeroes(c.struct_proc_bsdinfo);
        std.c._errno().* = 0;
        if (proc_pidinfo(pid, c.PROC_PIDTBSDINFO, 0, &bsd, @sizeOf(c.struct_proc_bsdinfo)) != @sizeOf(c.struct_proc_bsdinfo)) {
            // Darwin's ESRCH omits exited/zombie tasks from proc_pidinfo.
            // Permission/unknown inspection errors refuse instead of silently
            // shrinking the live group. kill(pid,0) also sees zombies and cannot
            // substitute for this kernel task-status observation.
            if (std.c.errno(@as(c_int, -1)) != .SRCH) return error.GroupInspectionFailed;
            continue;
        }
        if (bsd.pbi_pgid != pgid) continue; // Process exited/changed before sample.
        var task: c.struct_proc_taskinfo = std.mem.zeroes(c.struct_proc_taskinfo);
        std.c._errno().* = 0;
        if (proc_pidinfo(pid, c.PROC_PIDTASKINFO, 0, &task, @sizeOf(c.struct_proc_taskinfo)) != @sizeOf(c.struct_proc_taskinfo)) {
            if (std.c.errno(@as(c_int, -1)) != .SRCH) return error.GroupInspectionFailed;
            continue;
        }
        usage.processes += 1;
        usage.resident_bytes = try std.math.add(u64, usage.resident_bytes, task.pti_resident_size);
    }
    if (!leader_present) return error.GroupInspectionFailed;
    return usage;
}

fn capture(fd: c_int, list: *std.ArrayList(u8), limit: usize, open: *bool) !void {
    var buffer: [8192]u8 = undefined;
    // One chunk per turn bounds deadline/cancellation starvation even when the
    // child continuously fills both pipes. Read one byte beyond remaining cap.
    const rc = c.read(fd, &buffer, @min(buffer.len, limit - list.items.len + 1));
    if (rc == 0) {
        open.* = false;
        return;
    }
    if (rc < 0) {
        const code = std.c.errno(rc);
        if (code == .AGAIN or code == .INTR) return;
        return error.CaptureFailed;
    }
    const size: usize = @intCast(rc);
    if (size > limit - list.items.len) return error.OutputLimit;
    list.appendSliceAssumeCapacity(buffer[0..size]);
}

fn fixture(script: []const u8, limits: Limits) !Result {
    return run(std.testing.allocator, std.testing.io, .{ .argv = &.{ "/bin/sh", "-c", script }, .limits = limits });
}

test "quiet success retains ownership through exactly one reap" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const result = try fixture("exit 0", .{});
    defer result.deinit(std.testing.allocator);
    try std.testing.expect(result.failure == null);
    try std.testing.expectEqual(@as(?u8, 0), result.exit_code);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
}

test "exact output cap succeeds and one-over cap refuses" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const exact = try fixture("printf 1234", .{ .stdout_bytes = 4 });
    defer exact.deinit(std.testing.allocator);
    try std.testing.expect(exact.failure == null);
    try std.testing.expectEqualStrings("1234", exact.stdout);
    const over = try fixture("printf 12345", .{ .stdout_bytes = 4 });
    defer over.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .stdout_limit), over.failure);
    try std.testing.expect(over.leader_reaped and over.group_disposed);
}

test "independent stderr cap refuses" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const result = try fixture("printf 12345 >&2", .{ .stderr_bytes = 4 });
    defer result.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .stderr_limit), result.failure);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
}

test "EOF does not disable deadline or reap" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const result = try fixture("exec 1>&- 2>&-; sleep 10", .{ .wall_ms = 50 });
    defer result.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .wall_timeout), result.failure);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
}

test "stopped owned child stays live until deadline cleanup" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const result = try fixture("printf '%s' $$; kill -STOP $$; exit 7", .{ .wall_ms = 100, .cleanup_ms = 1000 });
    defer result.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .wall_timeout), result.failure);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
    const pid = try std.fmt.parseInt(i32, result.stdout, 10);
    try std.testing.expect(!liveProcess(pid));
}

test "stopped owned child can be cancelled and disposed" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    var calls: usize = 0;
    const result = try run(std.testing.allocator, std.testing.io, .{ .argv = &.{ "/bin/sh", "-c", "printf '%s' $$; kill -STOP $$; exit 7" }, .cancel_probe = cancelAfterTurns, .cancel_context = &calls });
    defer result.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .cancelled), result.failure);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
    const pid = try std.fmt.parseInt(i32, result.stdout, 10);
    try std.testing.expect(!liveProcess(pid));
}

test "only exited killed and dumped wait events are terminal" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    for ([_]c_int{ c.CLD_EXITED, c.CLD_KILLED, c.CLD_DUMPED }) |code| try std.testing.expect(try terminalEvent(code));
    for ([_]c_int{ c.CLD_STOPPED, c.CLD_CONTINUED, c.CLD_TRAPPED }) |code| try std.testing.expect(!try terminalEvent(code));
    try std.testing.expectError(error.ExitObservationFailed, terminalEvent(-1));
    try std.testing.expectError(error.ExitObservationFailed, terminalEvent(0));
}

test "continuous output cannot starve elapsed deadline" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const result = try fixture("while :; do printf x; printf y >&2; done", .{ .wall_ms = 300, .stdout_bytes = 1024 * 1024, .stderr_bytes = 1024 * 1024 });
    defer result.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .wall_timeout), result.failure);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
    try std.testing.expect(result.stdout.len > 0 and result.stderr.len > 0);
}

test "leader exit cannot strand a descendant with closed pipes" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const result = try fixture("(exec 1>&- 2>&-; sleep 10) & printf '%s' $!; exit 0", .{});
    defer result.deinit(std.testing.allocator);
    try std.testing.expect(result.failure == null);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
    const pid = try std.fmt.parseInt(i32, result.stdout, 10);
    try std.testing.expect(!liveProcess(pid));
}

test "cancellation remains active after EOF" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    var calls: usize = 0;
    const result = try run(std.testing.allocator, std.testing.io, .{ .argv = &.{ "/bin/sh", "-c", "exec 1>&- 2>&-; sleep 10" }, .cancel_probe = cancelAfterTurns, .cancel_context = &calls });
    defer result.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .cancelled), result.failure);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
}

test "spawn failure never acquires a signal target" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    try std.testing.expectError(error.FileNotFound, run(std.testing.allocator, std.testing.io, .{ .argv = &.{"/threebody/nonexistent/program"} }));
}

fn cancelAfterTurns(context: ?*anyopaque) bool {
    const calls: *usize = @ptrCast(@alignCast(context.?));
    calls.* += 1;
    return calls.* >= 5;
}

test "quiet live process is bounded even without output" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const result = try fixture("sleep 10", .{ .wall_ms = 30 });
    defer result.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .wall_timeout), result.failure);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
}

test "process fanout and sampled resident budgets refuse" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const fanout = try fixture("sleep 10 & sleep 10 & wait", .{ .processes = 1 });
    defer fanout.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .process_limit), fanout.failure);
    try std.testing.expect(fanout.leader_reaped and fanout.group_disposed);
    const memory = try fixture("sleep 10", .{ .resident_bytes = 1 });
    defer memory.deinit(std.testing.allocator);
    try std.testing.expectEqual(@as(?Failure, .resident_limit), memory.failure);
    try std.testing.expect(memory.leader_reaped and memory.group_disposed);
}

test "leader exit with inherited open pipes still disposes descendants" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const result = try fixture("sleep 10 & printf '%s' $!; exit 0", .{});
    defer result.deinit(std.testing.allocator);
    try std.testing.expect(result.failure == null);
    try std.testing.expect(result.leader_reaped and result.group_disposed);
    try std.testing.expect(!liveProcess(try std.fmt.parseInt(i32, result.stdout, 10)));
}

test "external reap invalidates ownership before any group signal" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    const pid = c.fork();
    try std.testing.expect(pid >= 0);
    if (pid == 0) c._exit(0);
    var status: c_int = 0;
    try std.testing.expectEqual(pid, c.waitpid(pid, &status, 0));
    var owner = Ownership{ .pid = pid };
    try std.testing.expectError(error.ExitObservationFailed, owner.observe());
    try std.testing.expect(!owner.valid);
    try std.testing.expect(!owner.dispose(std.testing.io, 10));
    try std.testing.expect(!owner.reaped and !owner.disposed);
}

test "zero or excessive budgets refuse before spawn" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    try std.testing.expectError(error.InvalidProcessBudget, fixture("exit 0", .{ .wall_ms = 0 }));
    try std.testing.expectError(error.InvalidProcessBudget, fixture("exit 0", .{ .processes = 33 }));
    try std.testing.expectError(error.InvalidProcessBudget, fixture("exit 0", .{ .stdout_bytes = 17 * 1024 * 1024 }));
}
fn liveProcess(pid: i32) bool {
    var bsd: c.struct_proc_bsdinfo = std.mem.zeroes(c.struct_proc_bsdinfo);
    return proc_pidinfo(pid, c.PROC_PIDTBSDINFO, 0, &bsd, @sizeOf(c.struct_proc_bsdinfo)) == @sizeOf(c.struct_proc_bsdinfo);
}

test "failed zero-byte libproc enumeration cannot prove group disposal" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    try std.testing.expectError(error.GroupInspectionFailed, groupUsageUsing(123, true, failedList));
}
fn failedList(_: u32, _: u32, _: ?*anyopaque, _: c_int) callconv(.c) c_int {
    std.c._errno().* = @intFromEnum(std.c.E.ACCES);
    return 0;
}

test "ambiguous enumeration and omitted retained leader refuse" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    std.c._errno().* = @intFromEnum(std.c.E.SRCH);
    try std.testing.expectError(error.GroupInspectionFailed, groupUsageUsing(123, true, ambiguousList));
    try std.testing.expectEqual(@as(c_int, 0), std.c._errno().*);
    try std.testing.expectError(error.GroupInspectionFailed, groupUsageUsing(123, true, missingLeaderList));
}
fn ambiguousList(_: u32, _: u32, _: ?*anyopaque, _: c_int) callconv(.c) c_int {
    return 0;
}
fn missingLeaderList(_: u32, _: u32, _: ?*anyopaque, _: c_int) callconv(.c) c_int {
    return @sizeOf(c_int);
}

test "expired whole-operation deadline refuses before spawn" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    try std.testing.expectError(error.OperationDeadlineExceeded, run(std.testing.allocator, std.testing.io, .{ .argv = &.{ "/bin/sh", "-c", "exit 0" }, .absolute_deadline_ns = now(std.testing.io) - 1 }));
}

// The signal comes from a real disposable child process, never the test runner.
// Broken default signal handling leaves only a finite harmless three-second sleep.
fn externalSignalFixture(signal: []const u8) !void {
    const pid = c.fork();
    try std.testing.expect(pid >= 0);
    if (pid == 0) {
        var threaded = std.Io.Threaded.init(std.heap.page_allocator, .{});
        const script = std.fmt.allocPrint(std.heap.page_allocator, "printf '%s' $$; exec 1>&- 2>&-; sleep .02; kill -{s} \"$PPID\"; exec /bin/sleep 3", .{signal}) catch c._exit(2);
        const result = run(std.heap.page_allocator, threaded.io(), .{
            .argv = &.{ "/bin/sh", "-c", script },
            .limits = .{ .wall_ms = 1000, .cleanup_ms = 300 },
        }) catch c._exit(3);
        const child_pid = std.fmt.parseInt(i32, result.stdout, 10) catch c._exit(4);
        const ok = result.failure == .cancelled and result.leader_reaped and result.group_disposed and !liveProcess(child_pid) and result.elapsed_ms < 1000;
        c._exit(if (ok) 0 else 5);
    }
    var status: c_int = 0;
    try std.testing.expectEqual(pid, c.waitpid(pid, &status, 0));
    try std.testing.expectEqual(@as(c_int, 0), status);
}

test "real SIGTERM cancels public owner after EOF and disposes its child" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    try externalSignalFixture("TERM");
}

test "real SIGINT cancels public owner after EOF and disposes its child" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    try externalSignalFixture("INT");
}

fn priorSignal(_: c_int) callconv(.c) void {}

test "signal bridge restores prior handlers and refuses a second owner" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    var prior = std.mem.zeroes(c.struct_sigaction);
    prior.__sigaction_u.__sa_handler = priorSignal;
    var original: c.struct_sigaction = undefined;
    try std.testing.expectEqual(@as(c_int, 0), c.sigaction(c.SIGINT, &prior, &original));
    defer _ = c.sigaction(c.SIGINT, &original, null);
    var signals = try SignalBridge.install();
    defer _ = signals.restore() catch 0;
    try std.testing.expectError(error.SignalBridgeBusy, SignalBridge.install());
    _ = try signals.restore();
    var restored: c.struct_sigaction = undefined;
    try std.testing.expectEqual(@as(c_int, 0), c.sigaction(c.SIGINT, null, &restored));
    try std.testing.expect(restored.__sigaction_u.__sa_handler == prior.__sigaction_u.__sa_handler);
    const result = try fixture("exit 0", .{});
    defer result.deinit(std.testing.allocator);
    try std.testing.expect(result.failure == null and result.group_disposed);
}
