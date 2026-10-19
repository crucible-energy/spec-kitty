# Pre-review aggregate budget repair — October 19, 2026

Earlier observations below are historical. The current disposition is recorded
in the October 19 owner self-review closeout at the end.

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


## October 19 owner self-review closeout

Sam confirmed that Blacksmith and CodeRabbit are retired and directed owner
self-review. Do not restore either service, introduce a replacement runner,
wait for their queued jobs, or represent those jobs as passing. Routine PR
review uses exact-diff self-review and retained local checks. This direction
does not change production qualification or the charter's operator merge rule.

The current Elastic Fog native aggregate has completed: its retained output
reports all 91 build steps succeeded, with 7,113 tests passed and 93 declared
skips. This supersedes the earlier pending-run observations without erasing
either 300-second timeout. Exact elapsed time was not captured by this observer.

Self-review found stale pending-run/workspace statements and a missing test
separator. This dated closeout supplies the current state; the separator is
fixed with unchanged test AST and assertions. No functional defect was found
in the narrow runtime change. All head-side review entrypoints, including
pytest review runs, now share the finite 1,800-second default; explicit caller
budgets still take precedence. Baseline capture remains separately bounded at
300 seconds and can still be uncomputable for long suites; its existing verdict
semantics are unchanged. A longer aggregate allowance is not a performance gain.

The prior affected review/transition validation passed 463 tests with two
declared skips, with 100% changed-code coverage and 96% module coverage. Strict
mypy, lint, normal wheel build and isolated installed-command checks passed.
Executable source is unchanged by this closeout; new validation receipts stay
external. Pre-existing whole-file formatter drift remains disclosed.

The first temporary checkout was removed after validated publication. A brief
restoration of the same published lane is owned solely for these review fixes,
with expiry at validated handoff or October 19, 2026 at 23:59:59 UTC, whichever
comes first. Preserve the unmerged branch and remove only its eligible owned
checkout. The review restoration inventory is retained externally at
`/private/tmp/spec-kitty109-self-review-workspace-exception.json`.

The normal candidate wheel is independently installed under
`/private/tmp/spec-kitty-budget-repair-installed-20261019`; the shared operator
installation remains unchanged. Source publication, protected-main merge and
canonical installed-tool delivery remain distinct. Remote queued jobs are
historical status, not a required provider-recovery action under Sam's direction.
