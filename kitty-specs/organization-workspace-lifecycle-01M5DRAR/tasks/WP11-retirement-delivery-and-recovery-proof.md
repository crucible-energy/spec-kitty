---
work_package_id: WP11
title: Retirement delivery and recovery proof
dependencies:
- WP07
requirement_refs:
- FR-004
- FR-005
- FR-008
- FR-009
- FR-011
- SC-006
- NFR-001
- NFR-003
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks:
- T011
phase: Lifecycle production safety
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/workspace_lifecycle/adapters.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/workspace_lifecycle/adapters.py
- tests/workspace_lifecycle/test_adapters.py
- tests/workspace_lifecycle/test_acceptance.py
- src/kernel/git/remote.py
- tests/kernel/test_git_remote.py
tags: []
task_type: implement
tracker_refs: []
---

# WP11 — Retirement delivery and recovery proof

## Objectives & Success Criteria

Close the independently reproduced retained-runtime safety gap before any organization deployment. A GitHub merged flag alone cannot retire a workspace: fetch the actual current default branch; verify exact source/merge evidence and merge ancestry, current review-thread disposition and current local/remote refs. Preserve exact unique source ancestry and prove its recoverability before deleting the last local source branch. Protect shallow boundaries and prerequisites; bundle verify alone is not restoration. Existing active/dirty/ignored/nested/unknown controls remain unchanged.

## Context & Constraints

This is a bounded correctness repair to retained Python, permitted by current default-branch language policy. No new Python platform/service, installed-wheel patch, guard bypass or unmerged-policy downgrade. It is independent of the native finish store. Preserve all old approvals; do not weaken actual accepted behavior tests to hide failures.

## Validation

Reproduce unsafe actual removal with an old merged-PR API response whose merge is absent from the current default branch, then prove refusal through real Git fixtures. Prove normal merge and squash controls, unresolved/unavailable reviews, source recovery/restore and changed branch/owner refusal. Run focused retained-runtime subsystem checks, ruff/mypy and changed-statement coverage required by project policy. Independent review and source publication are separate from local passes.

Remote contact stays in kernel.git.remote: extend its bounded fetch seam for a creator-generation evidence ref instead of constructing remote argv in the adapter. Recovery ref advancement uses the existing guarded CAS ref owner.
