//! Actual immutable planning inspection assertions; the CLI reuses canonical readers.
const std = @import("std");
const c = @cImport({ @cInclude("stdlib.h"); });

const fixture =
    \\import hashlib,json,os,pathlib,subprocess,sys,tempfile
    \\source=pathlib.Path.cwd();env=dict(os.environ);env['PYTHONPATH']=str(source/'src')
    \\with tempfile.TemporaryDirectory(prefix='planning-inspect-owned-') as directory:
    \\ root=pathlib.Path(directory);repo=root/'repo';repo.mkdir()
    \\ def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],timeout=5,stderr=subprocess.PIPE).decode().strip()
    \\ git('init','-q','-b','main');git('config','user.name','Inspection fixture');git('config','user.email','inspection@example.invalid');git('config','commit.gpgsign','false');git('config','gc.auto','0')
    \\ (repo/'.kittify').mkdir();(repo/'.kittify/config.yaml').write_text('vcs:\n  type: git\n')
    \\ (repo/'seed.md').write_text('seed\n');git('add','.');git('commit','-qm','seed');git('checkout','-qb','codex/planning')
    \\ slug='pinned-planning-01M5G2NS';mission=repo/'kitty-specs'/slug;mission.mkdir(parents=True)
    \\ identity='01M5G2NSXWNKGCX9GJH8GM48QP'
    \\ meta={'mission_id':identity,'mission_slug':slug,'slug':slug,'mission_type':'software-dev','target_branch':'codex/planning','topology':'single_branch','flattened':False}
    \\ raw=(json.dumps(meta,sort_keys=True)+'\n').encode();(mission/'meta.json').write_bytes(raw)
    \\ (mission/'spec.md').write_text('# Preserve the pinned planning identity\n');(mission/'plan.md').write_text('# Read without claiming readiness\n');(mission/'tasks.md').write_text('# Pending useful work\n')
    \\ git('add','.');git('commit','-qm','planning');pinned=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}');git('checkout','-q','main')
    \\ (repo/'seed.md').write_text('active dirty work\n');(repo/'valuable-untracked.md').write_text('useful work\n');(repo/'staged.md').write_text('staged work\n');git('add','staged.md')
    \\ def state():return {'head':git('rev-parse','HEAD'),'refs':git('show-ref'),'index':git('ls-files','--stage'),'status':git('status','--porcelain=v1','--untracked-files=all'),'dirty':(repo/'seed.md').read_bytes().hex(),'untracked':(repo/'valuable-untracked.md').read_bytes().hex(),'config':(repo/'.kittify/config.yaml').read_bytes().hex()}
    \\ before=state();result=subprocess.run([sys.executable,'-B','-m','specify_cli','agent','mission','inspect','--mission',slug,'--at',pinned,'--json'],cwd=repo,env=env,capture_output=True,text=True,timeout=15)
    \\ facts={'exit':result.returncode,'diagnostic':(result.stdout+result.stderr)[-12000:],'unchanged':before==state(),'mission_absent_from_current':not mission.exists(),'expected_id':identity,'expected_commit':pinned,'expected_tree':tree,'expected_meta_sha256':hashlib.sha256(raw).hexdigest()}
    \\ if result.returncode==0:facts['observation']=json.loads(result.stdout)
    \\ print(json.dumps(facts))
;

test "actual pinned planning query preserves dirty unrelated checkout and exact historical identity" {
    const raw = c.getenv("SPEC_KITTY_HOST_TEST_PYTHON") orelse return error.ExplicitFixtureInterpreterRequired;
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ std.mem.span(raw), "-B", "-c", fixture },
        .stdout_limit = .limited(64 * 1024),
        .stderr_limit = .limited(64 * 1024),
        .timeout = .{ .duration = .{ .clock = .awake, .raw = .fromSeconds(30) } },
    });
    defer std.testing.allocator.free(result.stdout);
    defer std.testing.allocator.free(result.stderr);
    if (result.term != .exited or result.term.exited != 0) {
        std.debug.print("actual inspection fixture failed: {s}\n", .{result.stderr});
        return error.FixtureFailed;
    }
    var parsed = try std.json.parseFromSlice(std.json.Value, std.testing.allocator, result.stdout, .{});
    defer parsed.deinit();
    const facts = parsed.value.object;
    std.debug.print("actual query exit={d}: {s}\n", .{ facts.get("exit").?.integer, facts.get("diagnostic").?.string });
    try std.testing.expect(facts.get("unchanged").?.bool);
    try std.testing.expect(facts.get("mission_absent_from_current").?.bool);
    try std.testing.expectEqual(@as(i64, 0), facts.get("exit").?.integer);
    const observation = facts.get("observation").?.object;
    try std.testing.expect(observation.get("read_only").?.bool);
    try std.testing.expectEqualStrings(facts.get("expected_commit").?.string, observation.get("commit").?.string);
    try std.testing.expectEqualStrings(facts.get("expected_tree").?.string, observation.get("tree").?.string);
    try std.testing.expectEqualStrings(facts.get("expected_id").?.string, observation.get("mission_id").?.string);
    try std.testing.expectEqualStrings(facts.get("expected_meta_sha256").?.string, observation.get("meta_sha256").?.string);
    try std.testing.expect(!observation.get("current_readiness_qualified").?.bool);
}
