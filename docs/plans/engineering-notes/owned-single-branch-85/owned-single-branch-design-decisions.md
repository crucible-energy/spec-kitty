---
title: 'Explicit owned single-branch recovery: decisions'
description: 'Explains ownership, history, archive and transaction boundaries for explicit conversion of an archived legacy lane into an owned single branch.'
type: explanation
audience: software-engineer
doc_status: point_in_time
updated: '2026-10-09'
---

1. Explicit conversion has its own closed proof input. Ordinary legacy re-stamp,
   topology admission, finalization refusal and whole-branch absorption stay intact.
2. Ownership is minted once through the existing authority. The historical
   execution base, current planning pin and current WP claim refs are separate pins.
3. The admissible historical case has both zero post-base source diff and zero
   source-touching commits, plus a byte-verified archive of the raw event stream.
   Inherited source differences do not imply post-base work. Historical refs remain
   intact; no whole-branch absorption or historical approval is claimed.
4. Canonical single-branch lane computation preserves CODE classification and all
   WP membership. The explicit receipt records `lane-a` to `lane-planning` conversion.
5. The checkout claim lock precedes the existing Mission transaction; apply rechecks
   frozen inputs under those locks, writes through the transaction and rolls back
   failure. Repeating a committed conversion requires its qualifying receipt.
6. Previously uncommitted historical files remain unknown. Conversion does not
   claim their recovery, nor any implementation approval.
7. Canonical status and path decoding use `kernel.git`. Its bounded NUL-safe
   workspace parser retains detached HEADs and literal byte wire labels. The
   explicit read-only `worktree list` query remains in the guarded recovery caller,
   as the existing negative control permits. Both parsing ownership and C-007's
   destructive-argv guard remain unchanged. Immutable blob bounds are optional;
   ordinary blob callers and migration/topology behavior keep their contracts.
8. Independent review reproductions tightened full-history source probes,
   duplicate-key/privacy handling, detached-workspace refusal, ordered archive
   containment and pre-read byte bounds. The selected raw archive is byte-identical;
   other historical streams' raw lines must be included in order with multiplicity.
9. Transaction identity uses the failover-aware `resolve_mid8` authority. Retained
   historical ref recognition compares canonical parsed mission identities rather
   than composing a lane prefix. The workspace parser's record type is private;
   its public parser remains the production entry point.
10. The separately scoped successor adds explicit schema-2 `preserved_unapplied`
    custody. Schema 1 keeps its zero-work contract. Typed checkout authority still
    governs conversion; canonical WP review remains implementation approval.
11. Closed custody binds the entire reconstructed scope, retained refs, all
    post-base commits and every parent edge, including empty edges, merges and
    intermediate reverts. It preserves before/after/tip/current raw blob versions.
    Unknown paths, commits, blobs or caller approval/generation flags refuse.
12. Initial custody supports only regular modifications with unchanged `100644`
    or `100755` modes. Presence changes, mode transitions, renames, copies and
    nonregular entries refuse. External evidence is bounded and read without
    following symlinks; apply and idempotency must requalify that evidence.
