# Explicit operation closeout commit policy

Owner: WP15, organization-workspace-lifecycle-01M5DRAR. The real implementation
claim is commit `4c1c38e9aae2c9f657f9bdb416031795f3ae49db`, event
`01M5ZX368CDKWHJE56NP8ASPTS`, with the existing Source checkout and declared
mission integration target. Prior WP07/WP14 approvals remain unchanged.

Status: implemented candidate; ten focused controls pass. Full qualification, independent review and
isolated installed-artifact acceptance remain pending.

## User experience and decision

An operator must be able to close their own operation in a repository holding
other people's unfinished work without creating a Git commit. Add the explicit
`profile-invocation complete --no-commit` option. The default still commits the
operation record through the existing protection boundary.

The executor's keyword-only `auto_commit=False` skips only the final commit
helper. Checkout custody, branch drift, outcome/evidence validation, canonical
completion writing, correlation links and propagation retain their behavior.
The executor clears its previous commit outcome at the successful completion
boundary so a later opt-out cannot report an earlier commit or refusal.

Human output explicitly says that the journal is uncommitted. JSON keeps its
existing response shape. The existing `--commit` argument remains a correlation
reference; it does not select the commit policy. An uncommitted completion is
local recoverable state, not a claim of Git publication or cleanup authority.

## Reproduction and validation

The actual standard pre-repair run reported seven failures and three passes
across ten selected cases. Failures identify the missing CLI option and executor
keyword; existing default-policy controls passed. The tests preserve exact
HEAD, index bytes, refs and unrelated staged/unstaged/untracked files while
checking single closure, correlations, unchanged JSON, human output, validation
refusals, accepted evidence and sequential executor reuse after a real default
commit. Propagation is checked independently of the commit choice.

Receipts remain outside the source candidate under the owning Connector
`spec-kitty-no-commit-2026-10-27` receipt root. Preserve these distinct outcomes:

- `red-r1`: startup exceeded its explicit 1 GiB sampled RSS allowance; no test
  result was obtained. It is an infrastructure refusal.
- `diagnostic-red-r2`: the optional timed traceback crashed in the owned
  `faulthandler_thread`/`dump_frame` path. The macOS report does not establish a
  collection-guard defect. The diagnostic was withdrawn; no shared interpreter
  or guard was changed.
- `standard-red-r3`: standard pytest retained every mandatory collection and
  authenticated-cache check, completed without that crash, and produced the
  actual seven-failure/three-pass behavioral RED and JUnit evidence.
- `green-r1`: eight controls passed; two correctly refused the synthetic
  repository's protected initial branch. The fixture now initializes `main`
  before creating `fixture/ops-work`; product protection remains unchanged.
- `green-r2`: all ten focused controls passed with no errors or skips. Original
  session `19272` exited successfully; source pins were unchanged, resources
  joined and final resource bounds passed.

The existing mandatory clock scan examines the entire test tree. Its
authenticated Source cache must remain intact; the pytest metadata cache
option does not relocate that separate guard cache. Private runtime/tool
identity, exact Source imports and read-only locked development dependencies
are separately pinned. Older editable distribution metadata is not presented
as the qualified governance CLI or as a repaired installed artifact.

## Remaining gates and limitations

Run the complete affected invocation subsystem and
required ownership regressions, named architecture/lint/type/format checks and
the unchanged changed-statement coverage gate. Freeze the candidate before
final gates and use normal publication hooks. The excluded legacy executor
test file retains its prior formatting debt; per-file formatter commands use
the repository's required force-exclude policy.

Only a separately qualified isolated repaired artifact may close the preserved
operation in the foreign dirty PDB primary. Its genuine ownership and branch
checks remain mandatory. No live foreign-primary operation was closed by this
candidate or by its synthetic tests. Source owns landing coordination and the
independent reviewer owns the review disposition.

This is a bounded correctness repair to the existing Python governance API.
Any future Zig port must preserve these default/opt-out, custody and audit
contracts; this change introduces no parallel lifecycle engine.
