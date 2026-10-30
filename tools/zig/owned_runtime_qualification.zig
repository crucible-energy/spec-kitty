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
    \\P=pathlib.Path(os.environ['OWNED_RUNTIME_FIXTURE_ROOT'])/sys.argv[1];P.mkdir(mode=0o700,parents=True)
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
    \\if sys.argv[1]=='owned-managed':
    \\ import re
    \\ original_environment=dict(E);seed_home=P/'managed-seed-runtime';seed_home.mkdir(mode=0o700)
    \\ E.update(SPEC_KITTY_HOME=str(seed_home),SPEC_KITTY_ASSET_SCOPE='user',PATH='/opt/homebrew/Cellar/git/2.55.0/bin:/opt/homebrew/bin:/Users/sam/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin')
    \\ seed=P/'managed-seed-project';seed.mkdir(mode=0o700)
    \\ git(seed,'init','-q','-b','qualification');git(seed,'config','user.name','Managed fixture');git(seed,'config','user.email','fixture@example.invalid')
    \\ run([SDK,'init','--ai','codex','--non-interactive'],cwd=seed)
    \\ managed_skills=[p for p in (H/'.agents/skills').rglob('*') if p.is_file() and not p.is_symlink()]
    \\ managed_commands=[p for p in (H/'.claude/commands').glob('spec-kitty.*.md') if p.is_file() and not p.is_symlink()]
    \\ assert managed_skills and managed_commands
    \\ for path in managed_skills:path.chmod(0o400)
    \\ for path in managed_commands:
    \\  updated,count=re.subn(r'(?m)^<!-- spec-kitty-command-version: [^\n]+ -->$','<!-- spec-kitty-command-version: 4.0.0rc7 -->',path.read_text());assert count==1
    \\  path.chmod(0o600);path.write_text(updated);path.chmod(0o444)
    \\ E.clear();E.update(original_environment);E['PATH']='/opt/homebrew/Cellar/git/2.55.0/bin:/opt/homebrew/bin:/Users/sam/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin'
    \\ protected_home=home_snapshot()
    \\ js('managed-native-seed.json',{'skill_files':len(managed_skills),'commands':len(managed_commands),'shape':'Genuine managed canonical names, skills0400/commandsplain4rc7mode0444','actual_sam_home_touched':False,'receiver_PATH_matched':True})
    \\F=P/'fixture-primary';F.mkdir(mode=0o700)
    \\run([GIT,'init','--initial-branch=codex/runtime-qualification-bootstrap',F])
    \\git(F,'config','user.name','Phoenix disposable qualification');git(F,'config','user.email','fixture@example.invalid');git(F,'config','gc.auto','0')
    \\run([SDK,'init','--ai','codex','--non-interactive'],cwd=F)
    \\git(F,'add','.');git(F,'commit','-m','Seed disposable runtime qualification');git(F,'branch','-m','main')
    \\O=P/'fixture-owned';git(F,'worktree','add','-b','codex/runtime-qualification-owner',O,'main')
    \\protected={'head':git(F,'rev-parse','HEAD').decode(),'status':git(F,'--no-optional-locks','status','--porcelain').decode(),'index_sha256':h((F/'.git/index').read_bytes())}
    \\if sys.argv[1]=='operations':
    \\ import shlex
    \\ foreign=O/'foreign-owned.txt';foreign.write_text('Preserve another task staged content.\n');git(O,'add',foreign.name)
    \\ staged=git(O,'diff','--cached','--binary');branch=git(O,'branch','--show-current').decode().strip();original_head=git(O,'rev-parse','HEAD')
    \\ def open_op(checkout=O,ok=True):return run([SDK,'dispatch','diagnose local checkout custody only','--profile','generic-agent','--owned-checkout',checkout,'--json'],cwd=O,ok=ok)
    \\ outcomes=[]
    \\ for outcome in ('done','failed','abandoned'):
    \\  opened=open_op();payload=json.loads(opened.stdout);assert payload['status']=='open'
    \\  args=shlex.split(payload['close_contract']['command']);assert args[args.index('--owned-checkout')+1]==str(O)
    \\  args[0]=SDK;args[args.index('--outcome')+1]=outcome
    \\  record=O/'kitty-ops'/(payload['invocation_id']+'.jsonl');assert record.is_file() and not (F/'kitty-ops').exists()
    \\  run([*args,'--no-commit','--json'],cwd=P)
    \\  events=[json.loads(line) for line in record.read_text().splitlines()];assert [e['event'] for e in events]==['started','completed'];assert events[-1]['outcome']==outcome
    \\  assert git(O,'rev-parse','HEAD')==original_head and git(O,'diff','--cached','--binary')==staged
    \\  outcomes.append(outcome)
    \\ opened=json.loads(open_op().stdout);record=O/'kitty-ops'/(opened['invocation_id']+'.jsonl');before_record=record.read_bytes()
    \\ args=shlex.split(opened['close_contract']['command']);args[0]=SDK;args[args.index('--outcome')+1]='abandoned'
    \\ git(O,'checkout','-b','codex/fixture-other-owner');refused=run([*args,'--no-commit','--json'],cwd=P,ok=False);assert refused.returncode!=0 and record.read_bytes()==before_record
    \\ git(O,'checkout',branch);run([*args,'--no-commit','--json'],cwd=P)
    \\ rejected={}
    \\ rejected['protected']=open_op(F,ok=False).returncode
    \\ E['SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS']='1';rejected['protected_hatch']=open_op(F,ok=False).returncode;E.pop('SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS')
    \\ detached=P/'fixture-detached';git(F,'worktree','add','--detach',detached,'main');rejected['detached']=open_op(detached,ok=False).returncode
    \\ unrelated=P/'foreign-repository';unrelated.mkdir();git(unrelated,'init','-q','-b','codex/foreign');git(unrelated,'config','user.name','Foreign fixture');git(unrelated,'config','user.email','fixture@example.invalid');(unrelated/'seed').write_text('Foreign repository must not receive an Op.');git(unrelated,'add','.');git(unrelated,'commit','-m','Foreign seed');rejected['foreign']=open_op(unrelated,ok=False).returncode
    \\ assert all(v!=0 for v in rejected.values()) and not (F/'kitty-ops').exists() and not (detached/'kitty-ops').exists() and not (unrelated/'kitty-ops').exists()
    \\ # The normal owning close still commits only its Op; --no-commit is not a forced substitute.
    \\ opened=json.loads(open_op().stdout);args=shlex.split(opened['close_contract']['command']);args[0]=SDK;args[args.index('--outcome')+1]='done';run([*args,'--json'],cwd=P)
    \\ assert git(O,'diff','--cached','--binary')==staged and foreign.read_text()=='Preserve another task staged content.\n'
    \\ normal_record='kitty-ops/'+opened['invocation_id']+'.jsonl';assert git(O,'rev-parse','HEAD')!=original_head and git(O,'show','HEAD:'+normal_record)==(O/normal_record).read_bytes()
    \\ assert git(O,'diff-tree','--no-commit-id','--name-only','-r','HEAD').decode().splitlines()==[normal_record]
    \\ assert git(F,'rev-parse','HEAD').decode()==protected['head'] and git(F,'--no-optional-locks','status','--porcelain').decode()==protected['status'] and h((F/'.git/index').read_bytes())==protected['index_sha256']
    \\ assert protected_home==home_snapshot()
    \\ print(json.dumps({'actual_outcomes':outcomes,'normal_close_commits_own_record':True,'switched_branch_refused_before_append':True,'foreign_protected_detached_refused':rejected,'primary_and_native_unchanged':True,'foreign_staged_state_exact':True,'actual_host_actions':False}))
    \\ sys.exit(0)
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
const managed_native_fixture =
    \\import hashlib,json,os,pathlib,re,subprocess,sys,tempfile
    \\for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_CEILING_DIRECTORIES','GIT_DISCOVERY_ACROSS_FILESYSTEM'):
    \\ assert key not in os.environ,'Inherited Git override refused: '+key
    \\sdk=str(pathlib.Path(sys.prefix)/'bin/spec-kitty')
    \\with tempfile.TemporaryDirectory(prefix='owned-managed-native-') as temporary:
    \\ root=pathlib.Path(temporary);home=root/'protected-home';home.mkdir(mode=0o700)
    \\ seedhome=root/'seed-runtime';private=root/'consumer-runtime'
    \\ for path in (seedhome,private):path.mkdir(mode=0o700)
    \\ env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_CONFIG','UV_','PIP_')) and k not in ('PYTHONPATH','PYTHONHOME','SPEC_KITTY_PACKS_ROOT','SPECIFY_REPO_ROOT','SPEC_KITTY_REPO_ROOT','SPEC_KITTY_TEMPLATE_ROOT','FORCE_COLOR')}
    \\ env.update(HOME=str(home),SPEC_KITTY_HOME=str(seedhome),SPEC_KITTY_ASSET_SCOPE='user',SPEC_KITTY_NO_UPGRADE_CHECK='1',XDG_CONFIG_HOME=str(seedhome/'config'),XDG_CACHE_HOME=str(seedhome/'cache'),XDG_STATE_HOME=str(seedhome/'state'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0',PYTHONDONTWRITEBYTECODE='1',NO_COLOR='1')
    \\ def initialize(name,environment):
    \\  repo=root/name;repo.mkdir(mode=0o700)
    \\  for args in (['/usr/bin/git','init','-q','-b','qualification',str(repo)],['/usr/bin/git','-C',str(repo),'config','user.name','Managed native fixture'],['/usr/bin/git','-C',str(repo),'config','user.email','fixture@example.invalid']):subprocess.run(args,env=environment,capture_output=True,check=True,timeout=10)
    \\  result=subprocess.run([sdk,'init','--ai','codex','--non-interactive'],cwd=repo,env=environment,capture_output=True,text=True,timeout=65)
    \\  assert result.returncode==0,(name,result.returncode,result.stderr[-1600:])
    \\ initialize('seed-project',env)
    \\ skills=[p for p in (home/'.agents/skills').rglob('*') if p.is_file() and not p.is_symlink()]
    \\ commands=[p for p in (home/'.claude/commands').glob('spec-kitty.*.md') if p.is_file() and not p.is_symlink()]
    \\ assert skills and commands,'Genuine managed native seed not generated'
    \\ for path in skills:path.chmod(0o400)
    \\ for path in commands:
    \\  raw=path.read_text();updated,count=re.subn(r'(?m)^<!-- spec-kitty-command-version: [^\n]+ -->$', '<!-- spec-kitty-command-version: 4.0.0rc7 -->',raw)
    \\  assert count==1
    \\  path.chmod(0o600);path.write_text(updated);path.chmod(0o444)
    \\ def snapshot():return {str(p.relative_to(home)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode,p.stat().st_ino,p.stat().st_mtime_ns) for p in home.rglob('*') if p.is_file() and not p.is_symlink()}
    \\ before=snapshot();env.update(SPEC_KITTY_HOME=str(private),SPEC_KITTY_ASSET_SCOPE='consumer',XDG_CONFIG_HOME=str(private/'config'),XDG_CACHE_HOME=str(private/'cache'),XDG_STATE_HOME=str(private/'state'))
    \\ initialize('consumer-project',env);after=snapshot()
    \\ changes=[{'path':p,'before':before.get(p),'after':after.get(p)} for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
    \\ print(json.dumps({'genuine_managed_skill_files':len(skills),'genuine_managed_commands':len(commands),'protected_managed_native_state_exact':not changes,'changes':changes,'actual_sam_home_touched':False,'interpretation':'Recreated managed-name/version/permission shape only; not exact lost native before content or actual receiver causation.'}))
;
const acceptance_fixture =
    \\import hashlib,json,os,pathlib,subprocess,sys,tarfile
    \\P=pathlib.Path(os.environ['OWNED_RUNTIME_FIXTURE_ROOT'])/'acceptance';P.mkdir(mode=0o700,parents=True)
    \\F=P/'primary';F.mkdir();O=P/'owned';H=P/'native-home';H.mkdir();C=P/'operator';C.mkdir()
    \\V=H/'.agents/skills/valuable/SKILL.md';V.parent.mkdir(parents=True);V.write_text('Valuable native state remains outside SDK authority.\n');V.chmod(0o400)
    \\E={k:v for k,v in os.environ.items() if not k.startswith(('GIT_CONFIG','UV_','PIP_')) and k not in ('PYTHONPATH','PYTHONHOME','GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE','SPECIFY_REPO_ROOT','SPEC_KITTY_REPO_ROOT','SPEC_KITTY_PACKS_ROOT','SPEC_KITTY_TEMPLATE_ROOT','BASH_ENV','ENV','GH_TOKEN','GITHUB_TOKEN','SSH_AUTH_SOCK','SSH_AGENT_PID')}
    \\E.update(HOME=str(H),SPEC_KITTY_HOME=str(C),SPEC_KITTY_ASSET_SCOPE='consumer',SPEC_KITTY_NO_UPGRADE_CHECK='1',PYTHONDONTWRITEBYTECODE='1',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_OPTIONAL_LOCKS='0',GIT_TERMINAL_PROMPT='0',PATH='/opt/homebrew/Cellar/git/2.55.0/bin:/usr/bin:/bin',XDG_CONFIG_HOME=str(C/'config'),XDG_CACHE_HOME=str(C/'cache'),XDG_STATE_HOME=str(C/'state'),NO_COLOR='1')
    \\SDK=pathlib.Path(sys.prefix)/'bin/spec-kitty';M='inference-protected-signing-01M65BHK';sequence=0
    \\h=lambda b:hashlib.sha256(b).hexdigest()
    \\def run(args,cwd,allowed=(0,)):
    \\ global sequence
    \\ sequence+=1;r=subprocess.run([str(x)for x in args],cwd=cwd,env=E,capture_output=True,timeout=45)
    \\ (P/f'{sequence:02d}.stdout.log').write_bytes(r.stdout);(P/f'{sequence:02d}.stderr.log').write_bytes(r.stderr)
    \\ assert r.returncode in allowed,(sequence,args,r.returncode,r.stderr[-1500:]);return r
    \\def git(root,*args):return run(['/opt/homebrew/Cellar/git/2.55.0/bin/git','--no-optional-locks','-C',root,*args],root).stdout.decode()
    \\(F/'.kittify').mkdir();(F/'.kittify/config.yaml').write_text('agents:\n  available: [codex]\n')
    \\git(F,'init','-q','-b','main');git(F,'config','user.name','Disposable acceptance fixture');git(F,'config','user.email','fixture@example.invalid');git(F,'config','commit.gpgsign','false');git(F,'add','.');git(F,'commit','-qm','Primary without owning mission');git(F,'worktree','add','-qb','codex/inference-signing',str(O))
    \\for key,digest in [('OWNED_ACCEPTANCE_SOURCE_ARCHIVE','b36e04cf831edbaa6e8e4e58c895cacd4b4ef9fce36046ba5dffa4123e52a581'),('OWNED_ACCEPTANCE_MISSION_ARCHIVE','0ff8338c6460dcfb6cfb46b0a718865c639b802e39aab16dcdfb4e6416709da9')]:
    \\ archive=pathlib.Path(os.environ[key]);assert h(archive.read_bytes())==digest
    \\ with tarfile.open(archive)as tf:
    \\  for member in tf.getmembers():
    \\   path=pathlib.PurePosixPath(member.name);assert not path.is_absolute() and '..'not in path.parts and '.git'not in path.parts
    \\   assert member.isfile()or member.isdir()or member.issym(),member.name
    \\   if member.issym():assert not pathlib.PurePosixPath(member.linkname).is_absolute()and '..'not in pathlib.PurePosixPath(member.linkname).parts
    \\ run(['/usr/bin/tar','-xf',archive,'-C',O],F)
    \\git(O,'add','.');git(O,'commit','-qm','Immutable source and authored mission fixture')
    \\D=O/'kitty-specs'/M;matrix=D/'acceptance-matrix.json';original=matrix.read_bytes();task=next((D/'tasks').glob('WP01-*.md'));task_before=task.read_bytes();lanes=D/'lanes.json';lanes_before=lanes.read_bytes()
    \\def snapshot(root):
    \\ files={}
    \\ for base,dirs,names in os.walk(root,followlinks=False):
    \\  dirs[:]=sorted(d for d in dirs if d!='.git')
    \\  for name in sorted(names):
    \\   if name=='.git':continue
    \\   p=pathlib.Path(base)/name;s=p.lstat();files[str(p.relative_to(root))]=(h(p.read_bytes()),s.st_mode,s.st_ino,s.st_mtime_ns)
    \\ return {'head':git(root,'rev-parse','HEAD'),'status':git(root,'status','--porcelain=v1','--untracked-files=all'),'files':files}
    \\primary=snapshot(F);native=(h(V.read_bytes()),V.stat().st_mode,V.stat().st_ino,V.stat().st_mtime_ns);assert not(F/'kitty-specs'/M).exists()
    \\def diagnose(label):
    \\ before=snapshot(O);r=run([SDK,'accept','--mission',M,'--owned-checkout',O,'--mode','local','--actor','codex','--diagnose','--json'],O,(0,1));summary=json.loads(r.stdout)
    \\ (P/(label+'.json')).write_text(json.dumps(summary,indent=2)+'\n');assert snapshot(O)==before and snapshot(F)==primary;assert native==(h(V.read_bytes()),V.stat().st_mode,V.stat().st_ino,V.stat().st_mtime_ns)
    \\ return summary
    \\positive=diagnose('positive');matrix.unlink();missing=diagnose('missing')
    \\failing=json.loads(original);failing['criteria'][0]['pass_fail']='fail';matrix.write_text(json.dumps(failing,indent=2)+'\n');failed=diagnose('failing')
    \\# Planning-only control has explicit planning frontmatter, not an inferred default.
    \\matrix.unlink();assert b'execution_mode: code_change'in task_before;task.write_bytes(task_before.replace(b'execution_mode: code_change',b'execution_mode: planning_artifact',1));planning=json.loads(lanes_before);planning['planning_artifact_wps']=['WP01'];lanes.write_text(json.dumps(planning,indent=2)+'\n');planning_result=diagnose('planning-only')
    \\# Restore exactly the authored bytes; do not synthesize review evidence or history.
    \\task.write_bytes(task_before);lanes.write_bytes(lanes_before);matrix.write_bytes(original)
    \\def wrongly_skips(summary):return any('planning_artifact-only'in x['detail']for x in summary['skipped_checks'])
    \\facts={'positive_matrix_evaluated':not wrongly_skips(positive),'positive_ok':positive['ok'],'missing_refuses_matrix':not missing['ok']and any(x['check']=='acceptance_matrix'for x in missing['blocked_checks']),'failing_refuses_verdict':not failed['ok']and not wrongly_skips(failed)and any('verdict'in x['detail'].lower()or 'fail'in x['detail'].lower()for x in failed['failed_checks']),'planning_only_skips_matrix':wrongly_skips(planning_result),'primary_mission_absent':not(F/'kitty-specs'/M).exists(),'primary_native_unchanged':snapshot(F)==primary and native==(h(V.read_bytes()),V.stat().st_mode,V.stat().st_ino,V.stat().st_mtime_ns),'scope':'Disposable exact authored source+mission fixture; historical commit ancestry not reconstructed, no actual Auth mutation'}
    \\(P/'facts.json').write_text(json.dumps(facts,indent=2)+'\n');print(json.dumps(facts))
;
fn probe(mode: []const u8) !std.json.Parsed(std.json.Value) {
    const python = c.getenv("OWNED_RUNTIME_PYTHON") orelse return error.ExplicitInstalledRuntimeRequired;
    const result = try std.process.run(std.testing.allocator, std.testing.io, .{
        .argv = &.{ std.mem.span(python), "-I", "-B", "-c", if (std.mem.eql(u8, mode, "acceptance")) acceptance_fixture else if (std.mem.eql(u8, mode, "managed-native")) managed_native_fixture else if (std.mem.eql(u8, mode, "cache-admission")) cache_admission_fixture else if (std.mem.eql(u8, mode, "owned") or std.mem.eql(u8, mode, "owned-managed") or std.mem.eql(u8, mode, "operations")) owned_fixture else fixture, mode },
        .stdout_limit = .limited(256 * 1024),
        .stderr_limit = .limited(64 * 1024),
        .timeout = .{ .duration = .{ .clock = .awake, .raw = .fromSeconds(if (std.mem.eql(u8, mode, "owned") or std.mem.eql(u8, mode, "owned-managed") or std.mem.eql(u8, mode, "managed-native") or std.mem.eql(u8, mode, "operations")) 180 else 90) } },
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

test "consumer SDK preserves genuine existing managed native assets with readonly modes and older command markers" {
    var parsed = try probe("managed-native");
    defer parsed.deinit();
    try std.testing.expect(parsed.value.object.get("protected_managed_native_state_exact").?.bool);
}

test "owned workflow preserves canonical managed native state across both setup-plan calls and matched caller PATH" {
    var parsed = try probe("owned-managed");
    defer parsed.deinit();
    const facts = parsed.value.object;
    try std.testing.expect(facts.get("protected_fixture_primary_exact").?.bool);
    try std.testing.expect(facts.get("protected_fixture_native_home_exact").?.bool);
    try std.testing.expectEqualStrings("implement", facts.get("actual_owned_next_advance").?.object.get("action").?.string);
}

test "standalone operation opens and closes only in its owned checkout with real outcomes and custody refusals" {
    var parsed = try probe("operations");
    defer parsed.deinit();
    const facts = parsed.value.object;
    try std.testing.expect(facts.get("normal_close_commits_own_record").?.bool);
    try std.testing.expect(facts.get("switched_branch_refused_before_append").?.bool);
    try std.testing.expect(facts.get("primary_and_native_unchanged").?.bool);
    try std.testing.expect(facts.get("foreign_staged_state_exact").?.bool);
    try std.testing.expectEqual(@as(usize, 3), facts.get("actual_outcomes").?.array.items.len);
}

test "owned code acceptance evaluates its matrix and refuses missing or failed evidence while planning stays planning" {
    var parsed = try probe("acceptance");
    defer parsed.deinit();
    const facts = parsed.value.object;
    try std.testing.expect(facts.get("positive_matrix_evaluated").?.bool);
    try std.testing.expect(facts.get("positive_ok").?.bool);
    try std.testing.expect(facts.get("missing_refuses_matrix").?.bool);
    try std.testing.expect(facts.get("failing_refuses_verdict").?.bool);
    try std.testing.expect(facts.get("planning_only_skips_matrix").?.bool);
    try std.testing.expect(facts.get("primary_mission_absent").?.bool);
    try std.testing.expect(facts.get("primary_native_unchanged").?.bool);
}
