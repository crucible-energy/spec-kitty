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
    const bytes = try std.fmt.allocPrint(init.arena.allocator(), "{{\"schema_version\":1,\"source\":\"{s}\",\"peak_bytes\":{?d}}}\n", .{ if (peak != null) "cgroup-v2-memory-peak" else "unavailable", peak });
    // Zig's optional formatter spells null as null, preserving unmeasured input.
    try std.Io.File.stdout().writeStreamingAll(init.io, bytes);
    try before(init.io, deadline);
    return 0;
}
