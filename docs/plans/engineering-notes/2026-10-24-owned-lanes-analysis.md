---
title: Owned LANES Analysis Admission
description: Canonical target-checkout admission and isolated report transactions.
doc_status: active
updated: '2026-10-25'
---

# Owned LANES Analysis Admission

## User Experience Findings

The published RC7 migration can truthfully classify a mission as `lanes` while
analysis recording and prerequisite inspection still refuse it as unsupported.
That prevents repairing a stale analysis through the supported command. A
separate real-checkout regression found report-only recording blocked by a
merge marker in the shared primary checkout even though its selected target
checkout was idle.

A wider integration run exposed Darwin Git's zero-errno text (`Undefined error: 0`)
not matching the existing `Success` retry spelling. The narrow classifier
now recognizes both at the same registry path, retaining bounded retries and
refusal of actual nonzero read errors.

Hosted CI subsequently found two pre-existing formatting failures outside the
initial changed-file check: the sampler frame helper and the doctor CLI golden
option table. CI's pinned formatter corrected both. Complete syntax-tree
comparison proves no semantic change; focused frame and golden-surface checks
cover their contracts. The full-tree formatter check now passes with that
same pinned formatter, rather than relying only on local changed-file checks.

Normal RC7 recording also bypassed the report-only canonical-policy dirty-input
guard. Both owned modes now use the same existing transaction. A real linked
checkout without primary governance could incorrectly inherit unrelated
ancestor governance; root discovery now honors its existing Git boundary.

The test launcher previously swept sibling run directories based on age.
Age does not prove release: a live run or its only failure evidence can be old.
The replacement reserves a fresh private leaf and records a private owner
manifest before execution. A separate live-child regression proved that even successful same-process
completion with an unchanged manifest cannot release another runtime. The
launcher now records outcome DATA and retains the exact leaf until the existing
lifecycle owner independently proves runtime release. Eligible owner cleanup
remains separate; failures and uncertain ownership stay retained. No sibling age sweep runs at startup.

## Engineering Decisions

Analysis and prerequisite inspection explicitly admit `single_branch` and
`lanes` through the existing sole ownership validator. The fact still binds the
mission, target branch and owned root. Implementation, finalization and merge
retain their separate topology restrictions; lane and coordination checkout
placement guards remain in force. No mission metadata restamp or report
freshness bypass is introduced.

Report transactions request worktree-local Git operation detection from the
existing canonical detector. Primary transactions still inspect the primary
Git directory; linked transactions inspect their own Git directory. General
status callers retain the existing conservative common-directory behavior.
Real worktree tests preserve primary index bytes, staged/unstaged/untracked
work and merge markers while exercising the actual recorder. Target operation
markers still refuse. The owned-root freshness regression exercises the
existing owned-aware workflow gate with a distinct common repository root.

The broader review exposed invocation violations in the older published
integration baseline. The target owner subsequently published the accepted
sealed `OperationRoot` implementation at `fda26ce35`. Reconciliation preserves
that existing canonical minter, checkout/branch/writing binding, close-contract
type refusal and negative tests. The earlier local `OperationCheckout` port
is superseded and removed; it must not become a second custody authority.
Old-head test results do not qualify this reconciled candidate. The target's
current execution-evidence refusal remains intact.

The separate [RC7 qualification recipe](../../../tools/qualification/README.md)
starts from the exact published sdist. It applies a checked patch to the actual
RC7 currency callback rather than substituting the older integration runtime,
whose `next` implementation predates that callback. This preserves RC7's report
and charter semantics while fixing its root binding. The integration lineage's
existing owned-aware report semantics remain distinct.

The helper uses a shorter versioned namespace so older launchers cannot sweep
new retained evidence. Owner permissions are restored under restrictive umasks. The explicitly
authorized architectural/doc parity repair removes the unsafe age-sweep
requirement; it enforces retention and no outcome-driven unlink instead.
Actual live-child, PID-reuse, collision, altered-manifest and failed-run tests
exercise custody; no synthetic fixture grants global cleanup authority.

The explicitly delegated CI change enrolls only the existing workspace-lifecycle
source and tests in the existing aggregate row. Baseline formatting, completion
manifest and documentation failures exposed by hosted checks are repaired
without weakening guards. Historical notes move to the canonical engineering
notes section; the unpublished platform-control test remains explicitly
unpublished rather than a broken link or invented passing evidence.

## Known Limitations

This is a narrow repair on the owned 4.x integration branch, not a release to
the fork's 3.x default branch or publication of a new package-index release.
Published RC7 lacks earlier owned-aware analysis signatures already present
in this integration lineage. An isolated source-derived distribution must
record its exact revision and dependency identity; it must not be described as
the unchanged published RC7 wheel. Migration and release convergence remain
with their existing owners. No shared installation is patched in place. The local RC7 recipe remains
limited to its six declared analysis files; the integration-only Darwin
zero-errno retry correction is separate and does not widen any authority.

The launcher cannot establish external-service release or change pytest
per-test teardown. Retained run records are explicit recovery obligations,
not a claim that all workspace cleanup is implemented or that all held files
can be reclaimed. The existing lifecycle owner confirmed that published
`fda26ce35` has no admitted release API for arbitrary pytest directories; its
Git `OperationRoot` cannot be cast into temp-resource authority. That owner
retains qualification of the missing producer/runtime-release adapter through
existing WP09. Automatic eligible closeout remains an acceptance obligation;
this source repair does not close it. The old failed and passing proofs remain retained.

PDB HELD/v5 custody, Source recovery, authentication, admission and runtime
effects are outside this source repair. A passing synthetic regression grants
no source access or production readiness. External receipts retain exact
frozen inputs, failed and passing runs, and owned resource closeout obligations.

## Hosted integration hygiene follow-up

Hosted checks on `9392aa4` found three inherited integration publication gaps:
missing workspace command references, one stale derived pinning-inventory entry,
and the unused five-line `invocation.checkout` re-export. The existing owner
released the exact reviewed source and supported retiring that unreleased alias;
no retained consumer was known in its program, and the actual default and
published RC7 lack it. This is a bounded source/program search, not an exhaustive
claim about every external ecosystem. The canonical `OperationRoot` and resolver,
actual dispatch/close/executor source and negative tests remain intact. No dummy
caller or dead-module allowlist is introduced.

The inventory is regenerated by its canonical derivation. Its sole added row
already has the established no-dependency disposition for a surviving workflow;
no rule is dropped or regenerated away. CLI references are rendered from the
actual registered surface with the canonical generator; rendering help does not
activate a workspace worker or grant cleanup. These publication corrections
remain separate from subsequent LANES-finalizer route qualification.


## Required-help capture correction

### User Experience Findings

Independent incremental review found six empty help fences after a generator
run reported success. The old capture discarded return codes and stderr;
a controlled child exiting 9 with partial stdout reproduced the false success.
The original six child failure causes remain unknown because those diagnostics
were not retained. A new actual-reference guard detects all six, with a planted
empty/nonempty control to verify the guard itself.

### Engineering Decisions

Required help now rejects nonzero exit, empty normalized output, invalid UTF-8,
timeout and spawn failure. CLI failures retain exact stdout/stderr and command
metadata in a private owner-released diagnostic directory. Both reference
bodies render completely before either target is written. Captures use the
canonical console entry point under the generator's exact interpreter instead
of running a package-manager synchronization for each command. The existing
owner approved the additive nonempty-reference guard without weakening other
checks. Complete reference regeneration uses successful real captures only.

### Known Limitations

The original discarded failures cannot be reconstructed from later successful
help commands. Pre-rendering prevents capture failures from partially updating
the pair; it does not make two filesystem writes one crash-atomic transaction.
Diagnostic directories remain retained pending owner release. This closes a
documentation capture defect, not LANES finalizer qualification, runtime
adoption, production authority, or PDB HELD/v5 custody.


A strict regeneration subsequently refused `context mission-show --help` with
an actual global slash-command input-change diagnostic. This is a newly observed
cause, not proof of the six original discarded failures. Rendered help now uses
the supported consumer-scoped private asset root during qualification, preserving
shared agents' assets and the existing currentness guards. Hosted routing checks
also exposed an inherited canonical-local-authority migration mismatch: the
registry/scrub/workflow mirrors had the new subsystem but the active local JSON
selection lacked it. The delegated owner approved matching additive local
source/test enrollment and explicit YAML input for YAML-transcription guards.
Consolidation fixture corrections remain with the existing lifecycle owner.

The non-main-registry fixture now supplies its actual synthetic router and
registry explicitly to the real selection function; changing the retired
legacy default no longer redirected the canonical authority. Its original
lost-routing negative remains, and all 21 focused routing/fixture checks pass.
The first applied fixture exposed a missing module-level `sys` import in the
negative branch; that failure is retained and the import corrected. Local
review-base probes replay exact GitHub-observed PR metadata; they are not
hosted execution evidence. The actual default branch has no 4.x registry, so
an ordinary default-main comparison is not a valid integration-base proof.

A normal nested CLI help invocation still runs the existing global-asset
startup owners. The failed shared-scope attempt has no before/after asset
manifest, so it does not establish that those assets stayed unchanged or
identify which producer caused the observed drift. Subsequent rendering is
consumer-scoped; no shared asset cleanup, rollback or runtime replacement is
attempted by this repair. PDB Store/HELD/v5 state is outside these help calls.


The full affected-subsystem run retained failures before publication. Self-review
found that a subsequent render targeted nested temporary paths while the seed
references were root-level, so those generated copies lacked the existing
hybrid envelope. The canonical `wrap_with_markers` restored the exact current
hand-authored prefix around byte-identical successful generated blocks. No help
was manually filled. Its receipt records both hashes. The private test environment
also lacked lockfile-pinned `defusedxml` 0.7.1; the exact lockfile wheel checksum
was verified before installation after the original producer joined. Router
mapping pins still require explicit source-epoch review for the already approved
source glob; changed-source refusal remains mandatory. The published RC7 private
agent-root gap is documented separately from integration-source isolation.

The delegated source review confirmed that removing only the approved new
router glob reproduces its exact previous SHA. The new epoch is admitted in
the canonical extractor; source, migration, workflow contracts and inventory
are regenerated from that reviewed source. All 19 original workflow definitions
remain exact apart from the single approved filter addition. Existing pinned
source and changed-workflow refusal controls remain intact. JSON ordering is
retained for review without changing the extractor's computed object. The full
failed run classifies exactly six envelope failures, 29 missing-dependency
failures and six source-epoch failures; none are silently relabeled as passes.

## 2026-10-25 — Provision the hosted native-validation compiler

### User Experience Findings

The actual CI module failed before native validation because its Linux runner
had no `zig` executable. Local compiler-backed results and a successful source
merge do not establish that the hosted environment can execute the same suite.
The lifecycle owner's interruption and recovery fixture corrections are joined
in this lane; their distinct frozen checkout and all PDB HELD/v5 state remain
preserved.

### Engineering Decisions

Under the delegated owner's exact workflow approval, the existing CI module
job alone obtains official Zig 0.16.0 for Linux x86_64 in a private runner-owned
temporary directory. The pinned SHA-256 must pass before extraction, and the
executable version must pass before PATH publication. No missing-tool skip,
new job, changed status, timeout budget or test filter is introduced. Canonical
workflow contracts and inventory are rederived from that exact reviewed source;
router source and changed-source refusal remain unchanged. A focused wiring
regression protects the condition, target, checksum and verification order.

### Known Limitations

The wiring regression checks the provisioning contract; it does not execute a
Linux compiler on macOS. Actual hosted CI-module execution and the full owning
consolidation/terminus checks still gate merge. Runner resource disposal is owned
by the hosted job lifecycle; this step does not prune shared caches. Local test
resources and raw failures remain in the external recovery bundle. This source
fix grants no runtime admission, production authority, PDB source access, fit or
unhold.

## 2026-10-25 — Preserve actual hosted failures and repair publication metadata

### User Experience Findings

Hosted checks at the combined source passed the Linux compiler provisioning
step, then exposed additional integration gaps: missing required frontmatter in
the lifecycle correction note, a filter still naming removed tracked doctrine
assets, four Linux creator-operation refusals, and archive classification of
live planning files in the stacked branch. Fail-fast canceled sibling module
jobs; they are not passing or complete owning-suite evidence.

### Engineering Decisions

The existing migration owner released only the correction note's frontmatter
for this lane. Add its canonical description and active document status while
preserving the exact body bytes. The migration owner retains the Linux
creator-operation diagnosis and archive/live-in-stack boundary. The stale-filter
repair requires exact delegated workflow review and source-epoch rederivation;
no dummy asset, missing-tool skip or changed-source waiver is appropriate.

### Known Limitations

The published combined source remains red. Local passes and successful compiler
setup do not replace actual Linux suite completion. Failed logs, canceled job
identities, prior planning/status history and both source revisions remain
retained. No archive policy, source authority, runtime admission, HELD/v5, fit
or unhold effect follows from these publication repairs.

The delegated owner approved deletion of exactly the retired doctrine filter
after independently confirming zero tracked files remain there. Its reviewed
router preimage is f24918e; the result is b2816b9. The canonical extractor epoch,
source contracts and inventory are regenerated from that exact source. All
other live filters, jobs, statuses, triggers, budgets and changed-source refusal
controls remain intact. The hosted CI-module job was canceled by fail-fast
before completion: its successful compiler provision is not a passing suite.

The interrupted affected run has no retained terminal result. Its focused
unchanged-source diagnostic joined with 642 passes and two concrete failures:
the scrub's routing-documentation mirror still carried the retired glob, and
a corpus-selection positive row still expected that retired path to trigger.
The delegated owner approved matching mirror removal and moving that existing
row into the negative truth table. Total rows, assertion functions and all live
positive controls are preserved; the retirement is tested, not silently omitted.
The original partial and diagnostic logs remain failures, separate from the
completed mandatory baseline. Final affected checks retain individual test IDs
so an interruption need not discard their diagnostic identity.

The completed affected run retained 5,254 passes, 40 declared skips and one
failure in the derived native stopped-child cancellation control. Its imported
five-poll trigger never established that the child had stopped before requesting
cancellation. The failing PID bytes were not logged, so empty early capture is
an explanation to test, not a reconstructed fact about that run.

The delegated owner approved replacing only this derived control's trigger with
a kernel CLD_STOPPED witness observed using WNOWAIT. It must match the captured
owned leader PID before the test can pass; an unrelated stopped child cannot be
credited. Cancellation, terminal reap, group disposal, PID parsing and liveness
assertions remain, with unchanged limits and test count. The historical source
fixture and its digest remain untouched. Invalid PID bytes now have explicit
bounded diagnostics. This corrects a missing test precondition, not production
process-ownership logic or a claim that the original transient is fully explained.

The stop-only focused rerun retained an actual empty PID capture. A stopped
producer has written its bytes, but cancellation can precede the parent's next
pipe read; this is not proof that already-retained data was lost. Refine the
same control using the existing synchronous retained monitor: it reports actual
owned preview bytes and returns no failure, while the original cancellation
probe still requires the kernel stop. The final parsed PID must still match the
witness exactly, so partial or incorrect captures remain visible failures. No
output is reconstructed, no limit widened, and no production path changed.
Both failed control runs remain retained beside the delegated v2 review.

## October 25 — canonical review and private invocation discipline

### User Experience Findings

A deep help inspection was accidentally invoked without the private consumer
scope. Its bootstrap refreshed 182 generated command files across 13 non-Codex
agent roots and eight cache lock/stamp nodes during the observed call window.
Shared Codex and agent skill files were outside that window. Exact post-call
bytes were preserved externally. A subsequent independent read found another
writer had regenerated those commands with the official RC7 marker; that writer
is unattributed. No restoration, shared pruning, processing-tier configuration,
Store access, fit or unhold was attempted.

The explicit owned-review path also correctly refused the integration checkout
because its branch differs from the mission's recorded write branch. Addressing
the actual Source checkout resolved ownership selection. A private home reached
through the system temporary-directory alias then failed the material-input
symlink guard; explicitly addressing the identical physical home resolved that
caller error without weakening the guard.

### Engineering Decisions

Use a mandatory external invocation wrapper that fixes the isolated executable,
canonical private home and consumer asset scope, and clears inherited source
imports. Future governance commands must not depend on remembering those flags.
Retain both shared-asset observations; never restore old generated files over a
concurrent writer or active consumer without owner-supported reconciliation.

The normal owned `move-task` review API applied the independently reviewed WP13
verdict with a distinct reviewer actor and a generated review artifact. No force,
skip, raw event edit or manufactured prompt was used. The old twelve WP rows,
prior event prefix, acceptance metadata and six tested source/test hashes remain
identical. This leaf-review operation does not advance the full mission past its
separate stale-analysis guard. Runtime query, bounded source approval, publication
and installed adoption remain different facts.

### Known Limitations and Retained Obligations

No pre-call content snapshot exists for the accidental shared bootstrap; the
original bytes cannot be claimed restored or lossless. The observed snapshots,
private governance state, failed invocations and exact command observations are
retained under this mission's external receipt root. The existing migration owner
has the incident and active-consumer boundary; shared repair remains unperformed.

The complete archive/lifecycle owner gate passed 353 tests. The exact combined
source passed the mandatory baseline with 2,452 tests and five declared skips;
all owned producers are joined. The subsequent review child changes only
canonical review metadata. Actual Linux visibility failures, full-mission
analysis freshness, remaining hosted gates, default-branch delivery and runtime
adoption are not closed by those passes or by WP13 approval. HELD/v5 and existing
Source/native owner lanes remain preserved.

## 2026-10-25 — Owned plain-lanes planning finalization

### User Experience Findings

The real owned-checkout finalization CLI accepted the single-branch fixture but
refused a registered plain-lanes Mission with `OWNED_TOPOLOGY_UNSUPPORTED`.
Analysis already admitted that shape. This prevented an ownership amendment to
unstarted work without contributing protection for active work.

### Engineering Decisions

Give only planning finalization a dedicated closed topology set and continue
through the canonical resolver and existing transactional finalizer. Preserve
all other lifecycle topology sets. Registered-checkout tests cover read-only
validation, unchanged invoking repositories, coordinated-topology refusal,
branch and staged-index guards, active lane/history preservation and removal
refusal. The failing real CLI reproduction is retained separately from its
passing amended-source checks. No status, lane or authority record is manually
edited in an actual Mission.

### Known Limitations and Retained Obligations

Source conformance is not installed-runtime qualification or PDB workflow
adoption. Exact final test and immutable artifact receipts remain external so
recording their results cannot change the validated source. The existing
migration owner retains the actual Linux process-visibility diagnosis; its
hosted failure is not resolved by this planning fix. The fork default-branch
release convergence and downstream dependency gates remain separate obligations.
HELD/v5, current Source/native lanes and processing-tier preferences are preserved.

The broader source gate exposed two cycle-fixture setup failures before the
finalizer was invoked. An immutable pre-change archive reproduced both: the
fixture tried to allocate a successor while the predecessor still occupied the
same lane. Its synthetic setup now completes the predecessor through the test
status API before allocating and normally claiming the successor. The two WPs
remain history-started, and the original exact cycle/refusal/no-write assertions
are unchanged. No allocator or occupancy predicate was weakened. The initial
117-pass/two-failure result and frozen baseline failures remain retained.

A wider documentation run passed its ordinary checks but could not set up two
wheel tests without the declared test extra. Running those exact two tests with
the declared dependencies resolved the setup error; it does not convert the
original errored aggregate into a passing run.

## 2026-10-25 — Close exact hosted clock and corpus-root findings

### User Experience Findings

Hosted architectural checks found the new active-history fixture imported and
called the standard wall clock outside the canonical clock module. This was an
introduced test-source defect; the earlier functional passes did not exercise
that architectural contract. Another guard still required the retired doctrine
root after the separately approved router retirement. The actual corpus run
also exceeded its unchanged 120-second limit at 120.921 seconds; its cause is
not established by that single timing result.

### Engineering Decisions

Use `kernel.clock.now_utc_iso` in the fixture, preserving real event ordering
and the same history assertions. Keep both clock guards unchanged. Remove only
the obsolete `.kittify/doctrine/` data-root expectation under the existing native
delegate's exact patch approval; all live roots, independent assertions, jobs,
registry, selection and budgets remain unchanged. Retain the original hosted
failures and their exact source/job bindings. Do not treat a subsequent pass as
a diagnosis of timing variance.

### Known Limitations and Retained Obligations

The lifecycle owner's reviewed denial observation is now joined, with its full
255-test owning result and the combined baseline retained separately. It has not
yet explained the actual Linux process or granted retirement. The corpus timing
failure remains open pending source-backed diagnosis and unchanged-gate proof.
PDB's actual read-only next/validate-only calls passed with all 49 Mission files
and checkout state preserved; this does not approve WP09 or supply missing
issuer/serving inputs. The released pre-change fixture extraction was archived,
all 35,360 file/link entries verified, then the exact private tree retired.
Its source, failure logs and restore manifest remain recoverable externally;
no shared cache or worktree was pruned. HELD/v5 and Fast-mode preferences stay
preserved; no fit, unhold or canonical source operation occurred.

## 2026-10-25 — Reduce canonical index ordering work without caching

### User Experience Findings

A generated-data profile of the real reference Project reader found repeated
full Path comparisons inside the canonical Mission index walk. With 20 and
40 generated Missions, the existing path performed 3,780 and 18,840 such
comparisons. A deterministic regression through the public filesystem resolver
reproduced that ordering cost while asserting the independently computed Path
order. This does not establish the cause of the separate hosted 120.921-second
corpus result.

### Engineering Decisions

Keep the same single filesystem enumeration primitive, fresh metadata reads,
resolver precedence, injections and missing/ambiguous-identity behavior. Compute
each child name's platform-normalized ordering key once; all entries have the
same parent, so this preserves full Path order and leaves actual directory
spellings untouched. Do not add a result/index cache, literal-handle shortcut,
parallel resolver, timeout change or admission exemption.

The same generated fixtures returned identical Project output hashes afterward.
Index builds, metadata reads and actual resolver-call counts stayed equal;
full Path comparisons fell to zero. The regression passed, as did all 175
context tests and the focused canonical-walker checks. Final qualification is
recorded externally against frozen inputs.

### Known Limitations and Retained Obligations

These are generated local operation-count and output-equivalence observations,
not a hardware or wall-clock speedup, full-corpus timing success or production
reader/admission receipt. Actual new-head CI remains required; the 120-second
budget is unchanged. Actual Windows execution was not performed locally.
Failed profiling setup attempts and the partial fixture are retained separately
from successful reads; all profiling producers are joined. The lifecycle owner
has captured the published Linux failure and retains its cause/repair lane.
The public run was preserved until that capture. HELD/v5 and current Source/
native custody remain untouched, with no fit, unhold or faster-tier change.

## 2026-10-25 — Review the actual control deadline and release inventory

### User Experience Findings

The migration owner's Linux mechanism control bounded pipe readiness, then used
a blocking line read. That did not bound receipt of a complete frame. The owner
reproduced the gap with actual owned pipe children and supplied a correction;
Root reviewed its exact bytes independently before final qualification.

The first release comparison covered tracked `src/` files only. A separate
repository-wide tracked-native inventory identifies fourteen additional paths;
the earlier zero native rows do not establish native release closure.

### Engineering Decisions

Keep the correction in the existing migration lane: one absolute monotonic
deadline, bounded nonblocking reads, explicit EOF/size/trailing-data refusal and
restoration of the prior descriptor mode. Retain isolated child environments,
independent watchdogs and joined cleanup. Do not change production visibility
or retirement predicates to make a control pass.

Preserve the earlier inventory and add a hash-bound correction. Archive the
three owned generated profiling repositories, verify every regular file against
the archives, and check for open consumers before retiring those exact private
trees. Raw failures, profiles, original bytes and restoration manifests remain
available; no shared cache or worktree was pruned.

### Known Limitations and Retained Obligations

The migration owner released `53afc55c` with 272 passing tests, two explicit
Linux-only skips, strict checks and joined execution. Its twenty added production
statements were covered without exclusions. Merged qualification and actual
new-head Linux checks remain required. Local review is not Linux execution or
complete-host visibility. Release inventory is not asset,
dependency or packaging closure. The separate PDB Host composition still needs
a genuine owning installation and independently current authority; a healthy
source-unproven incumbent or an Auth provider module does not supply either.
HELD/v5, Source's exclusive Store custody and processing-tier preferences remain
unchanged; no fit, unhold, source query, enrollment or runtime action occurred.

## 2026-10-25 — Separate governance scope from the native-path test profile

### User Experience Findings

The first combined baseline inherited an explicit consumer asset scope and
private home from its runner. Eleven tests intentionally exercise native agent
destinations and one requires no explicit home override. Those inputs changed
their subject: the run completed with twelve failures, 2,440 passes and five
skips. Every tracked source hash remained unchanged.

### Engineering Decisions

Correct only the external test runner. The canonical pytest configuration
already establishes isolated per-worker home and configuration roots before
collection; use that test profile without inherited consumer overrides. The
private consumer wrapper remains mandatory for governance CLI invocations.
All twelve exact failed cases then passed on the same frozen source. Retain
both runs and repeat the required combined baseline with the corrected inputs;
do not change assertions, production paths or enforcement to obtain a pass.

### Known Limitations and Retained Obligations

The failed aggregate remains failed; the twelve-case diagnostic is not the
full required gate. Final results must bind the frozen candidate and actual
test environment externally. Private failed-run assets remain retained; no
global command rollback, shared cleanup or processing-tier change is implied.
