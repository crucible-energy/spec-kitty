---
work_package_id: WP07
title: Typed operation custody and closeout integration
dependencies:
- WP05
requirement_refs:
- FR-006
- FR-007
- FR-008
- SC-005
- C-001
- C-003
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks:
- T007
phase: Closeout recovery
history: []
authoritative_surface: src/specify_cli/core/owned_mission.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/core/owned_mission.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/cli/commands/dispatch.py
- src/specify_cli/cli/commands/profile_invocation.py
- tests/specify_cli/invocation/cli/test_owned_checkout.py
- tests/integration/test_owned_lifecycle_acceptance_finalize.py
- tests/integration/test_owned_lifecycle_acceptance_e2e.py
- tests/integration/test_owned_analysis_implementation_cli.py
tags: []
tracker_refs: []
---

# WP07 — Typed operation custody and closeout integration

## Objective

Close the actual sole-minter/typed-custody violations exposed by the expanded architecture gate in the original Op routing repair. Mint a dedicated opaque operation-root fact in the existing canonical owned-mission authority, using the existing ownership validator and unchanged protection policy. Carry that fact through dispatch, internal payload and generated close contract; raw paths remain only at the documented CLI claim boundary. Preserve explicit read-only primary selection, protected-branch refusal, legacy no-explicit-custody/non-Git context errors, branch drift checks and primary immutability. This grants no mission ownership or runtime authority.

Correct the stale owning integration fixtures to test the real supported contract: exact resolver accounting under an explicit posture, and missing-analysis refusal for supported owned implement separately from unsupported owned review. Preserve all no-effect/content-read/unknown-frame assertions and existing accepted-analysis positive coverage. The expanded owning gate also exposed a stale model-provenance refusal assertion: require the actual earlier rejection of an unproven resolved-model claim, preserving exit, event-stream and primary-state checks; never fabricate model execution evidence. Do not relax production or architectural gates, widen allowlists or rename parameters merely to evade scans.

## Validation

Retain the preceding full failing gate receipts as red architecture proof. Add focused behavioral tests for unforgeable operation custody and preserved read-only primary compatibility before implementation; show they fail against the prior source. Run full invocation subsystem, acceptance and affected owned lifecycle integration, required unchanged baseline, relevant architecture, configured lint/type, and at least90percent changed-statement coverage. Independent canonical review and owning PR publication required. Original five approvals stay immutable; WP06 matrix fix remains separately owned.

## Constraints

Same existing checkout, feature-first/PR-only delivery. Preserve active owners and native Zig changes. No global installation, backlog retirement, cloud/DNS/service/Store mutation or deployment retry.

### Reviewed source-retirement reconciliation (2026-10-25)

Dependency commit 9fdcc64b6aa7354312318229e5a3bd3610c4ae1e removed the obsolete five-line invocation/checkout.py re-export shim (prior Git blob85fefb859). Its actual authority was already src/specify_cli/core/owned_mission.py, which remains this WP's authoritative_surface and owned source. Remove only the retired literal from the current execution map so canonical literal-path validation describes existing source. The original authored scope and approval remain in Git/status history; this planning reconciliation neither restamps that approval nor adds implementation authority. Do not recreate the shim or falsely add create_intent. All recorded approval/status/event bytes must remain unchanged through supported finalization.
