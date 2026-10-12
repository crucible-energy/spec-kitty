---
title: Implementation Admission
description: Owning host implementation log for read-only and safe lane admission.
doc_status: active
updated: '2026-10-12'
---

# Implementation Admission

## Objective And State

Provide read-only normal LANES implementation admission using the same allocation decision as real start. Preserve existing work, and refuse unsafe reuse before allocation, reconciliation, or context changes. Current compatible base: `5dd503eec09cb2b011619cb00b4812e997787136`, `fix/owned-analysis-implementation`; this increment does not establish default-branch release or Temet admission.

Owner: Samuel Goff. Implementation: Python Pedro, Op `01M4S13FKF2S2SBKMYH74M6P5M`. Independent review: the existing Temet workflow owner. Tracker: [issue 89](https://github.com/crucible-energy/spec-kitty/issues/89), assigned to Samuel Goff, native Feature type. P1 stabilization rationale is recorded in the issue; the Crucible fork has no priority labels, and none were added.

## User Experience Findings

- `resolve-workspace` intentionally reports placement without validating safe admission. Calling actual start merely to discover admission may install hooks, reconcile history, and refresh the context before claiming the requested WP.
- Normal LANES and single_branch have different workspace ownership. The existing single_branch occupancy guard is not applicable to a normal execution lane.

## Engineering Decisions

- Reuse the explicitly released existing checkout on `codex/implementation-admission-preflight`. Preserve the earlier recovery branch, other dirty lanes, the qualified installed runtime, and live corpus/model custody.
- Extract a read-only allocation decision from the current allocator, keeping route order, base decisions, and reconciliation behavior. Real allocation recomputes its decision; a previous preflight is advisory evidence, not a reservation.
- Add actual public-start regressions before production changes. Determine occupancy from canonical status for other WPs assigned to the same lane; a historical `current_wp` pointer alone does not establish an active owner.
- Reconciliation required is not equivalent to an unrecoverable ancestry refusal. Preflight cannot prove merge compatibility without performing the mutations it must avoid.

## Known Limitations

- Implementation is present but not yet delivered or independently reviewed. A preflight is an observation, not a reservation; claim authorization, dependency readiness, reconciliation compatibility, and post-materialization ancestry remain execution gates.
- No actual Temet lane allocation, LoRA training, model evaluation, or production serving is established by these host checks.

## Validation And Delivery

Observed RED on the unchanged production base: the public start accepted a second WP while another WP in the same lane was `in_progress`, and accepted the predicted workspace on an unexpected branch. The additive preflight returned the existing structured `USAGE_ERROR`. All three desired assertions failed; there were no collection or fixture failures. The first run took 61.65 seconds. Formatting and lint pass for the acceptance file. Snapshots compare retained bytes directly; no charter hashing helper is reused for unrelated Git/file integrity.

The separate RED commit is `9a30ac6d5` and is pushed to the explicitly selected `origin` branch. The first implementation run exposed an incorrect status-kind identifier, which was corrected. The next focused run passed all selected admission, base, recovery, coordination, and structural-seam controls. Expanded controls then exposed an uncaught existing `DirtyWorktreeError` on the additive preflight; it was corrected by matching the actual allocator's typed refusal boundary. Failed diagnostics are retained separately from successful evidence.

The safety correction reuses the existing lane-mate status reader in `checkout_occupancy.py`. It protects claimed, implementation, review, and blocked work regardless of actor, permits approved sequential reuse, and excludes the same WP for compatible resume. Cached Git topology is refreshed before identity validation. The shared cleanliness probe now uses Git's existing `optional_locks=False` contract so preflight does not refresh the index. The API contract, actual help-derived CLI reference, and public documentation describe the additive command and tightened refusal behavior.

Pending final frozen-candidate checks, changed-line coverage, self-review, independent review, PR delivery, and immutable consumer qualification. Final check receipts live outside the candidate so recording outcomes does not change the validated tree.

The broad gate exposed two intentional compatibility changes against the former warning-only implement contract. Updated controls preserve the advisory reader and review behavior, while implementation refuses other outstanding WPs, including identical actor strings. A separate public CLI RED captured VCS metadata changes before refusal and was committed as `d3ef4a605`. The shared planner now runs in the existing read-only claim preflight before planning and VCS writes.

Normal implementation holds the existing checkout claim lock across preflight, allocation, and claim. Its owning-repository input anchors missing-lane locks in the verified repository without creating a husk; existing checkouts cannot select a foreign lock authority. The lock-order and same-WP contracts remain intact. Public competing-start and held-lock controls passed in the focused iteration; final receipts must bind the subsequent ownership hardening and frozen candidate.

Remote integration checks exposed four candidate defects: direct imports bypassed the status facade, a now-formatted contract test retained its old formatting exclusion, completion data omitted the additive command, and this log lacked required frontmatter. The correction uses the existing facade, shrinks the stale exclusion, regenerates completion through the canonical command, and adds log metadata. No test invariant or validation threshold is weakened. Sam's explicit direction to replace hosted QA with local Zig tooling and a pre-commit hook is being grounded separately by the workflow owner; this admission increment does not introduce hosted enforcement or claim that replacement is implemented.

The owning structural lint also requires dated engineering records under `docs/plans/`; this log was moved to that sanctioned home with its history preserved. The independent reviewer reproduced an explicit-base reuse refusal after metadata mutation. Its public CLI regression failed on changed metadata and Git status, and was separately committed before the correction. Early claim preflight now receives the requested base and delegates its resolution and refusal to the existing shared seams before planning and operational-context writes. Repository-root planning retains its existing ignored-base semantics.
