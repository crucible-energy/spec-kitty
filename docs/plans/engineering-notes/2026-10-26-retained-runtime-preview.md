---
title: Retained runtime-state preview
type: explanation
doc_status: active
updated: '2026-10-26'
---

# Retained runtime-state preview

## User Experience Findings

Issue #60 retains real implementation and review history in an owned checkout
whose Mission is absent from the busy repository root. `next` can discover the
dossier, but the migration command had no explicit checkout binding. Its
pre-existing CLI rejected the new regression with `No such option:
--owned-checkout`. That is distinct from a history decoding or approval defect.
The pinned historical stream remains readable by the current canonical parser.

The old linked-worktree recovery guide suggested manually writing
`status_phase` with validation disabled. That does not establish history
custody or parity and is replaced with the bounded preview and an explicit
unresolved adoption boundary.

## Engineering Decisions

Reuse the sole owned-checkout validator and the existing runtime-state cutover
engine. The new explicit CLI arm requires a Mission handle and dry-run, accepts
the topologies already available to `next`, and passes the validated fact all
the way to the retained directory reader. It does not broaden any lifecycle
write capability, change topology, select a fallback history, or copy data into
the repository root. Non-owned calls retain their original payload and behavior.

The owned JSON labels the retained scope and denies canonical adoption. Real
Git fixture tests check content, heads and staged entries across the selected,
primary and sibling checkouts, including unrelated dirty owner work. Corrupt
history stays intact and produces an explicit failed preview result.

The first fixture had assignee data without any transition timestamp; the
existing migration correctly found no anchored seeds. That failure is retained.
A subsequent fixture-construction failure omitted required `execution_mode`;
it is also retained. The corrected synthetic fixture records an explicit
transition anchor rather than weakening the migration's provenance rules.

## Known Limitations

This increment supplies inspection, not live coordinated recovery or adoption.
It does not qualify historical approvals as fresh review, update an installed
consumer runtime, or establish default-branch delivery. Preview results must be
read even when dry-run exits zero. Existing Git-metadata mutex files may be
created; canonical history and metadata remain unchanged. Inputs are current
filesystem reads, not an immutable source snapshot.

Independent coordinating-owner review found that the command's help still
claimed exit zero meant successful verification, contrary to its existing
dry-run behavior. The help now explicitly requires result inspection; a CLI
help regression covers that wording. No exit semantics changed.

Self-review then found that the pre-existing dry-run summary intentionally
suppresses raw verification mismatches while seeds are unwritten. A real
synthetic altered-seed regression reproduced the missing diagnostic. The
owned-only `retained_verification` field now preserves exact pre-seed findings
and their anchored-runtime denominator; unavailable verification stays null.
The old non-owned payload and dry-run exit/summary semantics remain unchanged.

Root retains this source lane and its external run receipts through publication
and post-merge verification. The Source owner retains ordinary lifecycle/native
ingress work; Aletheia retains its active runtime and consumer recovery lane.
No Store, model, host, shared-runtime, HELD/v5, fit or unhold action is part of
this increment.
