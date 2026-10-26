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
    const executable = c.getenv("SPEC_KITTY_INGRESS_TEST_PYTHON") orelse return error.ExplicitFixtureInterpreterRequired;
    const python = std.mem.span(executable);
    if (!std.fs.path.isAbsolute(python)) return error.AbsoluteFixtureInterpreterRequired;
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ python, "-B", "-c", allocation_fixture, mode },
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
