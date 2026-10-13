---
work_package_id: WP03
title: Native execution, diagnostics, and platform supervision
dependencies:
- WP01
- WP02
requirement_refs:
- FR-004
- FR-007
- NFR-002
- NFR-005
- NFR-004
- C-001
planning_base_branch: codex/native-local-validation
merge_target_branch: codex/native-local-validation
branch_strategy: Planning artifacts for this mission were generated on codex/native-local-validation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/native-local-validation unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
phase: Native local validation
history:
- at: '2026-10-12T23:33:08Z'
  actor: codex
  action: Authored task draft; finalization and claim pending
agent_profile: implementer-ivan
authoritative_surface: tools/zig/validation_execution.zig
create_intent:
- tools/zig/validation_execution.zig
- tools/zig/validation_process.zig
- tools/zig/validation_process_darwin.zig
- tools/zig/validation_process_linux.zig
- tools/zig/validation_process_windows.zig
- tests/local_validation/test_execution.py
- tests/local_validation/test_platforms.py
execution_mode: code_change
owned_files:
- tools/zig/validation_execution.zig
- tools/zig/validation_process.zig
- tools/zig/validation_process_darwin.zig
- tools/zig/validation_process_linux.zig
- tools/zig/validation_process_windows.zig
- tests/local_validation/test_execution.py
- tests/local_validation/test_platforms.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` through `/spk-doctrine-profile-load` before implementation. Use the actual owning mission workflow. This profile selection does not dispatch another agent.

## Objectives And Success Criteria

Native execution, diagnostics, and platform supervision.

Success/failure discriminate; actual owned terminal cleanup is observed. Detached controls cannot pass solely on group_disposed. Raw quota failures retain diagnostics. Process/RSS samples are not hard peak claims. Each supported platform has real evidence.

## Context And Constraints

Read this mission’s spec, plan, research, data model, and local contract. Sam authorizes unattended local execution, routine engineering decisions, and the exact hosted migration. Preserve actual validators, thresholds, user assets, other dirty lanes, recovery refs, and runtime resources. You are not alone in this codebase; do not revert other owners’ edits.

No model, Source/Store, canonical corpus, or credential effect is part of this package. Human-facing text uses normal spaces and Oxford commas. Unknown measurements remain unknown. Missing tools, bindings, checks, cleanup, or platform proof cannot yield a passing outcome.

## Branch Strategy

Planning/runtime target: `codex/native-local-validation`. Eventual GitHub review base: `fix/owned-analysis-implementation`, distinct from the mission write target. Existing topology is `single_branch`; reuse the assigned checkout. Do not create another worktree or bypass owned routing. Finalization provides canonical lane metadata.

## Ownership And Delivery

Use declared paths; a narrow out-of-map fix requires recorded rationale and coordination with its actual owner. Preserve existing work. Commit genuine RED controls separately before implementation. After each coherent validated increment, commit and push to one intended origin destination through the owning workflow. No uncommitted handoff is delivery.

## Subtasks And Detailed Guidance

### T009 — Commit real execution and escape RED controls

Drive success, failure, failed spawn, timeout, cancellation, quota breach, same-group descendant, changed-group descendant, and setsid/session escape. Retain PID/kernel identity and terminal observations; preserve an unrelated live process. Helper exit alone cannot establish all-descendant cleanup.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T010 — Adapt the reviewed Darwin ownership foundation

Reuse Temet helper revision 7d99ede611abbbfbda4503471fa71b417a6ef177 and SHA-256 16dbf37d5d9199e61523e731cf931404e695d7a37fec463519951ba0a26fff8b with provenance/license. Preserve retained identity, reaping, cancellation, and bounded cleanup. Add a separately tested streaming sink. Original-group disposal and sampled process/RSS values remain labeled exactly; unsupported containment refuses or stays unqualified.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T011 — Execute dependency-ordered checks with retained logs

Run specification argv against the private candidate and declared environment with finite wall, cleanup, output, process, and memory budgets derived from authorities and observed controls. Retain produced raw logs separately from display excerpts. A budget/quota breach refuses, keeps produced evidence, and joins owned resources. Unknown cleanup or failed required dependency cannot yield success.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T012 — Qualify real platform backends

Use identity-safe Linux ownership and Windows job ownership, reusing verified ecosystem foundations where applicable. Qualify actual commands and platform control boundaries, not inferred portability. Coordinate existing strict GX10 access for Linux proof; do not touch canonical model/corpus resources. Unavailable Windows execution is a named missing qualification, never a Darwin substitute or completed retirement. No unrelated VM/service or unowned process signaling.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

## Test Strategy

Compile and format using verified Zig 0.16.0. Run actual native/public-entry controls and affected Python tests, strict mypy, Ruff, docs, completion, architecture, and coverage gates. At least 90% changed executable statement coverage needs genuine native instrumentation and denominator evidence; Python-only XML cannot establish native coverage. Freeze code/docs before final gates and keep immutable results outside the candidate.

## Risks And Review Guidance

A distinct existing workflow owner reviews fixed candidate evidence. Verify positive and negative controls, exact staged source and imports, complete relevant input closure, actual process ownership/cleanup, retained diagnostics, preserved requirements, and honest platform/resource claims. No fresh test count, green summary, or bot availability establishes those invariants. Reply to public findings and resolve them only after validation and explicit disposition.

## Definition Of Done

Actual package requirements pass; affected documentation, self-review, and independent review are complete; the useful increment is committed and pushed. Required findings are resolved through their public surfaces where available. No unrelated work is lost. Compatible-line delivery does not establish default-main integration, Temet adoption, trained LoRAs, or deployed serving.

## Activity Log

- 2026-10-12T23:33:08Z — codex — Task draft authored; independent fixed-plan review and finalization pending.
