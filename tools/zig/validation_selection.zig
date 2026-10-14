const std = @import("std");
const Allocator = std.mem.Allocator;
const Value = std.json.Value;

pub const SelectionReason = struct {
    check: []const u8,
    kind: []const u8,
    reference: []const u8 = "",
};

pub const Selection = struct {
    matched_groups: []const []const u8,
    unmatched_src: bool,
    selected_jobs: []const []const u8,
    selected_code_shards: []const []const u8,
    selected_reasons: []const SelectionReason,
    requested_platform: ?[]const u8 = null,
    target_checked: bool = false,
    selection_only: bool = true,
    validation_performed: bool = false,
    execution_supported: bool = false,

    pub fn deinit(self: Selection, allocator: Allocator) void {
        allocator.free(self.matched_groups);
        allocator.free(self.selected_jobs);
        allocator.free(self.selected_code_shards);
        allocator.free(self.selected_reasons);
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

fn requiredStrings(fields: std.json.ObjectMap, name: []const u8) ![]const Value {
    const value = fields.get(name) orelse return error.InvalidChecks;
    if (value != .array or value.array.items.len == 0) return error.InvalidChecks;
    for (value.array.items) |item| {
        if (item != .string or item.string.len == 0) return error.InvalidChecks;
    }
    return value.array.items;
}

fn validateModeAndPlatform(check: std.json.ObjectMap, name: []const u8, allowed: []const []const u8) !void {
    if (check.get(name)) |value| {
        const entries = try requiredStrings(check, name);
        for (entries) |entry| {
            var supported = false;
            for (allowed) |candidate| supported = supported or std.mem.eql(u8, entry.string, candidate);
            if (!supported) return error.UnsupportedCheckTarget;
        }
        if (value.array.items.len != entries.len) return error.InvalidChecks;
    }
}

fn validateCheck(value: Value) ![]const Value {
    try rejectUnknownFields(value, &.{ "argv", "modes", "platforms", "dependencies", "environment", "budgets", "recipe" });
    const fields = try object(value);
    const argv_value = fields.get("argv") orelse return error.InvalidCommand;
    if (argv_value != .array or argv_value.array.items.len == 0) return error.InvalidCommand;
    const argv = argv_value.array.items;
    for (argv) |command| {
        if (command != .array or command.array.items.len == 0) return error.InvalidCommand;
        for (command.array.items) |argument| {
            if (argument != .string or std.mem.indexOfScalar(u8, argument.string, 0) != null) return error.InvalidCommand;
        }
        if (command.array.items[0].string.len == 0) return error.InvalidCommand;
    }
    _ = try requiredStrings(fields, "modes");
    try validateModeAndPlatform(fields, "modes", &.{ "commit", "full", "release", "docs", "platform" });
    try validateModeAndPlatform(fields, "platforms", &.{ "macos", "linux", "windows", "all" });
    const dependency_value = fields.get("dependencies") orelse return error.InvalidChecks;
    if (dependency_value != .array) return error.InvalidChecks;
    for (dependency_value.array.items) |dependency| {
        if (dependency != .string or !validIdentifier(dependency.string)) return error.InvalidDependency;
    }
    const dependencies = dependency_value.array.items;
    const environment_value = fields.get("environment") orelse return error.InvalidChecks;
    const environment = try object(environment_value);
    var environment_iterator = environment.iterator();
    while (environment_iterator.next()) |entry| {
        if (!validEnvironmentName(entry.key_ptr.*) or entry.value_ptr.* != .string) return error.InvalidChecks;
        if (std.mem.indexOfScalar(u8, entry.value_ptr.string, 0) != null) return error.InvalidChecks;
    }
    const budgets_value = fields.get("budgets") orelse return error.InvalidBudget;
    try rejectUnknownFields(budgets_value, &.{ "wall_ms", "cleanup_ms", "stdout_bytes", "stderr_bytes", "sampled_processes", "sampled_resident_bytes" });
    const budgets = try object(budgets_value);
    const budget_names = [_][]const u8{ "wall_ms", "cleanup_ms", "stdout_bytes", "stderr_bytes", "sampled_processes", "sampled_resident_bytes" };
    for (budget_names) |name| {
        const budget = budgets.get(name) orelse return error.InvalidBudget;
        if (budget != .integer or budget.integer <= 0) return error.InvalidBudget;
    }
    return dependencies;
}

fn validEnvironmentName(name: []const u8) bool {
    if (name.len == 0) return false;
    for (name, 0..) |character, index| {
        const letter = (character >= 'A' and character <= 'Z') or (character >= 'a' and character <= 'z');
        if (index == 0) {
            if (!letter and character != '_') return false;
        } else if (!letter and character != '_' and !(character >= '0' and character <= '9')) {
            return false;
        }
    }
    return true;
}

fn validateCheckGraph(checks: std.json.ObjectMap) !void {
    var dependencies = std.StringHashMap([]const Value).init(std.heap.page_allocator);
    defer dependencies.deinit();
    var iterator = checks.iterator();
    while (iterator.next()) |entry| {
        if (!validIdentifier(entry.key_ptr.*)) return error.InvalidChecks;
        try dependencies.put(entry.key_ptr.*, try validateCheck(entry.value_ptr.*));
    }
    var completed = std.StringHashMap(void).init(std.heap.page_allocator);
    defer completed.deinit();
    while (completed.count() < checks.count()) {
        var advanced = false;
        var entries = dependencies.iterator();
        while (entries.next()) |entry| {
            if (completed.contains(entry.key_ptr.*)) continue;
            var ready = true;
            for (entry.value_ptr.*) |dependency| {
                const name = dependency.string;
                if (!checks.contains(name)) return error.InvalidDependency;
                ready = ready and completed.contains(name);
            }
            if (ready) {
                try completed.put(entry.key_ptr.*, {});
                advanced = true;
            }
        }
        if (!advanced) return error.DependencyCycle;
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
        if (checks.count() == 0) return error.InvalidChecks;
        try validateCheckGraph(checks);
    }
}

fn oneOf(value: []const u8, allowed: []const []const u8) bool {
    for (allowed) |candidate| if (std.mem.eql(u8, value, candidate)) return true;
    return false;
}

fn validateRecipe(value: Value, command_count: usize, migration: []const Value) !void {
    try rejectUnknownFields(value, &.{ "source", "python_version", "advisory", "required_inputs", "conditions", "instances", "applicability", "packages", "instance_environment", "observed_dependencies" });
    const recipe = try object(value);
    const source = recipe.get("source") orelse return error.InvalidRecipe;
    try validateSource(source);
    const source_fields = try object(source);
    var pinned = false;
    for (migration) |oracle| {
        const fields = try object(oracle);
        pinned = pinned or (std.mem.eql(u8, fields.get("path").?.string, source_fields.get("path").?.string) and
            std.mem.eql(u8, fields.get("sha256").?.string, source_fields.get("sha256").?.string));
    }
    if (!pinned) return error.UnboundRecipeSource;
    const python = recipe.get("python_version") orelse return error.InvalidRecipe;
    const advisory = recipe.get("advisory") orelse return error.InvalidRecipe;
    if (python != .string or !std.mem.eql(u8, python.string, "3.12") or advisory != .bool) return error.InvalidRecipe;
    const applicability = recipe.get("applicability") orelse return error.InvalidRecipe;
    if (applicability != .string or !oneOf(applicability.string, &.{ "routing", "routing-and-not-prose", "routing-or-prose" })) return error.UnsupportedCondition;
    const packages = try object(recipe.get("packages") orelse return error.InvalidRecipe);
    var package_iterator = packages.iterator();
    while (package_iterator.next()) |entry| {
        if (!validIdentifier(entry.key_ptr.*) or entry.value_ptr.* != .string or entry.value_ptr.string.len == 0) return error.InvalidRecipe;
    }
    for (try requiredStrings(recipe, "required_inputs")) |input| {
        if (!oneOf(input.string, &.{ "candidate", "base", "dependencies", "prose", "results", "commit_range", "memory_output", "universe_decision", "universe_reuse" })) return error.UnsupportedBinding;
    }
    const conditions = try requiredStrings(recipe, "conditions");
    const instances = try requiredStrings(recipe, "instances");
    if (conditions.len != command_count or instances.len != command_count) return error.InvalidRecipe;
    for (conditions) |condition| {
        if (!oneOf(condition.string, &.{ "success", "always", "advisory", "decision", "optional-cache", "universe", "universe-always" })) return error.UnsupportedCondition;
    }
    for (instances) |instance| if (!validIdentifier(instance.string)) return error.InvalidRecipe;
    const environments = try object(recipe.get("instance_environment") orelse return error.InvalidRecipe);
    var environment_iterator = environments.iterator();
    while (environment_iterator.next()) |entry| {
        var known = false;
        for (instances) |instance| known = known or std.mem.eql(u8, instance.string, entry.key_ptr.*);
        if (!known) return error.InvalidRecipe;
        var variables = (try object(entry.value_ptr.*)).iterator();
        while (variables.next()) |variable| {
            if (!validEnvironmentName(variable.key_ptr.*) or variable.value_ptr.* != .string or std.mem.indexOfScalar(u8, variable.value_ptr.string, 0) != null) return error.InvalidRecipe;
        }
    }
}

fn validateRecipes(root: std.json.ObjectMap, version: i64) !void {
    const migration_value = root.get("migration");
    if (version == 1) {
        if (migration_value != null) return error.UnsupportedSchemaVersion;
        if (root.get("checks")) |checks_value| {
            var legacy_checks = (try object(checks_value)).iterator();
            while (legacy_checks.next()) |entry| if ((try object(entry.value_ptr.*)).contains("recipe")) return error.UnsupportedSchemaVersion;
        }
        return;
    }
    const migration = migration_value orelse return error.InvalidRecipe;
    if (migration != .array or migration.array.items.len == 0 or migration.array.items.len > 256) return error.InvalidRecipe;
    var sources = std.StringHashMap(void).init(std.heap.page_allocator);
    defer sources.deinit();
    for (migration.array.items) |source| {
        try validateSource(source);
        const fields = try object(source);
        const path = fields.get("path").?.string;
        if (sources.contains(path)) return error.InvalidRecipe;
        try sources.put(path, {});
    }
    const checks = try object(root.get("checks") orelse return error.MissingCheck);
    var iterator = checks.iterator();
    while (iterator.next()) |entry| {
        const check = try object(entry.value_ptr.*);
        _ = try requiredStrings(check, "platforms");
        const recipe = check.get("recipe") orelse return error.InvalidRecipe;
        try validateRecipe(recipe, check.get("argv").?.array.items.len, migration.array.items);
        const observation = (try object(recipe)).get("observed_dependencies") orelse return error.InvalidRecipe;
        for (try strings(observation)) |dependency| {
            if (!checks.contains(dependency.string) and !std.mem.eql(u8, dependency.string, "changes")) return error.InvalidDependency;
            if (std.mem.eql(u8, dependency.string, entry.key_ptr.*)) return error.InvalidDependency;
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
    if (!oneOf(mode, &.{ "pr", "commit", "full" })) return error.UnsupportedMode;
    if (paths.len > 32768) return error.InputLimit;
    const root = try object(document);
    try rejectUnknownFields(document, &.{ "schema_version", "source", "routing", "modules", "checks", "migration" });
    try validateOptionalSections(root);
    const version = root.get("schema_version") orelse return error.UnsupportedSchemaVersion;
    if (version != .integer or (version.integer != 1 and version.integer != 2)) return error.UnsupportedSchemaVersion;
    try validateRecipes(root, version.integer);
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
    if (root.get("checks")) |checks_value| {
        const checks = try object(checks_value);
        var selected_checks = std.StringHashMap(void).init(allocator);
        defer selected_checks.deinit();
        for (jobs.items) |job| {
            if (!checks.contains(job)) return error.MissingCheck;
            try selected_checks.put(job, {});
        }
        while (true) {
            var pending: std.ArrayList([]const u8) = .empty;
            defer pending.deinit(allocator);
            var selected_iterator = selected_checks.keyIterator();
            while (selected_iterator.next()) |selected| {
                const check_value = checks.get(selected.*) orelse return error.MissingCheck;
                const check = try object(check_value);
                const dependencies = check.get("dependencies") orelse return error.InvalidChecks;
                for (dependencies.array.items) |dependency| {
                    const name = dependency.string;
                    if (!selected_checks.contains(name)) try pending.append(allocator, name);
                }
            }
            if (pending.items.len == 0) break;
            for (pending.items) |name| {
                if (!checks.contains(name)) return error.InvalidDependency;
                try selected_checks.put(name, {});
            }
        }
        jobs.clearRetainingCapacity();
        shards.clearRetainingCapacity();
        var selected_iterator = selected_checks.keyIterator();
        while (selected_iterator.next()) |selected| {
            try jobs.append(allocator, selected.*);
            if (gates.get(selected.*)) |route| {
                for (route.array.items) |group| {
                    if (sourceGroup(filters, group.string)) {
                        try shards.append(allocator, selected.*);
                        break;
                    }
                }
            }
        }
    }
    std.mem.sort([]const u8, groups.items, {}, ordered);
    std.mem.sort([]const u8, jobs.items, {}, ordered);
    std.mem.sort([]const u8, shards.items, {}, ordered);
    const reasons = try explainSelection(allocator, root, gates, jobs.items, groups.items, mode, unmatched);
    errdefer allocator.free(reasons);
    const owned_groups = try groups.toOwnedSlice(allocator);
    errdefer allocator.free(owned_groups);
    const owned_jobs = try jobs.toOwnedSlice(allocator);
    errdefer allocator.free(owned_jobs);
    return .{ .matched_groups = owned_groups, .unmatched_src = unmatched, .selected_jobs = owned_jobs, .selected_code_shards = try shards.toOwnedSlice(allocator), .selected_reasons = reasons };
}

fn reasonOrdered(_: void, a: SelectionReason, b: SelectionReason) bool {
    if (!std.mem.eql(u8, a.check, b.check)) return std.mem.lessThan(u8, a.check, b.check);
    if (!std.mem.eql(u8, a.kind, b.kind)) return std.mem.lessThan(u8, a.kind, b.kind);
    return std.mem.lessThan(u8, a.reference, b.reference);
}

fn explainSelection(allocator: Allocator, root: std.json.ObjectMap, gates: std.json.ObjectMap, jobs: []const []const u8, groups: []const []const u8, mode: []const u8, unmatched: bool) ![]const SelectionReason {
    var reasons: std.ArrayList(SelectionReason) = .empty;
    errdefer reasons.deinit(allocator);
    for (jobs) |job| {
        if (gates.get(job)) |route| {
            if (route.array.items.len == 0) {
                try reasons.append(allocator, .{ .check = job, .kind = "always_on" });
            } else if (std.mem.eql(u8, mode, "full")) {
                try reasons.append(allocator, .{ .check = job, .kind = "full" });
            } else if (unmatched) {
                try reasons.append(allocator, .{ .check = job, .kind = "unmatched_source" });
            } else {
                for (route.array.items) |group| {
                    if (oneOf(group.string, groups)) try reasons.append(allocator, .{ .check = job, .kind = "matched_group", .reference = group.string });
                }
            }
        }
        if (root.get("checks")) |checks_value| {
            for (jobs) |dependent| {
                const check = checks_value.object.get(dependent).?.object;
                for (check.get("dependencies").?.array.items) |dependency| {
                    if (std.mem.eql(u8, dependency.string, job)) try reasons.append(allocator, .{ .check = job, .kind = "dependency", .reference = dependent });
                }
            }
        }
    }
    std.mem.sort(SelectionReason, reasons.items, {}, reasonOrdered);
    return reasons.toOwnedSlice(allocator);
}

/// Check declarations for an explicit target; this never executes or qualifies it.
pub fn selectForTarget(allocator: Allocator, document: Value, paths: []const []const u8, mode: []const u8, platform: []const u8) !Selection {
    if (!oneOf(platform, &.{ "macos", "linux", "windows" })) return error.UnsupportedPlatform;
    var selection = try select(allocator, document, paths, mode);
    errdefer selection.deinit(allocator);
    const checks = (try object(document)).get("checks") orelse return error.MissingCheck;
    var requested_mode = mode;
    if (std.mem.eql(u8, mode, "pr")) requested_mode = "commit";
    for (selection.selected_jobs) |job| {
        const check = (try object(checks)).get(job).?.object;
        const modes = try requiredStrings(check, "modes");
        var mode_supported = false;
        for (modes) |entry| mode_supported = mode_supported or std.mem.eql(u8, entry.string, requested_mode);
        const platforms = try requiredStrings(check, "platforms");
        var platform_supported = false;
        for (platforms) |entry| platform_supported = platform_supported or oneOf(entry.string, &.{ "all", platform });
        if (!mode_supported or !platform_supported) return error.UnavailableRequiredCheck;
    }
    selection.requested_platform = platform;
    selection.target_checked = true;
    return selection;
}

fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len < 3) return error.InvalidArguments;
    const targeted = std.mem.eql(u8, args[2], "--platform");
    if (targeted and args.len < 5) return error.InvalidArguments;
    var mode = args[2];
    var paths = args[3..];
    if (targeted) {
        mode = args[4];
        paths = args[5..];
    }
    const bytes = try std.Io.Dir.cwd().readFileAlloc(init.io, args[1], allocator, .limited(16 * 1024 * 1024));
    const parsed = try std.json.parseFromSlice(Value, allocator, bytes, .{ .duplicate_field_behavior = .@"error" });
    defer parsed.deinit();
    var selection: Selection = undefined;
    if (targeted) {
        selection = try selectForTarget(allocator, parsed.value, paths, mode, args[3]);
    } else {
        selection = try select(allocator, parsed.value, paths, mode);
    }
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
