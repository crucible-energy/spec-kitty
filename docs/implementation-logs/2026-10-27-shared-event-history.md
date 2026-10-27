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

- **2026-10-27:** Adopt the independently owned log procedure from
  [Kaizen's pinned procedure](https://github.com/crucible-energy/kaizen/blob/4ca2672d97ffe34d9a7d9a4df3d6f8b6c93c8b51/docs/mission-log-procedure.md),
  using this project's existing `docs/implementation-logs/` convention.
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

- Final validation, independent review, publication and installed-runtime
  qualification are pending. T010, WP04 and production acceptance remain open.
- No Aletheia event log, index, approval or live runtime was modified by this
  repair owner. Its sole writer must recover through its supported workflow.
- Test collection currently adds about 52 seconds to this focused run; the seven
  assertions themselves each take less than one second. No optimization claim.
