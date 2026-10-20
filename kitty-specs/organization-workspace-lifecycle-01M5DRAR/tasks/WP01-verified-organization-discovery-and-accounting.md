---
work_package_id: WP01
title: Verified organization discovery and accounting
dependencies: []
requirement_refs:
- FR-001
- FR-002
- SC-001
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks: []
history: []
authoritative_surface: src/specify_cli/workspace_lifecycle/
create_intent:
- src/specify_cli/workspace_lifecycle/discovery.py
- src/specify_cli/workspace_lifecycle/inventory.py
- src/specify_cli/cli/commands/_organization_workspaces_doctor.py
- tests/workspace_lifecycle/test_discovery.py
- tests/workspace_lifecycle/test_inventory_cli.py
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/workspace_lifecycle/discovery.py
- src/specify_cli/workspace_lifecycle/inventory.py
- src/kernel/git_topology.py
- src/specify_cli/cli/commands/_organization_workspaces_doctor.py
- src/specify_cli/cli/commands/doctor.py
- tests/workspace_lifecycle/test_discovery.py
- tests/workspace_lifecycle/test_inventory_cli.py
- tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py
tags: []
tracker_refs: []
---

# WP01: Verified organization discovery and accounting

## Requirement coverage

FR-001, FR-002

## Objective

Verified organization discovery and accounting. Follow the accepted spec/plan and preserve all other owners. Primary branches advance only through PRs.

## Validation

Real Git stores and external worktrees; ambient overrides; malformed/failed pagination; bounded traversal and symlink/bare coverage; production CLI ingress; read-only actual representative inventory.

Run focused checks while iterating; freeze source and docs before required baseline/subsystem gates and independent review. Keep exact receipts outside the validated candidate. Never substitute a report, event or mocked refusal for an actual required positive production-path result.

## Completion

Source delivery, runtime admission, installation and cleanup outcomes are separate. Retained/unknown states remain explicit. Do not mark done until this package’s proof and owning workflow are complete.
