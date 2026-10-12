# Mission Specification: Native Local Validation

**Mission Branch**: `codex/native-local-validation`  
**Created**: October 12, 2026  
**Status**: Specified; implementation and qualification pending  
**Input**: Sam's explicit direction to replace hosted CI/CD with Zig-native local tooling invoked by pre-commit. Tracker: [issue 91](https://github.com/crucible-energy/spec-kitty/issues/91).

## Intent Summary

Developers and agents proposing a commit receive unattended local validation for the exact staged candidate. A passing proposal produces verifiable evidence; missing tools, unsupported selection, failed checks, changed inputs, or incomplete cleanup refuse acceptance with a useful explanation. Existing behavioral, architectural, release, and platform requirements remain authoritative. Hosted execution is retired after local selection and behavior equivalence is proved.

Scope is grounded in Sam's direct direction, standing authority to resolve routine decisions without repeated approval, and Temet Nosce's `docs/local-validation.md` on October 12. Discovery is minimized accordingly; no new human confirmation, unperformed interview, or fictitious approval is claimed. This mission does not qualify models or authorize canonical Source/Store effects.

## User Scenarios & Testing

### User Story 1 - Validate the Proposed Commit (Priority: P1)

A developer stages a coherent change and commits. The local gate examines that proposal, selects required checks, and accepts only after the checks pass against matching inputs.

**Independent Test**: Drive the installed pre-commit entry point in disposable repositories containing passing and deliberately failing proposals.

**Acceptance Scenarios**:

1. **Given** a staged passing proposal, **when** the gate runs, **then** selected checks execute, the receipt matches the proposal, and the gate succeeds.
2. **Given** staged failing code and unstaged passing code in the same file, **when** the gate runs, **then** it tests the staged version and refuses without discarding either version.
3. **Given** relevant input drift during validation, **when** acceptance is attempted, **then** the stale result is refused.
4. **Given** an unknown changed surface or missing tool, **when** selection runs, **then** it conservatively selects a supported gate or explicitly refuses; it never silently accepts an empty selection.

### User Story 2 - Diagnose and Recover Locally (Priority: P1)

A developer sees the failed check and retained diagnostics, corrects the proposal, and reruns the same local entry point. Failures and interruptions leave no owned child running and preserve local work.

**Independent Test**: On one shared fixture, alternate success, failure, input drift, and interruption; inspect actual exits, receipts, repository state, and child termination.

**Acceptance Scenarios**:

1. **Given** a failed check, **when** the gate terminates, **then** it records the actual failure, retains bounded diagnostics, joins owned children, and refuses.
2. **Given** a successful check on the same fixture, **when** the gate terminates, **then** the observation distinguishes success from failure and records its actual result.
3. **Given** concurrent invocations or a linked worktree, **when** validation runs, **then** each invocation uses its own candidate and diagnostics while preserving existing planning guards.

### User Story 3 - Retire Hosted Execution Without Losing Qualification (Priority: P2)

A maintainer uses one local specification for commits and explicit full, release, packaging, and documentation publication actions. Hosted routing is retired after comparison proves that intended checks and selection rules are preserved.

**Independent Test**: Compare native selection with pinned existing routing across discriminating changed-surface cases; execute local positive and negative controls and explicit qualification/publication modes.

**Acceptance Scenarios**:

1. **Given** existing routing and command authorities, **when** they are extracted, **then** local selection preserves intended coverage without runtime dependence on retired YAML.
2. **Given** a required but unavailable platform, **when** release qualification runs, **then** it records the missing qualification and refuses readiness instead of crediting another platform.
3. **Given** successful equivalence proof, **when** hosted QA is retired, **then** guidance and actual remote requirements agree with the local authority, while publication remains explicitly available.

### Edge Cases

- Partial staging, renames, deletions, untracked inputs, unusual paths, and linked worktrees.
- Missing or malformed specifications, executables, dependencies, and evidence.
- Changed tree, base, specification, environment, dependencies, or toolchain during a run.
- Concurrent invocations, interruption, timeout, failed startup, and surviving descendants.
- Existing hooks, user customizations, branch/planning guards, and platform differences.
- Hosted workflows containing packaging, publication, or delivery beyond test execution.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status | Delivery | No-op passable? |
|----|-------|------------|----------|--------|----------|-----------------|
| FR-001 | Native local entry | As a developer, I want one local entry used by pre-commit and explicit commands so proposed commits have unattended proof. | High | Open | [build] | no |
| FR-002 | Exact staged proposal | As a developer, I want checks to inspect the staged tree, including partial staging, so unstaged work cannot hide failure. | High | Open | [build] | no |
| FR-003 | One selection authority | As a maintainer, I want routing and commands extracted into one versioned local specification before workflow retirement. | High | Open | [build] | no |
| FR-004 | Diagnosed refusal | As a developer, I want missing tools, invalid inputs, unsupported selection, and failures to refuse with retained diagnostics. | High | Open | [build] | no |
| FR-005 | Input-bound receipt | As a reviewer, I want candidate, parent/base, specification, toolchain, dependencies, relevant environment, commands, outcomes, and logs bound together. | High | Open | [build] | no |
| FR-006 | Fresh acceptance | As a developer, I want changed relevant inputs to invalidate prior proof before acceptance. | High | Open | [build] | no |
| FR-007 | Joined ownership | As an operator, I want success, failure, and interruption to join owned children without disturbing unrelated processes. | High | Open | [build] | no |
| FR-008 | Work and guard preservation | As a developer, I want branch/planning guards and staged, unstaged, untracked, and user-owned hook state preserved. | High | Open | [ratchet] | yes; paired with real accepted and rejected commit controls on the same fixtures |
| FR-009 | Explicit qualification | As a maintainer, I want full, release, platform, packaging, and documentation publication modes to preserve actual requirements. | High | Open | [build] | no |
| FR-010 | Qualified retirement | As a maintainer, I want hosted QA retired after equivalence and guidance/remote-requirement reconciliation without losing publication. | High | Open | [build] | no |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Complete binding | Every accepted invocation records all FR-005 bindings; missing bindings produce zero accepted receipts. | Integrity | High | Open |
| NFR-002 | Bounded execution | Every child has a finite documented execution and cleanup budget; terminal invocations have zero unjoined owned children. | Reliability | High | Open |
| NFR-003 | Deterministic selection | Matching normalized inputs and specification produce identical check identities and order; comparison has zero unexplained differences. | Consistency | High | Open |
| NFR-004 | Honest qualification | Missing or failed required platform/release checks produce zero passing qualification claims. | Correctness | High | Open |
| NFR-005 | Bounded diagnostics | Every check defines a diagnostic limit; reaching it remains visible and preserves a useful failure reason. | Operability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Native tooling | Use Zig 0.16 for local selection/execution and the same entry point from pre-commit, as explicitly requested. | Technical | High | Confirmed |
| C-002 | Existing authorities | Preserve pytest, strict mypy, Ruff, docs, completion, architecture, coverage, and release authorities until separately validated replacements exist. | Technical | High | Confirmed |
| C-003 | No competing map | Extract current routing before retirement; the final specification neither depends on deleted YAML nor coexists with a second manually maintained map. | Architecture | High | Confirmed |
| C-004 | Owned resources | Reuse the assigned checkout, preserve other active work and user assets, and cause no model or Source/Store effects. | Ownership | High | Confirmed |
| C-005 | Safe retirement | Retire hosted QA after local equivalence; preserve packaging/publication through explicit local commands, without sweeping secrets or settings. | Delivery | High | Confirmed |
| C-006 | Honest measurements | Record actual outcomes, regressions, elapsed time, and available token/cost data; unknown values remain unknown and savings require a comparable baseline. | Evidence | High | Confirmed |

### Key Entities

- **Staged candidate**: proposed commit tree and parent/base, distinct from unstaged work.
- **Gate specification**: single versioned authority for checks, selection, bounds, and modes.
- **Validation receipt**: retained evidence of actual inputs, execution, outcomes, and cleanup.
- **Platform qualification**: evidence from the required platform; another platform cannot substitute for unavailable execution.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Passing proposals succeed and corresponding failing proposals refuse through the installed commit entry on shared fixtures. — [build] · no-op passable: no
- **SC-002**: Partial staging and input drift produce zero false acceptances and preserve developer work. — [build] · no-op passable: no
- **SC-003**: Every terminal controlled invocation has an input-bound result and zero unjoined owned children. — [build] · no-op passable: no
- **SC-004**: Routing comparison has zero unexplained differences, and retirement leaves no required check or intentional publication without supported local authority. — [build] · no-op passable: no
- **SC-005**: Missing tools, unknown selection, invalid evidence, and unavailable qualification refuse usefully on fixtures also proving their corresponding successful path. — [build] · no-op passable: no

## Assumptions And Known Limitations

The starting source is the PR 90 compatible merge. Planning writes belong to `codex/native-local-validation`; GitHub review and delivery use `fix/owned-analysis-implementation` separately. Default-main integration and application-runtime adoption remain separate. Numeric execution budgets and the preserved command matrix are derived during planning from existing authorities and actual observations, rather than invented here. No model quality, deployment, or savings is claimed.

## Bootstrap Recovery

An earlier uncommitted scaffold declared the delivery branch as its planning/write branch and was refused by the owning guard. Its original ID `01M4S5BZWCR96H6QEYPQ42TSJ2`, lifecycle history, and authored spec are preserved outside the active namespace with an explicit failed-bootstrap disposition. This mission has the distinct identity returned by supported creation; it does not inherit or falsify the older identity.
