---
title: Qualified single-shard workflow registration
description: Records the registration-only manual workflow, exact selected-ref prerequisites, direct contract validation, and preserved runtime and custody boundaries.
doc_status: implemented
updated: '2026-10-25'
version_tag: internal
type: explanation
owning_workstream: organization-workspace-lifecycle
---
# Register the qualified single-shard continuation

## User Experience Findings

A cancelled reusable-matrix job could be retried, but its inherited failing
sibling cancelled it again before pytest. GitHub also returned 404 for the
qualified branch's existing manual workflow because it was absent from the
default branch. The first proposed full-file backport passed the default's
19 baseline tests but failed two direct workflow-catalog contracts: it added
an executor outside that older layout's gate model. Retain those failed results.

## Engineering Decisions

Register only the workflow-dispatch entrypoint on the older default branch.
Preserve the exact seven input definitions from the qualified canonical runner.
This anchor has zero token permissions, no checkout, helpers or test executor;
its one job exits 64 with an explicit unsupported-ref diagnostic. Do not add a
dynamic manual shard to the default's automatic coverage model, weaken its
catalog guards, or import the larger migration history to register a name.

The owning migration lane selects codex/owned-lanes-analysis only while it
resolves to reviewed 24856332d5bfd7a4ddd71bbcb561172889a4c7d9. GitHub loads that
selected ref's unchanged full workflow, helpers and registry. Independently
verify the resulting run head and one-job shape before proceeding. Run the
unchanged core_misc 4/5 then 5/5 registry rows sequentially in pr mode, without
a custom test filter. Selecting this older default must refuse, never fall back.

The selected workflow has no explicit token permissions. Recheck the actual
repository read-only default and disabled PR-review approval before dispatch;
do not infer contents-only inheritance or change settings. Exact-candidate
self-review and objective local checks follow Sam's direction not to wait on
Blacksmith or CodeRabbit; queued hosted jobs are not passes or approvals.

## Known Limitations and Retained Obligations

Registration is not default RC7 adoption, Linux control execution, complete
host visibility or a passing parent matrix. Verify actual registered identity,
selected-ref execution and exact JUnit cases after normal PR delivery. Preserve
failed/cancelled evidence and the platform-held Native lane without workaround.
Keep HELD/v5 and Source custody intact: no Store action, fit, unhold or faster
tier. Keep validation and resource-closeout receipts outside frozen candidates.
