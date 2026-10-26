//! Ordinary creator ingress. Missing registrations are retained recovery custody,
//! never an authorization to prune another creator's Git metadata.
const std = @import("std");
const c = @cImport({
    @cInclude("stdlib.h");
});

// Exercise the existing Python allocator at its real public boundary. Python
// supplies only the retained migration adapter and disposable Git fixture; the
// expected safety contract is asserted independently here in Zig.
const allocation_fixture =
    \\import hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile
    \\sys.path.insert(0,str(pathlib.Path.cwd()/'src'))
    \\from specify_cli.lanes.models import ExecutionLane,LanesManifest
    \\from specify_cli.lanes.worktree_allocator import allocate_lane_worktree
    \\with tempfile.TemporaryDirectory(prefix='ingress-owned-') as directory:
    \\ root=pathlib.Path(directory); repo=root/'repo';repo.mkdir()
    \\ def git(*args):
    \\  return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE,text=True,timeout=10).strip()
    \\ def hashes(path):
    \\  return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file() and not p.is_symlink()}
    \\ git('init','-q','-b','main');git('config','user.name','Owned fixture');git('config','user.email','owned@example.invalid');git('config','commit.gpgsign','false');git('config','gc.auto','0')
    \\ (repo/'seed.md').write_text('fixture source\n');git('add','seed.md');git('commit','-qm','seed')
    \\ mission='ingress-recovery-01M5WP09'
    \\ manifest=LanesManifest(version=1,mission_slug=mission,mission_id=None,mission_branch='kitty/mission-'+mission,target_branch='main',lanes=[ExecutionLane(lane_id='lane-a',wp_ids=('WP01',),write_scope=(),predicted_surfaces=(),depends_on_lanes=(),parallel_group=0)],computed_at='2026-10-26T00:00:00Z',computed_from='owned-fixture')
    \\ target,branch=allocate_lane_worktree(repo,mission,'WP01',manifest)
    \\ sibling=root/'unrelated';git('worktree','add','-qb','unrelated-owner',str(sibling),'main')
    \\ (sibling/'valuable.md').write_text('staged unrelated evidence\n')
    \\ subprocess.run(['git','-C',str(sibling),'add','valuable.md'],check=True,timeout=10)
    \\ quarantine=root/'preserved';quarantine.mkdir();shutil.move(str(target),str(quarantine/'target'));shutil.move(str(sibling),str(quarantine/'unrelated'))
    \\ if sys.argv[1]=='released':git('worktree','remove','--force',str(target))
    \\ for p in (repo/'.git/worktrees').glob('*/gitdir'):os.utime(p,(0,0))
    \\ before=hashes(repo/'.git/worktrees');files=hashes(quarantine);branch_before=git('rev-parse','refs/heads/'+branch)
    \\ succeeded=False;message=''
    \\ try:
    \\  allocate_lane_worktree(repo,mission,'WP01',manifest);succeeded=True
    \\ except RuntimeError as error:message=str(error)
    \\ after=hashes(repo/'.git/worktrees')
    \\ result={'succeeded':succeeded,'unrelated_preserved':all(after.get(p)==h for p,h in before.items() if p.startswith('unrelated/')),'all_metadata_preserved':all(after.get(p)==h for p,h in before.items()),'quarantine_preserved':files==hashes(quarantine),'branch_preserved':branch_before==git('rev-parse','refs/heads/'+branch),'reason':message}
    \\ print(json.dumps(result))
;

fn allocationProbe(mode: []const u8) !std.json.Parsed(std.json.Value) {
    return migrationProbe(allocation_fixture, mode);
}

fn migrationProbe(fixture: []const u8, mode: []const u8) !std.json.Parsed(std.json.Value) {
    const executable = c.getenv("SPEC_KITTY_INGRESS_TEST_PYTHON") orelse return error.ExplicitFixtureInterpreterRequired;
    const python = std.mem.span(executable);
    if (!std.fs.path.isAbsolute(python)) return error.AbsoluteFixtureInterpreterRequired;
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ python, "-B", "-c", fixture, mode },
        .stdout_limit = .limited(64 * 1024),
        .stderr_limit = .limited(64 * 1024),
        .timeout = .{ .duration = .{ .clock = .awake, .raw = .fromSeconds(45) } },
    });
    defer std.testing.allocator.free(result.stdout);
    defer std.testing.allocator.free(result.stderr);
    if (result.term != .exited or result.term.exited != 0) {
        std.debug.print("allocator fixture failed: {s}\n", .{result.stderr});
        return error.FixtureFailed;
    }
    return std.json.parseFromSlice(std.json.Value, std.testing.allocator, result.stdout, .{});
}

const launch_fixture =
    \\import json,os,pathlib,sys,tempfile,threading
    \\sys.path.insert(0,str(pathlib.Path.cwd()/'src'))
    \\from specify_cli.workspace_lifecycle.state import StateStore
    \\from specify_cli.workspace_lifecycle import worker
    \\with tempfile.TemporaryDirectory(prefix='ingress-owned-') as directory:
    \\ root=pathlib.Path(directory);candidate=root/'candidate';candidate.mkdir()
    \\ ledger=(candidate if sys.argv[1]=='nested' else root)/'ledger';ledger.mkdir(mode=0o700)
    \\ store=StateStore.initialize(ledger);output=root/'child.json'
    \\ child_code='import json,os,pathlib;pathlib.Path('+repr(str(output))+').write_text(json.dumps({"cwd":os.getcwd()}))'
    \\ worker.distribution_argv=lambda *args:[sys.executable,'-B','-c',child_code]
    \\ previous=pathlib.Path.cwd();threads=set(threading.enumerate())
    \\ try:
    \\  os.chdir(candidate);worker.LifecycleService(store).launch()
    \\  for thread in set(threading.enumerate())-threads:thread.join(timeout=10)
    \\  observed=json.loads(output.read_text())
    \\ finally:os.chdir(previous)
    \\ child=pathlib.Path(observed['cwd']);caller=candidate.resolve()
    \\ print(json.dumps({'child_inside_candidate':child==caller or caller in child.parents,'owned_join_threads_alive':any(t.is_alive() for t in set(threading.enumerate())-threads),'ledger_preserved':ledger.is_dir()}))
;

test "worker child cwd cannot hold the candidate even with nested state ledger" {
    for ([_][]const u8{ "sibling", "nested" }) |mode| {
        var result = try migrationProbe(launch_fixture, mode);
        defer result.deinit();
        const facts = result.value.object;
        try std.testing.expect(!facts.get("child_inside_candidate").?.bool);
        try std.testing.expect(!facts.get("owned_join_threads_alive").?.bool);
        try std.testing.expect(facts.get("ledger_preserved").?.bool);
    }
}

test "ordinary recovery retains unknown requested and sibling registrations including staged index" {
    var result = try allocationProbe("unknown");
    defer result.deinit();
    const facts = result.value.object;
    try std.testing.expect(!facts.get("succeeded").?.bool);
    try std.testing.expect(facts.get("unrelated_preserved").?.bool);
    try std.testing.expect(facts.get("all_metadata_preserved").?.bool);
    try std.testing.expect(facts.get("quarantine_preserved").?.bool);
    try std.testing.expect(facts.get("branch_preserved").?.bool);
}

test "ordinary recovery after explicit requested registration disposition preserves unknown sibling" {
    var result = try allocationProbe("released");
    defer result.deinit();
    const facts = result.value.object;
    try std.testing.expect(facts.get("succeeded").?.bool);
    try std.testing.expect(facts.get("unrelated_preserved").?.bool);
    try std.testing.expect(facts.get("quarantine_preserved").?.bool);
    try std.testing.expect(facts.get("branch_preserved").?.bool);
}

const creator_base_fixture =
    \\import json,pathlib,subprocess,sys,tempfile
    \\sys.path.insert(0,str(pathlib.Path.cwd()/'src'))
    \\from specify_cli.workspace_lifecycle.adapters import ManagedGitCreator,GitHubDelivery
    \\from specify_cli.workspace_lifecycle.state import StateStore
    \\with tempfile.TemporaryDirectory(prefix='ingress-base-owned-') as directory:
    \\ root=pathlib.Path(directory).resolve();repo=root/'repo';repo.mkdir()
    \\ def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE,text=True,timeout=10).strip()
    \\ git('init','-q','-b','main');git('config','user.name','Owned fixture');git('config','user.email','owned@example.invalid');git('config','commit.gpgsign','false');git('config','gc.auto','0')
    \\ git('commit','--allow-empty','-qm','base');base=git('rev-parse','HEAD')
    \\ git('remote','add','origin','https://github.com/crucible-energy/example.git');git('symbolic-ref','refs/remotes/origin/HEAD','refs/remotes/origin/main')
    \\ git('commit','--allow-empty','-qm','different caller HEAD');caller=git('rev-parse','HEAD')
    \\ git('-c','tag.gpgsign=false','tag','-a','owned-tag','-m','owned annotated tag',base);tag=git('rev-parse','refs/tags/owned-tag')
    \\ ledger=root/'ledger';ledger.mkdir(mode=0o700);store=StateStore.initialize(ledger);target=root/'task'
    \\ before=set(ledger.iterdir());mode=sys.argv[1];bases={'explicit':base,'symbolic':'main','missing':'0'*40,'tag':tag};kwargs={} if mode=='default' else {'expected_base_commit':bases[mode]}
    \\ succeeded=False;bound=False;reason=''
    \\ try:
    \\  owner=ManagedGitCreator.create(store,repo_root=repo,path=target,branch='owned-task',repository='crucible-energy/example',repository_id=7,delivery=GitHubDelivery(timeout=1),on_complete=lambda event:None,**kwargs)
    \\  succeeded=True;wanted=caller if mode=='default' else base
    \\  bound=owner.identity.head==wanted and git('-C',str(target),'rev-parse','HEAD')==wanted
    \\ except Exception as error:reason=type(error).__name__+': '+str(error)
    \\ print(json.dumps({'succeeded':succeeded,'bound_to_selected_base':bound,'target_absent':not target.exists(),'ledger_unchanged':before==set(ledger.iterdir()),'validated_refusal':reason.startswith(('StateError:','GitCommandError:')),'reason':reason}))
;

test "creator uses exact selected parent and preserves unchanged caller HEAD default" {
    for ([_][]const u8{ "explicit", "default" }) |mode| {
        var result = try migrationProbe(creator_base_fixture, mode);
        defer result.deinit();
        const facts = result.value.object;
        try std.testing.expect(facts.get("succeeded").?.bool);
        try std.testing.expect(facts.get("bound_to_selected_base").?.bool);
    }
}

test "creator refuses symbolic absent and peeled tag parents before custody or worktree effects" {
    for ([_][]const u8{ "symbolic", "missing", "tag" }) |mode| {
        var result = try migrationProbe(creator_base_fixture, mode);
        defer result.deinit();
        const facts = result.value.object;
        try std.testing.expect(!facts.get("succeeded").?.bool);
        try std.testing.expect(facts.get("validated_refusal").?.bool);
        try std.testing.expect(facts.get("target_absent").?.bool);
        try std.testing.expect(facts.get("ledger_unchanged").?.bool);
    }
}
