---
title: Lifecycle integration acceptance corrections
description: Source and fixture corrections for lifecycle integration, with retained failure evidence and explicit qualification limits.
doc_status: active
type: explanation
audience: software-engineer
updated: 2026-10-24
---

# Lifecycle integration acceptance corrections

## User Experience Findings

Hosted PR120 checks exposed inherited feature-integration regressions. WP04 correctly added PR-only target validation but older rollback, content and attestation success fixtures still use main/develop, so they abort before their intended checks. Four selected exact-source tests failed before repair: rollback, unprotected-target positive, internal Op field completeness, and canonical Windows detection. External failed fixtures and logs remain retained.

## Engineering Decisions

Keep the strict canonical protection policy and real failure injections. Distinguish actual protected/default-branch and historical references from positive feature-consolidation targets before editing. A successful feature fixture needs a distinct real primary branch whose ref remains unchanged; changing a branch label alone is insufficient.

The inherited direct-ref cleanup predicate delegates Windows detection to kernel.paths.is_windows without changing its signalling or join behavior. OpStartedEvent.checkout_branch is internal custody identity; the closed public status schema deliberately omits it. The shared real-record fixture carries a nonempty private branch, so existing schema rejection, omission and mutation checks exercise that boundary rather than only adjusting a field-set assertion.

## Known Limitations

The fixture migration, complete owning validation and independent review are still in progress. These corrections do not qualify automatic cleanup, source delivery to actual default, runtime installation or organization execution adoption. Root separately owns generator and CI-selection corrections. No other owner's checkout, process, cache or host resource was removed.

The first bounded correction passed 57 focused checks: canonical OS-door scan, real native-ref lock/timeout/descendant controls, and non-timing public Op contract rows including the new private branch value. Ruff and configured mypy for the production file passed; the final formatter-only change was executable-AST-equivalent. These focused results do not replace the required final baseline, remaining fixture checks, independent review or hosted gates. The failed four-case reproduction and successful private validation tree are retained under this owner's closeout obligation; no automatic cleanup claim is made.

The first shared-fixture rerun passed five controls but left three intended positive paths refused on develop. Canonical primary resolution also treats a checked-out common primary name as primary; adding a main ref alone did not change that. The reviewed positive builder defaults and four rollback targets now use feature/integration, while deliberately protected-main/target-override references remain unchanged. Both fixture families create a distinct real main at their initial base, and actual feature consolidation checks that its primary ref does not advance.

The same original rollback/positive failures, a real post-mutation exception, and canceled-content controls then passed all eight selected cases in 94.71 seconds; all four frozen fixture hashes were unchanged during the run. Remaining historical crash/resume and protected-success expectation cases still need semantic review and broader required gates. No mass literal replacement was performed, and no production protection source was changed.

A separate source-compatibility observation remains open: the pristine published RC7 runtime lacks the consumer asset-scope seam available in the current fork. Private SPEC_KITTY_HOME alone is not proof that every agent-file destination was private. Prior shared destinations lack a complete pre/post manifest; their effects are unknown. Further governance/startup CLI calls await an admitted consumer-scoped latest-source qualification through the existing release owner; no installed-wheel overlay, shared rollback or unqualified preservation claim is used.

The four-file diagnostic at 52c725c9c passed 37 and failed 13. Those failures separated older protected-primary success/diagnostic assumptions from a crash setup that disabled an older protection preflight. Current tests retain deliberate primary inputs, require strict PR-only refusal despite hatch/config/status/retention choices, and assert exact refs/reflogs and useful source stay preserved. The recorded-bookkeeping target override and dry-run JSON diagnostic remain independently checked. Protected-primary cleanup is not made to succeed locally; actual eligible retirement after delivery remains the lifecycle creator's separate acceptance surface.

The crash fixture now executes a real feature consolidation, injects a fault after the actual mutation phase and hard-kills the rollback door with exit 137. No protection check is disabled. The next run passed 48 and failed two: the commit_to_target fixture already contained code on main, so its refusal must preserve that prior content; and a newly protected target after the real crash lacked an abort remedy. The existing strict preflight now adds only a conditional instruction to inspect saved state and use the guarded abort command, explicitly saying this refusal does not undo earlier mutations. No protection or release decision changes.

The corrected frozen source/task set passed 64 named rollback/protection/crash/single-branch/target-preflight cases in 238.35 seconds, including actual abort restoration and no-effect refused resume. Every frozen file hash matched at terminal disposition; source Ruff/format and strict mypy passed. Remaining original hosted cases, required baseline/owning checks, canonical scope refresh and independent review still gate publication. Current test outcomes are not source/default delivery, installed runtime adoption or automatic closeout proof.

Self-review found that the broad generic fixture change introduced a duplicate-main failure in the original workspace-lifecycle acceptance case. The failed one-case reproduction is retained. Restore the exact generic builder defaults and repository initialization, and use the existing opt-in feature_landing adapter only for the reviewed positive crash/rollback/feature cases. This preserves unrelated callers and deliberate protected-primary tests; no policy guard is weakened. The original hosted replay still had 27 failures out of 67 and remains an open finish obligation, not a green gate.

The release owner supplied a frozen private-consumer qualification packet after correcting a mutable conformance-support path. Independent verification matched all 2,075 recorded installed files, executable, patch and six logs; the earlier mismatch receipt is preserved. Actual real-mission validate-only passed with 12 WPs and no ownership warnings; mission status/events/task bytes and dirty primary snapshot were unchanged. This bounded planning API qualification does not qualify automatic cleanup or organization runtime adoption.

The narrowed crash/rollback/protection replay passed all 64 cases. The original workspace acceptance case no longer fails with duplicate-main; it reaches the independently reproduced ancestor-root/mission-not-found blocker, retained at its original location for Root's owning fix. The remaining original hosted fixtures now opt in through internal test-only imports. Specialized adapters reuse canonical primary pinning and existing frozen helper APIs; generic defaults and all deliberate primary/low-level simulations stay intact. Three specialized generic builders gain optional target parameters with unchanged defaults. The teammate remote advertises real main separately from its feature target. Persisted-target recovery distinguishes two feature branches and asserts the stale metadata target stays unchanged. No public import, product command, protection decision or assertion threshold was renamed or weakened.

The occurrence map now explicitly permits manual review of the scoped internal test-adapter imports, with product src/kernel import identities excluded. This authored classification amendment and same-owner dependency-ordered WP12 scope require canonical validation before publication; no status, verdict, event or approval payload is edited.

The 67-case frozen replay passed57/failed10 in501.26s; every one of45 file hashes matched at completion. Nine failures were the shared InterruptedConsolidate constructor still using generic primary targets; one was the rollback_harness precondition accepting a policy refusal before any consolidation state existed. Both now import the existing canonical opt-in builders. The rollback harness additionally requires persisted mutation state and actual rollback-door output before its failure can serve as a fixture precondition. Real resync kill/lock injection and all content/ref/refusal assertions remain unchanged. These ten exact red results are retained and the complete four consuming modules must run before acceptance.
