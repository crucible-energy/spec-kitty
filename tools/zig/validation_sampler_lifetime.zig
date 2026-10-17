//! Check-owned native sampler lifetime. A stored PID is data, never authority.
//! Worker protocol support does not qualify a Linux command/descendant backend.
const std = @import("std");
const builtin = @import("builtin");
const sampler = @import("validation_memory_sampler.zig");
const process = @import("validation_process_darwin.zig");
const c = @cImport({
    @cDefine("_GNU_SOURCE", "1");
    @cInclude("sys/socket.h");
    @cInclude("sys/un.h");
    @cInclude("unistd.h");
    @cInclude("fcntl.h");
    @cInclude("poll.h");
});
const Allocator = std.mem.Allocator;
const max_frame = 4096;

fn now(io: std.Io) i96 {
    return std.Io.Clock.boot.now(io).nanoseconds;
}
fn within(io: std.Io, deadline: i96) !void {
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
    if (process.samplingSignal() != 0) return error.Cancelled;
}
fn pause(io: std.Io, fd: c_int, events: c_short, deadline: i96) !void {
    try within(io, deadline);
    var descriptor: c.struct_pollfd = .{ .fd = fd, .events = events, .revents = 0 };
    const milliseconds: c_int = @intCast(@min(5, @max(0, @divTrunc(deadline - now(io), std.time.ns_per_ms))));
    if (c.poll(&descriptor, 1, milliseconds) < 0 and std.c.errno(@as(c_int, -1)) != .INTR) return error.SamplerProtocolRefused;
}

const Reader = struct {
    bytes: [max_frame + 1]u8 = undefined,
    length: usize = 0,

    fn read(self: *Reader, fd: c_int) !?[]const u8 {
        const count = c.recv(fd, @ptrCast(self.bytes[self.length..].ptr), self.bytes.len - self.length, 0);
        if (count < 0) {
            const problem = std.c.errno(@as(c_int, -1));
            if (problem == .AGAIN or problem == .INTR) return null;
            return error.SamplerProtocolRefused;
        }
        if (count == 0) return error.SamplerOwnerLost;
        self.length += @intCast(count);
        if (self.length > max_frame) return error.SamplerProtocolRefused;
        if (std.mem.indexOfScalar(u8, self.bytes[0..self.length], '\n')) |end| {
            // No valid peer sends a second frame before this one is consumed.
            if (end == 0 or end + 1 != self.length) return error.SamplerProtocolRefused;
            self.length = 0;
            return self.bytes[0..end];
        }
        return null;
    }

    fn wait(self: *Reader, io: std.Io, fd: c_int, deadline: i96) ![]const u8 {
        while (true) {
            try within(io, deadline);
            if (try self.read(fd)) |bytes| return bytes;
            try pause(io, fd, c.POLLIN, deadline);
        }
    }
};

fn frame(comptime T: type, a: Allocator, raw: []const u8) !T {
    // Bound nesting before allocating the JSON value. This is a protocol-only
    // guard; JSON validity and escape semantics remain with std.json.
    var depth: usize = 0;
    var string = false;
    var escaped = false;
    for (raw) |byte| {
        if (string) {
            if (escaped) {
                escaped = false;
            } else if (byte == '\\') {
                escaped = true;
            } else if (byte == '"') string = false;
        } else if (byte == '"') {
            string = true;
        } else if (byte == '{' or byte == '[') {
            depth += 1;
            if (depth > 16) return error.SamplerProtocolRefused;
        } else if (byte == '}' or byte == ']') {
            if (depth == 0) return error.SamplerProtocolRefused;
            depth -= 1;
        }
    }
    const value = (std.json.parseFromSlice(std.json.Value, a, raw, .{ .duplicate_field_behavior = .@"error", .allocate = .alloc_always }) catch return error.SamplerProtocolRefused).value;
    const fields = std.meta.fields(T);
    if (value != .object or value.object.count() != fields.len) return error.SamplerProtocolRefused;
    inline for (fields) |field| {
        const actual = value.object.get(field.name) orelse return error.SamplerProtocolRefused;
        if (field.type == []const u8) {
            if (actual != .string) return error.SamplerProtocolRefused;
        } else if (actual != .integer) return error.SamplerProtocolRefused;
    }
    return (std.json.parseFromValue(T, a, value, .{}) catch return error.SamplerProtocolRefused).value;
}

fn send(init: std.process.Init, fd: c_int, value: anytype, deadline: i96) !void {
    const a = init.arena.allocator();
    const raw = try std.json.Stringify.valueAlloc(a, value, .{});
    if (raw.len + 1 > max_frame) return error.SamplerProtocolRefused;
    const bytes = try std.fmt.allocPrint(a, "{s}\n", .{raw});
    var offset: usize = 0;
    while (offset < bytes.len) {
        try within(init.io, deadline);
        const flags = if (builtin.os.tag == .linux) c.MSG_NOSIGNAL else 0;
        const count = c.send(fd, @ptrCast(bytes[offset..].ptr), bytes.len - offset, flags);
        if (count < 0) {
            const problem = std.c.errno(@as(c_int, -1));
            if (problem == .INTR) continue;
            if (problem == .AGAIN) {
                try pause(init.io, fd, c.POLLOUT, deadline);
                continue;
            }
            return error.SamplerProtocolRefused;
        }
        if (count == 0) return error.SamplerProtocolRefused;
        offset += @intCast(count);
    }
}

fn workerChannel() !void {
    try sampler.verifyWorkerChannel();
    var address: c.struct_sockaddr_un = std.mem.zeroes(c.struct_sockaddr_un);
    var length: c.socklen_t = @sizeOf(@TypeOf(address));
    if (c.getpeername(0, @ptrCast(&address), &length) != 0 or address.sun_family != c.AF_UNIX) return error.SamplerOwnerRequired;
    for ([_]c_int{ 0, 1 }) |fd| {
        const flags = c.fcntl(fd, c.F_GETFL);
        if (flags < 0 or c.fcntl(fd, c.F_SETFL, flags | c.O_NONBLOCK) != 0) return error.SamplerProtocolRefused;
        if (builtin.os.tag == .macos) {
            const enabled: c_int = 1;
            if (c.setsockopt(fd, c.SOL_SOCKET, c.SO_NOSIGPIPE, &enabled, @sizeOf(@TypeOf(enabled))) != 0) return error.SamplerProtocolRefused;
        }
    }
}

const Start = struct { schema_version: u8, command: []const u8, owner_pid: i32, deadline_boot_ns: []const u8 };
const Stop = struct { schema_version: u8, command: []const u8 };
const Acknowledgement = struct {
    schema_version: u8 = 1,
    event: []const u8,
    pid: i32,
    parent_pid: i32,
    attempts: u32,
    samples: u32,
    state_sha256: []const u8,
    state_metadata_sha256: []const u8,
    directory_identity_sha256: []const u8,
    parent_identity_sha256: []const u8,
};

pub const Outcome = struct {
    pid: i32,
    attempts: u32,
    samples: u32,
    ready_attempts: u32,
    stopped_attempts: u32,
    exit_code: ?u8,
    leader_reaped: bool,
    forced: bool,
    max_sampled_processes: usize,
    max_sampled_resident_bytes: u64,
    commitment: sampler.OwnedSampling.Commitment,
};

fn digestText(value: []const u8) bool {
    if (value.len != 64) return false;
    for (value) |byte| if (!((byte >= '0' and byte <= '9') or (byte >= 'a' and byte <= 'f'))) return false;
    return true;
}

/// Parent-side owner for the one declaration-bound worker. The child remains
/// an unreaped direct child across each ordinary command group and is always
/// stopped and reaped before the recipe result can be accepted.
pub const Supervisor = struct {
    io: std.Io,
    fd: c_int,
    identity: process.DirectChild,
    reader: Reader = .{},
    deadline: i96,
    cleanup_ms: u32,
    attempts: u32 = 0,
    samples: u32 = 0,
    max_sampled_processes: usize = 0,
    max_sampled_resident_bytes: u64 = 0,
    forced: bool = false,
    active: bool = true,
    initial: Acknowledgement,
    final: ?Acknowledgement = null,

    pub fn start(init: std.process.Init, argv: []const []const u8, cwd: []const u8, environment: *const std.process.Environ.Map, deadline: i96, cleanup_ms: u32) !Supervisor {
        if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
        try within(init.io, deadline);
        var pair: [2]c_int = undefined;
        if (c.socketpair(c.AF_UNIX, c.SOCK_STREAM, 0, &pair) != 0) return error.SamplerProtocolRefused;
        var close_parent = true;
        var close_child = true;
        defer {
            if (close_parent) _ = c.close(pair[0]);
            if (close_child) _ = c.close(pair[1]);
        }
        for (&pair) |*fd| {
            if (fd.* <= 2) {
                const duplicate = c.fcntl(fd.*, c.F_DUPFD_CLOEXEC, @as(c_int, 3));
                if (duplicate < 0) return error.SamplerProtocolRefused;
                _ = c.close(fd.*);
                fd.* = duplicate;
            } else {
                const descriptor_flags = c.fcntl(fd.*, c.F_GETFD);
                if (descriptor_flags < 0 or c.fcntl(fd.*, c.F_SETFD, descriptor_flags | c.FD_CLOEXEC) != 0) return error.SamplerProtocolRefused;
            }
        }
        const status_flags = c.fcntl(pair[0], c.F_GETFL);
        if (status_flags < 0 or c.fcntl(pair[0], c.F_SETFL, status_flags | c.O_NONBLOCK) != 0) return error.SamplerProtocolRefused;
        const child_file: std.Io.File = .{ .handle = pair[1], .flags = .{ .nonblocking = false } };
        var child = if (builtin.os.tag == .linux)
            try process.spawnSamplerWorkerLinux(init.arena.allocator(), init.io, argv, cwd, environment, pair[1], deadline, cleanup_ms)
        else
            try std.process.spawn(init.io, .{ .argv = argv, .cwd = .{ .path = cwd }, .environ_map = environment, .stdin = .{ .file = child_file }, .stdout = .{ .file = child_file }, .stderr = .inherit });
        const pid = child.id orelse {
            child.kill(init.io);
            return error.SamplerOwnerLost;
        };
        const identity = process.DirectChild.init(pid) catch |problem| {
            child.kill(init.io);
            return problem;
        };
        var self: Supervisor = .{ .io = init.io, .fd = pair[0], .identity = identity, .deadline = deadline, .cleanup_ms = cleanup_ms, .initial = undefined };
        child.id = null;
        close_parent = false;
        close_child = false;
        errdefer self.dispose(init.io) catch {};
        if (c.close(pair[1]) != 0) return error.SamplerProtocolRefused;
        const deadline_text = try std.fmt.allocPrint(init.arena.allocator(), "{d}", .{deadline});
        try send(init, self.fd, .{ .schema_version = 1, .command = "start", .owner_pid = c.getpid(), .deadline_boot_ns = deadline_text }, deadline);
        self.initial = try frame(Acknowledgement, init.arena.allocator(), try self.reader.wait(init.io, self.fd, deadline));
        try self.validateAck(self.initial, "ready", c.getpid());
        if (self.initial.attempts != 1 or self.initial.samples != 1) return error.SamplerProtocolRefused;
        self.attempts = self.initial.attempts;
        self.samples = self.initial.samples;
        const usage = try self.identity.usage();
        self.max_sampled_processes = usage.processes;
        self.max_sampled_resident_bytes = usage.resident_bytes;
        return self;
    }

    fn validateAck(self: *Supervisor, value: Acknowledgement, event: []const u8, parent_pid: i32) !void {
        if (value.schema_version != 1 or !std.mem.eql(u8, value.event, event) or value.pid != self.identity.pid() or value.parent_pid != parent_pid or value.attempts == 0 or value.samples == 0 or !digestText(value.state_sha256) or !digestText(value.state_metadata_sha256) or !digestText(value.directory_identity_sha256) or !digestText(value.parent_identity_sha256)) return error.SamplerProtocolRefused;
    }

    pub fn poll(self: *Supervisor, in_flight: process.InFlight, limits: process.Limits) ?process.Failure {
        if (!self.active) return .ownership_lost;
        if (now(self.io) >= self.deadline) return .wall_timeout;
        if (process.samplingSignal() != 0) return .cancelled;
        const terminal = self.identity.observe() catch return .inspection_failed;
        if (terminal) return .ownership_lost;
        const worker = self.identity.usage() catch return .inspection_failed;
        const processes = std.math.add(usize, worker.processes, in_flight.sampled_processes) catch return .process_limit;
        const resident = std.math.add(u64, worker.resident_bytes, in_flight.sampled_resident_bytes) catch return .resident_limit;
        self.max_sampled_processes = @max(self.max_sampled_processes, processes);
        self.max_sampled_resident_bytes = @max(self.max_sampled_resident_bytes, resident);
        if (processes > limits.processes) return .process_limit;
        if (resident > limits.resident_bytes) return .resident_limit;
        return null;
    }

    pub fn stop(self: *Supervisor, init: std.process.Init) !Outcome {
        if (!self.active) return error.SamplerOwnerLost;
        try send(init, self.fd, .{ .schema_version = 1, .command = "stop" }, self.deadline);
        const received = try frame(Acknowledgement, init.arena.allocator(), try self.reader.wait(init.io, self.fd, self.deadline));
        try self.validateAck(received, "stopped", c.getpid());
        if (received.attempts < self.initial.attempts + 1 or received.samples < self.initial.samples + 1) return error.SamplerProtocolRefused;
        self.attempts = received.attempts;
        self.samples = received.samples;
        self.final = received;
        while (true) {
            if (try self.identity.observe()) {
                if (!try self.identity.reap()) return error.SamplerIdentityUnknown;
                self.active = false;
                if (c.close(self.fd) != 0) return error.SamplerProtocolRefused;
                const value = self.final.?;
                return .{ .pid = value.pid, .attempts = value.attempts, .samples = value.samples, .ready_attempts = self.initial.attempts, .stopped_attempts = value.attempts, .exit_code = self.identity.exitCode(), .leader_reaped = self.identity.reaped(), .forced = self.forced, .max_sampled_processes = self.max_sampled_processes, .max_sampled_resident_bytes = self.max_sampled_resident_bytes, .commitment = .{ .state_sha256 = value.state_sha256, .state_metadata_sha256 = value.state_metadata_sha256, .directory_identity_sha256 = value.directory_identity_sha256, .parent_identity_sha256 = value.parent_identity_sha256 } };
            }
            try pause(init.io, self.fd, c.POLLIN, self.deadline);
        }
    }

    pub fn dispose(self: *Supervisor, io: std.Io) !void {
        if (!self.active) return;
        const cleanup_deadline = now(io) + @as(i96, self.cleanup_ms) * std.time.ns_per_ms;
        self.identity.signal(true) catch {};
        while (now(io) < cleanup_deadline) {
            const terminal = self.identity.observe() catch break;
            if (terminal) {
                if (!try self.identity.reap()) return error.SamplerIdentityUnknown;
                self.active = false;
                if (c.close(self.fd) != 0) return error.SamplerProtocolRefused;
                return;
            }
            _ = c.poll(null, 0, 1);
        }
        return error.SamplerCleanupIncomplete;
    }
};

fn deadlineValue(raw: []const u8, io: std.Io) !i96 {
    if (raw.len == 0 or raw.len > 29) return error.SamplerProtocolRefused;
    for (raw) |byte| if (byte < '0' or byte > '9') return error.SamplerProtocolRefused;
    const value = std.fmt.parseInt(i96, raw, 10) catch return error.SamplerProtocolRefused;
    if (value <= 0 or value > now(io) + 3_600_000 * std.time.ns_per_ms) return error.SamplerProtocolRefused;
    try within(io, value);
    return value;
}

fn acknowledgement(event: []const u8, observed: sampler.OwnedSampling.Observation, parent: i32, sampling: *sampler.OwnedSampling) !Acknowledgement {
    const committed = try sampling.commitment();
    return .{ .event = event, .pid = observed.pid, .parent_pid = parent, .attempts = observed.attempts, .samples = observed.samples, .state_sha256 = committed.state_sha256, .state_metadata_sha256 = committed.state_metadata_sha256, .directory_identity_sha256 = committed.directory_identity_sha256, .parent_identity_sha256 = committed.parent_identity_sha256 };
}

fn work(init: std.process.Init, path: []const u8, owned: *?sampler.OwnedSampling, original_deadline: *i96) !Acknowledgement {
    const a = init.arena.allocator();
    var reader: Reader = .{};
    const start = try frame(Start, a, try reader.wait(init.io, 0, original_deadline.*));
    if (start.schema_version != 1 or !std.mem.eql(u8, start.command, "start") or start.owner_pid < 1 or start.owner_pid != c.getppid()) return error.SamplerOwnerRequired;
    original_deadline.* = try deadlineValue(start.deadline_boot_ns, init.io);
    // SDK spawn leaves this worker outside each ordinary command's group. A
    // source-closed worker can establish its own session without losing its
    // parent's unreaped direct-child identity.
    if (c.getsid(0) != c.getpid() and c.setsid() < 0) return error.SamplerStartupFailed;
    if (c.getsid(0) != c.getpid() or c.getpgrp() != c.getpid()) return error.SamplerStartupFailed;
    // Awake is read before the later boot observation, so this conversion is
    // conservative. The parent also retains and enforces the boot deadline.
    const awake = std.Io.Clock.awake.now(init.io).nanoseconds;
    const remaining = original_deadline.* - now(init.io);
    if (remaining <= 0) return error.OperationDeadlineExceeded;
    owned.* = try sampler.OwnedSampling.begin(init, path, awake + remaining);
    const first = try owned.*.?.take();
    try send(init, 1, try acknowledgement("ready", first, start.owner_pid, &owned.*.?), original_deadline.*);
    var wake = now(init.io) + @as(i96, owned.*.?.intervalMilliseconds()) * std.time.ns_per_ms;
    while (true) {
        try within(init.io, original_deadline.*);
        if (c.getppid() != start.owner_pid) return error.SamplerOwnerLost;
        if (try reader.read(0)) |raw| {
            const stop = try frame(Stop, a, raw);
            if (stop.schema_version != 1 or !std.mem.eql(u8, stop.command, "stop")) return error.SamplerProtocolRefused;
            return acknowledgement("stopped", try owned.*.?.take(), start.owner_pid, &owned.*.?);
        }
        if (now(init.io) >= wake) {
            _ = try owned.*.?.take();
            wake = now(init.io) + @as(i96, owned.*.?.intervalMilliseconds()) * std.time.ns_per_ms;
        }
        try pause(init.io, 0, c.POLLIN, original_deadline.*);
    }
}

pub fn workerCommand(init: std.process.Init, path: []const u8) !u8 {
    if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
    try workerChannel();
    var lease = try process.beginSamplingSignals();
    var owned: ?sampler.OwnedSampling = null;
    var deadline = now(init.io) + 3_600_000 * std.time.ns_per_ms;
    var primary: ?anyerror = null;
    const stopped: ?Acknowledgement = work(init, path, &owned, &deadline) catch |problem| blk: {
        primary = problem;
        break :blk @as(?Acknowledgement, null);
    };
    var disposition: ?anyerror = null;
    if (owned) |*sampling| sampling.finish() catch |problem| {
        disposition = problem;
    };
    const received = try process.restoreSamplingSignals(&lease);
    if (disposition) |problem| return problem;
    if (primary) |problem| return problem;
    if (received != 0) return error.Cancelled;
    try send(init, 1, stopped.?, deadline);
    try within(init.io, deadline);
    return 0;
}
