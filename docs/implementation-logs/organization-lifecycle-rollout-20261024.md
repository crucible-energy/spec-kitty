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
