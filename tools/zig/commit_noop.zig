//! Real canonical commit bridge and hook effects; no mocked Git or model calls.
const std = @import("std");
const c = @cImport({
    @cInclude("stdlib.h");
});

const fixture =
    \\import json,os,pathlib,shlex,subprocess,sys,tempfile
    \\sys.path.insert(0,str(pathlib.Path.cwd()/'src'))
    \\from specify_cli.cli.commands.agent.mission_setup_plan import _commit_to_branch
    \\mode=sys.argv[1]
    \\with tempfile.TemporaryDirectory(prefix='canonical-noop-owned-') as directory:
    \\ root=pathlib.Path(directory);repo=root/'repo';repo.mkdir()
    \\ def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],timeout=5,stderr=subprocess.PIPE).decode().strip()
    \\ git('init','-q','-b','main');git('config','user.name','Canonical hook fixture');git('config','user.email','hook@example.invalid');git('config','commit.gpgsign','false');git('config','gc.auto','0')
    \\ (repo/'.kittify').mkdir();(repo/'.kittify/config.yaml').write_text('vcs:\n  type: git\n')
    \\ foreign=repo/'foreign.md';foreign.write_text('independent original\n');(repo/'seed.md').write_text('seed\n');git('add','.');git('commit','-qm','seed');git('checkout','-qb','feat/noop-owned')
    \\ slug='canonical-noop-01M5G2NS';mission=repo/'kitty-specs'/slug;mission.mkdir(parents=True);plan=mission/'plan.md';plan.write_text('retained original plan\n')
    \\ target='main' if mode=='protected' else 'feat/noop-other' if mode=='wrong' else 'feat/noop-owned'
    \\ meta={'mission_id':'01M5G2NSXWNKGCX9GJH8GM48QP','mission_slug':slug,'slug':slug,'mission_type':'software-dev','friendly_name':'Canonical hook fixture','created_at':'2026-10-29T00:00:00Z','target_branch':target,'topology':'single_branch','flattened':False}
    \\ (mission/'meta.json').write_text(json.dumps(meta));git('add','.');git('commit','-qm','plan')
    \\ if mode=='wrong':git('branch','feat/noop-other')
    \\ if mode in ('foreign-noop','partial','dirty','reject'):
    \\  foreign.write_text('foreign staged\n');git('add','foreign.md');foreign.write_text('foreign unstaged\n')
    \\ if mode=='partial':plan.write_text('requested staged original\n');git('add',str(plan));plan.write_text('retained original plan\n')
    \\ if mode in ('dirty','reject'):plan.write_text('genuine new plan\n')
    \\ if mode=='missing':plan.unlink()
    \\ valuable=repo/'valuable-untracked.md';valuable.write_text('preserve useful work\n')
    \\ marker=root/'hook-invocations.log';hook=repo/'.git/hooks/pre-commit';hook.write_text('#!/bin/sh\nprintf "hook\\n" >> '+shlex.quote(str(marker))+'\n'+('printf "nothing to commit\\n" >&2\nexit 1\n' if mode=='reject' else 'exit 0\n'));hook.chmod(0o700)
    \\ def state():return {'head':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),'refs':git('show-ref'),'index':git('ls-files','--stage'),'staged':git('diff','--cached','--binary'),'plan':plan.read_bytes().hex() if plan.exists() else None,'foreign':foreign.read_bytes().hex(),'foreign_patch':git('diff','--cached','--binary','--','foreign.md'),'valuable':valuable.read_bytes().hex(),'config':(repo/'.git/config').read_bytes().hex(),'kittify':(repo/'.kittify/config.yaml').read_bytes().hex()}
    \\ before=state();facts={}
    \\ try:
    \\  result=_commit_to_branch(plan,slug,'plan',repo,target,json_output=True);facts['status']=result.status;facts['diagnostic']=str(result)
    \\ except Exception as error:facts['status']='raised';facts['diagnostic']=type(error).__name__+': '+str(error)
    \\ after=state();facts.update({'mode':mode,'hook_calls':marker.read_text().count('hook\n') if marker.exists() else 0,'unchanged':before==after,'foreign_preserved':before['foreign_patch']==after['foreign_patch'] and before['foreign']==after['foreign'],'valuable_preserved':before['valuable']==after['valuable'],'head_advanced':before['head']!=after['head'],'requested_committed':git('show','HEAD:kitty-specs/'+slug+'/plan.md')=='genuine new plan' if mode=='dirty' and before['head']!=after['head'] else False})
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
        std.debug.print("actual canonical commit fixture failed: {s}\n", .{result.stderr});
        return error.FixtureFailed;
    }
    return std.json.parseFromSlice(std.json.Value, std.testing.allocator, result.stdout, .{});
}

test "canonical unchanged plan invokes no commit hook and preserves actual state" {
    for ([_][]const u8{ "noop", "foreign-noop", "partial" }) |mode| {
        var parsed = try probe(mode);
        defer parsed.deinit();
        const facts = parsed.value.object;
        std.debug.print("{s}: {s}, actual hook calls={d}, preserved={any}\n", .{ mode, facts.get("diagnostic").?.string, facts.get("hook_calls").?.integer, facts.get("unchanged").?.bool });
        try std.testing.expectEqualStrings("unchanged", facts.get("status").?.string);
        try std.testing.expect(facts.get("unchanged").?.bool);
        try std.testing.expect(facts.get("foreign_preserved").?.bool);
        try std.testing.expect(facts.get("valuable_preserved").?.bool);
        try std.testing.expectEqual(@as(i64, 0), facts.get("hook_calls").?.integer);
    }
}

test "genuine requested delta still runs mandatory hook and preserves foreign partial staging" {
    var parsed = try probe("dirty");
    defer parsed.deinit();
    const facts = parsed.value.object;
    if (!std.mem.eql(u8, facts.get("status").?.string, "committed")) std.debug.print("dirty commit: {s}\n", .{facts.get("diagnostic").?.string});
    try std.testing.expectEqualStrings("committed", facts.get("status").?.string);
    try std.testing.expectEqual(@as(i64, 1), facts.get("hook_calls").?.integer);
    try std.testing.expect(facts.get("requested_committed").?.bool);
    try std.testing.expect(facts.get("foreign_preserved").?.bool);
    try std.testing.expect(facts.get("valuable_preserved").?.bool);
}

test "canonical protection placement and missing-artifact refusals survive apparent no-op" {
    for ([_][]const u8{ "protected", "wrong", "missing" }) |mode| {
        var parsed = try probe(mode);
        defer parsed.deinit();
        const facts = parsed.value.object;
        std.debug.print("{s}: {s}\n", .{ mode, facts.get("diagnostic").?.string });
        try std.testing.expect(!std.mem.eql(u8, facts.get("status").?.string, "unchanged"));
        try std.testing.expect(!std.mem.eql(u8, facts.get("status").?.string, "committed"));
        try std.testing.expect(facts.get("unchanged").?.bool);
        try std.testing.expectEqual(@as(i64, 0), facts.get("hook_calls").?.integer);
    }
}

test "rejecting hook empty-looking output remains a real failure with staged recovery" {
    var parsed = try probe("reject");
    defer parsed.deinit();
    const facts = parsed.value.object;
    std.debug.print("rejecting hook: {s}\n", .{facts.get("diagnostic").?.string});
    try std.testing.expect(!std.mem.eql(u8, facts.get("status").?.string, "unchanged"));
    try std.testing.expect(!std.mem.eql(u8, facts.get("status").?.string, "committed"));
    try std.testing.expectEqual(@as(i64, 1), facts.get("hook_calls").?.integer);
    try std.testing.expect(facts.get("unchanged").?.bool);
    try std.testing.expect(facts.get("foreign_preserved").?.bool);
    try std.testing.expect(facts.get("valuable_preserved").?.bool);
}
