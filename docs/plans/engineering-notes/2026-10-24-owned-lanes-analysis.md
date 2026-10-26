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

## 2026-10-25 — Bind Linux control expectations to observed metadata

### User Experience Findings

The actual Linux inside/outside controls both reproduced zero dumpability,
unchanged UID credentials, cwd access denial and unknown visibility. They then
failed a hardcoded claim that the PID directory becomes root-owned. Directory
metadata does not establish dumpability or retirement authority. The original
whole shards remain failed, and their opaque-process diagnostics remain open.

The mandatory fast baseline does not collect the lifecycle owning directory.
Its passing result cannot substitute for that directory's qualification. The
Source branch also lacks this integration's resolver and finalization changes,
so its complete owning result alone is not a test of the combined candidate.

### Engineering Decisions

Integrate the existing owner's reviewed `58164a96` correction without changing
production eligibility or any real protection and lifetime assertion. Expected
metadata now comes from independent, non-following stat of the exact live child.
The released Source gate passed 272 cases with two explicit Linux-only skips;
it is Source-specific conformance, not execution of the corrected Linux body.

Freeze the combined code and documentation before publication checks. Execute
the original six-file strict scope, the distinct mandatory fast baseline, and
one full owning-directory run against this combined tree. Retain raw results
and input identities externally. This additional owning run is justified by
changed CLI dependencies, rather than repeating an identical validated tree.

### Known Limitations and Retained Obligations

Actual new-head Linux controls and the remaining opaque-process failures are
still required. Unknown visibility retains state; a passing metadata comparison
cannot supply missing creator, host, ingress or rollout evidence. The standalone
workflow registration is delivered separately in PR121, not runtime adoption.
Preserve earlier failures and recovery archives. HELD/v5, Source Store custody
and the platform-held Native lane remain unchanged; no fit, unhold, shared
pruning or faster processing follows from this source integration.

### Combined strict-check discovery

The combined strict scope followed an existing ledger CLI test callback and
reported its missing return annotation. Substituting the exact pre-correction
adapter test from `24856332` reproduced the same error, so the directory change
did not introduce it. Give the always-raising callback its truthful standard
library `NoReturn` annotation; keep its body, assertions, strict flags and the
original six-file scope. Check the helper explicitly too. Retain both original
failures and the import-profile investigation; a narrower type-check traversal
must not silently hide this imported test contract.

The owner subsequently recovered the earlier check's retained import metadata:
its explicit acceptance/event targets were checked, but the imported ledger
helper had `ignore_all` set. That historical result is not proof of this
helper's strictness. The original six targets plus the helper now pass as seven
explicit targets, and the real CLI inventory-failure/ledger-preservation case
passes unchanged. The earlier configuration's complete inherited environment
was not retained; do not assert an unproved historical cause for its import
classification or hide the original failed combined check.

## 2026-10-25 — Separate workflow conformance from ambient visibility

### User Experience Findings

Both corrected Linux nondumpability controls passed on `af2c4128`: inside in
0.030 seconds and outside in 0.025 seconds. Their full shards still failed five
and two cases respectively. The opaque same-UID process observations supplied
neither complete visibility nor permission to remove a workspace. Production
correctly retained it, but workflow tests assumed that their unrelated receipt,
recovery or dispatch checks would always reach retirement on a shared host.

### Engineering Decisions

Keep production observers, eligibility and deletion unchanged. Give the existing
real-Git workflow fixture an explicitly synthetic observer; live-holder cases
select the actual provider, and the actual Linux kernel controls remain intact.
The fresh-worker workflow covers clear, held and unknown observations, preserving
the branch, checkout and absence of recovery effects for both refused cases.

Propagate only this test observer through the canonical distribution launcher.
Preserve its absolute interpreter, `-I`, exact source-selection statements,
module invocation, arguments and real child/join behavior. Reject a changed
launcher shape instead of silently using another interpreter profile. Check
the preserved bootstrap independently against its original AST and leave other
modules unchanged. No production flag, environment override or observer API is
introduced.

Independent review found that the first test adapter matched only legacy `-m`
commands, missing the actual isolated distribution bootstrap. Its focused run
failed four held/unknown cases while eighteen passed; retain that failure.
Replace the obsolete interception with the canonical launcher seam, rather than
removing isolation. Use the public runtime module for strict typing instead of
treating an imported worker alias as an exported API. Preserve the original
strict-check errors and avoid suppressions.

Check the canonical runtime launcher explicitly as an eighth strict target,
in addition to the original six and ledger helper. The exercised observer
selection covers the parent and its first dispatched worker, not arbitrary
self-respawn generations inside that child. No general inheritance claim is
made for unexercised worker generations.

At late-holder cuts, begin with the controlled workflow prerequisite, restore
the actual provider before starting the real holder, and require that the
intended boundary was entered. Retention must come from that boundary's runtime
check; an earlier unrelated refusal cannot satisfy the test accidentally.

### Known Limitations and Retained Obligations

Synthetic workflow conformance is not full-host visibility, deployment or
cleanup qualification. The actual live-holder tests establish preservation at
their cut; unknown visibility does not become a positive holder-detection claim.
Unknown processes remain unknown, and the worker remains uninstalled/disabled.
Retain the original shard failures, independent review, focused failures and
frozen final receipts. Source still owns the canonical Store, HELD/v5 remains
unchanged, and neither fit, unhold, Native platform-gate bypass, shared pruning
nor faster processing is authorized by this test repair.

## 2026-10-25 — Keep review recovery tied to the recorded claim

### User Experience Findings

The B88 Linux lifecycle shard passed. The execution-context shard instead
reported one failure: an existing guard test expected obsolete instructions
to edit the planning pin. The production diagnostic already directed recovery
through the recorded claim or validated legacy base, explicitly prohibiting a
planning-pin change. Both production text and stale test predate this integration
base; the failure is retained rather than classified as a new runtime regression.

### Engineering Decisions

Replace the stale assertions and misleading test name with the actual safety
contract. Preserve real Git, the unreadable reference and the refusal; require
reachable-ancestor recovery guidance, the correct checkout, and the prohibition
on moving the planning pin. Also verify the refusal creates no replacement
metadata. Do not change production behavior or restore unsafe advice to satisfy
an obsolete assertion.

### Known Limitations and Retained Obligations

The failed automatic run remains failed, with unfinished shards cancelled.
Retain its raw failure and successful Linux evidence separately. Qualify the
next frozen candidate through normal checks; do not dispatch the cancelled old
candidate just before a new source push. This test-only correction grants no
runtime, cleanup, Source, Store or HELD/v5 authority.

## 2026-10-25 — Preserve project intent across the charter cutover

### User Experience Findings

The next Linux charter shard exposed two distinct problems. The earlier RC7
upgrade intentionally reset selections equal to released defaults and explicit
empty opt-outs, but the migration workflow accepted that reset without preserving
this project's original selection. Separately, a manual workaround enabled
automatic commits project-wide when an owned status transition needed an atomic
commit. The original paradigm parity guard correctly detected missing configured
intent. It remains unchanged.

The no-op render fixture still required the retired `.kittify/doctrine` tree
after its legitimate move to `.kittify/charter-packs`. Local ignore rules cannot
hide edits to tracked files; the fixture must establish actual tracked artifact
bodies and then prove its status check detects a real edit.

### Engineering Decisions

Restore exactly the previously configured eight paradigms, explicit empty
mission-step-contract/glossary selections, and `agents.auto_commit: false`.
Use the canonical explicitly rooted activation/YAML writers after qualification
in a real linked-worktree fixture. Verify input identities, pointer-drift refusal,
unrelated-field preservation, idempotence, and unchanged shared-checkout bytes.
Apply the activation plan before changing its config-pointer input. Do not alter
the migration ledger or the intentional released reset contract.

For future upgrade intake, retain the exact configured selection and agent
preference before applying the migration. Review semantic changes separately
from structural relocation before accepting the upgraded project. Deliberate
post-cutover selections must survive read-only migration detection; an applied
ledger is not permission to discard restored user intent. Worktree recovery
must use explicitly rooted canonical APIs: the agent-config CLI resolves the
shared repository-root checkout and is unsuitable for this lane-local repair.
Reject unknown agent fields before using a writer that only preserves known
agent fields.

Keep the owned transition's atomic-commit guard. Use the existing per-command
`move-task --auto-commit` override when that transition is intended, rather than
enabling persistent automatic commits. Exercise the real linked-worktree
command both without the override (refusal without effects) and with it
(committed transition), preserving the false preference and other checkouts.

Resolve the render fixture's artifact root through
`kernel.doctrine_root.resolve_doctrine_read_root`. Require tracked artifact
bodies, preserve both actual render calls, and add a tracked-file mutation
witness. This follows the canonical/legacy read contract without weakening
the cleanliness assertion or hardcoding another path.

### Known Limitations and Retained Obligations

The earlier Linux run remains failed; cancelled shards are not passes.
Prepared/applied recovery receipts, original failures, independent owner review,
and final frozen-candidate validation live outside the checkout. Exact project
roots are distinct from any required transitive doctrine closure. This repair
does not install the lifecycle worker, complete PDB package acceptance, or grant
Source/Store/serving authority. HELD/v5, the Native platform hold, and standard
processing remain unchanged. Retain the small recovery fixtures until reviewed
closeout; no shared pruning or duplicate owner lane is introduced.

## 2026-10-25 — Bound render fixtures to their actual committed input

### User Experience Findings

The recovery's committed-input check passed both real render cases, parity and
command-override tests, but one additional fixture setup exceeded the unchanged
240-second test deadline during checkout: 50 passed and one setup error. The
first checkout also took 145 seconds. This is not a successful gate or evidence
of a content regression; retain the failed log and all four exact clone pins.
The cause of the transient checkout delay remains unproved. Full historical
object copying is nevertheless unnecessary work in this committed-tree fixture.

### Engineering Decisions

Use Git's shallow transport for the exact current commit, retaining the full
committed tree, fresh ignore configuration and real tracked-file status checks.
Require exact HEAD equality, actual shallow history and no alternate object
store. The render contract does not inspect historical commits. No deadline is
widened, artifact is excluded, assertion is skipped or failed run relabeled.
This is a fixture input reduction, not a production Git/lifecycle change.

### Known Limitations and Retained Obligations

Historical ancestry is intentionally not qualified by these render tests;
ancestry-dependent lifecycle tests retain their own real-history fixtures.
Requalify the changed fixture and exact committed inputs before publishing.
Retain failure evidence and review this new fixture change independently. No
global filesystem improvement or cause of concurrent capacity changes is claimed.

## 2026-10-25 — Retire the repaired fixture's formatter exemption

### User Experience Findings

Current Linux architectural CI caught a stale formatter exemption for the
now-formatted render fixture: 798 passed, one skipped, one failed. The existing
shrink-only ratchet correctly refused to retain an unnecessary exclusion.
Keep that failure as the reproduction, separate from passing local test results.

### Engineering Decisions

Remove only this exact path from the formatter exclusion list, as the existing
ratchet requires. Do not restore formatting debt, add an exception, raise the
baseline or change any test, CI workflow, hook, budget or status expectation.
The fixture becomes subject to the already-established formatting requirement.
Recheck the named ratchet and mandatory baseline before publication.

### Known Limitations and Retained Obligations

Other current-head CI jobs still need their actual terminal outcomes. A local
formatter check does not substitute for the architectural ratchet or passing
Linux control evidence. No Source/Store, authority, resource-pruning or runtime
behavior changes are introduced by retiring this obsolete exception.

## 2026-10-25 — Reach consolidation behavior without targeting protected history

### User Experience Findings

The current consolidation shard finished with eight failures, 1,254 passes and
three expected failures. Eight fixtures still requested protected main/develop
targets, so PR-only admission correctly refused before the intended claim,
reconciliation, teardown or reviewed-fix boundary. Those tests were not proving
their intended behavior. Preserve the actual failed run and cancelled shards.

### Engineering Decisions

Opt these consolidation cases into the existing real integration-target adapter,
which pins a separate protected primary. Keep the legacy builders' defaults and
all protected-target tests unchanged. For the mixed canceled-content builder,
use its existing target parameter and the same primary-pin helper. Do not change
production target policy, enable an escape hatch or relax any status/content
assertion.

The explicit-target resume case now uses distinct eligible integration targets:
one stale metadata target and one actual explicit target. Require successful
consolidation, exact approved-commit reachability, unchanged stale target and the
shared harness's unchanged-primary check. Protected bookkeeping cannot be
laundered by an explicit override; retain that separate negative control.

### Known Limitations and Retained Obligations

These are real Git/CLI fixture corrections, not production branch-policy changes.
Run every affected file, the protected-target controls and the formatter ratchet,
then the mandatory baseline. Existing larger-scope Linux results remain failed
until current-candidate CI proves the correction. Canonical Store exclusion,
HELD/v5, no-fit/no-unhold and the Native platform hold remain unchanged.

## 2026-10-25 — Make recovery preservation controls non-vacuous

### User Experience Findings

A scoped audit of remaining legacy-builder callers found five recovery controls
that accepted refusal and preserved content, but could stop at unrelated
protected-target admission. Through the existing real CLI entry points, new
phase-precondition assertions failed all five cases before the fixture repair.
Commit those red controls separately and preserve their raw outputs.

### Engineering Decisions

Use the same existing integration-target adapter in these three test files.
Retain the new refusal-cause checks and every original no-op, branch-survival,
dirty-content, untracked-collision and ignored-file preservation assertion.
The separate real primary is pinned and checked by the shared CLI harness.
Do not alter legacy-builder defaults, production recovery or protected-branch
policy. The remaining explicit protected-target controls and read-only dry-run
fixture intentionally keep their original target choices.

### Known Limitations and Retained Obligations

The red controls prove the previous unrelated-refusal shortcut; they do not
establish a production data-loss event. Validate both the recovered paths and
protected-target negative controls before publication. Old red CI and local
environment failures remain distinct retained evidence; passing controls do not
grant installed runtime, cleanup or canonical Store authority.

## 2026-10-25 — Separate native fixture profiles from platform qualification

### User Experience Findings

The next independent Linux module run reached existing native validation tests
that assumed Darwin candidate capture, a dyld/process-group producer, or a Mac
Docker Desktop container fixture. Those assumptions obscured the declared
`PlatformUnqualified` boundary with unrelated setup and downstream failures.
The native guard is unchanged from the integration base; passing governance
checks does not qualify the missing Linux recipe implementation.

### Engineering Decisions

Declare the profile at the narrow capture/producer/container helper boundary,
before its platform-specific effects. Keep raw executable construction, source
integrity, platform-neutral commands and native Linux sampler controls live.
Missing prerequisites on the declared Darwin/Desktop profile still fail; there
is no opportunistic missing-tool skip, endpoint replacement or image pull.
Add real Linux capture and verify refusal controls through the raw candidate
executable, retaining Git/file state, request bytes and namespace absence checks.
Independent review caught two witness gaps: a dangling destination symlink and
empty repository directories. Use no-follow destination absence plus a separate
repository namespace comparison rather than weakening the existing snapshot.
The duplicate-JSON parser case remains platform-neutral: parsing precedes the
native platform guard, so it must assert `DuplicateField` on Linux too. A
generic refusal would allow an unrelated platform refusal to hide parser drift.

### Known Limitations and Retained Obligations

These are fixture-context classifications, not Linux recipe qualification or a
release waiver. Native-local-validation WP03's Linux, coverage and subsequent
platform requirements remain open. Actual Darwin functional results and actual
Linux refusal results must be reported separately. No production guards, CI
workflow, protected branch, budget, Source Store or native authority changes are
part of this repair. Preserve the independent failed Linux run and every skipped
context as unqualified; cancelled shards are not passing evidence.

Root-owned old render clones may be retired only after terminal ownership,
byte-preserving archives, actual restore checks and fresh no-holder evidence.
Retain raw failures, source pins and recovery receipts. Filesystem free-space
changes include concurrent producers and are not wholly attributable savings.

Closeout verified and retired twelve released original clones across the two
bounded recovery runs, retaining archives and actual restored source-pin proofs.
The full-clone restore initially failed because the standard safe extraction
filter added owner-write permission to three read-only Git pack files. Preserve
that failure; restoring exactly the archived modes made the full byte/mode
comparison pass without relaxing it. All owned recovery producers are joined.
The retained Source writer's qualified recovery has priority over new native
test allocations. Resume validation only after its custody release event and a
fresh capacity check; no Source Store or process intervention belongs here.

The first bounded actual Darwin candidate-file validation completed with
72 passes and three explicit skips: the two Linux-only refusal controls and
the filesystem's unsupported non-UTF-8 filename case. Retain those limitations;
this does not qualify Linux or the remaining native modules. The source and
repository HEAD stayed unchanged during the check. Its observed peak private
allocation stayed below the admitted budget, with all observed descendants
joined. Keep the exact tested executable, source/compiler binding and raw
result artifacts for the remaining owning-module validation.

Closed the current run's private derived caches and three older Root-only
checker cache prefixes after terminal-producer and no-holder checks. Source,
installed qualified runtimes, logs, fixtures, archives and all recovery evidence
remain retained. Source's rejected cache paths and shared caches were excluded.
Fresh ordinary capacity must decide publication readiness; these measured cache
removals do not establish exclusive attribution for filesystem-wide changes.

## WP14 — Post-squash review-source reconciliation

### User Experience Findings

PR #120 delivered the exact tested tree to the existing integration branch.
The lifecycle owner then legitimately refreshed an orphaned planning pin.
WP11's implementation was already in the squash, so the new committed window
contained only planning/status work and correctly failed the ordinary
`OWNED_IMPLEMENTATION_MISSING` guard. A fake code touch would hide the missing
history binding instead of repairing it.

The first three-case reproduction also exposed a test mistake: owned review
does not permit an explicit auto-commit override. That failed run is retained.
After removing only that unsupported option, the ordinary refusal control
passed and the two explicit-source cases failed because the new CLI capability
did not exist. The failing-first test commit precedes the source repair.

Adversarial local Git fixtures then exposed two candidate defects. Mutable
task/mission authority could mint a source fact despite committed-scope
equality; the public approval control still refused and was not an approval
bypass. Separately, assume-unchanged and skip-worktree hid changed owned bytes
from Git status and allowed a public `for_review` transition. A relative
`./app.py` spelling reproduced that admission defect until both validators
used identical pattern normalization. These are private candidate findings,
not claims about installed runtime exploitation or production approval.

The broader task-command run exposed two validation obligations: its help
snapshot needed the two additive flags, and a fixture's bare `python` hook
could not run because the private direct-interpreter profile omitted the
selected virtual environment from PATH. The hook then exited zero without
performing its mutation. The unchanged hook regression passed after binding
PATH to the advertised interpreter; the original two-failure run remains
retained and is not a passing gate. Both the existing changelog and exact help
fixture were admitted through the owning canonical scope workflow before edits.

### Engineering Decisions

The explicit `--review-source-commit` and `--review-delivery-commit` pair
supplies local review-source evidence only. The ordinary current planning and
claim-base guards still run. The canonical minter inspects full immutable IDs,
identical source/delivery trees, actual current/target ancestry, and exact
authored task/mission Git entries. An original present WP claim outranks its
planning fallback; read errors or invalid claims cannot become absence.

Original and current event history must bind the same attempt. Reclaims,
rejections, changed scope, unavailable history, changed implementation entries
and dirty owned paths refuse. Git entry modes matter; a dereferenced file hash
cannot substitute for a symlink or executable-mode identity. Existing dirty,
reviewer, regression and event-write guards remain mandatory.

The inspection shares one deadline and bounded blob reader. It mints an
immutable in-process fact, not a receipt or verdict. It neither verifies PR
acceptance nor grants owner release, cleanup, default-branch delivery or
installed runtime adoption. The already accepted explicit dispatch/close
custody implementation still needs separate newest-RC7 package propagation.

Committed authority, index entries and working bytes are compared independently
of Git status. Hidden index flags, conflict stages, altered entry identities,
unsupported types and executable-mode drift refuse. Regular-file reads use a
held no-follow descriptor; symbolic links compare link text, not target data.
The reader checks parent directory types and named-entry stability. Inspection
uses a ten-second deadline, 100,000 index-entry limit, four-MiB per-file limit
and 64-MiB aggregate inspected-content limit; these are eligibility bounds,
not a filesystem lock or subsequent-effect authorization.

### Known Limitations

This is a candidate repair. The development-runtime boundary run passed 37
cases, and the subsequent normalized-pattern plus durable reviewer/verdict
checks passed two more. Earlier failed fixtures, controller interruptions and
confirmed RED cases remain retained separately. The controller's disappearing
temporary-directory race was corrected without changing product behavior.
Owning regression/typing/architecture and baseline gates, independent review,
normal PR publication and actual newest-RC7 installed Source replay remain
required. Focused development results do not establish those later stages.
The core/parser/migration/invocation and selected architecture run passed
1,060 tests with one declared performance skip, and strict typing passed all
six selected production modules. The full task-command and baseline gates
must finish under the corrected interpreter profile on the final candidate.
Five terminal private bytecode caches were retired after exact ownership,
no-holder and source-recovery checks: 175,980,544 allocated bytes. Their source,
Git fixtures, raw logs, failed runs and receipts remain retained.
HELD/v5 and all other owners' source, Store, processes and recovery state are
unchanged; validation uses only declared private Git fixtures.

## 2026-10-26 — Retire two earned frontmatter formatter exemptions

### User Experience Findings

PR122 at source0d2 failed the existing Linux formatter-debt ratchet: 798
architectural checks passed, one skipped, one failed. Its exact two findings
were the now-formatted canonical frontmatter implementation and owning unit
test. The focused unchanged guard reproduced locally: five passed, one failed.
Keep both original failures; the earlier formatting check did not prove this
shrink-only configuration invariant.

### Engineering Decisions

Import Source's supported WP14 ownership/analysis amendment0eb645 through a
normal feature merge, preserving all14 task-state and full event bytes. Remove
only `src/specify_cli/frontmatter.py` and `tests/tasks/test_frontmatter_unit.py`
from the formatter-debt exclusion list, as its existing rule requires. No new
rule, baseline increase, test edit, CI/hook/budget change, guard waiver or
restored formatting debt. Both files now remain enrolled in the ordinary gate.

Product/runtime/test bytes remain exactly0d2; the already reviewed immutable
R6r2 wheel and installed Source-shaped qualification retain their original
source pins, including the measured undeclared-gate skipped distinction. Reuse
only their unchanged relevant byte/dependency/profile scope. Freeze this exact
config/docs increment, rerun the actual unchanged ratchet and required baseline,
and retain final results externally under the existing governance-recovery
evidence root so recording validation does not mutate the tested candidate.

### Known Limitations and Retained Obligations

New-head hosted checks, exact config-diff/owner review and normal PR122 delivery
remain mandatory. No earlier receipt is relabeled as a newer-head full gate.
Broader retired-API SDK failures remain red/unqualified; actual Source canonical
replay, default-main/package convergence and organization adoption remain
separate. Preserve HELD/v5, no fit/unhold, frozen runtimes, Source producer and
all recovery evidence; no shared-resource or runtime action is authorized.

## 2026-10-26 — Keep the independent detail-reader matcher faithful

### User Experience Findings

The same0d2 hosted contract-tools run exposed a stale test-side reader and
expected table: 2272 passed,37 skipped,one failed. The reviewed canonical writer
normalizes both path and authored pattern to close the demonstrated hidden-byte
inspection gap, while the reference still left its pattern raw. Unchanged local
matcher checks reproduced one failure/42passes. New explicit leading-dot and
Windows-pattern cases against the unchanged reference then failed four checks
with46passing, including the unmutated-reader controls. Keep these real REDs.

### Engineering Decisions

Normally import Source's exact two-file reference/test ownership amendment26c132
without changing existing dirty bytes, task states or full event history. Keep
this reader independent: normalize its pattern as well as its path, retain
fnmatch platform behavior, directory-prefix segment bounds and exactly one
leading-dot removal. Do not call the writer to derive expected values. Explicit
cases preserve the original path divergences from the raw Git commit guard and
add the authored-pattern divergences and negative sibling-segment controls.

Add a path-only-normalization mutant reproducing the old reader; both its clean
control and planted-fault detection must pass after the repair. Grow the explicit
mutation-registry count by exactly this one added mutant, preserving every old
mutation. No production/runtime matcher, commit-guard policy, contract schema,
assertion strength, required check, baseline or installed runtime changes.

### Known Limitations and Retained Obligations

The formatter increment's required baseline2452pass/5skip, docs/lint/3507-file
format/lock/diff checks are terminal/joined on their exact retained source; that
receipt is not proof of these later reference edits. Run the full affected reader
and its corpus caller, unchanged architectural guards, final baseline and docs
checks on the new frozen inputs before normal PR122 publication. Existing0d2
runtime/installed qualification keeps its original pins and narrow scope.
Current-head hosted checks and independent final source review remain gates;
Source canonical replay/default-main/adoption are not inferred. Preserve all
failed receipts, HELD/v5, Source custody and frozen runtimes; no fit or unhold.

## 2026-10-26 — Qualify the corpus in its supported primary context

### User Experience Findings

The expanded local reader/corpus/guard run completed1055pass/1skip/10fail;
retain the full FAILED result. Exact JUnit separates247changed-reader passes
and81unchanged architecture passes from the untouched Reality caller's
727passes/1skip/10fail. Its strict drift scan refuses data resolved outside the
selected linked checkout; Project records551outside-root fallbacks. Local
Project190.776s/combined203.649s also exceeded the unchanged120s limits.

### Engineering Decisions

Keep the boundary fail-closed: MissionStatus.load documents a PRIMARY checkout
argument. Read-only named-entry diagnostics return paths inside originalprimary
but outside this linkedRoot, followed by strict ReadDirOutsideRoot, without ever
importing the changed detail reference. A separate explicit archived-source
control verifies all366executed product module bytes against pre-WP14e848 Git
objects, including actual originalfrontmatter; it reproduces the same typed
boundary without Rootfile/ref/status mutation. This is NOT an installed SDK or
whole-corpus performance pass. The initial control's mistaken loaded-module
assertion stays failed; corrected instrumentation reports actual module usage.

The existing Source owner independently ratified the supported qualification
route. Do not duplicate CI with another repository clone or silently use the
dirty live primary. Finish exact-input mandatory local checks and require actual
NEWHEAD hosted PRIMARY-context fullcorpus, contract and protection checks before
merge. No skip, floor, cold-index, fallback, timing limit, test or policy is
weakened. Reuse only unchanged relevant original runtime/owning gate evidence.

### Known Limitations and Retained Obligations

Local linked-corpus qualification remains FAILED; the two local timing bounds
remain unqualified and are not attributed away by the narrow functional control.
Root's existing validation lane retains the linked-profile/timing investigation,
with Source owning the canonical primary-context boundary. Next review event is
WP14 delivery or the next relevant corpus increment, whichever comes first.
The proposed standalone validation clone was withdrawn before materialization;
no new checkout/resource was created. Actual Source replay, default-main,
runtime/admission and general SDK compatibility remain separate. Preserve
HELD/v5, no fit/unhold, Source custody, all failures and frozen runtimes.
