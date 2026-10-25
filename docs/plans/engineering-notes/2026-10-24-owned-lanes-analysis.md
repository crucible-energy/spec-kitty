---
title: Owned LANES Analysis Admission
description: Canonical target-checkout admission and isolated report transactions.
doc_status: active
updated: '2026-10-24'
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
