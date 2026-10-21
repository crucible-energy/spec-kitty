---
work_package_id: WP06
title: Owned code-kind acceptance and strict closeout
dependencies:
- WP05
requirement_refs:
- FR-005
- FR-007
- FR-008
- SC-003
- C-001
- C-003
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks:
- T006
phase: Closeout recovery
history: []
authoritative_surface: src/specify_cli/acceptance/
create_intent:
- tests/acceptance/test_owned_code_kind.py
execution_mode: code_change
owned_files:
- src/specify_cli/acceptance/gates_core.py
- tests/acceptance/test_owned_code_kind.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/specify_cli/cli/commands/agent/test_owned_checkout_move_task.py
- tests/integration/migration/test_wp03_advance_to_approval.py
- src/specify_cli/lanes/claim_base.py
- tests/lanes/test_claim_base.py
tags: []
task_type: implement
tracker_refs: []
---

# WP06 — Owned code-kind acceptance and strict closeout

## Objective

Carry the actual admitted OwnedCheckout through the existing canonical normalized-WP kind query and both acceptance no-code decisions. A code mission in an owned linked checkout must not be classified from another checkout or skip matrix/negative-invariant checks. Preserve existing genuinely planning-only behavior and the original five independent approvals.

## Validation

Commit a real linked-checkout red regression before the source repair. Distinct same-slug primary/owned metadata and an owned-only code mission must resolve correctly. Exercise the actual acceptance summary/diagnostic to prove missing matrix evidence remains a blocker, not a planning-only skip. Run full affected acceptance tests, required unchanged baseline, relevant routing tests, configured lint/type and changed-statement coverage; obtain independent review. Retain failures and immutable qualification evidence externally.

## Constraints

No primary-copy mutation, guard relaxation, lenient acceptance, manual status event, forged matrix evidence, global installation or deployment. Contract/planning artifacts are authored through the mission planning workflow and generated artifacts through existing canonical writers. Local source acceptance and owning PR merge/adoption remain separate.

## Retained-claim review recovery

Strict closeout reproduced OWNED_IMPLEMENTATION_MISSING after genuine later planning finalization moved the mission pin beyond this retained implementation. Reuse the existing canonical per-WP immutable claim-base ref for the implementation review window; preserve validation of mission planning and claim ancestry/currentness, real owned-file changes, primary protection and missing/invalid-ref refusals. Never rewind the mission pin, fabricate implementation churn, or edit status events. Commit a real linked-checkout regression before repair; validate the complete owning move-task module plus required gates and independent review.

The existing canonical claim-base reader gains strict error handling for the owned-review consumer only; legacy callers keep their current non-raising behavior. Genuine ref absence preserves the existing validated planning-base compatibility path. A malformed or unreadable present ref must refuse, never masquerade as historical absence.
