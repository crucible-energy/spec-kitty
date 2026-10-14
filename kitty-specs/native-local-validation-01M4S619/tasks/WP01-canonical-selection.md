---
work_package_id: WP01
title: Canonical specification and native selection
dependencies: []
requirement_refs:
- FR-003
- FR-004
- NFR-003
- C-002
- C-003
planning_base_branch: codex/native-local-validation
merge_target_branch: codex/native-local-validation
branch_strategy: Planning artifacts for this mission were generated on codex/native-local-validation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/native-local-validation unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Native local validation
history:
- at: '2026-10-12T23:33:08Z'
  actor: codex
  action: Authored task draft; finalization and claim pending
agent_profile: implementer-ivan
authoritative_surface: tools/validation/gates.json
create_intent:
- tools/validation/gates.json
- tools/zig/validation_selection.zig
- tools/zig/validation_statement_inventory.zig
- scripts/validation/extract_gates.py
- tests/local_validation/test_selection.py
execution_mode: code_change
owned_files:
- tools/validation/gates.json
- tools/zig/validation_selection.zig
- tools/zig/validation_statement_inventory.zig
- scripts/validation/extract_gates.py
- scripts/ci/gate_selection.py
- scripts/ci/local_gate_parity.py
- tests/local_validation/test_selection.py
- tests/architectural/test_gate_selection_authority.py
- tests/architectural/test_local_gate_parity.py
- tests/architectural/_ci_integrity_oracle.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` through `/spk-doctrine-profile-load` before implementation. Use the actual owning mission workflow. This profile selection does not dispatch another agent.

## Objectives And Success Criteria

Canonical specification and native selection.

Actual selection agrees for discriminating source, test, docs, tooling, unknown, full, and platform cases. Missing tools or malformed authority refuse visibly. Selection inspection cannot publish.

## Context And Constraints

Read this mission’s spec, plan, research, data model, and local contract. Sam authorizes unattended local execution, routine engineering decisions, and the exact hosted migration. Preserve actual validators, thresholds, user assets, other dirty lanes, recovery refs, and runtime resources. You are not alone in this codebase; do not revert other owners’ edits.

No model, Source/Store, canonical corpus, or credential effect is part of this package. Human-facing text uses normal spaces and Oxford commas. Unknown measurements remain unknown. Missing tools, bindings, checks, cleanup, or platform proof cannot yield a passing outcome.

## Branch Strategy

Planning/runtime target: `codex/native-local-validation`. Eventual GitHub review base: `fix/owned-analysis-implementation`, distinct from the mission write target. Existing topology is `single_branch`; reuse the assigned checkout. Do not create another worktree or bypass owned routing. Finalization provides canonical lane metadata.

## Ownership And Delivery

Use declared paths; a narrow out-of-map fix requires recorded rationale and coordination with its actual owner. Preserve existing work. Commit genuine RED controls separately before implementation. After each coherent validated increment, commit and push to one intended origin destination through the owning workflow. No uncommitted handoff is delivery.

## Subtasks And Detailed Guidance

### T001 — Reproduce selection refusal and parity failures

Commit RED controls through the intended selection boundary. Pin existing workflow and registry bytes; discriminate missing/malformed specification, unknown paths, always-on gates, module/test mirrors, and mode/platform dependencies. Pair refusal with real success on the same fixtures.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T002 — Extract the one versioned local specification

Inventory all actual hosted workflows, including packs, contracts, quality, docs, platform, and release. Extract argv, conditional applicability, platform/version matrices, routing, dependency edges, and finite budgets. Separate publication from commit mode. Reject unsupported control semantics instead of guessing; credentials never enter artifacts.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T003 — Implement deterministic native selection

Use Zig 0.16 and the single JSON specification. Validate IDs, paths, unknown keys, edges, cycles, and budgets. Select conservative supported gates or refuse unknown surfaces. Preserve always-on checks, dependency closure, test mirrors, stable reasons, and order. Never interpolate changed paths into shell commands.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T004 — Migrate existing consumers and retain equivalence proof

Make existing Python selection, local parity, and architectural oracle consume the local authority. Adapt their direct controls without weakening invariants. During transition use generated hosted routing or a pinned migration oracle, not two editable maps. Preserve no-op discrimination and explain every selection difference.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

## Test Strategy

Compile and format using verified Zig 0.16.0. Run actual native/public-entry controls and affected Python tests, strict mypy, Ruff, docs, completion, architecture, and coverage gates. At least 90% changed executable statement coverage needs genuine native instrumentation and denominator evidence; Python-only XML cannot establish native coverage. Freeze code/docs before final gates and keep immutable results outside the candidate.

## Risks And Review Guidance

A distinct existing workflow owner reviews fixed candidate evidence. Verify positive and negative controls, exact staged source and imports, complete relevant input closure, actual process ownership/cleanup, retained diagnostics, preserved requirements, and honest platform/resource claims. No fresh test count, green summary, or bot availability establishes those invariants. Reply to public findings and resolve them only after validation and explicit disposition.

## Definition Of Done

Actual package requirements pass; affected documentation, self-review, and independent review are complete; the useful increment is committed and pushed. Required findings are resolved through their public surfaces where available. No unrelated work is lost. Compatible-line delivery does not establish default-main integration, Temet adoption, trained LoRAs, or deployed serving.

## Activity Log

- 2026-10-12T23:33:08Z — codex — Task draft authored; independent fixed-plan review and finalization pending.

- 2026-10-14T23:22:17.644675+00:00 — Root explicitly authorizes the single native statement-inventory path to close the independently reproduced embedded-continue denominator omission. The collector, existing selection tests, and owned log stay in WP01; its own changed executable statements require coverage. This does not admit later execution or platform scope.
