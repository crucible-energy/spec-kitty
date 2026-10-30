//! Actual immutable planning inspection assertions; the CLI reuses canonical readers.
const std = @import("std");
const c = @cImport({
    @cInclude("stdlib.h");
});

const fixture =
    \\import hashlib,json,os,pathlib,subprocess,sys,tempfile
    \\mode=sys.argv[1];source=pathlib.Path.cwd();env=dict(os.environ);env['PYTHONPATH']=str(source/'src')
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
    \\ if mode=='ambiguous':
    \\  other=repo/'kitty-specs'/'other-planning-01M5G2NS';other.mkdir();(other/'meta.json').write_text(json.dumps({**meta,'mission_slug':other.name,'slug':other.name}))
    \\ if mode=='legacy':
    \\  other=repo/'kitty-specs'/'legacy';other.mkdir();(other/'meta.json').write_text(json.dumps({'friendly_name':'Preserved legacy work'}))
    \\ if mode=='malformed':(mission/'meta.json').write_text('{broken')
    \\ if mode=='oversized':(mission/'meta.json').write_text(json.dumps({**meta,'oversized':'x'*65537}))
    \\ if mode=='symlink':(mission/'meta.json').unlink();(mission/'meta.json').symlink_to('/unrelated-owner/metadata.json')
    \\ git('add','.');git('commit','-qm','planning');pinned=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}');git('checkout','-q','main')
    \\ (repo/'seed.md').write_text('active dirty work\n');(repo/'valuable-untracked.md').write_text('useful work\n');(repo/'staged.md').write_text('staged work\n');git('add','staged.md')
    \\ def state():return {'head':git('rev-parse','HEAD'),'refs':git('show-ref'),'index':git('ls-files','--stage'),'index_bytes':(repo/'.git/index').read_bytes().hex(),'git_config':(repo/'.git/config').read_bytes().hex(),'status':git('status','--porcelain=v1','--untracked-files=all'),'dirty':(repo/'seed.md').read_bytes().hex(),'untracked':(repo/'valuable-untracked.md').read_bytes().hex(),'config':(repo/'.kittify/config.yaml').read_bytes().hex()}
    \\ base=git('rev-parse','main');moved=root/'ref-moved'
    \\ if mode=='moving':
    \\  shimdir=root/'shim';shimdir.mkdir();shim=shimdir/'git'
    \\  shim.write_text('#!'+sys.executable+'\nimport pathlib,subprocess,os,sys\np=pathlib.Path('+repr(str(moved))+')\nif "ls-tree" in sys.argv and not p.exists():\n subprocess.run(["/usr/bin/git","-C",'+repr(str(repo))+',"update-ref","refs/heads/codex/planning",'+repr(base)+'],check=True);p.touch()\nos.execv("/usr/bin/git",["git",*sys.argv[1:]])\n');shim.chmod(0o700);env['PATH']=str(shimdir)+':'+env['PATH']
    \\ before=state();handle=identity if mode=='ambiguous' else slug;revision='does-not-exist' if mode=='badref' else 'codex/planning' if mode=='moving' else pinned;command=[sys.executable,'-B','-m','specify_cli','agent','mission','inspect','--mission',handle,'--at',revision,'--json'];result=subprocess.run(command,cwd=repo,env=env,capture_output=True,text=True,timeout=15)
    \\ expected=dict(before)
    \\ if mode=='moving':expected['refs']=before['refs'].replace(pinned+' refs/heads/codex/planning',base+' refs/heads/codex/planning')
    \\ facts={'exit':result.returncode,'diagnostic':(result.stdout+result.stderr)[-12000:],'unchanged':expected==state(),'mission_absent_from_current':not mission.exists(),'expected_id':identity,'expected_commit':pinned,'expected_tree':tree,'expected_meta_sha256':hashlib.sha256(raw).hexdigest()}
    \\ if result.returncode==0:
    \\  facts['observation']=json.loads(result.stdout)
    \\  if mode=='moving':facts['controlled_ref_move']=moved.exists() and git('rev-parse','codex/planning')==base
    \\  else:
    \\   repeated=subprocess.run(command,cwd=repo,env=env,capture_output=True,text=True,timeout=15);facts['repeat_same']=repeated.returncode==0 and json.loads(repeated.stdout)==facts['observation'] and before==state()
    \\ else:
    \\  try:facts['refusal']=json.loads(result.stdout)
    \\  except ValueError:pass
    \\ print(json.dumps(facts))
;

fn probe(mode: []const u8) !std.json.Parsed(std.json.Value) {
    const raw = c.getenv("SPEC_KITTY_HOST_TEST_PYTHON") orelse return error.ExplicitFixtureInterpreterRequired;
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ std.mem.span(raw), "-B", "-c", fixture, mode },
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
    return std.json.parseFromSlice(std.json.Value, std.testing.allocator, result.stdout, .{});
}

test "actual pinned planning query preserves dirty unrelated checkout and exact historical identity" {
    var parsed = try probe("success");
    defer parsed.deinit();
    const facts = parsed.value.object;
    std.debug.print("actual query exit={d}: {s}\n", .{ facts.get("exit").?.integer, facts.get("diagnostic").?.string });
    try std.testing.expect(facts.get("unchanged").?.bool);
    try std.testing.expect(facts.get("mission_absent_from_current").?.bool);
    try std.testing.expectEqual(@as(i64, 0), facts.get("exit").?.integer);
    const observation = facts.get("observation").?.object;
    try std.testing.expect(facts.get("repeat_same").?.bool);
    try std.testing.expect(observation.get("read_only").?.bool);
    try std.testing.expectEqualStrings(facts.get("expected_commit").?.string, observation.get("commit").?.string);
    try std.testing.expectEqualStrings(facts.get("expected_tree").?.string, observation.get("tree").?.string);
    try std.testing.expectEqualStrings(facts.get("expected_id").?.string, observation.get("mission_id").?.string);
    try std.testing.expectEqualStrings(facts.get("expected_meta_sha256").?.string, observation.get("meta_sha256").?.string);
    try std.testing.expect(!observation.get("current_readiness_qualified").?.bool);
}

test "actual immutable planning query refuses unsafe missing ambiguous and excessive inputs without mutation" {
    for ([_][]const u8{ "ambiguous", "malformed", "oversized", "symlink", "badref" }) |mode| {
        var parsed = try probe(mode);
        defer parsed.deinit();
        const facts = parsed.value.object;
        std.debug.print("{s} refusal exit={d}: {s}\n", .{ mode, facts.get("exit").?.integer, facts.get("diagnostic").?.string });
        try std.testing.expect(facts.get("unchanged").?.bool);
        try std.testing.expectEqual(@as(i64, 1), facts.get("exit").?.integer);
        try std.testing.expectEqualStrings("error", facts.get("refusal").?.object.get("result").?.string);
        const refusal = facts.get("refusal").?.object;
        if (std.mem.eql(u8, mode, "ambiguous")) try std.testing.expectEqualStrings("MISSION_AMBIGUOUS_SELECTOR", refusal.get("error_code").?.string);
        if (std.mem.eql(u8, mode, "oversized")) try std.testing.expect(std.mem.indexOf(u8, refusal.get("error").?.string, "bounded read size") != null);
        if (std.mem.eql(u8, mode, "symlink")) try std.testing.expect(std.mem.indexOf(u8, refusal.get("error").?.string, "regular blob") != null);
    }
}

test "canonical pinned identity selection retains unindexable legacy missions" {
    var parsed = try probe("legacy");
    defer parsed.deinit();
    const facts = parsed.value.object;
    if (facts.get("exit").?.integer != 0) std.debug.print("legacy index: {s}\n", .{facts.get("diagnostic").?.string});
    try std.testing.expectEqual(@as(i64, 0), facts.get("exit").?.integer);
    try std.testing.expect(facts.get("unchanged").?.bool);
    try std.testing.expect(facts.get("repeat_same").?.bool);
}

test "actual branch movement after resolution cannot change immutable query input" {
    var parsed = try probe("moving");
    defer parsed.deinit();
    const facts = parsed.value.object;
    if (facts.get("exit").?.integer != 0) std.debug.print("moving ref query: {s}\n", .{facts.get("diagnostic").?.string});
    try std.testing.expectEqual(@as(i64, 0), facts.get("exit").?.integer);
    try std.testing.expect(facts.get("controlled_ref_move").?.bool);
    try std.testing.expect(facts.get("unchanged").?.bool);
    try std.testing.expectEqualStrings(facts.get("expected_commit").?.string, facts.get("observation").?.object.get("commit").?.string);
}
