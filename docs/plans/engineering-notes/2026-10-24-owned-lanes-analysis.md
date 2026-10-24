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

Hosted CI subsequently found two pre-existing formatting failures outside the
initial changed-file check: the sampler frame helper and the doctor CLI golden
option table. CI's pinned formatter corrected both. Complete syntax-tree
comparison proves no semantic change; focused frame and golden-surface checks
cover their contracts. The full-tree formatter check now passes with that
same pinned formatter, rather than relying only on local changed-file checks.

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

## Known Limitations

This is a narrow repair on the owned 4.x integration branch, not a release to
the fork's 3.x default branch or publication of a new package-index release.
Published RC7 lacks earlier owned-aware analysis signatures already present
in this integration lineage. An isolated source-derived distribution must
record its exact revision and dependency identity; it must not be described as
the unchanged published RC7 wheel. Migration and release convergence remain
with their existing owners. No shared installation is patched in place.

PDB HELD/v5 custody, Source recovery, authentication, admission and runtime
effects are outside this source repair. A passing synthetic regression grants
no source access or production readiness. External receipts retain exact
frozen inputs, failed and passing runs, and owned resource closeout obligations.
