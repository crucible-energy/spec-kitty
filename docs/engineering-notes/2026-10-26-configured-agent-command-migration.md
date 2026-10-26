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
version. Canonical dispatch is currently blocked by the very legacy upgrade
failure under repair, and no successful Op or governance migration is fabricated.
No audio consumer, production admission or storage-recovery claim follows from
these framework tests.
