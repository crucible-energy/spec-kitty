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
    \\from specify_cli.workspace_lifecycle.adapters import GitHubDelivery,ManagedGitCreator
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
    \\   job=OriginalWorkspaceRun.admit_foreground_job(native_executor=native,native_sha256=digest,execution_timeout=3.0,settlement_timeout=1.0,accountable_owner='native-owned-fixture',purpose='prove finite foreground lifetime',next_action='independent native review',review_event='after bounded lifetime acceptance')
    \\   run=OriginalWorkspaceRun.create_for_job(job,store,**args)
    \\   # Only the producer fixture allowance shrinks; creation keeps its normal cap.
    \\   assert run._creator is not None
    \\   run._creator.operation_timeout=0.1
    \\   started=time.monotonic();run.run_foreground_job([sys.executable,'-B','-c',child],job)
    \\   facts['elapsed']=time.monotonic()-started
    \\   facts['success']=(path/'produced.md').read_text()=='valuable admitted work\n'
    \\   facts['head_advanced']=git('rev-parse','HEAD',cwd=path)!=base
    \\ except Exception as error:
    \\  facts['error_type']=type(error).__name__;facts['error']=str(error)
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
    if (facts.get("error")) |message| std.debug.print("foreground outcome: {s}\n", .{message.string});
    try std.testing.expect(facts.get("success").?.bool);
    try std.testing.expect(facts.get("head_advanced").?.bool);
    try std.testing.expect(facts.get("parent_unchanged").?.bool);
    try std.testing.expect(facts.get("admission_before_creation").?.bool);
    try std.testing.expect(facts.get("elapsed").?.float > facts.get("short_allowance").?.float);
    try std.testing.expect(facts.get("elapsed").?.float < facts.get("job_allowance").?.float);
}
