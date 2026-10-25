---
work_package_id: WP12
title: Restore branch-first integration acceptance
dependencies:
- WP04
- WP07
requirement_refs:
- FR-006
- FR-009
- SC-005
- NFR-001
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks:
- T012
phase: Lifecycle productionization
history: []
agent_profile: implementer-ivan
authoritative_surface: tests/terminus/
create_intent:
- docs/plans/engineering-notes/2026-10-24-lifecycle-integration-contracts.md
execution_mode: code_change
owned_files:
- src/specify_cli/consolidation/preflight.py
- tests/terminus/**
- tests/specify_cli/consolidation/test_single_branch_consolidate_e2e.py
- src/specify_cli/git/ref_advance.py
- tests/git/test_ref_advance_cas.py
- tests/contract/test_mission_status_ops.py
- contracts/mission-status/schemas/OpsInvocation.yaml
- docs/plans/engineering-notes/2026-10-24-lifecycle-integration-contracts.md
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP12 — Restore branch-first integration acceptance

## Objectives & Success Criteria

Close inherited integration regressions without weakening PR-only protection, rollback, approved-content, lease or contract checks. Real success fixtures consolidate on a non-protected feature target with a distinct unchanged primary. Deliberate protected-target and real PR-landing fixtures remain protected and meaningful. All inherited failures need a recorded disposition and real owning checks before publication.

## Context & Constraints

Required hosted CI at PR120 source 9fdcc64 exposes missed WP04 fixture propagation (3a2f4a429). Initial four exact-source reproductions and full hosted logs are external retained evidence. Do not call these actual-default pre-existing failures: actual default lacks the 4.x consolidation surface. Root owns disjoint generator and CI router/registry changes in its existing lane. No new checkout, policy bypass, weakened assertions, fake approvals or raw metadata/status restamping.

## Subtask T012 — Qualify the branch-first integration contract

- Classify every edited fixture occurrence against the existing eight-category occurrence map. Preserve main/develop references whose subject is primary protection, actual PR landing or historical facts. Migrate only real positive/content/rollback fixtures and their target-specific expectations. Keep primary HEAD/reflog assertions and injected failures reachable.
- Reproduce the selected current failures before repair. Give shared positive fixtures a real primary branch distinct from the selected feature target; use canonical policy as-is and never patch it off.
- Repair the inherited raw Windows detection in `_stop_unjoined_ref_transaction` through the existing kernel OS door; preserve exact signalling/join behavior and tests, no exemption.
- Classify OpStartedEvent.checkout_branch as internal custody data in the existing closed public status contract, keeping omission/redaction/field-coverage mutation checks and documenting the real choice.
- Keep the implementation log's UX findings, engineering decisions and limitations current. Freeze source and docs before final checks; retain receipts externally.

## Test Strategy

Run the changed fixtures, owning consolidation/terminus test modules and specific OS/contract/PR-only gates; run required make test-fast and configured Ruff/mypy for the actual changed surface. No whole architectural/e2e/performance suite locally. Preserve actual red logs, failed fixtures, positive rollback/refusal controls and exact source identity. Existing ancestor governance must not be bypassed by moving a failed fixture to a favorable path.

## Review Guidance

Independent review must confirm tested mutation phases were reached and restored, primary refs stayed unchanged on feature consolidation, protected-target attempts still refuse before effects, approved/removed content assertions remain real, internal checkout identity is not exposed as public status, and source/CI baselines are attributed honestly. Do not accept a mass rename, test skip, changed gate threshold or preservation record as proof of automatic cleanup.

## Activity Log

- Bounded continuation authored from the canonical task-prompt template after hosted failure classification; runtime transitions are recorded by supported CLI only.

### Ownership clarification after real crash reproduction

The same lifecycle owner retains the earlier WP04 preflight surface; no other active writer owns it. WP12 includes the bounded protected-refusal diagnostic correction: retain the strict canonical decision and expose guarded abort for a previously interrupted attempt, without claiming earlier mutations were undone. This is same-owner, dependency-ordered ownership-map leeway, not a guard bypass. Canonical finalization/ownership verification remains required before review/publication once the isolated latest-runtime asset-scope compatibility blocker is qualified. No runtime status/event payload was hand-edited.
