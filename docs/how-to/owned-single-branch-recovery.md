---
title: 'Recover an archived legacy lane into an owned single-branch checkout'
description: 'Qualify pinned historical source and archived state before explicit lane conversion.'
type: how-to
audience: software-engineer
updated: '2026-10-09'
---

Use this operation when a linked owned checkout already carries a `single_branch`
mission with exactly one legacy code lane. It converts that lane explicitly to the
supported `lane-planning` execution shape while preserving code WP classifications,
membership, current source, events, historical refs, claim refs and the planning pin.
It does not recover unknown uncommitted historical files or establish WP approval.

1. Finish the historical workspace/process disposition and retain its Git refs.
   The command refuses a registered historical branch workspace, detached
   workspace at a historical tip or descendant, or a live/ambiguous
   historical PID. It also refuses unknown or changed historical refs.
2. Preserve the selected historical tip's raw `status.events.jsonl` under the
   owned mission. The selected stream must be byte-identical; every other
   historical stream's raw lines must occur in order, retaining multiplicity.
   The historical and current manifests must name the same mission and WPs.
3. Prepare an external JSON proof file so recording its own HEAD does not change
   the checkout being pinned. The closed schema requires every field below;
   additional fields, duplicate keys at any depth and malformed values refuse.

| Field | Required evidence |
|---|---|
| `schema_version` | Integer `1` |
| `owner_head` | Exact current owned HEAD, full 40-character lowercase Git SHA |
| `planning_commit_sha` | Original `lanes.json` planning pin, not implementation HEAD |
| `historical_base` | Verified historical execution base before committed source work |
| `historical_refs` | Complete list of objects with `ref` and full `sha`, including retained mission/lane and recorded lane-tip refs |
| `archived_status` | Object with selected historical `ref` and archive `path` relative to the owned mission |
| `claim_refs` | Exact mapping of current `refs/spec-kitty/wp-base/<mission>/<WP>` refs to their full SHAs |

The command verifies Git ancestry, zero production-scope tree difference and zero
source-touching commits across **full** post-base history. An "ours" merge cannot
hide committed source work. The union of historical and current declared scope is
checked. Inherited historical source may differ from the current reviewed source;
the proof establishes zero post-base source work, not whole-branch absorption.

4. From the owned checkout, run:

   ```sh
   spec-kitty migrate owned-single-branch --mission "$MISSION" \
     --owned-checkout "$CHECKOUT" --proof "$PROOF" --dry-run --json
   ```

   A successful preview returns `would_convert` without writing or committing.
   Inspect the explicit old/new lane mapping before applying.
5. Run the same command without `--dry-run`. It rechecks frozen inputs under the
   checkout claim, Mission and manifest locks, writes the manifest and receipt
   through the existing transaction, and commits them together. Failure rolls
   back the transaction. Git proof probes each have a 15-second timeout. Historical
   immutable manifests/status streams and qualifying receipts have an 8 MiB bound;
   the Git blob size is checked before reading its bytes. The external proof is
   limited to 64 KiB.
6. Inspect `recovery/owned-single-branch.json` inside the mission. The receipt
   preserves the original manifest, proof and input/state hashes, lane mapping,
   complete membership and the unknown status of historical uncommitted work.
   Repeating the operation requires the same proof and a HEAD-qualified receipt,
   and returns `already_converted` without another commit.
7. Continue ordinary owned finalization and runtime review without a planning-pin
   refresh. Verify that the original planning pin and current claim ref remain
   distinct and unchanged. Finalization's existing execution and planning guards
   continue to apply; conversion does not bypass them.

`OWNED_RECOVERY_REFUSED` reports a sanitized proof/recovery refusal. The shared
ownership resolver retains its existing authority refusal codes. Inspect the
pinned inputs and the documented predicates; raw malformed proof values are
never printed. Descriptor-safe regular-file reads are required; hosts lacking
that capability refuse rather than falling back to a weaker read.
