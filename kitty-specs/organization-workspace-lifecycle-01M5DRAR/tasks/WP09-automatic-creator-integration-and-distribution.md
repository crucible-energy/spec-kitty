---
work_package_id: WP09
title: Automatic creator integration and distribution
dependencies:
- WP08
- WP11
requirement_refs:
- FR-011
- FR-003
- FR-004
- FR-005
- NFR-001
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020.
  During /spec-kitty.implement this WP may branch from a dependency-specific base,
  but completed changes must merge back into codex/organization-workspace-lifecycle-20261020
  unless the human explicitly redirects the landing branch.
subtasks:
- T009
phase: Lifecycle productionization
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/workspace_lifecycle/worker.py
create_intent:
- tools/zig/workspace_ingress.zig
- tools/zig/workspace_host.zig
- docs/plans/engineering-notes/2026-10-28-lifecycle-foreground-ownership.md
execution_mode: code_change
owned_files:
- src/specify_cli/workspace_lifecycle/worker.py
- src/specify_cli/workspace_lifecycle/configuration.py
- src/specify_cli/cli/commands/workspaces.py
- src/specify_cli/lanes/worktree_allocator.py
- src/specify_cli/invocation/writer.py
- src/specify_cli/invocation/lifecycle.py
- tools/zig/workspace_ingress.zig
- tests/lanes/test_lane_tip_record_points.py
- tests/specify_cli/lanes/test_worktree_allocator_recovery.py
- src/specify_cli/workspace_lifecycle/adapters.py
- tools/zig/workspace_finish.zig
- src/specify_cli/workspace_lifecycle/original_run.py
- src/specify_cli/lanes/implement_support.py
- src/specify_cli/orchestrator_api/wp_lifecycle.py
- tools/zig/workspace_host.zig
- docs/plans/engineering-notes/2026-10-28-lifecycle-foreground-ownership.md
tags: []
task_type: implement
tracker_refs: []
---

# WP09 — Automatic creator integration and distribution

## Objectives & Success Criteria

Integrate native obligations into supported creator startup/completion/recovery. Python edits are bounded migration glue; new implementation/tests use Zig. Package exact artifacts, refuse unsupported creators, and prove actual asynchronous cleanup plus preservation/interruption. No broad prune or trust bypass.

## Context & Constraints

Follow the October 24 amendment, current language policy and existing creator custody. Preserve prior approvals. Implementation is not approval or deployment.

### Ordinary creator boundary and ownership

The existing core/release owner has released bounded ordinary allocator and
completion-hook integration to this lifecycle lane. Root retains core analysis,
finalizer and newest-release source/distribution convergence. Canonical task
finalization must admit the added paths before implementation; this amendment
does not claim any new implementation or runtime adoption.

- Bind supported creator resource identity and its generation before the actual
  `allocate_lane_worktree` creation effect, with reuse and interrupted creation
  classified explicitly. Observing an existing path cannot adopt its custody.
- Connect actual `write_completed` and `write_paired_completion` outcomes to the
  same bounded native startup/completion/recovery ingress. These records and
  session-end hints only wake the worker; they cannot mint owner release,
  accepted delivery, joined-descendant evidence or deletion authority.
- Keep new ingress logic and its positive/negative tests in Zig; changes to
  these existing Python authorities are narrowly reviewed migration glue.
  Preserve sealed OperationRoot, dispatch, close and executor bodies until any
  separate extension is explicitly scoped and reviewed. Do not repin historical
  evidence or bypass creator fences to make an ordinary callback appear safe.
- Freeze the converged newest-release source and immutable artifact identity
  before final installed acceptance. Prove ordinary creation/startup, successful,
  failed and canceled production, and missed-event recovery outside the source
  checkout. Retained useful results need an accountable owner/next action/review
  event; eligible resources must actually close once through their creator.
- Retain the plan's fresh-process callback latency and bounded worker budgets.
  Installed explicit manual `managed-run` proof alone is insufficient for this
  ordinary ingress requirement. Managed creators remain protected until their
  supported archive operation and release are qualified.

## Validation

### Ratified foreground lifetime increment

After WP12's independent approval, the existing Source lifecycle lane owns the
bounded implementation of Root's reviewed foreground design. The exact handback
is retained externally with SHA-256
`6736d958ddb7f8d50cedb2ee5e90b8997b68bd50f7945b8602b3c2a6a0164466`.
Root retains architecture, independent review and publication authority; no
competing writer or new mission is admitted.

- Put new job-admission policy, state-machine decisions and acceptance/refusal
  tests in `tools/zig/workspace_host.zig`, reusing existing native ingress and
  bounded persistence rather than inventing another store or process runner.
- Extend the existing `OriginalWorkspaceRun` atomic factory and creator adapter
  only as narrow bridges. Retain the genuine original object through one finite
  foreground producer, confirmed join and settlement. Keep legacy `create` and
  `run_producer` one-attempt behavior, the production 30-second short-operation
  cap, process signalling custody and all existing release checks unchanged.
- Admit the finite job before allocator setup. Pass only a private live creation
  context through `create_lane_workspace`, `_resolve_start_workspace` and their
  existing allocator; replace the fresh-worktree effect once through the original
  factory. Keep public tuple/JSON results as observations. Reuse, recovery and
  repository-root paths cannot manufacture creator authority.
- Prove actual execution outlives a strictly smaller short-operation fixture
  allowance while staying inside the distinct finite job budget. Exercise
  success, failure, timeout, cancellation, unknown descendants, repeated attempts
  and serialized/forged observations. Preserve useful work and exact recovery
  obligations on every uncertain result. Commit the actual failing-first native
  acceptance test before production changes.
- Root and Source have not identified an already configured normal foreground
  producer-owning harness. Record unsupported external-host retention explicitly;
  do not adopt the running Codex app, invent a normal-producer receipt or treat an
  opt-in software fixture as ordinary application adoption. This increment admits
  no model calls, new agents, host/route effects or shared-runtime replacement.
- Freeze the converged current-release artifact before installed qualification.
  Independently verify real caller lifetime, cleanup and preservation, then
  coordinate each current organization repository through WP10. Refresh exact
  repository IDs instead of freezing the historical count of 119.

The added Python paths are the already reviewed CLI/API and original-creator
bridges. The new native file owns policy and tests; the engineering note records
the approved contract and actual limitations. Existing WP08/WP11/WP12 approvals
are preserved, not reopened or silently broadened. Canonical task finalization
and current planning analysis must admit this amendment before implementation.

### Generation-bound ordinary creator admission

WP09 depends on the completed WP08 native finish store and WP11 creator
adapter. Extend only these two existing surfaces and the already owned native
ingress/tests; preserve their existing recovery, delivery and release checks.
Root's core/finalizer/status-resume work remains independently owned.

- Resolve the ordinary allocator's selected parent reference to an explicit
  expected starting commit. Preserve existing callers' default HEAD behavior;
  an ordinary creator must not be mislabeled as a managed creator.
- Before creation effects, bind creator kind, accountable owner, generation,
  common Git store, requested path/ref and expected commit in existing creator
  custody. Native ingress must consume that exact receipt, never adopt an
  observed workspace or infer ownership from its location.
- Reuse the native finish store's strict, bounded, revisioned persistence.
  Completion records convey outcome data only. Owner release still requires
  independent generation-bound capability; invocation/session labels, callbacks
  and finish obligations cannot mint it.
- Retain negative proofs for changed parent/ref/path/store, absent generation
  or receipt, unknown registration, wrong creator kind and missing release.
  Validate stale and interrupted events without resetting history or broadening
  deletion authority. Installed asynchronous closeout remains a separate gate.

This dependency-ordered scope amendment admits bounded migration changes to the
existing Python adapter and native Zig finish integration. It does not reopen
WP08/WP11 approvals, authorize unrelated adapter changes, or assert deployment.

The bounded creator API now accepts an optional exact starting commit; omitted
input preserves the existing caller-HEAD behavior. Symbolic references, absent
objects and annotated tag objects must refuse before custody/worktree effects.
Its native refusal witness compares exact existing ledger bytes and entry
identities, as well as target absence. This API alone does not admit ordinary
creators or confer release authority.

Native finish obligations bind creator kind and exact generation separately
from source identity; legacy unbound obligation identifiers remain unchanged.
Ordinary startup, completion and uncertain-recovery ingress records accountable
data only. Success waits for delivery, failure remains blocked, cancellation
returns to useful-work triage, and uncertain recovery stays blocked. No outcome
can assert accepted delivery, joined descendants, release or retirement. The
new native command still requires actual creator callbacks, distribution
packaging and installed acceptance before deployment can be claimed.

Integrate native obligations into supported creator startup/completion/recovery. Python edits are bounded migration glue; new implementation/tests use Zig. Package exact artifacts, refuse unsupported creators, and prove actual asynchronous cleanup plus preservation/interruption. No broad prune or trust bypass.

### Existing recovery-fixture compatibility

The actual public allocator reproduced deletion of an unrelated missing
registration's staged index. Native Zig tests retain that red and the unknown
requested/sibling metadata controls. Remove repository-wide prune; an unknown
requested registration must remain retained pending its owner's recovery.
The two existing Python recovery test modules are admitted only for fixture
compatibility: their positive re-attachment scenarios must explicitly dispose
of their own synthetic requested registration through Git before retrying.
Preserve every existing branch, tip, clean-state and sparse-checkout assertion;
do not delete, skip or weaken those positive regression checks. New behavior
and refusal tests remain in the scoped native Zig file. This amendment grants
no real missing-registration removal or owner-release authority.

## Production correctness findings to reproduce before repair

The current API-only delivery verifier accepts arbitrary merge SHA with a nonexistent local source path. Before automatic retirement, fetch actual default, establish merge ancestry and exact delivered tree/PR identity, inspect review-thread disposition, and preserve exact unique source ancestry through a named recovery anchor or verified restorable snapshot. Shallow bundles require their exact boundary/prerequisites; bundle verify alone is insufficient. Keep unavailable checks and uncertain effects retained with reasons. Validate against real local Git fixtures plus bounded API fixtures, retaining counterexamples first.
