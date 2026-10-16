---
title: WP03 Native Local Validation
description: Check-owned native sampler lifetime and local execution custody.
doc_status: active
updated: '2026-10-16'
---

# WP03 Native Local Validation

## Objective And State

Implement the owned native sampler lifecycle for WP03/T011, with exact source
and request binding, a retained direct-child owner across declared commands,
final sampling and joined stop on success or middle-command failure, and private
machine-readable evidence. The active lane is `codex/native-local-validation`
in the existing managed worktree. It began this turn at `614d3a30f`; work is
local, uncommitted, and unpushed. This log continues the history in
[`2026-10-12-native-local-validation.md`](../plans/engineering-notes/2026-10-12-native-local-validation.md),
including its WP03 sampler-lifetime scope coordination.

The PDB 178-row/16-original checkpoint-source-release-r1 notice is pending
intake only. No producer resume, Store write, PUT, CAS, old approval reuse, or
second Store was selected by this lane.

## User Experience Findings

- The first lifecycle control exposed that recipe-step fixtures could overwrite
  the marker consumed by a dependent check. The fixture now uses a distinct
  marker for the middle command, preserving the declared producer-consumer
  relationship.
- The sampler state, cgroup artifact, and summary must live under the private
  diagnostics root. A mislocated fixture was refused before any sampler process
  or output effect; output paths are now checked during preparation so this
  static mistake does not leave an empty run receipt.
- A full local-validation run against the prior frozen candidate completed with
  1,441 passed, 31 skipped, and two failures. The aarch64 Linux cross-build
  failure was a real C ABI translation defect in candidate file metadata
  inspection; the other failure reached Docker but the container could not exec
  its mounted probe at `/input/executor`. That runtime observation remains
  unresolved and is not being called transient without a successful retry.
- Re-running the isolated cgroup case did not reach Docker: its 120-second
  static-probe build limit expired while unrelated Zig validation builds were
  active. This is setup-timeout evidence and does not resolve the original
  missing-executor observation.
- One initial candidate-suite invocation used the system Python and failed all
  73 setup cases because that interpreter lacks the locked `re2` dependency.
  No test body ran. The repository-managed `uv run --frozen` environment is the
  required test surface and has since passed the candidate suite against the
  current source-bound image.
- This checkout does not contain the referenced `docs/mission-log-procedure.md`.
  The log follows the current [Kaizen mission-log procedure](https://github.com/crucible-energy/kaizen/blob/4ca2672d97ffe34d9a7d9a4df3d6f8b6c93c8b51/docs/mission-log-procedure.md)
  as read from the sibling repository; adding the missing local procedure is a
  separate documentation follow-up.

## Engineering Decisions

- Keep `memory_output` unavailable by default. Preparation accepts it only when
  the exact sampler declaration, command positions, request pins, output paths,
  and scoped worker qualifications agree.
- Preserve both legacy raw qualification records and the new exact
  `{check_id, command_index, qualification}` wrapper. Repeated argv alone cannot
  disambiguate a command reused by different checks or recipe steps.
- Report ready and stopped attempts from the actual worker acknowledgements;
  require the ready acknowledgement to attest the first sample. The parent
  independently checks the final state bytes, metadata, directory identities,
  PID, and sample count before rendering or appending output.
- Write the cgroup result through an exclusive no-follow file descriptor and
  verify exact readback. On macOS the actual cgroup peak is unavailable and
  remains `na`; no zero measurement is substituted.
- Reject non-hex acknowledgement digests. Keep macOS and Linux as the
  immediate qualification priorities; sequence Windows after both and use actual
  Windows execution only. Parallels is out of scope on this Mac. Linux child
  execution remains unimplemented and cannot be inferred from macOS tests or
  foreground sampler controls.
- Transfer the freshly spawned sampler PID into `DirectChild` custody before
  closing the parent's socket copy or performing further fallible setup. If
  owner construction itself refuses, use Zig's returned child handle to kill
  and join that spawn; every later setup failure uses the supervisor's bounded
  cleanup path.
- Linux metadata observation uses Zig's target-owned `statx` ABI and projects
  the required identity, mode, ownership, size, and timestamp fields into a
  platform-neutral snapshot. This avoids depending on musl's C `struct stat`
  translation while preserving descriptor-versus-path drift checks.

## Known Limitations

- The full local-validation suite has not passed on the current frozen source.
  The prior complete run had the two failures above; the Linux cross-build
  issue is fixed and covered by a fresh build, but the broad suite has not been
  repeated. The cgroup retry remains compile-blocked under unrelated host load.
- Linux child `CheckScope`, retained command supervision, and actual Linux recipe
  controls remain unimplemented. The current source still refuses recipe
  execution outside macOS, so WP03 does not meet the Mac-and-Linux priority.
- The branch has not yet completed the repository publication hook, Spec Kitty
  review, commit, push, PR, or merge. No deployment, model, Source, Store, or
  production-hook qualification is established.

## Validation And Delivery

- Zig 0.16.0 ReleaseSafe compilation of `tools/zig/validation_execution.zig`
  passed after both the output-path preflight and ownership-handoff changes.
- The focused ReleaseSafe Mac executor is retained at
  `/private/tmp/spec-kitty-native-validation-20261016/final-executor`; the fresh
  Linux cross-build is `/private/tmp/spec-kitty-native-validation-20261016/linux-executor`,
  and the Mac candidate build plus exact binding are
  `/private/tmp/spec-kitty-native-validation-20261016/final-candidate` and
  `candidate-binding.json`.
- `test_native_check_owned_sampler_finalizes_after_actual_middle_argv[ordinary]`
  and `[nonzero]` plus the three direct worker final-attempt cases passed against
  the ownership-handoff change (5 passed, 422 deselected; 289.26 seconds).
- The current candidate module cross-compiles as part of the static
  `aarch64-linux-musl` executor and builds natively on macOS in Zig 0.16.0
  ReleaseSafe mode. The current-source candidate suite passed: 72 passed, 1
  skipped in 87.94 seconds under `uv run --frozen`.
- `make test-fast` passed before the candidate portability fix (2,451 passed,
  5 skipped, 4 warnings); Ruff, Zig formatting, `git diff --check`, and docs lint
  also passed before the fix. Repeat only checks affected by the final Linux
  supervision work after its source and documentation are frozen.
- Earlier on the same lane, FIFO/final-binding controls passed (3 passed) and
  Ruff checks passed; rerun relevant controls after the candidate is frozen.
- Next: finish the Linux process owner and actual Linux recipe controls, then
  retry the cgroup probe after the currently active Zig load clears. Run the
  required gates against one frozen tree, self-review, and deliver through the
  existing Spec Kitty workflow. Do not claim WP03 or native local validation
  complete until Linux ownership and the unresolved runtime control pass.
