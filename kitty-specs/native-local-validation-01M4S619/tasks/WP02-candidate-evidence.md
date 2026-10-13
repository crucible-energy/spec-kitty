---
work_package_id: WP02
title: Exact staged candidate and reusable check evidence
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-005
- FR-006
- FR-008
- NFR-001
- C-004
planning_base_branch: codex/native-local-validation
merge_target_branch: codex/native-local-validation
branch_strategy: Planning artifacts for this mission were generated on codex/native-local-validation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/native-local-validation unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
phase: Native local validation
history:
- at: '2026-10-12T23:33:08Z'
  actor: codex
  action: Authored task draft; finalization and claim pending
agent_profile: implementer-ivan
authoritative_surface: tools/zig/validation_candidate.zig
create_intent:
- tools/zig/validation_candidate.zig
- tools/zig/validation_receipt.zig
- tests/local_validation/test_candidate.py
- tests/local_validation/test_receipt.py
execution_mode: code_change
owned_files:
- tools/zig/validation_candidate.zig
- tools/zig/validation_receipt.zig
- tests/local_validation/test_candidate.py
- tests/local_validation/test_receipt.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` through `/spk-doctrine-profile-load` before implementation. Use the actual owning mission workflow. This profile selection does not dispatch another agent.

## Objectives And Success Criteria

Exact staged candidate and reusable check evidence.

Both directions of partial staging use staged content. Matching per-check closure reuses proof; each relevant drift invalidates it. Incomplete/tampered/old global receipts refuse. Work, imports, and topology stay protected.

## Context And Constraints

Read this mission’s spec, plan, research, data model, and local contract. Sam authorizes unattended local execution, routine engineering decisions, and the exact hosted migration. Preserve actual validators, thresholds, user assets, other dirty lanes, recovery refs, and runtime resources. You are not alone in this codebase; do not revert other owners’ edits.

No model, Source/Store, canonical corpus, or credential effect is part of this package. Human-facing text uses normal spaces and Oxford commas. Unknown measurements remain unknown. Missing tools, bindings, checks, cleanup, or platform proof cannot yield a passing outcome.

## Branch Strategy

Planning/runtime target: `codex/native-local-validation`. Eventual GitHub review base: `fix/owned-analysis-implementation`, distinct from the mission write target. Existing topology is `single_branch`; reuse the assigned checkout. Do not create another worktree or bypass owned routing. Finalization provides canonical lane metadata.

## Ownership And Delivery

Use declared paths; a narrow out-of-map fix requires recorded rationale and coordination with its actual owner. Preserve existing work. Commit genuine RED controls separately before implementation. After each coherent validated increment, commit and push to one intended origin destination through the owning workflow. No uncommitted handoff is delivery.

## Subtasks And Detailed Guidance

### T005 — Reproduce partial-staging and drift failures

Commit RED controls with staged failure/unstaged success and the reverse. Include changed index, parent/base, executable, launcher/source, specification, dependencies, and environment. Snapshot staged/unstaged/untracked files, refs, hooks, and registry; do not count missing-command failures as identity proof.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T006 — Materialize the candidate without live-source fallback

Resolve actual repository/common-directory/index through NUL-safe Git plumbing. Materialize staged blobs and modes privately; preserve renames, deletions, executable modes, and unusual paths. Reject unsupported gitlinks and unsafe escapes. Provide a qualified private Git context when required, without modifying the live index or registering another operational worktree.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T007 — Bind receipts and first-party import identity

Bind staged tree, parent/base, native executable, launcher/source, specification, compiler/toolchain, locked and observed dependencies, relevant environment, selected argv, results, logs, and cleanup. Prevent editable imports from resolving to live unstaged code. Use private owned evidence paths and no secrets.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T008 — Prove positive reuse and paired invalidation

Declare each check’s relevant transitive input closure. A matching, policy-permitted closure may reuse actual check evidence; prove suppression versus fresh execution on a shared fixture. Pair with candidate/dependency/tool/specification/environment invalidation. Unproved closure executes fresh. Recheck full current-candidate bindings immediately before acceptance; old global receipts never qualify a new tree. Test the real Git acceptance boundary and document any unproved external race honestly.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

## Test Strategy

Compile and format using verified Zig 0.16.0. Run actual native/public-entry controls and affected Python tests, strict mypy, Ruff, docs, completion, architecture, and coverage gates. At least 90% changed executable statement coverage needs genuine native instrumentation and denominator evidence; Python-only XML cannot establish native coverage. Freeze code/docs before final gates and keep immutable results outside the candidate.

## Risks And Review Guidance

A distinct existing workflow owner reviews fixed candidate evidence. Verify positive and negative controls, exact staged source and imports, complete relevant input closure, actual process ownership/cleanup, retained diagnostics, preserved requirements, and honest platform/resource claims. No fresh test count, green summary, or bot availability establishes those invariants. Reply to public findings and resolve them only after validation and explicit disposition.

## Definition Of Done

Actual package requirements pass; affected documentation, self-review, and independent review are complete; the useful increment is committed and pushed. Required findings are resolved through their public surfaces where available. No unrelated work is lost. Compatible-line delivery does not establish default-main integration, Temet adoption, trained LoRAs, or deployed serving.

## Activity Log

- 2026-10-12T23:33:08Z — codex — Task draft authored; independent fixed-plan review and finalization pending.
