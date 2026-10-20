# Owned operation custody

## Objective and lane

Correct standalone operation routing on `codex/owned-op-worktree-routing-20261020`,
stacked on the preserved native-validation source. Keep canonical repository
discovery unchanged. Changes reach the owning dependency branch through a PR;
neither local nor remote main is a consolidation target for this repair.

## Acceptance

- Open in an explicitly owned linked checkout and close using the generated
  instruction from a different working directory.
- Both events and the completed-record commit belong to the selected checkout;
  the primary checkout's files and HEAD remain unchanged.
- Refuse foreign, nested, detached and protected checkout claims before effects.
  Protection also applies before an uninitialized primary creates `.kittify`.
- Preserve read-only routing and the existing unowned response shape.

## Validation and scope

The new public-command regression first failed because `--owned-checkout` did
not exist. Run the owning invocation subsystem, its payload consumers, relevant
Git architecture checks and the repository's `make test-fast` baseline. Retain
final counts and candidate identity externally and in the PR so recording a
pass does not change the validated candidate.

This repair does not implement organization-wide workspace discovery or
retirement. That separate lifecycle extension must include externally created
workspaces, explicit owner/runtime release, retained reasons and replay/resume.
No live service deployment, workspace sweep or source installation is included.
