---
title: 'Recovery: Cutover Flip Fails From a Linked Worktree'
description: 'Recovery when the runtime-state cutover flip fails closed with PlacementMismatchError inside a linked git worktree, even though migration events seeded.'
doc_status: active
type: how-to
updated: '2026-10-26'
related:
- docs/operations/recovery-index.md
- docs/archive/plans/engineering-notes/coord-splitbrain-rootcause.md
---

# Recovery: Cutover Flip Fails From a Linked Worktree

`spec-kitty cutover-guard --base-ref <ref>` reports `status_phase not flipped
despite event-log runtime evidence`, or `cutover_mission()` raises
`PlacementMismatchError`, even though the migration events were seeded
successfully.

## Why this happens

`cutover_mission()` (seed → verify → flip) is run from a linked git
worktree — for example a `.worktrees/pr-*-landing` landing worktree.
`_flip_phase` (`src/specify_cli/migration/runtime_state_cutover.py`)
resolves the PRIMARY home via `resolve_canonical_root`, which maps a linked
worktree back to the **primary checkout**. It then compares that absolute
primary-checkout path against the (relative, worktree-scoped) write target.
They never match, so the flip fails closed before writing `status_phase` — a
correct, intentional refusal, not a bug. The seed events still get written
(they append to a relative path), so only the flip step is blocked.

## No shipped `--fix` for this case

`spec-kitty doctor cutover` is informational only — it always exits 0 and
reports a per-mission cut-over verdict, but it has no `--fix`. Its
whole-corpus `--dry-run` spine also reads from a different root than a
single worktree expects (it can report `would_flip` for missions already
flipped on `main`), so trust the CI `cutover-guard` per-mission verdict over
a whole-corpus dry-run when you're inside a worktree.

## Preview a retained owned checkout

When the retained Mission is absent from a busy repository root checkout,
inspect that retained checkout explicitly instead of copying its history into
the root. Check the selected executable's command help for `--owned-checkout`;
an older installed package may not contain this source change.

```bash
spec-kitty migrate backfill-runtime-state --mission <handle> --owned-checkout <path> --dry-run --json
```

The command validates the existing checkout claim, Mission identity, branch,
index and protection rules through the same ownership validator as `next`.
It previews only that checkout's retained dossier and event history. The JSON
adds `owned_checkout`, `read_scope: retained_checkout` and
`canonical_status_adopted: false`. `retained_verification` exposes the exact
pre-seed runtime verification: `stage: before_seeding`, `ok`,
`runtime_wp_count` and `mismatches`. It is null when verification could not run,
for example after an unreadable-history error. The count covers anchored legacy
runtime entries, not every work package on the board. Missing unwritten seeds
can produce mismatches, so this field is evidence for inspection rather than
an adoption decision. It does not select the live coordination
surface, adopt old approvals, materialize a worktree, change `status_phase`, or
append events. The migration's existing status mutex can create an empty lock
file in the Git metadata; it writes no canonical Mission content.

Read `retained_verification`, each result's `verify_ok`, `failed` and `error`,
and the summary. The older summary suppresses verification mismatches during
dry-run; the owned field retains them, including existing seed conflicts.
As with the existing dry-run command, exit zero means the preview
completed, not that verification passed. Seeds reported as needed have not been
written and therefore cannot be counted as verified migration. This is a
current filesystem inspection, not an immutable source snapshot or a freshness
guarantee; retain the source revision and input hashes with any recovery review.

The explicit owned mode requires both a Mission handle and `--dry-run`.
Omitting either refuses before migration. It never walks the repository's
other Missions. Existing invocations without `--owned-checkout` retain their
original behavior.

## Keep the cutover closed until recovery is verified

When a split coordination status home has no canonical WP state but a
nonempty retained event log exists, `next` reports
`retained_status_reconciliation_required` rather than presenting zero classified
progress as an actionable board. Query mode remains read-only and withholds
progress and the preview step. The same board check refuses advancing work.
This detects retained bytes, not their validity or authority: malformed retained
history also needs inspection. A current canonical WP state remains authoritative;
retained events never replace it. A new board with no retained history keeps its
existing genesis behavior, and malformed canonical history still fails visibly.

For coordinated Missions, the retained history and the live coordination
status home are separate inputs. A retained preview does not authorize moving
or merging either. The existing lifecycle owner must reconcile their exact
identities and provenance, verify count and value parity, and use the supported
migration/adoption workflow before advancing work packages.

Do not hand-edit `status_phase`, reconstruct approvals, or run an unscoped live
migration against a dirty root checkout to bypass this boundary. The historical
manual metadata workaround is withdrawn: setting a flag does not prove that
the selected reader consumed the preserved history. Issue
[#60](https://github.com/crucible-energy/spec-kitty/issues/60) tracks the remaining
coordinated recovery/adoption path; this read-only preview does not close it.

## Related

- [Coord-branch bookkeeping root-cause](https://github.com/spec-kitty/spec-kitty/blob/main/docs/archive/plans/engineering-notes/coord-splitbrain-rootcause.md)
- [Recovery & Troubleshooting (agent-facing)](../guides/how-to/recovery/index.md) — implementation-crash and merge recovery
