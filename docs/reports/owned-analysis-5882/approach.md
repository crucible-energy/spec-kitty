---
title: 'Owned analysis and implementation: bounded fix approach'
description: 'Implementation scope, outside-in findings and validation approach for the explicitly delegated SDK dependency fix in issue 5882.'
type: explanation
updated: '2026-10-08'
---

# Approach — #5882

Audience: the SDK orchestrator and independent source reviewer.

This is an explicitly delegated dependency fix, not an admitted work package.
The existing lane is `fix/owned-analysis-implementation`, based on
`1af6a711074e45359ddfe568dd71f057286a13ee`. Sam approved lane reuse at
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
