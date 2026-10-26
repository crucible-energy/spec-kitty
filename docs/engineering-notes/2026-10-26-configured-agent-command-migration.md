---
title: Configured agent command migration detection
description: Repair legacy command population eligibility without creating unused agent surfaces.
doc_status: active
updated: '2026-10-26'
---

# Configured agent command migration detection

Owner: Dream Walker dependency recovery, `codex/issue-127-agent-migration`.
Tracker: [issue 127](https://github.com/crucible-energy/spec-kitty/issues/127).
Follow-up: [issue 129](https://github.com/crucible-energy/spec-kitty/issues/129).

## User Experience Findings

A Codex-only consumer could not finish upgrading because the legacy command
population migration always detected missing Claude commands. Current mission
assets lack its retired command templates, so the upgrade stopped before later
migrations. Conversely, complete unselected Claude commands hid an incomplete
configured Gemini surface. Invalid agent configuration was never consulted.

## Engineering Decisions

Use the canonical configuration-aware directory resolver for both detection and
application, retaining the existing parent-presence boundary. Codex uses skills,
so it has no eligible legacy command directory. No unused Claude or Copilot
surface is created. Configured legacy command agents still require real templates
and preserve existing custom commands. Missing templates for an eligible surface
remain an error; invalid configuration remains an error.

Regression tests extend the existing migration robustness module. Three original
failures reproduce Codex-only upgrade rejection, missed configured-agent repair
and ignored invalid configuration. The actual migration runner records a truthful
not-applicable result; no metadata success is manufactured by the caller. Tests
also cover real template copying, dry-run preservation and existing legacy roots.
This is a bounded correctness repair to retained Python, not a second migration
implementation. The eventual Zig parity surface must preserve these contracts.

The actual isolated RC7-derived consumer upgrade passed that migration and then
exposed a second defect: the earlier canonical-context runner stripped an
existing assignment before the later runtime-state cutover could verify it.
The runner now calls the sole seed/verify/phase-flip helper for every mission
before stripping any frontmatter. A refusal restores its existing backup;
neither rebuilding lane transitions nor an existing seed substitutes for verified
runtime-state cutover. A real corrupt assignment seed exercises rollback with
the original mission files preserved. The existing migration commit helper also
retried rejected hooks with verification disabled; a real rejecting-hook
regression reproduces that bypass, and the helper now returns failure after the
normal attempt. These are bounded retained-Python safety repairs, with the same
ordering and hook boundaries required of the eventual Zig implementation.

## Known Limitations

The migration retains its existing eight-command completeness threshold and
parent-presence policy. Missing agent roots are left to the canonical setup and
repair surfaces. This change does not repair all historical migrations or prove
an entire consumer upgrade; actual isolated downstream upgrade and runtime
identity verification remain required. The frozen installed runtime is preserved;
any derived package must be built from pinned source with an honest distinct
version. Canonical dispatch was subsequently admitted in the same owned lane
after replacing its linked checkout with an independent root at the same path
and running the supported RC7 project migrations. The dirty shared primary
remained unchanged. The complete upgrade still reports failure for preserved
edited global assets and a profile-root repair that needs a fresh plan; project
admission does not assert complete global upgrade or default-branch adoption.
No audio consumer, production admission or storage-recovery claim follows from
these framework tests.

## Hosted check admission

PR128's existing jobs remained unassigned on vendor-specific Ubuntu and Windows
labels. This lane replaces those labels in the six workflows triggered by the
repair with standard hosted Ubuntu 24.04 and Windows 2025 labels. No job, check
name, command, condition, permission, timeout or dependency version is removed
or weakened. Parsed before/after workflow comparison verifies that only runner
selection and its matching operating-system matrix entry change. Hosted jobs
must still execute and pass before delivery; a queued or locally green result
does not substitute for them.

The canonical invocation executor already emits `op(profile): action [id]`
commits, covered by its producer contract tests. The existing type registry
omitted `op` and rejected the real governed record created during this repair.
The registry now recognizes that domain type. Unknown types, empty types and
empty subjects remain rejected; no commit-lint rule or job is disabled. The
actual configured registry contract reproduced the rejection before the change;
the hosted commitlint invocation remains the final consumer check.

The declared strict bootstrap typecheck also exposed `Any` propagation from
imports skipped by the configured type analysis. Explicit local `str` and
`Path` annotations preserve the existing canonical constant and asset-resolver
contracts across all three return branches. This is a bounded typing repair to
retained Python: no path coercion, exception suppression or analyzer override
is introduced. Existing resolver and doctor tests exercise the runtime behavior;
the unchanged strict typecheck must pass.

The project upgrade's generated governance effects are preserved separately
from this bounded CI change. They are not a shortcut to importing another
owner's unpublished platform or CI architecture. The isolated validation
environment uses the committed frozen dependency lock with third-party builds
disabled. Python tests import this checkout's source; the governed CLI remains
the separately identified RC7-derived runtime. No installed wheel is patched.

The upgrade command's `--project --json` combination reports its compatibility
plan and does not apply it, even with `--yes`; the applying form was run
separately and its actual output retained. Migration history, preserved shared
edits and incomplete repair state remain explicit recovery obligations.

Hosted execution then exposed four existing docs without required descriptions
and two raw historical fixtures flagged by canonical-producer lint. The docs
receive only the required descriptive frontmatter. The fixtures retain exactly
the same event bytes and assertions: the decision input exercises an install
fence and its normal reentrancy control; the historical intake exercises
defensive recovery of incomplete legacy data. The linter's existing, validated
`exception-flow` test category documents those inputs. No baseline entry,
production exemption, producer model or gate rule is added or changed.

The hosted lock-freshness check reproduced a stale editable self-entry:
`pyproject.toml` already declared 3.2.8, while `uv.lock` retained 3.2.7. The
canonical offline resolver updates only that self-version; parsed comparison
verifies every third-party package, artifact hash and other lock field remains
identical. This does not add or upgrade a third-party dependency.

A superseded PR128 run also retained queued `always()` jobs and held the
workflow concurrency slot. After capturing its old source identity and proving
that none of its 54 jobs had an assigned runner or was running, normal cancel
was attempted. Its queue remained; the supported force-cancel endpoint then
retired only that obsolete run. Current-source checks subsequently executed.
No other owner's workflow was cancelled and no required result was replaced
with a manual success status.

The now-running full pipeline also reports older merge/read-surface regressions
and vulnerable dependencies. Those remain failed gates, with retained hosted
logs and a follow-up repair obligation; this metadata/fixture increment does
not claim to resolve them. Four changelog emphasis delimiters and two excess
blank lines are corrected to the existing Markdown policy without changing
their content.
