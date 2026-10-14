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
    unbound_workflow_jobs: []const []const u8,
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
        for (self.unbound_workflow_jobs) |name| allocator.free(name);
        allocator.free(self.unbound_workflow_jobs);
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
fn sourceGroup(filters: std.json.ObjectMap, name: []const u8, non_source: []const Value) bool {
    if (probe(name)) return false;
    for (non_source) |group| if (std.mem.eql(u8, name, group.string)) return false;
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
    try rejectUnknownFields(value, &.{ "argv", "modes", "platforms", "dependencies", "environment", "budgets", "recipe", "unmatched_source", "stderr_policy" });
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
    if (fields.get("unmatched_source")) |policy| if (policy != .bool) return error.InvalidChecks;
    if (fields.get("stderr_policy")) |policy| {
        const entries = try strings(policy);
        if (entries.len != argv.len) return error.InvalidChecks;
        for (entries) |entry| if (!oneOf(entry.string, &.{ "allow", "reject-warning-prefix" })) return error.UnsupportedOutputPolicy;
    }
    _ = try requiredStrings(fields, "modes");
    try validateModeAndPlatform(fields, "modes", &.{ "commit", "full", "release", "package", "docs", "platform" });
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
    try rejectUnknownFields(value, &.{ "source", "python_version", "advisory", "required_inputs", "conditions", "instances", "applicability", "packages", "instance_environment", "observed_dependencies", "workflow_job" });
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
    if (python != .string or advisory != .bool) return error.InvalidRecipe;
    if (!std.mem.eql(u8, python.string, "3.12") and !(recipe.contains("workflow_job") and std.mem.eql(u8, python.string, "unbound"))) return error.InvalidRecipe;
    if (recipe.get("workflow_job")) |job| if (job != .string or !validIdentifier(job.string)) return error.InvalidRecipe;
    const applicability = recipe.get("applicability") orelse return error.InvalidRecipe;
    if (applicability != .string or !oneOf(applicability.string, &.{ "routing", "routing-and-not-prose", "routing-or-prose", "workflow" })) return error.UnsupportedCondition;
    if (std.mem.eql(u8, applicability.string, "workflow") != recipe.contains("workflow_job")) return error.InvalidRecipe;
    const packages = try object(recipe.get("packages") orelse return error.InvalidRecipe);
    var package_iterator = packages.iterator();
    while (package_iterator.next()) |entry| {
        if (!validIdentifier(entry.key_ptr.*) or entry.value_ptr.* != .string or entry.value_ptr.string.len == 0) return error.InvalidRecipe;
    }
    for (try requiredStrings(recipe, "required_inputs")) |input| {
        if (!oneOf(input.string, &.{ "candidate", "base", "dependencies", "prose", "results", "commit_range", "memory_output", "universe_decision", "universe_reuse", "claude_cli_2_1_270", "workflow_context" })) return error.UnsupportedBinding;
    }
    if (recipe.contains("workflow_job")) {
        var context_required = false;
        for (try requiredStrings(recipe, "required_inputs")) |input| context_required = context_required or std.mem.eql(u8, input.string, "workflow_context");
        if (!context_required) return error.InvalidRecipe;
    }
    const conditions = try requiredStrings(recipe, "conditions");
    const instances = try requiredStrings(recipe, "instances");
    if (conditions.len != command_count or instances.len != command_count) return error.InvalidRecipe;
    for (conditions) |condition| {
        if (!oneOf(condition.string, &.{ "success", "always", "advisory", "decision", "optional-cache", "universe", "universe-always", "source-context" })) return error.UnsupportedCondition;
        if (std.mem.eql(u8, condition.string, "source-context") != recipe.contains("workflow_job")) return error.InvalidRecipe;
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
        if (version >= 3 and (!check.contains("unmatched_source") or !check.contains("stderr_policy"))) return error.InvalidChecks;
        _ = try requiredStrings(check, "platforms");
        const recipe = check.get("recipe") orelse return error.InvalidRecipe;
        if (version < 5 and recipe.object.contains("workflow_job")) return error.UnsupportedSchemaVersion;
        try validateRecipe(recipe, check.get("argv").?.array.items.len, migration.array.items);
        const observation = (try object(recipe)).get("observed_dependencies") orelse return error.InvalidRecipe;
        for (try strings(observation)) |dependency| {
            if (!checks.contains(dependency.string) and !std.mem.eql(u8, dependency.string, "changes")) return error.InvalidDependency;
            if (std.mem.eql(u8, dependency.string, entry.key_ptr.*)) return error.InvalidDependency;
        }
    }
}

fn workflowDependencyReady(name: []const u8, jobs: std.json.ObjectMap, completed: std.StringHashMap(void)) !bool {
    if (!validIdentifier(name) or !jobs.contains(name)) return error.InvalidDependency;
    return completed.contains(name);
}

fn workflowJobReady(job: std.json.ObjectMap, jobs: std.json.ObjectMap, completed: std.StringHashMap(void)) !bool {
    const needs = job.get("needs") orelse return true;
    if (needs == .string) return workflowDependencyReady(needs.string, jobs, completed);
    var ready = true;
    for (try strings(needs)) |dependency| ready = try workflowDependencyReady(dependency.string, jobs, completed) and ready;
    return ready;
}

fn validateWorkflowProgram(value: Value, job: std.json.ObjectMap) !void {
    const program = try object(value);
    const status = program.get("status") orelse return error.InvalidWorkflowProgram;
    if (status != .string) return error.InvalidWorkflowProgram;
    const context = program.get("context_required") orelse return error.InvalidWorkflowProgram;
    if (context != .bool or !context.bool) return error.UnboundWorkflowContext;
    var steps: []const Value = &.{};
    if (job.get("steps")) |value_steps| steps = value_steps.array.items;
    if (std.mem.eql(u8, status.string, "unsupported")) {
        try rejectUnknownFields(value, &.{ "status", "steps", "reason", "context_required" });
        const reason = program.get("reason") orelse return error.InvalidWorkflowProgram;
        if (reason != .string or !oneOf(reason.string, &.{ "unsupported-shell-or-command-control", "no-external-argv" })) return error.InvalidWorkflowProgram;
        const refused = program.get("steps") orelse return error.InvalidWorkflowProgram;
        if (refused != .array) return error.InvalidWorkflowProgram;
        var previous: ?i64 = null;
        for (refused.array.items) |step| {
            if (step != .integer or step.integer < 0 or step.integer >= steps.len or (previous != null and step.integer <= previous.?)) return error.InvalidWorkflowProgram;
            previous = step.integer;
        }
        return;
    }
    if (!std.mem.eql(u8, status.string, "normalized")) return error.InvalidWorkflowProgram;
    try rejectUnknownFields(value, &.{ "status", "argv", "controls", "argument_bindings", "context_required" });
    const argv_value = program.get("argv") orelse return error.InvalidWorkflowProgram;
    if (argv_value != .array or argv_value.array.items.len == 0 or argv_value.array.items.len > 4096) return error.InvalidWorkflowProgram;
    const argv = argv_value.array.items;
    var words: usize = 0;
    for (argv) |command| {
        const args = try strings(command);
        if (args.len == 0 or args.len > 4096 or args[0].string.len == 0) return error.InvalidWorkflowProgram;
        words += args.len;
        for (args) |arg| if (arg.string.len > 16384 or std.mem.indexOfScalar(u8, arg.string, 0) != null) return error.InvalidWorkflowProgram;
    }
    if (words > 32768) return error.InputLimit;
    const control_value = program.get("controls") orelse return error.InvalidWorkflowProgram;
    if (control_value != .array or control_value.array.items.len > steps.len) return error.InvalidWorkflowProgram;
    var next: i64 = 0;
    var source_step: i64 = -1;
    for (control_value.array.items) |control| {
        try rejectUnknownFields(control, &.{ "step", "start", "count", "failure" });
        const fields = try object(control);
        const step = fields.get("step") orelse return error.InvalidWorkflowProgram;
        const start = fields.get("start") orelse return error.InvalidWorkflowProgram;
        const count = fields.get("count") orelse return error.InvalidWorkflowProgram;
        const failure = fields.get("failure") orelse return error.InvalidWorkflowProgram;
        if (step != .integer or start != .integer or count != .integer or failure != .string) return error.InvalidWorkflowProgram;
        if (step.integer <= source_step or step.integer >= steps.len or start.integer != next or count.integer <= 0 or count.integer > @as(i64, @intCast(argv.len)) - next) return error.InvalidWorkflowProgram;
        if (!steps[@intCast(step.integer)].object.contains("run") or !oneOf(failure.string, &.{ "fail-fast", "collect-failures" })) return error.InvalidWorkflowProgram;
        next += count.integer;
        source_step = step.integer;
    }
    if (next != argv.len) return error.InvalidWorkflowProgram;
    var run_count: usize = 0;
    for (steps) |step| run_count += @intFromBool(step.object.contains("run"));
    if (run_count != control_value.array.items.len) return error.InvalidWorkflowProgram;
    const argument_value = program.get("argument_bindings") orelse return error.InvalidWorkflowProgram;
    if (argument_value != .array or argument_value.array.items.len > words) return error.InvalidWorkflowProgram;
    var coordinates = std.AutoHashMap(u64, void).init(std.heap.page_allocator);
    defer coordinates.deinit();
    for (argument_value.array.items) |argument| {
        try rejectUnknownFields(argument, &.{ "command", "argument", "variable", "prefix", "suffix" });
        const fields = try object(argument);
        const command = fields.get("command") orelse return error.InvalidWorkflowProgram;
        const index = fields.get("argument") orelse return error.InvalidWorkflowProgram;
        const variable = fields.get("variable") orelse return error.InvalidWorkflowProgram;
        const prefix = fields.get("prefix") orelse return error.InvalidWorkflowProgram;
        const suffix = fields.get("suffix") orelse return error.InvalidWorkflowProgram;
        if (command != .integer or index != .integer or variable != .string or prefix != .string or suffix != .string) return error.InvalidWorkflowProgram;
        if (command.integer < 0 or command.integer >= argv.len or index.integer <= 0 or index.integer >= argv[@intCast(command.integer)].array.items.len) return error.InvalidWorkflowProgram;
        if (!validEnvironmentName(variable.string) or prefix.string.len > 4096 or suffix.string.len > 4096 or std.mem.indexOfScalar(u8, prefix.string, 0) != null or std.mem.indexOfScalar(u8, suffix.string, 0) != null) return error.InvalidWorkflowProgram;
        const word = argv[@intCast(command.integer)].array.items[@intCast(index.integer)].string;
        if (!std.mem.startsWith(u8, word, "@environment.") or word.len <= 13) return error.InvalidWorkflowProgram;
        _ = std.fmt.parseInt(u32, word[13..], 10) catch return error.InvalidWorkflowProgram;
        const coordinate = (@as(u64, @intCast(command.integer)) << 32) | @as(u64, @intCast(index.integer));
        if (coordinates.contains(coordinate)) return error.InvalidWorkflowProgram;
        try coordinates.put(coordinate, {});
    }
    for (argv, 0..) |command, i| for (command.array.items, 0..) |arg, j| {
        if (std.mem.startsWith(u8, arg.string, "@environment.")) {
            const coordinate = (@as(u64, @intCast(i)) << 32) | @as(u64, @intCast(j));
            if (!coordinates.contains(coordinate)) return error.InvalidWorkflowProgram;
        }
    };
}

const ProgramReference = struct { program: Value, definition: std.json.ObjectMap, job: std.json.ObjectMap };

fn programReference(root: std.json.ObjectMap, subject: []const u8) !ProgramReference {
    if (subject.len == 0 or subject.len > 512 or !validIdentifier(subject)) return error.InvalidWorkflowProgram;
    if (root.get("schema_version").?.integer < 6) return error.MissingWorkflowProgram;
    for (root.get("workflow_contracts").?.array.items) |contract_value| {
        const contract = contract_value.object;
        const id = contract.get("id").?.string;
        if (subject.len <= id.len or !std.mem.startsWith(u8, subject, id) or subject[id.len] != '.') continue;
        const name = subject[id.len + 1 ..];
        const mapping = contract.get("jobs").?.object.get(name) orelse continue;
        const program = mapping.object.get("program").?;
        if (!std.mem.eql(u8, program.object.get("status").?.string, "normalized")) return error.UnsupportedWorkflowProgram;
        const definition = contract.get("definition").?.object;
        return .{ .program = program, .definition = definition, .job = definition.get("jobs").?.object.get(name).?.object };
    }
    return error.MissingWorkflowProgram;
}

fn sourceEnvironment(reference: ProgramReference, command: usize, name: []const u8) !?[]const u8 {
    var step_index: usize = undefined;
    for (reference.program.object.get("controls").?.array.items) |control| {
        const fields = control.object;
        const start: usize = @intCast(fields.get("start").?.integer);
        const count: usize = @intCast(fields.get("count").?.integer);
        if (command >= start and command < start + count) {
            step_index = @intCast(fields.get("step").?.integer);
            break;
        }
    } else return error.InvalidWorkflowProgram;
    const step = reference.job.get("steps").?.array.items[step_index].object;
    var value: ?Value = null;
    for ([_]std.json.ObjectMap{ reference.definition, reference.job, step }) |level| {
        if (level.get("env")) |env| if ((try object(env)).get(name)) |candidate| {
            value = candidate;
        };
    }
    if (value) |literal| {
        if (literal != .string or literal.string.len > 4096 or std.mem.indexOfAny(u8, literal.string, "$`\x00\r\n") != null) return error.UnboundEnvironmentExpression;
        return literal.string;
    }
    if (!std.mem.eql(u8, name, "RUNNER_TEMP")) return error.UnboundEnvironmentVariable;
    return null;
}

pub const BoundProgram = struct {
    argv: []const []const []const u8,
    pub fn deinit(self: BoundProgram, allocator: Allocator) void {
        for (self.argv) |command| {
            for (command) |argument| allocator.free(argument);
            allocator.free(command);
        }
        allocator.free(self.argv);
    }
};

fn boundCommand(allocator: Allocator, reference: ProgramReference, command: usize, environment: *const std.process.Environ.Map) ![]const []const u8 {
    const original = reference.program.object.get("argv").?.array.items[command].array.items;
    const args = try allocator.alloc([]const u8, original.len);
    var acquired: usize = 0;
    errdefer {
        for (args[0..acquired]) |arg| allocator.free(arg);
        allocator.free(args);
    }
    for (original, 0..) |argument, index| {
        var bound: ?std.json.ObjectMap = null;
        for (reference.program.object.get("argument_bindings").?.array.items) |binding| {
            const fields = binding.object;
            if (fields.get("command").?.integer == command and fields.get("argument").?.integer == index) {
                bound = fields;
                break;
            }
        }
        if (bound) |fields| {
            const name = fields.get("variable").?.string;
            const literal = try sourceEnvironment(reference, command, name);
            const actual = environment.get(name) orelse return error.MissingEnvironmentBinding;
            if (actual.len > 4096 or std.mem.indexOfScalar(u8, actual, 0) != null) return error.InputLimit;
            if (literal) |expected| if (!std.mem.eql(u8, expected, actual)) return error.EnvironmentBindingMismatch;
            args[index] = try std.fmt.allocPrint(allocator, "{s}{s}{s}", .{ fields.get("prefix").?.string, actual, fields.get("suffix").?.string });
        } else args[index] = try allocator.dupe(u8, argument.string);
        acquired += 1;
    }
    return args;
}

/// Render actual process argument data only. This cannot qualify or execute a workflow.
pub fn bindWorkflowProgram(allocator: Allocator, document: Value, subject: []const u8, environment: *const std.process.Environ.Map) !BoundProgram {
    const inspected = try select(allocator, document, &.{}, "full");
    defer inspected.deinit(allocator);
    const reference = try programReference(try object(document), subject);
    const argv = reference.program.object.get("argv").?.array.items;
    const commands = try allocator.alloc([]const []const u8, argv.len);
    var acquired: usize = 0;
    errdefer {
        for (commands[0..acquired]) |command| {
            for (command) |argument| allocator.free(argument);
            allocator.free(command);
        }
        allocator.free(commands);
    }
    var bytes: usize = 0;
    for (argv, 0..) |_, index| {
        commands[index] = try boundCommand(allocator, reference, index, environment);
        acquired += 1;
        for (commands[index]) |argument| bytes += argument.len;
        if (bytes > 8 * 1024 * 1024) return error.InputLimit;
    }
    return .{ .argv = commands };
}

fn validateProgramCheck(program_value: Value, check_value: Value) !void {
    const program = program_value.object;
    if (!std.mem.eql(u8, program.get("status").?.string, "normalized")) return error.UnsupportedWorkflowProgram;
    const expected = program.get("argv").?.array.items;
    const actual = check_value.object.get("argv").?.array.items;
    if (expected.len != actual.len) return error.UnboundRecipeSource;
    for (expected, actual) |left, right| {
        const a = left.array.items;
        const b = right.array.items;
        if (a.len != b.len) return error.UnboundRecipeSource;
        for (a, b) |x, y| if (!std.mem.eql(u8, x.string, y.string)) return error.UnboundRecipeSource;
    }
}

fn validateWorkflowContracts(root: std.json.ObjectMap, version: i64) !void {
    const value = root.get("workflow_contracts");
    if (version < 5) {
        if (value != null) return error.UnsupportedSchemaVersion;
        return;
    }
    const contracts = value orelse return error.MissingWorkflowContracts;
    if (contracts != .array or contracts.array.items.len == 0 or contracts.array.items.len > 256) return error.InvalidWorkflowContracts;
    const migration = root.get("migration").?.array.items;
    if (contracts.array.items.len != migration.len) return error.InvalidWorkflowContracts;
    const checks = root.get("checks").?.object;
    var paths = std.StringHashMap(void).init(std.heap.page_allocator);
    defer paths.deinit();
    var mapped_checks = std.StringHashMap(void).init(std.heap.page_allocator);
    defer mapped_checks.deinit();
    for (contracts.array.items) |contract_value| {
        try rejectUnknownFields(contract_value, &.{ "id", "source", "definition", "jobs" });
        const contract = try object(contract_value);
        const id = contract.get("id") orelse return error.InvalidWorkflowContracts;
        if (id != .string or !validIdentifier(id.string)) return error.InvalidWorkflowContracts;
        const source_value = contract.get("source") orelse return error.InvalidWorkflowContracts;
        try validateSource(source_value);
        const source = source_value.object;
        const path = source.get("path").?.string;
        if (!std.mem.startsWith(u8, path, ".github/workflows/") or !std.mem.endsWith(u8, path, ".yml") or !std.mem.eql(u8, path[18 .. path.len - 4], id.string)) return error.InvalidWorkflowContracts;
        if (paths.contains(path)) return error.InvalidWorkflowContracts;
        try paths.put(path, {});
        var pinned = false;
        for (migration) |row| pinned = pinned or (std.mem.eql(u8, row.object.get("path").?.string, path) and std.mem.eql(u8, row.object.get("sha256").?.string, source.get("sha256").?.string));
        if (!pinned) return error.UnboundRecipeSource;
        const definition_value = contract.get("definition") orelse return error.InvalidWorkflowContracts;
        try rejectUnknownFields(definition_value, &.{ "name", "on", "run-name", "jobs", "env", "permissions", "concurrency" });
        const definition = try object(definition_value);
        _ = try object(definition.get("on") orelse return error.InvalidWorkflowContracts);
        const jobs = try object(definition.get("jobs") orelse return error.InvalidWorkflowContracts);
        const mappings = try object(contract.get("jobs") orelse return error.InvalidWorkflowContracts);
        if (jobs.count() == 0 or jobs.count() > 256 or jobs.count() != mappings.count()) return error.InvalidWorkflowContracts;
        var iterator = jobs.iterator();
        while (iterator.next()) |entry| {
            if (!validIdentifier(entry.key_ptr.*)) return error.InvalidWorkflowContracts;
            try rejectUnknownFields(entry.value_ptr.*, &.{ "name", "needs", "if", "runs-on", "steps", "uses", "with", "env", "permissions", "outputs", "strategy", "timeout-minutes", "continue-on-error", "concurrency", "environment" });
            const job = try object(entry.value_ptr.*);
            if (job.get("steps")) |steps| {
                if (steps != .array or steps.array.items.len > 1024) return error.InvalidWorkflowContracts;
                for (steps.array.items) |step| {
                    try rejectUnknownFields(step, &.{ "name", "id", "run", "uses", "with", "if", "shell", "env", "timeout-minutes", "continue-on-error" });
                    const fields = try object(step);
                    const run_value = fields.get("run");
                    const uses_value = fields.get("uses");
                    if ((run_value == null) == (uses_value == null)) return error.InvalidWorkflowContracts;
                    if (run_value) |run_body| if (run_body != .string or run_body.string.len == 0) return error.InvalidWorkflowContracts;
                    if (uses_value) |action| if (action != .string or action.string.len == 0) return error.InvalidWorkflowContracts;
                }
            } else if (!job.contains("uses")) return error.InvalidWorkflowContracts;
            const mapping_value = mappings.get(entry.key_ptr.*) orelse return error.InvalidWorkflowContracts;
            try rejectUnknownFields(mapping_value, &.{ "check_id", "wall_ms", "budget_scope", "budget_origin", "binding_required", "program" });
            const mapping = mapping_value.object;
            if (version >= 6) {
                try validateWorkflowProgram(mapping.get("program") orelse return error.MissingWorkflowProgram, job);
            } else if (mapping.contains("program")) return error.UnsupportedSchemaVersion;
            const binding = mapping.get("binding_required") orelse return error.InvalidWorkflowContracts;
            if (binding != .bool or !binding.bool) return error.UnboundWorkflowContext;
            const budget_scope = mapping.get("budget_scope") orelse return error.InvalidWorkflowContracts;
            const budget_origin = mapping.get("budget_origin") orelse return error.InvalidWorkflowContracts;
            const wall = mapping.get("wall_ms") orelse return error.InvalidWorkflowContracts;
            if (budget_scope != .string or !std.mem.eql(u8, budget_scope.string, "per-job-instance") or budget_origin != .string or wall != .integer) return error.InvalidBudget;
            var minutes: i64 = 360;
            if (job.get("timeout-minutes")) |timeout| {
                if (timeout != .integer or timeout.integer < 1 or timeout.integer > 360 or !std.mem.eql(u8, budget_origin.string, "source")) return error.InvalidBudget;
                minutes = timeout.integer;
            } else if (!std.mem.eql(u8, budget_origin.string, "github-default-360-minutes")) return error.InvalidBudget;
            if (wall.integer != minutes * 60000) return error.InvalidBudget;
            const check_id = mapping.get("check_id") orelse return error.InvalidWorkflowContracts;
            if (check_id != .null) {
                if (check_id != .string or !checks.contains(check_id.string)) return error.MissingCheck;
                if (mapped_checks.contains(check_id.string)) return error.InvalidWorkflowContracts;
                try mapped_checks.put(check_id.string, {});
                const recipe = checks.get(check_id.string).?.object.get("recipe").?.object;
                if (!std.mem.eql(u8, recipe.get("source").?.object.get("path").?.string, path)) return error.UnboundRecipeSource;
                if (recipe.get("workflow_job")) |name| {
                    if (!std.mem.eql(u8, name.string, entry.key_ptr.*)) return error.InvalidWorkflowContracts;
                    if (version >= 6) try validateProgramCheck(mapping.get("program").?, checks.get(check_id.string).?);
                }
            }
        }
        var completed = std.StringHashMap(void).init(std.heap.page_allocator);
        defer completed.deinit();
        while (completed.count() < jobs.count()) {
            var advanced = false;
            iterator = jobs.iterator();
            while (iterator.next()) |entry| {
                if (completed.contains(entry.key_ptr.*)) continue;
                if (try workflowJobReady(entry.value_ptr.object, jobs, completed)) {
                    try completed.put(entry.key_ptr.*, {});
                    advanced = true;
                }
            }
            if (!advanced) return error.DependencyCycle;
        }
    }
    if (mapped_checks.count() != checks.count()) return error.UnboundRecipeSource;
}

fn unboundWorkflowJobs(allocator: Allocator, root: std.json.ObjectMap) ![]const []const u8 {
    var names: std.ArrayList([]const u8) = .empty;
    errdefer {
        for (names.items) |name| allocator.free(name);
        names.deinit(allocator);
    }
    if (root.get("workflow_contracts")) |contracts| {
        for (contracts.array.items) |contract_value| {
            const contract = contract_value.object;
            var jobs = contract.get("jobs").?.object.iterator();
            while (jobs.next()) |job| {
                const name = try std.fmt.allocPrint(allocator, "{s}.{s}", .{ contract.get("id").?.string, job.key_ptr.* });
                errdefer allocator.free(name);
                try names.append(allocator, name);
            }
        }
    }
    std.mem.sort([]const u8, names.items, {}, ordered);
    return names.toOwnedSlice(allocator);
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

fn validate(filters: std.json.ObjectMap, gates: std.json.ObjectMap, non_source: []const Value, root: std.json.ObjectMap) !void {
    if (filters.count() == 0 or gates.count() == 0 or filters.count() > 4096 or gates.count() > 4096) return error.InvalidRouting;
    var fit = filters.iterator();
    while (fit.next()) |entry| {
        if (!validIdentifier(entry.key_ptr.*)) return error.InvalidRouting;
        for (try strings(entry.value_ptr.*)) |pattern| {
            _ = try matches(pattern.string, "");
        }
    }
    for (non_source, 0..) |group, index| {
        if (!filters.contains(group.string) or probe(group.string)) return error.InvalidRouting;
        for (non_source[0..index]) |previous| if (std.mem.eql(u8, group.string, previous.string)) return error.InvalidRouting;
    }
    var git = gates.iterator();
    while (git.next()) |entry| {
        if (!validIdentifier(entry.key_ptr.*)) return error.InvalidRouting;
        for (try strings(entry.value_ptr.*)) |group| {
            if (!filters.contains(group.string) or probe(group.string)) return error.InvalidRouting;
        }
        if (!conservativeCheck(root, entry.key_ptr.*)) {
            if (entry.value_ptr.array.items.len == 0) return error.InvalidRouting;
            for (entry.value_ptr.array.items) |group| {
                var data = false;
                for (non_source) |candidate| data = data or std.mem.eql(u8, candidate.string, group.string);
                if (!data) return error.InvalidRouting;
            }
        }
    }
}

fn conservativeCheck(root: std.json.ObjectMap, name: []const u8) bool {
    if (root.get("checks")) |checks| {
        if (checks.object.get(name)) |check| {
            if (check.object.get("unmatched_source")) |policy| return policy.bool;
        }
    }
    return true;
}

// An unresolved source-context declaration cannot establish covered work.
fn previewRoute(root: std.json.ObjectMap, gates: std.json.ObjectMap, group: []const u8) bool {
    if (root.get("schema_version").?.integer < 5) return true;
    var iterator = gates.iterator();
    while (iterator.next()) |entry| {
        const check = root.get("checks").?.object.get(entry.key_ptr.*).?.object;
        if (check.get("recipe")) |recipe| if (recipe.object.contains("workflow_job")) continue;
        for (entry.value_ptr.array.items) |candidate| if (std.mem.eql(u8, candidate.string, group)) return true;
    }
    return false;
}

pub fn select(allocator: Allocator, document: Value, paths: []const []const u8, mode: []const u8) !Selection {
    const qualification = qualificationMode(mode);
    if (!qualification and !oneOf(mode, &.{ "pr", "commit", "full" })) return error.UnsupportedMode;
    if (paths.len > 32768) return error.InputLimit;
    if (qualification and paths.len != 0) return error.UnexpectedChangedPaths;
    const root = try object(document);
    try rejectUnknownFields(document, &.{ "schema_version", "source", "routing", "modules", "checks", "migration", "workflow_contracts" });
    try validateOptionalSections(root);
    const version = root.get("schema_version") orelse return error.UnsupportedSchemaVersion;
    if (version != .integer or (version.integer < 1 or version.integer > 6)) return error.UnsupportedSchemaVersion;
    try validateRecipes(root, version.integer);
    try validateWorkflowContracts(root, version.integer);
    const routing = try object(root.get("routing") orelse return error.InvalidRouting);
    try rejectUnknownFields(root.get("routing").?, &.{ "filters", "job_gates", "non_source_groups", "unknown_surface_policy" });
    var refuse_unknown = false;
    if (routing.get("unknown_surface_policy")) |policy| {
        if (policy != .string or !std.mem.eql(u8, policy.string, "refuse-path-sensitive")) return error.InvalidRouting;
        refuse_unknown = true;
    }
    if (version.integer >= 4 and !refuse_unknown) return error.InvalidRouting;
    var non_source: []const Value = &.{};
    if (routing.get("non_source_groups")) |data| non_source = try strings(data);
    if (version.integer >= 3 and !routing.contains("non_source_groups")) return error.InvalidRouting;
    const filters = try object(routing.get("filters") orelse return error.InvalidRouting);
    const gates = try object(routing.get("job_gates") orelse return error.InvalidRouting);
    try validate(filters, gates, non_source, root);
    var matched: std.StringHashMap(void) = .init(allocator);
    defer matched.deinit();
    var unmatched = false;
    for (paths) |path| {
        if (path.len == 0 or path.len > 4096 or path[0] == '/' or std.mem.indexOfScalar(u8, path, 0) != null) return error.InvalidPath;
        var parts = std.mem.splitScalar(u8, path, '/');
        while (parts.next()) |part| if (std.mem.eql(u8, part, "..")) return error.InvalidPath;
        var known_source = false;
        var known_route = false;
        var fit = filters.iterator();
        while (fit.next()) |entry| {
            const name = entry.key_ptr.*;
            if (probe(name)) continue;
            for (entry.value_ptr.array.items) |pattern| {
                if (try matches(pattern.string, path)) {
                    try matched.put(name, {});
                    known_route = known_route or previewRoute(root, gates, name);
                    known_source = known_source or sourceGroup(filters, name, non_source);
                    break;
                }
            }
        }
        if (refuse_unknown and !known_route and !std.mem.startsWith(u8, path, "src/") and !std.mem.eql(u8, mode, "full")) return error.UnsupportedChangedSurface;
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
        if (qualification) continue;
        if (root.get("checks")) |checks| {
            const check_value = checks.object.get(entry.key_ptr.*) orelse return error.MissingCheck;
            const check = check_value.object;
            if (check.get("recipe")) |recipe| {
                if (recipe.object.contains("workflow_job") and !try modeApplies(check, requestedMode(mode))) continue;
            }
        }
        const references = entry.value_ptr.array.items;
        var selected = references.len == 0;
        var code = false;
        for (references) |group| {
            selected = selected or (all and (std.mem.eql(u8, mode, "full") or conservativeCheck(root, entry.key_ptr.*))) or matched.contains(group.string);
            code = code or sourceGroup(filters, group.string, non_source);
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
        if (qualification) {
            var check_iterator = checks.iterator();
            while (check_iterator.next()) |entry| {
                if (try modeApplies(entry.value_ptr.object, mode)) try selected_checks.put(entry.key_ptr.*, {});
            }
            if (selected_checks.count() == 0) return error.NoApplicableChecks;
        }
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
                if (qualification and !try modeApplies(check, mode)) return error.UnavailableRequiredCheck;
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
                    if (sourceGroup(filters, group.string, non_source)) {
                        try shards.append(allocator, selected.*);
                        break;
                    }
                }
            }
        }
    } else if (qualification) {
        return error.MissingCheck;
    }
    std.mem.sort([]const u8, groups.items, {}, ordered);
    std.mem.sort([]const u8, jobs.items, {}, ordered);
    std.mem.sort([]const u8, shards.items, {}, ordered);
    const reasons = try explainSelection(allocator, root, gates, jobs.items, groups.items, mode, unmatched);
    errdefer allocator.free(reasons);
    const unbound = try unboundWorkflowJobs(allocator, root);
    errdefer {
        for (unbound) |name| allocator.free(name);
        allocator.free(unbound);
    }
    if (qualification and unbound.len != 0) return error.UnboundWorkflowContext;
    const owned_groups = try groups.toOwnedSlice(allocator);
    errdefer allocator.free(owned_groups);
    const owned_jobs = try jobs.toOwnedSlice(allocator);
    errdefer allocator.free(owned_jobs);
    return .{ .matched_groups = owned_groups, .unmatched_src = unmatched, .selected_jobs = owned_jobs, .selected_code_shards = try shards.toOwnedSlice(allocator), .selected_reasons = reasons, .unbound_workflow_jobs = unbound };
}

fn reasonOrdered(_: void, a: SelectionReason, b: SelectionReason) bool {
    if (!std.mem.eql(u8, a.check, b.check)) return std.mem.lessThan(u8, a.check, b.check);
    if (!std.mem.eql(u8, a.kind, b.kind)) return std.mem.lessThan(u8, a.kind, b.kind);
    return std.mem.lessThan(u8, a.reference, b.reference);
}

fn qualificationMode(mode: []const u8) bool {
    return oneOf(mode, &.{ "platform", "release", "package", "docs" });
}

fn requestedMode(mode: []const u8) []const u8 {
    if (std.mem.eql(u8, mode, "pr")) return "commit";
    return mode;
}

fn modeApplies(check: std.json.ObjectMap, mode: []const u8) !bool {
    for (try requiredStrings(check, "modes")) |entry| {
        if (std.mem.eql(u8, entry.string, mode)) return true;
    }
    return false;
}

fn explainSelection(allocator: Allocator, root: std.json.ObjectMap, gates: std.json.ObjectMap, jobs: []const []const u8, groups: []const []const u8, mode: []const u8, unmatched: bool) ![]const SelectionReason {
    var reasons: std.ArrayList(SelectionReason) = .empty;
    errdefer reasons.deinit(allocator);
    for (jobs) |job| {
        if (qualificationMode(mode)) {
            try reasons.append(allocator, .{ .check = job, .kind = "mode", .reference = mode });
        } else if (gates.get(job)) |route| {
            if (route.array.items.len == 0) {
                try reasons.append(allocator, .{ .check = job, .kind = "always_on" });
            } else if (std.mem.eql(u8, mode, "full")) {
                try reasons.append(allocator, .{ .check = job, .kind = "full" });
            } else if (unmatched and conservativeCheck(root, job)) {
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
    if (selection.unbound_workflow_jobs.len != 0) return error.UnboundWorkflowContext;
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

/// Inspect a command's captured bytes only; this does not establish execution.
pub fn outputPolicyAllows(check_value: Value, command_index: usize, stderr: []const u8) !bool {
    _ = try validateCheck(check_value);
    const check = try object(check_value);
    if (command_index >= check.get("argv").?.array.items.len) return error.InvalidCommandIndex;
    const limit = std.math.cast(usize, check.get("budgets").?.object.get("stderr_bytes").?.integer) orelse return error.InvalidBudget;
    if (stderr.len > limit) return error.DiagnosticLimit;
    if (check.get("stderr_policy")) |policies| {
        if (std.mem.eql(u8, policies.array.items[command_index].string, "reject-warning-prefix")) {
            var lines = std.mem.splitScalar(u8, stderr, '\n');
            while (lines.next()) |line| if (std.ascii.startsWithIgnoreCase(line, "Warning:")) return false;
        }
    }
    return true;
}

fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len < 3) return error.InvalidArguments;
    const inspect_program = std.mem.eql(u8, args[2], "inspect-program");
    const bind_program = std.mem.eql(u8, args[2], "bind-program-environment");
    if ((inspect_program or bind_program) and args.len != 4) return error.InvalidArguments;
    const output_policy = std.mem.eql(u8, args[2], "output-policy");
    if (output_policy and args.len != 5) return error.InvalidArguments;
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
    if (inspect_program or bind_program) {
        const inspected = try select(allocator, parsed.value, &.{}, "full");
        defer inspected.deinit(allocator);
        const reference = try programReference(try object(parsed.value), args[3]);
        var program_output: std.Io.Writer.Allocating = .init(allocator);
        defer program_output.deinit();
        var program_stringify: std.json.Stringify = .{ .writer = &program_output.writer };
        if (bind_program) {
            const bound = try bindWorkflowProgram(allocator, parsed.value, args[3], init.environ_map);
            defer bound.deinit(allocator);
            try program_stringify.write(.{ .argv = bound.argv, .controls = reference.program.object.get("controls").?, .argument_binding_only = true, .workflow_context_complete = false, .execution_supported = false });
        } else try program_stringify.write(.{ .program = reference.program, .workflow_context_complete = false, .execution_supported = false });
        try program_output.writer.writeByte('\n');
        if (program_output.written().len > 16 * 1024 * 1024) return error.DiagnosticLimit;
        try std.Io.File.stdout().writeStreamingAll(init.io, program_output.written());
        return;
    }
    if (output_policy) {
        const inspected = try select(allocator, parsed.value, &.{}, "pr");
        defer inspected.deinit(allocator);
        const checks = (try object(parsed.value)).get("checks") orelse return error.MissingCheck;
        const check = checks.object.get(args[3]) orelse return error.MissingCheck;
        const index = try std.fmt.parseInt(usize, args[4], 10);
        if (index >= check.object.get("argv").?.array.items.len) return error.InvalidCommandIndex;
        const limit = std.math.cast(usize, check.object.get("budgets").?.object.get("stderr_bytes").?.integer) orelse return error.InvalidBudget;
        var input_buffer: [4096]u8 = undefined;
        var input_reader = std.Io.File.stdin().readerStreaming(init.io, &input_buffer);
        const captured = try input_reader.interface.allocRemaining(allocator, .limited(@min(limit, 16 * 1024 * 1024)));
        const allowed = try outputPolicyAllows(check, index, captured);
        var policy_output: std.Io.Writer.Allocating = .init(allocator);
        defer policy_output.deinit();
        var policy_stringify: std.json.Stringify = .{ .writer = &policy_output.writer };
        try policy_stringify.write(.{ .policy_allows_output = allowed, .check_validation_performed = false, .execution_supported = false });
        try policy_output.writer.writeByte('\n');
        try std.Io.File.stdout().writeStreamingAll(init.io, policy_output.written());
        if (!allowed) return error.OutputPolicyRefused;
        return;
    }
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
