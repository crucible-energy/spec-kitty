# Canonical unchanged-artifact commit admission

## User experience findings

An unchanged `agent mission setup-plan` operation returned `commit_created=false`
but still ran the repository's full pre-commit hook. The independently observed
Cmail operation took 460.900 seconds without advancing HEAD. A native regression
fixture reproduced one real hook invocation for an unchanged plan while verifying
that repository state was preserved.

## Engineering decisions

Keep the decision in ordinary `safe_commit`, after existing protection, placement,
path admission, requested-index snapshot and staging. Compare the requested staged
tree to HEAD using the existing authoritative scoped comparison. If unchanged,
restore the exact requested index snapshot and raise the existing typed
`SafeCommitStagedTreeUnchanged` result before invoking Git commit or its hooks.
The existing router continues to translate that result to an unchanged operation.

This preserves foreign staged content and requested partial staging. Genuine
changes still run mandatory hooks. A rejecting hook's text cannot turn a failed
real commit into a successful no-op. Native tests exercise the public planning
commit bridge against real disposable Git repositories and executable hooks;
Python only supplies the existing API bridge, not a second decision policy.

## Known limitations

The expected-parent and index-deletion commit paths retain their existing
semantics. This bounded correction does not bypass their checks or qualify them
for a new optimization. Local native validation and installed operation evidence
are separate from independent approval, protected default-branch delivery and
organization-wide ordinary-workflow adoption. External receipts record actual
validation outcomes without changing the validated candidate.
