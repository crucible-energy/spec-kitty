---
title: Target acceptance evidence preservation repair
description: Record the pending-target consolidation defect, bounded repair decisions and validation obligations.
type: explanation
doc_status: point_in_time
updated: '2026-10-27'
---

# Target acceptance evidence preservation repair

## Current state

Owner: Subsequent mission owner, coordinated with the existing Root Source owner.
Branch: `codex/owned-lanes-analysis`; declared integration target:
`codex/organization-workspace-lifecycle-20261020`.
Tracked defect: [Spec Kitty #136](https://github.com/crucible-energy/spec-kitty/issues/136).
Governed Op: `01M5YN4J93DYREY9Y19MM7K1WW` (Python Pedro).

Observed on October 27, 2026: the preservation guard snapshots any existing target
matrix and restores its bytes after consolidation. Its documented prerequisite
is an already accepted target, but the implementation never checks that
prerequisite. This can restore an old pending scaffold over newer accepted
mission evidence. The reverse-direction regression demonstrated two intended
failures, while the original
accepted-target case passed. Red-first commit `b0a680b53f` records it separately.
The first focused post-fix run passed 69 tests but failed both real integration
cases at their issue-metadata assertions. The canonical acceptance guard and
issue metadata placeholder correction are implemented. The corrected focused
run passed all 85 tests at 13:18:26 UTC, including the real Git integration,
malformed-input controls and authored metadata tie behavior. Broader required
validation, review and delivery remain open. This log is frozen before those
final gates; subsequent outcomes belong in the external receipts and tracked
issue, without changing the validated candidate merely to record a pass.

The inherited typing blocker was subsequently reproduced on unchanged target
source and repaired through the canonical module-follow rule. The exact strict
two-module invocation and real valid/invalid callable regression both passed at
13:37:42 UTC. Preserve the first broader gate's typing failure; baseline and
owning-subsystem validation still require a fresh run on this corrected candidate.

Both subsequently identified Native authority findings are corrected through
canonical acceptance-evidence and captured issue-readiness validation. The
combined strict two-module check and 98 focused tests passed at 14:24:30 UTC,
with unchanged source and a naturally joined producer. Freeze this correction
for independent final review before the next complete required delivery gate;
no ready PR, merge or installed-runtime qualification is established here.

## User Experience Findings

- The paired issue-artifact boundary needed its own validation: canonical merge
  gates check the coordination matrix, not a divergent captured target copy.
  Actual corrected old-helper regressions showed six invalid target issue
  restorations while two filled controls passed. The initial run proved two
  no-gating failures but five other cases stopped at a fixture precondition;
  canonical discovery recognizes two-to-six-digit references, so use `#1582`
  instead of the fixture's unsupported `#1`. Preserve that initial run without
  crediting the five setup failures as causal product regressions.

- Native independent review of `ee658fce59` found that the computed passing
  verdict does not validate required manual-QA evidence or recorded negative
  invariant provenance. The passing broader gate and earlier bounded reviews
  missed that evidence-completeness layer. Actual old-helper regressions showed
  two invalid target restorations while both complete-evidence controls passed.
  The separate red regression commit precedes the canonical validation call.

- The first broader delivery gate passed formatting and lint but stopped at
  three strict `untyped-decorator` errors before baseline/subsystem tests ran.
  Exact original integration-target files reproduce all three under the same
  invocation. This inherited blocker is tracked as
  [Spec Kitty #137](https://github.com/crucible-energy/spec-kitty/issues/137).
  Its real callable-contract regression failed at the valid-call assertion
  before the typing configuration changed; record that separate red commit.

- Independent Root review found that deeply nested JSON raises `RecursionError`,
  outside the initial malformed-input handler. A bounded 4,096-byte, 2,048-level
  input reproduced that error through the existing restore helper (one intended
  failure, 68 deselected). The separate regression commit precedes the explicit
  exception handler; no alternative parser or invariant execution is needed.
- Coordinator review found a post-start receipt-write gap in the external
  validation wrapper. Reuse the already qualified Aletheia lifetime handlers
  before fallible writes. Actual receipt-write failure and cancellation controls
  both returned failure and joined the original child and its descendants;
  preserve these administrative proofs separately from product acceptance.

- Aletheia's normal consolidation completed and advanced its target, but its
  authentic acceptance matrix was subsequently replaced with the target's old
  pending placeholder. Successful consolidation alone did not prove preservation
  of the accepted evidence.
- The pre-existing regression covered an accepted target and a stale incoming
  scaffold. It did not cover a pending target and an accepted incoming mission.
- After the acceptance guard was corrected, real consolidation preserved the
  incoming issue verdict but combined it with the target's `<link or commit>`
  evidence placeholder and scaffold title. The canonical driver recognized the
  unset verdict but treated unfilled metadata as authored target content.
- A stored `overall_verdict` is not authoritative: the canonical matrix model
  computes it from criteria and negative invariants. A misleading stored `pass`
  must not activate the preservation guard.

## Engineering Decisions

- Validate each captured issue copy through the existing content-aware domain
  evaluator. It combines schema/business checks with canonical missing-row and
  nonterminal checks against current primary requirements. Do not use the
  approval blocker's zero-gating early return as schema validation, read the
  post-merge matrix instead of the snapshot, duplicate verdict sets, or create
  new obligations for missions without gating references. A rejected issue copy
  leaves incoming issue proof authoritative while valid acceptance remains
  independently protected. No invariant execution or row reconciliation is added.

- Reuse the pure `validate_matrix_evidence` alongside matching mission identity
  and the computed ready verdict. Do not duplicate evidence rules or execute
  negative invariants. Preserve existing legacy/deferred semantics and require
  real evidenced controls alongside the incomplete manual-QA/recorded-NI cases.

- Root approved one existing mypy module-follow override for the already typed
  consolidation recorder. Following its canonical `ParamSpec` declaration
  restores real signature checking; the read-only control passed strict checks
  for both affected modules. Preserve the helper body and strictness settings;
  do not ignore errors, introduce stubs or redeclare its signature at callers.
  The regression tests valid and invalid calls through the actual type checker,
  rather than merely matching configuration text.

- Fix the existing owning Python consolidation path. This bounded correctness
  repair does not introduce a new Python backend. Subsequent's new acceptance
  tooling remains Zig under its updated language and safety policy.
- Keep the real consolidation entry point, Git integration and existing accepted
  target regression. Extend the existing fixture to exercise the reverse
  direction, including a misleading stored verdict. Commit the demonstrated
  failing regression separately before implementation, as required by charter.
- Decide preservation from the exact captured acceptance bytes
  using the canonical matrix model, without re-reading a changing file or
  executing negative invariants. A target that was not accepted cannot activate
  the paired acceptance/issue artifact preservation guard. Row reconciliation
  remains the canonical merge drivers' responsibility.
- Correct issue metadata in the existing canonical row driver, using the
  scaffolder's exact evidence and title placeholder constants. An unfilled
  token yields to authored content in either direction. Two authored metadata
  values retain the established target tie; genuinely conflicting verdicts
  remain fail-closed. Do not add guard-side row reconciliation or a heuristic
  based on artifact size, row count or apparent completeness.
- Preserve active WP04 source and planning documents in their existing lanes.
  Hash-verified external copies retain all eleven active files. Do not replace
  installed runtimes or repeat the accepted native capture to repair metadata.
- Use the current published non-yanked release including prereleases for workflow
  admission. The isolated official `4.0.0rc7` was verified at 12:45:57 UTC;
  all 1,047 installed package files matched its published wheel. Organization
  properties require latest prereleases and owner-scoped useful-work closeout.
  Runtime identity and source repair delivery remain separate facts.

## Known Limitations

- Final review must close both Native findings: acceptance evidence completeness
  and independent captured issue readiness. The historical 90-test focused pass
  covered only the first correction. Earlier passing checks and bounded reviews
  did not prove either missing authority layer; retain that review limitation
  in the external closeout ledger. Validate and review the newly frozen source
  before another full required gate or ready PR.

- Candidate `ee658fce59` passed the complete R2 local gate and was pushed as a
  historical validated increment. Native review then exposed the evidence
  completeness P2; no full PR, merge or runtime qualification was claimed.
  Publication readiness is held until the correction is validated, reviewed and
  delivered. Preserve the earlier pass and its review limitation explicitly;
  it is not acceptance of this newer candidate.

- The first broader gate stopped at inherited strict typing. Formatting/lint
  passed, while baseline/subsystem/remaining gates did not run. After the narrow
  typing correction, re-freeze and run the required gate; no earlier broad pass
  can be reused or invented.

- Preserve the original two-failure baseline, the first post-fix run with 69
  passes and two issue-evidence failures, and the separate deep-JSON failure.
  The corrected focused run passed 85 tests, naturally joined its owned group,
  and retained unchanged source with no artifact, descriptor, cleanup or final
  capacity errors. This focused result is not the required full owning-subsystem
  baseline, final review, delivery or installed-runtime qualification.
- Final source and documentation must be frozen before broader delivery gates;
  record those outcomes externally so evidence recording does not alter the
  validated candidate.
- Root owns supported recovery of Aletheia's actual accepted matrix and installed
  runtime qualification. Source package repair does not itself prove either.
- The prior source increment was squash-delivered to the declared integration
  target. Before publishing this repair, normally merge the fresh target into
  the existing branch, verify ancestry and the bounded final diff, and preserve
  existing history. Do not reset, force-push or claim default-branch delivery.
- WP04 remains in progress. Native tools, actual acceptance proofs, required
  gates, independent review and Subsequent production acceptance remain open.
