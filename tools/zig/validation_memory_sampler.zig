//! Finite foreground state producer adapted from scripts/ci/memory_sampler.py.
//! The maintained Python reader/report remains authority; gates are unchanged.
//! This bounded ASCII/finite-integer adapter deliberately refuses unsafe input,
//! cancellation and deadlines. It neither detaches nor starts/signals a child.
const std = @import("std");
const builtin = @import("builtin");
const owner = @import("validation_process_darwin.zig");
const c = @cImport({
    @cInclude("sys/stat.h");
    @cInclude("unistd.h");
    @cInclude("fcntl.h");
    @cInclude("stdio.h");
});
const Allocator = std.mem.Allocator;
const max_bytes = 65536;
const Request = struct { schema_version: u8, destination: []const u8, proc_root: []const u8, interval_ms: u32, max_samples: u32, wall_ms: u32 };
const State = struct { baseline_bytes: i128 = 0, elapsed_seconds: f64 = 0, peak_bytes: i128 = 0, pid: i32, samples: u32 = 0, source: enum { unavailable, meminfo } = .unavailable };
const Usage = struct { total: i128, available: i128 };
fn now(io: std.Io) i96 {
    return std.Io.Clock.awake.now(io).nanoseconds;
}
fn before(io: std.Io, deadline: i96) !void {
    if (now(io) >= deadline) return error.OperationDeadlineExceeded;
}
fn same(a: c.struct_stat, b: c.struct_stat) bool {
    return a.st_dev == b.st_dev and a.st_ino == b.st_ino;
}
fn regular(value: c.struct_stat) bool {
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
fn statAt(fd: c_int, name: [*:0]const u8) !?c.struct_stat {
    var value: c.struct_stat = undefined;
    if (c.fstatat(fd, name, &value, c.AT_SYMLINK_NOFOLLOW) == 0) return value;
    if (std.c.errno(@as(c_int, -1)) == .NOENT) return null;
    return error.SamplerPathObservationFailed;
}
const Directory = struct {
    fd: c_int,
    path: []const u8,
    path_z: [:0]const u8,
    identity: c.struct_stat,
    private: bool,
    fn open(a: Allocator, io: std.Io, path: []const u8, private: bool) !Directory {
        try canonical(io, path);
        const path_z = try a.dupeZ(u8, path);
        const fd = c.open(path_z, c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW | c.O_CLOEXEC);
        if (fd < 0) return error.UnsafeSamplerDirectory;
        errdefer _ = c.close(fd);
        var identity: c.struct_stat = undefined;
        if (c.fstat(fd, &identity) != 0 or identity.st_mode & c.S_IFMT != c.S_IFDIR) return error.UnsafeSamplerDirectory;
        if (private and (identity.st_uid != c.geteuid() or identity.st_mode & 0o7777 != 0o700)) return error.UnsafeSamplerDirectory;
        return .{ .fd = fd, .path = path, .path_z = path_z, .identity = identity, .private = private };
    }
    fn verify(self: Directory, io: std.Io) !void {
        try canonical(io, self.path);
        var path_stat: c.struct_stat = undefined;
        var held: c.struct_stat = undefined;
        if (c.lstat(self.path_z, &path_stat) != 0 or c.fstat(self.fd, &held) != 0 or !same(path_stat, self.identity) or !same(held, self.identity) or path_stat.st_mode & c.S_IFMT != c.S_IFDIR) return error.SamplerDirectoryDrift;
        if (self.private and (path_stat.st_uid != c.geteuid() or path_stat.st_mode & 0o7777 != 0o700)) return error.SamplerDirectoryDrift;
    }
    fn close(self: Directory) void {
        _ = c.close(self.fd);
    }
};
// Return null only for ordinary unreadable/missing bytes. Never open an observed
// FIFO/device/symlink, and verify the descriptor after the bounded nonblocking open.
fn readAt(fd: c_int, name: [*:0]const u8, buffer: []u8, unavailable: bool, io: std.Io, deadline: ?i96) !?[]const u8 {
    const observed = (try statAt(fd, name)) orelse {
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
    defer _ = c.close(file);
    var held: c.struct_stat = undefined;
    if (c.fstat(file, &held) != 0 or !same(observed, held) or !regular(held)) return error.SamplerInputDrift;
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
    if (c.fstat(file, &held) != 0 or !regular(held) or !same(observed, held)) return error.SamplerInputDrift;
    return buffer[0..length];
}
fn parseRequest(init: std.process.Init, path: []const u8) !Request {
    const a = init.arena.allocator();
    try pathText(path, false);
    try canonical(init.io, path);
    const path_z = try a.dupeZ(u8, path);
    const buffer = try a.alloc(u8, max_bytes + 1);
    const bytes = (try readAt(c.AT_FDCWD, path_z, buffer, false, init.io, null)).?;
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
    previous: ?c.struct_stat = null,
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
            const bytes = (try readAt(self.directory.fd, "state.json", &buffer, false, io, deadline)).?;
            if (!std.mem.eql(u8, bytes, self.previous_bytes.?)) return error.SamplerOutputDrift;
        } else if (value != null) return error.SamplerOutputDrift;
        if (try statAt(self.directory.fd, "state.tmp") != null) return error.SamplerOutputDrift;
    }
    fn removeTemp(self: Output, identity: c.struct_stat) !void {
        const value = (try statAt(self.directory.fd, "state.tmp")) orelse return error.SamplerOutputCustodyUnknown;
        if (!same(value, identity) or !regular(value) or value.st_nlink != 1 or value.st_uid != c.geteuid()) return error.SamplerOutputCustodyUnknown;
        if (c.unlinkat(self.directory.fd, "state.tmp", 0) != 0) return error.SamplerOutputCustodyUnknown;
    }
    fn replace(self: Output, file: c_int, identity: c.struct_stat, bytes: []const u8, io: std.Io, deadline: i96, committed: *bool) !c.struct_stat {
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
        var identity: c.struct_stat = undefined;
        if (c.fstat(file, &identity) != 0) return error.SamplerOutputCustodyUnknown;
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
fn collect(init: std.process.Init, request: Request, proc: Directory, output: *Output, started: i96, cutoff: i96, deadline: i96) !void {
    const buffer = try init.arena.allocator().alloc(u8, max_bytes + 1);
    var state: State = .{ .pid = c.getpid() };
    var attempts: u32 = 0;
    while (attempts < request.max_samples) : (attempts += 1) {
        try before(init.io, cutoff);
        try proc.verify(init.io);
        try before(init.io, cutoff);
        if (try readAt(proc.fd, "meminfo", buffer, true, init.io, cutoff)) |bytes| {
            if (try parseUsage(bytes)) |usage| {
                const used = usage.total - usage.available;
                const first = state.samples == 0;
                state = .{ .baseline_bytes = if (first) used else state.baseline_bytes, .peak_bytes = if (first) used else @max(state.peak_bytes, used), .samples = state.samples + 1, .elapsed_seconds = @as(f64, @floatFromInt(now(init.io) - started)) / std.time.ns_per_s, .source = .meminfo, .pid = state.pid };
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
    if (builtin.os.tag != .macos) return error.PlatformUnsupported;
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
