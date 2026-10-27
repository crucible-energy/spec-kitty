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

## User Experience Findings

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
