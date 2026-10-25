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
