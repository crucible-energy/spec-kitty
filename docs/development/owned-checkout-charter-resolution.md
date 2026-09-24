# Owned-checkout charter resolution repair

An explicitly validated `--owned-checkout` selects the mission write surface.
Mission activation, mission-type context and specification template resolution
must read that same checkout. Previously those three reads used the primary
checkout, rejecting an activated feature checkout when primary was inactive,
or accepting primary activation when the owned checkout was inactive.

The repair keeps ownership validation and the inactive-charter refusal intact.
The existing `effective_root` is the single configuration root after validation;
without an owned checkout it remains the primary root.

## Evidence and implementation log

- Regression reproduced both incorrect outcomes before the implementation:
  two failing cases in `tests/core/test_mission_creation_owned_charter.py`.
- After repair, owned-charter, unborn-HEAD and topology tests: 15 passed.
- User experience finding: the old error recommended activating a charter that
  was already active in the caller's explicitly selected checkout.
- Decision: resolve all three configuration/template reads consistently; do not
  weaken the guard, mirror configuration into primary or patch installed tools.
- Limitation: this is source qualification, not a released CLI installation.

Workspace: reused the clean review-thread-closure checkout, preserving its two
unmerged commits on its prior branch. Primary has unrelated dirty changes and
the redact-operation-request checkout retains unmerged work. No checkout was
added. This repair owns the temporary fourth active branch exception until
2026-10-01; after operator merge, audit and retire its branch and release the
reused workspace when dependencies permit. No storage-recovery claim is made.
