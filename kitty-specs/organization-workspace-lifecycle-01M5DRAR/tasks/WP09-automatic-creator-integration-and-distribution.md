---
work_package_id: WP09
title: Automatic creator integration and distribution
dependencies:
- WP08
requirement_refs:
- FR-011
- FR-003
- FR-004
- FR-005
- NFR-001
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks:
- T009
phase: Lifecycle productionization
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/workspace_lifecycle/worker.py
create_intent:
- tools/zig/workspace_ingress.zig
execution_mode: code_change
owned_files:
- src/specify_cli/workspace_lifecycle/worker.py
- src/specify_cli/workspace_lifecycle/configuration.py
- src/specify_cli/cli/commands/workspaces.py
- tools/zig/workspace_ingress.zig
tags: []
task_type: implement
tracker_refs: []
---

# WP09 — Automatic creator integration and distribution

## Objectives & Success Criteria

Integrate native obligations into supported creator startup/completion/recovery. Python edits are bounded migration glue; new implementation/tests use Zig. Package exact artifacts, refuse unsupported creators, and prove actual asynchronous cleanup plus preservation/interruption. No broad prune or trust bypass.

## Context & Constraints

Follow the October 24 amendment, current language policy and existing creator custody. Preserve prior approvals. Implementation is not approval or deployment.

## Validation

Integrate native obligations into supported creator startup/completion/recovery. Python edits are bounded migration glue; new implementation/tests use Zig. Package exact artifacts, refuse unsupported creators, and prove actual asynchronous cleanup plus preservation/interruption. No broad prune or trust bypass.
