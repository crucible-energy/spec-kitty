//! Finite foreground jobs. Admission data never grants creator release authority.
const std = @import("std");
const builtin = @import("builtin");
const process = @import("validation_process_darwin.zig");
const candidate = @import("validation_candidate.zig");
const c = @cImport({
    @cDefine("_FORTIFY_SOURCE", "0");
    @cInclude("stdlib.h");
    @cInclude("sys/stat.h");
    @cInclude("fcntl.h");
    @cInclude("unistd.h");
    @cInclude("time.h");
});

const Policy = struct {
    execution_ms: u32,
    settlement_ms: u32,
    accountable_owner: []const u8,
    purpose: []const u8,
    next_action: []const u8,
    review_event: []const u8,
    stdout_bytes: usize = 1024 * 1024,
    stderr_bytes: usize = 1024 * 1024,
    processes: u16 = 8,
    resident_bytes: u64 = 512 * 1024 * 1024,
};
const Admission = struct { policy: Policy, deadline_ns: i64, settlement_deadline_ns: i64 };
const Run = struct {
    admission: Admission,
    argv: []const []const u8,
    result_root: []const u8,
    root_device: u64,
    root_inode: u64,
    generation: []const u8,
};

fn now() !i64 {
    var value: c.struct_timespec = undefined;
    if (c.clock_gettime(c.CLOCK_MONOTONIC, &value) != 0) return error.ClockUnavailable;
    return @as(i64, @intCast(value.tv_sec)) * std.time.ns_per_s + @as(i64, @intCast(value.tv_nsec));
}

fn validate(policy: Policy) !void {
    if (builtin.os.tag != .macos and builtin.os.tag != .linux) return error.UnsupportedForegroundHost;
    if (policy.execution_ms == 0 or policy.execution_ms > 3_600_000 or policy.settlement_ms == 0 or policy.settlement_ms > 5000 or
        policy.stdout_bytes > 16 * 1024 * 1024 or policy.stderr_bytes > 16 * 1024 * 1024 or policy.processes == 0 or policy.processes > 64 or policy.resident_bytes == 0)
        return error.InvalidJobBudget;
    inline for (.{ "accountable_owner", "purpose", "next_action", "review_event" }) |field| {
        const text = @field(policy, field);
        if (std.mem.trim(u8, text, " \r\n\t").len == 0 or text.len > 8192 or std.mem.indexOfScalar(u8, text, 0) != null or !std.unicode.utf8ValidateSlice(text)) return error.AccountableJobRequired;
    }
}

fn parse(comptime T: type, allocator: std.mem.Allocator, raw: []const u8) !std.json.Parsed(T) {
    if (raw.len > 65536) return error.InputBoundExceeded;
    return std.json.parseFromSlice(T, allocator, raw, .{ .duplicate_field_behavior = .@"error", .ignore_unknown_fields = false });
}

fn openRoot(allocator: std.mem.Allocator, request: Run) !c_int {
    if (!std.fs.path.isAbsolute(request.result_root)) return error.AbsoluteResultRootRequired;
    var fd = c.open("/", c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW | c.O_CLOEXEC);
    if (fd < 0) return error.DirectoryUnavailable;
    errdefer _ = c.close(fd);
    var parts = std.mem.tokenizeScalar(u8, request.result_root, '/');
    while (parts.next()) |part| {
        if (std.mem.eql(u8, part, ".") or std.mem.eql(u8, part, "..")) return error.TraversalRefused;
        const next = c.openat(fd, try allocator.dupeZ(u8, part), c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW | c.O_CLOEXEC);
        if (next < 0) return error.UnsafeResultRoot;
        _ = c.close(fd);
        fd = next;
    }
    var info: c.struct_stat = undefined;
    if (c.fstat(fd, &info) != 0 or info.st_uid != c.getuid() or info.st_mode & 0o777 != 0o700 or
        info.st_dev != request.root_device or info.st_ino != request.root_inode) return error.ResultRootChanged;
    return fd;
}

fn createLog(allocator: std.mem.Allocator, root: c_int, generation: []const u8, suffix: []const u8) !std.Io.File {
    const name = try std.fmt.allocPrintSentinel(allocator, "foreground-{s}-{s}", .{ generation, suffix }, 0);
    const fd = c.openat(root, name, c.O_WRONLY | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW | c.O_CLOEXEC, @as(c_uint, 0o600));
    if (fd < 0) return error.ExclusiveResultRequired;
    return .{ .handle = fd, .flags = .{ .nonblocking = false } };
}

pub fn main(init: std.process.Init) void {
    run(init) catch |failure| std.process.fatal("foreground job retained: {s}", .{@errorName(failure)});
}

fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len != 3) return error.InvalidArguments;
    if (std.mem.eql(u8, args[1], "admit")) {
        const policy = (try parse(Policy, allocator, args[2])).value;
        try validate(policy);
        const deadline = try now() + @as(i64, policy.execution_ms) * std.time.ns_per_ms;
        const admission: Admission = .{ .policy = policy, .deadline_ns = deadline, .settlement_deadline_ns = deadline + @as(i64, policy.settlement_ms) * std.time.ns_per_ms };
        try std.Io.File.stdout().writeStreamingAll(init.io, try candidate.json(allocator, admission));
        return;
    }
    if (!std.mem.eql(u8, args[1], "run")) return error.UnknownOperation;
    const request = (try parse(Run, allocator, args[2])).value;
    const admission = request.admission;
    try validate(admission.policy);
    // Sample the destination clock first: conversion can only shorten the
    // original horizons, including time spent preparing logs before spawn.
    const boot_started = std.Io.Clock.boot.now(init.io).nanoseconds;
    const admitted_now = try now();
    const remaining = try std.math.sub(i64, admission.deadline_ns, admitted_now);
    const expected_settlement = try std.math.add(i64, admission.deadline_ns, @as(i64, admission.policy.settlement_ms) * std.time.ns_per_ms);
    if (remaining <= 0 or remaining > @as(i64, admission.policy.execution_ms) * std.time.ns_per_ms or
        admission.settlement_deadline_ns != expected_settlement) return error.AdmissionExpiredOrChanged;
    const execution_deadline = boot_started + remaining;
    const settlement_deadline = boot_started + @as(i96, admission.settlement_deadline_ns) - admitted_now;
    if (request.generation.len != 32) return error.InvalidGeneration;
    for (request.generation) |char| if (!std.ascii.isDigit(char) and (char < 'a' or char > 'f')) return error.InvalidGeneration;
    try process.validateSpawnInputs(request.argv, null);
    const root = try openRoot(allocator, request);
    defer _ = c.close(root);
    const stdout = try createLog(allocator, root, request.generation, "stdout.log");
    defer stdout.close(init.io);
    const stderr = try createLog(allocator, root, request.generation, "stderr.log");
    defer stderr.close(init.io);
    // Pre-create the exact result before execution; failure leaves a retained
    // empty/partial record, never a fabricated successful join.
    const receipt = try createLog(allocator, root, request.generation, "execution.json");
    defer receipt.close(init.io);
    const result = try process.runLogged(allocator, init.io, .{
        .argv = request.argv,
        .absolute_deadline_ns = execution_deadline,
        .absolute_cleanup_deadline_ns = settlement_deadline,
        .limits = .{
            .wall_ms = admission.policy.execution_ms,
            .cleanup_ms = admission.policy.settlement_ms,
            .stdout_bytes = admission.policy.stdout_bytes,
            .stderr_bytes = admission.policy.stderr_bytes,
            .processes = admission.policy.processes,
            .resident_bytes = admission.policy.resident_bytes,
        },
    }, .{ .stdout = stdout, .stderr = stderr });
    defer result.deinit(allocator);
    const completed = try now();
    // Raw output remains in its bounded logs, not duplicated into JSON or
    // interpreted as UTF-8. The receipt carries actual terminal observations.
    try receipt.writeStreamingAll(init.io, try candidate.json(allocator, .{ .admission = admission, .result = .{
        .failure = result.failure,
        .exit_code = result.exit_code,
        .leader_reaped = result.leader_reaped,
        .group_disposed = result.group_disposed,
        .terminal_group_quiescent = result.terminal_group_quiescent,
        .elapsed_ms = result.elapsed_ms,
        .max_sampled_processes = result.max_sampled_processes,
        .max_sampled_resident_bytes = result.max_sampled_resident_bytes,
        .stdout_observed_bytes = result.stdout_observed_bytes,
        .stderr_observed_bytes = result.stderr_observed_bytes,
        .ownership_scope = result.ownership_scope,
        .session_escape_containment_qualified = result.session_escape_containment_qualified,
    }, .completed_ns = completed }));
    if (c.fsync(receipt.handle) != 0 or c.fsync(stdout.handle) != 0 or c.fsync(stderr.handle) != 0) return error.ResultDurabilityUnknown;
    // This profile is the existing cooperative original POSIX group. Its
    // terminal proof is not a claim of containment for detached session escapes.
    if (result.failure != null or result.exit_code != 0 or !result.leader_reaped or !result.group_disposed or !result.terminal_group_quiescent or completed > admission.deadline_ns) return error.ProducerNotSuccessfullyJoined;
}

// Python supplies the existing creator and real disposable Git/process fixture.
// The native assertions below own the required outcomes; no model or host call.
const lifetime_fixture =
    \\import hashlib,json,os,pathlib,subprocess,sys,tempfile,time
    \\sys.path.insert(0,str(pathlib.Path.cwd()/'src'))
    \\from specify_cli.workspace_lifecycle.original_run import OriginalWorkspaceRun
    \\from specify_cli.workspace_lifecycle.adapters import GitHubDelivery
    \\from specify_cli.workspace_lifecycle.state import StateStore,StateError
    \\mode=sys.argv[1]
    \\with tempfile.TemporaryDirectory(prefix='host-owned-') as directory:
    \\ root=pathlib.Path(directory);repo=root/'repo';repo.mkdir();ledger=root/'ledger';ledger.mkdir(mode=0o700)
    \\ def git(*args,cwd=repo):
    \\  return subprocess.check_output(['git','-C',str(cwd),*args],stderr=subprocess.PIPE,text=True,timeout=5).strip()
    \\ git('init','-q','-b','main');git('config','user.name','Owned fixture');git('config','user.email','owned@example.invalid');git('config','commit.gpgsign','false');git('config','gc.auto','0')
    \\ git('remote','add','origin','https://github.com/crucible-energy/fixture.git')
    \\ (repo/'seed.md').write_text('original source\n');git('add','seed.md');git('commit','-qm','seed');base=git('rev-parse','HEAD')
    \\ store=StateStore.initialize(ledger);path=root/'lane';seen=[]
    \\ original_path=os.environ.get('PATH','');original_dyld=os.environ.get('DYLD_INSERT_LIBRARIES')
    \\ if mode=='setup':
    \\  source=root/'setup-delay.c';library=root/'setup-delay.dylib'
    \\  source.write_text(r'''
    \\#include <sys/stat.h>
    \\#include <fcntl.h>
    \\#include <unistd.h>
    \\#include <stdarg.h>
    \\#include <stdlib.h>
    \\#include <string.h>
    \\static int delayed_openat(int fd, const char *name, int flags, ...) {
    \\  mode_t mode=0; if (flags & O_CREAT) { va_list ap;va_start(ap,flags);mode=va_arg(ap,int);va_end(ap); }
    \\  int (*actual)(int,const char*,int,...)=openat;
    \\  if (strstr(name,"foreground-") && strstr(name,"-execution.json")) {
    \\    const char *marker=getenv("SPEC_KITTY_HOST_SETUP_DELAY_MARKER");
    \\    if(marker) { int f=actual(AT_FDCWD,marker,O_WRONLY|O_CREAT|O_EXCL,0600);if(f>=0){write(f,"1",1);close(f);} }
    \\    usleep(900000);
    \\  }
    \\  return actual(fd,name,flags,mode);
    \\}
    \\__attribute__((used)) static struct { const void *replacement; const void *original; }
    \\interpose __attribute__((section("__DATA,__interpose"))) = { (const void*)delayed_openat, (const void*)openat };
    \\''')
    \\  subprocess.run([os.environ['SPEC_KITTY_HOST_TEST_ZIG'],'cc','-dynamiclib',str(source),'-o',str(library)],check=True,capture_output=True,timeout=20)
    \\  os.environ['DYLD_INSERT_LIBRARIES']=str(library);os.environ['SPEC_KITTY_HOST_SETUP_DELAY_MARKER']=str(root/'setup-delay-observed')
    \\ def admitted(receipt):seen.append(not path.exists() and receipt['source']['head']==base)
    \\ args=dict(repo_root=repo,path=path,branch='topic/foreground-lifetime',repository='crucible-energy/fixture',repository_id=7,delivery=GitHubDelivery(),on_complete=lambda hint:None,expected_base_commit=base,accountable_owner='native-owned-fixture',on_admitted=admitted)
    \\ child="import pathlib,subprocess,time;time.sleep(0.4);pathlib.Path('produced.md').write_text('valuable admitted work\\n');subprocess.run(['git','add','produced.md'],check=True,timeout=3);subprocess.run(['git','commit','-qm','produced'],check=True,timeout=3)"
    \\ facts={'success':False,'legacy_refused':False,'short_allowance':0.1,'job_allowance':3.0}
    \\ try:
    \\  if mode=='legacy':
    \\   run=OriginalWorkspaceRun.create(store,**args)
    \\   assert run._creator is not None
    \\   run._creator.operation_timeout=0.1
    \\   try:run.run_producer([sys.executable,'-B','-c',child],timeout=3.0)
    \\   except StateError:facts['legacy_refused']=True
    \\  else:
    \\   native=pathlib.Path(os.environ['SPEC_KITTY_HOST_TEST_BACKEND'])
    \\   digest=hashlib.sha256(native.read_bytes()).hexdigest() if native.is_file() else '0'*64
    \\   job=OriginalWorkspaceRun.admit_foreground_job(native_executor=native,native_sha256=digest,execution_timeout=1.5 if mode in ('bookkeeping-success','bookkeeping-failure') else 0.7 if mode in ('timeout','lock','setup') else 3.0,settlement_timeout=0.1 if mode in ('lock','bookkeeping-success','bookkeeping-failure') else 1.0,accountable_owner='native-owned-fixture',purpose='prove finite foreground lifetime',next_action='independent native review',review_event='after bounded lifetime acceptance')
    \\   run=OriginalWorkspaceRun.create_for_job(job,store,**args)
    \\   # Only the producer fixture allowance shrinks; creation keeps its normal cap.
    \\   assert run._creator is not None
    \\   run._creator.operation_timeout=0.1
    \\   if mode=='forged':
    \\    original=job._admission;data=json.loads(original);data['deadline_ns']+=1000000000000
    \\    facts['admission_immutable']=job._admission==original and json.loads(job._admission)['deadline_ns']!=data['deadline_ns']
    \\    try:run.run_foreground_job([sys.executable,'-B','-c',child],data)
    \\    except StateError:facts['data_refused']=True
    \\    import copy,pickle
    \\    refused=0
    \\    for operation in (copy.copy,copy.deepcopy,pickle.dumps):
    \\     try:operation(job)
    \\     except TypeError:refused+=1
    \\    facts['copy_refused']=refused==3
    \\    try:OriginalWorkspaceRun.create_for_job(job,store,**args)
    \\    except StateError:facts['second_creation_refused']=True
    \\    try:run.run_producer([sys.executable,'-B','-c',child],timeout=3)
    \\    except StateError:facts['legacy_profile_refused']=True
    \\   if mode in ('nonzero','timeout'):
    \\    child="import pathlib,time;pathlib.Path('valuable.md').write_text('retain failed work\\n');"+('raise SystemExit(3)' if mode=='nonzero' else 'time.sleep(5)')
    \\   if mode=='leftover':
    \\    child="import pathlib,subprocess,sys,time;pathlib.Path('valuable.md').write_text('retain failed work\\n');subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(5)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(0.05)"
    \\   if mode in ('bookkeeping-success','bookkeeping-failure'):
    \\    run._creator.operation_timeout=2.0
    \\    facts['settlement_remaining']=job.remaining(settlement=True)
    \\    child="import pathlib;pathlib.Path('valuable.md').write_text('retain failed work\\n');pathlib.Path('bookkeeping-ready').touch();"+('raise SystemExit(3)' if mode=='bookkeeping-failure' else '')
    \\    if mode=='bookkeeping-success':
    \\     shimdir=root/'shim';shimdir.mkdir();shim=shimdir/'git'
    \\     shim.write_text('#!'+sys.executable+'\nimport pathlib,time,os,sys\nif pathlib.Path('+repr(str(path/'bookkeeping-ready'))+').exists():\n pathlib.Path('+repr(str(root/'bookkeeping-delay-observed'))+').touch();time.sleep(1.8)\nos.execv("/usr/bin/git",["git",*sys.argv[1:]])\n');shim.chmod(0o700)
    \\     os.environ['PATH']=str(shimdir)+':'+original_path
    \\    else:
    \\     import specify_cli.workspace_lifecycle.adapters as adapters
    \\     from kernel.owned_process import bounded_run
    \\     real_write=adapters.atomic_write;real_stop=run._creator._stop_producer
    \\     def slow_write(target,raw,**kwargs):
    \\      if b'"status":"producer_unknown"' in raw:
    \\       (root/'bookkeeping-delay-observed').touch();bounded_run([sys.executable,'-B','-c','import time;time.sleep(1.8)'],timeout=5)
    \\      return real_write(target,raw,**kwargs)
    \\     def observed_stop(process,**kwargs):
    \\      facts['stop_elapsed']=time.monotonic()-started;return real_stop(process,**kwargs)
    \\     adapters.atomic_write=slow_write;run._creator._stop_producer=observed_stop
    \\   if mode=='setup':
    \\    deadline=json.loads(job._admission)['deadline_ns']
    \\    child="import pathlib,time,json;pathlib.Path('after-expiry.json').write_text(json.dumps({'observed_ns':time.clock_gettime_ns(time.CLOCK_MONOTONIC),'deadline_ns':"+str(deadline)+"}))"
    \\   if mode=='lock':
    \\    import threading
    \\    held=threading.Event();release=threading.Event()
    \\    def holder():
    \\     with run._creator._fence():held.set();release.wait(timeout=1.2)
    \\    blocker=threading.Thread(target=holder);blocker.start();assert held.wait(timeout=1)
    \\    facts['settlement_remaining']=job.remaining(settlement=True)
    \\   started=time.monotonic()
    \\   if mode!='forged':run.run_foreground_job([sys.executable,'-B','-c',child],job)
    \\   if mode not in ('forged','leftover','lock','setup','bookkeeping-success','bookkeeping-failure'):
    \\    facts['elapsed']=time.monotonic()-started
    \\    facts['success']=(path/'produced.md').read_text()=='valuable admitted work\n'
    \\    facts['head_advanced']=git('rev-parse','HEAD',cwd=path)!=base
    \\    facts['terminal_group_quiescent']=json.loads(next(ledger.glob('foreground-*-execution.json')).read_text())['result']['terminal_group_quiescent']
    \\ except Exception as error:
    \\  facts['error_type']=type(error).__name__;facts['error']=str(error)
    \\ if mode in ('bookkeeping-success','bookkeeping-failure'):
    \\  facts['elapsed']=time.monotonic()-started;os.environ['PATH']=original_path
    \\  facts['bookkeeping_delay_seen']=(root/'bookkeeping-delay-observed').exists()
    \\  facts['useful_work_retained']=(path/'valuable.md').read_text()=='retain failed work\n'
    \\  facts['unreleased']=run._creator._read().status in ('active','producer_unknown')
    \\  if mode=='bookkeeping-failure':adapters.atomic_write=real_write
    \\  try:run.complete(pr=9)
    \\  except StateError:facts['release_refused']=True
    \\ if mode=='setup':
    \\  if original_dyld is None:os.environ.pop('DYLD_INSERT_LIBRARIES',None)
    \\  else:os.environ['DYLD_INSERT_LIBRARIES']=original_dyld
    \\  facts['setup_delay_seen']=(root/'setup-delay-observed').exists()
    \\  facts['late_marker_absent']=not (path/'after-expiry.json').exists()
    \\  if not facts['late_marker_absent']:facts['late_marker']=json.loads((path/'after-expiry.json').read_text())
    \\  try:run.complete(pr=9)
    \\  except StateError:facts['release_refused']=True
    \\ if mode=='lock':
    \\  facts['elapsed']=time.monotonic()-started;release.set();blocker.join(timeout=2)
    \\  facts['holder_joined']=not blocker.is_alive()
    \\  facts['unreleased']=run._creator._read().status=='active'
    \\  facts['no_producer_effect']=not (path/'produced.md').exists() and not list(ledger.glob('foreground-*-execution.json'))
    \\  try:run.complete(pr=9)
    \\  except StateError:facts['release_refused']=True
    \\ if mode in ('nonzero','timeout','leftover'):
    \\  facts['useful_work_retained']=(path/'valuable.md').read_text()=='retain failed work\n'
    \\  facts['durably_unknown']=run._creator._read().status=='producer_unknown'
    \\  facts['elapsed']=time.monotonic()-started
    \\  receipt=json.loads(next(ledger.glob('foreground-*-execution.json')).read_text())
    \\  facts['actual_native_terminal']=receipt['result']['leader_reaped'] and receipt['result']['group_disposed']
    \\  facts['native_failure']=receipt['result']['failure']
    \\  facts['terminal_group_quiescent']=receipt['result']['terminal_group_quiescent']
    \\  try:run.complete(pr=9)
    \\  except StateError:facts['release_refused']=True
    \\  try:run.run_foreground_job([sys.executable,'-B','-c',"raise SystemExit(0)"],job)
    \\  except StateError:facts['retry_refused']=True
    \\ facts['parent_unchanged']=git('rev-parse','HEAD')==base
    \\ facts['admission_before_creation']=seen==[True]
    \\ facts['produced_file_exists']=(path/'produced.md').exists()
    \\ print(json.dumps(facts))
;

fn probe(mode: []const u8) !std.json.Parsed(std.json.Value) {
    const raw = c.getenv("SPEC_KITTY_HOST_TEST_PYTHON") orelse return error.ExplicitFixtureInterpreterRequired;
    const python = std.mem.span(raw);
    if (!std.fs.path.isAbsolute(python)) return error.AbsoluteFixtureInterpreterRequired;
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ python, "-B", "-c", lifetime_fixture, mode },
        .stdout_limit = .limited(64 * 1024),
        .stderr_limit = .limited(64 * 1024),
        .timeout = .{ .duration = .{ .clock = .awake, .raw = .fromSeconds(45) } },
    });
    defer std.testing.allocator.free(result.stdout);
    defer std.testing.allocator.free(result.stderr);
    if (result.term != .exited or result.term.exited != 0) {
        std.debug.print("foreground fixture failed: {s}\n", .{result.stderr});
        return error.FixtureFailed;
    }
    return std.json.parseFromSlice(std.json.Value, std.testing.allocator, result.stdout, .{});
}

test "legacy producer cannot borrow the separate foreground job budget" {
    var result = try probe("legacy");
    defer result.deinit();
    const facts = result.value.object;
    if (facts.get("error")) |message| std.debug.print("legacy outcome: {s}\n", .{message.string});
    try std.testing.expect(facts.get("legacy_refused").?.bool);
    try std.testing.expect(facts.get("parent_unchanged").?.bool);
    try std.testing.expect(facts.get("admission_before_creation").?.bool);
    try std.testing.expect(!facts.get("produced_file_exists").?.bool);
}

test "actual foreground producer outlives the short operation allowance and preserves primary" {
    var result = try probe("job");
    defer result.deinit();
    const facts = result.value.object;
    if (facts.get("elapsed")) |elapsed| std.debug.print("foreground measured seconds: {d}\n", .{elapsed.float});
    if (facts.get("error")) |message| std.debug.print("foreground outcome: {s}\n", .{message.string});
    try std.testing.expect(facts.get("success").?.bool);
    try std.testing.expect(facts.get("head_advanced").?.bool);
    try std.testing.expect(facts.get("terminal_group_quiescent").?.bool);
    try std.testing.expect(facts.get("parent_unchanged").?.bool);
    try std.testing.expect(facts.get("admission_before_creation").?.bool);
    try std.testing.expect(facts.get("elapsed").?.float > facts.get("short_allowance").?.float);
    try std.testing.expect(facts.get("elapsed").?.float < facts.get("job_allowance").?.float);
}

test "failed and timed out original jobs retain useful work and refuse release or retry" {
    for ([_][]const u8{ "nonzero", "timeout" }) |mode| {
        var result = try probe(mode);
        defer result.deinit();
        const facts = result.value.object;
        std.debug.print("{s} measured seconds: {d}\n", .{ mode, facts.get("elapsed").?.float });
        inline for (.{ "useful_work_retained", "durably_unknown", "actual_native_terminal", "release_refused", "retry_refused", "parent_unchanged", "admission_before_creation" }) |key| {
            try std.testing.expect(facts.get(key).?.bool);
        }
        if (std.mem.eql(u8, mode, "timeout")) try std.testing.expectEqualStrings("wall_timeout", facts.get("native_failure").?.string);
        try std.testing.expect(facts.get("elapsed").?.float < 2.0);
    }
}

test "copied or serialized job facts cannot acquire the original creator" {
    var result = try probe("forged");
    defer result.deinit();
    const facts = result.value.object;
    inline for (.{ "admission_immutable", "data_refused", "copy_refused", "second_creation_refused", "legacy_profile_refused", "parent_unchanged", "admission_before_creation" }) |key| {
        try std.testing.expect(facts.get(key).?.bool);
    }
    try std.testing.expect(!facts.get("produced_file_exists").?.bool);
}

test "disposing a live descendant after parent exit never grants successful producer release" {
    var result = try probe("leftover");
    defer result.deinit();
    const facts = result.value.object;
    std.debug.print("live-descendant outcome retained={any} release_refused={any}\n", .{ facts.get("durably_unknown").?.bool, facts.get("release_refused") != null });
    try std.testing.expect(!facts.get("terminal_group_quiescent").?.bool);
    inline for (.{ "useful_work_retained", "actual_native_terminal", "durably_unknown", "release_refused", "retry_refused", "parent_unchanged", "admission_before_creation" }) |key| {
        try std.testing.expect(facts.get(key) != null);
        try std.testing.expect(facts.get(key).?.bool);
    }
}

test "contended creator fence cannot lend a job the store's longer timeout" {
    var result = try probe("lock");
    defer result.deinit();
    const facts = result.value.object;
    std.debug.print("fence wait seconds={d} original settlement remaining={d}\n", .{ facts.get("elapsed").?.float, facts.get("settlement_remaining").?.float });
    inline for (.{ "holder_joined", "unreleased", "no_producer_effect", "release_refused", "parent_unchanged", "admission_before_creation" }) |key| {
        try std.testing.expect(facts.get(key) != null and facts.get(key).?.bool);
    }
    try std.testing.expect(facts.get("elapsed").?.float < facts.get("settlement_remaining").?.float + 0.15);
}

fn expectBookkeepingHorizon(mode: []const u8) !void {
    var result = try probe(mode);
    defer result.deinit();
    const facts = result.value.object;
    std.debug.print("{s} elapsed={d} original remaining={d}\n", .{ mode, facts.get("elapsed").?.float, facts.get("settlement_remaining").?.float });
    inline for (.{ "bookkeeping_delay_seen", "useful_work_retained", "unreleased", "release_refused", "parent_unchanged", "admission_before_creation" }) |key| {
        try std.testing.expect(facts.get(key) != null and facts.get(key).?.bool);
    }
    try std.testing.expect(facts.get("elapsed").?.float < facts.get("settlement_remaining").?.float + 0.15);
    if (std.mem.eql(u8, mode, "bookkeeping-failure")) {
        try std.testing.expect(facts.get("stop_elapsed").?.float < facts.get("settlement_remaining").?.float + 0.15);
        try std.testing.expectEqualStrings("Owned producer did not complete successfully", facts.get("error").?.string);
    }
}

test "post-wait Git bookkeeping cannot borrow a fresh operation horizon" {
    try expectBookkeepingHorizon("bookkeeping-success");
}

test "failed persistence cannot postpone stop beyond original settlement" {
    try expectBookkeepingHorizon("bookkeeping-failure");
}

test "actual delayed native log setup cannot start a producer after execution expiry" {
    if (builtin.os.tag != .macos) return error.SkipZigTest;
    var result = try probe("setup");
    defer result.deinit();
    const facts = result.value.object;
    if (facts.get("error")) |failure| std.debug.print("native setup outcome: {s}\n", .{failure.string});
    std.debug.print("native setup delay seen={any} late marker absent={any}\n", .{ facts.get("setup_delay_seen").?.bool, facts.get("late_marker_absent").?.bool });
    inline for (.{ "setup_delay_seen", "late_marker_absent", "release_refused", "parent_unchanged", "admission_before_creation" }) |key| {
        try std.testing.expect(facts.get(key) != null and facts.get(key).?.bool);
    }
}

test "native admission refuses missing accountability and unsupported finite budgets" {
    const original: Policy = .{ .execution_ms = 3000, .settlement_ms = 1000, .accountable_owner = "fixture", .purpose = "preserve original work", .next_action = "review", .review_event = "after bounded test" };
    try validate(original);
    var changed = original;
    changed.execution_ms = 0;
    try std.testing.expectError(error.InvalidJobBudget, validate(changed));
    changed = original;
    changed.execution_ms = 3_600_001;
    try std.testing.expectError(error.InvalidJobBudget, validate(changed));
    changed = original;
    changed.settlement_ms = 5001;
    try std.testing.expectError(error.InvalidJobBudget, validate(changed));
    changed = original;
    changed.accountable_owner = " \t";
    try std.testing.expectError(error.AccountableJobRequired, validate(changed));
    changed = original;
    changed.processes = 0;
    try std.testing.expectError(error.InvalidJobBudget, validate(changed));
    changed = original;
    changed.stdout_bytes = 16 * 1024 * 1024 + 1;
    try std.testing.expectError(error.InvalidJobBudget, validate(changed));
}

const kernel_horizon_fixture =
    \\import json,math,pathlib,subprocess,sys,time
    \\sys.path.insert(0,str(pathlib.Path.cwd()/'src'))
    \\from kernel.owned_process import bounded_run,process_budget,process_deadline
    \\facts={};invalid=0
    \\for value in (math.inf,-math.inf,math.nan):
    \\ try:
    \\  with process_budget(1,cleanup_deadline=value):pass
    \\ except ValueError:invalid+=1
    \\facts['nonfinite_refused']=invalid==3
    \\with process_budget(0.3,cleanup_deadline=time.monotonic()+0.2):
    \\ outer=process_deadline()
    \\ with process_budget(5,cleanup_deadline=time.monotonic()+10):facts['nested_tightens']=process_deadline()<=outer
    \\facts['restored']=process_deadline() is None
    \\with process_budget(1,cleanup_deadline=0):
    \\ try:bounded_run([sys.executable,'-B','-c',"raise SystemExit('must not start')"],timeout=5)
    \\ except subprocess.TimeoutExpired:facts['expired_refused']=True
    \\started=time.monotonic();horizon=started+0.3
    \\with process_budget(5,cleanup_deadline=horizon):
    \\ try:bounded_run([sys.executable,'-B','-c','import time;time.sleep(5)'],timeout=5)
    \\ except subprocess.TimeoutExpired:facts['timeout_preserved']=True
    \\facts['elapsed']=time.monotonic()-started
    \\with process_budget(1):facts['legacy_success']=bounded_run([sys.executable,'-B','-c','print(17)'],text=True,timeout=1).stdout.strip()=='17'
    \\print(json.dumps(facts))
;

test "existing kernel optional original cleanup horizon tightens and retains legacy absence" {
    const raw = c.getenv("SPEC_KITTY_HOST_TEST_PYTHON") orelse return error.ExplicitFixtureInterpreterRequired;
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ std.mem.span(raw), "-B", "-c", kernel_horizon_fixture },
        .stdout_limit = .limited(8192),
        .stderr_limit = .limited(8192),
        .timeout = .{ .duration = .{ .clock = .awake, .raw = .fromSeconds(10) } },
    });
    defer std.testing.allocator.free(result.stdout);
    defer std.testing.allocator.free(result.stderr);
    if (result.term != .exited or result.term.exited != 0) {
        std.debug.print("kernel horizon fixture: {s}\n", .{result.stderr});
        return error.FixtureFailed;
    }
    var parsed = try std.json.parseFromSlice(std.json.Value, std.testing.allocator, result.stdout, .{});
    defer parsed.deinit();
    const facts = parsed.value.object;
    inline for (.{ "nonfinite_refused", "nested_tightens", "restored", "expired_refused", "timeout_preserved", "legacy_success" }) |field| {
        try std.testing.expect(facts.get(field).?.bool);
    }
    try std.testing.expect(facts.get("elapsed").?.float <= 0.4);
}
