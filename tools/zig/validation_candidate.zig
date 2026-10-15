//! Private staged-tree capture. Never evaluates live source or registers a worktree.
//! The caller owns an arena for the returned manifest. This module's closed Git
//! plumbing is distinct from the later general validator execution backend.
const std = @import("std");
const builtin = @import("builtin");
// The installed Zig 0.16 Threaded pre-exec error path can lose its forked
// child and parent pipes before returning an error. Use the same SDK launch
// boundary qualified by validation_process_darwin, without changing Git stdin
// or this module's independent capture limits. No general executor is implied.
const git_c = if (builtin.os.tag == .macos) @cImport({
    @cInclude("unistd.h");
    @cInclude("fcntl.h");
    @cInclude("errno.h");
    @cInclude("sys/spawn.h");
}) else struct {};
const git_spawn = if (builtin.os.tag == .macos) @cImport({
    @cDefine("_POSIX_C_SOURCE", "200809L");
    @cInclude("spawn.h");
}) else struct {};
pub const Allocator = std.mem.Allocator;
pub const Value = std.json.Value;
const limit = 256 * 1024 * 1024;

pub fn object(value: Value) !std.json.ObjectMap {
    if (value != .object) return error.InvalidRequest;
    return value.object;
}

pub fn text(fields: std.json.ObjectMap, key: []const u8) ![]const u8 {
    const value = fields.get(key) orelse return error.MissingBinding;
    if (value != .string or value.string.len == 0 or value.string.len > 8192 or std.mem.indexOfScalar(u8, value.string, 0) != null) return error.InvalidBinding;
    return value.string;
}

pub fn fieldsOnly(value: Value, allowed: []const []const u8) !void {
    const fields = try object(value);
    var iterator = fields.iterator();
    while (iterator.next()) |entry| {
        var found = false;
        for (allowed) |key| {
            if (std.mem.eql(u8, key, entry.key_ptr.*)) found = true;
        }
        if (!found) return error.UnknownField;
    }
}

pub fn hash(allocator: Allocator, bytes: []const u8) ![]const u8 {
    var digest: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(bytes, &digest, .{});
    const hex = std.fmt.bytesToHex(digest, .lower);
    return allocator.dupe(u8, &hex);
}

pub fn read(allocator: Allocator, io: std.Io, path: []const u8) ![]const u8 {
    return std.Io.Dir.cwd().readFileAlloc(io, path, allocator, .limited(limit));
}

pub fn write(io: std.Io, path: []const u8, bytes: []const u8, mode: u16) !void {
    const file = try std.Io.Dir.cwd().createFile(io, path, .{ .exclusive = true, .permissions = .fromMode(mode) });
    defer file.close(io);
    try file.writeStreamingAll(io, bytes);
}

pub fn json(allocator: Allocator, value: anytype) ![]const u8 {
    var buffer: std.Io.Writer.Allocating = .init(allocator);
    defer buffer.deinit();
    var stringify: std.json.Stringify = .{ .writer = &buffer.writer };
    try stringify.write(value);
    try buffer.writer.writeByte('\n');
    return allocator.dupe(u8, buffer.written());
}

pub fn parse(allocator: Allocator, bytes: []const u8) !std.json.Parsed(Value) {
    return std.json.parseFromSlice(Value, allocator, bytes, .{ .duplicate_field_behavior = .@"error" });
}

fn makeDir(io: std.Io, path: []const u8) !void {
    try std.Io.Dir.cwd().createDir(io, path, .fromMode(0o700));
}

fn parents(allocator: Allocator, io: std.Io, path: []const u8) !void {
    _ = allocator;
    const parent = std.fs.path.dirname(path) orelse return error.UnsafePath;
    _ = try std.Io.Dir.cwd().createDirPathStatus(io, parent, .fromMode(0o700));
}

pub fn safeRelative(path: []const u8) bool {
    if (path.len == 0 or path.len > 4096 or path[0] == '/' or std.mem.indexOfScalar(u8, path, 0) != null) return false;
    var parts = std.mem.splitScalar(u8, path, '/');
    while (parts.next()) |part| {
        if (part.len == 0 or std.mem.eql(u8, part, ".") or std.mem.eql(u8, part, "..") or std.ascii.eqlIgnoreCase(part, ".git")) return false;
    }
    return true;
}

pub fn pathHex(allocator: Allocator, path: []const u8) ![]const u8 {
    const hex = try allocator.alloc(u8, path.len * 2);
    for (path, 0..) |byte, offset| {
        const alphabet = "0123456789abcdef";
        hex[offset * 2] = alphabet[byte >> 4];
        hex[offset * 2 + 1] = alphabet[byte & 15];
    }
    return hex;
}

pub const FileFingerprint = struct { path_hex: []const u8, kind: []const u8, sha256: []const u8, mode: u32 };

fn fileOrder(_: void, left: FileFingerprint, right: FileFingerprint) bool {
    return std.mem.lessThan(u8, left.path_hex, right.path_hex);
}

pub fn fingerprintDirectory(allocator: Allocator, io: std.Io, path: []const u8) ![]const FileFingerprint {
    var root = try std.Io.Dir.cwd().openDir(io, path, .{ .iterate = true });
    defer root.close(io);
    var walker = try root.walk(allocator);
    defer walker.deinit();
    var files: std.ArrayList(FileFingerprint) = .empty;
    while (try walker.next(io)) |entry| {
        var kind: []const u8 = "directory";
        var digest: []const u8 = "";
        if (entry.kind != .directory) {
            if (entry.kind != .file) return error.UnsupportedMetadataFile;
            kind = "file";
            digest = try hash(allocator, try root.readFileAlloc(io, entry.path, allocator, .limited(limit)));
        }
        const stat = try root.statFile(io, entry.path, .{});
        try files.append(allocator, .{ .path_hex = try pathHex(allocator, entry.path), .kind = kind, .sha256 = digest, .mode = stat.permissions.toMode() });
        if (files.items.len > 100000) return error.TreeLimit;
    }
    std.mem.sort(FileFingerprint, files.items, {}, fileOrder);
    return files.toOwnedSlice(allocator);
}

fn oid(value: []const u8) bool {
    if (value.len != 40 and value.len != 64) return false;
    for (value) |byte| {
        if (!std.ascii.isHex(byte) or std.ascii.isUpper(byte)) return false;
    }
    return true;
}

const Command = struct {
    argv: []const []const u8,
    stdout_sha256: []const u8,
    stderr_sha256: []const u8,
    stderr_path: ?[]const u8,
    exit_code: ?u8,
    direct_child_joined: bool,
};

pub const Context = struct {
    allocator: Allocator,
    io: std.Io,
    environment: *std.process.Environ.Map,
    git_executable: []const u8,
    repository: []const u8,
    evidence: ?[]const u8 = null,
    commands: std.ArrayList(Command) = .empty,

    fn git(self: *Context, tail: []const []const u8, input: ?[]const u8) ![]const u8 {
        var argv: std.ArrayList([]const u8) = .empty;
        try argv.appendSlice(self.allocator, &.{ self.git_executable, "--no-pager", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", self.repository });
        try argv.appendSlice(self.allocator, tail);
        var input_file: ?std.Io.File = null;
        defer if (input_file) |file| file.close(self.io);
        if (input) |path| {
            input_file = try std.Io.Dir.cwd().openFile(self.io, path, .{});
        }
        var child = try spawnGit(self, argv.items, input_file);
        defer child.kill(self.io);
        var buffers: std.Io.File.MultiReader.Buffer(2) = undefined;
        var reader: std.Io.File.MultiReader = undefined;
        reader.init(self.allocator, self.io, buffers.toStreams(), &.{ child.stdout.?, child.stderr.? });
        defer reader.deinit();
        const deadline = std.Io.Timeout.toDeadline(.{ .duration = .{ .raw = .fromSeconds(20), .clock = .awake } }, self.io);
        while (true) {
            _ = reader.fill(4096, deadline) catch |failure| {
                if (failure == error.EndOfStream) break;
                return failure;
            };
            if (reader.reader(0).buffered().len > limit or reader.reader(1).buffered().len > 1024 * 1024) return error.GitOutputLimit;
        }
        try reader.checkAnyError();
        const term = try child.wait(self.io);
        const stdout = try reader.toOwnedSlice(0);
        const stderr = try reader.toOwnedSlice(1);
        var stderr_path: ?[]const u8 = null;
        if (self.evidence) |directory| {
            stderr_path = try std.fmt.allocPrint(self.allocator, "{s}/git-{d}.stderr.log", .{ directory, self.commands.items.len });
            try write(self.io, stderr_path.?, stderr, 0o600);
        }
        var exit_code: ?u8 = null;
        if (term == .exited) exit_code = term.exited;
        try self.commands.append(self.allocator, .{ .argv = argv.items, .stdout_sha256 = try hash(self.allocator, stdout), .stderr_sha256 = try hash(self.allocator, stderr), .stderr_path = stderr_path, .exit_code = exit_code, .direct_child_joined = true });
        if (exit_code == null or exit_code.? != 0) return error.GitRefused;
        return stdout;
    }

    fn line(self: *Context, tail: []const []const u8) ![]const u8 {
        const result = try self.git(tail, null);
        if (result.len == 0 or result[result.len - 1] != '\n' or std.mem.indexOfScalar(u8, result, 0) != null) return error.GitIdentityRefused;
        // Remove ONLY Git's terminal separator: embedded path newlines remain data.
        return result[0 .. result.len - 1];
    }
};

fn gitPipe() ![2]c_int {
    var descriptors: [2]c_int = undefined;
    if (git_c.pipe(&descriptors) != 0) return error.PipeCreationFailed;
    errdefer {
        _ = git_c.close(descriptors[0]);
        _ = git_c.close(descriptors[1]);
    }
    // Preserve callers with a closed standard descriptor. No temporary pipe
    // endpoint may be overwritten by a child stdin/stdout/stderr file action.
    for (&descriptors) |*fd| {
        const duplicate = git_c.fcntl(fd.*, git_c.F_DUPFD_CLOEXEC, @as(c_int, 3));
        if (duplicate < 0) return error.PipeCreationFailed;
        _ = git_c.close(fd.*);
        fd.* = duplicate;
    }
    return descriptors;
}

fn spawnGit(context: *Context, arguments: []const []const u8, input: ?std.Io.File) !std.process.Child {
    var arena = std.heap.ArenaAllocator.init(context.allocator);
    defer arena.deinit();
    const allocator = arena.allocator();
    const argv = try allocator.allocSentinel(?[*:0]u8, arguments.len, null);
    for (arguments, 0..) |argument, index| {
        if (std.mem.indexOfScalar(u8, argument, 0) != null) return error.InvalidArguments;
        argv[index] = (try allocator.dupeZ(u8, argument)).ptr;
    }
    for (context.environment.keys(), context.environment.values()) |key, value| {
        if (key.len == 0 or std.mem.indexOfAny(u8, key, "=\x00") != null or std.mem.indexOfScalar(u8, value, 0) != null) return error.InvalidEnvironment;
    }
    const environment = try context.environment.createPosixBlock(allocator, .{});
    var actions: git_spawn.posix_spawn_file_actions_t = null;
    if (git_spawn.posix_spawn_file_actions_init(&actions) != 0) return error.SpawnSetupFailed;
    var actions_active = true;
    defer if (actions_active) {
        _ = git_spawn.posix_spawn_file_actions_destroy(&actions);
    };
    var attributes: git_spawn.posix_spawnattr_t = null;
    if (git_spawn.posix_spawnattr_init(&attributes) != 0) return error.SpawnSetupFailed;
    var attributes_active = true;
    defer if (attributes_active) {
        _ = git_spawn.posix_spawnattr_destroy(&attributes);
    };
    if (git_spawn.posix_spawnattr_setflags(&attributes, git_c.POSIX_SPAWN_CLOEXEC_DEFAULT) != 0) return error.SpawnSetupFailed;
    if (input) |file| {
        if (git_spawn.posix_spawn_file_actions_adddup2(&actions, file.handle, 0) != 0) return error.SpawnSetupFailed;
    } else if (git_spawn.posix_spawn_file_actions_addopen(&actions, 0, "/dev/null", git_c.O_RDONLY, 0) != 0) return error.SpawnSetupFailed;
    const out = try gitPipe();
    defer _ = git_c.close(out[1]);
    var out_owned = true;
    errdefer if (out_owned) {
        _ = git_c.close(out[0]);
    };
    const err = try gitPipe();
    defer _ = git_c.close(err[1]);
    var err_owned = true;
    errdefer if (err_owned) {
        _ = git_c.close(err[0]);
    };
    if (git_spawn.posix_spawn_file_actions_adddup2(&actions, out[1], 1) != 0 or git_spawn.posix_spawn_file_actions_adddup2(&actions, err[1], 2) != 0) return error.SpawnSetupFailed;
    try context.io.checkCancel();
    var pid: git_c.pid_t = 0;
    const spawn_error = git_spawn.posix_spawn(&pid, argv[0].?, &actions, &attributes, @ptrCast(argv.ptr), @ptrCast(environment.slice.ptr));
    const actions_error = git_spawn.posix_spawn_file_actions_destroy(&actions);
    actions_active = false;
    const attributes_error = git_spawn.posix_spawnattr_destroy(&attributes);
    attributes_active = false;
    if (spawn_error != 0) {
        if (spawn_error == git_c.ENOENT) return error.FileNotFound;
        if (spawn_error == git_c.EACCES) return error.AccessDenied;
        if (spawn_error == git_c.ENOEXEC) return error.InvalidExe;
        return error.SpawnFailed;
    }
    var child: std.process.Child = .{
        .id = pid,
        .thread_handle = {},
        .stdin = null,
        .stdout = .{ .handle = out[0], .flags = .{ .nonblocking = false } },
        .stderr = .{ .handle = err[0], .flags = .{ .nonblocking = false } },
        .request_resource_usage_statistics = false,
    };
    // Transfer read-end custody once, before any postlaunch error cleanup.
    // Child.kill retains the exact direct child and closes these two handles.
    out_owned = false;
    err_owned = false;
    if (actions_error != 0 or attributes_error != 0) {
        child.kill(context.io);
        return error.SpawnMetadataCleanupFailed;
    }
    return child;
}

pub const Entry = struct {
    path_hex: []const u8,
    mode: []const u8,
    oid: []const u8,
    sha256: []const u8 = "",
};

const SharedIndex = struct { path: []const u8, sha256: []const u8, mtime_ns: i96 };

pub const Manifest = struct {
    schema_version: u8 = 1,
    repository: []const u8,
    git_directory: []const u8,
    common_directory: []const u8,
    object_directory: []const u8,
    index_path: []const u8,
    index_sha256: []const u8,
    shared_indexes: []const SharedIndex,
    head: []const u8,
    base_reference: []const u8,
    base: []const u8,
    candidate_tree: []const u8,
    root: []const u8,
    git_executable: []const u8,
    git_executable_sha256: []const u8,
    private_git_files: []const FileFingerprint,
    paths: []const Entry,
    git_commands: []const Command,
    capture_only: bool = true,
    acceptance_performed: bool = false,
};

fn treeEntries(allocator: Allocator, bytes: []const u8) ![]Entry {
    if (bytes.len == 0) return allocator.alloc(Entry, 0);
    if (bytes[bytes.len - 1] != 0) return error.MalformedTree;
    var result: std.ArrayList(Entry) = .empty;
    var seen = std.StringHashMap(void).init(allocator);
    defer seen.deinit();
    var rows = std.mem.splitScalar(u8, bytes[0 .. bytes.len - 1], 0);
    while (rows.next()) |row| {
        const tab = std.mem.indexOfScalar(u8, row, '\t') orelse return error.MalformedTree;
        const path = row[tab + 1 ..];
        if (!safeRelative(path)) return error.UnsafePath;
        var header = std.mem.splitScalar(u8, row[0..tab], ' ');
        const mode = header.next() orelse return error.MalformedTree;
        const kind = header.next() orelse return error.MalformedTree;
        const identity = header.next() orelse return error.MalformedTree;
        if (std.mem.eql(u8, mode, "160000")) return error.UnsupportedGitlink;
        if (!std.mem.eql(u8, kind, "blob") or header.next() != null or !oid(identity)) return error.MalformedTree;
        if (!std.mem.eql(u8, mode, "100644") and !std.mem.eql(u8, mode, "100755") and !std.mem.eql(u8, mode, "120000")) return error.UnsupportedMode;
        const hex = try pathHex(allocator, path);
        const unique = try seen.getOrPut(hex);
        if (unique.found_existing) return error.DuplicatePath;
        try result.append(allocator, .{ .path_hex = hex, .mode = mode, .oid = identity });
        if (result.items.len > 100000) return error.TreeLimit;
    }
    return result.toOwnedSlice(allocator);
}

pub fn decodePath(allocator: Allocator, value: []const u8) ![]const u8 {
    if (value.len == 0 or value.len % 2 != 0 or value.len > 8192) return error.UnsafePath;
    const result = try allocator.alloc(u8, value.len / 2);
    _ = std.fmt.hexToBytes(result, value) catch return error.UnsafePath;
    if (!safeRelative(result)) return error.UnsafePath;
    return result;
}

fn objectMatches(identity: []const u8, bytes: []const u8) bool {
    var buffer: [64]u8 = undefined;
    const header = std.fmt.bufPrint(&buffer, "blob {d}\x00", .{bytes.len}) catch return false;
    if (identity.len == 40) {
        var hasher = std.crypto.hash.Sha1.init(.{});
        hasher.update(header);
        hasher.update(bytes);
        const hex = std.fmt.bytesToHex(hasher.finalResult(), .lower);
        return std.mem.eql(u8, identity, &hex);
    }
    var hasher = std.crypto.hash.sha2.Sha256.init(.{});
    hasher.update(header);
    hasher.update(bytes);
    const hex = std.fmt.bytesToHex(hasher.finalResult(), .lower);
    return std.mem.eql(u8, identity, &hex);
}

fn materialize(context: *Context, root: []const u8, entries: []Entry, bytes: []const u8) !void {
    var offset: usize = 0;
    var contents: std.ArrayList([]const u8) = .empty;
    for (entries) |*entry| {
        const end = std.mem.indexOfScalarPos(u8, bytes, offset, '\n') orelse return error.MalformedBlob;
        var header = std.mem.splitScalar(u8, bytes[offset..end], ' ');
        const identity = header.next() orelse return error.MalformedBlob;
        const kind = header.next() orelse return error.MalformedBlob;
        const size_text = header.next() orelse return error.MalformedBlob;
        if (!std.mem.eql(u8, identity, entry.oid) or !std.mem.eql(u8, kind, "blob") or header.next() != null) return error.MalformedBlob;
        const size = std.fmt.parseInt(usize, size_text, 10) catch return error.MalformedBlob;
        offset = end + 1;
        if (size > bytes.len - offset or size == bytes.len - offset) return error.MalformedBlob;
        const content = bytes[offset .. offset + size];
        offset += size;
        if (bytes[offset] != '\n' or !objectMatches(entry.oid, content)) return error.CorruptBlob;
        offset += 1;
        entry.sha256 = try hash(context.allocator, content);
        try contents.append(context.allocator, content);
        if (std.mem.eql(u8, entry.mode, "120000")) {
            if (!safeRelative(content)) return error.UnsafeSymlink;
            continue;
        }
        const path = try std.fmt.allocPrint(context.allocator, "{s}/{s}", .{ root, try decodePath(context.allocator, entry.path_hex) });
        try parents(context.allocator, context.io, path);
        var mode: u16 = 0o644;
        if (std.mem.eql(u8, entry.mode, "100755")) mode = 0o755;
        try write(context.io, path, content, mode);
    }
    if (offset != bytes.len) return error.MalformedBlob;
    // Create links last; no materialized regular file can follow a staged link.
    for (entries, contents.items) |entry, content| {
        if (!std.mem.eql(u8, entry.mode, "120000")) continue;
        const path = try std.fmt.allocPrint(context.allocator, "{s}/{s}", .{ root, try decodePath(context.allocator, entry.path_hex) });
        try parents(context.allocator, context.io, path);
        try std.Io.Dir.cwd().symLink(context.io, content, path, .{});
    }
}

fn gitEnvironment(allocator: Allocator, inherited: *const std.process.Environ.Map) !std.process.Environ.Map {
    var environment = try inherited.clone(allocator);
    errdefer environment.deinit();
    var iterator = inherited.array_hash_map.iterator();
    while (iterator.next()) |entry| {
        if (!std.mem.startsWith(u8, entry.key_ptr.*, "GIT_")) continue;
        var context_key = false;
        for ([_][]const u8{ "GIT_DIR", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES" }) |key| {
            if (std.mem.eql(u8, key, entry.key_ptr.*)) context_key = true;
        }
        if (!context_key) _ = environment.swapRemove(entry.key_ptr.*);
    }
    try environment.put("GIT_CONFIG_NOSYSTEM", "1");
    try environment.put("GIT_CONFIG_GLOBAL", "/dev/null");
    try environment.put("GIT_NO_REPLACE_OBJECTS", "1");
    return environment;
}

pub fn capture(allocator: Allocator, io: std.Io, inherited: *const std.process.Environ.Map, request: Value) !Manifest {
    if (builtin.os.tag != .macos) return error.PlatformUnqualified;
    try fieldsOnly(request, &.{ "schema_version", "repository", "base", "destination", "git_executable" });
    const fields = try object(request);
    const schema = fields.get("schema_version") orelse return error.InvalidRequest;
    if (schema != .integer or schema.integer != 1) return error.InvalidRequest;
    const repository = try text(fields, "repository");
    const base_reference = try text(fields, "base");
    const destination = try text(fields, "destination");
    const executable = try text(fields, "git_executable");
    if (!std.fs.path.isAbsolute(repository) or !std.fs.path.isAbsolute(destination) or !std.fs.path.isAbsolute(executable) or base_reference[0] == '-') return error.InvalidRequest;
    if (std.mem.indexOfAny(u8, destination, "\r\n") != null) return error.UnsafeDestination;
    var environment = try gitEnvironment(allocator, inherited);
    defer environment.deinit();
    var context = Context{ .allocator = allocator, .io = io, .environment = &environment, .git_executable = executable, .repository = repository };
    const root_repository = try context.line(&.{ "rev-parse", "--path-format=absolute", "--show-toplevel" });
    const expected_repository = try std.Io.Dir.cwd().realPathFileAlloc(io, repository, allocator);
    if (!std.mem.eql(u8, root_repository, expected_repository)) return error.RepositoryContextMismatch;
    const git_directory = try context.line(&.{ "rev-parse", "--path-format=absolute", "--git-dir" });
    const common_directory = try context.line(&.{ "rev-parse", "--path-format=absolute", "--git-common-dir" });
    const index = try context.line(&.{ "rev-parse", "--path-format=absolute", "--git-path", "index" });
    const object_directory = try context.line(&.{ "rev-parse", "--path-format=absolute", "--git-path", "objects" });
    const object_format = try context.line(&.{ "rev-parse", "--show-object-format" });
    if (!std.mem.eql(u8, object_format, "sha1") and !std.mem.eql(u8, object_format, "sha256")) return error.UnsupportedObjectFormat;
    const head = try context.line(&.{ "rev-parse", "--verify", "HEAD^{commit}" });
    const base_arg = try std.fmt.allocPrint(allocator, "{s}^{{commit}}", .{base_reference});
    const base = try context.line(&.{ "rev-parse", "--verify", base_arg });
    if (!oid(head) or !oid(base)) return error.GitIdentityRefused;
    const index_bytes = try read(allocator, io, index);
    const index_digest = try hash(allocator, index_bytes);
    const destination_parent = std.fs.path.dirname(destination) orelse return error.UnsafeDestination;
    const parent = try std.Io.Dir.cwd().realPathFileAlloc(io, destination_parent, allocator);
    const directory = try std.fmt.allocPrint(allocator, "{s}/{s}", .{ parent, std.fs.path.basename(destination) });
    for ([_][]const u8{ root_repository, common_directory }) |protected| {
        if (std.mem.eql(u8, directory, protected) or (std.mem.startsWith(u8, directory, protected) and directory.len > protected.len and directory[protected.len] == '/')) return error.UnsafeDestination;
    }
    if (std.mem.eql(u8, std.fs.path.basename(directory), ".") or std.mem.eql(u8, std.fs.path.basename(directory), "..")) return error.UnsafeDestination;
    try makeDir(io, directory);
    context.evidence = directory;
    const root = try std.fmt.allocPrint(allocator, "{s}/candidate", .{directory});
    const private_git = try std.fmt.allocPrint(allocator, "{s}/git", .{directory});
    const objects = try std.fmt.allocPrint(allocator, "{s}/objects", .{private_git});
    try makeDir(io, root);
    try makeDir(io, private_git);
    try makeDir(io, objects);
    const copied_index = try std.fmt.allocPrint(allocator, "{s}/source.index", .{directory});
    try write(io, copied_index, index_bytes, 0o600);
    const private_index = try std.fmt.allocPrint(allocator, "{s}/index", .{private_git});
    _ = environment.swapRemove("GIT_COMMON_DIR");
    try environment.put("GIT_DIR", private_git);
    _ = environment.swapRemove("GIT_WORK_TREE");
    try environment.put("GIT_INDEX_FILE", private_index);
    try environment.put("GIT_OBJECT_DIRECTORY", objects);
    const quoted_objects = try std.json.Stringify.valueAlloc(allocator, object_directory, .{});
    try environment.put("GIT_ALTERNATE_OBJECT_DIRECTORIES", quoted_objects);
    const format_arg = try std.fmt.allocPrint(allocator, "--object-format={s}", .{object_format});
    _ = try context.git(&.{ "init", "--bare", "--template=", "--quiet", format_arg }, null);
    try environment.put("GIT_WORK_TREE", root);
    _ = try context.git(&.{ "config", "core.bare", "false" }, null);
    _ = try context.git(&.{ "config", "core.worktree", root }, null);
    try write(io, private_index, index_bytes, 0o600);
    // Reading a split index through the live Git dir freshens its shared base's
    // mtime. Copy bases using filesystem reads, then use ONLY the private Git dir.
    var shared: std.ArrayList(SharedIndex) = .empty;
    var common = try std.Io.Dir.cwd().openDir(io, common_directory, .{ .iterate = true });
    defer common.close(io);
    var shared_files = common.iterate();
    while (try shared_files.next(io)) |entry| {
        if (!std.mem.startsWith(u8, entry.name, "sharedindex.")) continue;
        if (!oid(entry.name[12..]) or entry.kind != .file) return error.UnsupportedSharedIndex;
        const source_path = try std.fmt.allocPrint(allocator, "{s}/{s}", .{ common_directory, entry.name });
        const source_file = try common.openFile(io, entry.name, .{});
        defer source_file.close(io);
        const stat = try source_file.stat(io);
        const content = try read(allocator, io, source_path);
        try shared.append(allocator, .{ .path = source_path, .sha256 = try hash(allocator, content), .mtime_ns = stat.mtime.nanoseconds });
        try write(io, try std.fmt.allocPrint(allocator, "{s}/{s}", .{ private_git, entry.name }), content, 0o600);
        if (shared.items.len > 256) return error.SharedIndexLimit;
    }
    const tree = try context.line(&.{"write-tree"});
    if (!oid(tree)) return error.GitIdentityRefused;
    const entries = try treeEntries(allocator, try context.git(&.{ "ls-tree", "-r", "-z", "--full-tree", tree }, null));
    var batch: std.Io.Writer.Allocating = .init(allocator);
    for (entries) |entry| {
        try batch.writer.writeAll(entry.oid);
        try batch.writer.writeByte('\n');
    }
    const batch_input = try std.fmt.allocPrint(allocator, "{s}/blob-requests", .{directory});
    try write(io, batch_input, batch.written(), 0o600);
    const blobs = try context.git(&.{ "cat-file", "--batch" }, batch_input);
    try materialize(&context, root, entries, blobs);
    const alternatives = try std.fmt.allocPrint(allocator, "{s}/info/alternates", .{objects});
    try write(io, alternatives, try std.fmt.allocPrint(allocator, "{s}\n", .{quoted_objects}), 0o600);
    const old_head_path = try std.fmt.allocPrint(allocator, "{s}/HEAD", .{private_git});
    const head_file = try std.Io.Dir.cwd().createFile(io, old_head_path, .{ .permissions = .fromMode(0o600) });
    defer head_file.close(io);
    try head_file.writeStreamingAll(io, try std.fmt.allocPrint(allocator, "{s}\n", .{head}));
    try write(io, try std.fmt.allocPrint(allocator, "{s}/.git", .{root}), try std.fmt.allocPrint(allocator, "gitdir: {s}\n", .{private_git}), 0o600);
    _ = try context.git(&.{ "update-index", "--refresh" }, null);
    const private_files = try fingerprintDirectory(allocator, io, private_git);
    if (!std.mem.eql(u8, index_digest, try hash(allocator, try read(allocator, io, index)))) return error.InputDrift;
    for (shared.items) |input| {
        const file = try std.Io.Dir.cwd().openFile(io, input.path, .{});
        defer file.close(io);
        const stat = try file.stat(io);
        if (stat.mtime.nanoseconds != input.mtime_ns or !std.mem.eql(u8, input.sha256, try hash(allocator, try read(allocator, io, input.path)))) return error.InputDrift;
    }
    // Final parent/base observations use the ORIGINAL context, never private HEAD.
    _ = environment.swapRemove("GIT_DIR");
    _ = environment.swapRemove("GIT_WORK_TREE");
    _ = environment.swapRemove("GIT_INDEX_FILE");
    for ([_][]const u8{ "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR" }) |key| {
        if (inherited.get(key)) |value| try environment.put(key, value);
    }
    if (!std.mem.eql(u8, head, try context.line(&.{ "rev-parse", "--verify", "HEAD^{commit}" })) or !std.mem.eql(u8, base, try context.line(&.{ "rev-parse", "--verify", base_arg }))) return error.InputDrift;
    const manifest = Manifest{ .repository = root_repository, .git_directory = git_directory, .common_directory = common_directory, .object_directory = object_directory, .index_path = index, .index_sha256 = index_digest, .shared_indexes = shared.items, .head = head, .base_reference = base_reference, .base = base, .candidate_tree = tree, .root = root, .git_executable = executable, .git_executable_sha256 = try hash(allocator, try read(allocator, io, executable)), .private_git_files = private_files, .paths = entries, .git_commands = context.commands.items };
    try write(io, try std.fmt.allocPrint(allocator, "{s}/candidate.json", .{directory}), try json(allocator, manifest), 0o600);
    return manifest;
}

pub fn verify(allocator: Allocator, io: std.Io, inherited: *const std.process.Environ.Map, value: Value) !void {
    if (builtin.os.tag != .macos) return error.PlatformUnqualified;
    const fields = try object(value);
    const names = std.meta.fieldNames(Manifest);
    if (fields.count() != names.len) return error.InvalidManifest;
    for (names) |name| {
        if (!fields.contains(name)) return error.InvalidManifest;
    }
    const parsed = try std.json.parseFromSlice(Manifest, allocator, try json(allocator, value), .{ .duplicate_field_behavior = .@"error" });
    const manifest = parsed.value;
    if (manifest.schema_version != 1 or !manifest.capture_only or manifest.acceptance_performed or !oid(manifest.head) or !oid(manifest.base) or !oid(manifest.candidate_tree)) return error.InvalidManifest;
    if (!std.fs.path.isAbsolute(manifest.repository) or !std.fs.path.isAbsolute(manifest.root) or !std.fs.path.isAbsolute(manifest.git_executable) or manifest.base_reference.len == 0 or manifest.base_reference[0] == '-') return error.InvalidManifest;
    if (!std.mem.eql(u8, manifest.git_executable_sha256, try hash(allocator, try read(allocator, io, manifest.git_executable)))) return error.ToolDrift;
    var environment = try gitEnvironment(allocator, inherited);
    defer environment.deinit();
    var context = Context{ .allocator = allocator, .io = io, .environment = &environment, .git_executable = manifest.git_executable, .repository = manifest.repository };
    if (!std.mem.eql(u8, manifest.repository, try context.line(&.{ "rev-parse", "--path-format=absolute", "--show-toplevel" }))) return error.RepositoryContextMismatch;
    if (!std.mem.eql(u8, manifest.git_directory, try context.line(&.{ "rev-parse", "--path-format=absolute", "--git-dir" })) or !std.mem.eql(u8, manifest.common_directory, try context.line(&.{ "rev-parse", "--path-format=absolute", "--git-common-dir" })) or !std.mem.eql(u8, manifest.object_directory, try context.line(&.{ "rev-parse", "--path-format=absolute", "--git-path", "objects" }))) return error.RepositoryContextMismatch;
    const index = try context.line(&.{ "rev-parse", "--path-format=absolute", "--git-path", "index" });
    if (!std.mem.eql(u8, index, manifest.index_path) or !std.mem.eql(u8, manifest.index_sha256, try hash(allocator, try read(allocator, io, index)))) return error.IndexDrift;
    if (!std.mem.eql(u8, manifest.head, try context.line(&.{ "rev-parse", "--verify", "HEAD^{commit}" }))) return error.ParentDrift;
    const base_arg = try std.fmt.allocPrint(allocator, "{s}^{{commit}}", .{manifest.base_reference});
    if (!std.mem.eql(u8, manifest.base, try context.line(&.{ "rev-parse", "--verify", base_arg }))) return error.BaseDrift;
    for (manifest.shared_indexes) |input| {
        const file = try std.Io.Dir.cwd().openFile(io, input.path, .{});
        defer file.close(io);
        const stat = try file.stat(io);
        if (stat.mtime.nanoseconds != input.mtime_ns or !std.mem.eql(u8, input.sha256, try hash(allocator, try read(allocator, io, input.path)))) return error.IndexDrift;
    }
    const actual_root = try std.Io.Dir.cwd().realPathFileAlloc(io, manifest.root, allocator);
    if (!std.mem.eql(u8, actual_root, manifest.root)) return error.SnapshotDrift;
    var entries = std.StringHashMap(Entry).init(allocator);
    defer entries.deinit();
    var directories = std.StringHashMap(void).init(allocator);
    defer directories.deinit();
    for (manifest.paths) |entry| {
        if (!oid(entry.oid) or entry.sha256.len != 64) return error.InvalidManifest;
        if (!std.mem.eql(u8, entry.mode, "100644") and !std.mem.eql(u8, entry.mode, "100755") and !std.mem.eql(u8, entry.mode, "120000")) return error.InvalidManifest;
        const path = try decodePath(allocator, entry.path_hex);
        const row = try entries.getOrPut(path);
        if (row.found_existing) return error.InvalidManifest;
        row.value_ptr.* = entry;
        var parent = std.fs.path.dirname(path);
        while (parent) |directory| {
            try directories.put(directory, {});
            parent = std.fs.path.dirname(directory);
        }
    }
    var root = try std.Io.Dir.cwd().openDir(io, manifest.root, .{ .iterate = true });
    defer root.close(io);
    var walker = try root.walk(allocator);
    defer walker.deinit();
    var seen: usize = 0;
    var git_seen = false;
    while (try walker.next(io)) |item| {
        if (item.kind == .directory) {
            if (!directories.contains(item.path)) return error.UnexpectedSnapshotInput;
            continue;
        }
        if (std.mem.eql(u8, item.path, ".git")) {
            const expected = try std.fmt.allocPrint(allocator, "gitdir: {s}/git\n", .{std.fs.path.dirname(manifest.root).?});
            if (item.kind != .file or !std.mem.eql(u8, expected, try root.readFileAlloc(io, item.path, allocator, .limited(8192)))) return error.SnapshotDrift;
            git_seen = true;
            continue;
        }
        const entry = entries.get(item.path) orelse return error.UnexpectedSnapshotInput;
        const path = try std.fmt.allocPrint(allocator, "{s}/{s}", .{ manifest.root, item.path });
        var contents: []const u8 = undefined;
        if (std.mem.eql(u8, entry.mode, "120000")) {
            if (item.kind != .sym_link) return error.SnapshotModeDrift;
            const buffer = try allocator.alloc(u8, 4096);
            const count = try root.readLink(io, item.path, buffer);
            contents = buffer[0..count];
        } else {
            if (item.kind != .file) return error.SnapshotModeDrift;
            const file = try root.openFile(io, item.path, .{});
            defer file.close(io);
            const stat = try file.stat(io);
            const executable = stat.permissions.toMode() & 0o111 != 0;
            if (std.mem.eql(u8, entry.mode, "100755") != executable) return error.SnapshotModeDrift;
            contents = try read(allocator, io, path);
        }
        if (!std.mem.eql(u8, entry.sha256, try hash(allocator, contents)) or !objectMatches(entry.oid, contents)) return error.SnapshotDrift;
        seen += 1;
    }
    if (seen != manifest.paths.len or !git_seen) return error.MissingSnapshotInput;
    const private_git = try std.fmt.allocPrint(allocator, "{s}/git", .{std.fs.path.dirname(manifest.root).?});
    const metadata = try fingerprintDirectory(allocator, io, private_git);
    if (!std.mem.eql(u8, try json(allocator, metadata), try json(allocator, manifest.private_git_files))) return error.PrivateGitDrift;
    // A syntactically valid tree ID must describe these exact paths and modes.
    // Only the private index may be consumed; live split-index bases stay private.
    var private_environment = try gitEnvironment(allocator, inherited);
    defer private_environment.deinit();
    for ([_][]const u8{ "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_INDEX_FILE" }) |key| {
        _ = private_environment.swapRemove(key);
    }
    try private_environment.put("GIT_DIR", private_git);
    try private_environment.put("GIT_WORK_TREE", manifest.root);
    try private_environment.put("GIT_INDEX_FILE", try std.fmt.allocPrint(allocator, "{s}/index", .{private_git}));
    var private_context = Context{ .allocator = allocator, .io = io, .environment = &private_environment, .git_executable = manifest.git_executable, .repository = manifest.root };
    if (!std.mem.eql(u8, manifest.candidate_tree, try private_context.line(&.{"write-tree"}))) return error.TreeIdentityMismatch;
    const tree_entries = try treeEntries(allocator, try private_context.git(&.{ "ls-tree", "-r", "-z", "--full-tree", manifest.candidate_tree }, null));
    if (tree_entries.len != manifest.paths.len) return error.TreeIdentityMismatch;
    for (tree_entries) |entry| {
        const expected = entries.get(try decodePath(allocator, entry.path_hex)) orelse return error.TreeIdentityMismatch;
        if (!std.mem.eql(u8, expected.oid, entry.oid) or !std.mem.eql(u8, expected.mode, entry.mode)) return error.TreeIdentityMismatch;
    }
    if (!std.mem.eql(u8, try json(allocator, manifest.private_git_files), try json(allocator, try fingerprintDirectory(allocator, io, private_git)))) return error.PrivateGitDrift;
    // Last sampling boundary; external mutation after return is not reserved.
    if (!std.mem.eql(u8, manifest.index_sha256, try hash(allocator, try read(allocator, io, index)))) return error.IndexDrift;
    if (!std.mem.eql(u8, manifest.head, try context.line(&.{ "rev-parse", "--verify", "HEAD^{commit}" }))) return error.ParentDrift;
    if (!std.mem.eql(u8, manifest.base, try context.line(&.{ "rev-parse", "--verify", base_arg }))) return error.BaseDrift;
}

fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len != 3) return error.InvalidArguments;
    const bytes = try read(allocator, init.io, args[2]);
    const request = try parse(allocator, bytes);
    if (std.mem.eql(u8, args[1], "capture")) {
        const manifest = try capture(allocator, init.io, init.environ_map, request.value);
        try std.Io.File.stdout().writeStreamingAll(init.io, try json(allocator, manifest));
    } else if (std.mem.eql(u8, args[1], "verify")) {
        try verify(allocator, init.io, init.environ_map, request.value);
        try std.Io.File.stdout().writeStreamingAll(init.io, try json(allocator, .{ .candidate_identity_current = true, .acceptance_performed = false }));
    } else return error.InvalidArguments;
}

pub fn main(init: std.process.Init) void {
    run(init) catch |failure| std.process.fatal("candidate refused: {s}", .{@errorName(failure)});
}
