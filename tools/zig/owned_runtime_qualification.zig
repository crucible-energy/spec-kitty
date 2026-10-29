//! Actual installed-runtime custody controls; no simulated policy engine.
const std = @import("std");
const c = @cImport({
    @cInclude("stdlib.h");
});
const fixture =
    \\import hashlib,json,os,pathlib,subprocess,sys,tempfile
    \\for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_CEILING_DIRECTORIES','GIT_DISCOVERY_ACROSS_FILESYSTEM'):
    \\ assert key not in os.environ,'Inherited Git override refused: '+key
    \\mode=sys.argv[1]
    \\with tempfile.TemporaryDirectory(prefix='owned-runtime-custody-') as temporary:
    \\ root=pathlib.Path(temporary);home=root/'protected-home';private=root/'operator';repo=root/'repo'
    \\ for path in (home,private,repo):path.mkdir(mode=0o700)
    \\ for relative in ('.claude/commands/keep.md','.agents/skills/keep/SKILL.md'):
    \\  path=home/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Valuable protected native-agent state.\n')
    \\ before={str(p.relative_to(home)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode,p.stat().st_ino,p.stat().st_mtime_ns) for p in home.rglob('*') if p.is_file()}
    \\ env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_CONFIG','UV_','PIP_')) and k not in ('PYTHONPATH','PYTHONHOME','SPEC_KITTY_PACKS_ROOT','SPECIFY_REPO_ROOT','SPEC_KITTY_REPO_ROOT','SPEC_KITTY_TEMPLATE_ROOT','FORCE_COLOR')}
    \\ env.update(HOME=str(home),SPEC_KITTY_HOME=str(private),SPEC_KITTY_ASSET_SCOPE='consumer',XDG_CONFIG_HOME=str(private/'config'),XDG_CACHE_HOME=str(private/'cache'),XDG_STATE_HOME=str(private/'state'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0',PYTHONDONTWRITEBYTECODE='1',NO_COLOR='1',SPEC_KITTY_NO_UPGRADE_CHECK='1')
    \\ os.environ.clear();os.environ.update(env)
    \\ from specify_cli.runtime.agent_commands import get_global_command_dir
    \\ from specify_cli.skills.paths import get_primary_global_skill_root
    \\ import specify_cli
    \\ command=get_global_command_dir('claude');skill=get_primary_global_skill_root('codex')
    \\ facts={'mode':mode,'product_origin':specify_cli.__file__,'command':str(command),'skill':str(skill),'private_agent_root':str(private/'agent-assets'),'commands_private':command.is_relative_to(private/'agent-assets'),'skills_private':skill is not None and skill.is_relative_to(private/'agent-assets')}
    \\ if mode=='cache':
    \\  from types import SimpleNamespace
    \\  from unittest.mock import patch
    \\  from specify_cli.session_presence import upgrade_check
    \\  facts['cache_private']=upgrade_check.CACHE_PATH==private/'last-cli-check.json'
    \\  os.environ.pop('SPEC_KITTY_NO_UPGRADE_CHECK',None)
    \\  provider=SimpleNamespace(get_latest=lambda package,prerelease=False:SimpleNamespace(version='4.0.0rc7'))
    \\  with patch('specify_cli.distribution.upgrade_provider.resolve_upgrade_provider',return_value=provider):upgrade_check.refresh_cache_once()
    \\  facts['actual_foreground_refresh']=json.loads(upgrade_check.CACHE_PATH.read_text())['latest_version']=='4.0.0rc7'
    \\  ordinary=dict(os.environ);ordinary.pop('SPEC_KITTY_HOME',None);ordinary['SPEC_KITTY_ASSET_SCOPE']='user'
    \\  default=subprocess.run([sys.executable,'-I','-B','-c','from specify_cli.session_presence.upgrade_check import CACHE_PATH;print(CACHE_PATH)'],env=ordinary,capture_output=True,text=True,check=True,timeout=10)
    \\  facts['default_user_cache_native']=default.stdout.strip()==str(home/'.kittify/last-cli-check.json')
    \\ if mode=='startup':
    \\  for args in (['/usr/bin/git','init','-q','-b','qualification',str(repo)],['/usr/bin/git','-C',str(repo),'config','user.name','Custody fixture'],['/usr/bin/git','-C',str(repo),'config','user.email','fixture@example.invalid']):subprocess.run(args,env=env,capture_output=True,check=True,timeout=10)
    \\  result=subprocess.run([str(pathlib.Path(sys.prefix)/'bin/spec-kitty'),'init','--ai','codex','--non-interactive'],cwd=repo,env=env,capture_output=True,text=True,timeout=65)
    \\  facts['startup_exit']=result.returncode;facts['startup_stderr_tail']=result.stderr[-1600:]
    \\ after={str(p.relative_to(home)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode,p.stat().st_ino,p.stat().st_mtime_ns) for p in home.rglob('*') if p.is_file()}
    \\ facts['protected_native_state_exact']=before==after;facts['protected_added_paths']=sorted(set(after)-set(before));print(json.dumps(facts))
;
const owned_fixture =
    \\import hashlib,json,os,pathlib,subprocess,sys
    \\for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_CEILING_DIRECTORIES','GIT_DISCOVERY_ACROSS_FILESYSTEM'):
    \\ assert key not in os.environ,'Inherited Git override refused: '+key
    \\P=pathlib.Path(os.environ['OWNED_RUNTIME_FIXTURE_ROOT']);P.mkdir(mode=0o700)
    \\H=P/'protected-home';H.mkdir(mode=0o700);V=H/'.agents/skills/valuable/SKILL.md';V.parent.mkdir(parents=True);V.write_text('Protected native state must survive.\n')
    \\private=P/'operator';private.mkdir(mode=0o700)
    \\E={k:v for k,v in os.environ.items() if not k.startswith(('GIT_CONFIG','UV_','PIP_')) and k not in ('PYTHONPATH','PYTHONHOME','SPEC_KITTY_PACKS_ROOT','SPECIFY_REPO_ROOT','SPEC_KITTY_REPO_ROOT','SPEC_KITTY_TEMPLATE_ROOT','FORCE_COLOR')}
    \\E.update(HOME=str(H),SPEC_KITTY_HOME=str(private),SPEC_KITTY_ASSET_SCOPE='consumer',XDG_CONFIG_HOME=str(private/'config'),XDG_CACHE_HOME=str(private/'cache'),XDG_STATE_HOME=str(private/'state'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0',PYTHONDONTWRITEBYTECODE='1',NO_COLOR='1',SPEC_KITTY_NO_UPGRADE_CHECK='1')
    \\os.environ.clear();os.environ.update(E)
    \\GIT='/usr/bin/git';RP=sys.executable;SDK=str(pathlib.Path(sys.prefix)/'bin/spec-kitty')
    \\h=lambda raw:hashlib.sha256(raw).hexdigest()
    \\def home_snapshot():return {str(x.relative_to(H)):(h(x.read_bytes()),x.stat().st_mode,x.stat().st_ino,x.stat().st_mtime_ns) for x in H.rglob('*') if x.is_file()}
    \\protected_home=home_snapshot()
    \\def retain(name,data):(P/name).write_bytes(data)
    \\def js(name,data):retain(name,(json.dumps(data,indent=2)+'\n').encode())
    \\sequence=0
    \\def run(args,cwd=P,ok=True,limit=30):
    \\ global sequence
    \\ sequence+=1;r=subprocess.run([str(x) for x in args],cwd=cwd,env=E,capture_output=True,timeout=limit)
    \\ retain(f'command-{sequence:03d}.log',r.stdout+b'\nSTDERR\n'+r.stderr)
    \\ assert not ok or r.returncode==0,(sequence,r.returncode,r.stdout[-2000:],r.stderr[-2000:])
    \\ return r
    \\def git(root,*args):return run([GIT,'-C',root,*args]).stdout
    \\F=P/'fixture-primary';F.mkdir(mode=0o700)
    \\run([GIT,'init','--initial-branch=codex/runtime-qualification-bootstrap',F])
    \\git(F,'config','user.name','Phoenix disposable qualification');git(F,'config','user.email','fixture@example.invalid');git(F,'config','gc.auto','0')
    \\run([SDK,'init','--ai','codex','--non-interactive'],cwd=F)
    \\git(F,'add','.');git(F,'commit','-m','Seed disposable runtime qualification');git(F,'branch','-m','main')
    \\O=P/'fixture-owned';git(F,'worktree','add','-b','codex/runtime-qualification-owner',O,'main')
    \\protected={'head':git(F,'rev-parse','HEAD').decode(),'status':git(F,'--no-optional-locks','status','--porcelain').decode(),'index_sha256':h((F/'.git/index').read_bytes())}
    \\r=run([SDK,'agent','mission','create','owned-runtime-qualification','--mission-type','software-dev','--topology','single_branch','--owned-checkout',O,'--target-branch','main','--pr-bound','--friendly-name','Disposable owned runtime qualification','--purpose-tldr','Prove owned-root analysis freshness without production effects.','--purpose-context','Disposable caller-specific qualification of the existing corrected runtime artifact; no Phoenix or host mutation.','--json'],cwd=O)
    \\created=json.loads(r.stdout);assert created['result']=='success';M=created['mission_slug'];D=pathlib.Path(created['mission_dir']);assert D.parent==O/'kitty-specs'
    \\js('constructor.json',created)
    \\def sdk(*args,ok=True):return run([SDK,*args,'--mission',M,'--owned-checkout',O,'--json'],cwd=O,ok=ok)
    \\def nxt():return json.loads(sdk('next','--agent','codex','--result','success').stdout)
    \\assert nxt()['action']=='research'
    \\(D/'research.md').write_text('# Discovery\n\nDisposable qualification; no child effects or deployment authority.\n')
    \\assert nxt()['action']=='specify'
    \\(D/'spec.md').write_text('''# Mission Specification: Disposable owned runtime qualification
    \\
    \\## User Scenarios & Testing
    \\An operator reads a local result without touching a host. Given a valid retained
    \\input, when inspected, then one bounded report is returned. Invalid input refuses.
    \\
    \\## Requirements
    \\### Functional Requirements
    \\| ID | Title | User Story | Priority | Status | Delivery | No-op passable? |
    \\|----|-------|------------|----------|--------|----------|-----------------|
    \\| FR-001 | Read report | Operator reads one report. | High | Open | [build] | no |
    \\### Non-Functional Requirements
    \\| ID | Title | Requirement | Category | Priority | Status |
    \\|----|-------|-------------|----------|----------|--------|
    \\| NFR-001 | Bound | Report is at most 1024 bytes. | Resource | High | Open |
    \\### Constraints
    \\| ID | Title | Constraint | Category | Priority | Status |
    \\|----|-------|------------|----------|----------|--------|
    \\| C-001 | No host | No host operation is allowed. | Authority | High | Open |
    \\## Success Criteria
    \\- **SC-001**: Valid local report is returned once, with invalid control refused. — [build] · no-op passable: no
    \\''')
    \\assert nxt()['action']=='plan';sdk('agent','mission','setup-plan')
    \\(D/'plan.md').write_text('''# Implementation Plan: Disposable qualification
    \\## Summary
    \\Prepare one local read-only report with bounded output; no host action.
    \\## Technical Context
    \\**Language/Version**: Zig 0.16.0.
    \\**Primary Dependencies**: Standard library only.
    \\**Storage**: None.
    \\**Testing**: Positive bounded report and malformed refusal.
    \\**Target Platform**: macOS ARM64.
    \\**Project Type**: CLI.
    \\**Performance Goals**: Output at most1024 bytes.
    \\**Constraints**: No host effects.
    \\**Scale/Scope**: One disposable report.
    \\## Charter Check
    \\No authority or live change; actual source checks remain mandatory.
    \\## Project Structure
    \\One docs/qualification.md planning artifact; no service or implementation.
    \\''')
    \\sdk('agent','mission','setup-plan');assert nxt()['action']=='tasks'
    \\(D/'tasks.md').write_text('# Tasks\n\n## WP01 — Document the bounded report\n\n- T001: Document positive bounded report and malformed control; no host action.\n')
    \\(D/'tasks/WP01-report.md').write_text('''---
    \\work_package_id: WP01
    \\title: Document the bounded report
    \\dependencies: []
    \\subtasks: [T001]
    \\execution_mode: planning_artifact
    \\owned_files: [docs/qualification.md]
    \\create_intent: [docs/qualification.md]
    \\authoritative_surface: docs/qualification.md
    \\requirement_refs: [FR-001, NFR-001, C-001, SC-001]
    \\---
    \\## Objective
    \\Document the bounded positive report and invalid-input refusal. No host or child effect.
    \\## Subtasks
    \\T001: Write a local description of report/output/refusal bounds.
    \\## Validation
    \\Check explicit1024-byte bound and no-host constraint in the document.
    \\''')
    \\sdk('agent','mission','finalize-tasks','--validate-only');sdk('agent','mission','finalize-tasks');assert nxt()['action']=='analyze'
    \\C=P/'fixture-analysis-input.md';C.write_text('---\nschema: analysis-findings/v1\nfindings: []\ncounts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}\nverdict_hint: ready\n---\n# Analysis\nAll four requirements map to one planning artifact; no implementation or host execution.\n')
    \\sdk('agent','mission','record-analysis','--input-file',C,'--agent','codex')
    \\# The candidate's public owned action-implement is intentionally unsupported.
    \\def wp_snapshot():
    \\ return {'head':git(O,'rev-parse','HEAD').decode(),'files':{str(x.relative_to(D)):h(x.read_bytes()) for x in D.rglob('*') if x.is_file()}}
    \\unsupported_before=wp_snapshot()
    \\unsupported=run([SDK,'agent','action','implement','WP01','--agent','codex','--mission',M,'--owned-checkout',O],cwd=O,ok=False)
    \\assert unsupported.returncode!=0 and b'OWNED_ACTION_UNSUPPORTED' in (unsupported.stdout+unsupported.stderr)
    \\retain('public-owned-action-implement.unsupported.log',unsupported.stdout+unsupported.stderr)
    \\assert wp_snapshot()==unsupported_before,'Unsupported action mutated original specimen/WP state'
    \\# Current installed three-argument workflow gate: exercise positive and true drift.
    \\gate='from pathlib import Path; from specify_cli.cli.commands.agent.workflow import _require_current_analysis_report; import sys; _require_current_analysis_report(Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3])'
    \\run([RP,'-I','-B','-c',gate,D,O,M],cwd=O)
    \\original=(D/'spec.md').read_bytes();(D/'spec.md').write_bytes(original+b'\nA changed material requirement is deliberately unreviewed.\n')
    \\git(O,'add',str(D/'spec.md'));git(O,'commit','-m','Introduce intentional material drift for refusal control')
    \\gate_bad=run([RP,'-I','-B','-c',gate,D,O,M],cwd=O,ok=False);assert gate_bad.returncode!=0 and b'analysis_report_required' in gate_bad.stdout+gate_bad.stderr
    \\bad=nxt();js('actual-owned-next-drift-refusal.json',bad)
    \\assert bad.get('error_code')=='ANALYSIS_REPORT_STALE' and bad.get('action')=='analyze'
    \\(D/'spec.md').write_bytes(original);git(O,'add',str(D/'spec.md'));git(O,'commit','-m','Restore exact reviewed specimen input')
    \\sdk('agent','mission','record-analysis','--input-file',C,'--agent','codex')
    \\good=nxt();js('actual-owned-next-advance.json',good)
    \\assert good.get('action')=='implement' and good.get('wp_id')=='WP01',good
    \\assert protected=={'head':git(F,'rev-parse','HEAD').decode(),'status':git(F,'--no-optional-locks','status','--porcelain').decode(),'index_sha256':h((F/'.git/index').read_bytes())},'Disposable protected primary changed'
    \\assert protected_home==home_snapshot(),'Protected native HOME changed'
    \\js('qualification.json',{'actual_owned_next_advance':good,'true_material_drift_refused':True,'actual_workflow_helper_positive_and_negative':True,'public_owned_action_implement':'OWNED_ACTION_UNSUPPORTED with exact WP files and HEAD invariant','protected_fixture_primary_exact':True,'protected_fixture_native_home_exact':True,'actual_phoenix_qualified':False,'fixture_root':str(P),'retention':'Retain exact disposable SDK fixture and logs until independent review; no production runtime or ordinary adoption.'})
    \\print((P/'qualification.json').read_text())
;
const cache_admission_fixture =
    \\import hashlib,json,os,pathlib,subprocess,sys,tempfile
    \\child="""import json,os
    \\from types import SimpleNamespace
    \\from unittest.mock import patch
    \\try:
    \\ from specify_cli.session_presence import upgrade_check
    \\ provider=SimpleNamespace(get_latest=lambda package,prerelease=False:SimpleNamespace(version='4.0.0rc7'))
    \\ with patch('specify_cli.distribution.upgrade_provider.resolve_upgrade_provider',return_value=provider):upgrade_check.refresh_cache_once()
    \\ print(json.dumps({'refused':False,'cache_path':str(upgrade_check.CACHE_PATH)}))
    \\except ValueError as error:
    \\ import traceback
    \\ print(json.dumps({'refused':True,'reason':str(error),'admission_frames':[{'file':frame.filename,'function':frame.name,'line':frame.lineno} for frame in traceback.extract_tb(error.__traceback__)]}))
    \\"""
    \\def snapshot(root):return {str(p.relative_to(root)):(hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None,p.stat().st_mode,p.stat().st_ino,p.stat().st_mtime_ns) for p in root.rglob('*')}
    \\with tempfile.TemporaryDirectory(prefix='owned-cache-admission-') as temporary:
    \\ root=pathlib.Path(temporary);facts=[]
    \\ for kind in ('relative','parent-segment','missing-home','invalid-scope'):
    \\  case=root/kind;case.mkdir(mode=0o700);home=case/'protected-home';home.mkdir(mode=0o700)
    \\  env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_CONFIG','UV_','PIP_')) and k not in ('PYTHONPATH','PYTHONHOME','SPEC_KITTY_HOME','SPEC_KITTY_NO_UPGRADE_CHECK','SPEC_KITTY_PACKS_ROOT','SPECIFY_REPO_ROOT','SPEC_KITTY_REPO_ROOT','SPEC_KITTY_TEMPLATE_ROOT')}
    \\  env.update(HOME=str(home),SPEC_KITTY_ASSET_SCOPE='consumer',XDG_CONFIG_HOME=str(case/'config'),XDG_CACHE_HOME=str(case/'cache'),XDG_STATE_HOME=str(case/'state'),PYTHONDONTWRITEBYTECODE='1')
    \\  if kind=='relative':env['SPEC_KITTY_HOME']='relative-home'
    \\  elif kind=='parent-segment':env['SPEC_KITTY_HOME']=str(case/'segment'/'..'/'outside')
    \\  elif kind=='invalid-scope':env.update(SPEC_KITTY_ASSET_SCOPE='unadmitted',SPEC_KITTY_HOME=str(case/'operator'))
    \\  before=snapshot(case);r=subprocess.run([sys.executable,'-I','-B','-c',child],cwd=case,env=env,capture_output=True,text=True,timeout=15)
    \\  assert r.returncode==0,(kind,r.stderr)
    \\  result=json.loads(r.stdout);after=snapshot(case);facts.append({'kind':kind,**result,'state_exact':before==after,'added_paths':sorted(set(after)-set(before))})
    \\ print(json.dumps({'cases':facts,'all_refused_before_effects':all(x['refused'] and x['state_exact'] for x in facts)}))
;
fn probe(mode: []const u8) !std.json.Parsed(std.json.Value) {
    const python = c.getenv("OWNED_RUNTIME_PYTHON") orelse return error.ExplicitInstalledRuntimeRequired;
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ std.mem.span(python), "-I", "-B", "-c", if (std.mem.eql(u8, mode, "cache-admission")) cache_admission_fixture else if (std.mem.eql(u8, mode, "owned")) owned_fixture else fixture, mode },
        .stdout_limit = .limited(256 * 1024),
        .stderr_limit = .limited(64 * 1024),
        .timeout = .{ .duration = .{ .clock = .awake, .raw = .fromSeconds(if (std.mem.eql(u8, mode, "owned")) 180 else 90) } },
    });
    defer std.testing.allocator.free(result.stdout);
    defer std.testing.allocator.free(result.stderr);
    if (result.term != .exited or result.term.exited != 0) {
        std.debug.print("actual runtime fixture failed: {s}\n", .{result.stderr});
        return error.FixtureFailed;
    }
    std.debug.print("actual installed custody {s}: {s}\n", .{ mode, result.stdout });
    return std.json.parseFromSlice(std.json.Value, std.testing.allocator, result.stdout, .{});
}
test "consumer scope selects private commands and skills rather than protected native agent roots" {
    var parsed = try probe("paths");
    defer parsed.deinit();
    const facts = parsed.value.object;
    try std.testing.expect(facts.get("commands_private").?.bool);
    try std.testing.expect(facts.get("skills_private").?.bool);
    try std.testing.expect(facts.get("protected_native_state_exact").?.bool);
}
test "actual SDK startup preserves protected native-agent custody with an explicit private consumer scope" {
    var parsed = try probe("startup");
    defer parsed.deinit();
    const facts = parsed.value.object;
    try std.testing.expectEqual(@as(i64, 0), facts.get("startup_exit").?.integer);
    try std.testing.expect(facts.get("protected_native_state_exact").?.bool);
    try std.testing.expect(facts.get("commands_private").?.bool and facts.get("skills_private").?.bool);
}

test "actual owned mission advances after recorded analysis and refuses material drift without mutating protected state" {
    var parsed = try probe("owned");
    defer parsed.deinit();
    const facts = parsed.value.object;
    try std.testing.expect(facts.get("true_material_drift_refused").?.bool);
    try std.testing.expect(facts.get("actual_workflow_helper_positive_and_negative").?.bool);
    try std.testing.expect(facts.get("protected_fixture_primary_exact").?.bool);
    try std.testing.expect(facts.get("protected_fixture_native_home_exact").?.bool);
    try std.testing.expectEqualStrings("implement", facts.get("actual_owned_next_advance").?.object.get("action").?.string);
}

test "actual upgrade cache refresh honors private runtime home while default user resolution stays native" {
    var parsed = try probe("cache");
    defer parsed.deinit();
    const facts = parsed.value.object;
    try std.testing.expect(facts.get("cache_private").?.bool);
    try std.testing.expect(facts.get("actual_foreground_refresh").?.bool);
    try std.testing.expect(facts.get("default_user_cache_native").?.bool);
    try std.testing.expect(facts.get("protected_native_state_exact").?.bool);
}

test "direct foreground cache writer refuses invalid consumer admission before filesystem effects" {
    var parsed = try probe("cache-admission");
    defer parsed.deinit();
    try std.testing.expect(parsed.value.object.get("all_refused_before_effects").?.bool);
}
