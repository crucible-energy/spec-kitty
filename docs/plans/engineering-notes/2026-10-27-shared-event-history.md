---
title: Shared event-history merge repair
description: Record the guarded event-log merge defect, source repair, validation findings and remaining qualification obligations.
type: explanation
doc_status: point_in_time
updated: '2026-10-27'
---

# Shared event-history merge repair

## Current state

Owner: Subsequent mission owner, under Root's bounded Source checkout lease.
Branch: `codex/owned-lanes-analysis`; declared integration target:
`codex/organization-workspace-lifecycle-20261020`.
Tracked defect: [Spec Kitty #134](https://github.com/crucible-energy/spec-kitty/issues/134).
Scope: status event-log detector, its canonical consolidation driver, focused
regressions and this log. Active lifecycle/native/allocator work and installed
runtimes remain protected. This is a correctness repair to existing Python code
in the owning Spec Kitty project; new Subsequent tooling remains Zig.

## User Experience Findings

- **2026-10-27, final receiving review:** A real maintained-driver reproduction
  showed same-ID nested JSON `true` and `1` silently merging at `33a4a6c65a`.
  Python equality conflates their types in both the pre-existing union and the
  new shared-history classifier. The public P1 finding supersedes earlier
  bounded zero-finding reviews and blocks merge until corrected and validated.

- **2026-10-27, documentation structure:** Hosted structural checks rejected
  this new log because its original directory was not sanctioned and required
  frontmatter was absent. The earlier spelling/changelog check did not cover
  those rules. Preserve the full log in the existing engineering-notes section
  and validate the existing structural gate without exemptions.

- **2026-10-27, owning-subsystem validation:** A fixture's recursive event-log
  search enters `.git` before applying its existing exclusion. Concurrent Git
  object collection removed an object directory during that search, causing a
  real `FileNotFoundError` before any cancellation-attribution assertion. The
  run retained 3,725 passing tests and this failure; it is not a full pass.
- **2026-10-27, hosted review:** The existing architecture gate correctly
  rejected the new driver's direct status-submodule import. The local source
  review missed that facade boundary. The exact existing test also fails
  locally; preserve the failure and repair the public import/export without
  adding an exemption or weakening the gate.
- **2026-10-27:** Aletheia's owner separately recovered the normal WP03 claim
  through its supported workflow. That recovery is not attributed to this
  unadopted repair; actual response proof and Subsequent acceptance remain open.
- Observed: released 4.0.0rc7 rejects a merge when all 43 records on one side
  already occur with identical payloads among the other side's 57 records.
  Shared post-base rejection/approval cycles are mistaken for independent work.
- Observed: the declared `.githooks` directory is absent in this checkout and
  the primary Source checkout. Delivery must reconcile this with the owner;
  absence is not evidence that required hooks ran.

## Engineering Decisions

- **2026-10-27, typed payload identity:** Extract the existing deterministic
  JSON renderer inside the same event-log module and use it for both payload
  identity comparisons and output. Preserve JSON type distinctions recursively
  while retaining key-order-independent deduplication. The actual-driver
  no-write regression, union scalar/array controls and direct fork-classifier
  case fail before this repair; equivalent key orders still deduplicate. This
  is a bounded correctness repair, not a new schema or serializer authority.

- **2026-10-27, log placement correction:** The repository structural contract
  takes precedence over the initially selected implementation-log directory.
  Under Root's exact relocation lease, move only this owned log into the
  sanctioned point-in-time engineering-notes section with required metadata.
  Source, dependencies, toolchain and runtime inputs remain unchanged; retain
  completed source-gate evidence and rerun affected documentation gates after
  this documentation-only correction.

- **2026-10-27, bounded fixture repair:** Under Root's exact helper/test lease
  extension, prune Git metadata before walking and retain every genuine nested
  status log. Propagate other traversal and real status-read errors. The
  deterministic regression drives the existing helper and reproduces the
  disappearing-Git-directory error before the fix; the real-status permission
  error control already passed. No product guard or assertion is weakened.
  Baseline reuse is limited to unchanged inputs: this helper and its callers
  belong to consolidation/Terminus, outside the baseline's selected directories;
  runtime source, dependencies, toolchain and test environment are unchanged.
  The affected subsystem and caller checks must run again on the new fixture.
- **2026-10-27, facade repair:** Route the unchanged detector through the
  maintained status facade. Root explicitly extended the lease for that export
  and the binding root-project version bump in `pyproject.toml` and `uv.lock`.
  Only the project version changes from RC6 to RC7; dependency records and
  constraints remain unchanged. This fork metadata is not official RC7 source
  convergence, a published artifact, organization adoption or a live upgrade.
  The existing architecture test is the red-first regression; no new allowlist.
- **2026-10-27:** Adopt the independently owned log procedure from
  [Kaizen's pinned procedure](https://github.com/crucible-energy/kaizen/blob/4ca2672d97ffe34d9a7d9a4df3d6f8b6c93c8b51/docs/mission-log-procedure.md),
  preserving independent ownership and history. The original
  `docs/implementation-logs/` placement was an incorrect local assumption; the
  structural-gate correction above records its canonical home.
- **2026-10-27:** After the frozen source checks joined, add the required
  changelog entry under Root's explicit documentation-only lease extension.
  Revalidate affected documentation, formatting and terminology; retain source
  evidence only for identical code, dependencies, toolchain and environment.
- Preserve the released concurrent cancellation/rejection guard before repairing
  it. The fork's starting revision lacks this guard; an unguarded merge passing
  is not a fix. Port provenance: official `spec-kitty-cli` 4.0.0rc7 wheel SHA-256
  `174361d4a2c75f1f9fb20ca17f6f9eca60b0017052425680630628feab362124`;
  upstream commits `500419708d2dd8bc2a9e789689bf6199699b6e7c`,
  `3c6a384bb942a53f9317e51abfe5155020886b7e`, and
  `3498b426d9e66e27f995de528f117a050ad2e4eb`.
- Port the released detector module and the exact `_read_jsonl` and
  `run_event_log_driver` functions into their existing canonical boundaries.
  Do not replace unrelated consolidation behavior or a live installation.
- The regression exercises the existing `run_event_log_driver` seam. On the
  exact ported guard, both directions of a shared review-cycle extension fail
  with the observed concurrent-transition error; five refusal/retention controls
  pass (2 failed, 5 passed). The original immutable 7/57/43-row reproduction
  also fails on the official installed runtime without changing its output.
- Keep detailed immutable inputs, admission hashes and raw test diagnostics in
  external owner receipts, avoiding unnecessary publication of mission payloads.
- The fix excludes post-base event IDs only when both sides carry identical
  payloads. The canonical union still validates every row and refuses collisions.
  The immutable 7/57/43-row reproduction now merges to 57 unchanged payloads;
  output serialization is normalized, so input byte identity is not claimed.
- The first focused green run passed all 17 tests, including existing event-log
  tests. Narrow strict type checking passed both touched source modules.
  Final frozen checks, publication and installed qualification are recorded in
  external receipts so recording results cannot change the validated candidate.
- Root confirmed the existing declared integration target and that the absent
  configured hook is not an installed gate. Normal Git operations retain the
  configuration; repository manual checks remain mandatory. No hook bypass or
  hook-installation claim is made.
- Keep the change local: the detector and wrapper are small enough to review
  directly and lint/type checks identify no prerequisite structural cleanup.
  Unrelated consolidation and lifetime refactoring would increase repair risk.

## Known Limitations

- **2026-10-27, P1 review supersedes earlier local readiness:**
  [typed-identity thread](https://github.com/crucible-energy/spec-kitty/pull/135#discussion_r4386211366)
  remains open pending repair validation, publication and explicit reply. The
  earlier frozen code-gate results do not qualify the changed identity logic.

- **2026-10-27, superseding local readiness:**
  [PR #135](https://github.com/crucible-energy/spec-kitty/pull/135) is published
  at `5b31b04a9069cbc9da33a2b870d35ed0a462549e`, but its hosted architecture
  finding blocks merge. The owning lease permits the public facade repair;
  the local public-facade repair and required RC7 root metadata bump pass
  focused checks. The fixture traversal repair passes its full 18-test owning
  module and strict type checking. Complete frozen final gates, publish the
  corrective increment, then close the finding publicly. Earlier passing local checks do
  not prove the architecture gate passed.
- Final validation, independent review, publication and installed-runtime
  qualification are pending. T010 now has separate real-producer proof against
  published equivalent implementation; WP02 full publication validation, WP04
  and production acceptance remain open.
- No Aletheia event log, index, approval or live runtime was modified by this
  repair owner. Its sole writer must recover through its supported workflow.
- Test collection currently adds about 52 seconds to this focused run; the seven
  assertions themselves each take less than one second. No optimization claim.
