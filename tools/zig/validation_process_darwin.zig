//! Adapted under the owner-authorized Native Local Validation plan/T010 from
//! temet-nosce 7d99ede611abbbfbda4503471fa71b417a6ef177,
//! tools/zig/owned_process_group.zig, SHA-256
//! 16dbf37d5d9199e61523e731cf931404e695d7a37fec463519951ba0a26fff8b.
//! Upstream snapshot has no root LICENSE; no upstream license is invented here.
//! Changes: live regular-file sinks, quota-prefix retention, bounded previews,
//! explicit original-group/all-descendant qualification, and supported 64-process
//! sample budgets, plus SDK posix_spawn to avoid losing failed-spawn child/pipe
//! custody in Zig 0.16 Threaded. Cwd file actions require macOS 26 or later;
//! actual platform qualification remains tied to its observed host and SDK.
//! The unchanged test fixture retains the exact original source.
//! Bounded native child-group ownership. Darwin uses the reviewed libproc
//! foundation; Linux uses waitid, an owned POSIX process group, and procfs
//! inspection. Neither backend claims session-escape containment.
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
    @cInclude("sys/stat.h");
    @cInclude("errno.h");
    @cInclude("sys/spawn.h");
    @cInclude("crt_externs.h");
    @cInclude("sys/proc_info.h");
    @cInclude("unistd.h");
    @cInclude("fcntl.h");
    @cInclude("poll.h");
    @cInclude("signal.h");
}) else if (builtin.os.tag == .linux) @cImport({
    @cDefine("_GNU_SOURCE", "1");
    @cInclude("sys/wait.h");
    @cInclude("sys/types.h");
    @cInclude("sys/stat.h");
    @cInclude("errno.h");
    @cInclude("unistd.h");
    @cInclude("fcntl.h");
    @cInclude("poll.h");
    @cInclude("signal.h");
    @cInclude("dirent.h");
}) else struct {};
// The strict POSIX spawn header keeps its SDK-owned opaque handle types while
// excluding unrelated Mach packed-layout extensions that Zig cannot translate.
const spawn = if (builtin.os.tag == .macos) @cImport({
    @cDefine("_POSIX_C_SOURCE", "200809L");
    @cInclude("spawn.h");
}) else if (builtin.os.tag == .linux) @cImport({
    @cDefine("_GNU_SOURCE", "1");
    @cInclude("spawn.h");
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
pub const Failure = enum { wall_timeout, stdout_limit, stderr_limit, process_limit, resident_limit, cancelled, external_budget, inspection_failed, ownership_lost, cleanup_failed, log_failed };
pub const ChildUsage = struct { processes: usize, resident_bytes: u64 };
pub const InFlight = struct {
    stdout_retained: usize = 0,
    stderr_retained: usize = 0,
    stdout_preview: usize = 0,
    stderr_preview: usize = 0,
    sampled_processes: usize = 0,
    sampled_resident_bytes: u64 = 0,
};
/// A synchronous borrowed monitor for the check's retained, source-closed worker.
/// Its context remains owned by the caller until this run and cleanup return.
pub const RetainedMonitor = struct { context: *anyopaque, poll: *const fn (*anyopaque, InFlight) ?Failure };
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
    stdout_sink: ?std.Io.File = null,
    stderr_sink: ?std.Io.File = null,
    display_bytes: usize = 8192,
    retained_monitor: ?RetainedMonitor = null,
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
    stdout_observed_bytes: u64,
    stderr_observed_bytes: u64,
    stdout_retained_bytes: ?usize,
    stderr_retained_bytes: ?usize,
    ownership_scope: []const u8 = "original-posix-group",
    all_owned_children_terminal: bool = false,
    session_escape_containment_qualified: bool = false,
    usage_measurement: []const u8 = "sampled-not-hard-peaks",
    pub fn deinit(self: Result, allocator: std.mem.Allocator) void {
        allocator.free(self.stdout);
        allocator.free(self.stderr);
    }
};

fn validBudget(limits: Limits) bool {
    return limits.wall_ms != 0 and limits.wall_ms <= 3_600_000 and limits.cleanup_ms != 0 and limits.cleanup_ms <= 5000 and limits.stdout_bytes <= 16 * 1024 * 1024 and limits.stderr_bytes <= 16 * 1024 * 1024 and limits.processes != 0 and limits.processes <= 64 and limits.resident_bytes != 0;
}

fn validateOptions(io: std.Io, options: Options) !void {
    if (options.argv.len == 0 or !std.fs.path.isAbsolute(options.argv[0]) or !validBudget(options.limits)) return error.InvalidProcessBudget;
    if ((options.stdout_sink == null) != (options.stderr_sink == null)) return error.InvalidLogSink;
    if (options.stdout_sink != null and (options.display_bytes == 0 or options.display_bytes > 65536)) return error.InvalidLogSink;
    const Identity = struct { device: u64, inode: u64 };
    var identities: [2]Identity = undefined;
    for ([_]?std.Io.File{ options.stdout_sink, options.stderr_sink }, 0..) |sink, index| if (sink) |file| {
        const stat = try file.stat(io);
        if (stat.kind != .file or stat.size != 0 or stat.nlink != 1) return error.InvalidLogSink;
        if (builtin.os.tag == .linux) {
            const wanted: std.os.linux.STATX = .{ .TYPE = true, .NLINK = true, .INO = true };
            var observed = std.mem.zeroes(std.os.linux.Statx);
            if (std.c.statx(file.handle, "", std.os.linux.AT.EMPTY_PATH, wanted, &observed) != 0) return error.InvalidLogSink;
            const bits: u32 = @bitCast(wanted);
            if (@as(u32, @bitCast(observed.mask)) & bits != bits or observed.mode & c.S_IFMT != c.S_IFREG or observed.nlink != 1) return error.InvalidLogSink;
            identities[index] = .{ .device = (@as(u64, observed.dev_major) << 32) | observed.dev_minor, .inode = observed.ino };
        } else {
            var observed: c.struct_stat = undefined;
            if (c.fstat(file.handle, &observed) != 0) return error.InvalidLogSink;
            identities[index] = .{ .device = @intCast(observed.st_dev), .inode = @intCast(observed.st_ino) };
        }
    };
    if (options.stdout_sink != null and identities[0].device == identities[1].device and identities[0].inode == identities[1].inode) return error.InvalidLogSink;
}

pub fn run(allocator: std.mem.Allocator, io: std.Io, options: Options) !Result {
    if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
    try validateOptions(io, options);
    const started = now(io);
    var signals = try SignalBridge.install();
    var result = runOwned(allocator, io, options, started, null) catch |failure| {
        _ = try signals.restore();
        return failure;
    };
    errdefer result.deinit(allocator);
    const received_signal = try signals.restore();
    if (received_signal != 0 and result.failure == null) result.failure = .cancelled;
    return result;
}

pub const LogSinks = struct { stdout: std.Io.File, stderr: std.Io.File };

/// Borrow empty, unaliased regular files for this synchronous call only.
/// Quotas bound raw files; display_bytes bounds independently returned excerpts.
pub fn runLogged(allocator: std.mem.Allocator, io: std.Io, options: Options, sinks: LogSinks) !Result {
    var logged = options;
    logged.stdout_sink = sinks.stdout;
    logged.stderr_sink = sinks.stderr;
    return run(allocator, io, logged);
}

/// One synchronous check lifetime. Commands must have separately qualified
/// no-process-creation closure: each group joins before another argv starts.
/// This context is not a descendant namespace or a detached-sampler owner.
pub const CheckScope = struct {
    limits: Limits,
    started: i96,
    deadline: i96,
    cleanup_used_ns: i96 = 0,
    signals: SignalBridge,
    active: bool = true,
    stopped: bool = false,
    custody_complete: bool = true,
    leaders_reaped: bool = true,
    groups_disposed: bool = true,
    stdout: std.ArrayList(u8) = .empty,
    stderr: std.ArrayList(u8) = .empty,
    display_bytes: usize,
    stdout_observed: u64 = 0,
    stderr_observed: u64 = 0,
    stdout_retained: usize = 0,
    stderr_retained: usize = 0,
    retention_known: bool = true,
    max_processes: usize = 0,
    max_resident: u64 = 0,
    failure: ?Failure = null,
    exit_code: ?u8 = null,
    failed_exit_seen: bool = false,

    pub fn begin(allocator: std.mem.Allocator, io: std.Io, limits: Limits, display_bytes: usize) !CheckScope {
        if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
        if (!validBudget(limits) or display_bytes == 0 or display_bytes > 65536) return error.InvalidProcessBudget;
        var output: std.ArrayList(u8) = .empty;
        errdefer output.deinit(allocator);
        try output.ensureTotalCapacity(allocator, display_bytes);
        var diagnostic: std.ArrayList(u8) = .empty;
        errdefer diagnostic.deinit(allocator);
        try diagnostic.ensureTotalCapacity(allocator, display_bytes);
        const started = now(io);
        const signals = try SignalBridge.install();
        return .{ .limits = limits, .started = started, .deadline = started + @as(i96, limits.wall_ms) * std.time.ns_per_ms, .signals = signals, .display_bytes = display_bytes, .stdout = output, .stderr = diagnostic };
    }

    pub fn ready(self: *CheckScope, io: std.Io) !void {
        if (!self.active or self.stopped) return error.CheckScopeStopped;
        if (pending_signal.load(.monotonic) != 0) return error.OperationCancelled;
        if (now(io) >= self.deadline) return error.OperationDeadlineExceeded;
        if (self.stdout_retained > self.limits.stdout_bytes) return error.StdoutBudgetExceeded;
        if (self.stderr_retained > self.limits.stderr_bytes) return error.StderrBudgetExceeded;
        if (self.cleanup_used_ns >= @as(i96, self.limits.cleanup_ms) * std.time.ns_per_ms) return error.CleanupBudgetExceeded;
    }

    /// The initial limits, clock and signal owner cannot be reset by a step.
    pub fn runLogged(self: *CheckScope, allocator: std.mem.Allocator, io: std.Io, options: Options, sinks: LogSinks) !Result {
        if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
        try self.ready(io);
        var current = options;
        current.limits = self.limits;
        current.limits.stdout_bytes -= self.stdout_retained;
        current.limits.stderr_bytes -= self.stderr_retained;
        current.absolute_deadline_ns = @min(self.deadline, options.absolute_deadline_ns orelse std.math.maxInt(i96));
        current.display_bytes = self.display_bytes;
        current.stdout_sink = sinks.stdout;
        current.stderr_sink = sinks.stderr;
        try validateOptions(io, current);
        const outcome = runOwned(allocator, io, current, now(io), self) catch |failure| {
            self.stopped = true;
            self.custody_complete = false;
            self.leaders_reaped = false;
            self.groups_disposed = false;
            self.retention_known = false;
            return failure;
        };
        self.stdout.appendSliceAssumeCapacity(outcome.stdout);
        self.stderr.appendSliceAssumeCapacity(outcome.stderr);
        self.stdout_observed += outcome.stdout_observed_bytes;
        self.stderr_observed += outcome.stderr_observed_bytes;
        if (outcome.stdout_retained_bytes) |count| self.stdout_retained += count else self.retention_known = false;
        if (outcome.stderr_retained_bytes) |count| self.stderr_retained += count else self.retention_known = false;
        self.max_processes = @max(self.max_processes, outcome.max_sampled_processes);
        self.max_resident = @max(self.max_resident, outcome.max_sampled_resident_bytes);
        self.leaders_reaped = self.leaders_reaped and outcome.leader_reaped;
        self.groups_disposed = self.groups_disposed and outcome.group_disposed;
        self.custody_complete = self.leaders_reaped and self.groups_disposed;
        if (!self.failed_exit_seen) {
            self.exit_code = outcome.exit_code;
            self.failed_exit_seen = outcome.exit_code == null or outcome.exit_code.? != 0;
        }
        if (outcome.failure) |failure| {
            if (self.failure == null) self.failure = failure;
            self.stopped = true;
        }
        if (!self.custody_complete or !self.retention_known) self.stopped = true;
        return outcome;
    }

    fn dispose(self: *CheckScope, owner: *Ownership, io: std.Io) bool {
        const started = now(io);
        const remaining = @max(0, @as(i96, self.limits.cleanup_ms) * std.time.ns_per_ms - self.cleanup_used_ns);
        const disposed = owner.disposeUntil(io, started + remaining);
        self.cleanup_used_ns += @max(0, now(io) - started);
        return disposed;
    }

    pub fn finish(self: *CheckScope, allocator: std.mem.Allocator, io: std.Io) !Result {
        if (!self.active) return error.CheckScopeStopped;
        self.active = false;
        const received = try self.signals.restore();
        if (received != 0 and self.failure == null) self.failure = .cancelled;
        if (now(io) >= self.deadline and self.failure == null) self.failure = .wall_timeout;
        const output = try allocator.dupe(u8, self.stdout.items);
        errdefer allocator.free(output);
        return .{ .stdout = output, .stderr = try allocator.dupe(u8, self.stderr.items), .failure = self.failure, .exit_code = self.exit_code, .leader_reaped = self.leaders_reaped, .group_disposed = self.groups_disposed, .elapsed_ms = @intCast(@divTrunc(now(io) - self.started, std.time.ns_per_ms)), .max_sampled_processes = self.max_processes, .max_sampled_resident_bytes = self.max_resident, .stdout_observed_bytes = self.stdout_observed, .stderr_observed_bytes = self.stderr_observed, .stdout_retained_bytes = if (self.retention_known) self.stdout_retained else null, .stderr_retained_bytes = if (self.retention_known) self.stderr_retained else null };
    }

    pub fn deinit(self: *CheckScope, allocator: std.mem.Allocator) void {
        if (self.active) {
            self.active = false;
            _ = self.signals.restore() catch {};
        }
        self.stdout.deinit(allocator);
        self.stderr.deinit(allocator);
    }
};

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
        if (builtin.os.tag == .macos) {
            action.__sigaction_u.__sa_handler = cancellationSignal;
        } else {
            action.__sa_handler.sa_handler = cancellationSignal;
        }
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

fn disposeOwned(owner: *Ownership, io: std.Io, cleanup_ms: u32, scope: ?*CheckScope) bool {
    if (scope) |check| return check.dispose(owner, io);
    return owner.dispose(io, cleanup_ms);
}

fn runOwned(allocator: std.mem.Allocator, io: std.Io, options: Options, started: i96, scope: ?*CheckScope) !Result {
    const limits = options.limits;
    const deadline = @min(started + @as(i96, limits.wall_ms) * std.time.ns_per_ms, options.absolute_deadline_ns orelse std.math.maxInt(i96));
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
    var stdout_preview = limits.stdout_bytes;
    if (options.stdout_sink != null) stdout_preview = options.display_bytes;
    var stderr_preview = limits.stderr_bytes;
    if (options.stderr_sink != null) stderr_preview = options.display_bytes;
    if (scope) |check| {
        stdout_preview = @min(stdout_preview, check.display_bytes - check.stdout.items.len);
        stderr_preview = @min(stderr_preview, check.display_bytes - check.stderr.items.len);
    }
    var out = try Capture.init(allocator, limits.stdout_bytes, stdout_preview, options.stdout_sink);
    defer out.list.deinit(allocator);
    var err = try Capture.init(allocator, limits.stderr_bytes, stderr_preview, options.stderr_sink);
    defer err.list.deinit(allocator);
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
    if (pending_signal.load(.monotonic) != 0) return error.OperationCancelled;
    var child = try spawnOwned(allocator, io, options, deadline, scope);
    var owner = Ownership{ .pid = child.id.? };
    defer {
        if (owner.valid and !owner.reaped) _ = disposeOwned(&owner, io, limits.cleanup_ms, scope);
        if (child.stdout) |file| file.close(io);
        if (child.stderr) |file| file.close(io);
        child.id = null;
    }
    for ([_]?std.Io.File{ child.stdout, child.stderr }) |file| {
        if (c.fcntl(file.?.handle, c.F_SETFL, @as(c_int, c.O_NONBLOCK)) != 0) return error.PipeConfigurationFailed;
    }
    var failure: ?Failure = null;
    var max_processes: usize = 0;
    var max_resident: u64 = 0;
    while (true) {
        var usage: Usage = .{};
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
                failure = .ownership_lost;
                if (owner.valid) failure = .inspection_failed;
                break;
            };
            usage = groupUsage(owner.pid, terminal) catch {
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
                if (!disposeOwned(&owner, io, limits.cleanup_ms, scope)) {
                    failure = .cleanup_failed;
                    if (!owner.valid and !owner.reaped) failure = .ownership_lost;
                }
            }
        }
        if (options.retained_monitor) |monitor| {
            if (monitor.poll(monitor.context, .{ .stdout_retained = out.retained, .stderr_retained = err.retained, .stdout_preview = out.list.items.len, .stderr_preview = err.list.items.len, .sampled_processes = usage.processes, .sampled_resident_bytes = usage.resident_bytes })) |problem| {
                failure = problem;
                break;
            }
            // The retained worker and current command share the original raw
            // and display budgets. A monitor cannot grant a command fresh quota.
            if (scope) |check| {
                if (check.stdout_retained > check.limits.stdout_bytes or out.retained > check.limits.stdout_bytes - check.stdout_retained) {
                    failure = .stdout_limit;
                    break;
                }
                if (check.stderr_retained > check.limits.stderr_bytes or err.retained > check.limits.stderr_bytes - check.stderr_retained) {
                    failure = .stderr_limit;
                    break;
                }
                if (check.stdout.items.len + out.list.items.len > check.display_bytes or check.stderr.items.len + err.list.items.len > check.display_bytes) {
                    failure = .inspection_failed;
                    break;
                }
                out.quota = check.limits.stdout_bytes - check.stdout_retained;
                err.quota = check.limits.stderr_bytes - check.stderr_retained;
                out.preview = @min(out.quota, check.display_bytes - check.stdout.items.len);
                err.preview = @min(err.quota, check.display_bytes - check.stderr.items.len);
            }
        }
        if (out.open) out.read(io, child.stdout.?.handle) catch |e| {
            failure = .inspection_failed;
            if (e == error.OutputLimit) {
                failure = .stdout_limit;
            } else if (e == error.LogWriteFailed) {
                failure = .log_failed;
            }
            break;
        };
        if (err.open) err.read(io, child.stderr.?.handle) catch |e| {
            failure = .inspection_failed;
            if (e == error.OutputLimit) {
                failure = .stderr_limit;
            } else if (e == error.LogWriteFailed) {
                failure = .log_failed;
            }
            break;
        };
        if (failure != null or (owner.reaped and !out.open and !err.open)) break;
        var stdout_fd: c_int = -1;
        if (out.open) stdout_fd = child.stdout.?.handle;
        var stderr_fd: c_int = -1;
        if (err.open) stderr_fd = child.stderr.?.handle;
        var fds = [_]c.struct_pollfd{ .{ .fd = stdout_fd, .events = c.POLLIN, .revents = 0 }, .{ .fd = stderr_fd, .events = c.POLLIN, .revents = 0 } };
        const remaining_ms: c_int = @intCast(@min(5, @max(0, @divTrunc(deadline - now(io), std.time.ns_per_ms))));
        if (c.poll(&fds, fds.len, remaining_ms) < 0 and std.c.errno(@as(c_int, -1)) != .INTR) {
            failure = .inspection_failed;
            break;
        }
    }
    if (!owner.reaped and owner.valid and !disposeOwned(&owner, io, limits.cleanup_ms, scope)) {
        failure = .cleanup_failed;
        if (!owner.valid and !owner.reaped) failure = .ownership_lost;
    }
    var stdout_retained: ?usize = null;
    if (out.retained_known) stdout_retained = out.retained;
    var stderr_retained: ?usize = null;
    if (err.retained_known) stderr_retained = err.retained;
    const stdout = try allocator.dupe(u8, out.list.items);
    errdefer allocator.free(stdout);
    return .{ .stdout = stdout, .stderr = try allocator.dupe(u8, err.list.items), .failure = failure, .exit_code = owner.exit_code, .leader_reaped = owner.reaped, .group_disposed = owner.disposed, .elapsed_ms = @intCast(@divTrunc(now(io) - started, std.time.ns_per_ms)), .max_sampled_processes = max_processes, .max_sampled_resident_bytes = max_resident, .stdout_observed_bytes = out.observed, .stderr_observed_bytes = err.observed, .stdout_retained_bytes = stdout_retained, .stderr_retained_bytes = stderr_retained };
}

// SDK posix_spawn reports pre-exec failure without losing an already forked
// identity inside std.Io.Threaded. All allocation and file-action setup precedes
// the syscall; every unsuccessful attempt closes its exact parent descriptors.
fn spawnOwned(allocator: std.mem.Allocator, io: std.Io, options: Options, deadline: i96, scope: ?*CheckScope) !std.process.Child {
    if (comptime builtin.os.tag == .linux) return spawnOwnedLinux(allocator, io, options, deadline, scope);
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();
    const temporary = arena.allocator();
    const argv = try temporary.allocSentinel(?[*:0]u8, options.argv.len, null);
    for (options.argv, 0..) |argument, index| {
        if (std.mem.indexOfScalar(u8, argument, 0) != null) return error.InvalidArguments;
        argv[index] = (try temporary.dupeZ(u8, argument)).ptr;
    }
    var inherited: [*c]const [*c]u8 = c._NSGetEnviron().*;
    if (options.environment) |environment| {
        for (environment.keys(), environment.values()) |key, value| {
            if (key.len == 0 or std.mem.indexOfScalar(u8, key, '=') != null or std.mem.indexOfScalar(u8, key, 0) != null or std.mem.indexOfScalar(u8, value, 0) != null) return error.InvalidEnvironment;
        }
        const block = try environment.createPosixBlock(temporary, .{});
        inherited = @ptrCast(block.slice.ptr);
    }
    var actions: spawn.posix_spawn_file_actions_t = null;
    if (spawn.posix_spawn_file_actions_init(&actions) != 0) return error.SpawnSetupFailed;
    var actions_active = true;
    defer if (actions_active) {
        _ = spawn.posix_spawn_file_actions_destroy(&actions);
    };
    var attributes: spawn.posix_spawnattr_t = null;
    if (spawn.posix_spawnattr_init(&attributes) != 0) return error.SpawnSetupFailed;
    var attributes_active = true;
    defer if (attributes_active) {
        _ = spawn.posix_spawnattr_destroy(&attributes);
    };
    if (spawn.posix_spawnattr_setpgroup(&attributes, 0) != 0 or spawn.posix_spawnattr_setflags(&attributes, c.POSIX_SPAWN_SETPGROUP | c.POSIX_SPAWN_CLOEXEC_DEFAULT) != 0) return error.SpawnSetupFailed;
    if (spawn.posix_spawn_file_actions_addopen(&actions, 0, "/dev/null", c.O_RDONLY, 0) != 0) return error.SpawnSetupFailed;
    if (options.cwd == .path) {
        const path = options.cwd.path;
        if (std.mem.indexOfScalar(u8, path, 0) != null) return error.InvalidArguments;
        const terminated = try temporary.dupeZ(u8, path);
        if (spawn.posix_spawn_file_actions_addchdir(&actions, terminated.ptr) != 0) return error.SpawnSetupFailed;
    } else if (options.cwd == .dir) {
        if (spawn.posix_spawn_file_actions_addfchdir(&actions, options.cwd.dir.handle) != 0) return error.SpawnSetupFailed;
    }
    const out = try ownedPipe();
    defer _ = c.close(out[1]);
    errdefer _ = c.close(out[0]);
    const err = try ownedPipe();
    defer _ = c.close(err[1]);
    errdefer _ = c.close(err[0]);
    if (spawn.posix_spawn_file_actions_adddup2(&actions, out[1], 1) != 0 or spawn.posix_spawn_file_actions_adddup2(&actions, err[1], 2) != 0) return error.SpawnSetupFailed;
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
    if (pending_signal.load(.monotonic) != 0) return error.OperationCancelled;
    try io.checkCancel();
    if (options.cancel_probe) |probe| if (probe(options.cancel_context)) return error.OperationCancelled;
    if (options.budget_probe) |probe| if (probe(options.budget_context)) return error.OperationBudgetExceeded;
    var pid: c.pid_t = 0;
    const spawn_error = spawn.posix_spawn(&pid, argv[0].?, &actions, &attributes, @ptrCast(argv.ptr), inherited);
    // Attempt both metadata disposals before interpreting the outcome. A real
    // child remains unreaped and exclusively retained throughout this seam.
    const actions_error = spawn.posix_spawn_file_actions_destroy(&actions);
    actions_active = false;
    const attributes_error = spawn.posix_spawnattr_destroy(&attributes);
    attributes_active = false;
    if (spawn_error != 0) {
        if (spawn_error == c.ENOENT) return error.FileNotFound;
        if (spawn_error == c.EACCES) return error.AccessDenied;
        return error.SpawnFailed;
    }
    var owner = Ownership{ .pid = pid };
    errdefer _ = disposeOwned(&owner, io, options.limits.cleanup_ms, scope);
    if (actions_error != 0 or attributes_error != 0) return error.SpawnMetadataCleanupFailed;
    return .{ .id = pid, .thread_handle = {}, .stdin = null, .stdout = .{ .handle = out[0], .flags = .{ .nonblocking = false } }, .stderr = .{ .handle = err[0], .flags = .{ .nonblocking = false } }, .request_resource_usage_statistics = false };
}

fn spawnOwnedLinux(allocator: std.mem.Allocator, io: std.Io, options: Options, deadline: i96, scope: ?*CheckScope) !std.process.Child {
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();
    const temporary = arena.allocator();
    const argv = try temporary.allocSentinel(?[*:0]u8, options.argv.len, null);
    for (options.argv, 0..) |argument, index| {
        if (std.mem.indexOfScalar(u8, argument, 0) != null) return error.InvalidArguments;
        argv[index] = (try temporary.dupeZ(u8, argument)).ptr;
    }
    var environment: [*c]const [*c]u8 = @ptrCast(std.c.environ);
    if (options.environment) |map| {
        for (map.keys(), map.values()) |key, value| {
            if (key.len == 0 or std.mem.indexOfScalar(u8, key, '=') != null or std.mem.indexOfScalar(u8, key, 0) != null or std.mem.indexOfScalar(u8, value, 0) != null) return error.InvalidEnvironment;
        }
        const block = try map.createPosixBlock(temporary, .{});
        environment = @ptrCast(block.slice.ptr);
    }

    var actions: spawn.posix_spawn_file_actions_t = undefined;
    if (spawn.posix_spawn_file_actions_init(&actions) != 0) return error.SpawnSetupFailed;
    var actions_active = true;
    defer if (actions_active) {
        _ = spawn.posix_spawn_file_actions_destroy(&actions);
    };
    var attributes: spawn.posix_spawnattr_t = undefined;
    if (spawn.posix_spawnattr_init(&attributes) != 0) return error.SpawnSetupFailed;
    var attributes_active = true;
    defer if (attributes_active) {
        _ = spawn.posix_spawnattr_destroy(&attributes);
    };
    if (spawn.posix_spawnattr_setpgroup(&attributes, 0) != 0 or spawn.posix_spawnattr_setflags(&attributes, spawn.POSIX_SPAWN_SETPGROUP) != 0) return error.SpawnSetupFailed;
    if (spawn.posix_spawn_file_actions_addopen(&actions, 0, "/dev/null", c.O_RDONLY, 0) != 0) return error.SpawnSetupFailed;
    if (options.cwd == .path) {
        const path = options.cwd.path;
        if (std.mem.indexOfScalar(u8, path, 0) != null) return error.InvalidArguments;
        const terminated = try temporary.dupeZ(u8, path);
        if (spawn.posix_spawn_file_actions_addchdir_np(&actions, terminated.ptr) != 0) return error.SpawnSetupFailed;
    } else if (options.cwd == .dir) {
        if (spawn.posix_spawn_file_actions_addfchdir_np(&actions, options.cwd.dir.handle) != 0) return error.SpawnSetupFailed;
    }

    const out = try ownedPipe();
    defer _ = c.close(out[1]);
    errdefer _ = c.close(out[0]);
    const err = try ownedPipe();
    defer _ = c.close(err[1]);
    errdefer _ = c.close(err[0]);
    if (spawn.posix_spawn_file_actions_adddup2(&actions, out[1], 1) != 0 or spawn.posix_spawn_file_actions_adddup2(&actions, err[1], 2) != 0) return error.SpawnSetupFailed;

    // /proc is required by the Linux group-inspection backend. Keep its stream
    // open through spawn while arranging close actions for every observed fd
    // above stderr, including these pipe originals and caller-owned log files.
    const inherited_directory = c.opendir("/proc/self/fd") orelse return error.DescriptorInspectionFailed;
    defer _ = c.closedir(inherited_directory);
    try addCloseActionsForInheritedDescriptors(&actions, inherited_directory);

    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
    if (pending_signal.load(.monotonic) != 0) return error.OperationCancelled;
    try io.checkCancel();
    if (options.cancel_probe) |probe| if (probe(options.cancel_context)) return error.OperationCancelled;
    if (options.budget_probe) |probe| if (probe(options.budget_context)) return error.OperationBudgetExceeded;
    var pid: c.pid_t = 0;
    const spawn_error = spawn.posix_spawn(&pid, argv[0].?, &actions, &attributes, @ptrCast(argv.ptr), environment);
    const actions_error = spawn.posix_spawn_file_actions_destroy(&actions);
    actions_active = false;
    const attributes_error = spawn.posix_spawnattr_destroy(&attributes);
    attributes_active = false;
    if (spawn_error != 0) {
        if (spawn_error == c.ENOENT) return error.FileNotFound;
        if (spawn_error == c.EACCES) return error.AccessDenied;
        return error.SpawnFailed;
    }
    var owner = Ownership{ .pid = pid };
    errdefer _ = disposeOwned(&owner, io, options.limits.cleanup_ms, scope);
    if (actions_error != 0 or attributes_error != 0) return error.SpawnMetadataCleanupFailed;
    return .{ .id = pid, .thread_handle = {}, .stdin = null, .stdout = .{ .handle = out[0], .flags = .{ .nonblocking = false } }, .stderr = .{ .handle = err[0], .flags = .{ .nonblocking = false } }, .request_resource_usage_statistics = false };
}

/// Spawn the lifetime-bound sampler worker with only its private socket on
/// stdin/stdout. The worker creates its own session after exec, so this child
/// must not join the ordinary command's process group.
pub fn spawnSamplerWorkerLinux(allocator: std.mem.Allocator, io: std.Io, argv_values: []const []const u8, cwd: []const u8, environment_map: *const std.process.Environ.Map, socket_fd: c_int, deadline: i96, cleanup_ms: u32) !std.process.Child {
    if (comptime builtin.os.tag != .linux) return error.PlatformUnsupported;
    if (cleanup_ms == 0 or cleanup_ms > 5000) return error.InvalidProcessBudget;
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
    var arena = std.heap.ArenaAllocator.init(allocator);
    defer arena.deinit();
    const temporary = arena.allocator();
    const argv = try temporary.allocSentinel(?[*:0]u8, argv_values.len, null);
    for (argv_values, 0..) |argument, index| {
        if (std.mem.indexOfScalar(u8, argument, 0) != null) return error.InvalidArguments;
        argv[index] = (try temporary.dupeZ(u8, argument)).ptr;
    }
    for (environment_map.keys(), environment_map.values()) |key, value| {
        if (key.len == 0 or std.mem.indexOfScalar(u8, key, '=') != null or std.mem.indexOfScalar(u8, key, 0) != null or std.mem.indexOfScalar(u8, value, 0) != null) return error.InvalidEnvironment;
    }
    const environment = try environment_map.createPosixBlock(temporary, .{});
    const cwd_z = try temporary.dupeZ(u8, cwd);
    var actions: spawn.posix_spawn_file_actions_t = undefined;
    if (spawn.posix_spawn_file_actions_init(&actions) != 0) return error.SpawnSetupFailed;
    var actions_active = true;
    defer if (actions_active) {
        _ = spawn.posix_spawn_file_actions_destroy(&actions);
    };
    if (spawn.posix_spawn_file_actions_adddup2(&actions, socket_fd, 0) != 0 or spawn.posix_spawn_file_actions_adddup2(&actions, socket_fd, 1) != 0) return error.SpawnSetupFailed;
    if (spawn.posix_spawn_file_actions_addchdir_np(&actions, cwd_z.ptr) != 0) return error.SpawnSetupFailed;
    const inherited_directory = c.opendir("/proc/self/fd") orelse return error.DescriptorInspectionFailed;
    defer _ = c.closedir(inherited_directory);
    try addCloseActionsForInheritedDescriptors(&actions, inherited_directory);
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
    if (pending_signal.load(.monotonic) != 0) return error.OperationCancelled;
    try io.checkCancel();
    var pid: c.pid_t = 0;
    const spawn_error = spawn.posix_spawn(&pid, argv[0].?, &actions, null, @ptrCast(argv.ptr), @ptrCast(environment.slice.ptr));
    const actions_error = spawn.posix_spawn_file_actions_destroy(&actions);
    actions_active = false;
    if (spawn_error != 0) {
        if (spawn_error == c.ENOENT) return error.FileNotFound;
        if (spawn_error == c.EACCES) return error.AccessDenied;
        return error.SpawnFailed;
    }
    if (actions_error != 0) {
        // The exact child remains observable until it is reaped. Attempt a
        // bounded direct-child cleanup before returning the metadata failure.
        _ = c.kill(pid, c.SIGKILL);
        const cleanup_deadline = now(io) + @as(i96, cleanup_ms) * std.time.ns_per_ms;
        while (now(io) < cleanup_deadline) {
            var status: c_int = 0;
            const joined = c.waitpid(pid, &status, c.WNOHANG);
            if (joined == pid or (joined < 0 and std.c.errno(joined) == .CHILD)) break;
            _ = c.poll(null, 0, 1);
        }
        return error.SpawnMetadataCleanupFailed;
    }
    return .{ .id = pid, .thread_handle = {}, .stdin = null, .stdout = null, .stderr = null, .request_resource_usage_statistics = false };
}

fn addCloseActionsForInheritedDescriptors(actions: *spawn.posix_spawn_file_actions_t, directory: anytype) !void {
    // The caller keeps /proc/self/fd open through spawn so every descriptor
    // observed here remains stable while its child-side close action is used.
    while (true) {
        std.c._errno().* = 0;
        const entry = c.readdir(directory) orelse {
            if (std.c.errno(@as(c_int, -1)) != .SUCCESS) return error.DescriptorInspectionFailed;
            break;
        };
        const name = std.mem.sliceTo(@as([*:0]const u8, @ptrCast(&entry.*.d_name)), 0);
        const fd = std.fmt.parseInt(c_int, name, 10) catch continue;
        if (fd <= 2) continue;
        if (spawn.posix_spawn_file_actions_addclose(actions, fd) != 0) return error.SpawnSetupFailed;
    }
}

fn ownedPipe() ![2]c_int {
    var descriptors: [2]c_int = undefined;
    if (c.pipe(&descriptors) != 0) return error.PipeCreationFailed;
    errdefer {
        _ = c.close(descriptors[0]);
        _ = c.close(descriptors[1]);
    }
    // Keep all temporary endpoints away from stdin/stdout/stderr, including
    // callers that had one of those descriptors closed before this call.
    for (&descriptors) |*fd| {
        const duplicate = c.fcntl(fd.*, c.F_DUPFD_CLOEXEC, @as(c_int, 3));
        if (duplicate < 0) return error.PipeCreationFailed;
        _ = c.close(fd.*);
        fd.* = duplicate;
    }
    return descriptors;
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
        if (builtin.os.tag == .linux) {
            const linux = std.os.linux;
            var info: linux.siginfo_t = std.mem.zeroes(linux.siginfo_t);
            switch (linux.errno(linux.waitid(.PID, self.pid, &info, linux.W.EXITED | linux.W.NOHANG | linux.W.NOWAIT, null))) {
                .SUCCESS => {},
                .CHILD => {
                    self.valid = false;
                    return error.OwnershipLost;
                },
                .INTR => return false,
                else => return error.ExitObservationFailed,
            }
            if (@intFromEnum(info.signo) == 0) return false;
            if (info.signo != .CHLD or info.fields.common.first.piduid.pid != self.pid) {
                self.valid = false;
                return error.OwnershipLost;
            }
            if (!try terminalEvent(info.code)) return false;
            if (info.code == c.CLD_EXITED) self.exit_code = @intCast(info.fields.common.second.sigchld.status);
            return true;
        } else {
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
    }

    fn dispose(self: *Ownership, io: std.Io, cleanup_ms: u32) bool {
        return self.disposeUntil(io, now(io) + @as(i96, cleanup_ms) * std.time.ns_per_ms);
    }

    fn disposeUntil(self: *Ownership, io: std.Io, deadline: i96) bool {
        if (!self.valid) return false;
        if (self.reaped) return self.disposed;
        if (self.cleanup_attempted) return false;
        self.cleanup_attempted = true;
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
        const terminal = self.observe() catch return false;
        if (terminal) {
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

/// A direct native sampler child, retained unreaped across ordinary argv groups.
/// This proves only this source-closed child, never arbitrary descendants.
pub const DirectChild = struct {
    identity: Ownership,
    wait_status: ?c_int = null,

    pub fn init(child_pid: i32) !DirectChild {
        if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
        if (child_pid <= 1) return error.SamplerIdentityUnknown;
        return .{ .identity = .{ .pid = child_pid } };
    }

    pub fn observe(self: *DirectChild) !bool {
        if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
        return self.identity.observe();
    }

    pub fn signal(self: *DirectChild, force: bool) !void {
        if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
        if (!self.identity.valid or self.identity.reaped) return error.SamplerIdentityUnknown;
        if (try self.identity.observe()) return;
        const rc = c.kill(self.identity.pid, if (force) c.SIGKILL else c.SIGTERM);
        const problem = std.c.errno(rc);
        if (rc == 0) return;
        // A concurrent natural exit is accepted only through the retained
        // direct-child kernel observation, never kill(pid, 0) or PID text.
        if (problem == .SRCH and try self.identity.observe()) return;
        return error.SamplerSignalFailed;
    }

    pub fn reap(self: *DirectChild) !bool {
        if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
        if (self.identity.reaped) return true;
        if (!try self.identity.observe()) return false;
        var status: c_int = 0;
        const joined_pid = c.waitpid(self.identity.pid, &status, c.WNOHANG);
        if (joined_pid != self.identity.pid) {
            if (joined_pid < 0 and std.c.errno(joined_pid) == .CHILD) self.identity.valid = false;
            return error.SamplerIdentityUnknown;
        }
        self.wait_status = status;
        self.identity.reaped = true;
        self.identity.valid = false;
        return true;
    }

    pub fn pid(self: *const DirectChild) i32 {
        return self.identity.pid;
    }
    pub fn reaped(self: *const DirectChild) bool {
        return self.identity.reaped;
    }
    pub fn valid(self: *const DirectChild) bool {
        return self.identity.valid;
    }
    pub fn exitCode(self: *const DirectChild) ?u8 {
        return self.identity.exit_code;
    }

    pub fn usage(self: *const DirectChild) !ChildUsage {
        if (builtin.os.tag == .linux) {
            if (!self.identity.valid or self.identity.reaped) return error.SamplerIdentityUnknown;
            const directory = c.opendir("/proc") orelse return error.SamplerIdentityUnknown;
            defer _ = c.closedir(directory);
            const status = (try linuxProcStat(c.dirfd(directory), self.identity.pid)) orelse return error.SamplerIdentityUnknown;
            if (status.state == 'Z' or status.state == 'X' or status.state == 'x') return error.SamplerIdentityUnknown;
            const page_size = c.sysconf(c._SC_PAGESIZE);
            if (page_size <= 0) return error.SamplerIdentityUnknown;
            return .{ .processes = 1, .resident_bytes = try std.math.mul(u64, status.resident_pages, @intCast(page_size)) };
        }
        if (builtin.os.tag != .macos) return error.PlatformUnsupported;
        if (!self.identity.valid or self.identity.reaped) return error.SamplerIdentityUnknown;
        var bsd: c.struct_proc_bsdinfo = std.mem.zeroes(c.struct_proc_bsdinfo);
        if (proc_pidinfo(self.identity.pid, c.PROC_PIDTBSDINFO, 0, &bsd, @sizeOf(c.struct_proc_bsdinfo)) != @sizeOf(c.struct_proc_bsdinfo) or bsd.pbi_pid != self.identity.pid) return error.SamplerIdentityUnknown;
        var task: c.struct_proc_taskinfo = std.mem.zeroes(c.struct_proc_taskinfo);
        if (proc_pidinfo(self.identity.pid, c.PROC_PIDTASKINFO, 0, &task, @sizeOf(c.struct_proc_taskinfo)) != @sizeOf(c.struct_proc_taskinfo)) return error.SamplerIdentityUnknown;
        return .{ .processes = 1, .resident_bytes = task.pti_resident_size };
    }
};

fn terminalEvent(code: c_int) !bool {
    if (code == c.CLD_EXITED or code == c.CLD_KILLED or code == c.CLD_DUMPED) return true;
    if (code == c.CLD_STOPPED or code == c.CLD_CONTINUED or code == c.CLD_TRAPPED) return false;
    return error.ExitObservationFailed;
}

fn now(io: std.Io) i96 {
    return std.Io.Clock.boot.now(io).nanoseconds;
}
const Usage = struct { processes: usize = 0, resident_bytes: u64 = 0 };
const ListProcesses = *const fn (u32, u32, ?*anyopaque, c_int) callconv(.c) c_int;
fn groupUsage(pgid: i32, terminal_leader: bool) !Usage {
    if (builtin.os.tag == .linux) return linuxGroupUsage(pgid, terminal_leader);
    return groupUsageUsing(pgid, terminal_leader, proc_listpids);
}

const LinuxProcStat = struct { state: u8, process_group: i32, resident_pages: u64 };

fn parseLinuxProcStat(bytes: []const u8, expected_pid: i32) !LinuxProcStat {
    const open = std.mem.indexOfScalar(u8, bytes, '(') orelse return error.GroupInspectionFailed;
    const close = std.mem.lastIndexOfScalar(u8, bytes, ')') orelse return error.GroupInspectionFailed;
    if (close <= open or close + 2 >= bytes.len or bytes[close + 1] != ' ') return error.GroupInspectionFailed;
    const observed_pid = std.fmt.parseInt(i32, std.mem.trim(u8, bytes[0..open], " "), 10) catch return error.GroupInspectionFailed;
    if (observed_pid != expected_pid) return error.GroupInspectionFailed;
    var fields = std.mem.tokenizeScalar(u8, bytes[close + 2 ..], ' ');
    const state = fields.next() orelse return error.GroupInspectionFailed;
    if (state.len != 1) return error.GroupInspectionFailed;
    var process_group: ?i32 = null;
    var resident_pages: ?u64 = null;
    var index: usize = 0;
    while (fields.next()) |field| : (index += 1) {
        if (index == 1) process_group = std.fmt.parseInt(i32, field, 10) catch return error.GroupInspectionFailed;
        if (index == 20) {
            const value = std.fmt.parseInt(i64, field, 10) catch return error.GroupInspectionFailed;
            if (value < 0) return error.GroupInspectionFailed;
            resident_pages = @intCast(value);
            break;
        }
    }
    return .{ .state = state[0], .process_group = process_group orelse return error.GroupInspectionFailed, .resident_pages = resident_pages orelse return error.GroupInspectionFailed };
}

fn linuxProcStat(proc_fd: c_int, pid: i32) !?LinuxProcStat {
    var path_buffer: [32]u8 = undefined;
    const path = try std.fmt.bufPrintZ(&path_buffer, "{d}/stat", .{pid});
    const fd = c.openat(proc_fd, path.ptr, c.O_RDONLY | c.O_CLOEXEC);
    if (fd < 0) {
        const problem = std.c.errno(@as(c_int, -1));
        if (problem == .NOENT or problem == .SRCH) return null;
        return error.GroupInspectionFailed;
    }
    defer _ = c.close(fd);
    var bytes: [4096]u8 = undefined;
    var length: usize = 0;
    while (length < bytes.len) {
        const count = c.read(fd, @ptrCast(bytes[length..].ptr), bytes.len - length);
        if (count == 0) break;
        if (count < 0) {
            if (std.c.errno(@as(c_int, -1)) == .INTR) continue;
            if (std.c.errno(@as(c_int, -1)) == .NOENT or std.c.errno(@as(c_int, -1)) == .SRCH) return null;
            return error.GroupInspectionFailed;
        }
        length += @intCast(count);
    }
    if (length == bytes.len) return error.GroupInspectionFailed;
    return try parseLinuxProcStat(bytes[0..length], pid);
}

fn linuxGroupUsage(pgid: i32, terminal_leader: bool) !Usage {
    const directory = c.opendir("/proc") orelse return error.GroupInspectionFailed;
    defer _ = c.closedir(directory);
    const proc_fd = c.dirfd(directory);
    const page_size = c.sysconf(c._SC_PAGESIZE);
    if (page_size <= 0) return error.GroupInspectionFailed;
    var usage: Usage = .{};
    var leader_present = false;
    while (true) {
        std.c._errno().* = 0;
        const entry = c.readdir(directory) orelse {
            if (std.c.errno(@as(c_int, -1)) != .SUCCESS) return error.GroupInspectionFailed;
            break;
        };
        const name = std.mem.sliceTo(@as([*:0]const u8, @ptrCast(&entry.*.d_name)), 0);
        const pid = std.fmt.parseInt(i32, name, 10) catch continue;
        if (pid <= 0) continue;
        const status = try linuxProcStat(proc_fd, pid) orelse continue;
        if (status.process_group != pgid) continue;
        if (pid == pgid) leader_present = true;
        if (pid == pgid and terminal_leader) continue;
        if (status.state == 'Z' or status.state == 'X' or status.state == 'x') {
            // waitid and procfs are separate observations. A leader can become
            // a zombie just after waitid reports no exit; it remains unreaped
            // and identity-pinned, so exclude it from live usage and let the
            // next waitid pass establish terminal ownership before cleanup.
            continue;
        }
        usage.processes += 1;
        usage.resident_bytes = try std.math.add(u64, usage.resident_bytes, try std.math.mul(u64, status.resident_pages, @intCast(page_size)));
    }
    if (!leader_present) return error.GroupInspectionFailed;
    return usage;
}

fn groupUsageUsing(pgid: i32, terminal_leader: bool, list: ListProcesses) !Usage {
    var pids: [129]c_int = @splat(0);
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

test "Linux proc stat projection handles parentheses and stable field positions" {
    const resident_prefix = "420 (worker ) demo) S 1 420 420 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 77 8192 ";
    const parsed = try parseLinuxProcStat(resident_prefix ++ "5 0\n", 420);
    try std.testing.expectEqual(@as(u8, 'S'), parsed.state);
    try std.testing.expectEqual(@as(i32, 420), parsed.process_group);
    try std.testing.expectEqual(@as(u64, 5), parsed.resident_pages);

    const malformed_rows = [_][]const u8{
        "420 worker) S 1 420 420 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 77 8192 5 0", // missing command opener
        "420 (worker S 1 420 420 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 77 8192 5 0", // missing command closer
        "420 )(worker S 1 420 420 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 77 8192 5 0", // closer precedes opener
        "420 (worker)", // no state separator or fields
        "420 (worker)X S 1 420 420 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 77 8192 5 0", // invalid separator
        "not-a-pid (worker) S 1 420 420 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 77 8192 5 0",
        "421 (worker) S 1 420 420 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 77 8192 5 0", // wrong PID
        "420 (worker)  ", // missing state
        "420 (worker) RUN 1 420 420 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 77 8192 5 0", // multi-byte state
        "420 (worker) S 1 not-a-pgid 420 0 -1 0 0 0 0 0 0 0 0 20 0 1 0 77 8192 5 0",
        "420 (worker) S 1", // missing process group
        resident_prefix ++ "not-pages 0",
        resident_prefix ++ "-1 0", // negative resident pages
        resident_prefix, // missing resident pages
    };
    for (malformed_rows) |row| {
        try std.testing.expectError(error.GroupInspectionFailed, parseLinuxProcStat(row, 420));
    }
}

const Capture = struct {
    list: std.ArrayList(u8) = .empty,
    quota: usize,
    preview: usize,
    sink: ?std.Io.File,
    observed: u64 = 0,
    retained: usize = 0,
    retained_known: bool = true,
    open: bool = true,

    fn init(allocator: std.mem.Allocator, quota: usize, preview: usize, sink: ?std.Io.File) !Capture {
        var self: Capture = .{ .quota = quota, .preview = @min(quota, preview), .sink = sink };
        try self.list.ensureTotalCapacity(allocator, self.preview);
        return self;
    }

    fn read(self: *Capture, io: std.Io, fd: c_int) !void {
        var buffer: [8192]u8 = undefined;
        // One turn observes at most one byte beyond remaining execution quota.
        // Keep the permitted prefix before reporting that observed excess.
        const rc = c.read(fd, &buffer, @min(buffer.len, self.quota - self.retained + 1));
        if (rc == 0) {
            self.open = false;
            return;
        }
        if (rc < 0) {
            const code = std.c.errno(rc);
            if (code == .AGAIN or code == .INTR) return;
            return error.CaptureFailed;
        }
        const size: usize = @intCast(rc);
        self.observed += size;
        const keep = @min(size, self.quota - self.retained);
        if (self.sink) |file| file.writePositionalAll(io, buffer[0..keep], self.retained) catch {
            self.retained_known = false;
            return error.LogWriteFailed;
        };
        self.retained += keep;
        const excerpt = @min(keep, self.preview - self.list.items.len);
        self.list.appendSliceAssumeCapacity(buffer[0..excerpt]);
        if (size > keep) return error.OutputLimit;
    }
};

// Foreground no-child components share the same exclusive process signal owner.
// The inferred lease type stays internal; callers cannot install another bridge.
pub fn beginSamplingSignals() !SignalBridge {
    return SignalBridge.install();
}
pub fn samplingSignal() u32 {
    return pending_signal.load(.monotonic);
}
pub fn restoreSamplingSignals(lease: *SignalBridge) !u32 {
    return lease.restore();
}
