# Local Validation Interface

Status: Proposed interface; commands are not installed yet.

The native entry supports commit, full, platform, release, package, and docs modes. Selection inspection uses the same specification and returns selected check IDs, reasons, and missing prerequisites without executing publication. The thin pre-commit launcher calls commit mode and propagates its actual result.

Success means selected checks passed against matching staged and tooling inputs, all required evidence is retained, and owned children are joined. All refusals are nonzero with a stable reason and private receipt/log path. Distinguish invalid candidate, specification, tool, platform, failed check, input drift, timeout/quota, cancellation, ownership loss, and incomplete cleanup. Never present a refusal as a successful empty selection.

Read paths as bytes through NUL-delimited Git interfaces. Pass commands as argv arrays, never interpolate changed paths into a shell. Keep staged, unstaged, untracked, hook-customization, and linked-worktree state unchanged except explicitly installed owned hook integration. Installation composes with existing guards, detects conflicts, and offers an actionable refusal rather than overwriting user state.

Explicit publication modes require matching release qualification and configured credentials without exposing credentials. Missing prerequisites refuse that action. Commit mode cannot publish. Missing required Linux or Windows results do not become passing Darwin qualification.

Raw logs retain produced diagnostics up to the check's execution quota. Display excerpts have a separate limit. Crossing either execution quota or time/process/memory budget refuses, joins owned children, and retains produced evidence. Evidence without a matching final binding or cleanup disposition is unusable for acceptance.
