---
work_package_id: WP15
title: Explicit operation closeout commit policy
dependencies:
- WP07
- WP14
requirement_refs:
- FR-006
- FR-007
- FR-008
- SC-005
- C-001
- C-003
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks: []
phase: Prospective closeout safety correction
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/invocation/executor.py
create_intent:
- docs/plans/engineering-notes/2026-10-27-op-closeout-no-commit.md
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/executor.py
- src/specify_cli/cli/commands/profile_invocation.py
- tests/specify_cli/invocation/cli/test_complete.py
- tests/specify_cli/invocation/test_executor.py
- docs/plans/engineering-notes/2026-10-27-op-closeout-no-commit.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP15 – Explicit operation closeout commit policy

## Do This First: Load Agent Profile

Load canonical implementer-ivan. Google owner chat01a17b5e-b683-7402-aa18-d42068c3734c implements in the existing Source lane; Subsequent chat01a152ac-6843-7543-946b-e8207f2086fd independently reviews. Source lifecycle owns prospective planning admission and landing coordination. A claim must be made through the supported command by the actual implementation owner, never invented here.

## Review Feedback

This is new prospective corrective work after approved WP07/WP14. Their approvals, event history and accepted mission metadata remain immutable. No retrospective reapproval or reopened old package is implied.

## Objectives & Success Criteria

`profile-invocation complete --no-commit` closes the caller's canonical Op without invoking Git commit. Default behavior remains unchanged. Completion audit/evidence/correlation/propagation remain intact; completion is not source publication or cleanup authority. A user can safely close their own Op in an otherwise foreign dirty primary without committing unrelated work.

## Context & Constraints

Follow the current spec/plan and .kittify/charter/charter.md. The real PDB Op remains preserved/open until a new isolated qualified repair is available. No protected PDB changes, producer launch, model/Store/host effects, shared-runtime replacement, new checkout, hook bypass, or broadened ownership. Preserve every Source138 gate/result and unknown recovery obligation. Bounded correction to existing Python entrypoints/executor/tests is authorized; no new lifecycle engine or policy implementation is added.

## Branch Strategy

Canonical finalization owns target fields. Continue in the existing Source checkout and declared integration target codex/organization-workspace-lifecycle-20261020. Use ready PR and required platform gates; a mission-target merge is not mainline delivery. Preserve local squash-source ancestry through normal supported joins and recovery, never reset/rebase it away.

## Subtasks & Detailed Guidance

### Subtask T015 – Add explicit no-commit operation closure

- Reproduce actual current CLI unknown-option refusal before repair using a synthetic owned fixture, never the live dirty PDB primary.
- Add `--no-commit` and pass an explicit `auto_commit=False` policy to `ProfileInvocationExecutor.complete_invocation`; defaultTrue preserves existing callers. Skip only the final `_commit_op_record` call.
- Preserve owned_checkout authority, outcome/evidence validation, branch drift, idempotence, canonical completion writer, artifact/commit correlation links and propagation. Do not change JSON response shape.
- Prevent stale `last_op_commit` from leaking across same-executor reuse; reset at the correct successful no-commit operation boundary. Human output truthfully states that the journal is uncommitted rather than implying a refused default commit or durability in Git.
- Document intent, validation, decisions and limitations in the owned engineering note. No unrelated refactor or test-scope growth without a new explicit scoped amendment.

## Test Strategy

Required real CLI/executor controls: no-commit closes once and HEAD/index/refs/unrelated dirty bytes remain identical; invalid outcome, missing required evidence and double closure refuse without new effects; default path still commits once; sequential executor reuse reports no stale outcome. Existing owned_checkout tests remain required regression but are not added edit scope. Run focused cases, full owning invocation fast subsystem, implicated named architecture gates, configured lint/type checks and unchanged changed-statement coverage requirement. Required publication hook remains mandatory; no duplicate full gate immediately before it unless changed inputs or unresolved risk requires it. No local whole architectural/e2e/performance/test-full sweep.

## Risks & Mitigations

The commit flag is correlation data and must not be confused with auto-commit policy. Opt-out cannot bypass evidence or ownership guards. Persisting an event without committing leaves a recoverable uncommitted audit obligation, not a claim that the event is published. New runtime must be isolated and hash-qualified; never patch a running consumer.

## Review Guidance

Independent reviewer must inspect exact candidate and frozen receipts; prove only Git commit is skipped, useful dirty state preserved, default behavior unchanged, no stale outcome, no fabricated source/claim or old approval. Freeze source/docs before final gates; retain receipts externally. Review and installed acceptance are distinct from organization execution rollout.

## Progress & Status

Use canonical status events and real claim commands. This authored prompt contains no runtime history or approval.
