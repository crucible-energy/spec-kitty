---
work_package_id: WP13
title: Preserve live stacked missions and frozen archive history
task_type: implement
phase: Lifecycle publication safety
execution_mode: code_change
owned_files:
- tests/architectural/test_archive_root_byte_identical.py
authoritative_surface: tests/architectural/test_archive_root_byte_identical.py
create_intent: []
agent_profile: implementer-ivan
role: implementer
subtasks:
- T013
dependencies:
- WP07
requirement_refs:
- FR-006
- FR-007
- FR-009
- NFR-003
- SC-005
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
history: []
---

# Work Package Prompt: WP13 — Preserve live stacked missions and frozen archive history

## Do This First: Load Agent Profile

Continue the implementer-ivan profile through the canonical resolver and preserve project doctrine. Independent review is required; no setting/model/tier change is authorized.

## Objectives & Success Criteria

Resolve the actual hosted archive-freeze refusal without rebaselining, retargeting the PR, restoring a retired shim, dropping useful source/history, or carving out a broad path exemption. A newly introduced, still-live mission on a validated non-default integration branch must be distinguishable from immutable published or terminal archive history. Existing default archives stay frozen regardless of a candidate's claimed activity.

## Context & Constraints

At immutable9d0b594df5f3bd55b7a3cb5e58ce1204fbf7e16b, the hosted archive job compares to advertised feature base fda26ce35. The organization lifecycle dossier is absent from freshly fetched actual main66b98b892e36b49e0479b521a52f8cdef572b9eb. Immutable base metadata identifies the exact target branch and mission UUID, has no mission number or flattening, and its WPs are approved rather than done. Accepted_at records an earlier acceptance snapshot; it is not new implementation approval. Preserve canonical runtime history and all old archive counterexamples. No guard source edit before red reproduction and bounded independent design review.

## Subtask T013 — Qualify the actual live/archive boundary

- Capture the real non-main refusal and reproduce its exact event/base/head/default frontier using supported existing identity seams. Default/event visibility unavailable or mismatched must refuse.
- Classify from immutable validated BASE and independently established actual repository default history, never a candidate-only active flag. Require exact root/path/mission-ID/mid8/target compatibility, unnumbered/nonterminal/unarchived base state, immutable head identity, old event-byte prefix and actual canonical status reprojection.
- Preserve default-present, base-terminal/archived and identity-swap freezes. Do not modify the existing review frontier or the four archive roots. Permit no broad live-prefix, per-file waiver, false create_intent, raw status rewrite, fake approval, deletion or source-history rewrite.
- Add positive real-Git stacked-active controls and negative mismatched/unavailable default/event, path/root/ID/mid8/target swaps, candidate-only activity, old event rewrite, forged projection and default/archive cases. Keep prior controls unchanged and meaningful.
- Record UX findings, decisions, review evidence and limitations in the existing independently owned lifecycle implementation log. This is a bounded compatibility correction to an existing Python policy gate, not a new platform or service.

## Test Strategy

Run the exact archive gate file and its specific frontier/ratchet owners, all new negative/positive controls and configured lint/type checks. Never run the bare architectural/e2e/performance suite locally. Retain exact failed/positive receipts and candidate identities externally. Actual hosted required checks, independent review and owning PR merge remain separate gates; no source pass is runtime installation or organization adoption.

## Review Guidance

Reviewers must try to make frozen historical content appear active using only candidate data, an unrelated remote/default, an absent event, a changed identity or a forged projection. Any such admission blocks delivery. Prior operator-sanctioned correction pins and archived byte-preservation rules remain intact. This task's design has bounded existing-owner review, not blanket code approval.
