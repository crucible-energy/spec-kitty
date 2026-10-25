---
title: Organization lifecycle rollout
description: Implementation decisions, preservation findings, and qualification limits for automatic workspace closeout.
doc_status: active
audience: ../../context/audience/internal/ai-collaboration-agent.md
updated: '2026-10-24'
---

# Organization lifecycle rollout — October 24

Owner: Crucible workspace closeout chat 01a13ea3-0da1-74e1-8dac-15272359d71a. Existing source lane: `codex/organization-workspace-lifecycle-20261020`; no competing lifecycle lane. Independent shared analysis-control repair belongs to 01a0947c-e88c-7d52-b067-b6fcb634c064.

## User Experience Findings

Required organization metadata did not execute cleanup. Published RC7 lacks this fork's lifecycle module, and current source publication still targets an integration branch. Treating those facts as deployment would hide retained resources. Fixed worktree counts also obscured actual closeout; Sam removed them.

The older project layout blocked the latest CLI before mission advancement. The supported migration's first surface pass reported its changed `.claude` input; resuming after that materialized change completed. The CLI's `upgrade --project --json` is a compatibility report, not an applied migration. Owned task status changes require project auto-commit enabled; only this reserved lane's project setting was changed, allowing canonical status commits.

A safe tar extraction restored the ledger directory as 0755. The native store correctly refused it. Restoring its manifest's exact 0700 privacy requirement made the recovered history readable; permission restoration belongs in recovery instructions.

## Engineering Decisions

- Preserve the prior seven approvals; WP08–WP10 extend the accepted mission through canonical task validation/finalization. They cover durable useful-work obligations, automatic creator/distribution integration, and actual organization rollout proof.
- Follow the current default branch's Zig requirement for new implementation. Existing Python lifecycle remains the behavior/release reference; any migration glue remains bounded.
- Finish obligations preserve source identity, owner, purpose, next action, review event and append history with expected revision. They grant no release or deletion authority. There is no terminal `retired` or `closed` input stage. Existing creator-verified retirement remains the authority.
- Use an explicit private POSIX ledger, descriptor-relative no-follow access, owned regular 0600 files, nonblocking exclusive writer lock, atomic publication and file/directory synchronization. Missing history is never silently initialized. Unsupported storage/platform conditions refuse. Finite input/history bounds are storage safety limits, not worktree ceilings.
- RC7 runtime lives in a separate verified installation. Its runtime assets are isolated with `SPEC_KITTY_HOME`. Supported project migrations preserved the primary checkout HEAD, all eight original dirty source/prose files and 112 evidence files byte-for-byte; no pre-existing primary work was committed.

## Validation and delivery evidence

External receipts remain under the closeout workspace's `outputs/`, keeping validation results outside the candidate. Exact-source existing creator acceptance passed 75 tests, including real asynchronous workspace/local branch retirement, replay once and preservation controls. The first unpinned attempt mixed source with installed subprocess modules and failed three cases; it is retained rather than counted as a project pass.

Native finish-store tests exercise real persisted history, stale revision refusal, symlink evidence preservation, private permissions and concurrent writer exclusion. Self-review reproduced a missing-history reset: an existing lock with deleted history allowed initialize to replace lost obligations. The failing receipt was retained; exclusive initialization now requires explicit recovery, with Debug/ReleaseSafe and actual CLI refusal proof. Debug and ReleaseSafe results plus executable/source hashes and isolated restoration are recorded externally. These are bounded source/fixture proofs, not production adoption.

## Known Limitations

No organization automatic cleanup rollout is complete. WP08's obligation store does not itself clean anything. Worker integration, packaged native distribution, supported actual creator hooks, source review/publication chain and per-repository runtime/execution receipts remain WP09/WP10. Existing retirement also needs fresh actual-default ancestry/tree/review checks and exact unique-source recovery before any deployment; old API-only positive fixtures do not prove these. A shallow-source bundle may verify locally yet fail isolated restoration without its boundary; preserve and test that actual recovery scope. Historical unknown ownership or unrecovered artifacts remain retained; no count, age, session end or declaration permits retirement. The finish history currently refuses at its finite size limit; reviewed archival/compaction must preserve all history before expansion. No broad pruning, Docker or production-service action occurred.

## Independent review round 1 and repair

The independent owner review reproduced two P2 defects at native source f131e0df: umask0200 caused a successful replacement to publish unreadable0400 history, and an incomplete persisted object `{}` decoded as valid empty history because envelope fields had defaults. Both were captured as failing native regressions before repair; the canonical review event requested changes and reset the subtask. Only newly exclusively created descriptors are now normalized and verified0600 before publication. Persisted schema/revision/events are mandatory; initial in-memory state uses an explicit constructor. No existing untrusted file is chmodded by the tool.

Debug and ReleaseSafe each pass nine focused native tests; the rebuilt real CLI under restrictive umask now reopens exact revision1, and malformed envelope/missing fields refuse without rewrite. Existing wrong-mode history remains unchanged/refused. The updated exact-source receipt is external `lifecycle-wp08-r2-real-cli-proof.json`; independent re-review is still required. This is structural corruption protection, not cryptographic rollback detection against an owner replacing an entire valid history.

Retained creator repair separately reproduced three unsafe actual disposable-worktree retirements: stale merged API evidence with replaced default history, a live foreign cwd, and a live open-file dependency. The runtime-holder guard now preserves both actual holders and keeps the successful retirement/late-state controls; scoped Darwin system-lsof is used because protected user agents can deny psutil descriptor queries. Unknown visibility retains. Current default delivery/review/recovery proof remains an uncompleted production gate.

## Native approval and creator safety qualification

Independent Reviewer Renata replayed both native R1 defects against exact native source SHA-256 `587936899f3bb3912701ae5b4f41d872bff1193e0da688656e3c674fe3252ad1` and approved bounded WP08. The canonical review event now records that approval. It grants no creator retirement, release, or organization deployment approval. The prior accepted WP01–WP07 source was fast-forward-published at fda26ce35 as an intermediate integration base; PR #113 remains draft while production safety and release gates are resolved.

The first broader creator repair run passed 136 controls and failed the hostile-PYTHONPATH worker case: an internal Git ref child did not inherit the worker's pinned distribution. Its recovery refused and preserved the checkout. Only internal ref subprocesses now receive the actual loaded distribution; user producer environments remain unchanged. A subsequent frozen run passed 178 behavioral and architectural controls, but independent self-review still reproduced unsafe interpretation of Git replace refs. That result is retained as incomplete evidence, not a qualified deployment.

Further red/green cases cover a process holding linked-worktree administration outside the source directory, and borrowed Git objects that a local recovery ref cannot protect from a separate owner's garbage collection. The current repair observes exact creator administration as well as source paths, ignores replace-object overlays for custody proofs, refuses graft metadata, and retains shallow, partial, alternate, or symlinked object stores without a separately proved recovery workflow. Fresh fetched default ancestry/content, paginated review disposition, and current source-ref observation are required. Recovery records retain an accountable owner, purpose, next action, review event, exact source ref, and reconstruction scope. They prove an index and ancestry inside a retained canonical store; they are not off-host backups or archive approval.

### Remaining gates

The changed-statement gate initially reported 77%, below the required 90%; no threshold or exclusion was changed. Additional tests exercise actual Git-graph attacks, late runtime and source changes, borrowed-store custody, API pagination, and Linux guard predicates. Mocked Linux predicate checks are not actual Linux platform qualification. The final candidate still requires its complete checks and independent review. Native packaging, actual creator integration, intentional RC7 default-branch adoption, and per-repository execution rollout remain unfinished. Organization metadata is configured for 119 repositories; verified runtime execution adoption remains 0. No production worker, Docker cleanup, or broad cache prune was enabled.

## WP11 independent review repair

The independent review of candidate 597207757 requested changes: a linked `objects/pack` directory or individual pack/index symlinks still passed the recovery proof. Both real-Git cases retired disposable worktrees; their local ref did not retain the separately owned target. The canonical event rejected WP11 and reset T011 before repair. A bounded descriptor-relative traversal now refuses every nested object-storage symlink or special file without following it, checks directory identity across opens, and retains unsupported or exhausted inspection. Regular hard links remain allowed because the local directory entry retains the inode. The same check applies when replaying a stored retirement receipt.

Five actual external-storage variants (pack directory, pack, index, loose object and info directory), a positive regular-hardlink retirement, and the previous shallow/partial/alternate controls passed in the focused eleven-case repair run. Full regression, changed-statement and independent re-review gates remain pending; no source/runtime rollout is inferred.

A separate test-producer defect was reproduced without deletion: the existing startup helper selects other runs' directories for removal solely by age, including a live producer's cwd. It is routed to the existing owner as a release blocker. Current checks now use explicitly admitted private basetemp roots, avoiding that cross-run maintenance path without disabling any product behavior checks. Earlier invocations may have executed the existing helper; it did not retain an attribution receipt, so its possible effects cannot be retroactively attested. Failed-run artifacts remain preserved. No manual broad prune was performed.

## 2026-10-25 — actual event consumers of hardened delivery

The combined adapter/acceptance/kernel/remote-owner gate passed214 cases and the four complete interruption/rollback modules plus original-path cleanup case passed25. All137frozen source hashes matched. The mandatory combined baseline passed2452 with5declared skips. Broader required owning modules then passed113/failed3: event fixtures still used made-up merge SHA b*40 and no review-thread response, so production correctly retained delivery_missing. Update only the positive event fixtures to real existing local-mirror commit/source/default identity and bounded zero-thread API data; preserve the initial unmerged refusal, malformed-creator queue behavior and unreleased sibling. Production guards stay unchanged. This is fixture propagation, not a new Python service.

An external all-retention repeat now preserves actual async local retirement evidence: exact path/local branch absent, one retired operation, named canonical recovery ref, independent index and nine-file restore. Earlier passing per-test fixtures had been removed by pytest's failed-only retention; that custody gap is recorded, not a restored-data claim. This source proof uses a bounded API stand-in, not production GitHub admission, installed native distribution or organization adoption. No reclaimed-capacity claim.

Canonical finalization first refused because the reviewed dependency9fdcc64 retired a five-line alias shim still named literally in approved WP07's current execution map. The actual sole authority, core/owned_mission.py, was already declared there. Reconcile only that dead path in authored planning with the exact deletion provenance; preserve historical task/approval commits and every runtime status/event byte. No recreated shim, false create_intent, guard waiver or new implementation approval. Supported validate-only and normal refresh must accept and demonstrate preservation before publication.

## Hosted9d blockers — October24 local time

The required hosted run is red, with33siblings canceled; there is no full consolidation/terminus pass. Archive-freeze treats this new-to-default live dossier as ordinary archive at the stacked feature base. WP13 will qualify a typed immutable-base/default boundary with adversarial negative controls rather than remove history or add a broad exemption. Existing Root/native design review is advisory pending exact code and proofs.

Four Linux retirement cases retain creator_operation_unsupported before delivery. The adapter combines nested traversal completeness and runtime visibility completeness into that result, but currently hides the failed provider stage. WP11 first records actionable bounded diagnostics without weakening any predicate or deadline, then requires actual Linux evidence for repair. Root separately owns released documentation frontmatter and exact stale CI-filter/epoch corrections. No source-level local result is a hosted pass, default delivery, installed cleanup or119-repository execution adoption. No disk recovery is claimed.

## Linux visibility diagnosis — bounded source follow-up

### User experience finding

The actual Linux hosted run retained four released fixtures before delivery inspection with only `creator_operation_unsupported`. That correctly blocks uncertain cleanup but hides the failed provider, stage or bound; a successful Mac run cannot diagnose it. Worker stdout is intentionally detached, so the observation must survive in its existing structured result.

### Engineering decision

Runtime observations now attach a private-context diagnostic to an inspection and copy it into the worker result only for unsupported retention. It records provider, checkout/admin scope, scan stage, process count, elapsed time, outcome and exception class; it excludes paths, command lines, exception messages and release capabilities. It never enters eligibility, release, recovery or evidence fingerprints. All time/process bounds, UID filtering, holder checks and unknown-retention predicates remain unchanged. Tests preserve AccessDenied at each Linux stage, vanished processes, other users, exhausted bounds, real holders and detached-worker preservation.

### Validation and limitations

The first focused receipt has 18 passing controls, with all five frozen modified source files unchanged and the producer joined. The earlier eight-case run was named “red” but loaded implementation edits before collection; it is a passing exploratory result, not a before-repair reproduction. The actual hosted failures remain the red evidence. The diagnostic-only change is not a Linux cause repair, a full owning gate, installed distribution, cleanup of real project work, or organization adoption. Actual Linux observation and independent review remain required.

## WP13 — live stacked source and immutable default history

### User experience findings

The hosted archive job incorrectly froze a live mission newly introduced on its non-default integration branch. A real-Git fixture reproduced the same `ordinary archive history changed` refusal before guard implementation. Earlier acceptance metadata was a retained snapshot, while the work packages remained nonterminal; it was not new approval.

Self-review then reproduced three overly permissive cases in the initial correction: a legacy slug-based archive identity, metadata formatting changes, and local Git grafts hiding formerly published identity history. Those results were retained as failures, then corrected; they are not passing validation. The diagnostic follow-up separately passed the complete 117 adapter/event/original cleanup checks with all frozen source hashes unchanged and the producer joined.

### Engineering decisions

Preserve the validated event's exact review frontier and all four historical roots. The new classification uses immutable BASE identity and nonterminal state, exact unchanged metadata, matching canonical path/UUID/MID8/target, absence from BASE/current archive registry, old event-byte prefixes, actual canonical status replay, and index/disk parity. Only those preexisting paths in the qualified mission are admitted. Deletions, unknown visibility, identity changes and forged snapshots remain frozen.

Actual own-default identity is independently checked through the matching remote's live HEAD symref/SHA and exact available local default commit. The bounded joined Git transport reads complete, non-shallow/non-partial history, disables replacement/graft views and lazy fetching, and searches by UUID/MID8 across all historical roots and the canonical archive registry. A moved, deleted or legacy default identity remains frozen. No fetch, Git rewrite, fixture waiver, runtime repair, host operation or broad prefix exemption grants eligibility.

### Known limitations and gates

This bounded classifier also retains metadata edits, including formatting, until a separate reviewed workflow qualifies them. It intentionally refuses on unavailable/stale default identity or unsupported history, rather than guessing. New tests use real local Git with an explicitly private remote stand-in; their results do not establish hosted execution, default-branch delivery, installed runtime adoption or organization cleanup. The complete affected guard file, existing frontier/ratchet controls, independent review, required combined source/publication gates and actual Linux result remain outstanding. Organization verified execution adoption remains zero.

### Complete guard result and independent diagnostic finding

The full affected archive file completed with 89 passing checks and one failure at the actual local default frontier, before live-stack classification. Canonical replay of the pinned cyclic-lane dossier attributes three duplicate terminal transitions to their earlier event IDs/times, while the immutable committed snapshot attributes the later duplicates. No snapshot, archive proof pin, default frontier or guard exemption was changed. The installed test dependency is spec-kitty-events10.5.1, within current source requirements; actual default66b requires6.x and has no copy of this dossier. Attribution and compatibility repair remain open through the existing release/status owner; this is not labeled an actual-default failure or a passing full gate.

The independent owner review found uninstrumented lsof/unsupported counts were incorrectly emitted as zero, and a metadata-only failure could carry the previous checkout's count/time. Seven new assertions reproduced the issue before correction. Those measurements now remain null when unknown; metadata-only observations identify the Git identity stage and clear unrelated scan values. Linux observations retain measured enumeration counts, including a genuinely empty enumeration. All retirement predicates and bounds are unchanged. The follow-up requires exact-source validation and reviewer disposition; it does not resolve the actual hosted Linux visibility cause.

### Endpoint review finding and locked validation closure

Independent review reproduced a genuine namespace bypass: a different server with the same trailing owner/repository name could supply the clean default while the actual origin still contained the dossier. This was reproduced locally before repair. The legacy frontier helper remains unchanged; the new live exception now binds the platform server, correlated clone/SSH endpoints and exact repository path. Both the single configured fetch URL and its resolved effective URL must match that approved identity. Missing/mismatched context, rewritten foreign endpoints and multivalued URLs retain the archive before contact. No new authority flag, host action, token requirement, workflow exception or remote mutation was introduced.

Only the network contact is isolated in new fixtures; endpoint/config validation is real, and HEAD/history comes from an actual private Git mirror. Forty-nine focused controls passed after the correction. Self-review additionally reproduced optional clone-suffix normalization incorrectly consuming an authoritative repository-name suffix; the canonical endpoint now appends its own transport suffix before normalization, with valid-name and wrong-sibling controls.

The complete guard and adapters previously passed 187 checks under exact project-locked events10.4.0/Python3.11.15, with all source/dependency files unchanged. The governing latest qualified CLI remains a separate runtime. New-source strict type checks were already clean; existing test helpers exposed weak annotations/unchecked object access. Their transport contracts and JSON shape checks are now explicit, without ignores, casts or checker relaxation. The reused-PID negative uses a real bounded joined child, preserving the no-later-signal assertion. Full updated owning tests, exact-source type checks and independent final review remain delivery gates; all results live in external receipts so recording them does not mutate the candidate.

## October 25 — actual Linux refusal and complete diagnostics

### User experience findings

Exact source 525863 passed the complete 353 archive/lifecycle checks with unchanged
source/toolchain identity and received bounded independent approval. Canonical
WP13 approval is durable at e8c1f757. Root published the combined c19024d9 through
PR120 HEAD, preserving its integration base and main. The actual hosted archive
check passed. The Linux core_misc4 shard then failed two lifecycle cases after
1,129 passes and three skips: process inspection returned AccessDenied before
delivery. The core_misc3 shard was canceled by failfast, not passed. Existing
tuple/dictionary assertion messages abbreviated the diagnostic and concealed its
provider/stage/count. The complete retained job log confirms that this was pytest
message formatting, not only a log-download limit.

### Engineering decisions

Render the existing sanitized diagnostic as JSON text in the affected adapter
and fresh-worker assertions. The installed pytest formatter preserves string
messages verbatim while applying bounded repr to dictionaries. No runtime
predicate, deadline, process selection, authority, assertion condition, workflow
filter or delivery requirement changes. Actual Linux inspection-stage evidence
is still required before selecting an eligibility repair.

Retained receipts identified this chat's unfinished supported primary RC7
migration. A scoped local policy commit de1a2fdf preserved 110 distinct inherited
source/evidence files and byte-identical charter-pack moves. Its policy archive
members were independently hash-read; canonical context and scoped diff checks
passed. This is local project-policy adoption, not default delivery. The first
fresh 13-package report recorded a genuine high ownership finding; canonical
WP09 scope amendment 64f3e603 then added actual allocator/completion hook ownership
without changing sealed core bodies or prior runtime history. New report 2d165875
is ready for dependency-ordered planning, not production. Canonical next still
reports dependencies_not_satisfied, with no guard failure.

### Known limitations

All final results for this diagnostic-message increment remain in external
receipts. Actual Linux cause, WP11/WP12 review and delivery, true newest-release
source convergence, immutable installed ordinary ingress and every-repository
execution rollout remain open. Fresh authenticated inventory contains 119 exact
repository IDs with both required policy values; the connected app exposes only 87
and cannot supply the rollout denominator. Verified execution adoption remains
zero. No project/cache/host resource was removed or capacity recovery attributed.

## Denied-process observation before a Linux policy decision

### User experience findings

The complete a8b742e Linux core_misc3 log records five failures, 1,126 passes and
three skips. Full JSON establishes the unavailable operation: psutil cwd at
enumeration position 125, with AccessDenied, before delivery. A position is not
a process identity or cause. The actual process, principal and state were not
recorded, so no attribution to an unrelated service, stale producer or exit race
is justified. The sibling shard was canceled, not passed.

### Engineering decisions

The committed red controls reproduced four missing observation fields while the
eight existing holder/visibility outcomes remained unchanged. Add a private
non-authoritative observation only after a Linux access denial: the observed
PID, cached real/effective/saved UID match facts, and best-effort process state
within the existing remaining deadline. No additional UID query, process
selection change, privilege request, subprocess, signal, command line, name,
path or exception message is introduced. State-read errors remain unknown;
absence, exit and zombie observations do not grant identity, release or cleanup.
Enumeration failures cannot be attributed to the preceding process. Fresh
observations clear stale details, and elapsed accounting includes the optional
state read. Completion and release decisions never consume these fields.

Twenty-three controlled provider checks pass, including privacy, expired-budget,
no-context, principal mismatch, stale attribution and elapsed-accounting cases.
These controls explain the observation mechanism; they are not the actual Linux
cause. Strict checks keep the original six-file source/test scope without
suppressions. The validation controller now rejects a malformed JUnit receipt
argument before creating a job or starting tests, following an earlier retained
collection refusal. This controller improvement changes no product gate.

### Known limitations

The exact-source complete owning, coverage and publication checks remain in
external receipts. Another actual hosted Linux observation is required before
selecting a runtime repair. Runtime admission and every-repository execution
qualification remain incomplete; the production worker stays disabled. Useful
work, uncertain resources and their recovery obligations remain protected.

## October 25 — protected procfs observation, before any policy repair

### User experience findings

Published integration `2214f39c` reached Linux core_misc shard 2: four failures,
1,128 passes and four skips in 256.60 seconds. The exact decoded log is retained
externally. The denied PID was 970, sleeping, with real/effective/saved UIDs all
matching the caller. Its cwd remained unavailable. This is not an observation
of a vanished, zombie or foreign-effective-UID process. Shards 3 and 4 were
cancelled by matrix fail-fast, not passing. Process purpose and security policy
remain unknown; no inference from its PID or apparent age authorizes removal.

### Engineering decisions

The Linux kernel documents that cwd link reads use ptrace credential checks and
procfs ownership can differ after protection/credential changes. These explain
possible mechanisms, not this process's established cause. Add one non-follow
directory-metadata observation after the existing denial, only with a valid PID,
an observed live state and remaining original deadline. Emit only whether its
owner matches the caller or root, plus sanitized unavailability; no names,
paths, command lines, exception text, new privilege or extra UID query. Reject
relative proc roots, non-directory leaves and invalid PIDs. These observations
remain outside identity, evidence, release and eligibility. Dead/unknown state,
no diagnostic context and expired time cannot cause an additional filesystem
query. Elapsed accounting includes the optional metadata read.

Test-before-code retained ten missing-field/helper failures and one no-context
pass with unchanged source/toolchain and a joined producer. All 34 focused old
and new controls then passed, including exact metadata observation, symlink and
invalid-PID refusal, missing state, no-context/deadline, stale-data clearing,
privacy, unchanged retention and elapsed time. Full owning and strict checks
belong to the new frozen candidate's external receipts; they are not inferred
from the earlier 255-case pass. Newest non-yanked prerelease resolved again to
4.0.0rc7; the explicitly addressed qualified runtime was verified, not replaced.

### Known limitations

The actual Linux procfs ownership and denial mechanism still need a new hosted
observation before a repair is selected. No platform visibility rule, creator
fence, deadline or removal predicate changed. Default delivery, installed
ordinary native ingress and per-repository execution adoption remain unfinished.
No project, host, cache or uncertain registration was retired.

### Controlled Linux reproduction admission

The local shell and independent Node runtime both report Darwin/arm64; neither
can establish a Linux kernel result. Add a real Linux-only control to this
existing retained-runtime test scope, not another service or an invented local
pass. A sole explicitly owned child first exposes a readable cwd, then changes
only its own dumpability through `prctl`. Test both a cwd inside the candidate
and a separate owned outside directory. Real psutil reads must reproduce
same-UID access denial and protected procfs ownership in both cases, while the
adapter retains unknown visibility. Enumeration is explicitly limited to that
known child for the control; this does not qualify full-host visibility or
identify the original PID 970.

The child has a dedicated process group, bounded handshakes, a self-expiry alarm
and joined stdin completion; timeout force is restricted to that owned group.
Its admission/result receipt remains in the retained fixture. The normal Linux
CI input must execute these cases. Darwin compiles the literal fixture program
but declares the Linux cases skipped; those skips are not Linux passes. A
privileged/unsupported caller is not silently treated as a successful denial
control. No existing positive cleanup assertion is changed or weakened.

### Review finding — whole-frame deadline

The independent owner found that readiness followed by blocking `readline`
did not bound the whole response. The extracted unchanged pattern reproduced
four real pipe-control failures: an unterminated response survived until the
four-second child watchdog, slow partial output outlived the requested frame
deadline, oversized output was accepted and EOF was misclassified. The normal
ready response passed. All producer outcomes were retained and joined.

Use one absolute monotonic deadline with nonblocking short raw reads, a
1,024-byte frame bound and explicit EOF/oversize/deadline failures. Preserve
exclusive stdout ownership, restore descriptor flags, and reject trailing
frames. Both Linux protocol stages share the same three-second deadline;
partial reads and later stages cannot restart it. The watchdog remains a
separate last-resort child lifetime bound. Six real POSIX controls now pass,
including an already-expired deadline and descriptor-mode restoration. These
transport results do not establish a Linux kernel or full-host visibility pass.
