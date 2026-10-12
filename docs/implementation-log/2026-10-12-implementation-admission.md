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

- The public admission command and shared safety correction are not implemented yet. Acceptance tests are being run against the unchanged compatible base.
- No actual Temet lane allocation, LoRA training, model evaluation, or production serving is established by these host checks.

## Validation And Delivery

Observed RED on the unchanged production base: the public start accepted a second WP while another WP in the same lane was `in_progress`, and accepted the predicted workspace on an unexpected branch. The additive preflight returned the existing structured `USAGE_ERROR`. All three desired assertions failed; there were no collection or fixture failures. The first run took 61.65 seconds. Formatting and lint pass for the acceptance file. Snapshots compare retained bytes directly; no charter hashing helper is reused for unrelated Git/file integrity.

Pending: separate RED commit, implementation, focused tests, strict typing, formatting, relevant architecture checks, independent review, PR delivery, and immutable consumer qualification.
