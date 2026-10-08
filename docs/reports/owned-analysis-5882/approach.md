---
title: 'Owned analysis and implementation: bounded fix approach'
description: 'Implementation scope, outside-in findings and validation approach for the explicitly delegated SDK dependency fix in issue 5882.'
type: explanation
updated: '2026-10-08'
---

# Approach — #5882

Audience: the SDK orchestrator and independent source reviewer.

This is an explicitly delegated dependency fix, not an admitted work package.
The existing lane is `fix/owned-analysis-implementation`, originally based on
`1af6a711074e45359ddfe568dd71f057286a13ee`. The operator delivered the preceding
repair as `e86a792e5338d0b344456f1e1d9e5cfea2259afb`; the next compatibility
increment starts from that clean revision. Sam approved lane reuse at
`2026-10-08T08:04:51Z`, with delivery-or-24h expiry
`2026-10-09T08:04:51Z`. Source changes remain uncommitted for orchestrator review.

The implementation context loaded **python-pedro** through the real
`profiles show python-pedro --json` CLI. The branch charter was read in full.
Standalone Op placement cannot safely target this lane; see
[tooling-friction](tooling-friction.md). No admitted Mission/WP or Op is claimed.

## User Experience Findings

- At the unchanged base, the real `record-analysis` sub-app rejects
  `--owned-checkout` with a usage error. Owned implementation is also refused.
- An owned resolved workspace has no lane ID. Merely threading the ownership
  fact left the checkout occupancy and dirty guards inactive. A second real
  implementation command demonstrated the defect before the guard fix.
- Canonical feedback lookup could consult a stale repository-root Mission and
  ignore the owner's missing feedback. A real CLI reproduction now pins refusal
  and a positive owner-local fix-mode case.
- The generic planning-workspace prompt pointed at repository-root artifacts
  and described coordination commits. Owned implementation now identifies its
  exact workspace, artifact home and write branch in the prompt.
- Independent review identified P1 blocker **B1**: wrapped owner reports could
  omit transaction/manifest fields and downgrade to optional V1 freshness. The
  real CLI reproduced admission for a tokenless canonical wrapper, a stripped
  failed wrapper, and a tokenless wrapper with a committed WP-definition change.
  The owned read path now requires qualification and a complete supported
  manifest. All three refuse before claim after the fix; ordinary V1 behavior
  remains optional. Renderer operations were not restricted as a substitute for
  read-side enforcement.
- Actual native recording subsequently refused the documented canonical alias
  `zig/docs -> ../docs` before writing. The exact mode-120000/blob identity was
  reproduced in real sandbox Git fixtures. Canonical content remains rooted at
  `docs`; alias identity is now included separately without a duplicate master.
  Tests retain external/dangling/cycle/untracked/unsafe-ancestor refusals and
  prove content, membership, retargeting and transaction races invalidate proof.
- Independent review B2 found that deferred traversal let template prerequisite
  resolution read externally linked Mission metadata before refusing it. Both a
  real external metadata link and linked metadata ancestor reproduced one
  delegated content read before the fix. Strict metadata boundary validation and
  pre-resolution selected-closure validation now refuse both with zero reads.
  Canonical alias behavior and unsafe-authority policy remain unchanged.

## Validation approach

Real Git fixtures own committed substantive spec/plan/tasks and canonical status
in a linked single_branch checkout. The repository root carries partially
staged, unstaged and untracked sentinels. Assertions cover raw index bytes,
HEAD, status, sentinel bytes, branch/worktree registries, report-only commit
scope, claim scope, missing/stale inputs, hooks/races, dependency/dispatch
guards, resume, rollback, profile access, lock holds and canonical feedback.
No ownership/source-path resolver is mocked in these acceptance tests. Lock
observers call the real guarded paths. Ordinary routing and owned REVIEW
refusals retain their existing regression controls.

See [evidence](evidence.md) for executed commands and outcomes.

## Cold-bootstrap template provenance continuation

The renewed bounded authorization starts from clean
`604c63621c547c9e1f2d29b19171d311a33b39a5` in the same owned SDK checkout and
branch. The reported native failure was reproduced through the root source CLI,
which runs ordinary runtime bootstrap before recording. Python Pedro was loaded
through the source CLI; a separate profile-loaded, read-only investigation
confirmed the existing package-only resolution API and bootstrap ownership seam.

The correction qualifies a selected mission-scoped global template only against
its exact canonical bundled counterpart. It binds the replica's selection and
stable filesystem identity in the complete material manifest, retains the
existing package content pins, and repeats descriptor-safe proof during every
collection and transaction recheck. Mutable, foreign, linked and unverifiable
selections refuse. Root bootstrap remains part of the acceptance tests.

Real cold-HOME CLI tests cover both owned recording modes, ordinary default and
report-only recording, post-bootstrap unsafe selection, post-report changes,
HOME retargeting, equal-byte replacement, and real pre/post-commit hook races.
Supplemental read observers test package-pin coupling and transient read races
without changing SDK package bytes. No native recording or admission was run.

### Renata template-provenance re-review: B1 and B2

Both P1 findings were reproduced before their respective source edits. B1's
regular-file ancestor was read even though classification later refused it;
ancestor classification now requests metadata only. Zero-read observers cover
both the stable file and a file-to-external-symlink race after `lstat`.

B2's temporary source-subtree disappearance escaped pin completeness checks
when the subtree returned before final observations. Required package members
now come from the already-selected proofs; each must contribute a
digest-verified row. The full-collector reproduction uses temporary copied
package assets and the real canonical path/definition resolvers. Independent
re-review is pending; this pass changes only those two production seams.
