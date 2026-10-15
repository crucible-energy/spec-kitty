---
title: Native Local Validation REASONS Canvas
description: Retrospective reasoning for delivered native selection and the remaining local validation work.
doc_status: active
audience: ../../docs/context/audience/internal/ai-collaboration-agent.md
updated: '2026-10-14'
---

# REASONS Canvas — Native Local Validation

> Mission: native-local-validation-01M4S619
> Generated: 2026-10-14 (America/Chicago), **RETROSPECTIVE**
> Charter activation: structured-prompt-driven-development, reasons-canvas-fill, reasons-canvas-review, and directive 038.

This canvas did not exist before implementation. It is authored in response to
[review-cycle-1, finding R1](tasks/WP01-canonical-selection/review-cycle-1.md),
classified `canvas_update_needed`. It reconstructs intent from existing authorities
and retained evidence; it does not invent prior approval or replace that finding.
WP01 product correctness passed independent review at `fb2f3c887e61470a80732f6c0852738e9159143f`;
canonical approval was withheld for the missing canvas. This document still needs
independent Requirements, Operations, Norms, and Safeguards comparison.

## Requirements

The mission must validate the proposed commit without losing existing requirements;
WP01 delivers its canonical selection foundation, not the complete gate.

- R1 — [FR-003, FR-004, NFR-003, C-002, and C-003](spec.md#requirements)
  require one authority, deterministic selection, preserved validators, and visible
  refusal. [WP01 T001–T004](tasks/WP01-canonical-selection.md#subtasks-and-detailed-guidance)
  define source/test/docs/tooling/unknown/full/platform discrimination, extraction,
  native selection, and consumer equivalence. These are the delivered product scope.
- R2 — WP01's [test strategy](tasks/WP01-canonical-selection.md#test-strategy)
  requires genuine native statement coverage of at least ninety percent and complete
  denominator evidence. An AST inventory or Python coverage percentage cannot meet it.
- R3 — [WP02–WP05](tasks.md#subtask-index) still own exact staging and reusable
  evidence, execution and supervision, the public entry and hooks, and qualification
  before retirement. Their proposed acceptance scenarios remain requirements, not
  observations established by WP01 inspection.
- Definition of done: the [WP01 definition](tasks/WP01-canonical-selection.md#definition-of-done)
  includes validation, documentation, independent review, and committed/pushed useful
  work. Product PASS does not waive the active reasoning prerequisite or authorize
  this implementation owner to approve it.

## Entities

Use existing domain authorities rather than introduce new meanings in this canvas.

- [Mission](../../docs/context/orchestration.md#mission) and
  [owned checkout](../../docs/context/execution.md#owned-checkout) retain their
  glossary meanings; the stored single-branch mission writes to
  `codex/native-local-validation` in its existing checkout.
- The [evidence model](data-model.md) defines gate specification, candidate binding,
  run, check result, and receipt. WP01 supplies specification and selection behavior;
  their later complete execution lifecycle is not implemented by naming these entities.
- Module IDs, routing groups, checks, dependency edges, normalized programs, and
  context requirements remain data in the [one specification](../../tools/validation/gates.json).
  A module projection is an inspection result, not a check result or accepted receipt.

## Approach

Preserve the existing behavioral authorities while replacing selection ownership
with a native, inspectable foundation.

- The [selected architecture](plan.md#one-routing-authority) extracts routing and
  original workflow provenance into JSON, then migrates consumers. A separately
  editable module policy table would drift; registry-derived mirrors reuse the same
  roots, directories, and routing information.
- [T002](tasks/WP01-canonical-selection.md#t002--extract-the-one-versioned-local-specification)
  explicitly permits refusal of unsupported control semantics. Preserve original
  definitions and blockers rather than manufacture executable equivalence.
- Additive module inspection closes the actual test-mirror parity gap while
  preserving existing whole-gate responses and refusals. The
  [implementation log](../../docs/plans/engineering-notes/2026-10-12-native-local-validation.md#october-14-2026--native-module-and-test-mirror-projection)
  records the paired RED and choice; `a1647fcf29f4b9263d4347ea6b2cf8a71635cca9`
  precedes the product correction at `fb2f3c887e61470a80732f6c0852738e9159143f`.
- The [collector decision](../../docs/plans/engineering-notes/2026-10-12-native-local-validation.md#october-14-2026--complete-the-native-statement-proof-boundary)
  addresses the missing embedded transfer and incomplete denominator. The approved
  ownership amendment is `e6f189128af3c19c39fa1492560768b212033c97`, not a claim that
  the collector was in the original path roster. Unsupported measurement semantics
  refuse; existing entries and unobserved statements are retained.

## Structure

Trace the delivered WP01 surfaces to R1/R2 and the operations below; retain later
package ownership from the finalized task map.

| Responsibility | Source of truth | Requirement / operation |
| --- | --- | --- |
| Extraction, preserved provenance, and schema | [extractor](../../scripts/validation/extract_gates.py), [catalog](../../tools/validation/gates.json) | R1 / O1–O2 |
| Native selection, refusals, and additive module projection | [selector](../../tools/zig/validation_selection.zig) | R1 / O1–O3 |
| Canonical reader and existing parity/completeness consumers | [reader](../../scripts/ci/gate_selection.py), [parity consumer](../../scripts/ci/local_gate_parity.py), [oracle](../../tests/architectural/_ci_integrity_oracle.py) | R1 / O2–O3 |
| Native public-entry controls and paired refusal/success evidence | [selection controls](../../tests/local_validation/test_selection.py), [authority controls](../../tests/architectural/test_gate_selection_authority.py) | R1–R2 / O1–O4 |
| Complete statement inventory and visible measurement refusal | [collector](../../tools/zig/validation_statement_inventory.zig) | R2 / O3–O4 |
| Decisions, limitations, and review history | [owned log](../../docs/plans/engineering-notes/2026-10-12-native-local-validation.md), [review-cycle-1](tasks/WP01-canonical-selection/review-cycle-1.md) | R1–R3 / O4–O5 |

The [task map](tasks.md) assigns staging/receipts to WP02, bounded execution/platform
backends to WP03, installed entry/hooks to WP04, and qualification/publication/hosted
retirement to WP05. Existing prerequisite and companion history remains preserved;
this canvas neither reallocates it nor claims it as new work. Compiler-parser
witnesses and raw run receipts are external evidence, not another product service.

## Operations

Retrospective observations and remaining actions are distinguished explicitly.

1. O1 — Observed: genuine selection, normalization, collector, and module-mirror RED
   controls were retained before their corrections. Review their actual failures and
   paired successes in the [log](../../docs/plans/engineering-notes/2026-10-12-native-local-validation.md)
   and [preserved product finding](tasks/WP01-canonical-selection/review-cycle-1.md#preserved-product-verdict-and-evidence).
2. O2 — Observed: extraction retains original workflows, conditions, dependencies,
   budgets, argv or unsupported dispositions, and provenance. Existing default
   consumers use JSON; hosted YAML is a pinned migration oracle during transition,
   not permission to maintain two editable policies.
3. O3 — Observed: native schema/path/ID/edge/cycle/budget/mode/platform refusal and
   positive selection controls preserve dependency closure and test mirrors.
   Allocation and input-limit controls exercise actual native boundaries.
4. O4 — Observed: the complete statement collector, independent installed-parser
   witness, compiled semantic sentinels, and original/instrumented pairs establish
   source statement entry. The reviewed selector observes 1149/1248 entries and the
   collector 150/158, separately. Every miss and the initial external witness's
   deferred-body omission remain retained; no entry was excluded to cross a threshold.
   The [product review evidence](tasks/WP01-canonical-selection/review-cycle-1.md#preserved-product-verdict-and-evidence)
   pins the 466-pass/one-skip owning run, 545-pass consumer run, and one required fast
   baseline. These are historical results for their frozen subjects.
5. O5 — Current repair: author this retrospective canvas and append the existing log;
   validate links, structure, docs, and normal required delivery gates on the new
   documentation freeze. Reuse only unchanged relevant product proof. Commit/push,
   re-record actual completed subtasks, and request independent R/O/N/S review through
   supported owned commands. No approval is recorded by the author.
6. O6 — Planned: execute WP02–WP05 sequentially only after their actual dependency
   approvals. Their [acceptance tests](tasks.md) include both partial-staging
   directions, positive per-check reuse and drift invalidation, real Git acceptance,
   joined descendants, qualified platforms, hook preservation, and qualified retirement.

## Norms

The charter and existing validator authorities govern; this reasoning layer adds no
competing policy or invented historical decision.

- Follow [charter governance](../../.kittify/charter/charter.md#governing-principles),
  canonical terminology, plain language, normal spaces, and Oxford commas. Link
  behavior to maintained source instead of mirroring implementations in prose.
- Keep genuine RED, corrected success, immutable freeze, original process join,
  cleanup disposition, and independent review distinct. Use the
  [existing log](../../docs/plans/engineering-notes/2026-10-12-native-local-validation.md)
  for UX findings, decisions, and known limitations; do not rewrite historical notes
  to make this canvas appear earlier.
- Preserve [sequential dispatch](tasks.md), explicit ownership, one intended push
  destination, and reviewer/implementer separation. Record significant deviations
  below without rewriting or reordering prior deviation entries.

## Safeguards

Missing proof must refuse the relevant acceptance boundary and must never erase
local work or become a broader qualification claim.

- Selection inspection must not execute, publish, accept a candidate, or turn an
  uncovered whole-gate surface into successful empty validation. The 92 unbound
  workflow contexts remain disclosed; WP01's permitted unsupported-control refusal
  does not qualify later execution.
- Preserve [staged/unstaged/untracked work and user hooks](contracts/local-validation.md),
  primary-checkout history, admitted lane membership, existing validators, thresholds,
  and unrelated owners' work. No new checkout, dependency, model, credentials, or
  Source/Store effect is authorized by this repair.
- Retain finite execution/cleanup budgets and real joined-process evidence.
  Original-group disposal and sampled process/RSS observations do not prove session
  containment or hard peaks; [later qualification](plan.md#supervision-qualification-boundary)
  must address that gap. Never signal an unowned process.
- Statement entry does not prove expression completion, branches, universal Zig
  semantics, platform qualification, or successful validators. Separate Python
  coverage databases for concurrent suites. Historical shared-database percentages
  and original handle 84965's missing terminal acknowledgment remain limitations.
- Bind reused proof only to matching relevant source, dependencies, toolchain,
  environment, and configuration. New docs have a new freeze. Later
  [positive check reuse and final recheck](plan.md#relevant-input-closure-and-positive-reuse)
  remain WP02 requirements. No merge, deployment, savings, or full-mission completion
  follows from WP01 selection or this document.

## Deviations (append-only)

- 2026-10-14 — WP01 — The required canvas was absent throughout implementation and the first review admission — This retrospective artifact addresses finding R1, `canvas_update_needed`; it cannot retroactively satisfy the before-implementation authoring rule, and independent review remains required.
- 2026-10-14 — WP01 — A maintained statement collector extended the original source roster — Actual denominator omissions required deterministic native collection; approved ownership commit `e6f189128af3c19c39fa1492560768b212033c97` and the existing log retain rationale and evidence without changing admitted lane membership.
- 2026-10-14 — WP01 — Native module projection uses an additive inspection operation — Paired Python/native mirror RED exposed missing behavior; registry-derived projection closes T001/T003 parity while preserving existing whole-gate contracts and execution refusals, as recorded at `a1647fcf29f4b9263d4347ea6b2cf8a71635cca9` and `fb2f3c887e61470a80732f6c0852738e9159143f`.
