//! Owner-bound sampling lifecycle checks; no child or service is started.
const std = @import("std");
const sampler = @import("sampler");
const owner = @import("validation_process_darwin.zig");

fn processInit(arena: *std.heap.ArenaAllocator, environment: *std.process.Environ.Map) std.process.Init {
    return .{ .minimal = undefined, .arena = arena, .gpa = arena.child_allocator, .io = std.testing.io, .environ_map = environment, .preopens = undefined };
}

fn writeFile(dir: std.Io.Dir, path: []const u8, bytes: []const u8) !void {
    var file = try dir.createFile(std.testing.io, path, .{ .permissions = .fromMode(0o600) });
    defer file.close(std.testing.io);
    try file.writeStreamingAll(std.testing.io, bytes);
}

const Fixture = struct {
    init: std.process.Init,
    workspace: std.Io.Dir,
    sample_request: []const u8,
    group_request: []const u8,
    report_request: []const u8,
    diagnostics_path: []const u8,
};

fn fixture(a: std.mem.Allocator, tmp: *std.testing.TmpDir, max_samples: u32) !Fixture {
    const workspace = try tmp.dir.createDirPathOpen(std.testing.io, "private", .{ .permissions = .fromMode(0o700) });
    const proc = try workspace.createDirPathOpen(std.testing.io, "proc", .{ .permissions = .fromMode(0o700) });
    try writeFile(proc, "meminfo", "MemTotal: 8192 kB\nMemAvailable: 4096 kB\n");
    const self = try proc.createDirPathOpen(std.testing.io, "self", .{ .permissions = .fromMode(0o700) });
    try writeFile(self, "cgroup", "0::/tenant/job\n");
    self.close(std.testing.io);
    proc.close(std.testing.io);
    const sys = try workspace.createDirPathOpen(std.testing.io, "sys", .{ .permissions = .fromMode(0o700) });
    const group = try sys.createDirPathOpen(std.testing.io, "sys/fs/cgroup/tenant/job", .{ .permissions = .fromMode(0o700) });
    try writeFile(group, "memory.peak", "42\n");
    group.close(std.testing.io);
    sys.close(std.testing.io);
    const logs = try workspace.createDirPathOpen(std.testing.io, "logs", .{ .permissions = .fromMode(0o700) });
    try writeFile(logs, "summary.md", "# Prior native summaries\n");
    logs.close(std.testing.io);
    const absolute_workspace = try std.Io.Dir.cwd().realPathFileAlloc(std.testing.io, try std.fmt.allocPrint(a, ".zig-cache/tmp/{s}/private", .{tmp.sub_path}), a);
    const proc_path = try std.fmt.allocPrint(a, "{s}/proc", .{absolute_workspace});
    const sys_path = try std.fmt.allocPrint(a, "{s}/sys", .{absolute_workspace});
    const output_path = try std.fmt.allocPrint(a, "{s}/output", .{absolute_workspace});
    const logs_path = try std.fmt.allocPrint(a, "{s}/logs", .{absolute_workspace});
    const sample_request = try std.fmt.allocPrint(a, "{s}/sample-request.json", .{absolute_workspace});
    const group_request = try std.fmt.allocPrint(a, "{s}/group-request.json", .{absolute_workspace});
    const report_request = try std.fmt.allocPrint(a, "{s}/report-request.json", .{absolute_workspace});
    const sample_bytes = try std.json.Stringify.valueAlloc(a, .{ .schema_version = 1, .destination = output_path, .proc_root = proc_path, .interval_ms = 10, .max_samples = max_samples, .wall_ms = 5000 }, .{});
    const group_bytes = try std.json.Stringify.valueAlloc(a, .{ .schema_version = 1, .proc_root = proc_path, .sys_root = sys_path, .wall_ms = 5000 }, .{});
    const report_bytes = try std.json.Stringify.valueAlloc(a, .{ .schema_version = 1, .state_path = try std.fmt.allocPrint(a, "{s}/state.json", .{output_path}), .cgroup_path = try std.fmt.allocPrint(a, "{s}/cgroup-result.json", .{logs_path}), .warn_bytes = 10, .error_bytes = 20, .wall_ms = 5000 }, .{});
    try writeFile(workspace, "sample-request.json", sample_bytes);
    try writeFile(workspace, "group-request.json", group_bytes);
    try writeFile(workspace, "report-request.json", report_bytes);
    const environment = try a.create(std.process.Environ.Map);
    environment.* = std.process.Environ.Map.init(a);
    const arena = try a.create(std.heap.ArenaAllocator);
    arena.* = .init(a);
    return .{ .init = processInit(arena, environment), .workspace = workspace, .sample_request = sample_request, .group_request = group_request, .report_request = report_request, .diagnostics_path = logs_path };
}

test "owned sampler commits its exact state and closes once" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();
    var input = try fixture(arena.allocator(), &tmp, 2);
    defer input.workspace.close(std.testing.io);
    var owned = try sampler.OwnedSampling.begin(input.init, input.sample_request, std.Io.Clock.boot.now(input.init.io).nanoseconds + 4 * std.time.ns_per_s);
    try std.testing.expectEqual(@as(u32, 10), owned.intervalMilliseconds());
    const first = try owned.take();
    const second = try owned.take();
    try std.testing.expectError(error.SamplerAttemptLimit, owned.take());
    try std.testing.expect(owned.deadline() > owned.inputs.started);
    try std.testing.expectEqual(@as(u32, 1), first.samples);
    try std.testing.expectEqual(@as(u32, 2), second.attempts);
    const committed = try owned.commitment();
    try std.testing.expectEqual(@as(usize, 64), committed.state_sha256.len);
    try std.testing.expectEqual(@as(usize, 64), committed.state_metadata_sha256.len);
    const raw = try input.workspace.readFileAlloc(input.init.io, "output/state.json", input.init.arena.allocator(), .limited(65536));
    try std.testing.expect(std.mem.indexOf(u8, raw, "\"samples\":2") != null);
    try owned.finish();
    try std.testing.expectError(error.SamplerOwnerRequired, owned.take());
    try std.testing.expectError(error.SamplerOwnerRequired, owned.commitment());
    try std.testing.expectError(error.SamplerOwnerRequired, owned.finish());
}

test "owned sampler refuses invalid lifetime and preexisting output without taking custody" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    var too_short_tmp = std.testing.tmpDir(.{});
    defer too_short_tmp.cleanup();
    var too_short = try fixture(arena.allocator(), &too_short_tmp, 1);
    defer too_short.workspace.close(std.testing.io);
    try std.testing.expectError(error.InvalidSamplerLifetime, sampler.OwnedSampling.begin(too_short.init, too_short.sample_request, std.Io.Clock.boot.now(too_short.init.io).nanoseconds + std.time.ns_per_s));

    var existing_tmp = std.testing.tmpDir(.{});
    defer existing_tmp.cleanup();
    var existing = try fixture(arena.allocator(), &existing_tmp, 2);
    defer existing.workspace.close(std.testing.io);
    _ = try existing.workspace.createDirPathStatus(existing.init.io, "output", .fromMode(0o700));
    try std.testing.expectError(error.SamplerDestinationExists, sampler.OwnedSampling.begin(existing.init, existing.sample_request, std.Io.Clock.boot.now(existing.init.io).nanoseconds + std.time.ns_per_s));
    try std.testing.expect((try existing.workspace.statFile(existing.init.io, "output", .{ .follow_symlinks = false })).kind == .directory);
}

test "owned sampler detects changed published bytes before reporting commitment" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();
    var input = try fixture(arena.allocator(), &tmp, 2);
    defer input.workspace.close(std.testing.io);
    var owned = try sampler.OwnedSampling.begin(input.init, input.sample_request, std.Io.Clock.boot.now(input.init.io).nanoseconds + 4 * std.time.ns_per_s);
    _ = try owned.take();
    try writeFile(input.workspace, "output/state.json", "{}\n");
    try std.testing.expectError(error.SamplerOutputDrift, owned.commitment());
    try std.testing.expectError(error.SamplerOutputDrift, owned.finish());
}

test "lifetime request capture rejects a report bound to another sampler output" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();
    var input = try fixture(arena.allocator(), &tmp, 2);
    defer input.workspace.close(std.testing.io);
    const wrong_report = try std.json.Stringify.valueAlloc(input.init.arena.allocator(), .{
        .schema_version = 1,
        .state_path = "/tmp/unrelated/state.json",
        .cgroup_path = try std.fmt.allocPrint(input.init.arena.allocator(), "{s}/cgroup-result.json", .{input.diagnostics_path}),
        .warn_bytes = 10,
        .error_bytes = 20,
        .wall_ms = 5000,
    }, .{});
    try writeFile(input.workspace, "mismatched-report-request.json", wrong_report);
    const report_dir = std.fs.path.dirname(input.report_request).?;
    const report_path = try std.fmt.allocPrint(input.init.arena.allocator(), "{s}/mismatched-report-request.json", .{report_dir});
    var check = try owner.CheckScope.begin(arena.allocator(), std.testing.io, .{}, 1024);
    defer check.deinit(arena.allocator());
    try std.testing.expectError(error.InvalidSamplerLifetime, sampler.LifetimeRequests.capture(input.init, input.sample_request, input.group_request, report_path, &check));
    const finished = try check.finish(arena.allocator(), input.init.io);
    finished.deinit(arena.allocator());
}

test "lifetime requests bind sample publication, cgroup result, report, and summary" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();
    var input = try fixture(arena.allocator(), &tmp, 2);
    defer input.workspace.close(std.testing.io);
    var check = try owner.CheckScope.begin(arena.allocator(), std.testing.io, .{}, 1024);
    defer check.deinit(arena.allocator());
    var requests = try sampler.LifetimeRequests.capture(input.init, input.sample_request, input.group_request, input.report_request, &check);
    defer if (requests.active) requests.finish() catch {};
    var owned = try sampler.OwnedSampling.begin(input.init, input.sample_request, check.deadline);
    const first = try owned.take();
    const second = try owned.take();
    const commitment = try owned.commitment();
    try requests.verifyCommitment(commitment, second.pid, second.samples);
    try std.testing.expectError(error.SamplerOutputDrift, requests.verifyCommitment(commitment, second.pid + 1, second.samples));
    try std.testing.expectError(error.SamplerOutputDrift, requests.verifyCommitment(commitment, second.pid, second.samples - 1));
    var wrong_digest = commitment;
    wrong_digest.state_sha256 = "0000000000000000000000000000000000000000000000000000000000000000";
    try std.testing.expectError(error.SamplerOutputDrift, requests.verifyCommitment(wrong_digest, second.pid, second.samples));
    try std.testing.expectEqual(@as(u32, 1), first.samples);
    try std.testing.expectEqual(@as(u32, 2), second.samples);

    const cgroup_result = try sampler.cgroupForLifetime(input.init, &requests, &check);
    try std.testing.expect(std.mem.indexOf(u8, cgroup_result, "\"peak_bytes\":42") != null);
    try std.testing.expectError(error.InvalidCgroupResult, requests.writeCgroupResult(input.diagnostics_path, ""));
    try std.testing.expectError(error.PrivateEvidenceRequired, requests.writeCgroupResult("/tmp/unrelated", cgroup_result));
    try requests.writeCgroupResult(input.diagnostics_path, cgroup_result);
    try std.testing.expectError(error.SamplerOutputDrift, requests.writeCgroupResult(input.diagnostics_path, cgroup_result));
    const rendered = try sampler.reportForLifetime(input.init, input.report_request, &check);
    const parsed = try std.json.parseFromSlice(std.json.Value, input.init.arena.allocator(), rendered, .{ .duplicate_field_behavior = .@"error" });
    const summary = parsed.value.object.get("summary_line").?.string;
    try std.testing.expect(std.mem.indexOf(u8, summary, "cgroup peak 0.00 GiB") != null);
    const summary_path = try std.fmt.allocPrint(input.init.arena.allocator(), "{s}/summary.md", .{input.diagnostics_path});
    try std.testing.expectError(error.InvalidSummary, sampler.appendSummary(input.init, summary_path, "bad\nsummary", check.deadline));
    try std.testing.expectError(error.InvalidSummary, sampler.appendSummary(input.init, summary_path, "", check.deadline));
    try sampler.appendSummary(input.init, summary_path, summary, check.deadline);
    const log = try input.workspace.readFileAlloc(input.init.io, "logs/summary.md", input.init.arena.allocator(), .limited(65536));
    try std.testing.expect(std.mem.indexOf(u8, log, summary) != null);
    try owned.finish();
    try requests.finish();
    try std.testing.expectError(error.InvalidCgroupResult, requests.writeCgroupResult(input.diagnostics_path, cgroup_result));
    try std.testing.expectError(error.SamplerOwnerRequired, requests.verifyCommitment(commitment, second.pid, second.samples));
    const check_result = try check.finish(arena.allocator(), input.init.io);
    check_result.deinit(arena.allocator());
}
