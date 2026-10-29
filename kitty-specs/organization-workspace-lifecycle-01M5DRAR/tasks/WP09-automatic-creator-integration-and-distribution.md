---
work_package_id: WP09
title: Automatic creator integration and distribution
dependencies:
- WP08
- WP11
- WP15
- WP16
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
- src/specify_cli/cli/commands/agent/mission_inspect.py
- tools/zig/mission_inspect.zig
- docs/plans/engineering-notes/2026-10-29-pinned-planning-inspection.md
- tools/zig/commit_noop.zig
- docs/plans/engineering-notes/2026-10-29-canonical-noop-commit.md
- tools/zig/mission_number_commit.zig
- docs/plans/engineering-notes/2026-10-29-numbering-commit-diagnostics.md
- tools/zig/claim_origin.zig
- docs/plans/engineering-notes/2026-10-29-first-claim-provenance.md
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
- tools/zig/validation_process_darwin.zig
- src/kernel/owned_process.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/context/mission_resolver.py
- src/specify_cli/cli/commands/agent/mission_inspect.py
- tools/zig/mission_inspect.zig
- docs/plans/engineering-notes/2026-10-29-pinned-planning-inspection.md
- tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py
- docs/api/agent-subcommands.md
- src/specify_cli/git/commit_helpers.py
- tools/zig/commit_noop.zig
- docs/plans/engineering-notes/2026-10-29-canonical-noop-commit.md
- src/specify_cli/_completion_manifest.json
- tests/architectural/test_json_contract_enumeration.py
- tests/architectural/untrusted_path_audit/inventory.md
- pyproject.toml
- tests/_support/run_basetemp.py
- docs/plans/engineering-notes/2026-10-27-op-closeout-no-commit.md
- docs/plans/engineering-notes/2026-10-28-pytest-containment-and-private-yaml.md
- tests/architectural/test_single_mission_surface_resolver.py
- src/specify_cli/cli/commands/profile_invocation.py
- tests/architectural/_universe_store.py
- tests/architectural/test_universe_store.py
- src/specify_cli/consolidation/mission_number/bake.py
- tools/zig/mission_number_commit.zig
- docs/plans/engineering-notes/2026-10-29-numbering-commit-diagnostics.md
- src/specify_cli/consolidation/reconciliation.py
- src/specify_cli/consolidation/wp_attribution.py
- tools/zig/claim_origin.zig
- docs/plans/engineering-notes/2026-10-29-first-claim-provenance.md
- src/specify_cli/consolidation/phase_gate.py
tags: []
task_type: implement
tracker_refs: []
---

# WP09 — Automatic creator integration and distribution

## Protected first-claim provenance for useful-work integration

The official published release selects later stamped reclaims after genuine
legacy unstamped first claims. Reproduce the FIRST genuine governed claim
contract in native regressions; do not invent a historical creation stamp or
read broad ancestry as semantic approval. Preserve the documented legacy
contract or a named recoverable refusal for unknown origin. Before changing
dependent authored-content collection, port the two live-path official
upstream protection commits 2db04ded1fd877041457b60f1a1109304be738a7
and 3bde34db17ad841c86e6a9c26f8fdb29dd2457dd with explicit provenance.
Native controls must retain modern creation bounds, migration filtering,
multi-WP ordering, rewritten dependency rejection, canceled/removed-content
rejection and approved-content presence. Reuse existing functions/backends;
no new Python policy engine, force, historical event/claim rewrite, original
project/runtime edit or unauthorized consolidation retry. Unknown lane
provenance never grants workspace/resource retirement authority. Qualify and
independently review the exact protected installed candidate before delivery.

## Numbering commit diagnostics for useful-work integration

The existing Subsequent owner reported a normal consolidation refusal at the
mandatory detached numbered-meta commit. A single leased exact-blob fixture
reproduced the current-context hook failure; explicit existing read-only Biome
2.5.0 passed the same hook and meta-only commit. Original birth environment is
unknown, so no retrospective parity is claimed. Preserve this original refusal
and normal rollback, captured output, mandatory hooks and exact commit scope.
Add bounded native failing-first proof that public exception rendering exposes
all captured stderr without changing the CalledProcessError status/cause or
ref/cleanup outcomes; use only a narrow existing commit-site diagnostic change.
No new policy engine/function, hook bypass, Source/project runtime hotpatch,
Subsequent write or ordinary repository adoption is granted.

## Hosted session and diagnostic-contract repair

The remaining six hosted failures were reproduced before edits. Root accepted
exact diagnostic-only classification for the private immutable-index carrier,
not a wildcard/functional exemption or current-filesystem resolver. Rephrase
nonrecipe closeout help without changing behavior. Keep volatile test-enclosure
transport identity out of the semantic collection-cache key only; actual source,
options/profile/authority and admission/resource checks remain independent.
Preserve exact parity/mutation tests and genuine semantic-change negatives.
No new lane, Python policy engine, runtime swap or ordinary adoption is granted.

## Hosted contract propagation repair

Exact published e476 CI failures reproduced as14focused failures before edits.
Add missing required frontmatter to the five lifecycle notes without changing
bodies; classify immutable inspect in the existing PARSEABLE mission JSON family
and regenerate canonical completion data; document the Git-tree-only diagnostic
path in the bidirectional containment inventory; remove stale formatter debt;
use pytest.MonkeyPatch with registered undo for test enclosure globals. Keep
checks, data floors, typed errors and all current approvals/history unchanged.
This is a bounded lifecycle integration follow-up, not wholeWP09 completion.

## Canonical unchanged-commit hook correction

Parent assigned this concrete Cmail workflow blocker to the same Source lane;
Root approved the exact bounded architecture before code edits. The original
Cmail run and current Source producers are terminal/joined. Actual setup-plan
consumed460.900s and the full native hook despite unchanged HEAD/tree/bytes and
commit_created=false. RuntimeR remains a live seven-callback dependency; never
replace it. Qualify a new isolated candidate after source review.

In the ordinary existing safe_commit branch only, after all existing preflight,
scoped snapshot and staging, use the existing authoritative selected staged-tree
comparison before invoking Git commit. For a genuine no-op, restore the exact
scoped pre-call patch and raise existing SafeCommitStagedTreeUnchanged. Preserve
actual resolved target, locks, protection/path/foreign-stage guards, genuine-delta
mandatory hooks and misleading-hook-output failure classification. Do not add an
ambient caller shortcut, second runner or new Python policy engine. Retained
Python correctness edit is narrowly architecture-approved; new actual behavioral
assertions stay native. Expected-parent/index-deletion branches remain unchanged.

Prove true pre-fix marker-hook RED through the existing canonical caller, plus
real dirty hook, foreign/partial index preservation, protected/wrong placement,
missing path and rejecting misleading hook negatives. Preserve all current query
draft/history. Freeze the coherent combined lifecycle candidate before required
owning/architecture gates and exact installed qualification; earlier incomplete
or failed gates remain failed. No new lane, no installed/shared-runtime mutation.

## Immutable inspection contract join

Actual full owning validation exposed the exact frozen command-set contract
excluding the deliberately added inspect command. Targeted unchanged assertion
reproduced before repair. Amend the existing golden data in place to include
inspect and its exact mission/at/json flags, preserving symmetric equality and
all original commands/flags; do not waive or delete the guard. New behavioral
acceptance remains native. Refresh the two relevant live generated CLI reference
sections through canonical renderer/capture functions and retain companion docs,
without regenerating unrelated command pages or altering historical missions.

## Immutable planning inspection blocker correction

Root assigned and accepted a narrow read-only pinned planning query in this same
Source lane after the timing corrections qualified. Add `agent mission inspect
--mission HANDLE --at REF --json`: immutable planning identity/facts only, never
simulated next, current ready/analysis authority or runtime advancement. Reuse
existing canonical bounded Git object readers and the single mission handle
resolution algorithm; no new Python policy fork, fake checkout or branch change.
Python command/index adapters remain narrow existing-authority glue. New actual
acceptance/refusal assertions live in tools/zig/mission_inspect.zig. Preserve the
advancing owned-branch guard, claim/event history, dirty/untracked state, settings
and existing approved WPs. Pin REF once before enumeration; bound object/byte
reads and fail closed on missing/ambiguous/unsafe inputs. Installed qualification
must prove the supported query without borrowing local report receipts or
claiming cleanup/rollout adoption. This is an existing useful-work blocker, not
a competing mission or creator harness. Native Parent content auth/dispatch does
not constitute Git creator or foreground OS process ownership.

## Original absolute horizon review correction

Independent review of core 122390 found actual post-wait Git/failure persistence
borrowing fresh short-operation time, and actual delayed log setup starting a
producer after the original execution deadline. Both were reproduced before
production repair. Admit only narrow optional absolute cleanup-horizon plumbing
in the existing shared owned-process kernel. Python carries the original budget;
policy and new acceptance tests remain native. Absent preserves legacy behavior;
zero/expired remains distinct from absent, nonfinite values refuse, and nesting
only tightens. Stop and bookkeeping share the same original horizon. Preserve
uncertainty and the original failure if join/settlement cannot finish; never renew
cleanup time or signal a reaped identity. Carry original absolute execution and
settlement deadlines through the existing native primitive. No second runner,
store, producer owner, PDB implementation or installed adoption claim is admitted.

## Native producer terminal observation amendment

The existing bounded native process primitive reports successful group disposal.
That is not, by itself, natural producer completion: its terminal path can stop
remaining original-group children before reporting disposal. WP09 must reproduce
the parent-exit/live-descendant case and retain it rather than treat forced
cleanup as successful production. Extend the existing primitive only with the
required original terminal/quiescence observation, preserving its current
validation cleanup semantics and unreaped leader identity. The native foreground
policy consumes that fact; returned JSON never grants creator release. New
behavior and tests remain native; no second runner, store, daemon or claim of
unqualified whole-platform closure is introduced.

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

## Operative unknown-origin recovery diagnostics

Keep the existing first-known conservative attribution fence unchanged; it is not creation evidence. In the existing phase_gate, after strict verification reports un-attributable content, append exact lane/WP/first-event/later-fence and owning-workflow recovery guidance. Unknown history alone must not refuse a safe passing claim. Preserve verdict, divergence, canceled/removed and missing-approved-content precedence, rollback and teardown protections. Exercise the actual gate and safe post-fence passing case in native controls. No new Python helper/schema, historical event rewrite, original project or runtime mutation, waiver or consolidation retry.
