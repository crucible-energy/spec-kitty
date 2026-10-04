---
title: Establish and query owned coordinated authority
description: Recover the declared coordination ref in an existing registered checkout, inspect its genuine status partition, and record a later real peer-review disposition.
doc_status: active
updated: '2026-10-04'
---

# Establish and query owned coordinated authority

## Current supported boundary

The history-restoration command restores source truth into the target checkout.
This companion operation establishes **declared coordination authority** in that
same registered linked checkout. It creates no worktree, independent clone,
planning copy, lane base, approval, or runtime-success record.

The primary checkout remains the repository identity anchor. The explicitly owned
checkout carries the physical planning, status/review and retained run roots;
their logical refs remain distinct: planning on `target_branch`, status on the
declared `coordination_branch`. Existing default discovery/routing is unchanged.
The single-branch owned lifecycle contract is not broadened to coordinated missions.

An unregistered `.worktrees/<mission>-coord` directory is a **husk**, even if it
contains mission events or a snapshot. Owned query refuses it with
`COORD_AUTHORITY_HUSK_UNREGISTERED`. Recovery does not remove or overwrite it.
After explicit placement, the genuine registered checkout on the declared branch
is selected directly; the husk is never a fallback.

## Plan authority placement

From a checkout of the mission-owning repository:

```bash
spec-kitty migrate restore-owned-coordination \
  --mission "$MISSION" --owned-checkout "$OWNED_CHECKOUT" \
  --target-commit "$PUBLISHED_RESTORED_TARGET" \
  --coord-commit "$ORIGINAL_COORDINATION_PIN" \
  --dry-run --json
```

Both pins must be full immutable commit SHAs in the same repository. The declared
coordination head must be absent and not occupied by another checkout. Existing
refs are never overwritten. The owned checkout must be exact, Git-registered,
clean, on the pinned target branch, and inactive: live recorded process leases
and outstanding issued runtime steps refuse.

The operation verifies metadata identity/topology/branches, historical status
count/value parity, preserved coordination-log records, matching core planning
blobs, WP prompt/roster/dependency agreement, and the original planning ancestor.
Unrelated pins, unsafe paths, symlink artifacts, hidden divergent status bytes,
foreign Git backlinks and contradictory histories refuse before placement.

The preview reports counts, both parent pins, planning/common ancestry and the
declared destination. It creates no commit objects, refs, snapshots or run state.

## Apply after independent qualification

Replace `--dry-run` with `--apply` using the same inputs. Apply requires Git 2.48+
for native atomic symbolic-ref transactions and configured Git author identity.
It constructs a provenance recovery commit with:

- **exactly the target tree**, so tracked and ignored working files remain intact;
- first parent: the published restored target;
- second parent: the original coordination pin;
- an immutable coordination-binding message, not a source/WP approval event.

The existing per-mission lock serializes supported owners. The command revalidates
directory/data/ref state, then atomically creates the missing coordination ref and
changes only the selected linked checkout's symbolic HEAD with an expected-oid
check. The target and all other branch values stay unchanged. A native transaction
failure leaves no partially created ref or activated worktree. Unreachable commit
objects from a failed attempt are not delivery or authority.

Do not run arbitrary `git switch`, ref updates or raw filesystem changes concurrently
with an admitted placement operation. The native expected-oid transaction protects
revision consistency; literal branch and registration identity are validated under
the supported ownership lock immediately before it.

Inspect the result and publish the recovered coordination branch through the
repository's normal workflow. The second-parent relationship preserves the old
coordination lineage, including immutable historical artifacts not selected by
the target-tree projection. This is not code-lane consolidation or dependent-base
selection. `planning_commit_sha` is not invented or updated.

## Read-only owned query

```bash
spec-kitty next --mission "$MISSION" \
  --owned-checkout "$OWNED_CHECKOUT" --json
```

This form is **query only**. `--result`, `--answer` and `--decision-id` refuse.
It validates registered checkout/declared branch, a unique recovery anchor and
both parents, unchanged target binding, current canonical log and planning/WP
identity. It uses the public pure `materialize_snapshot` projection and returns:

- canonical lanes, counts and recorded `review_result` values;
- dependency readiness from the canonical dependency gate;
- explicit repository/planning/status/run roots and logical refs;
- retained blocked-run evidence without rekeying, bootstrapping or advancing it.

For the retained Subsequent packet, WP03 remains
`dependencies_not_satisfied` while WP02 is `in_review`; WP01's historical approval
does not manufacture a WP02 approval. Query allocates nothing and never emits
accept/merge or success for the blocked discovery DAG.

## Explicit projection migration

An older derived snapshot may lack the added verdict projection. Refresh it
explicitly on the validated status authority:

```bash
spec-kitty migrate refresh-owned-review-projection \
  --mission "$MISSION" --owned-checkout "$OWNED_CHECKOUT" --json
# Add --apply after inspecting the preview.
```

`agent status materialize --owned-checkout ...` uses the same migration helper and
also defaults to preview. Only `status.json` changes; event IDs/bytes, actors, null
bindings, planning and unrelated snapshot values remain intact. Commit the owned
projection before another clean-authority query. Default materialization retains
its existing semantics. No automatic dirty-primary/frozen-dossier rewrite occurs.

For other existing missions, the established explicit rematerialization path is
`spec-kitty agent status materialize --mission "$MISSION" --json`, from the
repository root checkout. It uses the normal topology-aware status resolver and
canonical lock; inspect and commit that authority's generated snapshot through
the existing workflow. Use the owned migration above for the retained coordinated
checkout. Audit remains read-only and still reports genuine snapshot drift.

## Later real independent review

After performing the actual review, the independent reviewer/operator may use:

```bash
spec-kitty agent status review-owned \
  --mission "$MISSION" --owned-checkout "$OWNED_CHECKOUT" --wp-id WP02 \
  --reviewer "$ACTUAL_REVIEWER" --verdict "$ACTUAL_VERDICT" \
  --reference "$ACTUAL_REVIEW_REFERENCE" --reviewed-commit "$IMMUTABLE_CODE_PIN" \
  --json
# Add --apply only for the actual disposition, then commit/push the two outputs.
```

This records supplied facts; it does not perform or invent a review. The existing
WP must be `in_review`, the code pin must carry the matching dossier and authored
owned-code paths, and the reviewer must differ from recorded implementation
actors. Canonical FSM/evidence consistency guards decide the transition: approved
or changes_requested back to in_progress. There is no force, claim, done, lease
reassignment, runtime issuance or dependent-lane allocation. Missing actual model
or profile bindings are never filled from authored recommendations. An exact
committed request retry is idempotent.

## Remaining scope

Advancing owned next, reviewer claim/issuance handoff, recovery of the blocked
runtime DAG, changing a target binding after target advancement, lane-base
qualification and WP03 allocation/integration remain separate supported work.
Historical restoration/authority are not canonical registration/export, protected
consumer acceptance or production qualification.
