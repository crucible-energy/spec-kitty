//! Durable finish obligations. This store never grants release or deletion authority.
//! POSIX private-directory profile; unsupported platforms refuse rather than weaken it.
const std = @import("std");
const builtin = @import("builtin");
const candidate = @import("validation_candidate.zig");
const c = @cImport({
    @cDefine("_FORTIFY_SOURCE", "0");
    @cInclude("sys/stat.h");
    @cInclude("sys/file.h");
    @cInclude("fcntl.h");
    @cInclude("unistd.h");
    @cInclude("stdio.h");
});
const Allocator = std.mem.Allocator;
const max_bytes = 4 * 1024 * 1024;
const max_events = 10000;

const Stage = enum { triage, implement, validate, review, publish, await_delivery, await_release, await_cleanup, blocked };
const Source = struct {
    repository_id: u64,
    repository: []const u8,
    common_dir: []const u8,
    path: []const u8,
    head: []const u8,
    branch: []const u8,
};
const Obligation = struct {
    source: Source,
    owner: []const u8,
    purpose: []const u8,
    next_action: []const u8,
    review_event: []const u8,
    stage: Stage,
    evidence: []const []const u8,
};
const Event = struct { sequence: u64, obligation_id: []const u8, obligation: Obligation };
const State = struct { schema_version: u8 = 1, revision: u64 = 0, events: []const Event = &.{} };
const Request = struct {
    operation: enum { initialize, record, status },
    expected_revision: ?u64 = null,
    obligation: ?Obligation = null,
};

fn text(value: []const u8) !void {
    if (std.mem.trim(u8, value, " \t\r\n").len == 0 or value.len > 8192 or std.mem.indexOfScalar(u8, value, 0) != null or !std.unicode.utf8ValidateSlice(value)) return error.InvalidText;
}

fn absolute(path: []const u8) !void {
    try text(path);
    if (!std.fs.path.isAbsolute(path)) return error.AbsolutePathRequired;
    var parts = std.mem.splitScalar(u8, path, '/');
    while (parts.next()) |part| {
        if (std.mem.eql(u8, part, ".") or std.mem.eql(u8, part, "..")) return error.TraversalRefused;
    }
}

fn validate(value: Obligation) !void {
    const source = value.source;
    if (source.repository_id == 0 or !std.mem.startsWith(u8, source.repository, "crucible-energy/") or source.repository.len == "crucible-energy/".len) return error.InvalidRepository;
    for (source.repository["crucible-energy/".len..]) |ch| {
        if (!std.ascii.isLower(ch) and !std.ascii.isDigit(ch) and ch != '-' and ch != '_' and ch != '.') return error.InvalidRepository;
    }
    try absolute(source.common_dir);
    try absolute(source.path);
    if (source.head.len != 40 and source.head.len != 64) return error.ExactHeadRequired;
    for (source.head) |ch| if (!std.ascii.isDigit(ch) and (ch < 'a' or ch > 'f')) return error.ExactHeadRequired;
    try text(source.branch);
    if (!std.mem.startsWith(u8, source.branch, "refs/heads/") or source.branch.len == "refs/heads/".len) return error.ExactBranchRequired;
    inline for (.{ "owner", "purpose", "next_action", "review_event" }) |field| try text(@field(value, field));
    if (value.evidence.len > 64) return error.EvidenceBoundExceeded;
    for (value.evidence) |item| try text(item);
}

fn identity(allocator: Allocator, source: Source) ![]const u8 {
    // Structured serialization prevents ambiguous concatenation; checksum is identity, not proof.
    return candidate.hash(allocator, try candidate.json(allocator, source));
}

fn validateState(allocator: Allocator, state: State) !void {
    if (state.schema_version != 1 or state.revision != state.events.len or state.events.len > max_events) return error.InvalidHistory;
    for (state.events, 1..) |event, sequence| {
        if (event.sequence != sequence) return error.InvalidHistory;
        try validate(event.obligation);
        if (!std.mem.eql(u8, event.obligation_id, try identity(allocator, event.obligation.source))) return error.InvalidHistory;
    }
}

fn append(allocator: Allocator, state: State, expected: u64, obligation: Obligation) !State {
    try validateState(allocator, state);
    try validate(obligation);
    if (state.revision != expected) return error.StaleRevision;
    if (state.events.len == max_events) return error.HistoryBoundExceeded;
    const events = try allocator.alloc(Event, state.events.len + 1);
    @memcpy(events[0..state.events.len], state.events);
    events[state.events.len] = .{ .sequence = expected + 1, .obligation_id = try identity(allocator, obligation.source), .obligation = obligation };
    return .{ .revision = expected + 1, .events = events };
}

fn parse(comptime T: type, allocator: Allocator, bytes: []const u8) !std.json.Parsed(T) {
    if (bytes.len > max_bytes) return error.InputBoundExceeded;
    return std.json.parseFromSlice(T, allocator, bytes, .{ .duplicate_field_behavior = .@"error", .ignore_unknown_fields = false });
}

fn privateFile(fd: c_int) !void {
    var info: c.struct_stat = undefined;
    if (c.fstat(fd, &info) != 0) return error.StatFailed;
    if (info.st_mode & c.S_IFMT != c.S_IFREG or info.st_mode & 0o777 != 0o600 or info.st_uid != c.getuid() or info.st_nlink != 1) return error.PrivateFileRequired;
}

fn openRoot(allocator: Allocator, path: []const u8) !c_int {
    if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.UnsupportedPlatform;
    try absolute(path);
    var fd = c.open("/", c.O_RDONLY | c.O_DIRECTORY | c.O_CLOEXEC | c.O_NOFOLLOW);
    if (fd < 0) return error.DirectoryUnavailable;
    errdefer _ = c.close(fd);
    var parts = std.mem.tokenizeScalar(u8, path, '/');
    while (parts.next()) |part| {
        const name = try allocator.dupeZ(u8, part);
        const next = c.openat(fd, name, c.O_RDONLY | c.O_DIRECTORY | c.O_CLOEXEC | c.O_NOFOLLOW);
        if (next < 0) return error.UnsafeDirectory;
        _ = c.close(fd);
        fd = next;
    }
    var info: c.struct_stat = undefined;
    if (c.fstat(fd, &info) != 0 or info.st_uid != c.getuid() or info.st_mode & 0o777 != 0o700) return error.PrivateDirectoryRequired;
    return fd;
}

fn sameNamedFile(root: c_int, name: [*:0]const u8, fd: c_int) !void {
    var descriptor: c.struct_stat = undefined;
    var named: c.struct_stat = undefined;
    if (c.fstat(fd, &descriptor) != 0 or c.fstatat(root, name, &named, c.AT_SYMLINK_NOFOLLOW) != 0) return error.RecordIdentityChanged;
    if (descriptor.st_dev != named.st_dev or descriptor.st_ino != named.st_ino) return error.RecordIdentityChanged;
}

fn readState(allocator: Allocator, root: c_int) !State {
    const fd = c.openat(root, "finish.json", c.O_RDONLY | c.O_CLOEXEC | c.O_NOFOLLOW | c.O_NONBLOCK);
    if (fd < 0) return error.HistoryMissingOrUnavailable;
    defer _ = c.close(fd);
    try privateFile(fd);
    var buffer: std.ArrayList(u8) = .empty;
    var block: [8192]u8 = undefined;
    while (true) {
        const count = c.read(fd, &block, block.len);
        if (count < 0) return error.ReadFailed;
        if (count == 0) break;
        const size: usize = @intCast(count);
        if (buffer.items.len > max_bytes - size) return error.InputBoundExceeded;
        try buffer.appendSlice(allocator, block[0..size]);
    }
    try sameNamedFile(root, "finish.json", fd);
    const state = (try parse(State, allocator, buffer.items)).value;
    try validateState(allocator, state);
    return state;
}

fn persist(allocator: Allocator, root: c_int, state: State, initialize: bool) !void {
    const bytes = try candidate.json(allocator, state);
    if (bytes.len > max_bytes) return error.InputBoundExceeded;
    const name = try std.fmt.allocPrintSentinel(allocator, "finish.tmp.{d}.{d}", .{ c.getpid(), state.revision }, 0);
    const fd = c.openat(root, name, c.O_WRONLY | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW | c.O_CLOEXEC, @as(c_uint, 0o600));
    if (fd < 0) return error.TemporaryRecordUnavailable;
    var published = false;
    defer {
        _ = c.close(fd);
        if (!published) _ = c.unlinkat(root, name, 0);
    }
    var offset: usize = 0;
    while (offset < bytes.len) {
        const count = c.write(fd, bytes[offset..].ptr, bytes.len - offset);
        if (count <= 0) return error.WriteFailed;
        offset += @intCast(count);
    }
    if (c.fsync(fd) != 0) return error.DurabilityUnconfirmed;
    try sameNamedFile(root, name, fd);
    if (initialize) {
        // linkat is an atomic no-replace publication, including a dangling symlink.
        if (c.linkat(root, name, root, "finish.json", 0) != 0) return error.HistoryAlreadyExists;
        if (c.unlinkat(root, name, 0) != 0) return error.DurabilityUnconfirmed;
    } else if (c.renameat(root, name, root, "finish.json") != 0) return error.PublishFailed;
    published = true;
    if (c.fsync(root) != 0) return error.DurabilityUnconfirmed;
}

fn process(allocator: Allocator, root_path: []const u8, request: Request) !State {
    if (request.operation != .record and (request.obligation != null or request.expected_revision != null)) return error.InvalidRequest;
    const root = try openRoot(allocator, root_path);
    defer _ = c.close(root);
    if (request.operation == .initialize) {
        var existing: c.struct_stat = undefined;
        if (c.fstatat(root, "finish.json", &existing, c.AT_SYMLINK_NOFOLLOW) == 0) return error.HistoryAlreadyExists;
        if (std.c.errno(@as(c_int, -1)) != .NOENT) return error.HistoryUnavailable;
    }
    const create: c_int = if (request.operation == .initialize) c.O_CREAT | c.O_EXCL else 0;
    const lock = c.openat(root, "finish.lock", c.O_RDWR | create | c.O_NOFOLLOW | c.O_CLOEXEC, @as(c_uint, 0o600));
    if (lock < 0) {
        if (request.operation == .initialize) return error.ExistingFinishHistoryRequiresRecovery;
        return error.LockUnavailable;
    }
    defer _ = c.close(lock);
    try privateFile(lock);
    if (c.flock(lock, c.LOCK_EX | c.LOCK_NB) != 0) return error.LockBusy;
    defer _ = c.flock(lock, c.LOCK_UN);
    try sameNamedFile(root, "finish.lock", lock);
    const current_root = try openRoot(allocator, root_path);
    defer _ = c.close(current_root);
    var held: c.struct_stat = undefined;
    var current: c.struct_stat = undefined;
    if (c.fstat(root, &held) != 0 or c.fstat(current_root, &current) != 0 or held.st_dev != current.st_dev or held.st_ino != current.st_ino) return error.DirectoryIdentityChanged;
    switch (request.operation) {
        .initialize => {
            if (request.obligation != null or request.expected_revision != null) return error.InvalidRequest;
            try persist(allocator, root, .{}, true);
            return .{};
        },
        .status => {
            if (request.obligation != null or request.expected_revision != null) return error.InvalidRequest;
            return readState(allocator, root);
        },
        .record => {
            const state = try readState(allocator, root);
            const next = try append(allocator, state, request.expected_revision orelse return error.ExpectedRevisionRequired, request.obligation orelse return error.ObligationRequired);
            try persist(allocator, root, next, false);
            return next;
        },
    }
}

pub fn main(init: std.process.Init) void {
    run(init) catch |failure| std.process.fatal("finish obligation refused: {s}", .{@errorName(failure)});
}

fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len != 3) return error.InvalidArguments;
    const request = (try parse(Request, allocator, try candidate.read(allocator, init.io, args[2]))).value;
    const state = try process(allocator, args[1], request);
    try std.Io.File.stdout().writeStreamingAll(init.io, try candidate.json(allocator, .{ .state = state, .cleanup_authority = false, .cleanup_performed = false }));
}

fn example() Obligation {
    return .{ .source = .{ .repository_id = 7, .repository = "crucible-energy/example", .common_dir = "/private/repo/.git", .path = "/private/lane", .head = "a" ** 40, .branch = "refs/heads/useful" }, .owner = "implementation-owner", .purpose = "finish useful change", .next_action = "reproduce failing behavior", .review_event = "after focused validation", .stage = .triage, .evidence = &.{} };
}

test "append retains prior source and owner history; stale revisions cannot replace it" {
    var arena: std.heap.ArenaAllocator = .init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    const first = try append(a, .{}, 0, example());
    var change = example();
    change.owner = "review-owner";
    change.stage = .review;
    const second = try append(a, first, 1, change);
    try std.testing.expectEqual(@as(u64, 2), second.revision);
    try std.testing.expectEqualStrings("implementation-owner", second.events[0].obligation.owner);
    try std.testing.expectEqualStrings("review-owner", second.events[1].obligation.owner);
    try std.testing.expectEqualStrings(second.events[0].obligation_id, second.events[1].obligation_id);
    try std.testing.expectError(error.StaleRevision, append(a, second, 1, example()));
}

test "unknown fields, duplicate keys and invented closed stage are refused" {
    const a = std.testing.allocator;
    try std.testing.expectError(error.DuplicateField, parse(Request, a, "{\"operation\":\"status\",\"operation\":\"initialize\"}"));
    try std.testing.expectError(error.UnknownField, parse(Request, a, "{\"operation\":\"status\",\"delete\":true}"));
    try std.testing.expectError(error.InvalidEnumTag, std.meta.stringToEnum(Stage, "retired") orelse error.InvalidEnumTag);
}

test "missing assignment, relative paths and non organization identities cannot become obligations" {
    var value = example();
    value.owner = "";
    try std.testing.expectError(error.InvalidText, validate(value));
    value.owner = " \t\n";
    try std.testing.expectError(error.InvalidText, validate(value));
    value = example();
    value.source.path = "/private/../other";
    try std.testing.expectError(error.TraversalRefused, validate(value));
    value = example();
    value.source.repository = "elsewhere/example";
    try std.testing.expectError(error.InvalidRepository, validate(value));
}

test "replacement source generation remains a separate obligation and history is verified" {
    var arena: std.heap.ArenaAllocator = .init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    const first = try append(a, .{}, 0, example());
    var replacement = example();
    replacement.source.head = "b" ** 40;
    var second = try append(a, first, 1, replacement);
    try std.testing.expect(!std.mem.eql(u8, second.events[0].obligation_id, second.events[1].obligation_id));
    second.revision = 1;
    try std.testing.expectError(error.InvalidHistory, validateState(a, second));
}

fn temporaryPath(allocator: Allocator, directory: std.Io.Dir) ![]const u8 {
    try directory.setPermissions(std.testing.io, .fromMode(0o700));
    return directory.realPathFileAlloc(std.testing.io, ".", allocator);
}

test "real durable store reloads history, refuses stale writes and never implicitly resets missing history" {
    var arena: std.heap.ArenaAllocator = .init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();
    const path = try temporaryPath(a, tmp.dir);
    try std.testing.expectError(error.LockUnavailable, process(a, path, .{ .operation = .status }));
    _ = try process(a, path, .{ .operation = .initialize });
    const first = try process(a, path, .{ .operation = .record, .expected_revision = 0, .obligation = example() });
    try std.testing.expectEqual(@as(u64, 1), first.revision);
    const before = try tmp.dir.readFileAlloc(std.testing.io, "finish.json", a, .limited(max_bytes));
    try std.testing.expectError(error.StaleRevision, process(a, path, .{ .operation = .record, .expected_revision = 0, .obligation = example() }));
    try std.testing.expectError(error.HistoryAlreadyExists, process(a, path, .{ .operation = .initialize }));
    const reloaded = try process(a, path, .{ .operation = .status });
    try std.testing.expectEqual(@as(u64, 1), reloaded.revision);
    try std.testing.expectEqualStrings(first.events[0].obligation_id, reloaded.events[0].obligation_id);
    try std.testing.expectEqualStrings(before, try tmp.dir.readFileAlloc(std.testing.io, "finish.json", a, .limited(max_bytes)));
    try tmp.dir.deleteFile(std.testing.io, "finish.json");
    try std.testing.expectError(error.HistoryMissingOrUnavailable, process(a, path, .{ .operation = .record, .expected_revision = 0, .obligation = example() }));
    try std.testing.expectError(error.ExistingFinishHistoryRequiresRecovery, process(a, path, .{ .operation = .initialize }));
}

test "symlink history cannot follow or overwrite valuable evidence" {
    var arena: std.heap.ArenaAllocator = .init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();
    const path = try temporaryPath(a, tmp.dir);
    _ = try process(a, path, .{ .operation = .initialize });
    try tmp.dir.deleteFile(std.testing.io, "finish.json");
    const valuable = try tmp.dir.createFile(std.testing.io, "valuable.json", .{ .permissions = .fromMode(0o600) });
    try valuable.writeStreamingAll(std.testing.io, "preserve exact evidence");
    valuable.close(std.testing.io);
    const fd = try openRoot(a, path);
    defer _ = c.close(fd);
    try std.testing.expectEqual(@as(c_int, 0), c.symlinkat("valuable.json", fd, "finish.json"));
    try std.testing.expectError(error.HistoryMissingOrUnavailable, process(a, path, .{ .operation = .record, .expected_revision = 0, .obligation = example() }));
    try std.testing.expectError(error.HistoryAlreadyExists, process(a, path, .{ .operation = .initialize }));
    try std.testing.expectEqualStrings("preserve exact evidence", try tmp.dir.readFileAlloc(std.testing.io, "valuable.json", a, .limited(100)));
}

test "another writer hold and non-private directory refuse without advancing state" {
    var arena: std.heap.ArenaAllocator = .init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();
    const path = try temporaryPath(a, tmp.dir);
    _ = try process(a, path, .{ .operation = .initialize });
    const fd = try openRoot(a, path);
    defer _ = c.close(fd);
    const lock = c.openat(fd, "finish.lock", c.O_RDWR | c.O_CLOEXEC | c.O_NOFOLLOW);
    try std.testing.expect(lock >= 0);
    defer _ = c.close(lock);
    try std.testing.expectEqual(@as(c_int, 0), c.flock(lock, c.LOCK_EX | c.LOCK_NB));
    try std.testing.expectError(error.LockBusy, process(a, path, .{ .operation = .record, .expected_revision = 0, .obligation = example() }));
    try std.testing.expectEqual(@as(c_int, 0), c.flock(lock, c.LOCK_UN));
    try tmp.dir.setPermissions(std.testing.io, .fromMode(0o755));
    try std.testing.expectError(error.PrivateDirectoryRequired, process(a, path, .{ .operation = .status }));
    try tmp.dir.setPermissions(std.testing.io, .fromMode(0o700));
    try std.testing.expectEqual(@as(u64, 0), (try process(a, path, .{ .operation = .status })).revision);
}
