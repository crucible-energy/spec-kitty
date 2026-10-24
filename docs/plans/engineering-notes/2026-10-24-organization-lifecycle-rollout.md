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
