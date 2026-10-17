//! Finite foreground state producer adapted from scripts/ci/memory_sampler.py.
//! The maintained Python reader/report remains authority; gates are unchanged.
//! This bounded ASCII/finite-integer adapter deliberately refuses unsafe input,
//! cancellation and deadlines. It neither detaches nor starts/signals a child.
//! Linux foreground support is separate from child/backend and cgroup qualification.
const std = @import("std");
const builtin = @import("builtin");
const owner = @import("validation_process_darwin.zig");
const c = @cImport({
    @cInclude("sys/stat.h");
    @cInclude("unistd.h");
    @cInclude("fcntl.h");
    @cInclude("stdio.h");
});
const linux_c = if (builtin.os.tag == .linux) @cImport({
    @cInclude("sys/vfs.h");
    @cInclude("linux/magic.h");
}) else struct {};
const Allocator = std.mem.Allocator;
const max_bytes = 65536;
const Request = struct { schema_version: u8, destination: []const u8, proc_root: []const u8, interval_ms: u32, max_samples: u32, wall_ms: u32 };
const State = struct { baseline_bytes: i128 = 0, elapsed_seconds: f64 = 0, peak_bytes: i128 = 0, pid: i32, samples: u32 = 0, source: enum { unavailable, meminfo } = .unavailable };
const Usage = struct { total: i128, available: i128 };
// This is a sampler value projection, never an ABI record passed to C.
// Zig 0.16's C translator cannot represent musl timespec's zero-width bitfields;
// its own Linux I/O uses the target-owned Statx layout instead of struct stat.
const LinuxStatx = std.os.linux.Statx;
const Stat = if (builtin.os.tag == .linux) struct {
    st_dev: struct {
        major: @FieldType(LinuxStatx, "dev_major"),
        minor: @FieldType(LinuxStatx, "dev_minor"),
    },
    st_ino: @FieldType(LinuxStatx, "ino"),
    st_mode: @FieldType(LinuxStatx, "mode"),
    st_nlink: @FieldType(LinuxStatx, "nlink"),
    st_uid: @FieldType(LinuxStatx, "uid"),
    st_size: @FieldType(LinuxStatx, "size"),
    st_mtime: @FieldType(LinuxStatx, "mtime"),
    st_ctime: @FieldType(LinuxStatx, "ctime"),
} else c.struct_stat;
fn linuxStat(fd: c_int, name: [*:0]const u8, flags: u32, output: *Stat) !c_int {
    const wanted: std.os.linux.STATX = .{ .TYPE = true, .MODE = true, .NLINK = true, .UID = true, .INO = true, .SIZE = true, .MTIME = true, .CTIME = true };
    var observed = std.mem.zeroes(LinuxStatx);
    const result = std.c.statx(fd, name, flags, wanted, &observed);
    if (result != 0) return result; // Preserve libc's return and errno unchanged.
    const bits: u32 = @bitCast(wanted);
    if (@as(u32, @bitCast(observed.mask)) & bits != bits) return error.SamplerPathObservationFailed;
    output.* = .{
        .st_dev = .{ .major = observed.dev_major, .minor = observed.dev_minor },
        .st_ino = observed.ino,
        .st_mode = observed.mode,
        .st_nlink = observed.nlink,
        .st_uid = observed.uid,
        .st_size = observed.size,
        .st_mtime = observed.mtime,
        .st_ctime = observed.ctime,
    };
    return 0;
}
fn descriptorStat(fd: c_int, output: *Stat) !c_int {
    if (builtin.os.tag == .linux) return linuxStat(fd, "", std.os.linux.AT.EMPTY_PATH, output);
    return c.fstat(fd, output);
}
fn relativeStat(fd: c_int, name: [*:0]const u8, output: *Stat, flags: c_int) !c_int {
    if (builtin.os.tag == .linux) return linuxStat(fd, name, @intCast(flags), output);
    return c.fstatat(fd, name, output, flags);
}
fn pathnameStat(name: [*:0]const u8, output: *Stat) !c_int {
    if (builtin.os.tag == .linux) return linuxStat(c.AT_FDCWD, name, std.os.linux.AT.SYMLINK_NOFOLLOW, output);
    return c.lstat(name, output);
}
fn now(io: std.Io) i96 {
    return std.Io.Clock.awake.now(io).nanoseconds;
}
fn before(io: std.Io, deadline: i96) !void {
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
}
fn same(a: Stat, b: Stat) bool {
    if (builtin.os.tag == .linux) return a.st_dev.major == b.st_dev.major and a.st_dev.minor == b.st_dev.minor and a.st_ino == b.st_ino;
    return a.st_dev == b.st_dev and a.st_ino == b.st_ino;
}
fn regular(value: Stat) bool {
    return value.st_mode & c.S_IFMT == c.S_IFREG;
}
fn pathText(path: []const u8, allow_root: bool) !void {
    if (path.len == 0 or path.len > 4096 or !std.fs.path.isAbsolute(path) or !std.unicode.utf8ValidateSlice(path)) return error.InvalidSamplerPath;
    for (path) |byte| if (byte < 32 or byte == 127) return error.InvalidSamplerPath;
    if (allow_root and std.mem.eql(u8, path, "/")) return;
    var parts = std.mem.splitScalar(u8, path[1..], '/');
    while (parts.next()) |part| if (part.len == 0 or std.mem.eql(u8, part, ".") or std.mem.eql(u8, part, "..")) return error.InvalidSamplerPath;
}
fn canonical(io: std.Io, path: []const u8) !void {
    const resolved = try std.Io.Dir.cwd().realPathFileAlloc(io, path, std.heap.page_allocator);
    defer std.heap.page_allocator.free(resolved);
    if (!std.mem.eql(u8, path, resolved)) return error.UnsafeSamplerPath;
}
fn statAt(fd: c_int, name: [*:0]const u8) !?Stat {
    var value: Stat = undefined;
    if (try relativeStat(fd, name, &value, c.AT_SYMLINK_NOFOLLOW) == 0) return value;
    if (std.c.errno(@as(c_int, -1)) == .NOENT) return null;
    return error.SamplerPathObservationFailed;
}
const Directory = struct {
    fd: c_int,
    path: []const u8,
    path_z: [:0]const u8,
    identity: Stat,
    private: bool,
    fn open(a: Allocator, io: std.Io, path: []const u8, private: bool) !Directory {
        try canonical(io, path);
        const path_z = try a.dupeZ(u8, path);
        const fd = c.open(path_z, c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW | c.O_CLOEXEC);
        if (fd < 0) return error.UnsafeSamplerDirectory;
        errdefer _ = c.close(fd);
        var identity: Stat = undefined;
        if (try descriptorStat(fd, &identity) != 0 or identity.st_mode & c.S_IFMT != c.S_IFDIR) return error.UnsafeSamplerDirectory;
        if (private and (identity.st_uid != c.geteuid() or identity.st_mode & 0o7777 != 0o700)) return error.UnsafeSamplerDirectory;
        return .{ .fd = fd, .path = path, .path_z = path_z, .identity = identity, .private = private };
    }
    fn verify(self: Directory, io: std.Io) !void {
        try canonical(io, self.path);
        var path_stat: Stat = undefined;
        var held: Stat = undefined;
        if (try pathnameStat(self.path_z, &path_stat) != 0 or try descriptorStat(self.fd, &held) != 0 or !same(path_stat, self.identity) or !same(held, self.identity) or path_stat.st_mode & c.S_IFMT != c.S_IFDIR) return error.SamplerDirectoryDrift;
        if (self.private and (path_stat.st_uid != c.geteuid() or path_stat.st_mode & 0o7777 != 0o700)) return error.SamplerDirectoryDrift;
    }
    fn close(self: Directory) void {
        _ = c.close(self.fd);
    }
};
// Return null only for ordinary unreadable/missing bytes. Never open an observed
// FIFO/device/symlink, and verify the descriptor after the bounded nonblocking open.
fn readAt(fd: c_int, name: [*:0]const u8, buffer: []u8, unavailable: bool, io: std.Io, deadline: ?i96, observation: ?*InputObservation) !?[]const u8 {
    const initial = try statAt(fd, name);
    if (observation) |record| record.* = .{ .fd = fd, .name = name, .initial = initial };
    const observed = initial orelse {
        if (unavailable) return null;
        return error.SamplerInputUnreadable;
    };
    if (!regular(observed)) return error.UnsafeSamplerInput;
    if (observed.st_size > max_bytes) return error.SamplerInputLimit;
    const file = c.openat(fd, name, c.O_RDONLY | c.O_NONBLOCK | c.O_NOFOLLOW | c.O_CLOEXEC);
    if (file < 0) {
        if (std.c.errno(@as(c_int, -1)) == .LOOP) return error.UnsafeSamplerInput;
        if (unavailable) return null;
        return error.SamplerInputUnreadable;
    }
    defer {
        if (c.close(file) != 0) {
            if (observation) |record| record.close_failed = true;
        }
    }
    var held: Stat = undefined;
    if (try descriptorStat(file, &held) != 0 or !same(observed, held) or !regular(held)) return error.SamplerInputDrift;
    var length: usize = 0;
    while (true) {
        if (deadline) |limit| try before(io, limit);
        const count = c.read(file, @ptrCast(buffer.ptr + length), buffer.len - length);
        if (count < 0) {
            if (std.c.errno(@as(c_int, -1)) == .INTR) continue;
            if (unavailable) return null;
            return error.SamplerInputUnreadable;
        }
        if (count == 0) break;
        length += @intCast(count);
        if (length > max_bytes) return error.SamplerInputLimit;
    }
    if (deadline) |limit| try before(io, limit);
    if (try descriptorStat(file, &held) != 0 or !regular(held) or !same(observed, held)) return error.SamplerInputDrift;
    return buffer[0..length];
}
fn parseRequest(init: std.process.Init, path: []const u8) !Request {
    const a = init.arena.allocator();
    try pathText(path, false);
    try canonical(init.io, path);
    const path_z = try a.dupeZ(u8, path);
    const buffer = try a.alloc(u8, max_bytes + 1);
    const bytes = (try readAt(c.AT_FDCWD, path_z, buffer, false, init.io, null, null)).?;
    return requestBytes(a, bytes);
}
fn requestBytes(a: Allocator, bytes: []const u8) !Request {
    const value = (std.json.parseFromSlice(std.json.Value, a, bytes, .{ .duplicate_field_behavior = .@"error" }) catch return error.InvalidSamplerRequest).value;
    if (value != .object or value.object.count() != 6) return error.InvalidSamplerRequest;
    const keys = [_][]const u8{ "schema_version", "destination", "proc_root", "interval_ms", "max_samples", "wall_ms" };
    for (keys, 0..) |key, index| {
        const field = value.object.get(key) orelse return error.InvalidSamplerRequest;
        if (index == 1 or index == 2) {
            if (field != .string) return error.InvalidSamplerRequest;
        } else if (field != .integer) return error.InvalidSamplerRequest;
    }
    const request = (std.json.parseFromValue(Request, a, value, .{}) catch return error.InvalidSamplerRequest).value;
    if (request.schema_version != 1 or request.interval_ms > 60000 or request.max_samples == 0 or request.max_samples > 10000 or request.wall_ms == 0 or request.wall_ms > 3600000) return error.InvalidSamplerRequest;
    try pathText(request.destination, false);
    try pathText(request.proc_root, true);
    return request;
}
fn space(byte: u8) bool {
    return byte == 32 or (byte >= 9 and byte <= 13) or (byte >= 28 and byte <= 31);
}
fn lineBreak(byte: u8) bool {
    return (byte >= 10 and byte <= 13) or (byte >= 28 and byte <= 30);
}
fn trim(bytes: []const u8) []const u8 {
    var start: usize = 0;
    var end = bytes.len;
    while (start < end and space(bytes[start])) : (start += 1) {}
    while (end > start and space(bytes[end - 1])) : (end -= 1) {}
    return bytes[start..end];
}
fn parseUsage(bytes: []const u8) !?Usage {
    for (bytes) |byte| if (byte > 127) return error.UnsupportedSamplerEncoding;
    var total: ?i128 = null;
    var available: ?i128 = null;
    var position: usize = 0;
    while (position < bytes.len) {
        const start = position;
        while (position < bytes.len and !lineBreak(bytes[position])) : (position += 1) {}
        const line = bytes[start..position];
        if (position < bytes.len) {
            const cr = bytes[position] == 13;
            position += 1;
            if (cr and position < bytes.len and bytes[position] == 10) position += 1;
        }
        const colon = std.mem.indexOfScalar(u8, line, ':') orelse continue;
        const key = trim(line[0..colon]);
        const rest = trim(line[colon + 1 ..]);
        if (rest.len == 0) continue;
        var end: usize = 0;
        while (end < rest.len and !space(rest[end])) : (end += 1) {}
        var digits = true;
        for (rest[0..end]) |byte| digits = digits and byte >= '0' and byte <= '9';
        if (!digits) continue;
        const kib = std.fmt.parseInt(u64, rest[0..end], 10) catch return error.UnsupportedSamplerValue;
        const value = @as(i128, kib) * 1024;
        if (std.mem.eql(u8, key, "MemTotal")) total = value;
        if (std.mem.eql(u8, key, "MemAvailable")) available = value;
    }
    return if (total != null and available != null) .{ .total = total.?, .available = available.? } else null;
}
const Output = struct {
    parent: Directory,
    directory: Directory,
    previous: ?Stat = null,
    previous_bytes: ?[]u8 = null,
    fn create(a: Allocator, io: std.Io, destination: []const u8) !Output {
        const parent_path = std.fs.path.dirname(destination) orelse return error.InvalidSamplerPath;
        const parent = try Directory.open(a, io, parent_path, true);
        errdefer parent.close();
        const leaf = try a.dupeZ(u8, std.fs.path.basename(destination));
        if (try statAt(parent.fd, leaf) != null) return error.SamplerDestinationExists;
        if (c.mkdirat(parent.fd, leaf, 0o700) != 0) return error.SamplerOutputCreateFailed;
        const directory = try Directory.open(a, io, destination, true);
        errdefer directory.close();
        try parent.verify(io);
        return .{ .parent = parent, .directory = directory };
    }
    fn close(self: Output) void {
        if (self.previous_bytes) |bytes| std.heap.page_allocator.free(bytes);
        self.directory.close();
        self.parent.close();
    }
    fn verify(self: Output, io: std.Io, deadline: i96) !void {
        try self.parent.verify(io);
        try self.directory.verify(io);
        const value = try statAt(self.directory.fd, "state.json");
        if (self.previous) |expected| {
            if (value == null or !same(value.?, expected) or !regular(value.?) or value.?.st_nlink != 1 or value.?.st_uid != c.geteuid() or value.?.st_mode & 0o7777 != 0o600) return error.SamplerOutputDrift;
            var buffer: [max_bytes + 1]u8 = undefined;
            const bytes = (try readAt(self.directory.fd, "state.json", &buffer, false, io, deadline, null)).?;
            if (!std.mem.eql(u8, bytes, self.previous_bytes.?)) return error.SamplerOutputDrift;
        } else if (value != null) return error.SamplerOutputDrift;
        if (try statAt(self.directory.fd, "state.tmp") != null) return error.SamplerOutputDrift;
    }
    fn removeTemp(self: Output, identity: Stat) !void {
        const value = (try statAt(self.directory.fd, "state.tmp")) orelse return error.SamplerOutputCustodyUnknown;
        if (!same(value, identity) or !regular(value) or value.st_nlink != 1 or value.st_uid != c.geteuid()) return error.SamplerOutputCustodyUnknown;
        if (c.unlinkat(self.directory.fd, "state.tmp", 0) != 0) return error.SamplerOutputCustodyUnknown;
    }
    fn replace(self: Output, file: c_int, identity: Stat, bytes: []const u8, io: std.Io, deadline: i96, committed: *bool) !Stat {
        var position: usize = 0;
        while (position < bytes.len) {
            try before(io, deadline);
            const count = c.write(file, @ptrCast(bytes.ptr + position), bytes.len - position);
            if (count < 0 and std.c.errno(@as(c_int, -1)) == .INTR) continue;
            if (count <= 0) return error.SamplerOutputWriteFailed;
            position += @intCast(count);
        }
        try self.parent.verify(io);
        try self.directory.verify(io);
        const current = (try statAt(self.directory.fd, "state.tmp")) orelse return error.SamplerOutputCustodyUnknown;
        if (!same(current, identity) or !regular(current) or current.st_nlink != 1 or current.st_mode & 0o7777 != 0o600) return error.SamplerOutputCustodyUnknown;
        const old = try statAt(self.directory.fd, "state.json");
        if (self.previous) |expected| {
            if (old == null or !same(old.?, expected) or old.?.st_nlink != 1 or old.?.st_mode & 0o7777 != 0o600) return error.SamplerOutputDrift;
        } else if (old != null) return error.SamplerOutputDrift;
        try before(io, deadline);
        if (c.renameat(self.directory.fd, "state.tmp", self.directory.fd, "state.json") != 0) return error.SamplerOutputReplaceFailed;
        committed.* = true;
        const final = (try statAt(self.directory.fd, "state.json")) orelse return error.SamplerOutputCustodyUnknown;
        if (!same(final, identity) or !regular(final) or final.st_nlink != 1 or final.st_uid != c.geteuid() or final.st_mode & 0o7777 != 0o600) return error.SamplerOutputCustodyUnknown;
        return final;
    }
    fn write(self: *Output, state: State, io: std.Io, deadline: i96) !void {
        try self.verify(io, deadline);
        const bytes = try std.json.Stringify.valueAlloc(std.heap.page_allocator, state, .{});
        errdefer std.heap.page_allocator.free(bytes);
        const file = c.openat(self.directory.fd, "state.tmp", c.O_WRONLY | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW | c.O_CLOEXEC, @as(c_uint, 0o600));
        if (file < 0) return error.SamplerTemporaryExists;
        defer _ = c.close(file);
        var identity: Stat = undefined;
        if (try descriptorStat(file, &identity) != 0) return error.SamplerOutputCustodyUnknown;
        var committed = false;
        const final = self.replace(file, identity, bytes, io, deadline, &committed) catch |failure| {
            if (committed) return error.SamplerOutputCustodyUnknown;
            try self.removeTemp(identity);
            return failure;
        };
        if (self.previous_bytes) |old| std.heap.page_allocator.free(old);
        self.previous_bytes = bytes;
        self.previous = final;
    }
};
fn sampledState(state: State, usage: Usage, elapsed: f64) State {
    const used = usage.total - usage.available;
    const first = state.samples == 0;
    return .{ .baseline_bytes = if (first) used else state.baseline_bytes, .peak_bytes = if (first) used else @max(state.peak_bytes, used), .samples = state.samples + 1, .elapsed_seconds = elapsed, .source = .meminfo, .pid = state.pid };
}
fn collect(init: std.process.Init, request: Request, proc: Directory, output: *Output, started: i96, cutoff: i96, deadline: i96) !void {
    const buffer = try init.arena.allocator().alloc(u8, max_bytes + 1);
    var state: State = .{ .pid = c.getpid() };
    var attempts: u32 = 0;
    while (attempts < request.max_samples) : (attempts += 1) {
        try before(init.io, cutoff);
        try proc.verify(init.io);
        try before(init.io, cutoff);
        if (try readAt(proc.fd, "meminfo", buffer, true, init.io, cutoff, null)) |bytes| {
            if (try parseUsage(bytes)) |usage| {
                state = sampledState(state, usage, @as(f64, @floatFromInt(now(init.io) - started)) / std.time.ns_per_s);
            }
        }
        try before(init.io, cutoff);
        try output.write(state, init.io, deadline);
        try before(init.io, deadline);
        if (owner.samplingSignal() != 0) return error.Cancelled;
        if (attempts + 1 == request.max_samples) break;
        const wake = @min(cutoff, now(init.io) + @as(i96, request.interval_ms) * std.time.ns_per_ms);
        while (now(init.io) < wake and owner.samplingSignal() == 0) {
            const remaining: i96 = @min(5 * std.time.ns_per_ms, wake - now(init.io));
            if (remaining > 0) try std.Io.sleep(init.io, .fromNanoseconds(remaining), .awake);
        }
    }
}
// Both retained namespaces are inspected on every exit after acquisition. A
// known custody failure outranks the primary sampling error; signal restoration
// is still performed by command before either error escapes to the public CLI.
fn disposition(io: std.Io, proc: Directory, output: Output, deadline: i96) !void {
    var failure: ?anyerror = null;
    proc.verify(io) catch |problem| {
        failure = problem;
    };
    output.verify(io, deadline) catch |problem| {
        if (failure == null) failure = problem;
    };
    if (failure) |problem| return problem;
    try before(io, deadline);
}
fn sample(init: std.process.Init, request: Request) !i96 {
    const a = init.arena.allocator();
    const started = now(init.io);
    const duration = @as(i96, request.wall_ms) * std.time.ns_per_ms;
    const deadline = started + duration;
    const cutoff = deadline - @min(5 * std.time.ns_per_ms, @divTrunc(duration, 4));
    const proc = try Directory.open(a, init.io, request.proc_root, false);
    defer proc.close();
    try before(init.io, cutoff);
    var output = try Output.create(a, init.io, request.destination);
    defer output.close();
    var failure: ?anyerror = null;
    collect(init, request, proc, &output, started, cutoff, deadline) catch |problem| {
        failure = problem;
    };
    try disposition(init.io, proc, output, deadline);
    if (failure) |problem| return problem;
    return deadline;
}
pub fn command(init: std.process.Init, path: []const u8) !u8 {
    if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
    const request = try parseRequest(init, path);
    var lease = try owner.beginSamplingSignals();
    var failure: ?anyerror = null;
    const deadline: ?i96 = sample(init, request) catch |problem| blk: {
        failure = problem;
        break :blk null;
    };
    const received = try owner.restoreSamplingSignals(&lease);
    if (failure) |problem| return problem;
    if (received != 0) return error.Cancelled;
    try before(init.io, deadline.?);
    return 0;
}

/// Sampling resources borrowed by the source-closed worker. The worker's parent
/// owns its process, channel, original work deadline, and normal/forced stop.
/// This value never creates or signals a child and never trusts a stored PID.
pub const OwnedSampling = struct {
    init: std.process.Init,
    inputs: ReportScope,
    request: ?Request = null,
    directories: [3]?Directory = .{ null, null, null },
    observed: [3]bool = .{ false, false, false },
    output: ?Output = null,
    state: State,
    attempts: u32 = 0,
    active: bool = true,

    pub fn begin(init: std.process.Init, path: []const u8, original_deadline: i96) !OwnedSampling {
        if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
        const started = now(init.io);
        var result: OwnedSampling = .{ .init = init, .inputs = .{ .init = init, .started = started, .deadline = original_deadline }, .state = .{ .pid = c.getpid() } };
        result.acquire(path) catch |problem| {
            try result.finish();
            return problem;
        };
        return result;
    }

    fn directory(self: *OwnedSampling, index: usize, path: []const u8, private: bool) !Directory {
        const a = self.init.arena.allocator();
        try self.inputs.check();
        try canonical(self.init.io, path);
        const path_z = try a.dupeZ(u8, path);
        const fd = c.open(path_z, c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW | c.O_CLOEXEC);
        if (fd < 0) return error.UnsafeSamplerDirectory;
        self.directories[index] = .{ .fd = fd, .path = path, .path_z = path_z, .identity = undefined, .private = private };
        var identity: Stat = undefined;
        if (try descriptorStat(fd, &identity) != 0 or identity.st_mode & c.S_IFMT != c.S_IFDIR) return error.UnsafeSamplerDirectory;
        self.directories[index].?.identity = identity;
        self.observed[index] = true;
        if (private and (identity.st_uid != c.geteuid() or identity.st_mode & 0o7777 != 0o700)) return error.UnsafeSamplerDirectory;
        return self.directories[index].?;
    }

    fn acquire(self: *OwnedSampling, path: []const u8) !void {
        const raw = (try self.inputs.read(path, false, false)).?;
        const request = try requestBytes(self.init.arena.allocator(), raw);
        if (request.max_samples < 2) return error.InvalidSamplerLifetime;
        self.request = request;
        self.inputs.deadline = @min(self.inputs.deadline, self.inputs.started + @as(i96, request.wall_ms) * std.time.ns_per_ms);
        _ = try self.directory(0, request.proc_root, false);
        const parent_path = std.fs.path.dirname(request.destination) orelse return error.InvalidSamplerPath;
        const parent = try self.directory(1, parent_path, true);
        const leaf = try self.init.arena.allocator().dupeZ(u8, std.fs.path.basename(request.destination));
        if (try statAt(parent.fd, leaf) != null) return error.SamplerDestinationExists;
        try parent.verify(self.init.io);
        if (c.mkdirat(parent.fd, leaf, 0o700) != 0) return error.SamplerOutputCreateFailed;
        const destination = try self.directory(2, request.destination, true);
        self.output = .{ .parent = parent, .directory = destination };
        try parent.verify(self.init.io);
        try self.inputs.check();
    }

    pub const Observation = struct { pid: i32, attempts: u32, samples: u32 };

    pub const Commitment = struct {
        state_sha256: []const u8,
        state_metadata_sha256: []const u8,
        directory_identity_sha256: []const u8,
        parent_identity_sha256: []const u8,
    };

    // Publication metadata is producer authority. Atomic replacement by the
    // next successful take installs a new authority; an acknowledgement never
    // substitutes a fresh observation for that retained publication.
    fn publication(self: *OwnedSampling) !void {
        const output = self.output orelse return error.SamplerOwnerRequired;
        for ([_]Directory{ output.parent, output.directory }) |directory_entry| {
            try directory_entry.verify(self.init.io);
            const held = try lifetimeDescriptor(directory_entry.fd);
            var named: Stat = undefined;
            if (try pathnameStat(directory_entry.path_z, &named) != 0 or !same(named, directory_entry.identity) or !same(held, directory_entry.identity) or named.st_mode != directory_entry.identity.st_mode or held.st_mode != directory_entry.identity.st_mode or named.st_uid != directory_entry.identity.st_uid or held.st_uid != directory_entry.identity.st_uid) return error.SamplerDirectoryDrift;
        }
        const expected = output.previous orelse return error.SamplerOutputDrift;
        const named = (try statAt(output.directory.fd, "state.json")) orelse return error.SamplerOutputDrift;
        if (!ReportScope.metadata(named, expected)) return error.SamplerOutputDrift;
        const fd = c.openat(output.directory.fd, "state.json", c.O_RDONLY | c.O_NONBLOCK | c.O_NOFOLLOW | c.O_CLOEXEC);
        if (fd < 0) return error.SamplerOutputDrift;
        var primary: ?anyerror = null;
        self.publicationBytes(fd, expected, output.previous_bytes.?) catch |problem| {
            primary = problem;
        };
        // Closing an acquired descriptor is required even when bytes or
        // identity failed; a failed close outranks the primary read failure.
        if (c.close(fd) != 0) return error.SamplerCloseFailed;
        if (primary) |problem| return problem;
        const final = (try statAt(output.directory.fd, "state.json")) orelse return error.SamplerOutputDrift;
        if (!ReportScope.metadata(final, expected) or try statAt(output.directory.fd, "state.tmp") != null) return error.SamplerOutputDrift;
        try output.parent.verify(self.init.io);
        try output.directory.verify(self.init.io);
    }

    fn publicationBytes(self: *OwnedSampling, fd: c_int, expected: Stat, bytes: []const u8) !void {
        if (!ReportScope.metadata(try lifetimeDescriptor(fd), expected)) return error.SamplerOutputDrift;
        var buffer: [max_bytes + 1]u8 = undefined;
        var length: usize = 0;
        while (true) {
            try self.inputs.check();
            const count = c.read(fd, @ptrCast(buffer[length..].ptr), buffer.len - length);
            if (count < 0 and std.c.errno(@as(c_int, -1)) == .INTR) continue;
            if (count < 0) return error.SamplerInputUnreadable;
            if (count == 0) break;
            length += @intCast(count);
            if (length > max_bytes) return error.SamplerInputLimit;
        }
        if (!ReportScope.metadata(try lifetimeDescriptor(fd), expected) or !std.mem.eql(u8, bytes, buffer[0..length])) return error.SamplerOutputDrift;
    }

    pub fn commitment(self: *OwnedSampling) !Commitment {
        if (!self.active) return error.SamplerOwnerRequired;
        try self.publication();
        const output = self.output.?;
        const a = self.init.arena.allocator();
        return .{
            .state_sha256 = try lifetimeDigest(a, output.previous_bytes.?),
            .state_metadata_sha256 = try lifetimeMetadataDigest(a, output.previous.?, true),
            .directory_identity_sha256 = try lifetimeMetadataDigest(a, output.directory.identity, false),
            .parent_identity_sha256 = try lifetimeMetadataDigest(a, output.parent.identity, false),
        };
    }

    pub fn take(self: *OwnedSampling) !Observation {
        if (!self.active or self.request == null or self.output == null) return error.SamplerOwnerRequired;
        try self.inputs.check();
        if (self.attempts >= self.request.?.max_samples) return error.SamplerAttemptLimit;
        self.attempts += 1;
        const proc = self.directories[0].?;
        try proc.verify(self.init.io);
        var buffer: [max_bytes + 1]u8 = undefined;
        if (try readAt(proc.fd, "meminfo", &buffer, true, self.init.io, self.inputs.deadline, null)) |bytes| {
            if (try parseUsage(bytes)) |usage| {
                self.state = sampledState(self.state, usage, @as(f64, @floatFromInt(now(self.init.io) - self.inputs.started)) / std.time.ns_per_s);
            }
        }
        try self.inputs.check();
        try self.output.?.write(self.state, self.init.io, self.inputs.deadline);
        try self.inputs.check();
        return .{ .pid = self.state.pid, .attempts = self.attempts, .samples = self.state.samples };
    }

    pub fn intervalMilliseconds(self: *const OwnedSampling) u32 {
        return self.request.?.interval_ms;
    }

    pub fn deadline(self: *const OwnedSampling) i96 {
        return self.inputs.deadline;
    }

    pub fn finish(self: *OwnedSampling) !void {
        if (!self.active) return error.SamplerOwnerRequired;
        self.active = false;
        var failure: ?anyerror = null;
        for (self.directories, self.observed) |entry, observed| if (entry) |directory_entry| {
            if (!observed) {
                if (failure == null) failure = error.SamplerPathObservationFailed;
            } else directory_entry.verify(self.init.io) catch |problem| {
                if (failure == null) failure = problem;
            };
        };
        if (self.output) |output| {
            if (output.previous != null) self.publication() catch |problem| {
                if (failure == null) failure = problem;
            };
            output.verify(self.init.io, self.inputs.deadline) catch |problem| {
                if (failure == null) failure = problem;
            };
            if (output.previous_bytes) |bytes| std.heap.page_allocator.free(bytes);
        }
        self.inputs.finish() catch |problem| {
            if (failure == null) failure = problem;
        };
        for (self.directories) |entry| if (entry) |directory_entry| {
            if (c.close(directory_entry.fd) != 0 and failure == null) failure = error.SamplerCloseFailed;
        };
        if (failure) |problem| return problem;
        try before(self.init.io, self.inputs.deadline);
    }
};

/// The worker accepts only two aliases of the same owned Unix socket endpoint.
/// Target-owned metadata observation stays shared with the sampler/cgroup code.
pub fn verifyWorkerChannel() !void {
    if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
    var input: Stat = undefined;
    var output: Stat = undefined;
    if (try descriptorStat(0, &input) != 0 or try descriptorStat(1, &output) != 0) return error.SamplerOwnerRequired;
    if (!same(input, output) or input.st_mode & c.S_IFMT != c.S_IFSOCK or output.st_mode & c.S_IFMT != c.S_IFSOCK or input.st_uid != c.geteuid() or output.st_uid != c.geteuid()) return error.SamplerOwnerRequired;
}

// The lifetime owner shares this target-owned metadata projection for its fixed
// logs/summary custody. It owns all opening, mutation, closing, and disposition.
pub const LifetimeMetadata = Stat;
pub fn lifetimeDigest(a: Allocator, bytes: []const u8) ![]const u8 {
    var digest: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(bytes, &digest, .{});
    return a.dupe(u8, &std.fmt.bytesToHex(digest, .lower));
}
pub fn lifetimeMetadataDigest(a: Allocator, value: LifetimeMetadata, file: bool) ![]const u8 {
    const platform = @tagName(builtin.os.tag);
    const first: i128 = if (builtin.os.tag == .linux) value.st_dev.major else value.st_dev;
    const second: i128 = if (builtin.os.tag == .linux) value.st_dev.minor else 0;
    const identity = .{ @as(i128, 1), platform, first, second, @as(i128, value.st_ino), @as(i128, value.st_mode), @as(i128, value.st_uid) };
    const raw = if (file) blk: {
        const modified = if (builtin.os.tag == .linux) value.st_mtime else value.st_mtimespec;
        const changed = if (builtin.os.tag == .linux) value.st_ctime else value.st_ctimespec;
        const modified_seconds = if (builtin.os.tag == .linux) modified.sec else modified.tv_sec;
        const modified_nanoseconds = if (builtin.os.tag == .linux) modified.nsec else modified.tv_nsec;
        const changed_seconds = if (builtin.os.tag == .linux) changed.sec else changed.tv_sec;
        const changed_nanoseconds = if (builtin.os.tag == .linux) changed.nsec else changed.tv_nsec;
        const fields = identity ++ .{ @as(i128, value.st_nlink), @as(i128, value.st_size), @as(i128, modified_seconds), @as(i128, modified_nanoseconds), @as(i128, changed_seconds), @as(i128, changed_nanoseconds) };
        break :blk try std.json.Stringify.valueAlloc(a, fields, .{});
    } else try std.json.Stringify.valueAlloc(a, identity, .{});
    return lifetimeDigest(a, raw);
}
pub fn lifetimeDescriptor(fd: c_int) !LifetimeMetadata {
    var observed: Stat = undefined;
    if (try descriptorStat(fd, &observed) != 0) return error.SamplerPathObservationFailed;
    return observed;
}
pub fn lifetimeEntry(fd: c_int, name: [:0]const u8) !?LifetimeMetadata {
    return statAt(fd, name);
}
pub fn lifetimeSame(left: LifetimeMetadata, right: LifetimeMetadata) bool {
    return same(left, right);
}
pub fn lifetimeEqual(left: LifetimeMetadata, right: LifetimeMetadata) bool {
    return ReportScope.metadata(left, right);
}
pub fn lifetimePath(path: []const u8, allow_root: bool) !void {
    try pathText(path, allow_root);
}
pub fn lifetimeCanonical(io: std.Io, path: []const u8) !void {
    try canonical(io, path);
}

// Cgroup reads observe names as well as held descriptors. Contents of a live
// kernel counter are not reserved; final custody checks cover identity/type.
const InputObservation = struct {
    fd: c_int,
    name: [*:0]const u8,
    initial: ?Stat,
    close_failed: bool = false,
    observed: bool = true,
    fn verify(self: InputObservation) !void {
        if (!self.observed) return;
        const current = try statAt(self.fd, self.name);
        if (self.initial) |initial| {
            const value = current orelse return error.SamplerInputDrift;
            if (!same(initial, value) or initial.st_mode != value.st_mode or initial.st_uid != value.st_uid or initial.st_nlink != value.st_nlink) return error.SamplerInputDrift;
        } else if (current != null) return error.SamplerInputDrift;
    }
};
const CgroupRequest = struct { schema_version: u8, proc_root: []const u8, sys_root: []const u8, wall_ms: u32 };
const CgroupScope = struct {
    init: std.process.Init,
    deadline: i96,
    directories: std.ArrayList(Directory) = .empty,
    descriptors: std.ArrayList(c_int) = .empty,
    inputs: std.ArrayList(InputObservation) = .empty,
    self_alias: ?struct { parent: c_int, target: [:0]const u8 } = null,
    fn observation(self: *CgroupScope, fd: c_int, name: [*:0]const u8) !*InputObservation {
        try self.inputs.appendBounded(.{ .fd = fd, .name = name, .initial = try statAt(fd, name) });
        return &self.inputs.items[self.inputs.items.len - 1];
    }
    fn own(self: *CgroupScope, fd: c_int) !void {
        self.descriptors.appendBounded(fd) catch {
            if (c.close(fd) != 0) return error.CgroupCloseFailed;
            return error.UnsupportedCgroupPath;
        };
    }
    fn root(self: *CgroupScope, path: []const u8) !c_int {
        try before(self.init.io, self.deadline);
        try canonical(self.init.io, path);
        const path_z = try self.init.arena.allocator().dupeZ(u8, path);
        const fd = c.open(path_z, c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW | c.O_CLOEXEC);
        if (fd < 0) return error.UnsafeSamplerDirectory;
        try self.own(fd);
        var identity: Stat = undefined;
        if (try descriptorStat(fd, &identity) != 0 or identity.st_mode & c.S_IFMT != c.S_IFDIR) return error.UnsafeSamplerDirectory;
        try self.directories.appendBounded(.{ .fd = fd, .path = path, .path_z = path_z, .identity = identity, .private = false });
        return fd;
    }
    fn child(self: *CgroupScope, parent: c_int, name: [*:0]const u8) !?c_int {
        try before(self.init.io, self.deadline);
        const record = try self.observation(parent, name);
        const initial = record.initial orelse return null;
        return try self.observedChild(parent, name, initial);
    }
    fn observedChild(self: *CgroupScope, parent: c_int, name: [*:0]const u8, initial: Stat) !c_int {
        try before(self.init.io, self.deadline);
        if (initial.st_mode & c.S_IFMT != c.S_IFDIR) return error.UnsafeSamplerDirectory;
        const fd = c.openat(parent, name, c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW | c.O_CLOEXEC);
        if (fd < 0) return error.UnsafeSamplerDirectory;
        try self.own(fd);
        var held: Stat = undefined;
        if (try descriptorStat(fd, &held) != 0 or !same(initial, held) or held.st_mode & c.S_IFMT != c.S_IFDIR) return error.SamplerDirectoryDrift;
        // Parent/name is revalidated separately; this record checks the held fd.
        try self.directories.appendBounded(.{ .fd = fd, .path = "", .path_z = "", .identity = held, .private = false });
        return fd;
    }
    fn procSelf(self: *CgroupScope, parent: c_int) !?c_int {
        const record = try self.observation(parent, "self");
        const value = record.initial orelse return null;
        if (value.st_mode & c.S_IFMT != c.S_IFLNK) return try self.observedChild(parent, "self", value);
        if (builtin.os.tag != .linux) return error.UnsafeSamplerDirectory;
        if (builtin.os.tag == .linux) {
            var filesystem: linux_c.struct_statfs = undefined;
            if (linux_c.fstatfs(parent, &filesystem) != 0) return error.CgroupFilesystemObservationFailed;
            if (filesystem.f_type != linux_c.PROC_SUPER_MAGIC) return error.UnsafeSamplerDirectory;
            const target = try std.fmt.allocPrintSentinel(self.init.arena.allocator(), "{d}", .{c.getpid()}, 0);
            self.self_alias = .{ .parent = parent, .target = target };
            try self.verifyAlias();
            return self.child(parent, target);
        }
        return error.PlatformUnsupported;
    }
    fn verifyAlias(self: *CgroupScope) !void {
        if (self.self_alias) |alias| {
            var target: [32]u8 = undefined;
            const length = c.readlinkat(alias.parent, "self", &target, target.len);
            if (length < 0) return error.CgroupFilesystemObservationFailed;
            if (length == target.len or !std.mem.eql(u8, target[0..@intCast(length)], alias.target)) return error.SamplerDirectoryDrift;
        }
    }
    fn read(self: *CgroupScope, fd: c_int, name: [*:0]const u8) !?[]const u8 {
        // Reserve a slot before the reader so all observed failures finalize too.
        try self.inputs.appendBounded(.{ .fd = fd, .name = name, .initial = null, .observed = false });
        const record = &self.inputs.items[self.inputs.items.len - 1];
        const buffer = try self.init.arena.allocator().alloc(u8, max_bytes + 1);
        return readAt(fd, name, buffer, true, self.init.io, self.deadline, record);
    }
    fn finish(self: *CgroupScope) !void {
        var failure: ?anyerror = null;
        for (self.directories.items) |directory| {
            if (directory.path.len != 0) {
                directory.verify(self.init.io) catch |problem| {
                    if (failure == null) failure = problem;
                };
            } else {
                var held: Stat = undefined;
                const observed = descriptorStat(directory.fd, &held) catch |problem| blk: {
                    if (failure == null) failure = problem;
                    break :blk @as(c_int, -1);
                };
                if (observed != 0 or !same(held, directory.identity) or held.st_mode & c.S_IFMT != c.S_IFDIR) {
                    if (failure == null) failure = error.SamplerDirectoryDrift;
                }
            }
        }
        for (self.inputs.items) |record| {
            record.verify() catch |problem| {
                if (failure == null) failure = problem;
            };
            if (record.close_failed and failure == null) failure = error.CgroupCloseFailed;
        }
        self.verifyAlias() catch |problem| {
            if (failure == null) failure = problem;
        };
        for (self.descriptors.items) |fd| {
            if (c.close(fd) != 0 and failure == null) failure = error.CgroupCloseFailed;
        }
        if (failure) |problem| return problem;
        try before(self.init.io, self.deadline);
    }
};
fn cgroupRequest(init: std.process.Init, path: []const u8, record: *InputObservation) !CgroupRequest {
    const a = init.arena.allocator();
    try pathText(path, false);
    try canonical(init.io, path);
    const bytes = (try readAt(c.AT_FDCWD, try a.dupeZ(u8, path), try a.alloc(u8, max_bytes + 1), false, init.io, null, record)).?;
    return cgroupRequestBytes(a, bytes);
}
fn cgroupRequestBytes(a: Allocator, bytes: []const u8) !CgroupRequest {
    const value = (std.json.parseFromSlice(std.json.Value, a, bytes, .{ .duplicate_field_behavior = .@"error" }) catch return error.InvalidCgroupRequest).value;
    if (value != .object or value.object.count() != 4) return error.InvalidCgroupRequest;
    for ([_][]const u8{ "schema_version", "proc_root", "sys_root", "wall_ms" }, 0..) |key, index| {
        const field = value.object.get(key) orelse return error.InvalidCgroupRequest;
        if (index == 1 or index == 2) {
            if (field != .string) return error.InvalidCgroupRequest;
        } else if (field != .integer) return error.InvalidCgroupRequest;
    }
    const request = (std.json.parseFromValue(CgroupRequest, a, value, .{}) catch return error.InvalidCgroupRequest).value;
    if (request.schema_version != 1 or request.wall_ms == 0 or request.wall_ms > 3600000) return error.InvalidCgroupRequest;
    try pathText(request.proc_root, true);
    try pathText(request.sys_root, true);
    return request;
}
fn cgroupSuffix(bytes: []const u8) !?[]const u8 {
    for (bytes) |byte| if (byte > 127) return error.UnsupportedCgroupEncoding;
    var position: usize = 0;
    while (position < bytes.len) {
        const start = position;
        while (position < bytes.len and !lineBreak(bytes[position])) : (position += 1) {}
        const line = bytes[start..position];
        if (position < bytes.len) position += 1;
        if (std.mem.startsWith(u8, line, "0::")) return line[3..];
    }
    return null;
}
fn cgroupValue(bytes: []const u8) !?u64 {
    for (bytes) |byte| if (byte > 127) return error.UnsupportedCgroupEncoding;
    const digits = trim(bytes);
    if (digits.len == 0) return null;
    for (digits) |byte| if (byte < '0' or byte > '9') return null;
    if (digits.len > 4300) return error.UnsupportedCgroupValue;
    return std.fmt.parseInt(u64, digits, 10) catch error.UnsupportedCgroupValue;
}
fn cgroupCollect(scope: *CgroupScope, request: CgroupRequest) !?u64 {
    const proc = try scope.root(request.proc_root);
    const sys = try scope.root(request.sys_root);
    const process = (try scope.procSelf(proc)) orelse return null;
    const membership = (try scope.read(process, "cgroup")) orelse return null;
    const suffix = (try cgroupSuffix(membership)) orelse return null;
    // Validate the whole normalized suffix before walking: dotdot wins over any
    // missing earlier component and never falls through to a later unified line.
    var parts_buffer: [64][:0]const u8 = undefined;
    var parts: std.ArrayList([:0]const u8) = .initBuffer(&parts_buffer);
    var iterator = std.mem.splitScalar(u8, suffix, '/');
    var dot_parts = std.mem.splitScalar(u8, suffix, '/');
    while (dot_parts.next()) |part| if (std.mem.eql(u8, part, "..")) return null;
    var length = request.sys_root.len + "/sys/fs/cgroup/memory.peak".len - @as(usize, if (request.sys_root.len == 1) 1 else 0);
    while (iterator.next()) |part| {
        if (std.mem.eql(u8, part, "..")) return null;
        if (part.len == 0 or std.mem.eql(u8, part, ".")) continue;
        if (part.len > 255) return error.UnsupportedCgroupPath;
        for (part) |byte| if (byte < 32 or byte == 127) return error.UnsupportedCgroupPath;
        length += part.len + 1;
        if (length > 4096) return error.UnsupportedCgroupPath;
        parts.appendBounded(try scope.init.arena.allocator().dupeZ(u8, part)) catch return error.UnsupportedCgroupPath;
    }
    if (length > 4096) return error.UnsupportedCgroupPath;
    var directory = sys;
    for ([_][*:0]const u8{ "sys", "fs", "cgroup" }) |part| directory = (try scope.child(directory, part)) orelse return null;
    for (parts.items) |part| directory = (try scope.child(directory, part)) orelse return null;
    return cgroupValue((try scope.read(directory, "memory.peak")) orelse return null);
}
pub fn cgroupCommand(init: std.process.Init, path: []const u8) !u8 {
    if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
    var input: InputObservation = undefined;
    const request = try cgroupRequest(init, path, &input);
    const deadline = now(init.io) + @as(i96, request.wall_ms) * std.time.ns_per_ms;
    // Fixed storage makes disposition available immediately after request
    // acquisition, before any further allocation or signal-owner acquisition.
    var directories: [70]Directory = undefined;
    var descriptors: [70]c_int = undefined;
    var inputs: [74]InputObservation = undefined;
    var scope = CgroupScope{
        .init = init,
        .deadline = deadline,
        .directories = .initBuffer(&directories),
        .descriptors = .initBuffer(&descriptors),
        .inputs = .initBuffer(&inputs),
    };
    scope.inputs.appendAssumeCapacity(input);
    var lease = owner.beginSamplingSignals() catch |problem| {
        const finished = scope.finish();
        // A partially installed lease can itself report failed restoration.
        // Inspect custody regardless, while preserving restoration priority.
        if (problem == error.SignalRestorationFailed) return problem;
        try finished;
        return problem;
    };
    var failure: ?anyerror = null;
    const peak = cgroupCollect(&scope, request) catch |problem| blk: {
        failure = problem;
        break :blk @as(?u64, null);
    };
    var final_failure: ?anyerror = null;
    scope.finish() catch |problem| {
        final_failure = problem;
    };
    const received = try owner.restoreSamplingSignals(&lease);
    // Restoration/custody failures take precedence over primary data failures;
    // the original work deadline is still authoritative after signal restoration.
    if (final_failure) |problem| return problem;
    try before(init.io, deadline);
    if (failure) |problem| return problem;
    if (received != 0) return error.Cancelled;
    const bytes = try cgroupResultBytes(init.arena.allocator(), peak);
    // Zig's optional formatter spells null as null, preserving unmeasured input.
    try std.Io.File.stdout().writeStreamingAll(init.io, bytes);
    try before(init.io, deadline);
    return 0;
}

fn cgroupResultBytes(a: Allocator, peak: ?u64) ![]const u8 {
    return std.fmt.allocPrint(a, "{{\"schema_version\":1,\"source\":\"{s}\",\"peak_bytes\":{?d}}}\n", .{ if (peak != null) "cgroup-v2-memory-peak" else "unavailable", peak });
}

// The renderer reads finalized artifacts. It neither finalizes a running
// sampler nor treats a persisted PID or cgroup JSON as process authority.
const ReportState = struct { baseline: i128 = 0, peak: i128 = 0, samples: i128 = 0, pid: i128 = 0, elapsed: f64 = 0, source: []const u8 = "unavailable" };
const ReportRequest = struct { state_path: []const u8, cgroup_path: ?[]const u8, warn_bytes: u64, error_bytes: u64, wall_ms: u32 };
const ReportInput = struct {
    parent: ?Directory = null,
    parent_observed: bool = false,
    leaf: [:0]const u8,
    initial: ?Stat = null,
    observed: bool = false,
    read_attempted: bool = false,
    raw: ?[]const u8 = null,
    close_failed: bool = false,
};
const ReportScope = struct {
    init: std.process.Init,
    started: i96,
    deadline: i96,
    inputs: [3]ReportInput = undefined,
    count: usize = 0,
    fn check(self: *ReportScope) !void {
        try before(self.init.io, self.deadline);
        if (owner.samplingSignal() != 0) return error.Cancelled;
    }
    fn metadata(a: Stat, b: Stat) bool {
        const times = if (builtin.os.tag == .linux) std.meta.eql(a.st_mtime, b.st_mtime) and std.meta.eql(a.st_ctime, b.st_ctime) else std.meta.eql(a.st_mtimespec, b.st_mtimespec) and std.meta.eql(a.st_ctimespec, b.st_ctimespec);
        return same(a, b) and a.st_mode == b.st_mode and a.st_uid == b.st_uid and a.st_nlink == b.st_nlink and a.st_size == b.st_size and times;
    }
    fn safe(value: Stat) !void {
        if (!regular(value) or value.st_uid != c.geteuid() or value.st_nlink != 1 or value.st_mode & 0o7777 != 0o600) return error.UnsafeSamplerInput;
        if (value.st_size > max_bytes) return error.SamplerInputLimit;
    }
    fn read(self: *ReportScope, path: []const u8, optional: bool, private: bool) !?[]const u8 {
        const a = self.init.arena.allocator();
        try self.check();
        try pathText(path, false);
        const leaf = try a.dupeZ(u8, std.fs.path.basename(path));
        const parent_path = std.fs.path.dirname(path) orelse return error.InvalidSamplerPath;
        if (self.count == self.inputs.len) return error.InvalidReportRequest;
        const item = &self.inputs[self.count];
        self.count += 1;
        item.* = .{ .leaf = leaf };
        try canonical(self.init.io, parent_path);
        const parent_z = try a.dupeZ(u8, parent_path);
        const fd = c.open(parent_z, c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW | c.O_CLOEXEC);
        if (fd < 0) return error.UnsafeSamplerDirectory;
        // Register the descriptor before any identity or ownership check can
        // fail, so even partial acquisition reaches the shared disposition.
        item.parent = .{ .fd = fd, .path = parent_path, .path_z = parent_z, .identity = undefined, .private = false };
        var identity: Stat = undefined;
        if (try descriptorStat(fd, &identity) != 0 or identity.st_mode & c.S_IFMT != c.S_IFDIR) return error.UnsafeSamplerDirectory;
        item.parent.?.identity = identity;
        item.parent_observed = true;
        if (private and (identity.st_uid != c.geteuid() or identity.st_mode & 0o7777 != 0o700)) return error.UnsafeSamplerDirectory;
        item.parent.?.private = private;
        item.initial = try statAt(item.parent.?.fd, item.leaf);
        item.observed = true;
        if (item.initial) |initial| try safe(initial) else {
            if (optional) return null;
            return error.SamplerInputUnreadable;
        }
        var observation: InputObservation = .{ .fd = item.parent.?.fd, .name = item.leaf, .initial = null, .observed = false };
        const buffer = try a.alloc(u8, max_bytes + 1);
        item.read_attempted = true;
        item.raw = readAt(item.parent.?.fd, item.leaf, buffer, optional, self.init.io, self.deadline, &observation) catch |problem| {
            item.close_failed = observation.close_failed;
            return problem;
        };
        item.close_failed = observation.close_failed;
        if (!observation.observed or observation.initial == null or !metadata(item.initial.?, observation.initial.?)) return error.SamplerInputDrift;
        return item.raw;
    }
    fn verify(self: *ReportScope, item: ReportInput) !void {
        const parent = item.parent orelse return;
        if (!item.parent_observed) return error.SamplerPathObservationFailed;
        if (!item.observed) return;
        const current = try statAt(parent.fd, item.leaf);
        if (item.initial) |initial| {
            if (current == null or !metadata(initial, current.?)) return error.SamplerInputDrift;
        } else {
            if (current != null) return error.SamplerInputDrift;
            return;
        }
        if (!item.read_attempted) return;
        var observation: InputObservation = .{ .fd = parent.fd, .name = item.leaf, .initial = null, .observed = false };
        const buffer = try self.init.arena.allocator().alloc(u8, max_bytes + 1);
        const bytes = readAt(parent.fd, item.leaf, buffer, true, self.init.io, self.deadline, &observation) catch |problem| {
            if (observation.close_failed) return error.CgroupCloseFailed;
            return problem;
        };
        if (observation.close_failed) return error.CgroupCloseFailed;
        if (!observation.observed or observation.initial == null or !metadata(item.initial.?, observation.initial.?)) return error.SamplerInputDrift;
        if (item.raw) |raw| {
            if (bytes == null or !std.mem.eql(u8, raw, bytes.?)) return error.SamplerInputDrift;
        } else if (bytes != null) return error.SamplerInputDrift;
    }
    fn finish(self: *ReportScope) !void {
        var failure: ?anyerror = null;
        // Inspect parent custody and every retained input separately: one lost
        // name must not prevent checks through other still-owned descriptors.
        for (self.inputs[0..self.count]) |item| if (item.parent) |parent| {
            if (!item.parent_observed) {
                if (failure == null) failure = error.SamplerPathObservationFailed;
            } else parent.verify(self.init.io) catch |problem| {
                if (failure == null) failure = problem;
            };
        };
        for (self.inputs[0..self.count]) |item| {
            self.verify(item) catch |problem| {
                if (failure == null) failure = problem;
            };
            if (item.close_failed and failure == null) failure = error.CgroupCloseFailed;
        }
        for (self.inputs[0..self.count]) |item| if (item.parent) |parent| {
            if (c.close(parent.fd) != 0 and failure == null) failure = error.CgroupCloseFailed;
        };
        if (failure) |problem| return problem;
        try before(self.init.io, self.deadline);
    }
};

// Bound structure and reject Python's non-JSON numeric extensions explicitly.
// This scan only guards this artifact parser; JSON grammar remains std.json's.
fn reportDomain(bytes: []const u8) !void {
    if (!std.unicode.utf8ValidateSlice(bytes)) return error.UnsupportedSamplerEncoding;
    var string = false;
    var escape = false;
    var depth: usize = 0;
    var index: usize = 0;
    while (index < bytes.len) : (index += 1) {
        const byte = bytes[index];
        if (string) {
            if (escape) {
                escape = false;
                if (byte == 'u' and index + 4 < bytes.len) {
                    const unit = std.fmt.parseInt(u16, bytes[index + 1 .. index + 5], 16) catch continue;
                    if (unit >= 0xd800 and unit <= 0xdbff) {
                        if (index + 10 >= bytes.len or bytes[index + 5] != '\\' or bytes[index + 6] != 'u') return error.UnsupportedSamplerEncoding;
                        const low = std.fmt.parseInt(u16, bytes[index + 7 .. index + 11], 16) catch return error.UnsupportedSamplerEncoding;
                        if (low < 0xdc00 or low > 0xdfff) return error.UnsupportedSamplerEncoding;
                        index += 10;
                    } else if (unit >= 0xdc00 and unit <= 0xdfff) return error.UnsupportedSamplerEncoding else index += 4;
                }
            } else if (byte == '\\') {
                escape = true;
            } else if (byte == '"') string = false;
            continue;
        }
        if (byte == '"') {
            string = true;
        } else if (byte == '{' or byte == '[') {
            depth += 1;
            if (depth > 64) return error.UnsupportedReportValue;
        } else if (byte == '}' or byte == ']') {
            if (depth != 0) depth -= 1;
        } else {
            for ([_][]const u8{ "NaN", "Infinity", "-Infinity" }) |token| {
                if (!std.mem.startsWith(u8, bytes[index..], token)) continue;
                const end = index + token.len;
                const prior = index == 0 or std.mem.indexOfScalar(u8, " \t\r\n[:,", bytes[index - 1]) != null;
                const next = end == bytes.len or std.mem.indexOfScalar(u8, " \t\r\n]},", bytes[end]) != null;
                if (prior and next) return error.UnsupportedReportValue;
            }
        }
    }
}
fn reportIntegerToken(number: []const u8) bool {
    // For validated JSON, Python creates integers for every token without a
    // fraction/exponent, including -0. Zig's conversion predicate excludes -0.
    return std.mem.findAny(u8, number, ".eE") == null;
}
fn reportJson(a: Allocator, bytes: []const u8, duplicates: bool) !?std.json.Value {
    try reportDomain(bytes);
    // CPython's pinned parser applies its integer limit before duplicate-field
    // replacement or state-field selection. Inspect every original token.
    var scanner = std.json.Scanner.initCompleteInput(a, bytes);
    defer scanner.deinit();
    while (true) {
        const token = scanner.next() catch |problem| switch (problem) {
            error.OutOfMemory => return problem,
            else => return null,
        };
        switch (token) {
            .number => |number| {
                const digits = number.len - @intFromBool(number[0] == '-');
                if (reportIntegerToken(number) and digits > 4300) return null;
            },
            .end_of_document => break,
            else => {},
        }
    }
    const parsed = std.json.parseFromSlice(std.json.Value, a, bytes, .{ .parse_numbers = false, .duplicate_field_behavior = if (duplicates) .use_last else .@"error" }) catch |problem| switch (problem) {
        error.OutOfMemory => return problem,
        else => return null,
    };
    return parsed.value;
}
fn reportInteger(comptime T: type, value: std.json.Value) !?T {
    if (value != .number_string or !reportIntegerToken(value.number_string)) return null;
    return std.fmt.parseInt(T, value.number_string, 10) catch return error.UnsupportedReportValue;
}
fn reportRequest(scope: *ReportScope, path: []const u8) !ReportRequest {
    const a = scope.init.arena.allocator();
    const bytes = (try scope.read(path, false, false)).?;
    const request = try reportRequestBytes(a, bytes);
    scope.deadline = @min(scope.deadline, scope.started + @as(i96, request.wall_ms) * std.time.ns_per_ms);
    try scope.check();
    try pathText(request.state_path, false);
    if (request.cgroup_path) |path_value| try pathText(path_value, false);
    return request;
}
fn reportRequestBytes(a: Allocator, bytes: []const u8) !ReportRequest {
    const value = (reportJson(a, bytes, false) catch |problem| switch (problem) {
        error.OutOfMemory, error.UnsupportedSamplerEncoding => return problem,
        else => return error.InvalidReportRequest,
    }) orelse return error.InvalidReportRequest;
    if (value != .object or value.object.count() != 6) return error.InvalidReportRequest;
    for ([_][]const u8{ "schema_version", "state_path", "cgroup_path", "warn_bytes", "error_bytes", "wall_ms" }) |key| if (!value.object.contains(key)) return error.InvalidReportRequest;
    const version = (reportInteger(u8, value.object.get("schema_version").?) catch return error.InvalidReportRequest) orelse return error.InvalidReportRequest;
    const wall = (reportInteger(u32, value.object.get("wall_ms").?) catch return error.InvalidReportRequest) orelse return error.InvalidReportRequest;
    const warn = (reportInteger(u64, value.object.get("warn_bytes").?) catch return error.InvalidReportRequest) orelse return error.InvalidReportRequest;
    const limit = (reportInteger(u64, value.object.get("error_bytes").?) catch return error.InvalidReportRequest) orelse return error.InvalidReportRequest;
    const state = value.object.get("state_path").?;
    const group = value.object.get("cgroup_path").?;
    if (version != 1 or wall == 0 or wall > 3_600_000 or state != .string or (group != .string and group != .null)) return error.InvalidReportRequest;
    return .{ .state_path = state.string, .cgroup_path = if (group == .null) null else group.string, .warn_bytes = warn, .error_bytes = limit, .wall_ms = wall };
}
fn reportState(a: Allocator, bytes: ?[]const u8) !?ReportState {
    const value = (try reportJson(a, bytes orelse return null, true)) orelse return null;
    if (value != .object) return null;
    var fields: [4]std.json.Value = undefined;
    for ([_][]const u8{ "baseline_bytes", "peak_bytes", "samples", "pid" }, 0..) |key, index| {
        fields[index] = value.object.get(key) orelse return null;
        if (fields[index] != .number_string or !reportIntegerToken(fields[index].number_string)) return null;
    }
    const elapsed = value.object.get("elapsed_seconds") orelse return null;
    const source = value.object.get("source") orelse return null;
    if (elapsed != .number_string or source != .string or (!std.mem.eql(u8, source.string, "meminfo") and !std.mem.eql(u8, source.string, "unavailable"))) return null;
    var integers: [4]i128 = undefined;
    for (fields, 0..) |field, index| integers[index] = (try reportInteger(i128, field)).?;
    var seconds = std.fmt.parseFloat(f64, elapsed.number_string) catch return error.UnsupportedReportValue;
    if (!std.math.isFinite(seconds)) return error.UnsupportedReportValue;
    // json.loads creates an integer for -0; float(integer_zero) is positive.
    // Float spellings such as -0.0 and -0e0 retain their original sign.
    if (seconds == 0 and reportIntegerToken(elapsed.number_string)) seconds = 0;
    return .{ .baseline = integers[0], .peak = integers[1], .samples = integers[2], .pid = integers[3], .elapsed = seconds, .source = source.string };
}
fn reportCgroup(a: Allocator, bytes: []const u8) !?u64 {
    const value = (reportJson(a, bytes, false) catch |problem| switch (problem) {
        error.OutOfMemory, error.UnsupportedSamplerEncoding => return problem,
        else => return error.InvalidCgroupResult,
    }) orelse return error.InvalidCgroupResult;
    if (value != .object or value.object.count() != 3) return error.InvalidCgroupResult;
    const schema = value.object.get("schema_version") orelse return error.InvalidCgroupResult;
    const source = value.object.get("source") orelse return error.InvalidCgroupResult;
    const peak = value.object.get("peak_bytes") orelse return error.InvalidCgroupResult;
    if (((reportInteger(u8, schema) catch return error.InvalidCgroupResult) orelse return error.InvalidCgroupResult) != 1 or source != .string) return error.InvalidCgroupResult;
    if (std.mem.eql(u8, source.string, "unavailable") and peak == .null) return null;
    if (!std.mem.eql(u8, source.string, "cgroup-v2-memory-peak")) return error.InvalidCgroupResult;
    return (reportInteger(u64, peak) catch return error.InvalidCgroupResult) orelse return error.InvalidCgroupResult;
}

// Scale the exact binary64 rational before rounding once to nearest/ties-even.
// u2048 holds every finite binary64 numerator at all selected decimal places.
fn reportFixed(a: Allocator, value: f64, places: u8) ![]const u8 {
    if (!std.math.isFinite(value) or places > 40) return error.UnsupportedReportValue;
    const bits: u64 = @bitCast(value);
    const exponent = (bits >> 52) & 0x7ff;
    const mantissa: u2048 = (bits & 0xfffffffffffff) | @as(u64, if (exponent == 0) 0 else 0x10000000000000);
    const power: i32 = if (exponent == 0) -1074 else @as(i32, @intCast(exponent)) - 1075;
    var scaled = mantissa;
    for (0..places) |_| scaled *= 10;
    var rounded: u2048 = undefined;
    if (power >= 0) {
        rounded = scaled << @as(u11, @intCast(power));
    } else {
        const shift: u11 = @intCast(-power);
        rounded = scaled >> shift;
        const remainder = scaled - (rounded << shift);
        const half = @as(u2048, 1) << (shift - 1);
        if (remainder > half or (remainder == half and rounded & 1 != 0)) rounded += 1;
    }
    const digits = try std.fmt.allocPrint(a, "{d}", .{rounded});
    const sign: []const u8 = if (bits >> 63 != 0) "-" else "";
    if (places == 0) return std.fmt.allocPrint(a, "{s}{s}", .{ sign, digits });
    if (digits.len <= places) {
        const padding = try a.alloc(u8, places - digits.len);
        @memset(padding, '0');
        return std.fmt.allocPrint(a, "{s}0.{s}{s}", .{ sign, padding, digits });
    }
    return std.fmt.allocPrint(a, "{s}{s}.{s}", .{ sign, digits[0 .. digits.len - places], digits[digits.len - places ..] });
}
// Python's default :g is six significant digits, with zero trimming and the
// exponent decision made after rounding. This call is only for u64/GiB limits.
fn reportThreshold(a: Allocator, bytes: u64) ![]const u8 {
    const value = @as(f64, @floatFromInt(bytes)) / 1073741824;
    const fixed = try reportFixed(a, value, 40);
    const point = std.mem.indexOfScalar(u8, fixed, '.').?;
    var digits: [64]u8 = undefined;
    var length: usize = 0;
    for (fixed) |byte| if (byte != '.') {
        digits[length] = byte;
        length += 1;
    };
    var first: usize = 0;
    while (first < length and digits[first] == '0') : (first += 1) {}
    if (first == length) return "0";
    var exponent: i32 = @as(i32, @intCast(point)) - @as(i32, @intCast(first)) - 1;
    var significant = try std.fmt.parseInt(u32, digits[first .. first + 6], 10);
    const next = digits[first + 6];
    var sticky = false;
    for (digits[first + 7 .. length]) |byte| sticky = sticky or byte != '0';
    if (next > '5' or (next == '5' and (sticky or significant & 1 != 0))) significant += 1;
    if (significant == 1_000_000) {
        significant = 100_000;
        exponent += 1;
    }
    const significant_text = try std.fmt.allocPrint(a, "{d}", .{significant});
    var end = significant_text.len;
    while (end > 1 and significant_text[end - 1] == '0') : (end -= 1) {}
    const text = significant_text[0..end];
    if (exponent < -4 or exponent >= 6) {
        const absolute = @abs(exponent);
        const exp = if (absolute < 10) try std.fmt.allocPrint(a, "0{d}", .{absolute}) else try std.fmt.allocPrint(a, "{d}", .{absolute});
        const coefficient = if (text.len == 1) text else try std.fmt.allocPrint(a, "{s}.{s}", .{ text[0..1], text[1..] });
        return std.fmt.allocPrint(a, "{s}e{s}{s}", .{ coefficient, if (exponent < 0) "-" else "+", exp });
    }
    if (exponent < 0) {
        const padding = try a.alloc(u8, @intCast(-exponent - 1));
        @memset(padding, '0');
        return std.fmt.allocPrint(a, "0.{s}{s}", .{ padding, text });
    }
    const position: usize = @intCast(exponent + 1);
    if (position >= text.len) {
        const padding = try a.alloc(u8, position - text.len);
        @memset(padding, '0');
        return std.fmt.allocPrint(a, "{s}{s}", .{ text, padding });
    }
    return std.fmt.allocPrint(a, "{s}.{s}", .{ text[0..position], text[position..] });
}
fn reportBuild(scope: *ReportScope, path: []const u8) ![]const u8 {
    const a = scope.init.arena.allocator();
    const request = try reportRequest(scope, path);
    const parsed = try reportState(a, try scope.read(request.state_path, true, true));
    const state = parsed orelse ReportState{};
    const peak = if (request.cgroup_path) |group| try reportCgroup(a, (try scope.read(group, false, true)).?) else null;
    try scope.check();
    var lines: std.ArrayList([]const u8) = .empty;
    if (parsed == null) {
        try lines.append(a, try std.fmt.allocPrint(a, "::warning title=memory sampler::no usable sampler state at {s}; was `start` run?", .{request.state_path}));
    } else if (std.mem.eql(u8, state.source, "unavailable")) try lines.append(a, "::warning title=memory sampler::no /proc/meminfo sample was recorded; peak memory is unavailable");
    const delta = std.math.sub(i128, state.peak, state.baseline) catch return error.UnsupportedReportValue;
    const elapsed = try reportFixed(a, state.elapsed, 1);
    const group_bytes = if (peak) |number| try std.fmt.allocPrint(a, "{d}", .{number}) else "na";
    try lines.append(a, try std.fmt.allocPrint(a, "peak_rss_bytes={d} source={s} baseline_bytes={d} delta_bytes={d} samples={d} elapsed_s={s} cgroup_peak_bytes={s}", .{ state.peak, state.source, state.baseline, delta, state.samples, elapsed, group_bytes }));
    const gib = try reportFixed(a, @as(f64, @floatFromInt(state.peak)) / 1073741824, 2);
    const warn = try reportThreshold(a, request.warn_bytes);
    const limit = try reportThreshold(a, request.error_bytes);
    if (state.peak >= request.error_bytes) {
        try lines.append(a, try std.fmt.allocPrint(a, "::error title=memory sampler::peak memory {s} GiB reached the {s} GiB NFR-005 limit", .{ gib, limit }));
    } else if (state.peak >= request.warn_bytes) try lines.append(a, try std.fmt.allocPrint(a, "::warning title=memory sampler::peak memory {s} GiB is above {s} GiB (NFR-005 limit {s} GiB)", .{ gib, warn, limit }));
    const baseline = try reportFixed(a, @as(f64, @floatFromInt(state.baseline)) / 1073741824, 2);
    const group_gib = if (peak) |number| try std.fmt.allocPrint(a, "{s} GiB", .{try reportFixed(a, @as(f64, @floatFromInt(number)) / 1073741824, 2)}) else "n/a";
    const summary = try std.fmt.allocPrint(a, "Memory sampler (NFR-005): peak {s} GiB (MemTotal - MemAvailable), baseline {s} GiB, {d} samples over {s}s, cgroup peak {s}", .{ gib, baseline, state.samples, elapsed, group_gib });
    const result = try std.json.Stringify.valueAlloc(a, .{ .schema_version = 1, .report_lines = lines.items, .summary_line = summary }, .{});
    if (result.len + 1 > 16384) return error.SamplerInputLimit;
    try scope.check();
    return std.fmt.allocPrint(a, "{s}\n", .{result});
}
pub fn reportCommand(init: std.process.Init, path: []const u8) !u8 {
    if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.PlatformUnsupported;
    const started = now(init.io);
    var scope: ReportScope = .{ .init = init, .started = started, .deadline = started + 3_600_000 * std.time.ns_per_ms };
    var lease = owner.beginSamplingSignals() catch |problem| {
        const finished = scope.finish();
        if (problem == error.SignalRestorationFailed) return problem;
        try finished;
        return problem;
    };
    var primary: ?anyerror = null;
    const result = reportBuild(&scope, path) catch |problem| blk: {
        primary = problem;
        break :blk @as(?[]const u8, null);
    };
    var final_failure: ?anyerror = null;
    scope.finish() catch |problem| {
        final_failure = problem;
    };
    const received = try owner.restoreSamplingSignals(&lease);
    if (final_failure) |problem| return problem;
    try before(init.io, scope.deadline);
    if (primary) |problem| return problem;
    if (received != 0) return error.Cancelled;
    try std.Io.File.stdout().writeStreamingAll(init.io, result.?);
    try before(init.io, scope.deadline);
    return 0;
}

/// The exact three existing requests held by one lifetime owner. This fixed
/// bundle does not admit other input classes or create a replacement schema.
pub const LifetimeRequests = struct {
    scope: ReportScope,
    report_path: []const u8,
    sample: Request = undefined,
    group: CgroupRequest = undefined,
    report: ReportRequest = undefined,
    active: bool = true,

    pub fn capture(init: std.process.Init, sample_path: []const u8, group_path: []const u8, report_path: []const u8, check: *owner.CheckScope) !LifetimeRequests {
        const deadline = try borrowedDeadline(init.io, check);
        var result: LifetimeRequests = .{ .scope = .{ .init = init, .started = now(init.io), .deadline = deadline }, .report_path = report_path };
        result.acquire(sample_path, group_path, report_path) catch |problem| {
            try result.finish();
            return problem;
        };
        return result;
    }

    fn acquire(self: *LifetimeRequests, sample_path: []const u8, group_path: []const u8, report_path: []const u8) !void {
        const a = self.scope.init.arena.allocator();
        self.sample = try requestBytes(a, (try self.scope.read(sample_path, false, false)).?);
        if (self.sample.max_samples < 2) return error.InvalidSamplerLifetime;
        self.group = try cgroupRequestBytes(a, (try self.scope.read(group_path, false, false)).?);
        self.report = try reportRequestBytes(a, (try self.scope.read(report_path, false, false)).?);
        try pathText(self.report.state_path, false);
        const expected_state = try std.fmt.allocPrint(a, "{s}/state.json", .{self.sample.destination});
        if (!std.mem.eql(u8, expected_state, self.report.state_path)) return error.InvalidSamplerLifetime;
        const cgroup_path = self.report.cgroup_path orelse return error.InvalidSamplerLifetime;
        try pathText(cgroup_path, false);
        try self.scope.check();
    }

    pub fn finish(self: *LifetimeRequests) !void {
        if (!self.active) return error.SamplerOwnerRequired;
        self.active = false;
        try self.scope.finish();
    }

    pub fn statePath(self: *const LifetimeRequests) []const u8 {
        return self.report.state_path;
    }

    pub fn cgroupResultPath(self: *const LifetimeRequests) ?[]const u8 {
        return self.report.cgroup_path;
    }

    /// Independently bind the stopped worker's acknowledgement to the
    /// published state bytes and their retained filesystem identities.
    pub fn verifyCommitment(self: *LifetimeRequests, expected: OwnedSampling.Commitment, pid: i32, samples: u32) !void {
        if (!self.active) return error.SamplerOwnerRequired;
        try self.scope.check();
        const a = self.scope.init.arena.allocator();
        const state_path = self.report.state_path;
        try pathText(state_path, false);
        try canonical(self.scope.init.io, state_path);
        const directory_path = std.fs.path.dirname(state_path) orelse return error.InvalidSamplerPath;
        const parent_path = std.fs.path.dirname(directory_path) orelse return error.InvalidSamplerPath;
        const parent = try Directory.open(a, self.scope.init.io, parent_path, true);
        defer parent.close();
        const directory = try Directory.open(a, self.scope.init.io, directory_path, true);
        defer directory.close();
        if (!std.mem.eql(u8, expected.parent_identity_sha256, try lifetimeMetadataDigest(a, parent.identity, false)) or
            !std.mem.eql(u8, expected.directory_identity_sha256, try lifetimeMetadataDigest(a, directory.identity, false))) return error.SamplerOutputDrift;

        const leaf = try a.dupeZ(u8, std.fs.path.basename(state_path));
        const initial = (try statAt(directory.fd, leaf)) orelse return error.SamplerOutputDrift;
        try ReportScope.safe(initial);
        if (!std.mem.eql(u8, expected.state_metadata_sha256, try lifetimeMetadataDigest(a, initial, true))) return error.SamplerOutputDrift;
        var observation: InputObservation = .{ .fd = directory.fd, .name = leaf, .initial = null, .observed = false };
        const buffer = try a.alloc(u8, max_bytes + 1);
        const bytes = readAt(directory.fd, leaf, buffer, false, self.scope.init.io, self.scope.deadline, &observation) catch |problem| {
            if (observation.close_failed) return error.SamplerCloseFailed;
            return problem;
        };
        const state_bytes = bytes orelse return error.SamplerOutputDrift;
        if (observation.close_failed) return error.SamplerCloseFailed;
        if (!observation.observed or observation.initial == null or !ReportScope.metadata(initial, observation.initial.?)) return error.SamplerOutputDrift;
        if (!std.mem.eql(u8, expected.state_sha256, try lifetimeDigest(a, state_bytes))) return error.SamplerOutputDrift;
        const final = (try statAt(directory.fd, leaf)) orelse return error.SamplerOutputDrift;
        if (!ReportScope.metadata(initial, final) or try statAt(directory.fd, "state.tmp") != null) return error.SamplerOutputDrift;
        const parsed = (try reportState(a, state_bytes)) orelse return error.SamplerOutputDrift;
        if (parsed.pid != pid or parsed.samples != samples) return error.SamplerOutputDrift;
        try parent.verify(self.scope.init.io);
        try directory.verify(self.scope.init.io);
        try self.scope.check();
    }

    /// Create the one declared cgroup result without following a replacement
    /// directory or overwriting an existing artifact.
    pub fn writeCgroupResult(self: *LifetimeRequests, diagnostics_path: []const u8, bytes: []const u8) !void {
        if (!self.active or bytes.len == 0 or bytes.len > max_bytes) return error.InvalidCgroupResult;
        try self.scope.check();
        const path = self.report.cgroup_path orelse return error.InvalidCgroupResult;
        const prefix = try std.fmt.allocPrint(self.scope.init.arena.allocator(), "{s}/", .{diagnostics_path});
        if (!std.mem.startsWith(u8, path, prefix)) return error.PrivateEvidenceRequired;
        try pathText(path, false);
        const parent_path = std.fs.path.dirname(path) orelse return error.InvalidSamplerPath;
        const parent = try Directory.open(self.scope.init.arena.allocator(), self.scope.init.io, parent_path, true);
        defer parent.close();
        const leaf = try self.scope.init.arena.allocator().dupeZ(u8, std.fs.path.basename(path));
        if (try statAt(parent.fd, leaf) != null) return error.SamplerOutputDrift;
        const fd = c.openat(parent.fd, leaf, c.O_WRONLY | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW | c.O_CLOEXEC, @as(c_uint, 0o600));
        if (fd < 0) return error.SamplerOutputCreateFailed;
        var close_needed = true;
        defer {
            if (close_needed) _ = c.close(fd);
        }
        var initial: Stat = undefined;
        if (try descriptorStat(fd, &initial) != 0 or !regular(initial) or initial.st_uid != c.geteuid() or initial.st_nlink != 1 or initial.st_mode & 0o7777 != 0o600 or initial.st_size != 0) return error.UnsafeSamplerOutput;
        var offset: usize = 0;
        while (offset < bytes.len) {
            try self.scope.check();
            const count = c.write(fd, @ptrCast(bytes[offset..].ptr), bytes.len - offset);
            if (count < 0 and std.c.errno(@as(c_int, -1)) == .INTR) continue;
            if (count <= 0) return error.SamplerOutputWriteFailed;
            offset += @intCast(count);
        }
        if (c.fsync(fd) != 0) return error.SamplerOutputWriteFailed;
        var final: Stat = undefined;
        if (try descriptorStat(fd, &final) != 0 or !regular(final) or final.st_uid != c.geteuid() or final.st_nlink != 1 or final.st_mode & 0o7777 != 0o600 or final.st_size != bytes.len) return error.SamplerOutputDrift;
        const named = (try statAt(parent.fd, leaf)) orelse return error.SamplerOutputDrift;
        if (!ReportScope.metadata(final, named)) return error.SamplerOutputDrift;
        if (c.close(fd) != 0) {
            close_needed = false;
            return error.SamplerCloseFailed;
        }
        close_needed = false;
        var observation: InputObservation = .{ .fd = parent.fd, .name = leaf, .initial = null, .observed = false };
        const buffer = try self.scope.init.arena.allocator().alloc(u8, max_bytes + 1);
        const readback = readAt(parent.fd, leaf, buffer, false, self.scope.init.io, self.scope.deadline, &observation) catch |problem| {
            if (observation.close_failed) return error.SamplerCloseFailed;
            return problem;
        };
        if (observation.close_failed) return error.SamplerCloseFailed;
        if (!observation.observed or observation.initial == null or !ReportScope.metadata(final, observation.initial.?) or readback == null or !std.mem.eql(u8, bytes, readback.?)) return error.SamplerOutputDrift;
        try parent.verify(self.scope.init.io);
        try self.scope.check();
    }
};

fn borrowedDeadline(io: std.Io, check: *owner.CheckScope) !i96 {
    try check.ready(io);
    // Read awake first, then boot, so conversion cannot extend the original
    // work deadline. The check keeps its original clock and signal owner.
    const awake = now(io);
    const remaining = check.deadline - std.Io.Clock.boot.now(io).nanoseconds;
    if (remaining <= 0) return error.OperationDeadlineExceeded;
    return awake + remaining;
}

pub fn cgroupForLifetime(init: std.process.Init, inputs: *LifetimeRequests, check: *owner.CheckScope) ![]const u8 {
    if (!inputs.active) return error.SamplerOwnerRequired;
    try inputs.scope.check();
    const started = now(init.io);
    const deadline = @min(try borrowedDeadline(init.io, check), started + @as(i96, inputs.group.wall_ms) * std.time.ns_per_ms);
    var directories: [70]Directory = undefined;
    var descriptors: [70]c_int = undefined;
    var observations: [74]InputObservation = undefined;
    var scope: CgroupScope = .{ .init = init, .deadline = deadline, .directories = .initBuffer(&directories), .descriptors = .initBuffer(&descriptors), .inputs = .initBuffer(&observations) };
    var primary: ?anyerror = null;
    const peak = cgroupCollect(&scope, inputs.group) catch |problem| blk: {
        primary = problem;
        break :blk @as(?u64, null);
    };
    try scope.finish();
    try check.ready(init.io);
    try before(init.io, deadline);
    if (primary) |problem| return problem;
    return cgroupResultBytes(init.arena.allocator(), peak);
}

pub fn reportForLifetime(init: std.process.Init, path: []const u8, check: *owner.CheckScope) ![]const u8 {
    const deadline = try borrowedDeadline(init.io, check);
    var scope: ReportScope = .{ .init = init, .started = now(init.io), .deadline = deadline };
    var primary: ?anyerror = null;
    const result: ?[]const u8 = reportBuild(&scope, path) catch |problem| blk: {
        primary = problem;
        break :blk null;
    };
    try scope.finish();
    try check.ready(init.io);
    try before(init.io, scope.deadline);
    if (primary) |problem| return problem;
    return result.?;
}

/// Append one rendered summary to an existing private log. A swapped name,
/// alias, non-regular target, or partial write cannot produce success.
pub fn appendSummary(init: std.process.Init, path: []const u8, line: []const u8, deadline: i96) !void {
    if (line.len == 0 or line.len > 8192 or std.mem.indexOfAny(u8, line, "\r\n\x00") != null) return error.InvalidSummary;
    try pathText(path, false);
    try canonical(init.io, path);
    const a = init.arena.allocator();
    const parent_path = std.fs.path.dirname(path) orelse return error.InvalidSamplerPath;
    const leaf = try a.dupeZ(u8, std.fs.path.basename(path));
    const parent_z = try a.dupeZ(u8, parent_path);
    const dir = c.open(parent_z, c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW | c.O_CLOEXEC);
    if (dir < 0) return error.UnsafeSamplerDirectory;
    defer _ = c.close(dir);
    var directory_stat: Stat = undefined;
    if (try descriptorStat(dir, &directory_stat) != 0 or directory_stat.st_mode & c.S_IFMT != c.S_IFDIR or directory_stat.st_uid != c.geteuid() or directory_stat.st_mode & 0o7777 != 0o700) return error.UnsafeSamplerDirectory;
    const before_stat = (try statAt(dir, leaf)) orelse return error.SamplerInputUnreadable;
    try ReportScope.safe(before_stat);
    var before_observation: InputObservation = .{ .fd = dir, .name = leaf, .initial = null, .observed = false };
    const before_buffer = try a.alloc(u8, @as(usize, @intCast(before_stat.st_size)) + 1);
    const previous = (try readAt(dir, leaf, before_buffer, false, init.io, deadline, &before_observation)).?;
    if (!before_observation.observed or before_observation.initial == null or !ReportScope.metadata(before_stat, before_observation.initial.?)) return error.SamplerInputDrift;
    const fd = c.openat(dir, leaf, c.O_WRONLY | c.O_APPEND | c.O_NONBLOCK | c.O_NOFOLLOW | c.O_CLOEXEC);
    if (fd < 0) return error.SamplerOutputDrift;
    var close_needed = true;
    defer {
        if (close_needed) _ = c.close(fd);
    }
    var opened: Stat = undefined;
    if (try descriptorStat(fd, &opened) != 0 or !ReportScope.metadata(before_stat, opened)) return error.SamplerOutputDrift;
    const appended = try std.fmt.allocPrint(a, "{s}\n", .{line});
    if (before_stat.st_size < 0 or @as(u128, @intCast(before_stat.st_size)) + appended.len > max_bytes) return error.SamplerInputLimit;
    var offset: usize = 0;
    while (offset < appended.len) {
        try before(init.io, deadline);
        const count = c.write(fd, @ptrCast(appended[offset..].ptr), appended.len - offset);
        if (count < 0 and std.c.errno(@as(c_int, -1)) == .INTR) continue;
        if (count <= 0) return error.SamplerOutputWriteFailed;
        offset += @intCast(count);
    }
    var after: Stat = undefined;
    if (try descriptorStat(fd, &after) != 0 or !same(before_stat, after) or after.st_mode != before_stat.st_mode or after.st_uid != before_stat.st_uid or after.st_nlink != 1 or after.st_size != before_stat.st_size + @as(@TypeOf(after.st_size), @intCast(appended.len))) return error.SamplerOutputDrift;
    const named = (try statAt(dir, leaf)) orelse return error.SamplerOutputDrift;
    if (!same(after, named) or named.st_mode != after.st_mode or named.st_uid != after.st_uid or named.st_size != after.st_size) return error.SamplerOutputDrift;
    const after_buffer = try a.alloc(u8, @as(usize, @intCast(after.st_size)) + 1);
    var after_observation: InputObservation = .{ .fd = dir, .name = leaf, .initial = null, .observed = false };
    const final_bytes = (try readAt(dir, leaf, after_buffer, false, init.io, deadline, &after_observation)).?;
    if (!after_observation.observed or after_observation.initial == null or !ReportScope.metadata(after, after_observation.initial.?) or final_bytes.len != previous.len + appended.len or !std.mem.eql(u8, final_bytes[0..previous.len], previous) or !std.mem.eql(u8, final_bytes[previous.len..], appended)) return error.SamplerOutputDrift;
    if (c.close(fd) != 0) {
        close_needed = false;
        return error.SamplerCloseFailed;
    }
    close_needed = false;
    const final_named = (try statAt(dir, leaf)) orelse return error.SamplerOutputDrift;
    if (!same(after, final_named) or final_named.st_size != after.st_size) return error.SamplerOutputDrift;
}

test "meminfo parser accepts bounded ASCII values and rejects malformed samples" {
    const valid = try parseUsage("MemTotal: 8192 kB\r\nMemAvailable: 2048 kB\n");
    try std.testing.expect(valid != null);
    try std.testing.expectEqual(@as(i128, 8192 * 1024), valid.?.total);
    try std.testing.expectEqual(@as(i128, 2048 * 1024), valid.?.available);
    try std.testing.expect((try parseUsage("MemTotal: 4 kB\nOther: 2\n")) == null);
    try std.testing.expect((try parseUsage("MemTotal: nope kB\nMemAvailable: 1 kB\n")) == null);
    try std.testing.expectError(error.UnsupportedSamplerEncoding, parseUsage("MemTotal: 1 kB\n\xff"));
    try std.testing.expectError(error.UnsupportedSamplerValue, parseUsage("MemTotal: 18446744073709551616 kB\nMemAvailable: 1 kB\n"));
}

test "sampler requests enforce exact fields, ranges, and safe paths" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    const request = try requestBytes(a, "{\"schema_version\":1,\"destination\":\"/tmp/out\",\"proc_root\":\"/proc\",\"interval_ms\":10,\"max_samples\":2,\"wall_ms\":1000}");
    try std.testing.expectEqual(@as(u32, 2), request.max_samples);
    for ([_][]const u8{
        "[]",
        "{}",
        "{\"schema_version\":1,\"schema_version\":1,\"destination\":\"/tmp/out\",\"proc_root\":\"/proc\",\"interval_ms\":10,\"max_samples\":2,\"wall_ms\":1000}",
        "{\"schema_version\":1,\"destination\":\"/tmp/out\",\"proc_root\":\"/proc\",\"interval_ms\":10,\"max_samples\":0,\"wall_ms\":1000}",
        "{\"schema_version\":1,\"destination\":\"/tmp/out\",\"proc_root\":\"/proc\",\"interval_ms\":60001,\"max_samples\":2,\"wall_ms\":1000}",
    }) |raw| try std.testing.expectError(error.InvalidSamplerRequest, requestBytes(a, raw));
    try std.testing.expectError(error.InvalidSamplerPath, requestBytes(a, "{\"schema_version\":1,\"destination\":\"/tmp/../out\",\"proc_root\":\"/proc\",\"interval_ms\":10,\"max_samples\":2,\"wall_ms\":1000}"));
}

test "cgroup request and membership values reject ambiguous input" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    const request = try cgroupRequestBytes(a, "{\"schema_version\":1,\"proc_root\":\"/proc\",\"sys_root\":\"/sys\",\"wall_ms\":500}");
    try std.testing.expectEqual(@as(u32, 500), request.wall_ms);
    try std.testing.expectError(error.InvalidCgroupRequest, cgroupRequestBytes(a, "{\"schema_version\":1,\"proc_root\":\"/proc\",\"sys_root\":\"/sys\",\"wall_ms\":0}"));
    try std.testing.expectEqualStrings("/tenant/job", (try cgroupSuffix("5:cpu:/tenant/job\n0::/tenant/job\n")).?);
    try std.testing.expect((try cgroupSuffix("5:cpu:/tenant/job\n")) == null);
    try std.testing.expectError(error.UnsupportedCgroupEncoding, cgroupSuffix("0::/bad\xff"));
    try std.testing.expectEqual(@as(?u64, 42), try cgroupValue(" \t42\r\n"));
    try std.testing.expect((try cgroupValue("not-a-number")) == null);
    try std.testing.expectError(error.UnsupportedCgroupEncoding, cgroupValue("\xff"));
    try std.testing.expectError(error.UnsupportedCgroupValue, cgroupValue("18446744073709551616"));
}

test "report parsers preserve JSON boundaries and owner-neutral unavailable values" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    try std.testing.expectError(error.UnsupportedSamplerEncoding, reportDomain("\xff"));
    try std.testing.expectError(error.UnsupportedReportValue, reportDomain("NaN"));
    try std.testing.expectError(error.UnsupportedReportValue, reportDomain("[" ** 65 ++ "0" ++ "]" ** 65));
    try std.testing.expect((try reportJson(a, "{\"x\":1,\"x\":2}", false)) == null);
    const duplicate = (try reportJson(a, "{\"x\":1,\"x\":2}", true)).?;
    try std.testing.expectEqualStrings("2", duplicate.object.get("x").?.number_string);
    try std.testing.expectError(error.InvalidReportRequest, reportRequestBytes(a, "{}"));
    const request = try reportRequestBytes(a, "{\"schema_version\":1,\"state_path\":\"/tmp/state\",\"cgroup_path\":null,\"warn_bytes\":10,\"error_bytes\":20,\"wall_ms\":100}");
    try std.testing.expectEqual(@as(u64, 20), request.error_bytes);
    const state = (try reportState(a, "{\"baseline_bytes\":10,\"peak_bytes\":15,\"samples\":2,\"pid\":7,\"elapsed_seconds\":-0.0,\"source\":\"meminfo\"}")).?;
    try std.testing.expectEqual(@as(i128, 15), state.peak);
    try std.testing.expect(std.math.signbit(state.elapsed));
    try std.testing.expect((try reportState(a, null)) == null);
    try std.testing.expect((try reportState(a, "{\"baseline_bytes\":1,\"peak_bytes\":2,\"samples\":1,\"pid\":7,\"elapsed_seconds\":\"bad\",\"source\":\"meminfo\"}")) == null);
    try std.testing.expectError(error.UnsupportedReportValue, reportState(a, "{\"baseline_bytes\":1,\"peak_bytes\":2,\"samples\":1,\"pid\":7,\"elapsed_seconds\":1e9999,\"source\":\"meminfo\"}"));
    try std.testing.expectEqual(@as(?u64, null), try reportCgroup(a, "{\"schema_version\":1,\"source\":\"unavailable\",\"peak_bytes\":null}"));
    try std.testing.expectEqual(@as(?u64, 42), try reportCgroup(a, "{\"schema_version\":1,\"source\":\"cgroup-v2-memory-peak\",\"peak_bytes\":42}"));
    try std.testing.expectError(error.InvalidCgroupResult, reportCgroup(a, "{}"));
}

test "report formatting rounds deterministically at fixed and threshold boundaries" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    try std.testing.expectEqualStrings("1.50", try reportFixed(a, 1.5, 2));
    try std.testing.expectEqualStrings("-0.00", try reportFixed(a, -0.0, 2));
    try std.testing.expectError(error.UnsupportedReportValue, reportFixed(a, std.math.nan(f64), 2));
    try std.testing.expectError(error.UnsupportedReportValue, reportFixed(a, 1.0, 41));
    try std.testing.expectEqualStrings("0", try reportThreshold(a, 0));
    try std.testing.expectEqualStrings("9.31323e-10", try reportThreshold(a, 1));
    try std.testing.expectEqualStrings("1", try reportThreshold(a, 1073741824));
    try std.testing.expectEqualStrings("1e+06", try reportThreshold(a, 1073741824 * 1_000_000));
}
