# Mission Specification: Organization workspace lifecycle

**Mission Branch**: `codex/organization-workspace-lifecycle-20261020`  
**Created**: 2026-10-20  
**Status**: Confirmed intent; implementation pending

## Intent Summary

Sam and Lynn require Spec Kitty to own deterministic workspace closeout across every `crucible-energy` repository, including workspaces created outside declared mission lanes. The trigger is creator completion/release, accepted delivery, or startup/resume recovery. The outcome is an accurate durable disposition for every discovered workspace and automatic retirement when all required evidence is present. Main changes only through PRs, locally and remotely. Unknown ownership, active work and valuable local data are preserved. These requirements were explicitly confirmed in this chat; the latest instruction directs autonomous completion without routine handoffs. No additional discovery interview is needed. This mission does not lift the separate production deployment hold.

Canonical terms: discovery is observation; delivery proves exact accepted content; owner release relinquishes execution authority; retirement removes/archives the creator-owned workspace; session end alone proves none of delivery, owner release or retirement eligibility.

## User Scenarios & Testing

### User Story 1 — Account for every organization workspace (Priority: P1)

An operator sees all accessible organization repositories matched to local Git stores and workspaces, including primary checkouts, independent clones, external worktrees and unsupported creators.

**Independent Test**: A paginated organization fixture and real disposable local stores produce a complete inventory with explicit unmatched/inaccessible coverage. Paths, case and origin URL variations cannot masquerade as ownership.

**Acceptance Scenarios**:
1. Given lanes and non-lane worktrees, reconciliation records both.
2. Given an inaccessible repository or broken Git registry, coverage is incomplete with an actionable reason, never silently complete.
3. Given a foreign remote or similarly named directory, no organization identity is inferred from its name.

### User Story 2 — Close completed work safely (Priority: P1)

A released workspace whose exact contents are durably delivered is retired through its supported creator interface. Every refusal is retained with a reason and retry checkpoint.

**Independent Test**: A real Git worktree is removed after accepted delivery and owner release; the same fixture with a late local change, hold or branch drift remains intact.

**Acceptance Scenarios**:
1. Given valid exact delivery, no local state, no runtime dependency and released ownership, the creator adapter retires once and records the result.
2. Given dirty/untracked/valuable ignored data, nested repositories, active producers, new leases, unknown owners or unsupported creator operations, the workspace is retained.
3. Given squash/rebase delivery, explicit content/PR evidence is required; an ancestor or branch-name match alone does not suffice.
4. Given a primary checkout or independent clone, Git-worktree removal is refused; canonical primary checkouts are never automatically retired. Independent clones require an explicit supported generation-bound owner procedure.

### User Story 3 — Recover missed events (Priority: P2)

Completion and startup/resume use one idempotent lifecycle. An interrupted intent is reconciled from current facts rather than repeated blindly.

**Independent Test**: Replay events, interrupt before/after adapter completion and run concurrent reconciliation. One terminal retirement is recorded; changed identity is retained.

### User Story 4 — Automatic closeout and branch disposition (Priority: P1)

**Independent Test**: The supported Spec Kitty completion path and an explicitly registered non-lane Git creator emit accepted delivery and generation-bound owner release. The running lifecycle reconciler retires the eligible disposable workspace and its exclusively owned merged branch without another model prompt or manual reconciliation command. Startup recovery reaches the same result after a missed completion event. Codex-managed archive remains incomplete until its supported creator interface is demonstrated; observing SessionEnd is not that demonstration.

**Acceptance Scenarios**:
1. A replacement workspace at the same path and same commit/branch has a different creator generation; prior evidence cannot retire it.
2. Forged or stale release inputs cannot authorize retirement; a producer requesting a new lease during retirement is fenced until the disposition is settled.
3. Protected refs, branches checked out elsewhere and refs with changed tips are retained. Local and remote branch outcomes are distinct; unsupported remote retirement is retained explicitly.
4. Canonical primary checkouts are never automatically retired. Independent clones require their explicit supported generation-bound owner procedure.

### Edge Cases

Missing remote permission, stale inventory, malformed/truncated state, symlinked registries, moved workspace, reused path, no active process record, untrusted release input, partial adapter failure, protected primary branch, active working directory, disconnected managed creator, expired lease and valuable ignored artifacts. Absence of a process in a snapshot is not proof that no future producer exists.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status | Delivery | No-op passable? |
|---|---|---|---|---|---|---|
| FR-001 | Organization discovery | As an operator, I need authenticated paginated repository inventory matched to bounded local Git roots, common stores and registered workspaces, with explicit coverage gaps. | High | Accepted | [build] | no |
| FR-002 | Durable accounting | As an operator, I need every discovered workspace recorded as active, owned, eligible, retained, failed or retired with exact identity and reason. | High | Accepted | [build] | no |
| FR-003 | Creator lifecycle | As an orchestrator, I need supported creator registration, completion, release and delivery events connected to the same lifecycle without requiring lane membership. | High | Accepted | [build] | no |
| FR-004 | Safe retirement | As an owner, I need exact identity, delivery, release, state/ignored/nested data and runtime holds rechecked under the supported lock before creator retirement. | High | Accepted | [build] | no |
| FR-005 | Replay and recovery | As an operator, I need durable intents, idempotent event replay and startup/resume recovery with explicit unresolved outcomes. | High | Accepted | [build] | no |
| FR-006 | Branch-first | As a contributor, I need planning, operations and consolidation to preserve local and remote primary branches until PR acceptance. | High | Accepted | [ratchet] | yes — paired with successful feature-branch flow |
| FR-007 | Complete closeout | As an operator, I need workflow completion and cleanup completion reported separately; unresolved eligible workspaces prevent a false cleanup-complete claim. | High | Accepted | [build] | no |

| FR-008 | Generation and fencing | As an owner, I need every release, hold, delivery and intent bound to the creator workspace generation and owner lease generation, authenticated by the configured creator authority; the creator fences new ownership through retirement. | High | Accepted | [build] | no |
| FR-009 | Branch disposition | As an operator, I need eligible owned merged branches accounted for and safely retired, preserving protected/shared refs and all other checkouts. Remote branch deletion requires a supported accepted-PR owner procedure. | High | Accepted | [build] | no |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|---|---|---|---|---|---|
| NFR-001 | Preservation | Zero deletions of active, dirty, unknown, primary or runtime-dependent fixtures across all negative acceptance cases. | Safety | High | Accepted |
| NFR-002 | Bounded execution | Every external inventory/adapter operation has a configured finite timeout; SessionEnd records only a bounded event within the documented maximum 3 seconds. | Reliability | High | Accepted |
| NFR-003 | Evidence fidelity | Every retirement result binds exact repository, common store, path, HEAD, branch, owner release, delivery and adapter result. Unknown measurements remain unknown. | Auditability | High | Accepted |
| NFR-004 | Validation | Changed executable statement coverage at least 90 percent; required baseline and affected subsystem gates pass; independent review before publication. | Quality | High | Accepted |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|---|---|---|---|---|---|
| C-001 | Owning layer | Lifecycle belongs in Spec Kitty; no arbitrary Git-hook cleanup and no destructive probabilistic inference. Reuse existing guards, locks and creators. | Architecture | High | Accepted |
| C-002 | Existing work | Preserve other owners and native Zig work. Reuse this existing checkout; do not create another lane checkout. | Ownership | High | Accepted |
| C-003 | Deployment hold | No deployment retry, cloud mutation, Store access, global runtime installation or hook trust bypass is authorized by this mission. | Scope | High | Accepted |
| C-004 | Managed workspaces | Codex-managed retirement must use the supported creator API. Never edit app databases or substitute raw Git removal. | Safety | High | Accepted |

## Success Criteria

- **SC-001**: Real disposable lane and non-lane workspace fixtures are both discovered and durably accounted for. [build]; no-op passable: no.
- **SC-002**: A released/delivered safe fixture retires once; all preservation controls refuse without data loss. [build]; no-op passable: no.
- **SC-003**: Replay, interruption and concurrent recovery cannot duplicate retirement or hide an unknown outcome. [build]; no-op passable: no.
- **SC-004**: Supported creator completion/startup integration exercises the production lifecycle path; managed adapter limitations and required trust/admission remain explicit. [build]; no-op passable: no.
- **SC-005**: Source and generated guidance enforce feature/integration consolidation with PR-only primary advancement. [ratchet]; no-op passable: yes — paired with feature delivery positive control.

## Assumptions and Boundaries

Authenticated visibility does not prove membership in inaccessible repositories. Local root discovery is configured and bounded; inaccessible or out-of-root stores remain visible coverage gaps. Existing unregistered owners cannot be invented. A managed creator may require a supported connection not available to a local hook; retain and retry through that creator. The first custody repair is PR112 and remains independently reviewable. Historical Op records and evidence are preserved.
