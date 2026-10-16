# Implementation Plan: Native Local Validation

**Branch**: `codex/native-local-validation` | **Date**: October 12, 2026 | **Spec**: [spec.md](spec.md)

Status: Planned architecture; implementation, independent acceptance, and hosted retirement remain open. Planning writes target this branch; the ready PR targets `fix/owned-analysis-implementation`. Compatible starting revision: `6e1dd8d14fbd5cb916a966cc1d13c8b5f06797b2`.

## Summary

A Zig 0.16 gate validates the exact proposed commit in an isolated staged-tree snapshot. One versioned JSON specification owns routing, command dependencies, modes, and execution budgets. Existing Python validators remain behavioral authorities. Retain complete produced diagnostics privately, show bounded excerpts, join owned processes, and recheck every relevant input before accepting. Retire hosted execution only after selection and behavior equivalence, local publication support, and guidance reconciliation.

## Technical Context

**Language/Version**: Zig 0.16.0 for selection, staged-tree orchestration, execution, and receipts; existing Python support range remains unchanged.
**Primary Dependencies**: Git, the existing frozen Python environment, pytest, Ruff, strict mypy, coverage, diff-cover, and existing docs, architecture, completion, and release validators. No new package dependency is selected by this plan.
**Storage**: Versioned JSON gate specification; private per-invocation candidate snapshots, JSON receipts, and raw `.log` diagnostics outside tracked source.
**Testing**: Committed RED acceptance controls before implementation; focused native and shell integration controls, existing affected Python tests, and at least 90% changed executable statement coverage with explicit native instrumentation evidence.
**Target Platform**: macOS and Linux are the immediate qualification priorities. Windows qualification follows both, requires actual Windows execution evidence, and will not use Parallels on this Mac. Unsupported platforms refuse; platform evidence does not transfer between operating systems.
**Project Type**: Repository-local tooling, hook integration, and migration of existing validation consumers.
**Performance Goals**: Measure actual gate elapsed time and repeated work; no latency or savings claim without a comparable baseline. Existing workflow timeout values seed finite command budgets, which actual controls qualify.
**Constraints**: Preserve exact staged files, existing work, branch/planning guards, user hooks, publication, and validation thresholds. No canonical corpus, Source/Store, or model effects. Use the already owned checkout; no additional worktree.
**Scale/Scope**: Replace this fork's hosted execution through explicit local commit, full, platform, release, packaging, and documentation publication modes.

## Engineering Alignment

Sam has authorized autonomous implementation and local native validation. Routine questions are resolved from the specification and existing authorities. The proposed commit is the authority, not the working directory. Unknown inputs, incomplete bindings, missing required tools, failing checks, and unfinished cleanup refuse. The independent workflow owner reviews the fixed candidate and equivalence evidence. No fresh human enrollment or approval ceremony is added.

## Charter Check

Preserve single canonical authority, ATDD-first, strict type and formatting checks, non-vacuous architecture controls, independently owned review, public finding disposition, and staged-work preservation. Sam's explicit local migration direction supersedes inherited hosted-only execution assignments; update those assignments only in the qualified retirement increment. Do not add allowlists or lower thresholds. Scoped cleanup precedes functional edits to touched complex surfaces. Existing routing is a migration oracle, not a permanent second map.

## Architecture And Flow

```mermaid
flowchart LR
    H[Pre-commit or explicit command] --> B[Bind Git candidate and gate tooling]
    B --> S[Materialize staged tree]
    S --> R[Select checks from local specification]
    R --> E[Execute checks with owned children]
    E --> L[Retain raw logs and terminal receipt]
    L --> F{Recheck bindings and cleanup}
    F -->|Match and pass| A[Accept]
    F -->|Failure or drift| D[Refuse with diagnostic]
```

The hook is a thin launcher to the same public entry. The launcher is trusted only when its bytes, native executable, native source, and specification match the staged candidate and qualified build inputs. Compile from the candidate when tooling changes; never let unstaged launcher or gate changes select a different candidate's checks.

Git plumbing identifies the actual repository, common directory, index, staged tree, HEAD, and explicit base. Materialize tracked candidate blobs and modes into a private non-worktree snapshot, preserving path bytes and executable modes. Reject unsupported gitlinks or unsafe escapes explicitly. Retain linked-worktree topology and provide an isolated private Git context where validators require it; never register another operational worktree or modify the live index to build the fixture. Validators importing first-party code must import candidate source rather than an editable environment's live checkout. Reuse dependencies only with locked and observed identity, and run with a declared environment allowlist.

Recheck tree, HEAD/base, specification, tooling, dependencies, and relevant environment after all checks and cleanup, immediately before hook success. Concurrent invocations have distinct resources and a repository/index-scoped admission lock. An unsupported or changed input refuses; a receipt is proof, not a reservation against subsequent external mutation. Test the actual Git commit path and document Git's final acceptance boundary honestly.

## One Routing Authority

Extract `scripts/ci/gate_selection.py`'s current path/group/job relationships, `.github/ci-module-registry.yml` module inventory, and actual workflow commands into `tools/validation/gates.json`. Preserve source provenance and discriminating migration controls. Native selection uses argv arrays and explicit dependency edges, never shell interpolation of changed paths. Update existing Python parity and completeness consumers to read the local authority; delete their runtime dependence on workflow YAML before retirement. During transition, generate hosted routing from the same specification or freeze the migration oracle without maintaining two editable maps.

Unknown surfaces select the supported conservative gate or refuse. Always-on checks remain selected. A failed dependency cannot silently skip a required terminal gate. Selection exposes check IDs and reasons without launching publication.

## Execution And Diagnostic Ownership

Reuse the reviewed Temet `tools/zig/owned_process_group.zig` from revision `7d99ede611abbbfbda4503471fa71b417a6ef177`, SHA-256 `16dbf37d5d9199e61523e731cf931404e695d7a37fec463519951ba0a26fff8b`, as the Darwin ownership foundation. It currently bounds in-memory captures and supports Darwin only. Adapt a streaming log sink in a separately tested step; preserve kernel identity checks, cancellation, and joined cleanup. Do not pretend its existing capture contract already provides complete large diagnostic logs or cross-platform supervision.

The versioned specification declares finite wall, cleanup, output, process, and memory budgets for each check. Retain every produced byte up to the declared execution quota in private raw logs; excerpts have a separate display limit. A quota breach terminates the owned run, retains produced evidence, and refuses explicitly. No truncation may yield a passing receipt. Retention and cleanup policies remove only terminal, owned resources; incomplete cleanup remains a failure with a recoverable path.

### Supervision Qualification Boundary

The imported Darwin helper observes and disposes members of its original process group. Its `group_disposed` result does not prove containment or cleanup of descendants that change process group or create another session. Its process and resident-memory maxima are samples, not hard peak limits; short-lived excess between observations can remain unobserved. Preserve these exact meanings in receipts and UI. Do not convert sampled usage into a hard resource-enforcement claim.

Add real changed-group and `setsid` escape controls alongside ordinary descendants. Qualify each supervised command and platform against the required ownership contract. An unsupported containment/supervision boundary refuses acceptance or remains explicitly unqualified; group disposal alone cannot satisfy the all-owned-children terminal requirement. If stronger ownership support is needed, extend a bounded owning backend with identity-safe controls, without signaling unrelated processes or introducing a separate VM or service merely for this gate. Missing ownership proof is a qualification gap to address, not a passing outcome.

### WP02 self-contained ownership fixture

WP02 may create `tests/local_validation/fixtures/owned_process_group.zig` as an
exact test-only copy of the Temet helper pinned above. Assert SHA-256
`16dbf37d5d9199e61523e731cf931404e695d7a37fec463519951ba0a26fff8b`
before compiling temporary test harnesses. Committed regressions must not depend
on an operator's Documents artifacts, a sibling checkout, or a network fetch.

Use its actual result, retained streams, failure, original-group disposal, and
sampled usage to test tiny, source-closed fixture programs. Preserve its Darwin,
group-escape, and sampled-resource limits. The unchanged helper is fixture input,
not a second maintained production supervisor. Changes to it require a new
reviewed pin; production adaptation and streaming/platform work remain WP03.
This does not qualify unknown check closures or relax native coverage for the
maintained WP02 product. Its receipt module consumes evidence; caller Booleans
and a check name cannot confer cleanup or reuse qualification.

### Relevant Input Closure And Positive Reuse

Each check declares its relevant input closure: candidate files and modes, transitive first-party imports/configuration, base-dependent inputs, executable/launcher/source and specification, toolchain, locked and observed dependencies, relevant environment, platform, and command/budgets. An unproved closure selects fresh execution conservatively. A receipt for an old global candidate cannot qualify a new staged tree. Assemble the current receipt from current bindings and only individually reusable check evidence whose complete relevant closure matches and whose policy permits reuse.

Prove positive matching-input reuse on the same fixture, paired with candidate, dependency, tool, specification, and environment drift invalidation. Observe actual check execution or suppression and its effect, rather than labeling a receipt lookup as saved work. Recheck complete current-candidate bindings before acceptance, including when selected check evidence was reused. No token, time, or cost savings are claimed without comparable measured evidence.

## Project Structure

Planned new surfaces: `tools/validation/gates.json`, `tools/zig/local_validation.zig`, focused candidate/selection/receipt/process modules under `tools/zig/`, a thin launcher under `scripts/validation/`, integration fixtures under `tests/local_validation/`, and a documented pre-commit integration preserving existing hook customizations. Reuse `scripts/git-hooks/pre-commit-task-workflow.sh` guards where applicable. Existing consumers in `scripts/ci/`, `tests/ci/`, and `tests/architectural/` migrate to the local authority. Exact ownership paths are finalized by actual tasks before implementation.

Mission artifacts: this plan, `research.md`, `data-model.md`, `contracts/local-validation.md`, `quickstart.md`, and sparse `traces/` files. The independently owned implementation log is `docs/plans/engineering-notes/2026-10-12-native-local-validation.md`.

## Implementation Concern Map

### IC-01 — Canonical specification and selection

- Purpose: Extract actual routing, commands, modes, and required qualification from pinned current authorities.
- Relevant requirements: FR-003, FR-009, FR-010, NFR-003.
- Affected surfaces: Local specification, current workflow/registry parser, parity consumers, and selection controls.
- Sequencing/depends-on: None.
- Risks: Missing command, platform, fork guard, conditional, or publication semantics; preserve rather than guess.

### IC-02 — Candidate and proof identity

- Purpose: Materialize and bind the exact staged candidate, tooling, dependencies, and environment.
- Relevant requirements: FR-002, FR-005, FR-006, FR-008, NFR-001.
- Affected surfaces: Native Git/candidate and receipt modules, partial-staging and linked-worktree fixtures.
- Sequencing/depends-on: Specification shape from IC-01.
- Risks: Editable imports, symlinks, unusual paths, index races, and stale gate binaries.

### IC-03 — Native execution and diagnostics

- Purpose: Execute selected validators with bounded ownership, complete produced logs, and joined terminal cleanup.
- Relevant requirements: FR-004, FR-007, NFR-002, NFR-005.
- Affected surfaces: Native process adapter and execution controls.
- Sequencing/depends-on: IC-01 and IC-02.
- Risks: Reused PID, surviving descendants, exhausted diagnostics, and unsupported platform claims.

### IC-04 — Hook and qualified retirement

- Purpose: Wire the actual commit path and local qualification/publication modes, then retire hosted execution without losing requirements.
- Relevant requirements: FR-001, FR-008, FR-009, FR-010, NFR-004.
- Affected surfaces: Hook launcher, existing guards, local release/docs entry points, workflow retirement, guidance, and remote-requirement receipts.
- Sequencing/depends-on: IC-01 through IC-03 and independent equivalence review.
- Risks: User hook clobbering, obsolete required checks, packaging or docs loss, and unavailable required platforms.

## Validation And Rollout

Commit a real failing acceptance increment first. On shared fixtures, prove both accepted passing commits and rejected failing commits, partial staging in both directions, native tooling drift, candidate/base drift, malformed and missing tools, selection equivalence, linked worktrees, path handling, concurrency, cancellation, descendant cleanup, quota breach, changed-group and session escape, positive matching-input per-check reuse, and drift invalidation. Run required affected architecture, completion, docs, format, type, and coverage gates. Retain immutable external candidate receipts; recording a pass must not modify the candidate.

Hosted retirement is the final implementation concern: independently review selection and actual validator behavior, qualify required platform/full/release modes, retain explicit packaging and documentation publication, refresh actual branch protection/rulesets, and reconcile governing guidance. A missing platform or publication credential is a named blocker for that qualification, not a reason to claim equivalence. Default-main integration and Temet adoption follow the owning review workflow and remain distinct from compatible-line delivery.

## Known Limitations

The numeric budgets and full extracted command matrix are implementation inputs to derive and test, not completed proof. The Darwin helper requires a streaming adaptation; Linux and Windows need qualified ownership backends. No native replacement, installed hook, hosted retirement, model improvement, or savings is claimed by this plan.
