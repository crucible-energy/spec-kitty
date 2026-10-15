//! Serial candidate execution. Selection and qualified input identity stay with
//! their existing authorities; source-closed fixture proof grants no general
//! validator, platform, or hook qualification.
const std = @import("std");
const candidate = @import("validation_candidate.zig");
const receipt = @import("validation_receipt.zig");
const selection = @import("validation_selection.zig");
const process = @import("validation_process_darwin.zig");
const Allocator = std.mem.Allocator;
const Value = std.json.Value;
const Request = struct { binding: []const u8, specification: []const u8, mode: []const u8, diagnostics: []const u8 };
const Prepared = struct { binding: receipt.Binding, manifest: candidate.Manifest, order: []const []const u8, checks: std.json.ObjectMap, qualifications: []const receipt.Qualification };
const CheckResult = struct {
    id: []const u8,
    status: []const u8,
    reason: ?[]const u8 = null,
    qualification_sha256: ?[]const u8 = null,
    stdout_log: ?receipt.Pin = null,
    stderr_log: ?receipt.Pin = null,
    result: ?process.Result = null,
};

fn contains(names: []const []const u8, name: []const u8) bool {
    for (names) |entry| if (std.mem.eql(u8, entry, name)) return true;
    return false;
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

fn simpleContext(check: std.json.ObjectMap) !void {
    // Recipes carry matrix, prerequisite, producer, and always-cleanup meaning.
    // Until check-scoped ownership and their complete context are bound, refuse
    // the entire recipe. Never run a plausible-looking subset of its commands.
    if (check.contains("recipe")) return error.UnsupportedRecipeBinding;
    if (check.get("argv").?.array.items.len != 1) return error.UnsupportedCheckLifecycle;
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
    const qualifications = try allocator.alloc(receipt.Qualification, order.len);
    for (order, 0..) |id, index| {
        const fields = checks.get(id).?.object;
        try simpleContext(fields);
        const check = try receipt.checkById(binding, id);
        if (!try receipt.equal(allocator, fields.get("argv").?, (try candidate.parse(allocator, try candidate.json(allocator, check.argv))).value)) return error.CommandBindingMismatch;
        const environment = fields.get("environment").?.object;
        if (environment.count() != binding.request.environment_names.len) return error.EnvironmentBindingMismatch;
        var variables = environment.iterator();
        while (variables.next()) |entry| {
            const actual = init.environ_map.get(entry.key_ptr.*) orelse return error.EnvironmentBindingMismatch;
            if (!contains(binding.request.environment_names, entry.key_ptr.*) or !std.mem.eql(u8, actual, entry.value_ptr.string)) return error.EnvironmentBindingMismatch;
        }
        const q = try receipt.qualification(init, binding, check);
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
        qualifications[index] = q;
    }
    const manifest_value = try candidate.parse(allocator, try candidate.read(allocator, init.io, binding.request.candidate_manifest));
    return .{ .binding = binding, .manifest = try receipt.exact(candidate.Manifest, allocator, manifest_value.value), .order = order, .checks = checks, .qualifications = qualifications };
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

fn currentInputs(init: std.process.Init, request: Request, id: []const u8, expected: receipt.Qualification) !void {
    const binding = try receipt.loadBinding(init, request.binding);
    const current = try receipt.qualification(init, binding, try receipt.checkById(binding, id));
    if (!try receipt.equal(init.arena.allocator(), current, expected)) return error.InputDrift;
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
    for (prepared.order, 0..) |id, index| {
        const check = prepared.checks.get(id).?.object;
        var blocked = !custody_complete;
        for (check.get("dependencies").?.array.items) |dependency| blocked = blocked or !passed.contains(dependency.string);
        if (blocked) {
            try results.append(allocator, .{ .id = id, .status = "blocked", .reason = "required-dependency-or-custody-incomplete" });
            continue;
        }
        const q = prepared.qualifications[index];
        const out_path = try std.fmt.allocPrint(allocator, "{s}/{d}.stdout.log", .{ request.diagnostics, index });
        const err_path = try std.fmt.allocPrint(allocator, "{s}/{d}.stderr.log", .{ request.diagnostics, index });
        const out = try std.Io.Dir.cwd().createFile(init.io, out_path, .{ .exclusive = true, .permissions = .fromMode(0o600) });
        defer out.close(init.io);
        const err = try std.Io.Dir.cwd().createFile(init.io, err_path, .{ .exclusive = true, .permissions = .fromMode(0o600) });
        defer err.close(init.io);
        var result: CheckResult = .{ .id = id, .status = "refused", .qualification_sha256 = try candidate.hash(allocator, try candidate.json(allocator, q)) };
        currentInputs(init, request, id, q) catch |failure| {
            result.reason = @errorName(failure);
            result.stdout_log = try receipt.pin(init, out_path);
            result.stderr_log = try receipt.pin(init, err_path);
            try results.append(allocator, result);
            refusal = @errorName(failure);
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
    for (prepared.order, prepared.qualifications) |id, q| {
        currentInputs(init, request, id, q) catch |failure| {
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

fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len != 3) return error.InvalidArguments;
    if (!std.mem.eql(u8, args[1], "execute")) return receipt.run(init);
    const request = try receipt.exact(Request, allocator, (try candidate.parse(allocator, try candidate.read(allocator, init.io, args[2]))).value);
    if (!try execute(init, request)) return error.ExecutionRefused;
}

pub fn main(init: std.process.Init) void {
    run(init) catch |failure| std.process.fatal("execution refused: {s}", .{@errorName(failure)});
}
