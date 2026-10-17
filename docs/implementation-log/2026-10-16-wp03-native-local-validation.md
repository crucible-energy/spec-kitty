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
in the existing managed worktree, based on the already-pushed commit
`eee3b2192`. This functional increment remains unmerged; WP03 acceptance is
still gated by qualified native statement coverage and independent review.
This log continues the history in
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
- The first focused Linux process probe pytest run also timed out compiling its
  cold, per-run-isolated Zig cache before it reached Docker. The same static
  aarch64 probe was compiled through the normal local cache and passed the
  actual bounded-container process-group and sampler-worker exercise. The
  compile timeout is an environment/load boundary, not runtime evidence.
- Linux Docker fixtures intermittently reported missing or incomplete bind-mount
  inputs when their source lived under pytest's transient `/private/var/folders`
  tree. Input and output now stage together in a private `/tmp` directory; a
  bounded in-container readiness check verifies the pinned input paths before
  `exec`, and retained evidence is copied back after container cleanup. The
  selected refusal and signal matrix no longer reports the entrypoint miss.
- The Linux signal test could sample the changed fixture before SIGTERM arrived
  under host load. Its interval now leaves enough time for the signal delivery
  step while preserving the specified final sample before cancellation. The
  synthetic `/proc/stat` parser row also had one omitted field; the corrected
  fixture now reaches and verifies the resident-page field.
- The retained native-control test counted only appended foundation tests and
  missed a Linux-specific test already present in the implementation source.
  It now derives the expected Zig test count from the complete generated source,
  keeping the assertion accurate as platform-owned controls are added.
- Git's shared repository config points `core.hooksPath` at a missing
  `.githooks` directory, while the installed Spec Kitty commit guard remains in
  the common `.git/hooks` directory. A normal commit from this checkout would
  therefore miss the installed guard. Delivery will use a command-scoped hook
  path and leave shared Git config untouched; repairing the local hook
  registration remains an operator setup follow-up.
- A focused run of the changed local-validation controls spent 597.88 seconds
  rebuilding native fixtures and reported 104 passing tests plus one setup
  error: the static AArch64 process probe exceeded its 120-second cold-build
  limit before Docker. The exact-source probe's bounded-container behavior had
  already passed; the test harness lacked a supported way to reuse that pinned
  artifact. An opt-in binding now requires the exact two-source set, target,
  optimization, and executable hash before reuse, while the default CI path
  still builds the probe itself.
- Running the full sampler module with the current macOS executor and exact
  Linux process-probe bindings completed in 137.52 seconds: 303 passed, 29
  skipped, and four cgroup-lifecycle cases excluded pending their separate
  probe build. The public AArch64 Linux executor cross-build passed in 88.42
  seconds. After extending the cgroup fixture's setup bound to 180 seconds,
  all four cgroup-lifecycle cases passed in 152.45 seconds; the probe build took
  107.28 seconds under concurrent local Zig load.
- One initial candidate-suite invocation used the system Python and failed all
  73 setup cases because that interpreter lacks the locked `re2` dependency.
  No test body ran. The repository-managed `uv run --frozen` environment is the
  required test surface and has since passed the candidate suite against the
  current source-bound image.
- This checkout does not contain the referenced `docs/mission-log-procedure.md`.
  The log follows the current [Kaizen mission-log procedure](https://github.com/crucible-energy/kaizen/blob/4ca2672d97ffe34d9a7d9a4df3d6f8b6c93c8b51/docs/mission-log-procedure.md)
  as read from the sibling repository; adding the missing local procedure is a
  separate documentation follow-up.
- The approved native statement inventory returns `UnsupportedStatement` with
  empty stdout for each of the six changed Zig sources. Its current grammar
  does not qualify this increment's loop-continuation, switch, inline-loop, and
  value-producing control forms. A relaxed private AST inventory is useful for
  diagnosis only: its experimental transform failed Zig compilation on shared
  statement terminators, confirming that it cannot supply a trustworthy
  denominator or coverage percentage.

## Engineering Decisions

- Keep `memory_output` unavailable by default. Preparation accepts it only when
  the exact sampler declaration, command positions, request pins, output paths,
  and scoped worker qualifications agree.
- Preserve both legacy raw qualification records and the new exact
  `{check_id, command_index, qualification}` wrapper. Repeated argv alone cannot
  disambiguate a command reused by different checks or recipe steps.
- Do not accept a relaxed AST scan, line map, Python XML, or uncompiled probe
  as the native changed-statement denominator. Keep the approved collector's
  refusal visible and extend its supported grammar only with paired
  compile-and-run semantics controls and an independent fixed-candidate review.
- Report ready and stopped attempts from the actual worker acknowledgements;
  require the ready acknowledgement to attest the first sample. The parent
  independently checks the final state bytes, metadata, directory identities,
  PID, and sample count before rendering or appending output.
- Write the cgroup result through an exclusive no-follow file descriptor and
  verify exact readback. On macOS the actual cgroup peak is unavailable and
  remains `na`; no zero measurement is substituted.
- Reject non-hex acknowledgement digests. Keep macOS and Linux as the
  immediate qualification priorities; sequence Windows after both and use actual
  Windows execution only. Parallels is out of scope on this Mac. Implement Linux
  child execution as a separate `posix_spawn` process-group path with exact
  `waitid` ownership and bounded `/proc` census; macOS tests do not establish
  Linux behavior.
- Transfer the freshly spawned sampler PID into `DirectChild` custody before
  closing the parent's socket copy or performing further fallible setup. If
  owner construction itself refuses, use Zig's returned child handle to kill
  and join that spawn; every later setup failure uses the supervisor's bounded
  cleanup path.
- Linux metadata observation uses Zig's target-owned `statx` ABI and projects
  the required identity, mode, ownership, size, and timestamp fields into a
  platform-neutral snapshot. This avoids depending on musl's C `struct stat`
  translation while preserving descriptor-versus-path drift checks.
- Linux command supervision and retained sampler workers use separate spawn
  paths but share explicit direct-child custody, bounded group disposal, and
  joined cleanup. Linux scope/recipe guards are enabled only for the owned
  local-validation path; no production or remote execution capability follows.
- The Linux process integration fixture can reuse an externally retained probe
  only through an explicit binding that checks target, optimization, exact
  source set and source hashes, and executable hash. Without that opt-in, the
  regular test build remains the default.
- Set the cgroup-lifecycle probe setup timeout to 180 seconds, matching the
  public Linux executor build fixture, because its prior 120-second cold build
  expired under concurrent local Zig builds before reaching Docker.
- Derive the native-control completion count from the full compilation unit,
  which includes implementation-owned tests as well as appended foundation
  controls. The prior assertion counted only the latter and falsely failed
  after the Linux stat projection control was added.
- Docker test fixtures stage inputs and outputs together under a private
  `/tmp` directory and use a bounded readiness relay before `exec`. This keeps
  transient macOS `/private/var/folders` bind-mount visibility from being
  mistaken for program behavior while retaining exact test evidence after
  container cleanup.

## Known Limitations

- The changed native local-validation suites were verified in focused runs
  because the Mac and Linux tests require different host and container
  bindings. The repository's `make test-fast` gate now passes on the current
  source; the native suites also pass in their source-bound Mac and Linux runs
  recorded below. These separate runs do not qualify an untested host/runtime.
- The selected oversized-input refusal leaves an empty `new-state` directory;
  current tests do not assert its absence, so whether that residue violates the
  contract remains an open question rather than a claimed product defect.
- On a busy host, the default cold process-probe AArch64 build can exceed its
  120-second setup limit. The opt-in exact binding avoids a repeated local
  compilation when a separately retained, hash-verified probe is available;
  it does not change the default CI build path or establish behavior on a
  different host/runtime.
- The repository-wide `core.hooksPath=.githooks` points to a directory absent
  from both the primary checkout and this worktree. The actual generated
  commit guard is in `.git/hooks`, so this repository-level setup mismatch must
  be repaired separately; the delivery command will invoke the existing guard
  through a one-command path override.
- The required threshold of at least 90% changed executable statement coverage
  is not established. The approved collector refuses all six changed Zig
  sources, and the exploratory relaxed transform is not valid denominator
  evidence. Until that grammar boundary is qualified, WP03 is not ready for
  independent review or completion.
- The branch has not yet completed independent Spec Kitty review, commit, push,
  PR, or GitHub review checks. No default-main integration, deployment, model,
  Source, Store, or production-hook qualification is established.

## Validation And Delivery

- Zig 0.16.0 ReleaseSafe compilation of `tools/zig/validation_execution.zig`
  passed after both the output-path preflight and ownership-handoff changes.
- The current-source macOS executor and source binding are retained at
  `/private/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/spec-kitty-pytest-tmp/run-64371/native-memory-sampler0/executor`
  and `/private/tmp/spec-kitty-native-validation-20261016/current-macos-executor-binding.json`.
  The fresh Linux executor and source binding are
  `/private/tmp/spec-kitty-native-validation-20261016/linux-executor-final` and
  `linux-execution-binding.json`; the Mac candidate is
  `/private/tmp/spec-kitty-native-validation-20261016/final-candidate` with
  `candidate-binding.json`.
- `test_native_check_owned_sampler_finalizes_after_actual_middle_argv[ordinary]`
  and `[nonzero]` plus the three direct worker final-attempt cases passed against
  the ownership-handoff change (5 passed, 422 deselected; 289.26 seconds).
- The current candidate module cross-compiles as part of the static
  `aarch64-linux-musl` executor and builds natively on macOS in Zig 0.16.0
  ReleaseSafe mode. The current-source candidate suite passed: 72 passed, 1
  skipped in 87.94 seconds under `uv run --frozen`.
- Linux backend parser unit passed (1/1), and the focused Linux foreground
  public-entry control passed (1/1) against the source-bound pinned image.
  Focused macOS executor regressions passed (8/8). The actual bounded-container
  Linux process-group/sampler-worker integration passed with cleanup verified
  (1/1 with the exact bound probe).
  The focused Linux signal/deadline/custody case passed, including the synthetic
  denied-path evidence preservation check (1/1). Direct bounded-container FIFO
  and oversized-input refusal checks also passed; complete matrix status remains
  open.
- Exact-source Linux executor and integration evidence are retained under
  `/private/tmp/spec-kitty-native-validation-20261016/`, including
  `linux-execution-binding.json` and
  `linux-process-backend-integration/focused-integration-result.json`.
- The required `make test-fast` baseline passed (2,451 passed, 5 skipped, 4
  warnings; 169.65 seconds). A focused changed-file run completed with 104
  passed and one setup error after 597.88 seconds, isolated to the cold Linux
  probe build. Re-running the Linux process integration with the exact bound
  probe and four binding-drift cases passed (5 passed in 43.62 seconds); the
  external binding is
  `/private/tmp/spec-kitty-native-validation-20261016/linux-process-backend-binding.json`.
- The full sampler test module passed except the separate cgroup lifecycle
  probe, which was run afterward and passed all four modes. The module run
  reported 303 passed, 29 skipped, 4 deselected in 137.52 seconds; the cgroup
  lifecycle run reported 4 passed in 152.45 seconds, including 107.28 seconds
  of probe setup. The deselected cgroup cases are therefore covered by the
  second run; 29 platform or separately bound Linux probe cases remain skipped.
- The exact-source Linux bounded-container sampler matrix passed 28 controls in
  31.92 seconds. The exact-source Linux cgroup lifecycle controls passed four
  modes in a separate 152.45-second run. The current-source execution test file
  passed 96 tests in 211.04 seconds after fixing the stale test-count assertion;
  the first run had 95 passes and one failure caused by that assertion, not by
  execution behavior. Its focused corrected test also passed independently.
- `make docs-lint` reported zero errors and 19 existing changelog-length
  warnings. After the final binding guard, scoped Ruff lint and formatting,
  Zig formatting, and `git diff --check` all passed. The source-bound process
  integration plus four binding-drift cases passed again after that guard
  (5 passed in 43.62 seconds).
- After correcting the native-control count assertion to include tests in both
  the implementation source and appended controls, the full
  `tests/local_validation/test_execution.py` module passed (96 passed in
  211.04 seconds). `make test-fast` then passed on the current source
  (2,451 passed, 5 skipped, 5 warnings in 167.27 seconds).
- Final scoped checks passed after the execution-count correction: Ruff lint
  on the changed Python test modules; Ruff formatting on the changed Python
  test modules; Zig formatting on the changed implementation and fixture
  files; `git diff --check`; and `make docs-lint` (zero errors, 19 changelog
  length warnings). The protected untracked Windows-only test file was not
  edited, executed as a test, or staged; a read-only Ruff invocation
  accidentally included it twice, which had no file effects.
- `make test-fast` passed before the candidate portability fix (2,451 passed,
  5 skipped, 4 warnings); Ruff, Zig formatting, `git diff --check`, and docs lint
  also passed before the fix. Repeat only checks affected by the final Linux
  supervision work after its source and documentation are frozen.
- Earlier on the same lane, FIFO/final-binding controls passed (3 passed) and
  Ruff checks passed; rerun relevant controls after the candidate is frozen.
- After the test-helper cleanup, the current
  `tests/local_validation/test_execution.py` module passed again: 111 passed in
  297.86 seconds. The complete output is retained at
  `/private/tmp/spec-kitty-wp03-final-20261016/execution.log` (SHA-256
  `dbb4eb7eae02cbbd76cb78e8c1f2ed11d740a4128338fe1554f24f098918de50`).
- The current `tests/local_validation/test_memory_sampler_native.py` module
  passed: 333 passed, 29 skipped in 180.35 seconds. The same run completed the
  AArch64 Linux cross-build and exercised the Linux process-group and cgroup
  controls present in this environment. Full output:
  `/private/tmp/spec-kitty-wp03-final-20261016/sampler.log` (SHA-256
  `24e947b4db182e32b7c3fd27f5e13ac55316d18694847597ac709418c38e4e7c`).
- The current `tests/local_validation/test_receipt.py` module passed: 96 passed
  in 378.27 seconds. Full output:
  `/private/tmp/spec-kitty-wp03-final-20261016/receipt.log` (SHA-256
  `b7024c3a53a8c2d198a2f8917704892da9e9060d6001ffc6f9854f87a2fef11e`).
- The approved Zig statement-inventory binary was rebuilt with Zig 0.16.0 and
  refused all six changed native Zig sources with `UnsupportedStatement` and
  empty stdout. The source and tool hashes plus exact per-source diagnostics
  are retained at
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r8/canonical-refusals/refusals.json`
  (SHA-256 `809e3986ed5b53233319c05753dcc8f699b9dd249804f4c0a8adf13dfa0726ab`).
  No percentage is claimed from the relaxed experimental inventory.
- Final Ruff lint and format checks, focused strict mypy on the three changed
  Python test modules, Zig formatting on changed implementation and fixture
  files, and `git diff --check` passed. `make docs-lint` passed with zero
  errors and 19 existing changelog-length warnings. Repository-wide
  `mypy --strict src` still reports 108 existing diagnostics in 53 unchanged
  files; it does not qualify or invalidate this focused result.
- Next: extend the approved native statement inventory with semantics-preserving
  support for the current source forms, paired with compile-and-run witness
  controls; or refactor those forms to the already qualified grammar where that
  is simpler and safer. Re-measure the exact frozen source set and obtain
  independent review before treating WP03 as review-ready. The functional
  modules pass, but the 90% gate remains open; no default-main integration,
  trained adapter, deployment, or production-hook qualification is established.
