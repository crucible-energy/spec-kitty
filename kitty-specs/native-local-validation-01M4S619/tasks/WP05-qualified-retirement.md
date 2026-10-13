---
work_package_id: WP05
title: Local qualification and publication, then hosted retirement
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-009
- FR-010
- NFR-004
- SC-004
- C-002
- C-003
- C-005
- C-006
planning_base_branch: codex/native-local-validation
merge_target_branch: codex/native-local-validation
branch_strategy: Planning artifacts for this mission were generated on codex/native-local-validation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/native-local-validation unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
phase: Native local validation
history:
- at: '2026-10-12T23:33:08Z'
  actor: codex
  action: Authored task draft; finalization and claim pending
agent_profile: implementer-ivan
authoritative_surface: scripts/validation/qualify.sh
create_intent:
- scripts/validation/qualify.sh
- scripts/validation/publish-release.sh
- scripts/validation/publish-docs.sh
- tests/local_validation/test_qualification.py
- tests/local_validation/test_publication.py
- docs/development/local-qualification.md
execution_mode: code_change
owned_files:
- scripts/validation/qualify.sh
- scripts/validation/publish-release.sh
- scripts/validation/publish-docs.sh
- tests/local_validation/test_qualification.py
- tests/local_validation/test_publication.py
- .github/workflows/**
- .github/ci-module-registry.yml
- tests/ci/**
- tests/architectural/test_ci_corpus_trigger_completeness.py
- tests/architectural/test_ci_router_transcription_guards.py
- tests/architectural/test_ci_quality_path_filters.py
- tests/architectural/test_ci_integrity_oracle_nonvacuous.py
- tests/architectural/test_dual_mode_contract.py
- tests/architectural/test_gate_os_tier.py
- tests/architectural/test_no_duplicate_suite_execution.py
- tests/architectural/test_module_shard_registry.py
- tests/architectural/test_module_length_agreement.py
- tests/architectural/test_same_tier_uniqueness.py
- tests/architectural/test_battery_partition_proof.py
- tests/architectural/test_meta_decode_l1.py
- tests/architectural/_gate_coverage.py
- scripts/ci/release_nightly_gate.py
- Makefile
- AGENTS.md
- .kittify/charter/charter.md
- docs/development/local-qualification.md
- docs/plans/engineering-notes/2026-10-12-native-local-validation.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` through `/spk-doctrine-profile-load` before implementation. Use the actual owning mission workflow. This profile selection does not dispatch another agent.

## Objectives And Success Criteria

Local qualification and publication, then hosted retirement.

No requirement or intentional publication disappears. Missing platform/ref/credential proof refuses. Final local authority has no deleted-YAML dependency or second editable routing map. Retirement and guidance agree with observed remote requirements.

## Context And Constraints

Read this mission’s spec, plan, research, data model, and local contract. Sam authorizes unattended local execution, routine engineering decisions, and the exact hosted migration. Preserve actual validators, thresholds, user assets, other dirty lanes, recovery refs, and runtime resources. You are not alone in this codebase; do not revert other owners’ edits.

No model, Source/Store, canonical corpus, or credential effect is part of this package. Human-facing text uses normal spaces and Oxford commas. Unknown measurements remain unknown. Missing tools, bindings, checks, cleanup, or platform proof cannot yield a passing outcome.

## Branch Strategy

Planning/runtime target: `codex/native-local-validation`. Eventual GitHub review base: `fix/owned-analysis-implementation`, distinct from the mission write target. Existing topology is `single_branch`; reuse the assigned checkout. Do not create another worktree or bypass owned routing. Finalization provides canonical lane metadata.

## Ownership And Delivery

Use declared paths; a narrow out-of-map fix requires recorded rationale and coordination with its actual owner. Preserve existing work. Commit genuine RED controls separately before implementation. After each coherent validated increment, commit and push to one intended origin destination through the owning workflow. No uncommitted handoff is delivery.

## Subtasks And Detailed Guidance

### T017 — Commit RED qualification and publication controls

Pair unavailable platform, missing exact-revision proof, failed required check, missing publication prerequisites, and stale evidence with successful authorized local modes. Prove actual packaging/docs behavior with synthetic private targets; never production credentials in fixtures.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T018 — Preserve explicit full, release, platform, and publication modes

Use the native specification and preserved validators for exact-revision release qualification, clean install, contracts, packaging, docs build/verification, and configured publication. Missing credentials/platforms refuse the affected action. Replacing hosted dispatch cannot remove its underlying proof requirement.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T019 — Independently qualify equivalence and refresh remote requirements

Freeze candidate and compare selection and executed behavior against all pinned hosted authorities. Refresh real owning-fork branch protection and rulesets for the intended target. Get existing workflow-owner independent review; reply to actionable public findings with validation and final disposition. No upstream settings, unrelated secrets, or other active resources are swept.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

### T020 — Retire hosted execution and reconcile valid contracts

Only after real equivalence proof, retire hosted workflows and runtime YAML dependence. Migrate valid hosted-specific controls into non-vacuous local behavioral contracts, preserving immutable fixtures and thresholds. Reconcile Makefile, AGENTS, charter, release/docs guidance, and consumers. Run required final gates and deliver through the compatible review line. Default-main integration and Temet adoption remain separate until actually proved.

Retain failed and passing evidence separately. Record completion through the owning event-sourced workflow only when the actual requirements hold.

## Test Strategy

Compile and format using verified Zig 0.16.0. Run actual native/public-entry controls and affected Python tests, strict mypy, Ruff, docs, completion, architecture, and coverage gates. At least 90% changed executable statement coverage needs genuine native instrumentation and denominator evidence; Python-only XML cannot establish native coverage. Freeze code/docs before final gates and keep immutable results outside the candidate.

## Risks And Review Guidance

A distinct existing workflow owner reviews fixed candidate evidence. Verify positive and negative controls, exact staged source and imports, complete relevant input closure, actual process ownership/cleanup, retained diagnostics, preserved requirements, and honest platform/resource claims. No fresh test count, green summary, or bot availability establishes those invariants. Reply to public findings and resolve them only after validation and explicit disposition.

## Definition Of Done

Actual package requirements pass; affected documentation, self-review, and independent review are complete; the useful increment is committed and pushed. Required findings are resolved through their public surfaces where available. No unrelated work is lost. Compatible-line delivery does not establish default-main integration, Temet adoption, trained LoRAs, or deployed serving.

## Activity Log

- 2026-10-12T23:33:08Z — codex — Task draft authored; independent fixed-plan review and finalization pending.
