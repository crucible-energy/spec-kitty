# Organization workspace lifecycle — tasks

These packages are authored for the accepted specification. Canonical finalization admitted all five packages; implementation/review transitions remain separate; no runtime claim or done event is inferred from source edits.

## WP01: Verified organization discovery and accounting

Depends on: none

Requirement Refs: FR-001, FR-002, SC-001, NFR-001, NFR-002, NFR-003

- [ ] T001 Implement, validate and review verified organization discovery and accounting.

## WP02: Durable lifecycle state and generation-bound recovery

Depends on: WP01

Requirement Refs: FR-002, FR-004, FR-005, FR-007, FR-008, SC-003, SC-001, NFR-001, NFR-003

- [ ] T002 Implement, validate and review durable lifecycle state and generation-bound recovery.

## WP03: Supported creator adapters and automatic ingress

Depends on: WP02

Requirement Refs: FR-003, FR-004, FR-005, FR-008, FR-009, SC-002, SC-004, NFR-001, NFR-002

- [ ] T003 Implement, validate and review supported creator adapters and automatic ingress.

## WP04: Branch-first consolidation and guidance

Depends on: WP01

Requirement Refs: FR-006, SC-005, C-001

- [ ] T004 Implement, validate and review branch-first consolidation and guidance.

## WP05: Integrated recovery acceptance and adoption

Depends on: WP01, WP02, WP03, WP04

Requirement Refs: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, SC-001, SC-002, SC-003, SC-004, SC-005, NFR-002, NFR-004, C-002, C-003, C-004

- [ ] T005 Implement, validate and review integrated recovery acceptance and adoption.

## WP06: Owned code-kind acceptance and strict closeout

Depends on: WP05

Requirement Refs: FR-005, FR-007, FR-008, SC-003, C-001, C-003

- [ ] T006 Preserve the admitted checkout through code-kind acceptance, prove missing matrices cannot be silently skipped, and finish strict local acceptance without altering prior approvals or runtime admission.


## WP07 — Typed operation custody and closeout integration

- [ ] T007 Replace raw operation custody with a canonical opaque fact and repair stale strict-closeout integration fixtures. Depends on WP05. Covers FR-006/FR-007/FR-008, SC-005 and C-001/C-003; validate red-first, full owning/architecture/baseline gates and independent review.

## Work Package WP08: Native durable useful-work finish obligations

**Dependencies**: WP07

**Requirement Refs**: FR-010, NFR-001, NFR-003

T008 Exact owner/purpose/next/review obligations and revisioned history in Zig. Strict bounded schema, private no-follow persistence and durable writes; reject stale updates and implicit missing-history reset. Never grant release/deletion authority. Focused behavior tests and ReleaseSafe build; independent review.

## Work Package WP09: Automatic creator integration and distribution

**Dependencies**: WP08, WP11

**Requirement Refs**: FR-011, FR-003, FR-004, FR-005, NFR-001

T009 Integrate native obligations into supported creator startup/completion/recovery. Python edits are bounded migration glue; new implementation/tests use Zig. Package exact artifacts, refuse unsupported creators, and prove actual asynchronous cleanup plus preservation/interruption. No broad prune or trust bypass.

## Work Package WP10: Organization rollout and observed closeout proof

**Dependencies**: WP09

**Requirement Refs**: FR-012, SC-006, FR-007

T010 Deliver source chain and runtime, admit every authenticated repo by exact ID, record runtime/creator/ingress/execution receipts. Preserve useful historical state with accountable follow-through. No metadata-only pass, concurrent-capacity attribution or protection bypass.

## Work Package WP11: Retirement delivery and recovery proof

**Dependencies**: WP07

**Requirement Refs**: FR-004, FR-005, FR-008, FR-009, FR-011, SC-006, NFR-001, NFR-003

T011 Repair retained creator delivery/recovery safety with real Git counterexamples and independent review. WP09 depends on this safety gate as well as WP08.

## Work Package WP12: Restore branch-first integration acceptance

**Dependencies**: WP04, WP07

**Requirement Refs**: FR-006, FR-009, SC-005, NFR-001

T012 Correct inherited protected-target fixture propagation and canonical OS/status-contract integration without weakening production guards. Preserve exact red evidence, active ownership and original primary/protected cases.
