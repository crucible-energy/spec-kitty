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
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
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

Actual automatic supported completion and non-lane retirement under creator fence; shared/protected/dirty/ignored/nested/active preservation; managed API unavailable is retained; branch results separate.

Run focused checks while iterating; freeze source and docs before required baseline/subsystem gates and independent review. Keep exact receipts outside the validated candidate. Never substitute a report, event or mocked refusal for an actual required positive production-path result.

## Completion

Source delivery, runtime admission, installation and cleanup outcomes are separate. Retained/unknown states remain explicit. Do not mark done until this package’s proof and owning workflow are complete.
