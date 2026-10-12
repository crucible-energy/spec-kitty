---
work_package_id: WP04
title: Public native entry and real hook integration
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-001
- FR-006
- FR-008
- SC-001
- SC-002
- SC-003
- SC-005
- C-001
- C-004
planning_base_branch: codex/native-local-validation
merge_target_branch: codex/native-local-validation
branch_strategy: Planning artifacts for this mission were generated on codex/native-local-validation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/native-local-validation unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
phase: Native local validation
history:
- at: '2026-10-12T23:33:08Z'
  actor: codex
  action: Authored task draft; finalization and claim pending
agent_profile: implementer-ivan
authoritative_surface: tools/zig/local_validation.zig
create_intent:
- tools/zig/local_validation.zig
- scripts/validation/local-validation.sh
- scripts/validation/install-hook.sh
- scripts/git-hooks/pre-commit-native-validation.sh
- tests/local_validation/test_commit_entry.py
- tests/local_validation/test_hook_install.py
- docs/development/native-local-validation.md
execution_mode: code_change
owned_files:
- tools/zig/local_validation.zig
- scripts/validation/local-validation.sh
- scripts/validation/install-hook.sh
- scripts/git-hooks/pre-commit-native-validation.sh
- tests/local_validation/test_commit_entry.py
- tests/local_validation/test_hook_install.py
- docs/development/native-local-validation.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` through `/spk-doctrine-profile-load` before implementation. Use the actual owning mission workflow. This profile selection does not dispatch another agent.

## Objectives And Success Criteria

Public native entry and real hook integration.

Actual passing commits succeed and failing staged proposals refuse. Existing work and custom hooks survive installation and recovery. Candidate/tool drift refuses; owned children are joined. A shell-only bypass cannot provide native acceptance.

## Context And Constraints

Read this mission’s spec, plan, research, data model, and local contract. Sam authorizes unattended local execution, routine engineering decisions, and the exact hosted migration. Preserve actual validators, thresholds, user assets, other dirty lanes, recovery refs, and runtime resources. You are not alone in this codebase; do not revert other owners’ edits.

No model, Source/Store, canonical corpus, or credential effect is part of this package. Human-facing text uses normal spaces and Oxford commas. Unknown measurements remain unknown. Missing tools, bindings, checks, cleanup, or platform proof cannot yield a passing outcome.

## Branch Strategy

Planning/runtime target: `codex/native-local-validation`. Eventual GitHub review base: `fix/owned-analysis-implementation`, distinct from the mission write target. Existing topology is `single_branch`; reuse the assigned checkout. Do not create another worktree or bypass owned routing. Finalization provides canonical lane metadata.

## Ownership And Delivery

Use declared paths; a narrow out-of-map fix requires recorded rationale and coordination with its actual owner. Preserve existing work. Commit genuine RED controls separately before implementation. After each coherent validated increment, commit and push to one intended origin destination through the owning workflow. No uncommitted handoff is delivery.

## Subtasks And Detailed Guidance

### T013 — Commit RED through the actual Git commit path

Install the intended hook in a disposable fixture and pair passing commit acceptance with failing commit refusal. Cover partial staging, linked worktrees, spaces/newlines/unicode paths, concurrent invocations, interruption, tooling drift, and existing guards. Retain actual refs, outcomes, and process cleanup.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T014 — Implement the shared native public entry

Wire selection inspection and commit execution through canonical modules. Resolve candidate-built tooling and launcher/source identity; an unstaged launcher or stale executable cannot choose another staged proposal’s checks. Bound compilation and command execution. Return actual stable refusal reason plus private receipt/log paths; commit mode never publishes.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T015 — Compose and install hooks safely

Inspect effective core.hooksPath, current branch/planning/task-workflow guards, and user customizations. Compose rather than overwrite; ambiguous hook ownership refuses with recovery guidance. Installation is explicit, recoverable, and idempotent. Use repository/index-scoped admission coordination and private per-invocation resources.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T016 — Qualify recovery, proof reuse, and the documented workflow

Run paired real commits, interruption/recovery, final freshness, relevant-input reuse, and drift controls through the installed entry. Document actual command syntax, budgets, logs, prerequisites, topology, platform limitations, hook recovery, and retention. Capture compiler, formatter, affected tests, strict type, native coverage, and independent-review evidence. No fixture count substitutes for delivery.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

## Test Strategy

Compile and format using verified Zig 0.16.0. Run actual native/public-entry controls and affected Python tests, strict mypy, Ruff, docs, completion, architecture, and coverage gates. At least 90% changed executable statement coverage needs genuine native instrumentation and denominator evidence; Python-only XML cannot establish native coverage. Freeze code/docs before final gates and keep immutable results outside the candidate.

## Risks And Review Guidance

A distinct existing workflow owner reviews fixed candidate evidence. Verify positive and negative controls, exact staged source and imports, complete relevant input closure, actual process ownership/cleanup, retained diagnostics, preserved requirements, and honest platform/resource claims. No fresh test count, green summary, or bot availability establishes those invariants. Reply to public findings and resolve them only after validation and explicit disposition.

## Definition Of Done

Actual package requirements pass; affected documentation, self-review, and independent review are complete; the useful increment is committed and pushed. Required findings are resolved through their public surfaces where available. No unrelated work is lost. Compatible-line delivery does not establish default-main integration, Temet adoption, trained LoRAs, or deployed serving.

## Activity Log

- 2026-10-12T23:33:08Z — codex — Task draft authored; independent fixed-plan review and finalization pending.
