//! Foreground lifetime acceptance. Policy implementation follows the committed RED.
const std = @import("std");
const c = @cImport({
    @cInclude("stdlib.h");
});

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
    \\   job=OriginalWorkspaceRun.admit_foreground_job(native_executor=native,native_sha256=digest,execution_timeout=0.7 if mode in ('timeout','lock') else 3.0,settlement_timeout=0.1 if mode=='lock' else 1.0,accountable_owner='native-owned-fixture',purpose='prove finite foreground lifetime',next_action='independent native review',review_event='after bounded lifetime acceptance')
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
    \\   if mode=='lock':
    \\    import threading
    \\    held=threading.Event();release=threading.Event()
    \\    def holder():
    \\     with run._creator._fence():held.set();release.wait(timeout=1.2)
    \\    blocker=threading.Thread(target=holder);blocker.start();assert held.wait(timeout=1)
    \\    facts['settlement_remaining']=job.remaining(settlement=True)
    \\   started=time.monotonic()
    \\   if mode!='forged':run.run_foreground_job([sys.executable,'-B','-c',child],job)
    \\   if mode not in ('forged','leftover','lock'):
    \\    facts['elapsed']=time.monotonic()-started
    \\    facts['success']=(path/'produced.md').read_text()=='valuable admitted work\n'
    \\    facts['head_advanced']=git('rev-parse','HEAD',cwd=path)!=base
    \\    facts['terminal_group_quiescent']=json.loads(next(ledger.glob('foreground-*-execution.json')).read_text())['result']['terminal_group_quiescent']
    \\ except Exception as error:
    \\  facts['error_type']=type(error).__name__;facts['error']=str(error)
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

