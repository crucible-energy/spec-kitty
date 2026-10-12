# Work Packages: Native Local Validation

Status: Finalized tasks; independent plan and task review passed. No implementation claim or native qualification is established.

Planning branch: `codex/native-local-validation`. Review base: `fix/owned-analysis-implementation`. Use the existing single-branch checkout; no parallel agent dispatch or new worktree.

Inputs: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), and [contract](contracts/local-validation.md). Tests are explicitly required. Task completion is event-sourced, not a Markdown checkbox.

## Subtask Index

| ID | Description | Work package |
| --- | --- | --- |
| T001 | Reproduce selection refusal and parity failures | WP01 |
| T002 | Extract the one versioned local specification | WP01 |
| T003 | Implement deterministic native selection | WP01 |
| T004 | Migrate existing consumers and retain equivalence proof | WP01 |
| T005 | Reproduce partial-staging and drift failures | WP02 |
| T006 | Materialize the candidate without live-source fallback | WP02 |
| T007 | Bind receipts and first-party import identity | WP02 |
| T008 | Prove positive reuse and paired invalidation | WP02 |
| T009 | Commit real execution and escape RED controls | WP03 |
| T010 | Adapt the reviewed Darwin ownership foundation | WP03 |
| T011 | Execute dependency-ordered checks with retained logs | WP03 |
| T012 | Qualify real platform backends | WP03 |
| T013 | Commit RED through the actual Git commit path | WP04 |
| T014 | Implement the shared native public entry | WP04 |
| T015 | Compose and install hooks safely | WP04 |
| T016 | Qualify recovery, proof reuse, and the documented workflow | WP04 |
| T017 | Commit RED qualification and publication controls | WP05 |
| T018 | Preserve explicit full, release, platform, and publication modes | WP05 |
| T019 | Independently qualify equivalence and refresh remote requirements | WP05 |
| T020 | Retire hosted execution and reconcile valid contracts | WP05 |

## Work Package WP01: Canonical specification and native selection

Prompt: [tasks/WP01-canonical-selection.md](tasks/WP01-canonical-selection.md)

Requirement Refs: FR-003, FR-004, NFR-003, C-002, C-003

Priority: P1. Independent Test: Actual selection agrees for discriminating source, test, docs, tooling, unknown, full, and platform cases. Missing tools or malformed authority refuse visibly. Selection inspection cannot publish.

### Included Subtasks

T001 Reproduce selection refusal and parity failures (WP01)
T002 Extract the one versioned local specification (WP01)
T003 Implement deterministic native selection (WP01)
T004 Migrate existing consumers and retain equivalence proof (WP01)

### Dependencies

None.

### Implementation Notes

Own declared paths, preserve validator authority, and commit actual RED before production changes. Execute serially through the existing owned single-branch mission. Evidence and implementation are independently reviewed; no approval prompt to Sam is needed for routine engineering.


## Work Package WP02: Exact staged candidate and reusable check evidence

Prompt: [tasks/WP02-candidate-evidence.md](tasks/WP02-candidate-evidence.md)

Requirement Refs: FR-002, FR-005, FR-006, FR-008, NFR-001, C-004

Priority: P1. Independent Test: Both directions of partial staging use staged content. Matching per-check closure reuses proof; each relevant drift invalidates it. Incomplete/tampered/old global receipts refuse. Work, imports, and topology stay protected.

### Included Subtasks

T005 Reproduce partial-staging and drift failures (WP02)
T006 Materialize the candidate without live-source fallback (WP02)
T007 Bind receipts and first-party import identity (WP02)
T008 Prove positive reuse and paired invalidation (WP02)

### Dependencies

Depends on WP01.

### Implementation Notes

Own declared paths, preserve validator authority, and commit actual RED before production changes. Execute serially through the existing owned single-branch mission. Evidence and implementation are independently reviewed; no approval prompt to Sam is needed for routine engineering.


## Work Package WP03: Native execution, diagnostics, and platform supervision

Prompt: [tasks/WP03-owned-execution.md](tasks/WP03-owned-execution.md)

Requirement Refs: FR-004, FR-007, NFR-002, NFR-005, NFR-004, C-001

Priority: P1. Independent Test: Success/failure discriminate; actual owned terminal cleanup is observed. Detached controls cannot pass solely on group_disposed. Raw quota failures retain diagnostics. Process/RSS samples are not hard peak claims. Each supported platform has real evidence.

### Included Subtasks

T009 Commit real execution and escape RED controls (WP03)
T010 Adapt the reviewed Darwin ownership foundation (WP03)
T011 Execute dependency-ordered checks with retained logs (WP03)
T012 Qualify real platform backends (WP03)

### Dependencies

Depends on WP01, WP02.

### Implementation Notes

Own declared paths, preserve validator authority, and commit actual RED before production changes. Execute serially through the existing owned single-branch mission. Evidence and implementation are independently reviewed; no approval prompt to Sam is needed for routine engineering.


## Work Package WP04: Public native entry and real hook integration

Prompt: [tasks/WP04-commit-entry.md](tasks/WP04-commit-entry.md)

Requirement Refs: FR-001, FR-006, FR-008, SC-001, SC-002, SC-003, SC-005, C-001, C-004

Priority: P1. Independent Test: Actual passing commits succeed and failing staged proposals refuse. Existing work and custom hooks survive installation and recovery. Candidate/tool drift refuses; owned children are joined. A shell-only bypass cannot provide native acceptance.

### Included Subtasks

T013 Commit RED through the actual Git commit path (WP04)
T014 Implement the shared native public entry (WP04)
T015 Compose and install hooks safely (WP04)
T016 Qualify recovery, proof reuse, and the documented workflow (WP04)

### Dependencies

Depends on WP01, WP02, WP03.

### Implementation Notes

Own declared paths, preserve validator authority, and commit actual RED before production changes. Execute serially through the existing owned single-branch mission. Evidence and implementation are independently reviewed; no approval prompt to Sam is needed for routine engineering.


## Work Package WP05: Local qualification and publication, then hosted retirement

Prompt: [tasks/WP05-qualified-retirement.md](tasks/WP05-qualified-retirement.md)

Requirement Refs: FR-009, FR-010, NFR-004, SC-004, C-002, C-003, C-005, C-006

Priority: P1. Independent Test: No requirement or intentional publication disappears. Missing platform/ref/credential proof refuses. Final local authority has no deleted-YAML dependency or second editable routing map. Retirement and guidance agree with observed remote requirements.

### Included Subtasks

T017 Commit RED qualification and publication controls (WP05)
T018 Preserve explicit full, release, platform, and publication modes (WP05)
T019 Independently qualify equivalence and refresh remote requirements (WP05)
T020 Retire hosted execution and reconcile valid contracts (WP05)

### Dependencies

Depends on WP01, WP02, WP03, WP04.

### Implementation Notes

Own declared paths, preserve validator authority, and commit actual RED before production changes. Execute serially through the existing owned single-branch mission. Evidence and implementation are independently reviewed; no approval prompt to Sam is needed for routine engineering.
