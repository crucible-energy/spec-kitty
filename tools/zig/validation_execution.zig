//! Serial candidate execution. Selection and qualified input identity stay with
//! their existing authorities; source-closed fixture proof grants no general
//! validator, platform, or hook qualification.
const std = @import("std");
const candidate = @import("validation_candidate.zig");
const receipt = @import("validation_receipt.zig");
const selection = @import("validation_selection.zig");
const process = @import("validation_process_darwin.zig");
const changelog = @import("validation_changelog.zig");
const memory_sampler = @import("validation_memory_sampler.zig");
const sampler_lifetime = @import("validation_sampler_lifetime.zig");
const Allocator = std.mem.Allocator;
const Value = std.json.Value;
const Request = struct { binding: []const u8, specification: []const u8, mode: []const u8, diagnostics: []const u8 };
const SamplerLifetime = struct {
    schema_version: u8,
    scope: []const u8,
    check_id: []const u8,
    start_index: usize,
    stop_index: usize,
    sampler_request: receipt.Pin,
    cgroup_request: receipt.Pin,
    report_request: receipt.Pin,
    summary_path: []const u8,
};
const Prepared = struct { binding: receipt.Binding, manifest: candidate.Manifest, order: []const []const u8, checks: std.json.ObjectMap, qualifications: []const []const receipt.Qualification, sampler_lifetimes: []const SamplerLifetime };
const StepResult = struct {
    index: usize,
    condition: []const u8,
    status: []const u8 = "refused",
    reason: ?[]const u8 = null,
    stdout_log: ?receipt.Pin = null,
    stderr_log: ?receipt.Pin = null,
    sampler_event: ?[]const u8 = null,
    result: ?process.Result = null,
};
const SamplerResult = struct {
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
    commitment: memory_sampler.OwnedSampling.Commitment,
    report: Value,
};
const CheckResult = struct {
    id: []const u8,
    status: []const u8,
    reason: ?[]const u8 = null,
    qualification_sha256: ?[]const u8 = null,
    stdout_log: ?receipt.Pin = null,
    stderr_log: ?receipt.Pin = null,
    sampler: ?SamplerResult = null,
    result: ?process.Result = null,
    steps: ?[]const StepResult = null,
};

fn lifetimeForCheck(lifetimes: []const SamplerLifetime, id: []const u8) ?SamplerLifetime {
    for (lifetimes) |lifetime| if (std.mem.eql(u8, lifetime.check_id, id)) return lifetime;
    return null;
}

fn pinMatchesBinding(init: std.process.Init, binding: receipt.Binding, expected: receipt.Pin) !bool {
    const current = try receipt.pin(init, expected.path);
    if (!try receipt.equal(init.arena.allocator(), expected, current)) return false;
    for (binding.files) |file| {
        if (std.mem.eql(u8, file.path, expected.path) and std.mem.eql(u8, file.sha256, expected.sha256) and file.mode == expected.mode and std.mem.eql(u8, file.role, "observed_dependency")) return true;
    }
    return false;
}

fn parseSamplerLifetimes(init: std.process.Init, binding: receipt.Binding, diagnostics_path: []const u8) ![]const SamplerLifetime {
    const allocator = init.arena.allocator();
    var lifetimes: std.ArrayList(SamplerLifetime) = .empty;
    for (binding.files) |file| {
        if (!std.mem.eql(u8, file.role, "specification")) continue;
        const parsed = try candidate.parse(allocator, try candidate.read(allocator, init.io, file.path));
        const rows = parsed.value.object.get("receipt_sampler_lifetimes") orelse continue;
        if (rows != .array or rows.array.items.len > 64 or lifetimes.items.len + rows.array.items.len > 64) return error.UnqualifiedSamplerLifetime;
        for (rows.array.items) |value| {
            const lifetime = try receipt.exact(SamplerLifetime, allocator, value);
            if (lifetime.schema_version != 1 or !std.mem.eql(u8, lifetime.scope, "exact-check-owned-native-memory-sampler") or lifetime.start_index != 0 or lifetime.stop_index != 3 or !safeOutputPath(diagnostics_path, lifetime.summary_path)) return error.PrivateEvidenceRequired;
            for (lifetimes.items) |previous| if (std.mem.eql(u8, previous.check_id, lifetime.check_id)) return error.UnqualifiedSamplerLifetime;
            if (!try pinMatchesBinding(init, binding, lifetime.sampler_request) or !try pinMatchesBinding(init, binding, lifetime.cgroup_request) or !try pinMatchesBinding(init, binding, lifetime.report_request)) return error.UnqualifiedSamplerLifetime;
            const sampler_document = try candidate.parse(allocator, try candidate.read(allocator, init.io, lifetime.sampler_request.path));
            const report_document = try candidate.parse(allocator, try candidate.read(allocator, init.io, lifetime.report_request.path));
            if (sampler_document.value != .object or report_document.value != .object) return error.UnqualifiedSamplerLifetime;
            const destination_value = sampler_document.value.object.get("destination") orelse return error.UnqualifiedSamplerLifetime;
            const state_value = report_document.value.object.get("state_path") orelse return error.UnqualifiedSamplerLifetime;
            const cgroup_value = report_document.value.object.get("cgroup_path") orelse return error.UnqualifiedSamplerLifetime;
            if (destination_value != .string or state_value != .string or cgroup_value != .string) return error.UnqualifiedSamplerLifetime;
            const expected_state = try std.fmt.allocPrint(allocator, "{s}/state.json", .{destination_value.string});
            if (!std.mem.eql(u8, expected_state, state_value.string) or !safeOutputPath(diagnostics_path, destination_value.string) or !safeOutputPath(diagnostics_path, state_value.string) or !safeOutputPath(diagnostics_path, cgroup_value.string)) return error.PrivateEvidenceRequired;
            const selected = try receipt.checkById(binding, lifetime.check_id);
            const proof = selected.closure_proof orelse return error.UnqualifiedSamplerLifetime;
            if (!try receipt.equal(allocator, proof, value)) return error.UnqualifiedSamplerLifetime;
            try lifetimes.append(allocator, lifetime);
        }
    }
    return lifetimes.toOwnedSlice(allocator);
}

fn contains(names: []const []const u8, name: []const u8) bool {
    for (names) |entry| if (std.mem.eql(u8, entry, name)) return true;
    return false;
}

fn underDirectory(root: []const u8, path: []const u8) bool {
    return std.mem.startsWith(u8, path, root) and path.len > root.len and path[root.len] == '/';
}

fn safeOutputPath(root: []const u8, path: []const u8) bool {
    if (!underDirectory(root, path) or !std.unicode.utf8ValidateSlice(path)) return false;
    for (path) |byte| if (byte < 32 or byte == 127) return false;
    var parts = std.mem.splitScalar(u8, path[root.len + 1 ..], '/');
    while (parts.next()) |part| if (part.len == 0 or std.mem.eql(u8, part, ".") or std.mem.eql(u8, part, "..")) return false;
    return true;
}

// Kahn order with lexical tie-breaking uses the already validated graph. The
// selected roster is complete before this operation; absent dependencies refuse.
fn dependencyOrder(allocator: Allocator, checks: std.json.ObjectMap, selected: []const []const u8) ![]const []const u8 {
    var ordered: std.ArrayList([]const u8) = .empty;
    var complete = std.StringHashMap(void).init(allocator);
    while (ordered.items.len < selected.len) {
        var next: ?[]const u8 = null;
        for (selected) |id| {
            if (complete.contains(id)) continue;
            var ready = true;
            for (checks.get(id).?.object.get("dependencies").?.array.items) |dependency| {
                if (!contains(selected, dependency.string)) return error.IncompleteSelection;
                ready = ready and complete.contains(dependency.string);
            }
            if (ready and (next == null or std.mem.lessThan(u8, id, next.?))) next = id;
        }
        const id = next orelse return error.InvalidDependency;
        try complete.put(id, {});
        try ordered.append(allocator, id);
    }
    return ordered.items;
}

fn limits(check: std.json.ObjectMap) !receipt.Limits {
    const budget = check.get("budgets").?.object;
    return .{
        .wall_ms = @intCast(budget.get("wall_ms").?.integer),
        .cleanup_ms = @intCast(budget.get("cleanup_ms").?.integer),
        .stdout_bytes = @intCast(budget.get("stdout_bytes").?.integer),
        .stderr_bytes = @intCast(budget.get("stderr_bytes").?.integer),
        .processes = @intCast(budget.get("sampled_processes").?.integer),
        .resident_bytes = @intCast(budget.get("sampled_resident_bytes").?.integer),
    };
}

fn processLimits(value: receipt.Limits) !process.Limits {
    // Refuse backend limits rather than lower or silently split authority budgets.
    if (value.wall_ms > 3_600_000 or value.cleanup_ms > 5000 or value.stdout_bytes > 16 * 1024 * 1024 or value.stderr_bytes > 16 * 1024 * 1024 or value.processes > 64) return error.UnsupportedBudget;
    return .{ .wall_ms = @intCast(value.wall_ms), .cleanup_ms = @intCast(value.cleanup_ms), .stdout_bytes = value.stdout_bytes, .stderr_bytes = value.stderr_bytes, .processes = @intCast(value.processes), .resident_bytes = value.resident_bytes };
}

fn simpleContext(check: std.json.ObjectMap, owns_memory_output: bool) !void {
    if (check.get("recipe")) |value| {
        const recipe = value.object;
        // This qualification does not admit detached samplers, external result
        // producers, setup/runtime resolution, decisions or instance overrides.
        if (recipe.contains("workflow_job") or recipe.get("advisory").?.bool or !std.mem.eql(u8, recipe.get("applicability").?.string, "routing") or recipe.get("packages").?.object.count() != 0 or recipe.get("instance_environment").?.object.count() != 0) return error.UnsupportedRecipeBinding;
        const inputs = recipe.get("required_inputs").?.array.items;
        if (owns_memory_output) {
            if (inputs.len != 2 or !std.mem.eql(u8, inputs[0].string, "candidate") or !std.mem.eql(u8, inputs[1].string, "memory_output")) return error.UnsupportedRecipeBinding;
        } else if (inputs.len != 1 or !std.mem.eql(u8, inputs[0].string, "candidate")) return error.UnsupportedRecipeBinding;
        const instances = recipe.get("instances").?.array.items;
        for (instances) |instance| if (!std.mem.eql(u8, instance.string, instances[0].string)) return error.UnsupportedRecipeBinding;
        for (recipe.get("conditions").?.array.items) |condition| if (!std.mem.eql(u8, condition.string, "success") and !std.mem.eql(u8, condition.string, "always")) return error.UnsupportedRecipeBinding;
        const observed = recipe.get("observed_dependencies").?.array.items;
        const dependencies = check.get("dependencies").?.array.items;
        if (observed.len != dependencies.len) return error.UnsupportedRecipeBinding;
        for (observed, 0..) |dependency, index| {
            for (observed[0..index]) |previous| if (std.mem.eql(u8, dependency.string, previous.string)) return error.UnsupportedRecipeBinding;
            var found = false;
            for (dependencies) |required| found = found or std.mem.eql(u8, dependency.string, required.string);
            if (!found) return error.UnsupportedRecipeBinding;
        }
        return;
    }
    if (check.get("argv").?.array.items.len != 1) return error.UnsupportedCheckLifecycle;
}

fn validateSamplerLifetime(binding: receipt.Binding, id: []const u8, check: std.json.ObjectMap, lifetime: SamplerLifetime) !void {
    const argv = check.get("argv").?.array.items;
    const recipe = check.get("recipe").?.object;
    const required = recipe.get("required_inputs").?.array.items;
    const conditions = recipe.get("conditions").?.array.items;
    const instances = recipe.get("instances").?.array.items;
    if (!std.mem.eql(u8, lifetime.check_id, id) or argv.len != 4 or lifetime.start_index != 0 or lifetime.stop_index != argv.len - 1 or required.len != 2 or conditions.len != argv.len or instances.len != argv.len) return error.UnqualifiedSamplerLifetime;
    if (!std.mem.eql(u8, required[0].string, "candidate") or !std.mem.eql(u8, required[1].string, "memory_output")) return error.UnsupportedRecipeBinding;
    for (instances) |instance| if (!std.mem.eql(u8, instance.string, "native")) return error.UnqualifiedSamplerLifetime;
    for (conditions, 0..) |condition, index| {
        const expected = if (index == lifetime.stop_index) "always" else "success";
        if (!std.mem.eql(u8, condition.string, expected)) return error.UnqualifiedSamplerLifetime;
    }
    const start = argv[lifetime.start_index].array.items;
    const stop = argv[lifetime.stop_index].array.items;
    if (start.len != 3 or stop.len != 3 or !std.mem.eql(u8, start[0].string, binding.native_executable.path) or !std.mem.eql(u8, stop[0].string, binding.native_executable.path) or !std.mem.eql(u8, start[1].string, "memory-owned-sample") or !std.mem.eql(u8, stop[1].string, "memory-owned-stop") or !std.mem.eql(u8, start[2].string, lifetime.sampler_request.path) or !std.mem.eql(u8, stop[2].string, lifetime.sampler_request.path)) return error.UnqualifiedSamplerLifetime;
}

fn commandQualification(init: std.process.Init, binding: receipt.Binding, id: []const u8, command_index: usize, fields: std.json.ObjectMap) !receipt.Qualification {
    const allocator = init.arena.allocator();
    const q = try receipt.qualificationAt(init, binding, id, command_index);
    if (!std.mem.eql(u8, q.producer.path, binding.native_executable.path) or !std.mem.eql(u8, q.producer.sha256, binding.native_executable.sha256) or q.producer.mode != binding.native_executable.mode) return error.UnqualifiedProducer;
    if (!std.mem.eql(u8, q.process_source_sha256, try candidate.hash(allocator, @embedFile("validation_process_darwin.zig")))) return error.UnqualifiedProducer;
    for (binding.native_sources) |source| {
        var found = false;
        for (q.producer_sources) |file| if (std.mem.eql(u8, std.fs.path.basename(file.path), source.name) and std.mem.eql(u8, file.sha256, source.sha256)) {
            found = true;
        };
        if (!found) return error.IncompleteProducerClosure;
    }
    if (!try receipt.equal(allocator, q.limits, try limits(fields))) return error.BudgetBindingMismatch;
    _ = try processLimits(q.limits);
    return q;
}

fn prepare(init: std.process.Init, request: Request) !Prepared {
    const allocator = init.arena.allocator();
    // Full is an actual complete-roster mode. Commit needs a separately bound
    // changed-path observation; caller paths cannot narrow required selection.
    if (!std.mem.eql(u8, request.mode, "full")) return error.UnsupportedChangedPathBinding;
    const binding = try receipt.loadBinding(init, request.binding);
    var specification_bound = false;
    for (binding.files) |file| {
        if (std.mem.eql(u8, file.role, "specification") and std.mem.eql(u8, request.specification, file.path) and file.candidate_path_hex != null) specification_bound = true;
    }
    if (!specification_bound) return error.UnboundSpecification;
    const document = try candidate.parse(allocator, try candidate.read(allocator, init.io, request.specification));
    var platform: []const u8 = "macos";
    if (@import("builtin").os.tag == .linux) platform = "linux";
    if (@import("builtin").os.tag != .macos and @import("builtin").os.tag != .linux) return error.PlatformUnsupported;
    const selected = try selection.selectForTarget(allocator, document.value, &.{}, request.mode, platform);
    if (selected.selected_jobs.len == 0 or selected.selected_jobs.len != binding.checks.len) return error.IncompleteSelection;
    for (binding.checks) |check| if (!contains(selected.selected_jobs, check.id)) return error.IncompleteSelection;
    const checks = document.value.object.get("checks").?.object;
    const order = try dependencyOrder(allocator, checks, selected.selected_jobs);
    const sampler_lifetimes = try parseSamplerLifetimes(init, binding, request.diagnostics);
    for (sampler_lifetimes) |lifetime| if (!contains(order, lifetime.check_id)) return error.UnqualifiedSamplerLifetime;
    const qualifications = try allocator.alloc([]const receipt.Qualification, order.len);
    for (order, 0..) |id, index| {
        const fields = checks.get(id).?.object;
        const lifetime = lifetimeForCheck(sampler_lifetimes, id);
        try simpleContext(fields, lifetime != null);
        if (lifetime) |owned| try validateSamplerLifetime(binding, id, fields, owned);
        const check = try receipt.checkById(binding, id);
        if (!try receipt.equal(allocator, fields.get("argv").?, (try candidate.parse(allocator, try candidate.json(allocator, check.argv))).value)) return error.CommandBindingMismatch;
        const environment = fields.get("environment").?.object;
        if (environment.count() != binding.request.environment_names.len) return error.EnvironmentBindingMismatch;
        var variables = environment.iterator();
        while (variables.next()) |entry| {
            const actual = init.environ_map.get(entry.key_ptr.*) orelse return error.EnvironmentBindingMismatch;
            if (!contains(binding.request.environment_names, entry.key_ptr.*) or !std.mem.eql(u8, actual, entry.value_ptr.string)) return error.EnvironmentBindingMismatch;
        }
        const commands = try allocator.alloc(receipt.Qualification, check.argv.len);
        for (commands, 0..) |*command, command_index| {
            command.* = try commandQualification(init, binding, id, command_index, fields);
            if (lifetime) |owned| {
                const worker_command = command_index == owned.start_index or command_index == owned.stop_index;
                if (worker_command != std.mem.eql(u8, command.scope, "exact-check-owned-native-memory-worker")) return error.UnqualifiedSamplerLifetime;
            }
        }
        qualifications[index] = commands;
    }
    const manifest_value = try candidate.parse(allocator, try candidate.read(allocator, init.io, binding.request.candidate_manifest));
    return .{ .binding = binding, .manifest = try receipt.exact(candidate.Manifest, allocator, manifest_value.value), .order = order, .checks = checks, .qualifications = qualifications, .sampler_lifetimes = sampler_lifetimes };
}

fn diagnostics(init: std.process.Init, request: Request, manifest: candidate.Manifest) !void {
    if (!std.fs.path.isAbsolute(request.diagnostics)) return error.PrivateEvidenceRequired;
    const resolved = try std.Io.Dir.cwd().realPathFileAlloc(init.io, request.diagnostics, init.arena.allocator());
    const stat = try std.Io.Dir.cwd().statFile(init.io, request.diagnostics, .{ .follow_symlinks = false });
    if (!std.mem.eql(u8, resolved, request.diagnostics) or stat.kind != .directory or stat.permissions.toMode() & 0o077 != 0) return error.PrivateEvidenceRequired;
    // Produced logs cannot mutate the candidate or the live repository.
    for ([_][]const u8{ manifest.root, manifest.repository }) |root| {
        if (std.mem.eql(u8, resolved, root) or (std.mem.startsWith(u8, resolved, root) and resolved.len > root.len and resolved[root.len] == '/')) return error.PrivateEvidenceRequired;
    }
}

fn currentInputs(init: std.process.Init, request: Request, prepared_binding: receipt.Binding, id: []const u8, index: usize, expected: receipt.Qualification) !void {
    const binding = try receipt.loadBinding(init, request.binding);
    if (!try receipt.equal(init.arena.allocator(), binding, prepared_binding)) return error.InputDrift;
    const current = try receipt.qualificationAt(init, binding, id, index);
    if (!try receipt.equal(init.arena.allocator(), current, expected)) return error.InputDrift;
}

const RecipeExecution = struct { check: CheckResult, custody_complete: bool, halted: bool };

const RetainedSamplerMonitor = struct {
    supervisor: *sampler_lifetime.Supervisor,
    limits: process.Limits,
    fn poll(context: *anyopaque, in_flight: process.InFlight) ?process.Failure {
        const self: *RetainedSamplerMonitor = @ptrCast(@alignCast(context));
        return self.supervisor.poll(in_flight, self.limits);
    }
};

fn scopeReason(failure: anyerror) []const u8 {
    return switch (failure) {
        error.OperationDeadlineExceeded => "wall_timeout",
        error.OperationCancelled => "cancelled",
        error.StdoutBudgetExceeded => "stdout_limit",
        error.StderrBudgetExceeded => "stderr_limit",
        error.CleanupBudgetExceeded => "cleanup-incomplete",
        else => @errorName(failure),
    };
}

fn executeRecipe(init: std.process.Init, request: Request, prepared: Prepared, id: []const u8, index: usize, environment: *const std.process.Environ.Map) !RecipeExecution {
    if (@import("builtin").os.tag != .macos and @import("builtin").os.tag != .linux) return error.PlatformUnsupported;
    const allocator = init.arena.allocator();
    const check = prepared.checks.get(id).?.object;
    const conditions = check.get("recipe").?.object.get("conditions").?.array.items;
    const qualifications = prepared.qualifications[index];
    const lifetime = lifetimeForCheck(prepared.sampler_lifetimes, id);
    var scope = try process.CheckScope.begin(allocator, init.io, try processLimits(qualifications[0].limits), 8192);
    defer scope.deinit(allocator);
    var worker: ?sampler_lifetime.Supervisor = null;
    var lifetime_inputs: ?memory_sampler.LifetimeRequests = null;
    defer {
        if (worker) |*owned| owned.dispose(init.io) catch {};
        if (lifetime_inputs) |*inputs| inputs.finish() catch {};
    }
    var result: CheckResult = .{ .id = id, .status = "refused", .qualification_sha256 = try candidate.hash(allocator, try candidate.json(allocator, qualifications)) };
    var steps: std.ArrayList(StepResult) = .empty;
    var failed = false;
    var stopped = false;
    var custody_complete = true;
    var halted = false;
    for (qualifications, conditions, 0..) |q, condition, command_index| {
        var step: StepResult = .{ .index = command_index, .condition = condition.string };
        const sampler_start = lifetime != null and command_index == lifetime.?.start_index;
        const sampler_stop = lifetime != null and command_index == lifetime.?.stop_index;
        const stop_owned_worker = sampler_stop and worker != null;
        if ((stopped and !stop_owned_worker) or (failed and std.mem.eql(u8, condition.string, "success"))) {
            step.status = "blocked";
            step.reason = if (stopped) "check-stopped" else "earlier-command-failed";
            try steps.append(allocator, step);
            continue;
        }
        scope.ready(init.io) catch |failure| {
            failed = true;
            stopped = true;
            halted = failure == error.OperationCancelled;
            step.status = "blocked";
            step.reason = scopeReason(failure);
            if (result.reason == null) result.reason = step.reason;
            try steps.append(allocator, step);
            continue;
        };
        currentInputs(init, request, prepared.binding, id, command_index, q) catch |failure| {
            failed = true;
            stopped = true;
            halted = true;
            step.reason = @errorName(failure);
            if (result.reason == null) result.reason = step.reason;
            try steps.append(allocator, step);
            continue;
        };
        const out_path = try std.fmt.allocPrint(allocator, "{s}/{d}-{d}.stdout.log", .{ request.diagnostics, index, command_index });
        const err_path = try std.fmt.allocPrint(allocator, "{s}/{d}-{d}.stderr.log", .{ request.diagnostics, index, command_index });
        const out = try std.Io.Dir.cwd().createFile(init.io, out_path, .{ .exclusive = true, .permissions = .fromMode(0o600) });
        defer out.close(init.io);
        const err = try std.Io.Dir.cwd().createFile(init.io, err_path, .{ .exclusive = true, .permissions = .fromMode(0o600) });
        defer err.close(init.io);

        if (sampler_start) {
            const owned = lifetime.?;
            lifetime_inputs = try memory_sampler.LifetimeRequests.capture(init, owned.sampler_request.path, owned.cgroup_request.path, owned.report_request.path, &scope);
            const cgroup_path = lifetime_inputs.?.cgroupResultPath() orelse return error.UnqualifiedSamplerLifetime;
            if (!safeOutputPath(request.diagnostics, lifetime_inputs.?.statePath()) or !safeOutputPath(request.diagnostics, cgroup_path) or !safeOutputPath(request.diagnostics, owned.summary_path)) return error.PrivateEvidenceRequired;
            worker = try sampler_lifetime.Supervisor.start(init, q.argv, prepared.manifest.root, environment, scope.deadline, scope.limits.cleanup_ms);
            scope.max_processes = @max(scope.max_processes, worker.?.max_sampled_processes);
            scope.max_resident = @max(scope.max_resident, worker.?.max_sampled_resident_bytes);
            step.status = "passed";
            step.sampler_event = "ready";
            step.stdout_log = try receipt.pin(init, out_path);
            step.stderr_log = try receipt.pin(init, err_path);
            currentInputs(init, request, prepared.binding, id, command_index, q) catch |failure| {
                failed = true;
                stopped = true;
                halted = true;
                step.status = "refused";
                step.reason = @errorName(failure);
                if (result.reason == null) result.reason = step.reason;
            };
            try steps.append(allocator, step);
            continue;
        }

        if (sampler_stop) {
            if (worker) |*owned_worker| {
                const completed = try owned_worker.stop(init);
                worker = null;
                const inputs = if (lifetime_inputs) |*held| held else return error.UnqualifiedSamplerLifetime;
                try inputs.verifyCommitment(completed.commitment, completed.pid, completed.samples);
                const cgroup_bytes = try memory_sampler.cgroupForLifetime(init, inputs, &scope);
                try inputs.writeCgroupResult(request.diagnostics, cgroup_bytes);
                const report_bytes = try memory_sampler.reportForLifetime(init, inputs.report_path, &scope);
                try inputs.verifyCommitment(completed.commitment, completed.pid, completed.samples);
                const parsed_report = try candidate.parse(allocator, report_bytes);
                const summary = parsed_report.value.object.get("summary_line") orelse return error.InvalidSamplerReport;
                if (summary != .string) return error.InvalidSamplerReport;
                try memory_sampler.appendSummary(init, lifetime.?.summary_path, summary.string, scope.deadline);
                try inputs.finish();
                lifetime_inputs = null;
                result.sampler = .{ .pid = completed.pid, .attempts = completed.attempts, .samples = completed.samples, .ready_attempts = completed.ready_attempts, .stopped_attempts = completed.stopped_attempts, .exit_code = completed.exit_code, .leader_reaped = completed.leader_reaped, .forced = completed.forced, .max_sampled_processes = completed.max_sampled_processes, .max_sampled_resident_bytes = completed.max_sampled_resident_bytes, .commitment = completed.commitment, .report = parsed_report.value };
                scope.max_processes = @max(scope.max_processes, completed.max_sampled_processes);
                scope.max_resident = @max(scope.max_resident, completed.max_sampled_resident_bytes);
                if (!completed.leader_reaped or completed.exit_code == null or completed.exit_code.? != 0 or completed.forced) {
                    failed = true;
                    custody_complete = false;
                    step.reason = "sampler-cleanup-incomplete";
                    if (result.reason == null) result.reason = step.reason;
                } else {
                    step.status = "passed";
                    step.sampler_event = "stopped";
                }
                step.stdout_log = try receipt.pin(init, out_path);
                step.stderr_log = try receipt.pin(init, err_path);
                currentInputs(init, request, prepared.binding, id, command_index, q) catch |failure| {
                    failed = true;
                    halted = true;
                    if (result.reason == null) result.reason = @errorName(failure);
                    step.status = "refused";
                    step.reason = @errorName(failure);
                };
                try steps.append(allocator, step);
                continue;
            }
            step.status = "blocked";
            step.reason = "sampler-start-not-complete";
            failed = true;
            if (result.reason == null) result.reason = step.reason;
            try steps.append(allocator, step);
            continue;
        }

        var process_options: process.Options = .{ .argv = q.argv, .cwd = .{ .path = prepared.manifest.root }, .environment = environment };
        var monitor_context: ?RetainedSamplerMonitor = null;
        if (worker) |*retained| {
            monitor_context = .{ .supervisor = retained, .limits = try processLimits(q.limits) };
            process_options.retained_monitor = .{ .context = @ptrCast(&monitor_context.?), .poll = RetainedSamplerMonitor.poll };
        }
        const outcome = scope.runLogged(allocator, init.io, process_options, .{ .stdout = out, .stderr = err }) catch |failure| {
            failed = true;
            stopped = true;
            halted = true;
            custody_complete = false;
            step.reason = scopeReason(failure);
            if (result.reason == null) result.reason = step.reason;
            step.stdout_log = try receipt.pin(init, out_path);
            step.stderr_log = try receipt.pin(init, err_path);
            try steps.append(allocator, step);
            continue;
        };
        if (worker) |retained| {
            scope.max_processes = @max(scope.max_processes, retained.max_sampled_processes);
            scope.max_resident = @max(scope.max_resident, retained.max_sampled_resident_bytes);
        }
        step.result = outcome;
        step.stdout_log = try receipt.pin(init, out_path);
        step.stderr_log = try receipt.pin(init, err_path);
        custody_complete = custody_complete and outcome.leader_reaped and outcome.group_disposed;
        const policy = try selection.outputPolicyAllows(prepared.checks.get(id).?, command_index, try candidate.read(allocator, init.io, err_path));
        if (outcome.failure == null and outcome.exit_code == 0 and custody_complete and policy) {
            step.status = "passed";
        } else {
            failed = true;
            step.reason = "nonzero-exit";
            if (outcome.failure) |failure| {
                step.reason = @tagName(failure);
                stopped = true;
                if (failure == .cancelled) halted = true;
            } else if (!custody_complete) {
                step.reason = "cleanup-incomplete";
            } else if (!policy) {
                step.reason = "output-policy-refused";
            }
            if (result.reason == null) result.reason = step.reason;
        }
        if (!custody_complete) {
            stopped = true;
            halted = true;
        }
        try steps.append(allocator, step);
    }
    if (worker) |*owned_worker| {
        const cleanup_started = std.Io.Clock.boot.now(init.io).nanoseconds;
        owned_worker.dispose(init.io) catch {
            custody_complete = false;
        };
        scope.cleanup_used_ns += @max(0, std.Io.Clock.boot.now(init.io).nanoseconds - cleanup_started);
        worker = null;
        failed = true;
        custody_complete = false;
        if (result.reason == null) result.reason = "sampler-not-normally-stopped";
    }
    if (lifetime_inputs) |*inputs| {
        inputs.finish() catch {
            failed = true;
            custody_complete = false;
            if (result.reason == null) result.reason = "sampler-input-disposition-incomplete";
        };
        lifetime_inputs = null;
    }
    result.steps = steps.items;
    // Final current binding/qualification checks belong to this same work clock
    // and signal owner, after every command, stream and raw-log identity joins.
    for (qualifications, 0..) |q, command_index| {
        currentInputs(init, request, prepared.binding, id, command_index, q) catch |failure| {
            failed = true;
            halted = true;
            if (result.reason == null) result.reason = @errorName(failure);
            break;
        };
    }
    const aggregate = scope.finish(allocator, init.io) catch |failure| {
        if (result.reason == null) result.reason = @errorName(failure);
        return .{ .check = result, .custody_complete = false, .halted = true };
    };
    result.result = aggregate;
    custody_complete = custody_complete and aggregate.leader_reaped and aggregate.group_disposed;
    if (aggregate.failure) |failure| {
        failed = true;
        if (result.reason == null) result.reason = @tagName(failure);
        if (failure == .cancelled) halted = true;
    }
    if (!failed and custody_complete) result.status = "passed";
    return .{ .check = result, .custody_complete = custody_complete, .halted = halted };
}

fn execute(init: std.process.Init, request: Request) !bool {
    const allocator = init.arena.allocator();
    const prepared = try prepare(init, request);
    try diagnostics(init, request, prepared.manifest);
    // Reserve the final receipt before any child effect. All output files use
    // exclusive creation; a second invocation cannot overwrite this custody.
    const receipt_path = try std.fmt.allocPrint(allocator, "{s}/run.json", .{request.diagnostics});
    const run_file = try std.Io.Dir.cwd().createFile(init.io, receipt_path, .{ .exclusive = true, .permissions = .fromMode(0o600) });
    defer run_file.close(init.io);
    var environment = std.process.Environ.Map.init(allocator);
    for (prepared.binding.request.environment_names) |name| if (init.environ_map.get(name)) |value| {
        try environment.put(name, value);
    };
    var results: std.ArrayList(CheckResult) = .empty;
    var passed = std.StringHashMap(void).init(allocator);
    var refusal: ?[]const u8 = null;
    var custody_complete = true;
    var halted = false;
    for (prepared.order, 0..) |id, index| {
        const check = prepared.checks.get(id).?.object;
        var blocked = halted or !custody_complete;
        for (check.get("dependencies").?.array.items) |dependency| blocked = blocked or !passed.contains(dependency.string);
        if (blocked) {
            try results.append(allocator, .{ .id = id, .status = "blocked", .reason = "required-dependency-or-custody-incomplete" });
            continue;
        }
        if (check.contains("recipe")) {
            const recipe = try executeRecipe(init, request, prepared, id, index, &environment);
            custody_complete = custody_complete and recipe.custody_complete;
            halted = halted or recipe.halted;
            if (std.mem.eql(u8, recipe.check.status, "passed")) {
                try passed.put(id, {});
            } else if (refusal == null) {
                refusal = recipe.check.reason orelse "recipe-incomplete";
            }
            try results.append(allocator, recipe.check);
            continue;
        }
        const q = prepared.qualifications[index][0];
        const out_path = try std.fmt.allocPrint(allocator, "{s}/{d}.stdout.log", .{ request.diagnostics, index });
        const err_path = try std.fmt.allocPrint(allocator, "{s}/{d}.stderr.log", .{ request.diagnostics, index });
        const out = try std.Io.Dir.cwd().createFile(init.io, out_path, .{ .exclusive = true, .permissions = .fromMode(0o600) });
        defer out.close(init.io);
        const err = try std.Io.Dir.cwd().createFile(init.io, err_path, .{ .exclusive = true, .permissions = .fromMode(0o600) });
        defer err.close(init.io);
        var result: CheckResult = .{ .id = id, .status = "refused", .qualification_sha256 = try candidate.hash(allocator, try candidate.json(allocator, q)) };
        currentInputs(init, request, prepared.binding, id, 0, q) catch |failure| {
            result.reason = @errorName(failure);
            result.stdout_log = try receipt.pin(init, out_path);
            result.stderr_log = try receipt.pin(init, err_path);
            try results.append(allocator, result);
            refusal = @errorName(failure);
            halted = true;
            continue;
        };
        const outcome = process.runLogged(allocator, init.io, .{ .argv = q.argv, .cwd = .{ .path = prepared.manifest.root }, .environment = &environment, .limits = try processLimits(q.limits), .display_bytes = 8192 }, .{ .stdout = out, .stderr = err }) catch |failure| {
            result.reason = @errorName(failure);
            // A thrown process error has no terminal disposition. Do not infer
            // a join from a failed start, empty logs, or a later successful job.
            custody_complete = false;
            result.stdout_log = try receipt.pin(init, out_path);
            result.stderr_log = try receipt.pin(init, err_path);
            try results.append(allocator, result);
            refusal = @errorName(failure);
            continue;
        };
        result.result = outcome;
        result.stdout_log = try receipt.pin(init, out_path);
        result.stderr_log = try receipt.pin(init, err_path);
        // Only the prevalidated exact no-process-creation closure makes original
        // group disposal sufficient for this check; the backend itself continues
        // reporting all_owned_children_terminal=false for general commands.
        custody_complete = outcome.leader_reaped and outcome.group_disposed;
        if (outcome.failure == .cancelled) halted = true;
        const raw_stderr = try candidate.read(allocator, init.io, err_path);
        const policy = try selection.outputPolicyAllows(prepared.checks.get(id).?, 0, raw_stderr);
        if (outcome.failure == null and outcome.exit_code == 0 and custody_complete and policy) {
            result.status = "passed";
            try passed.put(id, {});
        } else {
            result.reason = "nonzero-exit";
            if (outcome.failure) |failure| {
                result.reason = @tagName(failure);
            } else if (!custody_complete) {
                result.reason = "cleanup-incomplete";
            } else if (!policy) {
                result.reason = "output-policy-refused";
            }
            refusal = result.reason;
        }
        try results.append(allocator, result);
    }
    // Current inputs are sampled after every started check, stream join, and raw
    // log identity observation, including when required checks have failed.
    for (prepared.order, prepared.qualifications) |id, commands| {
        for (commands, 0..) |q, command_index| currentInputs(init, request, prepared.binding, id, command_index, q) catch |failure| {
            refusal = @errorName(failure);
        };
    }
    const accepted = refusal == null and custody_complete and passed.count() == prepared.order.len;
    const report = .{ .schema_version = 1, .accepted = accepted, .scope = "qualified-source-closed-local-execution", .binding_sha256 = try receipt.bindingSha(init, prepared.binding), .selected_checks = prepared.order, .results = results.items, .refusal = refusal, .qualified_scope_joined = custody_complete, .general_validator_qualification = false, .hook_installed = false, .external_write_reservation = false };
    const bytes = try candidate.json(allocator, report);
    try run_file.writeStreamingAll(init.io, bytes);
    try std.Io.File.stdout().writeStreamingAll(init.io, bytes);
    return accepted;
}

fn run(init: std.process.Init) !u8 {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len != 3) return error.InvalidArguments;
    if (std.mem.eql(u8, args[1], "changelog-style")) return changelog.command(init, args[2]);
    if (std.mem.eql(u8, args[1], "memory-cgroup")) return memory_sampler.cgroupCommand(init, args[2]);
    if (std.mem.eql(u8, args[1], "memory-report")) return memory_sampler.reportCommand(init, args[2]);
    if (std.mem.eql(u8, args[1], "memory-sample")) return memory_sampler.command(init, args[2]);
    if (std.mem.eql(u8, args[1], "memory-owned-sample")) return sampler_lifetime.workerCommand(init, args[2]);
    if (std.mem.eql(u8, args[1], "memory-owned-stop")) return error.SamplerOwnerRequired;
    if (!std.mem.eql(u8, args[1], "execute")) {
        try receipt.run(init);
        return 0;
    }
    const request = try receipt.exact(Request, allocator, (try candidate.parse(allocator, try candidate.read(allocator, init.io, args[2]))).value);
    if (!try execute(init, request)) return error.ExecutionRefused;
    return 0;
}

pub fn main(init: std.process.Init) void {
    const status = run(init) catch |failure| std.process.fatal("execution refused: {s}", .{@errorName(failure)});
    if (status != 0) std.process.exit(status);
}
