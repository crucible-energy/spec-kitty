---
work_package_id: WP05
title: Integrated recovery acceptance and adoption
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- SC-001
- SC-002
- SC-003
- SC-004
- SC-005
- NFR-004
- C-002
- C-003
- C-004
- NFR-002
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this
  WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human
  explicitly redirects the landing branch.
subtasks: []
history: []
authoritative_surface: tests/workspace_lifecycle/
create_intent:
- tests/workspace_lifecycle/test_acceptance.py
- docs/guides/how-to/workspace-lifecycle.md
execution_mode: code_change
lane: planned
owned_files:
- tests/workspace_lifecycle/test_acceptance.py
- docs/guides/how-to/workspace-lifecycle.md
- docs/reports/organization-workspace-lifecycle/**
tags: []
tracker_refs: []
---

# WP05: Integrated recovery acceptance and adoption

## Requirement coverage

FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009

## Objective

Integrated recovery acceptance and adoption. Follow the accepted spec/plan and preserve all other owners. Primary branches advance only through PRs.

## Validation

Targeted test surface: `tests/workspace_lifecycle/test_acceptance.py`, the full owning `tests/workspace_lifecycle/` package and the implicated architecture checks listed in WP01–WP04. Add production process-start-to-exit status/enqueue latency observations for the representative fixture defined in plan.md (five fresh processes each, every result <2 seconds), hung-worker timeout and SessionEnd bounded-event checks. Retain actual elapsed results; missing measurements remain unknown.

Commit acceptance tests before implementation; verify the new checks fail on the planning base for the intended missing behavior, then pass on the candidate through the production interface. Preserve existing historical red/green receipts for already implemented WP01 cases; do not manufacture a new red by weakening behavior. Run focused checks during iteration and the unchanged required `make test-fast` plus affected subsystem gates before publication; no full heavy suite locally.

Supported startup/completion path without another model prompt; missed-event replay; representative actual adapters; required gates and independent review; honest remaining unsupported capabilities.

Run focused checks while iterating; freeze source and docs before required baseline/subsystem gates and independent review. Keep exact receipts outside the validated candidate. Never substitute a report, event or mocked refusal for an actual required positive production-path result.

## Completion

Source delivery, runtime admission, installation and cleanup outcomes are separate. Retained/unknown states remain explicit. Do not mark done until this package’s proof and owning workflow are complete.
