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
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
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

Classify live versus historical occurrences first; main unchanged through feature/integration consolidation and PR acceptance; generated guidance consistent.

Run focused checks while iterating; freeze source and docs before required baseline/subsystem gates and independent review. Keep exact receipts outside the validated candidate. Never substitute a report, event or mocked refusal for an actual required positive production-path result.

## Completion

Source delivery, runtime admission, installation and cleanup outcomes are separate. Retained/unknown states remain explicit. Do not mark done until this package’s proof and owning workflow are complete.
