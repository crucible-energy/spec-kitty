# Shared event-history merge repair

## Current state

Owner: Subsequent mission owner, under Root's bounded Source checkout lease.
Scope: status event-log detector, its canonical consolidation driver, focused
regressions and this log. Active lifecycle/native/allocator work and installed
runtimes remain protected. This is a correctness repair to existing Python code
in the owning Spec Kitty project; new Subsequent tooling remains Zig.

## User Experience Findings

- Observed: released 4.0.0rc7 rejects a merge when all 43 records on one side
  already occur with identical payloads among the other side's 57 records.
  Shared post-base rejection/approval cycles are mistaken for independent work.
- Observed: the declared `.githooks` directory is absent in this checkout and
  the primary Source checkout. Delivery must reconcile this with the owner;
  absence is not evidence that required hooks ran.

## Engineering Decisions

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

## Known Limitations

- Repair, final validation, independent review, publication and installed-runtime
  qualification are pending. T010, WP04 and production acceptance remain open.
- No Aletheia event log, index, approval or live runtime was modified by this
  repair owner. Its sole writer must recover through its supported workflow.
- Test collection currently adds about 52 seconds to this focused run; the seven
  assertions themselves each take less than one second. No optimization claim.
