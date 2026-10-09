---
title: 'Explicit owned single-branch recovery: decisions'
type: explanation
audience: software-engineer
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
