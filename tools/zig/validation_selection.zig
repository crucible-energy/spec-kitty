const std = @import("std");
const Allocator = std.mem.Allocator;
const Value = std.json.Value;

pub const Selection = struct {
    matched_groups: []const []const u8,
    unmatched_src: bool,
    selected_jobs: []const []const u8,
    selected_code_shards: []const []const u8,
    selection_only: bool = true,
    validation_performed: bool = false,

    pub fn deinit(self: Selection, allocator: Allocator) void {
        allocator.free(self.matched_groups);
        allocator.free(self.selected_jobs);
        allocator.free(self.selected_code_shards);
    }
};

fn object(value: Value) !std.json.ObjectMap {
    if (value != .object) return error.InvalidRouting;
    return value.object;
}
fn strings(value: Value) ![]const Value {
    if (value != .array) return error.InvalidRouting;
    for (value.array.items) |item| {
        if (item != .string or item.string.len == 0) return error.InvalidRouting;
    }
    return value.array.items;
}
fn probe(name: []const u8) bool {
    return std.mem.eql(u8, name, "any_src");
}
fn sourceGroup(filters: std.json.ObjectMap, name: []const u8) bool {
    if (probe(name)) return false;
    for (filters.get(name).?.array.items) |pattern| {
        if (std.mem.startsWith(u8, pattern.string, "src/")) return true;
    }
    return false;
}
fn ordered(_: void, a: []const u8, b: []const u8) bool {
    return std.mem.lessThan(u8, a, b);
}

fn validIdentifier(value: []const u8) bool {
    if (value.len == 0 or !std.ascii.isAlphanumeric(value[0])) return false;
    for (value[1..]) |character| {
        if (!std.ascii.isAlphanumeric(character) and character != '_' and character != '-' and character != '.') return false;
    }
    return true;
}

fn rejectUnknownFields(value: Value, allowed: []const []const u8) !void {
    const fields = try object(value);
    var iterator = fields.iterator();
    while (iterator.next()) |entry| {
        var recognized = false;
        for (allowed) |name| {
            if (std.mem.eql(u8, entry.key_ptr.*, name)) {
                recognized = true;
                break;
            }
        }
        if (!recognized) return error.UnknownField;
    }
}

fn validateSource(value: Value) !void {
    try rejectUnknownFields(value, &.{ "path", "sha256", "role" });
    const fields = try object(value);
    const path = fields.get("path") orelse return error.InvalidSource;
    const digest = fields.get("sha256") orelse return error.InvalidSource;
    const role = fields.get("role") orelse return error.InvalidSource;
    if (path != .string or path.string.len == 0 or digest != .string or digest.string.len != 64 or role != .string or role.string.len == 0) return error.InvalidSource;
    for (digest.string) |character| {
        if (!std.ascii.isHex(character)) return error.InvalidSource;
    }
}

fn validateOptionalSections(root: std.json.ObjectMap) !void {
    if (root.get("source")) |source| try validateSource(source);
    if (root.get("modules")) |modules| {
        if (modules != .array) return error.InvalidModules;
        for (modules.array.items) |row| {
            try rejectUnknownFields(row, &.{ "module", "roots", "test_dirs", "cov_targets", "shard_count", "tier" });
            const fields = try object(row);
            const name = fields.get("module") orelse return error.InvalidModules;
            if (name != .string or !validIdentifier(name.string)) return error.InvalidModules;
        }
    }
    if (root.get("checks")) |checks_value| {
        const checks = try object(checks_value);
        var iterator = checks.iterator();
        while (iterator.next()) |entry| {
            if (!validIdentifier(entry.key_ptr.*)) return error.InvalidChecks;
            try rejectUnknownFields(entry.value_ptr.*, &.{ "argv", "modes", "platforms", "dependencies", "environment", "budgets" });
            const check_fields = try object(entry.value_ptr.*);
            if (check_fields.get("budgets")) |budgets| {
                try rejectUnknownFields(budgets, &.{ "wall_ms", "cleanup_ms", "stdout_bytes", "stderr_bytes", "sampled_processes", "sampled_resident_bytes" });
            }
        }
    }
}

/// The pinned current routing uses literal bytes and star globs only.
/// Stars span slash, matching the existing fnmatch authority. Unsupported
/// syntax refuses rather than narrowing a check selection silently.
pub fn matches(pattern: []const u8, path: []const u8) !bool {
    if (pattern.len == 0 or std.mem.indexOfAny(u8, pattern, "?[]") != null) return error.UnsupportedPattern;
    var pi: usize = 0;
    var vi: usize = 0;
    var star: ?usize = null;
    var retry: usize = 0;
    while (vi < path.len) {
        if (pi < pattern.len and pattern[pi] == '*') {
            star = pi;
            pi += 1;
            retry = vi;
        } else if (pi < pattern.len and pattern[pi] == path[vi]) {
            pi += 1;
            vi += 1;
        } else if (star) |position| {
            retry += 1;
            vi = retry;
            pi = position + 1;
        } else return false;
    }
    while (pi < pattern.len and pattern[pi] == '*') pi += 1;
    return pi == pattern.len;
}

fn validate(filters: std.json.ObjectMap, gates: std.json.ObjectMap) !void {
    if (filters.count() == 0 or gates.count() == 0 or filters.count() > 4096 or gates.count() > 4096) return error.InvalidRouting;
    var fit = filters.iterator();
    while (fit.next()) |entry| {
        if (!validIdentifier(entry.key_ptr.*)) return error.InvalidRouting;
        for (try strings(entry.value_ptr.*)) |pattern| {
            _ = try matches(pattern.string, "");
        }
    }
    var git = gates.iterator();
    while (git.next()) |entry| {
        if (!validIdentifier(entry.key_ptr.*)) return error.InvalidRouting;
        for (try strings(entry.value_ptr.*)) |group| {
            if (!filters.contains(group.string) or probe(group.string)) return error.InvalidRouting;
        }
    }
}

pub fn select(allocator: Allocator, document: Value, paths: []const []const u8, mode: []const u8) !Selection {
    if (!std.mem.eql(u8, mode, "pr") and !std.mem.eql(u8, mode, "full")) return error.UnsupportedMode;
    if (paths.len > 32768) return error.InputLimit;
    const root = try object(document);
    try rejectUnknownFields(document, &.{ "schema_version", "source", "routing", "modules", "checks" });
    try validateOptionalSections(root);
    const version = root.get("schema_version") orelse return error.UnsupportedSchemaVersion;
    if (version != .integer or version.integer != 1) return error.UnsupportedSchemaVersion;
    const routing = try object(root.get("routing") orelse return error.InvalidRouting);
    try rejectUnknownFields(root.get("routing").?, &.{ "filters", "job_gates" });
    const filters = try object(routing.get("filters") orelse return error.InvalidRouting);
    const gates = try object(routing.get("job_gates") orelse return error.InvalidRouting);
    try validate(filters, gates);
    var matched: std.StringHashMap(void) = .init(allocator);
    defer matched.deinit();
    var unmatched = false;
    for (paths) |path| {
        if (path.len == 0 or path.len > 4096 or path[0] == '/' or std.mem.indexOfScalar(u8, path, 0) != null) return error.InvalidPath;
        var parts = std.mem.splitScalar(u8, path, '/');
        while (parts.next()) |part| if (std.mem.eql(u8, part, "..")) return error.InvalidPath;
        var known_source = false;
        var fit = filters.iterator();
        while (fit.next()) |entry| {
            const name = entry.key_ptr.*;
            if (probe(name)) continue;
            for (entry.value_ptr.array.items) |pattern| {
                if (try matches(pattern.string, path)) {
                    try matched.put(name, {});
                    known_source = known_source or sourceGroup(filters, name);
                    break;
                }
            }
        }
        unmatched = unmatched or (std.mem.startsWith(u8, path, "src/") and !known_source);
    }
    const all = unmatched or std.mem.eql(u8, mode, "full");
    var groups: std.ArrayList([]const u8) = .empty;
    defer groups.deinit(allocator);
    var mit = matched.keyIterator();
    while (mit.next()) |name| try groups.append(allocator, name.*);
    var jobs: std.ArrayList([]const u8) = .empty;
    defer jobs.deinit(allocator);
    var shards: std.ArrayList([]const u8) = .empty;
    defer shards.deinit(allocator);
    var git = gates.iterator();
    while (git.next()) |entry| {
        const references = entry.value_ptr.array.items;
        var selected = references.len == 0;
        var code = false;
        for (references) |group| {
            selected = selected or all or matched.contains(group.string);
            code = code or sourceGroup(filters, group.string);
        }
        if (selected) {
            try jobs.append(allocator, entry.key_ptr.*);
            if (code) try shards.append(allocator, entry.key_ptr.*);
        }
    }
    std.mem.sort([]const u8, groups.items, {}, ordered);
    std.mem.sort([]const u8, jobs.items, {}, ordered);
    std.mem.sort([]const u8, shards.items, {}, ordered);
    const owned_groups = try groups.toOwnedSlice(allocator);
    errdefer allocator.free(owned_groups);
    const owned_jobs = try jobs.toOwnedSlice(allocator);
    errdefer allocator.free(owned_jobs);
    return .{ .matched_groups = owned_groups, .unmatched_src = unmatched, .selected_jobs = owned_jobs, .selected_code_shards = try shards.toOwnedSlice(allocator) };
}

fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len < 3) return error.InvalidArguments;
    const bytes = try std.Io.Dir.cwd().readFileAlloc(init.io, args[1], allocator, .limited(16 * 1024 * 1024));
    const parsed = try std.json.parseFromSlice(Value, allocator, bytes, .{ .duplicate_field_behavior = .@"error" });
    defer parsed.deinit();
    const selection = try select(allocator, parsed.value, args[3..], args[2]);
    defer selection.deinit(allocator);
    var output: std.Io.Writer.Allocating = .init(allocator);
    defer output.deinit();
    var stringify: std.json.Stringify = .{ .writer = &output.writer };
    try stringify.write(selection);
    try output.writer.writeByte('\n');
    try std.Io.File.stdout().writeStreamingAll(init.io, output.written());
}
pub fn main(init: std.process.Init) !void {
    run(init) catch |err| std.process.fatal("selection refused: {t}", .{err});
}

test "star glob semantics and explicit unsupported syntax" {
    try std.testing.expect(try matches("src/**", "src/a/b.zig"));
    try std.testing.expect(try matches("a*b*c", "axbyc"));
    try std.testing.expect(try matches("**/kernel/clock.py", "src/kernel/clock.py"));
    try std.testing.expect(!try matches("**/kernel/clock.py", "kernel/clock.py"));
    try std.testing.expect(!try matches("src/*.zig", "docs/a.md"));
    try std.testing.expect(try matches("*", ""));
    try std.testing.expectError(error.UnsupportedPattern, matches("src/?", "src/a"));
}
