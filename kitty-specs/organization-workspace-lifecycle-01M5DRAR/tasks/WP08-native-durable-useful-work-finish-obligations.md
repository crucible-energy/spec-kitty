---
work_package_id: WP08
title: Native durable useful-work finish obligations
dependencies:
- WP07
requirement_refs:
- FR-010
- NFR-001
- NFR-003
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks:
- T008
phase: Lifecycle productionization
history: []
agent_profile: implementer-ivan
authoritative_surface: tools/zig/workspace_finish.zig
create_intent:
- tools/zig/workspace_finish.zig
execution_mode: code_change
owned_files:
- tools/zig/workspace_finish.zig
tags: []
task_type: implement
tracker_refs: []
---

# WP08 — Native durable useful-work finish obligations

## Objectives & Success Criteria

Exact owner/purpose/next/review obligations and revisioned history in Zig. Strict bounded schema, private no-follow persistence and durable writes; reject stale updates and implicit missing-history reset. Never grant release/deletion authority. Focused behavior tests and ReleaseSafe build; independent review.

## Context & Constraints

Follow the October 24 amendment, current language policy and existing creator custody. Preserve prior approvals. Implementation is not approval or deployment.

## Validation

Exact owner/purpose/next/review obligations and revisioned history in Zig. Strict bounded schema, private no-follow persistence and durable writes; reject stale updates and implicit missing-history reset. Never grant release/deletion authority. Focused behavior tests and ReleaseSafe build; independent review.
