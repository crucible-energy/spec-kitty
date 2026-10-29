//! First genuine claim provenance; actual authored-content and negative controls.
const std = @import("std");
const c = @cImport({
    @cInclude("stdlib.h");
});
const fixture =
    \\import json,os,pathlib,subprocess,sys,tempfile,dataclasses
    \\sys.path.insert(0,str(pathlib.Path.cwd()/'src'))
    \\from specify_cli.workspace_lifecycle.adapters import _git_env
    \\isolated=_git_env();os.environ.clear();os.environ.update(isolated)
    \\from specify_cli.status import StatusEvent,Lane,LANE_HEAD_KEY,MIGRATION_ACTOR_PREFIX
    \\from specify_cli.consolidation.wp_attribution import first_governed_open_stamp
    \\from specify_cli.consolidation.reconciliation import _collect_authored,_presence_scope,_fully_canceled_lane_commits,unmet_approved_content
    \\from specify_cli.lanes.models import ExecutionLane,LanesManifest
    \\from specify_cli.lanes.compute import lane_created_branch
    \\mode=sys.argv[1];slug='claim-origin-01M6ORIG'
    \\def event(number,wp,stamp,actor='codex'):
    \\ return StatusEvent(event_id='native-'+str(number),mission_slug=slug,wp_id=wp,from_lane=Lane.PLANNED,to_lane=Lane.CLAIMED,at='2026-10-01T00:00:00Z',actor=actor,force=False,execution_mode='worktree',policy_metadata={LANE_HEAD_KEY:stamp} if stamp else None)
    \\if mode=='claims':
    \\ first='1'*40;later='2'*40
    \\ legacy=[event(1,'WP01',None),event(2,'WP01',later)]
    \\ modern=[event(1,'WP01',first),event(2,'WP01',later)]
    \\ migration=[event(0,'WP01',first,MIGRATION_ACTOR_PREFIX+'native'),event(1,'WP01',None),event(2,'WP01',later)]
    \\ multi=[event(1,'WP01',None),event(2,'WP02',later)]
    \\ before=repr([dataclasses.asdict(e) for e in legacy+modern+migration+multi])
    \\ facts={'legacy':first_governed_open_stamp(legacy,frozenset({'WP01'})),'modern':first_governed_open_stamp(modern,frozenset({'WP01'})),'migration':first_governed_open_stamp(migration,frozenset({'WP01'})),'multi':first_governed_open_stamp(multi,frozenset({'WP01','WP02'})),'never':first_governed_open_stamp([],frozenset({'WP01'}))}
    \\ facts['events_preserved']=before==repr([dataclasses.asdict(e) for e in legacy+modern+migration+multi]);print(json.dumps(facts))
    \\else:
    \\ with tempfile.TemporaryDirectory(prefix='claim-origin-') as directory:
    \\  repo=pathlib.Path(directory)/'repo';repo.mkdir()
    \\  def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True,stderr=subprocess.PIPE,timeout=10).strip()
    \\  def commit(path,body):
    \\   (repo/path).write_text(body);git('add',path);git('commit','-qm',path);return git('rev-parse','HEAD')
    \\  git('init','-q','-b','main');git('config','user.name','Origin fixture');git('config','user.email','origin@example.invalid');git('config','commit.gpgsign','false');git('config','gc.auto','0');base=commit('README.md','base\n')
    \\  manifest=LanesManifest(version=1,mission_slug=slug,mission_id=None,mission_branch='kitty/mission-'+slug,target_branch='main',lanes=[ExecutionLane('lane-a',('WP01',),(),(),(),0),ExecutionLane('lane-b',('WP02',),(),(),('lane-a',),1)],computed_at='2026-10-01T00:00:00Z',computed_from='native fixture')
    \\  a=lane_created_branch(manifest,'lane-a');b=lane_created_branch(manifest,'lane-b');git('checkout','-qb',a,base);old=commit('stale.txt','old dependency\n');oldblob=git('rev-parse',old+':stale.txt');git('checkout','-qb',b,old);early=commit('early.txt','reviewed early own work\n');tip=commit('useful.txt','reviewed later own work\n')
    \\  if mode in ('rewritten','legacy_rewritten','legacy_rewritten_merged'):
    \\   git('checkout','main');git('branch','-f',a,base);git('checkout',a);commit('fresh.txt','reapproved dependency\n')
    \\  if mode=='legacy_rewritten_merged':git('checkout',b);git('merge','--no-ff','-m','integrate current dependency',a)
    \\  legacy=mode in ('legacy','legacy_rewritten','legacy_rewritten_merged','gate_legacy','gate_post_fence');events=[event(1,'WP01',old if mode=='independent' else base),event(2,'WP02',None if legacy else old),event(3,'WP02',old if mode=='gate_post_fence' else early)]
    \\  work={'WP01':{'lane':'canceled' if mode=='canceled' else 'approved'},'WP02':{'lane':'approved'}};excluded=frozenset({'WP01'}) if mode=='canceled' else frozenset()
    \\  canceled=_fully_canceled_lane_commits(repo,manifest,excluded,base,base);presence=_presence_scope(repo,manifest,excluded,base=base,coord_base_ref=base,events=events)
    \\  claim=_collect_authored(repo,manifest,work,base,canceled_lane_commits=canceled,presence=presence)
    \\  if mode.startswith('gate_'):
    \\   import io,types,typer
    \\   from rich.console import Console
    \\   from specify_cli.consolidation import phase_gate
    \\   from specify_cli.consolidation.reconciliation import ApprovedWpCommitSet
    \\   from specify_cli.consolidation.config import MergeStrategy
    \\   from specify_cli.consolidation.state import ConsolidationState
    \\   feature=repo/'fixture-mission';feature.mkdir();event_path=feature/'status.events.jsonl';event_path.write_text(''.join(json.dumps(dataclasses.asdict(e))+'\n' for e in events));event_bytes=event_path.read_bytes()
    \\   git('branch','-f','main',tip);refs=git('show-ref');capture=io.StringIO();phase_gate.console=Console(file=capture,color_system=None,width=240)
    \\   approved=ApprovedWpCommitSet(approved={'WP01':frozenset({old}),'WP02':frozenset({tip})},manifest_wp_ids=frozenset({'WP01','WP02'}),excluded_window_base=base,enforce_closed_world=True,authored_shas=claim.shas,authored_patch_ids=claim.patch_ids,authored_blobs=claim.blobs,authored_deletions=claim.deletions,approved_lane_content=claim.lane_content,mission_slug=slug)
    \\   run=types.SimpleNamespace(is_resume=False,main_repo=repo,feature_dir=feature,lanes_manifest=manifest,approved_wp_set=approved,strategy=MergeStrategy.MERGE,validated_lane_tips={},bound_anchor_shas=(),target_expected_old_sha=base,state=ConsolidationState(mission_id=slug,mission_slug=slug,target_branch='main',wp_order=['WP01','WP02']),checkpoint=None)
    \\   code=0
    \\   try:phase_gate._phase_reconcile_before_teardown(run)
    \\   except typer.Exit as exc:code=exc.exit_code
    \\   print(json.dumps({'mode':mode,'gate_code':code,'gate_status':run.reconciliation_result.status.value,'guidance':capture.getvalue(),'refs_preserved':refs==git('show-ref'),'events_preserved':event_bytes==event_path.read_bytes(),'old':old,'early':early}));sys.exit(0)
    \\  def state(path):
    \\   result=subprocess.run(['git','-C',str(repo),'rev-parse','--verify','main:'+path],capture_output=True,text=True,timeout=10);return result.stdout.strip() if result.returncode==0 else None
    \\  missing=unmet_approved_content(claim.lane_content,target_state=state,base_state=state)
    \\  print(json.dumps({'mode':mode,'stale_claimed':('stale.txt',oldblob) in claim.blobs,'early_claimed':any(path=='early.txt' for path,blob in claim.blobs),'useful_claimed':any(path=='useful.txt' for path,blob in claim.blobs),'canceled_detected':old in canceled,'missing_approved_refused':bool(missing),'selected_base':presence.lane_bases.get('lane-b'),'old':old,'registered_worktrees':git('worktree','list','--porcelain').count('worktree ')}))
;
fn probe(mode: []const u8) !std.json.Parsed(std.json.Value) {
    const raw = c.getenv("SPEC_KITTY_HOST_TEST_PYTHON") orelse return error.ExplicitInterpreterRequired;
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{ .argv = &.{ std.mem.span(raw), "-B", "-c", fixture, mode }, .stdout_limit = .limited(256 * 1024), .stderr_limit = .limited(64 * 1024), .timeout = .{ .duration = .{ .clock = .awake, .raw = .fromSeconds(45) } } });
    defer std.testing.allocator.free(result.stdout);
    defer std.testing.allocator.free(result.stderr);
    if (result.term != .exited or result.term.exited != 0) {
        std.debug.print("fixture failed: {s}\n", .{result.stderr});
        return error.FixtureFailed;
    }
    std.debug.print("actual claim origin {s}: {s}\n", .{ mode, result.stdout });
    return std.json.parseFromSlice(std.json.Value, std.testing.allocator, result.stdout, .{});
}
test "legacy first-known fence is retained without rewriting unknown original evidence" {
    var p = try probe("claims");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expectEqualStrings("2222222222222222222222222222222222222222", f.get("legacy").?.string);
    try std.testing.expect(f.get("events_preserved").?.bool);
}
test "modern fence and migration filtering preserve conservative multi-WP observations" {
    var p = try probe("claims");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expectEqualStrings("1111111111111111111111111111111111111111", f.get("modern").?.string);
    try std.testing.expectEqualStrings("2222222222222222222222222222222222222222", f.get("migration").?.string);
    try std.testing.expectEqualStrings("2222222222222222222222222222222222222222", f.get("multi").?.string);
    try std.testing.expect(f.get("never").? == .null);
    try std.testing.expect(f.get("events_preserved").?.bool);
}
test "rewritten reapproved dependency cannot contribute stale inherited authorship" {
    var p = try probe("rewritten");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expect(!f.get("stale_claimed").?.bool);
    try std.testing.expect(f.get("useful_claimed").?.bool);
    try std.testing.expect(f.get("missing_approved_refused").?.bool);
    try std.testing.expectEqual(@as(i64, 1), f.get("registered_worktrees").?.integer);
}
test "legacy conservative fence withholds unresolved early work while retaining required later content" {
    var p = try probe("legacy");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expect(f.get("selected_base").? == .string);
    try std.testing.expect(!f.get("early_claimed").?.bool);
    try std.testing.expect(f.get("useful_claimed").?.bool);
    try std.testing.expect(f.get("missing_approved_refused").?.bool);
}
test "canceled dependency remains excluded while approved own work stays required" {
    var p = try probe("canceled");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expect(f.get("canceled_detected").?.bool);
    try std.testing.expect(!f.get("stale_claimed").?.bool);
    try std.testing.expect(f.get("early_claimed").?.bool);
    try std.testing.expect(f.get("useful_claimed").?.bool);
    try std.testing.expect(f.get("missing_approved_refused").?.bool);
}

test "independent lane retains its own authored content even when its first stamp is at its tip" {
    var p = try probe("independent");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expect(f.get("stale_claimed").?.bool);
    try std.testing.expect(f.get("early_claimed").?.bool);
    try std.testing.expect(f.get("useful_claimed").?.bool);
    try std.testing.expect(f.get("missing_approved_refused").?.bool);
}

test "legacy missing birth must not admit a rewritten dependency's rejected old content" {
    var p = try probe("legacy_rewritten");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expect(!f.get("stale_claimed").?.bool);
    try std.testing.expect(f.get("useful_claimed").?.bool);
    try std.testing.expect(f.get("missing_approved_refused").?.bool);
}
test "merging the current dependency does not retrospectively authorize its rejected inherited content" {
    var p = try probe("legacy_rewritten_merged");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expect(!f.get("stale_claimed").?.bool);
    try std.testing.expect(f.get("useful_claimed").?.bool);
    try std.testing.expect(f.get("missing_approved_refused").?.bool);
}

test "actual gate retains unknown-origin failure and names exact recoverable evidence" {
    var p = try probe("gate_legacy");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expectEqual(@as(i64, 1), f.get("gate_code").?.integer);
    try std.testing.expect(f.get("refs_preserved").?.bool and f.get("events_preserved").?.bool);
    const guidance = f.get("guidance").?.string;
    try std.testing.expect(std.mem.indexOf(u8, guidance, "Attribution recovery context: lane lane-b (WP02), first genuine event native-2") != null);
    try std.testing.expect(std.mem.indexOf(u8, guidance, f.get("early").?.string) != null);
    try std.testing.expect(std.mem.indexOf(u8, guidance, "Do not rewrite historical events") != null);
}
test "actual gate permits safe post-fence content despite unknown original creation" {
    var p = try probe("gate_post_fence");
    defer p.deinit();
    const f = p.value.object;
    try std.testing.expectEqual(@as(i64, 0), f.get("gate_code").?.integer);
    try std.testing.expect(f.get("refs_preserved").?.bool and f.get("events_preserved").?.bool);
    try std.testing.expect(std.mem.indexOf(u8, f.get("guidance").?.string, "Attribution recovery context") == null);
}
