---
work_package_id: WP03
title: Supported creator adapters and automatic ingress
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-008
- FR-009
- SC-002
- SC-004
- NFR-001
- NFR-002
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this
  WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human
  explicitly redirects the landing branch.
subtasks: []
history: []
authoritative_surface: src/specify_cli/workspace_lifecycle/
create_intent:
- src/specify_cli/workspace_lifecycle/adapters.py
- src/specify_cli/workspace_lifecycle/events.py
- src/specify_cli/workspace_lifecycle/service.py
- tests/workspace_lifecycle/test_adapters.py
- tests/workspace_lifecycle/test_events.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/workspace_lifecycle/adapters.py
- src/specify_cli/workspace_lifecycle/events.py
- src/specify_cli/workspace_lifecycle/service.py
- tests/workspace_lifecycle/test_adapters.py
- tests/workspace_lifecycle/test_events.py
tags: []
tracker_refs: []
---

# WP03: Supported creator adapters and automatic ingress

## Requirement coverage

FR-003, FR-004, FR-005, FR-008, FR-009

## Objective

Supported creator adapters and automatic ingress. Follow the accepted spec/plan and preserve all other owners. Primary branches advance only through PRs.

## Validation

Targeted test surface: `tests/workspace_lifecycle/test_adapters.py` and `test_events.py`; `tests/specify_cli/git/test_destructive_guard.py`, `tests/git/test_delete_branch_ref.py`, `tests/architectural/test_destructive_op_routing.py` and `tests/architectural/test_layer_rules.py`. Include production completion/startup wiring, hung adapter timeout, bounded event callback and worker dispatch; event enqueue never scans or retires synchronously.

Commit acceptance tests before implementation; verify the new checks fail on the planning base for the intended missing behavior, then pass on the candidate through the production interface. Preserve existing historical red/green receipts for already implemented WP01 cases; do not manufacture a new red by weakening behavior. Run focused checks during iteration and the unchanged required `make test-fast` plus affected subsystem gates before publication; no full heavy suite locally.

Actual automatic supported completion and non-lane retirement under creator fence; shared/protected/dirty/ignored/nested/active preservation; managed API unavailable is retained; branch results separate.

Run focused checks while iterating; freeze source and docs before required baseline/subsystem gates and independent review. Keep exact receipts outside the validated candidate. Never substitute a report, event or mocked refusal for an actual required positive production-path result.

## Completion

Source delivery, runtime admission, installation and cleanup outcomes are separate. Retained/unknown states remain explicit. Do not mark done until this package’s proof and owning workflow are complete.
