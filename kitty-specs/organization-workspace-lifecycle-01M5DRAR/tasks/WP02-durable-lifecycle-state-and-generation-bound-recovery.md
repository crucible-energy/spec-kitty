---
work_package_id: WP02
title: Durable lifecycle state and generation-bound recovery
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-004
- FR-005
- FR-007
- FR-008
- SC-003
- NFR-001
- NFR-003
- SC-001
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this
  WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human
  explicitly redirects the landing branch.
subtasks: []
history: []
authoritative_surface: src/specify_cli/workspace_lifecycle/
create_intent:
- src/specify_cli/workspace_lifecycle/state.py
- src/specify_cli/workspace_lifecycle/policy.py
- src/specify_cli/workspace_lifecycle/coordinator.py
- tests/workspace_lifecycle/test_state.py
- tests/workspace_lifecycle/test_policy.py
- tests/workspace_lifecycle/test_coordinator.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/workspace_lifecycle/state.py
- src/specify_cli/workspace_lifecycle/policy.py
- src/specify_cli/workspace_lifecycle/coordinator.py
- tests/workspace_lifecycle/test_state.py
- tests/workspace_lifecycle/test_policy.py
- tests/workspace_lifecycle/test_coordinator.py
tags: []
tracker_refs: []
---

# WP02: Durable lifecycle state and generation-bound recovery

## Requirement coverage

FR-002, FR-004, FR-005, FR-007, FR-008

## Objective

Durable lifecycle state and generation-bound recovery. Follow the accepted spec/plan and preserve all other owners. Primary branches advance only through PRs.

## Validation

Targeted test surface: `tests/workspace_lifecycle/test_state.py`, `test_policy.py`, and `test_coordinator.py` (in that directory); existing authority regressions: `tests/kernel/test_atomic.py`, `tests/kernel/test_yaml_io.py`, `tests/kernel/test_locks.py`, `tests/kernel/test_locks_symlink_safe.py`, `tests/kernel/test_no_follow.py`; `tests/architectural/test_layer_rules.py`.

Commit acceptance tests before implementation; verify the new checks fail on the planning base for the intended missing behavior, then pass on the candidate through the production interface. Preserve existing historical red/green receipts for already implemented WP01 cases; do not manufacture a new red by weakening behavior. Run focused checks during iteration and the unchanged required `make test-fast` plus affected subsystem gates before publication; no full heavy suite locally.

Durable intent and corruption refusal; old generation/release refusal; replay and interruption; concurrent holds; no false cleanup completion.

Run focused checks while iterating; freeze source and docs before required baseline/subsystem gates and independent review. Keep exact receipts outside the validated candidate. Never substitute a report, event or mocked refusal for an actual required positive production-path result.

## Completion

Source delivery, runtime admission, installation and cleanup outcomes are separate. Retained/unknown states remain explicit. Do not mark done until this package’s proof and owning workflow are complete.
