---
work_package_id: WP04
title: Branch-first consolidation and guidance
dependencies:
- WP01
requirement_refs:
- FR-006
- SC-005
- C-001
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this
  WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human
  explicitly redirects the landing branch.
subtasks: []
history: []
authoritative_surface: src/specify_cli/consolidation/
create_intent: []
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/consolidation/**
- packs/built-in/missions/mission-steps/**
- AGENTS.md
- .kittify/charter/charter.md
- tests/consolidation/**
tags: []
tracker_refs: []
---

# WP04: Branch-first consolidation and guidance

## Requirement coverage

FR-006

## Objective

Branch-first consolidation and guidance. Follow the accepted spec/plan and preserve all other owners. Primary branches advance only through PRs.

## Validation

Targeted test surface: `tests/consolidation/`, `tests/core/test_mission_create_protected_single_branch.py`, `tests/integration/test_owned_protected_single_branch.py`, `tests/architectural/test_planning_lane_branch_requires_target.py`, and `tests/docs/test_docs_lint_guidance.py`. Select only the specific generated-guidance architecture checks implicated by the classified occurrence map; no whole architecture suite.

Commit acceptance tests before implementation; verify the new checks fail on the planning base for the intended missing behavior, then pass on the candidate through the production interface. Preserve existing historical red/green receipts for already implemented WP01 cases; do not manufacture a new red by weakening behavior. Run focused checks during iteration and the unchanged required `make test-fast` plus affected subsystem gates before publication; no full heavy suite locally.

Classify live versus historical occurrences first; main unchanged through feature/integration consolidation and PR acceptance; generated guidance consistent.

Run focused checks while iterating; freeze source and docs before required baseline/subsystem gates and independent review. Keep exact receipts outside the validated candidate. Never substitute a report, event or mocked refusal for an actual required positive production-path result.

## Completion

Source delivery, runtime admission, installation and cleanup outcomes are separate. Retained/unknown states remain explicit. Do not mark done until this package’s proof and owning workflow are complete.
