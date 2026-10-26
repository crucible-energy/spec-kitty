---
work_package_id: WP14
title: Post-squash review-source reconciliation
dependencies:
- WP06
- WP07
requirement_refs:
- FR-006
- FR-007
- FR-009
- NFR-001
- NFR-003
- SC-005
- C-001
- C-003
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks:
- T014
phase: Canonical review and runtime convergence
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_move_task.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/frontmatter.py
- src/specify_cli/core/owned_mission.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/agent/test_owned_checkout_move_task.py
- tests/integration/migration/test_wp03_advance_to_approval.py
- tests/specify_cli/invocation/cli/test_owned_checkout.py
- tests/tasks/test_frontmatter_unit.py
- docs/plans/engineering-notes/2026-10-24-owned-lanes-analysis.md
- docs/changelog/CHANGELOG.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP14 — Post-squash review-source reconciliation

## Do This First: Load Agent Profile

Load canonical implementer-ivan. The existing Root core owner implements and
qualifies this repair; lifecycle Source owns planning admission and downstream
WP09. No competing checkout or producer.

## Review Feedback

Preserve all prior rejected reviews and exact source/gate receipts. This
planning amendment is not implementation approval. Independent design conditions
are retained in the external lifecycle-post-squash-review-design-r1.json.

## Objectives & Success Criteria

Restore canonical review eligibility for genuine implementation delivered by
squash before a legitimate planning refresh. Preserve the normal no-code guard.
Explicit reconciliation supplies review-source evidence only; it cannot mint
approval, verified PR/default delivery, owner release or cleanup authority.

## Context & Constraints

Actual case: integration728dd3, subtaskadb11de4, supported pin refresh0a9d13ef.
Original source/history remains under a named recovery ref. Refusals transition
from OWNED_REVIEW_BASE_ORPHANED to OWNED_IMPLEMENTATION_MISSING; do not add a fake
source touch or rewrite old receipts. Current spec/plan/charter and mission
requirements remain binding. Bounded correctness/compatibility edits to these
existing Python authorities are permitted; new lifecycle product/ingress logic
remains Zig in WP09, whose owned paths are disjoint.

## Branch Strategy

Canonical finalization resolves planning and merge targets. Root reuses its
existing core lane and review workflow; Source retains integration planning.
No direct integration push or silent supersession of frozen remote CI.
Default/source/distribution convergence remains separate.

## Subtasks & Detailed Guidance

### T014 — Reconcile exact original review source after squash

1. Commit a failing-first real Git reproduction through the existing owned
   review entry point before the repair.
2. Keep ordinary current-pin/claim-base admission unchanged. Explicitly bind
   original source and delivered squash; require full-tree equality and delivered
   ancestry on actual selected current/target histories.
3. Recover the original base from immutable source mission authority. Require
   inspectable original ancestry, exact mission/WP/target/topology and full
   canonical scope, and a real owned implementation delta.
4. Require current owned implementation entries to remain delivered identities,
   including mode/type. Keep staged/worktree/untracked implementation guards.
   Status/planning refresh is not an extension-based path waiver.
5. Refuse missing/foreign/shallow or ambiguous history, scope drift, changed
   implementation and stale review. Supplied pins are not GitHub PR verification.
6. Qualify isolated newest-published RC7 propagation through the owning runtime
   workflow. Port existing accepted explicit dispatch custody, not duplicate
   logic or PYTHONPATH/editable masquerading.
7. Return actual canonical WP11 eligibility to Source. No force/skip,
   arbitrary historical base, alternate event writer or forged approval.
8. The reproduced dirty/staged authority gap requires immutable typed scope.
   Factor the existing FrontmatterManager post-read parsing into its canonical
   parse(content, source) entry point; read delegates after the same UTF-8-sig
   decode. Preserve duplicate-key behavior, exceptions and source diagnostics.
   Parse original Git authority through that same parser without temporary
   authority files or a second YAML interpretation. Current authority/index/
   no-follow mode and byte checks remain required. Preserve original per-WP
   claim-base precedence, including invalid-present refusal.

## Test Strategy

Run the declared existing task-review, migration and owned-invocation test surfaces,
strict typing, relevant architectural
guards, lint/format and mandatory baseline under project policy. Retain real red
and positive/negative cases for changed tree/owned source, staged/worktree dirt,
mode/type substitution, foreign/missing/shallow history, no implementation and
mission/target/scope drift. Existing same-head/no-code refusal stays nonvacuous.
Only identical relevant evidence may be reused; remote current-head checks and
independent review precede publication. Bound/join exact owned descendants and
close eligible private outputs, preserving other owners' resources.
Run the existing frontmatter owning unit tests and unchanged duplicate-key
regression as well. Six direct minter authority cases reproduced acceptance of
dirty/staged WP/meta/lanes inputs; the full public approval case refused, so this
must not be described as a demonstrated approval bypass.

## Risks & Mitigations

Arbitrary old changes must not become completion proof: bind exact immutable
scope and implementation history. Retain rejected events and original ancestry.
Keep review-source, installation and organization adoption as separate facts.

## Review Guidance

Verify actual red/green and refusal evidence, exact runtime artifact identity and
canonical Source replay. Review eligibility is not release/deletion authority.

## Activity Log

- 2026-10-26T06:03:41Z — codex — Authored from the canonically resolved task prompt template at the existing Root owner's request; canonical admission remains required.

## Required user-facing release note

The existing Root owner may update only docs/changelog/CHANGELOG.md for this
repair through the normal PR template and publication gate. Describe the actual
review-source reconciliation and refusal guarantees; do not claim default-branch
delivery, installed runtime qualification, automatic cleanup or rollout before
those facts are verified. This exact scope addition changes no task state,
review verdict, owner release or required validation.
