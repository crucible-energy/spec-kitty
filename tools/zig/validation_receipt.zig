//! Exact input bindings. Binding an input does not execute or qualify a check.
const std = @import("std");
const candidate = @import("validation_candidate.zig");
const Allocator = std.mem.Allocator;
const Value = std.json.Value;
const FileRequest = struct { role: []const u8, path: []const u8, candidate_path_hex: ?[]const u8 };
pub const Check = struct { id: []const u8, argv: []const []const []const u8, closure_proof: ?Value };
const Request = struct { schema_version: u8, candidate_manifest: []const u8, files: []const FileRequest, environment_names: []const []const u8, checks: []const Check };
const File = struct { role: []const u8, path: []const u8, candidate_path_hex: ?[]const u8, sha256: []const u8, mode: u32 };
const Environment = struct { name: []const u8, present: bool, sha256: ?[]const u8 };
const Source = struct { name: []const u8, sha256: []const u8 };
const Executable = struct { path: []const u8, sha256: []const u8, mode: u32 };
pub const Binding = struct {
    schema_version: u8 = 1,
    binding_only: bool = true,
    acceptance_performed: bool = false,
    request: Request,
    candidate_manifest_sha256: []const u8,
    native_executable: Executable,
    native_sources: []const Source,
    compiler_version: []const u8,
    files: []const File,
    environment: []const Environment,
    checks: []const Check,
};
const PlanRequest = struct { binding: []const u8, check_id: []const u8 };

pub fn exact(comptime T: type, allocator: Allocator, value: Value) !T {
    const fields = try candidate.object(value);
    const names = std.meta.fieldNames(T);
    if (fields.count() != names.len) return error.InvalidBinding;
    for (names) |name| {
        if (!fields.contains(name)) return error.InvalidBinding;
    }
    return (try std.json.parseFromSlice(T, allocator, try candidate.json(allocator, value), .{ .duplicate_field_behavior = .@"error" })).value;
}

fn fileOrder(_: void, left: File, right: File) bool {
    const order = std.mem.order(u8, left.role, right.role);
    if (order != .eq) return order == .lt;
    return std.mem.lessThan(u8, left.path, right.path);
}

fn environmentOrder(_: void, left: Environment, right: Environment) bool {
    return std.mem.lessThan(u8, left.name, right.name);
}

fn validWord(word: []const u8) bool {
    return word.len <= 8192 and std.mem.indexOfScalar(u8, word, 0) == null;
}

fn bind(init: std.process.Init, request: Request) !Binding {
    const allocator = init.arena.allocator();
    if (request.schema_version != 1 or request.files.len > 4096 or request.checks.len == 0 or request.checks.len > 4096 or request.environment_names.len > 4096) return error.InvalidBinding;
    const manifest_bytes = try candidate.read(allocator, init.io, request.candidate_manifest);
    const manifest_value = try candidate.parse(allocator, manifest_bytes);
    try candidate.verify(allocator, init.io, init.environ_map, manifest_value.value);
    const manifest = try exact(candidate.Manifest, allocator, manifest_value.value);
    const sources = try allocator.dupe(Source, &.{
        .{ .name = "validation_candidate.zig", .sha256 = try candidate.hash(allocator, @embedFile("validation_candidate.zig")) },
        .{ .name = "validation_receipt.zig", .sha256 = try candidate.hash(allocator, @embedFile("validation_receipt.zig")) },
        .{ .name = "validation_execution.zig", .sha256 = try candidate.hash(allocator, @embedFile("validation_execution.zig")) },
        .{ .name = "validation_selection.zig", .sha256 = try candidate.hash(allocator, @embedFile("validation_selection.zig")) },
        .{ .name = "validation_process_darwin.zig", .sha256 = try candidate.hash(allocator, @embedFile("validation_process_darwin.zig")) },
    });
    const found_sources = try allocator.alloc(bool, sources.len);
    for (found_sources) |*found| found.* = false;
    var roles = std.StringHashMap(void).init(allocator);
    var files: std.ArrayList(File) = .empty;
    for (request.files) |input| {
        var supported = false;
        for ([_][]const u8{ "launcher", "specification", "native_source", "toolchain", "dependency_lock", "observed_dependency" }) |role| {
            if (std.mem.eql(u8, input.role, role)) supported = true;
        }
        if (!supported or !std.fs.path.isAbsolute(input.path) or !validWord(input.path)) return error.InvalidBinding;
        const path = try std.Io.Dir.cwd().realPathFileAlloc(init.io, input.path, allocator);
        const contents = try candidate.read(allocator, init.io, path);
        const sha = try candidate.hash(allocator, contents);
        const file = try std.Io.Dir.cwd().openFile(init.io, path, .{});
        defer file.close(init.io);
        const stat = try file.stat(init.io);
        if (stat.kind != .file) return error.InvalidBinding;
        if (input.candidate_path_hex) |encoded| {
            const relative = try candidate.decodePath(allocator, encoded);
            var matched = false;
            for (manifest.paths) |entry| {
                if (std.mem.eql(u8, entry.path_hex, encoded) and std.mem.eql(u8, entry.sha256, sha) and !std.mem.eql(u8, entry.mode, "120000")) matched = true;
            }
            const live_path = try std.fmt.allocPrint(allocator, "{s}/{s}", .{ manifest.repository, relative });
            if (!matched or !std.mem.eql(u8, live_path, input.path)) return error.StagedInputMismatch;
        } else if (!std.mem.eql(u8, input.role, "toolchain") and !std.mem.eql(u8, input.role, "observed_dependency")) return error.MissingStagedBinding;
        if (std.mem.eql(u8, input.role, "native_source")) {
            var matched = false;
            for (sources, 0..) |source, index| {
                if (std.mem.eql(u8, std.fs.path.basename(input.path), source.name) and std.mem.eql(u8, sha, source.sha256) and !found_sources[index]) {
                    found_sources[index] = true;
                    matched = true;
                }
            }
            if (!matched) return error.NativeSourceMismatch;
        }
        try roles.put(input.role, {});
        try files.append(allocator, .{ .role = input.role, .path = path, .candidate_path_hex = input.candidate_path_hex, .sha256 = sha, .mode = stat.permissions.toMode() });
    }
    if (roles.count() != 6) return error.IncompleteBinding;
    for (found_sources) |found| if (!found) return error.IncompleteBinding;
    std.mem.sort(File, files.items, {}, fileOrder);
    for (files.items, 0..) |file, index| {
        if (index > 0 and !fileOrder({}, files.items[index - 1], file)) return error.DuplicateBinding;
    }
    var environment: std.ArrayList(Environment) = .empty;
    for (request.environment_names) |name| {
        if (name.len == 0 or !validWord(name) or std.mem.indexOfScalar(u8, name, '=') != null) return error.InvalidEnvironment;
        const value = init.environ_map.get(name);
        var sha: ?[]const u8 = null;
        if (value) |bytes| sha = try candidate.hash(allocator, bytes);
        try environment.append(allocator, .{ .name = name, .present = value != null, .sha256 = sha });
    }
    std.mem.sort(Environment, environment.items, {}, environmentOrder);
    for (environment.items, 0..) |entry, index| {
        if (index > 0 and std.mem.eql(u8, entry.name, environment.items[index - 1].name)) return error.DuplicateBinding;
    }
    var checks = std.StringHashMap(void).init(allocator);
    for (request.checks) |check| {
        if (check.id.len == 0 or !validWord(check.id) or check.argv.len == 0 or check.argv.len > 4096) return error.UnqualifiedClosure;
        const slot = try checks.getOrPut(check.id);
        if (slot.found_existing) return error.DuplicateBinding;
        for (check.argv) |command| {
            if (command.len == 0 or command.len > 4096 or command[0].len == 0 or !std.fs.path.isAbsolute(command[0])) return error.InvalidArgv;
            for (command) |word| {
                if (!validWord(word)) return error.InvalidArgv;
            }
        }
    }
    const executable = try std.process.executablePathAlloc(init.io, allocator);
    // Repeat complete candidate sampling after all other input observations.
    try candidate.verify(allocator, init.io, init.environ_map, manifest_value.value);
    return .{ .request = request, .candidate_manifest_sha256 = try candidate.hash(allocator, manifest_bytes), .native_executable = .{ .path = executable, .sha256 = try candidate.hash(allocator, try candidate.read(allocator, init.io, executable)), .mode = (try pin(init, executable)).mode }, .native_sources = sources, .compiler_version = @import("builtin").zig_version_string, .files = files.items, .environment = environment.items, .checks = request.checks };
}

fn currentBinding(init: std.process.Init, value: Value) !Binding {
    const allocator = init.arena.allocator();
    var fields = try candidate.object(value);
    const expected = try candidate.text(fields, "sha256");
    _ = fields.swapRemove("sha256");
    const binding = try exact(Binding, allocator, .{ .object = fields });
    if (binding.schema_version != 1 or !binding.binding_only or binding.acceptance_performed or !std.mem.eql(u8, expected, try candidate.hash(allocator, try candidate.json(allocator, binding)))) return error.InvalidBinding;
    const current = bind(init, binding.request) catch return error.InputDrift;
    if (!std.mem.eql(u8, try candidate.json(allocator, binding), try candidate.json(allocator, current))) return error.InputDrift;
    return current;
}

fn pythonPlan(init: std.process.Init, request: PlanRequest) ![]const u8 {
    const allocator = init.arena.allocator();
    const value = try candidate.parse(allocator, try candidate.read(allocator, init.io, request.binding));
    const binding = try currentBinding(init, value.value);
    const manifest_value = try candidate.parse(allocator, try candidate.read(allocator, init.io, binding.request.candidate_manifest));
    const manifest = try exact(candidate.Manifest, allocator, manifest_value.value);
    var selected: ?Check = null;
    for (binding.checks) |check| {
        if (std.mem.eql(u8, check.id, request.check_id)) selected = check;
    }
    const check = selected orelse return error.UnknownCheck;
    if (check.argv.len != 1) return error.UnsupportedImportContext;
    const argv = check.argv[0];
    if (argv.len < 5 or !std.mem.eql(u8, argv[1], "-I") or !std.mem.eql(u8, argv[2], "-S") or !std.mem.eql(u8, argv[3], "-B") or !candidate.safeRelative(argv[4])) return error.UnsupportedImportContext;
    var executable_bound = false;
    const executable = try std.Io.Dir.cwd().realPathFileAlloc(init.io, argv[0], allocator);
    for (binding.files) |file| {
        if (std.mem.eql(u8, file.role, "toolchain") and std.mem.eql(u8, file.path, executable)) executable_bound = true;
    }
    if (!executable_bound) return error.UnboundExecutable;
    const encoded = try candidate.pathHex(allocator, argv[4]);
    var script_bound = false;
    for (manifest.paths) |entry| {
        if (std.mem.eql(u8, encoded, entry.path_hex) and !std.mem.eql(u8, entry.mode, "120000")) script_bound = true;
    }
    if (!script_bound) return error.UnboundScript;
    // -I excludes ambient PYTHON* paths and user site; -S excludes site/.pth
    // execution; -B keeps the snapshot immutable. These four bootstrap statements
    // add only candidate roots. This is import isolation, not a filesystem sandbox
    // or a qualified third-party dependency environment.
    const bootstrap = "import sys,runpy\nroot=sys.argv.pop(1)\nsys.path[:0]=[root+'/src',root]\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name='__main__')\n";
    var planned: std.ArrayList([]const u8) = .empty;
    try planned.appendSlice(allocator, &.{ argv[0], "-I", "-S", "-B", "-c", bootstrap, manifest.root });
    try planned.appendSlice(allocator, argv[4..]);
    return candidate.json(allocator, .{ .argv = planned.items, .cwd = manifest.root, .environment_names = binding.request.environment_names, .execution_performed = false, .dependency_context = "isolated-stdlib-and-candidate" });
}

// Qualification documents are input policy, anchored in staged specification bytes.
// The consumer checks their complete identities; it does not infer arbitrary
// program semantics from argv, check names, caller booleans, or group_disposed.
// No production qualification document is shipped by this module.
pub const Pin = struct { path: []const u8, resolved: []const u8, sha256: []const u8, mode: u32 };
pub const Limits = struct { wall_ms: u64, cleanup_ms: u64, stdout_bytes: usize, stderr_bytes: usize, processes: usize, resident_bytes: usize };
pub const Qualification = struct {
    schema_version: u8,
    scope: []const u8,
    platform: []const u8,
    argv: []const []const u8,
    environment_names: []const []const u8,
    limits: Limits,
    program_path_hex: []const u8,
    program_sha256: []const u8,
    producer: Executable,
    producer_sources: []const Pin,
    producer_source_tool_sha256: []const u8,
    process_source_sha256: []const u8,
    compiler_version: []const u8,
    runtime_manifest_sha256: []const u8,
    runtime_files: []const Pin,
};
const Producer = struct { executable_path: []const u8, executable_sha256: []const u8, source_tool_sha256: []const u8, process_source_sha256: []const u8, compiler_version: []const u8 };
const Program = struct { source_sha256: []const u8, runtime_manifest_sha256: []const u8, scope: []const u8, runtime_files: []const Pin };
const Outcome = struct { stdout: []const u8, stderr: []const u8, failure: ?[]const u8, exit_code: ?u8, leader_reaped: bool, group_disposed: bool, elapsed_ms: u64, max_sampled_processes: usize, max_sampled_resident_bytes: usize };
const Witness = struct {
    schema_version: u8,
    run_id: []const u8,
    binding_sha256: []const u8,
    check_id: []const u8,
    producer: Producer,
    program_qualification: Program,
    argv: []const []const u8,
    cwd: []const u8,
    environment: []const Environment,
    limits: Limits,
    result: Outcome,
    ownership_scope: []const u8,
    session_escape_containment_qualified: bool,
    usage_measurement: []const u8,
};
const Evidence = struct {
    schema_version: u8 = 1,
    evidence_only: bool = true,
    acceptance_performed: bool = false,
    binding_sha256: []const u8,
    check_id: []const u8,
    qualification_sha256: []const u8,
    witness: Pin,
    stdout_log: Pin,
    stderr_log: Pin,
    run_id: []const u8,
};
const RecordRequest = struct { binding: []const u8, check_id: []const u8, witness: []const u8, stdout_log: []const u8, stderr_log: []const u8 };
const ReuseRequest = struct { binding: []const u8, check_id: []const u8, evidence: ?[]const u8 };
const AcceptRequest = struct { binding: []const u8, evidence: []const []const u8 };

pub fn equal(allocator: Allocator, a: anytype, b: @TypeOf(a)) !bool {
    return std.mem.eql(u8, try candidate.json(allocator, a), try candidate.json(allocator, b));
}

pub fn pin(init: std.process.Init, path: []const u8) !Pin {
    const allocator = init.arena.allocator();
    if (!std.fs.path.isAbsolute(path) or !validWord(path)) return error.InvalidEvidence;
    const resolved = try std.Io.Dir.cwd().realPathFileAlloc(init.io, path, allocator);
    const file = try std.Io.Dir.cwd().openFile(init.io, path, .{});
    defer file.close(init.io);
    const stat = try file.stat(init.io);
    if (stat.kind != .file) return error.InvalidEvidence;
    return .{ .path = path, .resolved = resolved, .sha256 = try candidate.hash(allocator, try candidate.read(allocator, init.io, path)), .mode = stat.permissions.toMode() };
}

fn currentPin(init: std.process.Init, expected: Pin) !void {
    if (!try equal(init.arena.allocator(), expected, try pin(init, expected.path))) return error.EvidenceDrift;
}

pub fn checkById(binding: Binding, id: []const u8) !Check {
    for (binding.checks) |check| {
        if (std.mem.eql(u8, check.id, id)) return check;
    }
    return error.UnknownCheck;
}

pub fn loadBinding(init: std.process.Init, path: []const u8) !Binding {
    const value = try candidate.parse(init.arena.allocator(), try candidate.read(init.arena.allocator(), init.io, path));
    return currentBinding(init, value.value);
}

pub fn qualification(init: std.process.Init, binding: Binding, check: Check) !Qualification {
    const allocator = init.arena.allocator();
    if (@import("builtin").os.tag != .macos or check.argv.len != 1) return error.UnqualifiedClosure;
    var selected: ?Qualification = null;
    for (binding.files) |file| {
        if (!std.mem.eql(u8, file.role, "specification")) continue;
        const value = try candidate.parse(allocator, try candidate.read(allocator, init.io, file.path));
        const fields = try candidate.object(value.value);
        const documents = fields.get("receipt_qualifications") orelse continue;
        if (documents != .array or documents.array.items.len > 4096) return error.UnqualifiedClosure;
        for (documents.array.items) |document| {
            const q = try exact(Qualification, allocator, document);
            if (!try equal(allocator, q.argv, check.argv[0])) continue;
            if (selected != null) return error.DuplicateBinding;
            selected = q;
        }
    }
    const q = selected orelse return error.UnqualifiedClosure;
    if (q.schema_version != 1 or !std.mem.eql(u8, q.scope, "exact-isolated-source-no-process-creation") or !std.mem.eql(u8, q.platform, @tagName(@import("builtin").cpu.arch) ++ "-macos") or !std.mem.eql(u8, q.compiler_version, @import("builtin").zig_version_string)) return error.UnqualifiedClosure;
    if (q.producer_sources.len == 0 or q.runtime_files.len == 0 or q.limits.wall_ms == 0 or q.limits.cleanup_ms == 0 or q.limits.stdout_bytes == 0 or q.limits.stderr_bytes == 0 or q.limits.processes == 0 or q.limits.resident_bytes == 0) return error.UnqualifiedClosure;
    if (!try equal(allocator, q.environment_names, binding.request.environment_names)) return error.UnqualifiedClosure;
    const producer = try pin(init, q.producer.path);
    if (!std.mem.eql(u8, producer.sha256, q.producer.sha256) or producer.mode != q.producer.mode) return error.EvidenceDrift;
    if (q.limits.wall_ms > std.math.maxInt(u64) - q.limits.cleanup_ms) return error.UnqualifiedClosure;
    var source_hash = std.crypto.hash.sha2.Sha256.init(.{});
    var process_bound = false;
    var program_source_bound = false;
    var runtime_manifest_bound = false;
    for (q.producer_sources) |file| {
        try currentPin(init, file);
        source_hash.update(try candidate.read(allocator, init.io, file.path));
        if (std.mem.eql(u8, file.sha256, q.process_source_sha256)) process_bound = true;
        if (std.mem.eql(u8, file.sha256, q.program_sha256)) program_source_bound = true;
        if (std.mem.eql(u8, file.sha256, q.runtime_manifest_sha256)) runtime_manifest_bound = true;
    }
    if (!process_bound or !program_source_bound or !runtime_manifest_bound) return error.UnqualifiedClosure;
    const source_sha = std.fmt.bytesToHex(source_hash.finalResult(), .lower);
    if (!std.mem.eql(u8, &source_sha, q.producer_source_tool_sha256)) return error.EvidenceDrift;
    for (q.runtime_files) |file| {
        try currentPin(init, file);
        var bound = false;
        for (binding.files) |input| {
            if ((std.mem.eql(u8, input.role, "toolchain") or std.mem.eql(u8, input.role, "observed_dependency")) and std.mem.eql(u8, input.path, file.resolved) and std.mem.eql(u8, input.sha256, file.sha256) and input.mode == file.mode) bound = true;
        }
        if (!bound) return error.UnboundDependency;
    }
    // Execute the canonical pinned command identity itself. A separately bound
    // resolved file cannot authorize an argv alias that may later be retargeted.
    const command = try pin(init, q.argv[0]);
    if (!std.mem.eql(u8, command.path, command.resolved)) return error.UnboundExecutable;
    var command_bound = false;
    for (q.runtime_files) |file| {
        if (try equal(allocator, command, file)) command_bound = true;
    }
    if (!command_bound) return error.UnboundExecutable;
    const manifest_value = try candidate.parse(allocator, try candidate.read(allocator, init.io, binding.request.candidate_manifest));
    const manifest = try exact(candidate.Manifest, allocator, manifest_value.value);
    var program_bound = false;
    for (manifest.paths) |file| {
        if (std.mem.eql(u8, file.path_hex, q.program_path_hex) and std.mem.eql(u8, file.sha256, q.program_sha256) and !std.mem.eql(u8, file.mode, "120000")) program_bound = true;
    }
    if (!program_bound) return error.UnqualifiedClosure;
    return q;
}

pub fn bindingSha(init: std.process.Init, binding: Binding) ![]const u8 {
    return candidate.hash(init.arena.allocator(), try candidate.json(init.arena.allocator(), binding));
}

fn privateEvidencePaths(init: std.process.Init, paths: []const []const u8) !void {
    const allocator = init.arena.allocator();
    for (paths, 0..) |path, index| {
        if (!std.fs.path.isAbsolute(path) or !validWord(path)) return error.PrivateEvidenceRequired;
        const parent = std.fs.path.dirname(path) orelse return error.PrivateEvidenceRequired;
        const directory = try std.Io.Dir.cwd().statFile(init.io, parent, .{ .follow_symlinks = false });
        if (directory.kind != .directory or directory.permissions.toMode() & 0o077 != 0) return error.PrivateEvidenceRequired;
        const stat = try std.Io.Dir.cwd().statFile(init.io, path, .{ .follow_symlinks = false });
        if (stat.kind != .file or stat.nlink != 1) return error.PrivateEvidenceRequired;
        const resolved = try std.Io.Dir.cwd().realPathFileAlloc(init.io, path, allocator);
        if (!std.mem.eql(u8, path, resolved)) return error.PrivateEvidenceRequired;
        for (paths[0..index]) |previous| {
            if (std.mem.eql(u8, path, previous)) return error.PrivateEvidenceRequired;
        }
    }
}

fn record(init: std.process.Init, request: RecordRequest) !Evidence {
    const allocator = init.arena.allocator();
    const binding = try loadBinding(init, request.binding);
    try privateEvidencePaths(init, &.{ request.witness, request.stdout_log, request.stderr_log });
    const check = try checkById(binding, request.check_id);
    const q = try qualification(init, binding, check);
    const raw = try candidate.read(allocator, init.io, request.witness);
    const value = try candidate.parse(allocator, raw);
    const witness = try exact(Witness, allocator, value.value);
    const sha = try bindingSha(init, binding);
    const qsha = try candidate.hash(allocator, try candidate.json(allocator, q));
    const expected_producer = Producer{ .executable_path = q.producer.path, .executable_sha256 = q.producer.sha256, .source_tool_sha256 = q.producer_source_tool_sha256, .process_source_sha256 = q.process_source_sha256, .compiler_version = q.compiler_version };
    const expected_program = Program{ .source_sha256 = q.program_sha256, .runtime_manifest_sha256 = q.runtime_manifest_sha256, .scope = q.scope, .runtime_files = q.runtime_files };
    const manifest_value = try candidate.parse(allocator, try candidate.read(allocator, init.io, binding.request.candidate_manifest));
    const manifest = try exact(candidate.Manifest, allocator, manifest_value.value);
    if (witness.schema_version != 1 or witness.run_id.len == 0 or !validWord(witness.run_id) or !std.mem.eql(u8, witness.binding_sha256, sha) or !std.mem.eql(u8, witness.check_id, check.id) or !std.mem.eql(u8, witness.cwd, manifest.root)) return error.InvalidEvidence;
    if (!try equal(allocator, witness.producer, expected_producer) or !try equal(allocator, witness.program_qualification, expected_program) or !try equal(allocator, witness.argv, q.argv) or !try equal(allocator, witness.environment, binding.environment) or !try equal(allocator, witness.limits, q.limits)) return error.InvalidEvidence;
    if (!std.mem.eql(u8, witness.ownership_scope, "original-posix-group") or witness.session_escape_containment_qualified or !std.mem.eql(u8, witness.usage_measurement, "sampled-not-hard-peaks")) return error.UnqualifiedOwnership;
    const result = witness.result;
    if (result.failure != null or result.exit_code == null or result.exit_code.? != 0 or !result.leader_reaped or !result.group_disposed) return error.IncompleteCheck;
    if (result.elapsed_ms > q.limits.wall_ms + q.limits.cleanup_ms or result.stdout.len > q.limits.stdout_bytes or result.stderr.len > q.limits.stderr_bytes or result.max_sampled_processes > q.limits.processes or result.max_sampled_resident_bytes > q.limits.resident_bytes) return error.IncompleteCheck;
    if (!std.mem.eql(u8, result.stdout, try candidate.read(allocator, init.io, request.stdout_log)) or !std.mem.eql(u8, result.stderr, try candidate.read(allocator, init.io, request.stderr_log))) return error.InvalidLogs;
    const evidence = Evidence{ .binding_sha256 = sha, .check_id = check.id, .qualification_sha256 = qsha, .witness = try pin(init, request.witness), .stdout_log = try pin(init, request.stdout_log), .stderr_log = try pin(init, request.stderr_log), .run_id = witness.run_id };
    // Recheck every candidate/tool/dependency observation after result/log cleanup.
    _ = try loadBinding(init, request.binding);
    return evidence;
}

fn evidenceCurrent(init: std.process.Init, binding_path: []const u8, path: []const u8) !Evidence {
    const allocator = init.arena.allocator();
    const parsed = try candidate.parse(allocator, try candidate.read(allocator, init.io, path));
    var fields = try candidate.object(parsed.value);
    const expected_sha = try candidate.text(fields, "sha256");
    _ = fields.swapRemove("sha256");
    const evidence = try exact(Evidence, allocator, .{ .object = fields });
    if (evidence.schema_version != 1 or !evidence.evidence_only or evidence.acceptance_performed or !std.mem.eql(u8, expected_sha, try candidate.hash(allocator, try candidate.json(allocator, evidence)))) return error.InvalidEvidence;
    try currentPin(init, evidence.witness);
    try currentPin(init, evidence.stdout_log);
    try currentPin(init, evidence.stderr_log);
    const current = try record(init, .{ .binding = binding_path, .check_id = evidence.check_id, .witness = evidence.witness.path, .stdout_log = evidence.stdout_log.path, .stderr_log = evidence.stderr_log.path });
    if (!try equal(allocator, evidence, current)) return error.InvalidEvidence;
    return evidence;
}

fn reuse(init: std.process.Init, request: ReuseRequest) ![]const u8 {
    const allocator = init.arena.allocator();
    const binding = try loadBinding(init, request.binding);
    const check = try checkById(binding, request.check_id);
    var action: []const u8 = "fresh";
    var reason: []const u8 = "closure-unproved";
    if (check.closure_proof) |proof| {
        const q = qualification(init, binding, check) catch return candidate.json(allocator, .{ .action = action, .reason = reason, .check_id = check.id, .acceptance_performed = false });
        const closure = exact(struct { qualification_sha256: []const u8 }, allocator, proof) catch return error.UnqualifiedClosure;
        if (!std.mem.eql(u8, closure.qualification_sha256, try candidate.hash(allocator, try candidate.json(allocator, q)))) return error.UnqualifiedClosure;
        reason = "evidence-missing";
        if (request.evidence) |path| {
            const evidence = try evidenceCurrent(init, request.binding, path);
            if (!std.mem.eql(u8, evidence.check_id, check.id)) return error.InvalidEvidence;
            action = "reuse";
            reason = "matching-qualified-check";
        }
    }
    _ = try loadBinding(init, request.binding);
    return candidate.json(allocator, .{ .action = action, .reason = reason, .check_id = check.id, .acceptance_performed = false });
}

fn accept(init: std.process.Init, request: AcceptRequest) ![]const u8 {
    const allocator = init.arena.allocator();
    const binding = try loadBinding(init, request.binding);
    if (request.evidence.len != binding.checks.len) return error.IncompleteCheck;
    var seen = std.StringHashMap(void).init(allocator);
    for (request.evidence) |path| {
        const evidence = try evidenceCurrent(init, request.binding, path);
        const slot = try seen.getOrPut(evidence.check_id);
        if (slot.found_existing) return error.DuplicateBinding;
    }
    for (binding.checks) |check| {
        if (!seen.contains(check.id)) return error.IncompleteCheck;
    }
    // This is a current local evidence decision, not a Git/index reservation,
    // installed hook, platform qualification, or canonical publication event.
    const final = try loadBinding(init, request.binding);
    return candidate.json(allocator, .{ .accepted = true, .binding_sha256 = try bindingSha(init, final), .checks = binding.checks.len, .scope = "qualified-local-evidence", .external_write_reservation = false });
}

fn withChecksum(init: std.process.Init, evidence: Evidence) ![]const u8 {
    const allocator = init.arena.allocator();
    const bytes = try candidate.json(allocator, evidence);
    var parsed = try candidate.parse(allocator, bytes);
    try parsed.value.object.put(allocator, "sha256", .{ .string = try candidate.hash(allocator, bytes) });
    return candidate.json(allocator, parsed.value);
}

pub fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len != 3) return error.InvalidArguments;
    const value = try candidate.parse(allocator, try candidate.read(allocator, init.io, args[2]));
    if (std.mem.eql(u8, args[1], "bind")) {
        const binding = try bind(init, try exact(Request, allocator, value.value));
        // The checksum detects alteration; it is not a signature or closure proof.
        const bytes = try candidate.json(allocator, binding);
        var parsed = try candidate.parse(allocator, bytes);
        try parsed.value.object.put(allocator, "sha256", .{ .string = try candidate.hash(allocator, bytes) });
        try std.Io.File.stdout().writeStreamingAll(init.io, try candidate.json(allocator, parsed.value));
    } else if (std.mem.eql(u8, args[1], "verify")) {
        _ = try currentBinding(init, value.value);
        try std.Io.File.stdout().writeStreamingAll(init.io, try candidate.json(allocator, .{ .binding_current = true, .acceptance_performed = false }));
    } else if (std.mem.eql(u8, args[1], "python-plan")) {
        try std.Io.File.stdout().writeStreamingAll(init.io, try pythonPlan(init, try exact(PlanRequest, allocator, value.value)));
    } else if (std.mem.eql(u8, args[1], "record")) {
        try std.Io.File.stdout().writeStreamingAll(init.io, try withChecksum(init, try record(init, try exact(RecordRequest, allocator, value.value))));
    } else if (std.mem.eql(u8, args[1], "reuse")) {
        try std.Io.File.stdout().writeStreamingAll(init.io, try reuse(init, try exact(ReuseRequest, allocator, value.value)));
    } else if (std.mem.eql(u8, args[1], "accept")) {
        try std.Io.File.stdout().writeStreamingAll(init.io, try accept(init, try exact(AcceptRequest, allocator, value.value)));
    } else return error.InvalidArguments;
}

pub fn main(init: std.process.Init) void {
    run(init) catch |failure| std.process.fatal("receipt refused: {s}", .{@errorName(failure)});
}
