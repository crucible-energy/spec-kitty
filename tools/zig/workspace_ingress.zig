//! Ordinary creator ingress. Missing registrations are retained recovery custody,
//! never an authorization to prune another creator's Git metadata.
const std = @import("std");
const finish = @import("workspace_finish.zig");
const candidate = @import("validation_candidate.zig");
const c = @cImport({
    @cInclude("stdlib.h");
});

const Receipt = struct {
    source: finish.Source,
    creator: finish.CreatorBinding,
    owner: []const u8,
    purpose: []const u8,
    next_action: []const u8,
    review_event: []const u8,
};
const Request = struct {
    operation: enum { startup, completion, recovery },
    expected_revision: u64,
    receipt: Receipt,
    outcome: ?enum { succeeded, failed, cancelled } = null,
};

fn parseRequest(allocator: std.mem.Allocator, bytes: []const u8) !std.json.Parsed(Request) {
    if (bytes.len > 65536) return error.InputBoundExceeded;
    return std.json.parseFromSlice(Request, allocator, bytes, .{ .duplicate_field_behavior = .@"error", .ignore_unknown_fields = false });
}

fn record(allocator: std.mem.Allocator, root: []const u8, request: Request) !finish.State {
    // This ingress is for ordinary Git creators only. The existing managed
    // producer path retains its separate supported release operation.
    if (request.receipt.creator.kind != .ordinary_git) return error.UnsupportedCreatorKind;
    if ((request.operation == .completion) != (request.outcome != null)) return error.OutcomeRequiredOnlyForCompletion;
    const stage: @FieldType(finish.Obligation, "stage") = switch (request.operation) {
        .startup => .implement,
        .recovery => .blocked,
        .completion => switch (request.outcome.?) {
            .succeeded => .await_delivery,
            .failed => .blocked,
            .cancelled => .triage,
        },
    };
    const evidence: []const []const u8 = switch (request.operation) {
        .startup => &.{"creator-event:startup"},
        .recovery => &.{"creator-event:recovery-uncertain"},
        .completion => switch (request.outcome.?) {
            .succeeded => &.{"producer-outcome:succeeded:data-only"},
            .failed => &.{"producer-outcome:failed:data-only"},
            .cancelled => &.{"producer-outcome:cancelled:data-only"},
        },
    };
    return finish.recordCreator(allocator, root, request.expected_revision, .{
        .source = request.receipt.source,
        .creator = request.receipt.creator,
        .owner = request.receipt.owner,
        .purpose = request.receipt.purpose,
        .next_action = request.receipt.next_action,
        .review_event = request.receipt.review_event,
        .stage = stage,
        .evidence = evidence,
    });
}

pub fn main(init: std.process.Init) void {
    run(init) catch |failure| std.process.fatal("ordinary creator ingress refused: {s}", .{@errorName(failure)});
}

fn run(init: std.process.Init) !void {
    const allocator = init.arena.allocator();
    const args = try init.minimal.args.toSlice(allocator);
    if (args.len != 3) return error.InvalidArguments;
    const request = (try parseRequest(allocator, try candidate.read(allocator, init.io, args[2]))).value;
    const state = try record(allocator, args[1], request);
    try std.Io.File.stdout().writeStreamingAll(init.io, try candidate.json(allocator, .{
        .revision = state.revision,
        .obligation_id = state.events[state.events.len - 1].obligation_id,
        .cleanup_authority = false,
        .cleanup_performed = false,
    }));
}

fn exampleReceipt() Receipt {
    return .{
        .source = .{ .repository_id = 7, .repository = "crucible-energy/example", .common_dir = "/private/repo/.git", .path = "/private/lane", .head = "a" ** 40, .branch = "refs/heads/useful" },
        .creator = .{ .kind = .ordinary_git, .generation = "a" ** 32 },
        .owner = "implementation-owner",
        .purpose = "finish useful change",
        .next_action = "reproduce behavior",
        .review_event = "after focused validation",
    };
}

test "ordinary startup completion and uncertain recovery persist data without release" {
    var arena: std.heap.ArenaAllocator = .init(std.testing.allocator);
    defer arena.deinit();
    const a = arena.allocator();
    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();
    try tmp.dir.setPermissions(std.testing.io, .fromMode(0o700));
    const path = try tmp.dir.realPathFileAlloc(std.testing.io, ".", a);
    _ = try finish.initializeStore(a, path);
    const startup = try record(a, path, .{ .operation = .startup, .expected_revision = 0, .receipt = exampleReceipt() });
    try std.testing.expectEqual(.implement, startup.events[0].obligation.stage);
    var revision: u64 = 1;
    inline for (.{ .succeeded, .failed, .cancelled }) |outcome| {
        const state = try record(a, path, .{ .operation = .completion, .expected_revision = revision, .receipt = exampleReceipt(), .outcome = outcome });
        const event = state.events[state.events.len - 1];
        try std.testing.expectEqualStrings(startup.events[0].obligation_id, event.obligation_id);
        try std.testing.expectEqualStrings("implementation-owner", event.obligation.owner);
        try std.testing.expect(event.obligation.stage != .await_cleanup);
        revision += 1;
    }
    const recovered = try record(a, path, .{ .operation = .recovery, .expected_revision = revision, .receipt = exampleReceipt() });
    try std.testing.expectEqual(.blocked, recovered.events[recovered.events.len - 1].obligation.stage);
    try std.testing.expectError(error.StaleRevision, record(a, path, .{ .operation = .startup, .expected_revision = 0, .receipt = exampleReceipt() }));
}

test "ordinary ingress refuses wrong creator missing receipt and forged release fields" {
    var request = Request{ .operation = .startup, .expected_revision = 0, .receipt = exampleReceipt() };
    request.receipt.creator.kind = .managed_git;
    try std.testing.expectError(error.UnsupportedCreatorKind, record(std.testing.allocator, "/unavailable-not-opened", request));
    request.receipt.creator.kind = .ordinary_git;
    request.outcome = .succeeded;
    try std.testing.expectError(error.OutcomeRequiredOnlyForCompletion, record(std.testing.allocator, "/unavailable-not-opened", request));
    try std.testing.expectError(error.MissingField, parseRequest(std.testing.allocator, "{\"operation\":\"startup\",\"expected_revision\":0}"));
    try std.testing.expectError(error.UnknownField, parseRequest(std.testing.allocator, "{\"release_capability\":\"invented\"}"));
    try std.testing.expectError(error.DuplicateField, parseRequest(std.testing.allocator, "{\"operation\":\"startup\",\"operation\":\"recovery\"}"));
}

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
    const script = try std.mem.concat(std.testing.allocator, u8, &.{
        "import os\nif coverage_config:=os.environ.get('SPEC_KITTY_INGRESS_TEST_COVERAGE_CONFIG'):\n import atexit,coverage\n cov=coverage.Coverage(config_file=coverage_config,data_suffix=True);cov.start();atexit.register(lambda:(cov.stop(),cov.save()))\n",
        fixture,
    });
    defer std.testing.allocator.free(script);
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ python, "-B", "-c", script, mode },
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
    \\import json,pathlib,stat,subprocess,sys,tempfile
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
    \\ def snapshot():
    \\  result={}
    \\  for path in ledger.iterdir():
    \\   info=path.lstat();result[path.name]=(info.st_dev,info.st_ino,info.st_mode,info.st_nlink,path.read_bytes() if stat.S_ISREG(info.st_mode) else None)
    \\  return result
    \\ before=snapshot();mode=sys.argv[1];bases={'explicit':base,'symbolic':'main','missing':'0'*40,'tag':tag};kwargs={} if mode=='default' else {'expected_base_commit':bases[mode]}
    \\ succeeded=False;bound=False;reason='';legacy_receipt_refused=False;legacy_adoption_refused=False
    \\ try:
    \\  owner=ManagedGitCreator.create(store,repo_root=repo,path=target,branch='owned-task',repository='crucible-energy/example',repository_id=7,delivery=GitHubDelivery(timeout=1),on_complete=lambda event:None,**kwargs)
    \\  succeeded=True;wanted=caller if mode=='default' else base
    \\  bound=owner.identity.head==wanted and git('-C',str(target),'rev-parse','HEAD')==wanted
    \\  from dataclasses import replace
    \\  from specify_cli.workspace_lifecycle.state import StateError
    \\  original=owner._path.read_bytes()
    \\  try:owner.admission_receipt
    \\  except StateError:legacy_receipt_refused=True
    \\  try:owner._write(replace(owner._read(),creator_kind='ordinary_git',accountable_owner='other-owner',starting_head=base))
    \\  except StateError:legacy_adoption_refused=owner._path.read_bytes()==original
    \\ except Exception as error:reason=type(error).__name__+': '+str(error)
    \\ print(json.dumps({'succeeded':succeeded,'bound_to_selected_base':bound,'target_absent':not target.exists(),'ledger_unchanged':before==snapshot(),'validated_refusal':reason.startswith(('StateError:','GitCommandError:')),'legacy_receipt_refused':legacy_receipt_refused,'legacy_adoption_refused':legacy_adoption_refused,'reason':reason}))
;

test "creator uses exact selected parent and preserves unchanged caller HEAD default" {
    for ([_][]const u8{ "explicit", "default" }) |mode| {
        var result = try migrationProbe(creator_base_fixture, mode);
        defer result.deinit();
        const facts = result.value.object;
        try std.testing.expect(facts.get("succeeded").?.bool);
        try std.testing.expect(facts.get("bound_to_selected_base").?.bool);
        try std.testing.expect(facts.get("legacy_receipt_refused").?.bool);
        try std.testing.expect(facts.get("legacy_adoption_refused").?.bool);
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

const ordinary_binding_fixture =
    \\import json,os,pathlib,shutil,subprocess,sys,tempfile
    \\sys.path.insert(0,str(pathlib.Path.cwd()/'src'))
    \\from specify_cli.workspace_lifecycle.adapters import ManagedGitCreator,GitHubDelivery
    \\from specify_cli.workspace_lifecycle.state import StateStore
    \\with tempfile.TemporaryDirectory(prefix='ordinary-binding-owned-') as directory:
    \\ root=pathlib.Path(directory).resolve();repo=root/'repo';repo.mkdir()
    \\ def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE,text=True,timeout=10).strip()
    \\ git('init','-q','-b','main');git('config','user.name','Owned fixture');git('config','user.email','owned@example.invalid');git('config','commit.gpgsign','false');git('config','gc.auto','0');git('commit','--allow-empty','-qm','base');base=git('rev-parse','HEAD')
    \\ git('remote','add','origin','https://github.com/crucible-energy/example.git');git('symbolic-ref','refs/remotes/origin/HEAD','refs/remotes/origin/main')
    \\ ledger=root/'ledger';ledger.mkdir(mode=0o700);store=StateStore.initialize(ledger);target=root/'task';mode=sys.argv[1];seen=[];bound=False;reason='';created=False;release_refused=False;starting_preserved=False;legacy_shaped_release_refused=False;restored_release_refused=False;record_kind_change_refused=False;immutable_receipt_preserved=False
    \\ def admission(receipt):
    \\  global bound
    \\  records=list(ledger.glob('creator-*.json'));data=json.loads(records[0].read_text()) if len(records)==1 else {}
    \\  bound=(not target.exists() and not git('branch','--list','ordinary-task') and data.get('status')=='creating' and data.get('schema_version')==2 and data.get('creator_kind')=='ordinary_git' and data.get('accountable_owner')=='fixture-owner' and data.get('starting_head')==base and receipt=={'source':{'repository_id':7,'repository':'crucible-energy/example','common_dir':str(repo/'.git'),'path':str(target),'head':base,'branch':'refs/heads/ordinary-task'},'creator':{'kind':'ordinary_git','generation':data.get('identity',{}).get('workspace_generation')},'owner':'fixture-owner'})
    \\  seen.append(receipt)
    \\  if mode=='interrupted':raise RuntimeError('owned admission interrupted')
    \\  if mode=='changed-pending':
    \\   data['starting_head']='b'*40;records[0].write_text(json.dumps(data))
    \\  if mode=='occupied-target':target.mkdir()
    \\  if mode=='changed-store':
    \\   (repo/'.git').rename(root/'preserved-git');shutil.copytree(root/'preserved-git',repo/'.git')
    \\  if mode in ('bad-owner','bad-head','bad-kind'):
    \\   field,value={'bad-owner':('accountable_owner',''),'bad-head':('starting_head','not-a-commit'),'bad-kind':('creator_kind','managed_git')}[mode];data[field]=value;records[0].write_text(json.dumps(data))
    \\ kwargs={'creator_kind':'ordinary_git','accountable_owner':None if mode=='missing-owner' else 'fixture-owner','on_admitted':None if mode=='missing-callback' else admission,'expected_base_commit':None if mode=='missing-base' else base}
    \\ if mode=='unknown-kind':kwargs['creator_kind']='unknown'
    \\ if mode=='managed-with-context':kwargs['creator_kind']='managed_git'
    \\ if mode=='invalid-callback':kwargs['on_admitted']=False
    \\ if mode in ('unicode-overflow','record-overflow','unicode-valid'):kwargs['accountable_owner']='\U0001f680'*{'unicode-overflow':8192,'record-overflow':5400,'unicode-valid':1000}[mode]
    \\ try:
    \\  owner=ManagedGitCreator.create(store,repo_root=repo,path=target,branch='ordinary-task',repository='crucible-energy/example',repository_id=7,delivery=GitHubDelivery(timeout=1),on_complete=lambda event:None,**kwargs);created=True
    \\  owner.run_producer([sys.executable,'-B','-c',"import subprocess;subprocess.run(['git','commit','--allow-empty','-m','owned result'],check=True)"],timeout=5)
    \\  starting_preserved=owner.admission_receipt['source']['head']==base and owner.identity.head!=base
    \\  from dataclasses import replace
    \\  from specify_cli.workspace_lifecycle.adapters import _released
    \\  legacy_shaped_release_refused=not _released(replace(owner._read(),status='released',release_cap=owner._capability,release_id='synthetic-release',pr=9))
    \\  restored=ManagedGitCreator(store,owner.token,delivery=owner.delivery,on_complete=lambda event:None,capability=owner._capability)
    \\  try:restored.complete(pr=9)
    \\  except Exception as error:restored_release_refused='qualified core custody' in str(error)
    \\  if mode=='binding-mutations':
    \\   from specify_cli.workspace_lifecycle.state import StateError
    \\   state=owner._read();original=owner._path.read_bytes();changes=[replace(state,accountable_owner='other-owner'),replace(state,starting_head='b'*40)]
    \\   for field,value in [('repository_id',8),('repository','crucible-energy/other'),('path',str(root/'other')),('common_dir',str(root/'other/.git')),('branch','refs/heads/other'),('workspace_generation','f'*32)]:changes.append(replace(state,identity=replace(state.identity,**{field:value})))
    \\   refused=0
    \\   for change in changes:
    \\    try:owner._write(change)
    \\    except StateError:refused+=1
    \\   immutable_receipt_preserved=refused==len(changes) and owner._path.read_bytes()==original
    \\  if mode=='downgraded-registry':
    \\   data=json.loads(owner._path.read_text());data['schema_version']=1
    \\   for key in ('creator_kind','accountable_owner','starting_head'):del data[key]
    \\   owner._path.write_text(json.dumps(data))
    \\   try:owner.identity
    \\   except Exception as error:record_kind_change_refused='Original creator kind' in str(error)
    \\  try:owner.complete(pr=9)
    \\  except Exception as error:release_refused='qualified core custody' in str(error)
    \\ except Exception as error:reason=type(error).__name__+': '+str(error)
    \\ records=[json.loads(p.read_text()) for p in ledger.glob('creator-*.json')]
    \\ print(json.dumps({'created':created,'pending_receipt_bound_before_effect':bound,'callback_count':len(seen),'target_absent':not target.exists(),'records':len(records),'pending_retained':len(records)==1 and records[0].get('status')=='creating','release_refused':release_refused,'restored_release_refused':restored_release_refused,'legacy_shaped_release_refused':legacy_shaped_release_refused,'record_kind_change_refused':record_kind_change_refused,'immutable_receipt_preserved':immutable_receipt_preserved,'starting_head_preserved':starting_preserved,'foreign_target_preserved':target.is_dir() and not list(target.iterdir()),'old_store_preserved':(root/'preserved-git').is_dir(),'reason':reason}))
;

test "ordinary creator binds pending receipt before effect and cannot use legacy release" {
    var result = try migrationProbe(ordinary_binding_fixture, "normal");
    defer result.deinit();
    const facts = result.value.object;
    try std.testing.expect(facts.get("created").?.bool);
    try std.testing.expect(facts.get("pending_receipt_bound_before_effect").?.bool);
    try std.testing.expectEqual(@as(i64, 1), facts.get("callback_count").?.integer);
    try std.testing.expect(facts.get("release_refused").?.bool);
    try std.testing.expect(facts.get("starting_head_preserved").?.bool);
    try std.testing.expect(facts.get("legacy_shaped_release_refused").?.bool);
    try std.testing.expect(facts.get("restored_release_refused").?.bool);
}

test "ordinary admission failure retains pending custody while missing prerequisites cause no creation" {
    var interrupted = try migrationProbe(ordinary_binding_fixture, "interrupted");
    defer interrupted.deinit();
    try std.testing.expect(interrupted.value.object.get("pending_receipt_bound_before_effect").?.bool);
    try std.testing.expect(interrupted.value.object.get("pending_retained").?.bool);
    try std.testing.expect(interrupted.value.object.get("target_absent").?.bool);
    for ([_][]const u8{ "missing-owner", "missing-callback", "missing-base", "invalid-callback", "unknown-kind", "managed-with-context" }) |mode| {
        var result = try migrationProbe(ordinary_binding_fixture, mode);
        defer result.deinit();
        const facts = result.value.object;
        try std.testing.expect(!facts.get("created").?.bool);
        try std.testing.expect(facts.get("target_absent").?.bool);
        try std.testing.expectEqual(@as(i64, 0), facts.get("records").?.integer);
        try std.testing.expectEqual(@as(i64, 0), facts.get("callback_count").?.integer);
    }
}

test "ordinary admission refuses changed pending custody before Git effect" {
    var result = try migrationProbe(ordinary_binding_fixture, "changed-pending");
    defer result.deinit();
    const facts = result.value.object;
    try std.testing.expect(facts.get("pending_receipt_bound_before_effect").?.bool);
    try std.testing.expect(!facts.get("created").?.bool);
    try std.testing.expect(facts.get("target_absent").?.bool);
    try std.testing.expect(facts.get("pending_retained").?.bool);
}

test "ordinary admission preserves a newly occupied target and original replaced Git store" {
    var occupied = try migrationProbe(ordinary_binding_fixture, "occupied-target");
    defer occupied.deinit();
    try std.testing.expect(!occupied.value.object.get("created").?.bool);
    try std.testing.expect(occupied.value.object.get("foreign_target_preserved").?.bool);
    try std.testing.expect(occupied.value.object.get("pending_retained").?.bool);
    var store = try migrationProbe(ordinary_binding_fixture, "changed-store");
    defer store.deinit();
    try std.testing.expect(!store.value.object.get("created").?.bool);
    try std.testing.expect(store.value.object.get("target_absent").?.bool);
    try std.testing.expect(store.value.object.get("old_store_preserved").?.bool);
    try std.testing.expect(store.value.object.get("pending_retained").?.bool);
}

test "ordinary malformed pending owner starting commit or creator kind stays recoverable without effects" {
    for ([_][]const u8{ "bad-owner", "bad-head", "bad-kind" }) |mode| {
        var result = try migrationProbe(ordinary_binding_fixture, mode);
        defer result.deinit();
        const facts = result.value.object;
        try std.testing.expect(facts.get("pending_receipt_bound_before_effect").?.bool);
        try std.testing.expect(!facts.get("created").?.bool);
        try std.testing.expect(facts.get("target_absent").?.bool);
        try std.testing.expect(facts.get("pending_retained").?.bool);
    }
}

test "ordinary producer cannot acquire legacy release through registry downgrade" {
    var result = try migrationProbe(ordinary_binding_fixture, "downgraded-registry");
    defer result.deinit();
    try std.testing.expect(result.value.object.get("created").?.bool);
    try std.testing.expect(result.value.object.get("release_refused").?.bool);
    try std.testing.expect(result.value.object.get("record_kind_change_refused").?.bool);
}

test "ordinary creator cannot rewrite generation owner parent or resource identity" {
    var result = try migrationProbe(ordinary_binding_fixture, "binding-mutations");
    defer result.deinit();
    try std.testing.expect(result.value.object.get("created").?.bool);
    try std.testing.expect(result.value.object.get("immutable_receipt_preserved").?.bool);
}

test "ordinary creator rejects oversized serialized custody before durable record or Git effects" {
    for ([_][]const u8{ "unicode-overflow", "record-overflow" }) |mode| {
        var result = try migrationProbe(ordinary_binding_fixture, mode);
        defer result.deinit();
        const facts = result.value.object;
        try std.testing.expect(!facts.get("created").?.bool);
        try std.testing.expect(facts.get("target_absent").?.bool);
        try std.testing.expectEqual(@as(i64, 0), facts.get("records").?.integer);
        try std.testing.expectEqual(@as(i64, 0), facts.get("callback_count").?.integer);
    }
    var valid = try migrationProbe(ordinary_binding_fixture, "unicode-valid");
    defer valid.deinit();
    try std.testing.expect(valid.value.object.get("created").?.bool);
    try std.testing.expect(valid.value.object.get("starting_head_preserved").?.bool);
    try std.testing.expect(valid.value.object.get("release_refused").?.bool);
}
