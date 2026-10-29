//! Real numbered-meta commit diagnostics: mandatory hooks and refusal are unchanged.
const std = @import("std");
const c = @cImport({
    @cInclude("stdlib.h");
});
const fixture =
    \\import io,json,os,pathlib,shlex,subprocess,sys,tempfile
    \\sys.path.insert(0,str(pathlib.Path.cwd()/'src'))
    \\from rich.console import Console
    \\from rich.traceback import Traceback
    \\from specify_cli.workspace_lifecycle.adapters import _git_env
    \\isolated=_git_env();os.environ.clear();os.environ.update(isolated)
    \\from specify_cli.consolidation.mission_number.bake import _write_mission_number_to_branch
    \\mode=sys.argv[1]
    \\with tempfile.TemporaryDirectory(prefix='numbering-diagnostic-') as directory:
    \\ root=pathlib.Path(directory);repo=root/'repo';repo.mkdir();slug='numbering-diagnostic-01M5G2NS';branch='kitty/mission-'+slug;relative='kitty-specs/'+slug+'/meta.json'
    \\ def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True,stderr=subprocess.PIPE,timeout=10).strip()
    \\ git('init','-q','-b','main');git('config','user.name','Numbering fixture');git('config','user.email','numbering@example.invalid');git('config','commit.gpgsign','false');git('config','gc.auto','0')
    \\ meta=repo/relative;meta.parent.mkdir(parents=True);meta.write_text(json.dumps({'mission_id':'01M5G2NSXWNKGCX9GJH8GM48QP','mission_slug':slug,'slug':slug,'mission_type':'software-dev','mission_number':None,'target_branch':'feat/numbering','coordination_branch':branch}));(repo/'foreign.md').write_text('foreign original\n');(repo/'.gitignore').write_text('valuable-ignored.log\n');git('add','.');git('commit','-qm','fixture initial');git('branch',branch);git('branch','feat/numbering')
    \\ (repo/'foreign.md').write_text('foreign staged\n');git('add','foreign.md');(repo/'foreign.md').write_text('foreign unstaged\n');(repo/'valuable-untracked.md').write_text('retain untracked work\n');(repo/'valuable-ignored.log').write_text('retain ignored evidence\n')
    \\ marker=root/'hook.log';hook=repo/'.git/hooks/pre-commit';hook.write_text('#!/bin/sh\nprintf "run\\n" >> '+shlex.quote(str(marker))+'\nprintf "NUMBERING_HOOK_STDOUT\\n"\n'+('printf "NUMBERING_HOOK_REJECTED\\nreason: retain α [literal]\\n" >&2\n' if mode=='reject' else '')+('exit 0\n' if mode=='success' else 'exit 1\n'));hook.chmod(0o700)
    \\ def state():return {'head':git('rev-parse','HEAD'),'refs':git('show-ref'),'index':git('ls-files','--stage'),'staged':git('diff','--cached','--binary'),'status':git('status','--porcelain=v1','--untracked-files=all'),'meta':meta.read_bytes().hex(),'foreign':(repo/'foreign.md').read_bytes().hex(),'untracked':(repo/'valuable-untracked.md').read_bytes().hex(),'ignored':(repo/'valuable-ignored.log').read_bytes().hex(),'config':(repo/'.git/config').read_bytes().hex()}
    \\ before=state();facts={'mode':mode}
    \\ try:
    \\  result=_write_mission_number_to_branch(repo,branch,slug,2,target_branch='feat/numbering');facts['result']=result;facts['exception']=None
    \\ except Exception as error:
    \\  rendered=io.StringIO();Console(file=rendered,width=1000,color_system=None,force_terminal=False).print(Traceback.from_exception(type(error),error,error.__traceback__,show_locals=False));facts.update({'exception':type(error).__name__,'returncode':getattr(error,'returncode',None),'stderr':os.fsdecode(getattr(error,'stderr',None) or b''),'stdout':os.fsdecode(getattr(error,'stdout',None) or b''),'notes':getattr(error,'__notes__',[]),'rendered':rendered.getvalue()})
    \\ after=state();facts['all_state_unchanged']=before==after;facts['primary_preserved']=all(before[k]==after[k] for k in before if k!='refs');facts['registered_worktrees']=git('worktree','list','--porcelain').count('worktree ')
    \\ if mode=='success':facts['committed_paths']=git('diff-tree','--no-commit-id','--name-only','-r',branch).splitlines();facts['committed_number']=json.loads(git('show',branch+':'+relative))['mission_number'];facts['repeat_result']=_write_mission_number_to_branch(repo,branch,slug,2,target_branch='feat/numbering')
    \\ facts['hook_calls']=marker.read_text().count('run\n') if marker.exists() else 0;print(json.dumps(facts))
;
const ambient_fixture =
    \\import json,os,pathlib,subprocess,sys,tempfile
    \\from specify_cli.workspace_lifecycle.adapters import _git_env
    \\clean=_git_env()
    \\with tempfile.TemporaryDirectory(prefix='numbering-foreign-owner-') as directory:
    \\ root=pathlib.Path(directory);outer=root/'outer';outer.mkdir()
    \\ def git(*args):return subprocess.check_output(['git','-C',str(outer),*args],env=clean,text=True,stderr=subprocess.PIPE,timeout=10).strip()
    \\ git('init','-q','-b','main');git('config','user.name','Preserved outer owner');git('config','user.email','outer@example.invalid');git('config','commit.gpgsign','false');git('config','gc.auto','0')
    \\ (outer/'foreign.md').write_text('original\n');(outer/'.gitignore').write_text('valuable-ignored.log\n');git('add','.');git('commit','-qm','outer seed')
    \\ (outer/'foreign.md').write_text('staged foreign\n');git('add','foreign.md');(outer/'foreign.md').write_text('unstaged foreign\n');(outer/'valuable-untracked.md').write_text('outer untracked evidence\n');(outer/'valuable-ignored.log').write_text('outer ignored evidence\n')
    \\ def state():return {'head':git('rev-parse','HEAD'),'refs':git('show-ref'),'config':(outer/'.git/config').read_bytes().hex(),'index':(outer/'.git/index').read_bytes().hex(),'work':(outer/'foreign.md').read_bytes().hex(),'untracked':(outer/'valuable-untracked.md').read_bytes().hex(),'ignored':(outer/'valuable-ignored.log').read_bytes().hex()}
    \\ before=state();poison={**clean,'GIT_DIR':str(outer/'.git'),'GIT_WORK_TREE':str(outer),'GIT_INDEX_FILE':str(outer/'.git/index'),'GIT_COMMON_DIR':str(outer/'.git'),'GIT_OBJECT_DIRECTORY':str(outer/'.git/objects'),'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'fixture.ambient','GIT_CONFIG_VALUE_0':'must-not-escape'}
    \\ result=subprocess.run([sys.executable,'-B','-c',sys.argv[1],'reject'],env=poison,text=True,capture_output=True,timeout=45)
    \\ facts=json.loads(result.stdout) if result.returncode==0 else {}
    \\ facts.update({'outer_preserved':before==state(),'child_exit':result.returncode,'child_stderr':result.stderr});print(json.dumps(facts))
;
fn probe(mode: []const u8) !std.json.Parsed(std.json.Value) {
    const raw = c.getenv("SPEC_KITTY_HOST_TEST_PYTHON") orelse return error.ExplicitInterpreterRequired;
    const python = std.mem.span(raw);
    const argv: []const []const u8 = if (std.mem.eql(u8, mode, "ambient")) &.{ python, "-B", "-c", ambient_fixture, fixture } else &.{ python, "-B", "-c", fixture, mode };
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{ .argv = argv, .stdout_limit = .limited(256 * 1024), .stderr_limit = .limited(64 * 1024), .timeout = .{ .duration = .{ .clock = .awake, .raw = .fromSeconds(45) } } });
    defer std.testing.allocator.free(result.stdout);
    defer std.testing.allocator.free(result.stderr);
    if (result.term != .exited or result.term.exited != 0) {
        std.debug.print("fixture failed: {s}\n", .{result.stderr});
        return error.FixtureFailed;
    }
    std.debug.print("actual numbered-meta {s}: {s}\n", .{ mode, result.stdout });
    return std.json.parseFromSlice(std.json.Value, std.testing.allocator, result.stdout, .{});
}
test "numbered-meta hook refusal exposes multiline stderr and preserves original exception and work" {
    var p = try probe("reject");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expectEqualStrings("CalledProcessError", f.get("exception").?.string);
    try std.testing.expectEqual(@as(i64, 1), f.get("returncode").?.integer);
    try std.testing.expectEqualStrings("NUMBERING_HOOK_STDOUT\nNUMBERING_HOOK_REJECTED\nreason: retain α [literal]\n", f.get("stderr").?.string);
    try std.testing.expect(f.get("all_state_unchanged").?.bool);
    try std.testing.expectEqual(@as(i64, 1), f.get("hook_calls").?.integer);
    try std.testing.expectEqual(@as(i64, 1), f.get("registered_worktrees").?.integer);
    const rendered = f.get("rendered").?.string;
    try std.testing.expect(std.mem.indexOf(u8, rendered, "NUMBERING_HOOK_REJECTED") != null);
    try std.testing.expect(std.mem.indexOf(u8, rendered, "reason: retain α [literal]") != null);
}
test "numbered-meta stdout-only refusal retains visible captured diagnostics" {
    var p = try probe("stdout");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expectEqualStrings("CalledProcessError", f.get("exception").?.string);
    try std.testing.expectEqual(@as(i64, 1), f.get("returncode").?.integer);
    try std.testing.expectEqualStrings("NUMBERING_HOOK_STDOUT\n", f.get("stderr").?.string);
    try std.testing.expectEqualStrings("", f.get("stdout").?.string);
    try std.testing.expect(f.get("all_state_unchanged").?.bool);
    try std.testing.expectEqual(@as(i64, 1), f.get("hook_calls").?.integer);
    try std.testing.expect(std.mem.indexOf(u8, f.get("rendered").?.string, "NUMBERING_HOOK_STDOUT") != null);
}
test "numbered-meta success keeps mandatory hook meta-only commit and idempotent closeout" {
    var p = try probe("success");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expect(f.get("exception").? == .null);
    try std.testing.expect(f.get("result").?.bool);
    try std.testing.expect(f.get("primary_preserved").?.bool);
    try std.testing.expectEqual(@as(i64, 2), f.get("committed_number").?.integer);
    try std.testing.expectEqual(@as(usize, 1), f.get("committed_paths").?.array.items.len);
    try std.testing.expectEqualStrings("kitty-specs/numbering-diagnostic-01M5G2NS/meta.json", f.get("committed_paths").?.array.items[0].string);
    try std.testing.expectEqual(@as(i64, 1), f.get("hook_calls").?.integer);
    try std.testing.expectEqual(@as(i64, 1), f.get("registered_worktrees").?.integer);
    try std.testing.expect(!f.get("repeat_result").?.bool);
}

test "numbered-meta fixture rejects ambient Git redirection and preserves all foreign state" {
    var p = try probe("ambient");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expect(f.get("outer_preserved").?.bool);
    try std.testing.expectEqual(@as(i64, 0), f.get("child_exit").?.integer);
    try std.testing.expectEqualStrings("CalledProcessError", f.get("exception").?.string);
    try std.testing.expectEqual(@as(i64, 1), f.get("returncode").?.integer);
    try std.testing.expect(f.get("all_state_unchanged").?.bool);
    try std.testing.expectEqual(@as(i64, 1), f.get("hook_calls").?.integer);
    try std.testing.expectEqual(@as(i64, 1), f.get("registered_worktrees").?.integer);
}
