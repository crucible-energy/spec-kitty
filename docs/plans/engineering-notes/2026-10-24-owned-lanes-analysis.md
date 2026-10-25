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
