# Pre-review aggregate budget repair — October 19, 2026

## Objective and owner

Codex owns a bounded repair of the retained pre-review runner. Elastic Fog's
native aggregate exceeded the installed 300-second wrapper twice without a
completed test verdict. Keep the exact configured command, assertions, per-test
deadlines, cancellation, process-group cleanup and terminal timeout behavior.
No installed-package patch, bypass, new configuration interface or automation
is authorized by this repair. Publish only to the Crucible fork through review.

## User Experience Findings

- The normal owned-checkout review transition offers no aggregate-budget
  override. A CPU-active complete native suite can outlive its inherited
  baseline-capture timeout, leaving work correctly unpromoted but unreviewable.
- The default is captured by several Python function signatures. Updating only
  a caller or installed package would create inconsistent behavior or lose the
  repair on reinstall.

## Engineering Decisions

- Repair the canonical retained runner, with virtual-clock red-first regression
  coverage through its existing public evaluator. Keep the baseline-capture
  budget independent. Add no Python product interface under the Zig migration.
- A provisional finite 30-minute review budget covers the observed run beyond
  ten minutes and historical documented aggregates beyond twenty minutes. The
  first uncapped current aggregate remains running; no passing or timing-bound
  claim is made from these observations. Retain explicit shorter caller budgets.
- Scope ownership: `src/specify_cli/review/pre_review_gate.py`, its existing
  affected review tests, and this log. Existing owner work stays untouched.
- Temporary workspace exception: Codex chat
  `01a152a2-b7b8-7693-a71b-88472b6d548b` owns a fifth registered checkout at
  `/Users/sam/git/crucible/_worktrees/spec-kitty-pre-review-budget-repair`.
  The four prior checkouts hold dirty, open-review or valuable unmerged work;
  none was proven eligible to overwrite or retire. The extra lane isolates
  this independent repair. Expiry is October 20, 2026 at 23:59:59 UTC or
  validated publication, whichever comes first. Next action is focused repair,
  validation and fork publication, then eligible closeout or a recorded renewal.
  Exact existing registry and parent inventories are retained externally at
  `/private/tmp/spec-kitty-pre-review-budget-workspace-exception-20261019.json`.

## Known Limitations

- The current full native aggregate has no final verdict yet. Neither prior
  timeout is a test pass; changing a wrapper budget cannot establish correctness.
- Source publication does not update the installed tool. Normal artifact
  delivery and the actual owned-checkout transition remain separate gates.
- The operator merges to protected main under the owning charter; no mainline
  merge or production admission is claimed here.
- No dependency changes, efficiency gains, model-quality gains or cost savings
  are claimed. Retain final validation receipts outside the frozen candidate.

## Red-first observation

The virtual-clock regression failed in both expected default-budget cases:
completion at 360 seconds was terminated at 300, and the still-running aggregate
was terminated at 300 instead of the proposed finite 1800 bound. The explicit
120-second caller-budget case passed. Raw output is retained externally at
`/private/tmp/spec-kitty-budget-repair-red-20261019.log`. The existing session
fixture created an isolated editable test environment and resolved dependencies;
that environment is test-only, not an installed operator-tool upgrade or a
lockfile change. Preserve its versions with the final validation receipt.

## Source self-review

The implementation changes the existing private default shared by head-side
review entrypoints and removes its baseline-capture import. The registry still
delegates to the same evaluator. Existing observer, lock, process-group,
cancellation, parser, baseline comparison and transition code are untouched.
The regression drives the actual observer with a virtual monotonic clock;
it checks completion, finite termination, exact command preservation, shorter
explicit deadlines and unchanged baseline-capture policy. Self-review found
no new execution path or configuration surface.

The repository's pre-existing whole-file formatter drift remains outside this
repair; changed test code is formatted and the affected files pass lint. Do not
claim a whole-file formatter pass. The initial strict check used an environment
missing `platformdirs`; rerunning with the existing runtime environment avoids
suppressing the missing import. Final validation receipts stay outside source.
