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
in the existing managed worktree; its latest delivered checkpoint is
`16b8cfbc9a2048564ee5fb0254e5ccf3aa904abf`; the current local increment makes
spawn-input refusal consistent across macOS and Linux and extends its contract
tests. WP03 acceptance remains gated by qualified native statement coverage and
independent review.
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
- 2026-10-16 update: the inventory refusal blocked qualification of valid
  switch-arm and inline-loop statement bodies as well as value-producing
  expressions. The collector now separates executable statement bodies from
  value expressions and compile-time controls; a paired compiled sentinel
  checks output and hit multiplicity before relying on those categories.
- 2026-10-16 — The expanded Linux process probe first exited 139 because its
  test fixture attempted to insert an invalid environment key, which Zig 0.16
  asserts against inside `Environ.Map.put` before the process boundary runs.
  The fixture now constructs a valid key with an embedded NUL in its value, so
  both command and worker paths exercise their intended `InvalidEnvironment`
  refusal. The corrected source-bound integration and instrumented probe pass.
- The Linux `/proc/<pid>/stat` parser's malformed-input tests exposed how easy it
  is to miscount positional fields in a synthetic row. The first malformed-RSS
  fixture placed its bad value in the preceding `vsize` field, so the parser
  correctly consumed the following zero as resident pages. The cases now share
  the known-good prefix and vary only the intended field.
- `spec-kitty next --json` reports `dependencies_not_satisfied` while WP03 is
  active because it previews a *new* claim and the remaining planned packages
  depend on WP03. The separate status view confirms WP01/WP02 approved and WP03
  in progress; no status repair or forced transition is needed. This expected
  selector result is easy to mistake for a blocked active package.
- The standard test IO clock is not guaranteed to advance like the host clock.
  A new deadline assertion initially compared against a second clock read and
  failed despite valid sampler behavior; it now compares with the request's
  captured start time.
- Zig's multi-module test invocation emitted a macOS binary when the Linux
  target option followed the root module declarations. File-format inspection
  caught it before Linux evidence was claimed; the corrected invocation places
  the target before module declarations.
- The instrumented execution harness uses a source-transformed executable as
  both binder and runner, while its staged files and qualification can describe
  the original source closure. Generic `UnqualifiedProducer`,
  `NativeSourceMismatch`, and `InputDrift` errors obscure that difference and
  cost repeated setup; future harnesses should separate the binder and runner
  while pinning both closures explicitly.
- 2026-10-16 — Rebuilding the isolated coverage mirror initially omitted four
  unchanged imported Zig modules, so its first instrumented compile failed
  before tests ran. Copying those exact unchanged dependencies fixed the setup;
  the helper should make this dependency closure explicit for future runs.
- The system Python on this Mac has no pytest installation. The repository's
  locked `uv run --frozen` environment is the supported route and passed the
  focused source-bound integration test.
- The readiness-failure case reports `SamplerOwnerLost` on macOS and
  `SamplerProtocolRefused` on Linux for the same child exit before the worker
  acknowledgement. The first platform-specific assertion obscured this
  stable refusal boundary; the test now accepts either defined error while
  requiring that startup never succeeds.
- 2026-10-16 — A NUL-containing environment value was rejected before spawn on
  Linux but accepted by macOS `std.process.spawn`, where it later surfaced as
  `SamplerOwnerLost`. The late error concealed malformed input as a worker
  failure; the shared pre-spawn check now refuses the value on both platforms.
- The first full instrumented execution run reported 42 passes and 69 setup
  errors because its temporary harness omitted four unchanged Zig imports.
  Supplying that exact import closure allowed the remaining cases to run. Two
  exact-source-closure tests correctly refused the transformed test binary and
  then passed against the ordinary source build.

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
- 2026-10-16 — Extend the native statement collector only with paired
  compilation and execution controls. Add explicit switch-arm bodies and
  compile-time loop classification, and preserve statements embedded in
  value-producing `if`, `catch`, `switch`, and `defer` expressions without
  treating those expressions as statements. Keep the instrumentation harness
  outside the product tree; it is measurement support, not a new runtime
  capability.
- 2026-10-16 — Exercise malformed environment values through Zig's supported
  `Environ.Map.put` API rather than constructing an impossible invalid key.
  Keep the invalid-input cases paired across Linux command spawning and retained
  worker spawning, and verify missing-image, denied-image, process-group, signal,
  usage, and reap behavior in the actual pinned Linux container.
- Exercise the proc-stat parser's malformed identity, delimiter, state, process
  group, and resident-page cases from one known-good field prefix. Run the same
  Zig unit test on macOS and as an AArch64 Linux binary in the already pinned
  container, keeping Linux parser evidence distinct from the broader process
  group integration result.
- Expand the owned sampler fixture with bounded-attempt, request-binding,
  commitment-mismatch, duplicate cgroup-output, and invalid-summary cases.
  Validate the unchanged native contracts on both target platforms; never
  weaken the executor's embedded-source qualification to obtain coverage.
- 2026-10-16 — A temporary producer path can be normalized without changing
  policy, but the test binary, binder, process-source digest, and staged
  producer closure must still describe the same bytes. The r13 execution
  attempts exposed mismatched source closures, so their traces are excluded
  from the acceptance aggregate.
- Added direct contract tests for strict diagnostics-root containment and
  summary append rejection of line injection and unsafe paths. Keep these as
  focused API-boundary tests; their only new measured hits are the two
  diagnostics-path rejection statements, while the summary-input rejection
  statements were already covered by prior traces.
- Add an owned-worker startup failure case using a short-lived local child.
  Require a refusal before readiness on both platforms and keep the test's
  accepted error set limited to the two observed protocol/ownership outcomes.
- Validate argv and environment once at the shared process boundary before
  platform-specific spawn setup, and call it before sampler socket creation.
  Keep the checks in the macOS/Linux process paths and Linux worker path aligned.
  Zig 0.16's `Environ.Map.put` asserts on malformed keys, so tests use representable
  invalid values and arguments instead of triggering that assertion before the
  boundary under test.
- 2026-10-16 — Reconcile old trace IDs for the modified process and sampler
  files only when exact statement bytes, AST tag, origin flags, and enclosing
  function/test produce one unique match. Discard ambiguous, deleted, or changed
  statements rather than carrying source-stale hits forward.

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
- Superseding the collector-refusal diagnosis above: the source-bound Zig
  inventory now generated and verified inventories for the seven changed
  Zig files in the measured WP03 set. The external isolated native trace
  measured 1,082 of 1,562 changed statements (69.27%), below the 90% gate by
  324 statements. The current harness and its source maps/traces are retained
  under `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r9/` for
  continued investigation; this partial measurement is not WP03 acceptance.
- 2026-10-16 — Superseding the 1,082/1,562 partial measurement: after checking
  that its trace rows reproduce that count, 66 Linux fixture hits tied to the
  previous fixture source hash were excluded. A fresh instrumented Linux run
  against the current source map yields 1,162/1,622 statements (71.64%), still
  298 hits below the required 1,460. The exact current summary and deduplicated
  trace are retained under
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r9/`; coverage is
  still incomplete and WP03 is not ready for acceptance.
- The parser-control test changed `validation_process_darwin.zig` after that
  aggregate was measured. Its prior 1,162/1,622 result remains valid only for
  the earlier process-source hash and is not a current aggregate. Rebuild the
  source map and regenerate the affected Mac/Linux native traces before making
  another total-coverage claim; the 90% gate remains open.
- WP03 has not yet completed independent Spec Kitty review, PR review checks, or
  default-main integration. No deployment, model, Source, Store, or
  production-hook qualification is established.
- The latest verified changed-statement aggregate remains below acceptance at
  1,219/1,623 (75.11%), 242 hits short of the 90% threshold. A source-equivalent
  instrumented executor was refused by the existing sampler qualification
  boundary before worker startup; the measurement harness did not bypass that
  check. Further coverage work must use owner-compatible source-bound fixtures
  or improve the approved deterministic inventory path.
- 2026-10-16 — Freshly rebuilt the ReleaseSafe native statement collector
  (binary SHA-256 `106bc45c5a165291bbde438243343f2619f237ce6f14da456f0e07a11264f250`)
  and verified all seven current source files. Their source hashes and selected
  statement node identities match the saved r10 denominator exactly: 1,623
  changed statements. This validates the denominator inputs, not trace
  completeness or the 90% acceptance gate.
- 2026-10-16 — The focused instrumented execution case still did not produce a
  passing run after path normalization. The last retained attempt is
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r13/execution-ordinary-current-source-bind.log`
  (SHA-256 `f37f6773ea45ed96cb5f52b3f035644cd38fa38682f70ef9c3dcaa5464e3e280`).
  Failed-run traces are excluded from the coverage total. The instrumented
  sampler rerun reproduced its previous trace and added no changed-statement
  hits, so it is not a useful repeat.
- 2026-10-16 — The refreshed source-bound aggregate is 1,221/1,623 (75.2311%),
  with 240 more selected statements required to reach 1,461/1,623 (90%). The
  two new diagnostics-path hits are real but do not materially close the gate;
  WP03 remains incomplete and the result is not acceptance evidence.
- 2026-10-16 — The owner-cleanup test adds 14 newly covered statements, bringing
  the source-bound aggregate to 1,235/1,623 (76.0937%). Another 226 selected
  statements remain to reach 90%; no acceptance or review-ready claim follows.
- 2026-10-16 — The fresh current-source aggregate is 1,239/1,626 (76.1993%),
  225 below the 1,464 statements required for 90%. The exact-source statement
  reconciliation and current trace receipt are retained in
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r15/`. The two exact
  source-closure tests cannot run against transformed bytes; both passed with
  the normal source build. WP03 remains incomplete.

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
- The current Zig inventory changes passed the focused collector/sentinel suite
  (9 passed in 32.34 seconds after the final transform simplification), Zig
  formatting, Ruff lint/format, and `git diff --check`. The full instrumented
  macOS execution suite passed 111 tests in 223.18 seconds. Its trace joins
  prior source-bound memory, collector, and Linux-container traces at
  1,082/1,562 statements (69.27%). The optimized trace helper used one
  process-local descriptor; a prior run took 235.24 seconds, so these two
  observations do not establish a repeatable time saving. The structured
  measurement receipt is
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r9/coverage-summary.json`
  (SHA-256 `6ecbe5b0ad1ef3672055555a7c8355c0e8ba217479e354f300773a124ae2ff03`).
  The optimized execution rerun's full raw output was not retained; the earlier
  complete 111-test output remains at `execution-clean.log` in that artifact
  directory.
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

- Current expanded Linux process-backend controls passed the source-bound
  `test_actual_linux_process_group_and_sampler_worker_ownership` test (1 passed
  in 1.50 seconds using a ReleaseSafe `aarch64-linux-musl` binary built from the
  exact current fixture and process source hashes). Full output is retained at
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r9/linux-process-regular-pass.log`
  (SHA-256 `1dd964c8df5c6037c0411f6c9e9e4fe0835174af1d26e7bc6476ab6683fe5961`);
  the source and executable binding is
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r9/linux-process-backend-binding-current.json`.
- The instrumented copy of that probe also exited zero in the pinned Linux
  container with joined cleanup. Its current-source witness is
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r9/linux-instrumented/retained-run-r1/output/fixture/process-backend.json`
  (SHA-256 `6375bcc942a1873606252f6c0e7924b1adc55fa5ad8ea2ce155462117fefc794`)
  and its trace is
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r9/linux-instrumented/retained-run-r1/output/statement-trace.log`
  (SHA-256 `d324559ecb24600464b285f511e34d1911ed807c0c37b2bea044c2cd6a641775`).
  The updated measurement receipt is
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r9/coverage-summary.json`
  (SHA-256 `85d0754433cb6719a197dc8169516ea47428d187e712d36b54183c141499045a`).
- The expanded proc-stat parser unit passed on macOS (1/1) and as an
  `aarch64-linux-musl` test binary in the existing pinned Linux image (1/1).
  Both complete outputs are retained under
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r9/parser-malformed-controls/`;
  their SHA-256 is `51367bcf958aaea9dd676c4309e2e342d24bb099f031d03dfcbe2abda24367d0`.
  The tested source SHA-256 is
  `4ebb916c0abfebdb7f5fd40685b8564305c9ccdeb16549ac6878844421bf55d4`, and the
  Linux test executable SHA-256 is
  `8f9f52abbee41fde877696562cc596f935dcc981d09240a56a98e9da31e53efc`.
- After the parser test and implementation-log updates, `git diff --check`,
  `zig fmt --check tools/zig/validation_process_darwin.zig`, and `make docs-lint`
  passed. Documentation lint reported zero errors and 19 existing changelog
  length warnings.
- 2026-10-16 — The expanded owned-sampler fixture passed 5/5 on macOS and 5/5
  in the pinned Linux ARM64 image `6b13e377e404ac4a3e8f307f79fa0621893d931bbd73d6c3116bc4a1556e0b2c`.
  The memory-sampler module passed 5/5 and sampler-lifetime passed 6/6 in that
  same Linux image. The source-equivalent instrumented native sampler suite
  passed 334 tests with 29 declared skips in 153.59 seconds; its trace added no
  new changed-statement hits to the existing aggregate. The aggregate remains
  1,219/1,623 (75.11%), so WP03 is still in progress. The focused Python test
  passed 1/1 in 25.47 seconds using the normal source build. Linux logs under
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r10/` have SHA-256
  `655ad6975b347da97d21a2b4635723fed52f5c602a457c9fa59306b5ef1b954c`,
  `cec31ae15c450f9ad9c2a9ee6f528f141d3eb1d1881fb99e218d64c4588b3b0b`, and
  `4ba1e4f048918f677b1e39bdd03847d4d532d81ee9966eaf1b1e1b09292272b9` for the
  owned fixture, memory module, and lifetime module, respectively. The focused
  Python log SHA-256 is
  `87e5a05f0e15d843e787e2abb24e5dc43ca3746603140bbf6fcc704aab89347b`.
  The fresh source-bound coverage receipt is
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r10/coverage-summary-r10-final.json`
  (SHA-256 `7e74379a9e0ea66828b8e31d02029097d55447009340215efecf34bd2349da75`).
- 2026-10-16 — Fresh source-bound inventory comparison is retained under
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r12/current-inventory-comparison.json`
  (SHA-256 `d235ff7f9e753d4e29a216ad14480857451357839be76044ad496e42a228179d`).
  All seven files were accepted, each source hash matched, and every selected
  node ID was present in current native inventory output. The 1,219/1,623 result
  remains partial; WP03 still needs valid additional coverage, independent
  review, and the remaining platform and entry qualification gates.
- 2026-10-16 — Added and ran the diagnostics-path and summary-input contract
  tests on macOS and the pinned Linux/arm64 Zig 0.16.0 image. The focused
  repository test passed 1/1. Instrumented current-source runs produced four
  per-platform traces; after validating candidate identities against the prior
  map, the aggregate is 1,221/1,623 (75.2311%). Full observed outputs and the
  partial measurement receipt are retained at
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r14/focused-validation.log`
  (SHA-256 `85a0db3c0db6dbb70c543fbfc4ab60f632a20c675d8e39c26fca84bef529041c`)
  and `coverage-summary-r14-partial.json` (SHA-256
  `c1b6b14b49e26159ffb9c5af80763c3d5d1e8af44a4ec909865e30eab24e92f0`).
  `make docs-lint` passed with zero errors and 19 existing changelog-length
  warnings; formatting and `git diff --check` passed. This remains partial
  WP03 evidence; independent review and the 90% gate are still outstanding.
- 2026-10-16 — Five instrumented recipe drift/cancellation cases passed on
  macOS but added no new selected statements. The worker-readiness failure test
  passed 7/7 on macOS and Linux/arm64 and added 14 statements (13 in sampler
  lifetime control, one in process supervision). Full outputs and current
  source map are retained at
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261016-r14/focused-validation-r14-lifecycle.log`
  (SHA-256 `e754431b59cc3ffe0391bd5ba30526d5535329dac5656e221f146cf146e04fa3`)
  and `coverage-summary-r14-lifecycle.json` (SHA-256
  `bc3bd9968bb6b5cf9d1d08b77ececbf94d46aacb1a6a7aaf8970650b6ebe47ff`).
  The 1,235/1,623 result remains partial; WP03 still needs 226 additional
  selected hits, independent review, and the remaining platform and entry gates.
- 2026-10-16 — The shared spawn-input validator passed macOS Zig process tests
  (2/2) and sampler-lifetime tests (9/9). Instrumented current-source versions
  passed 2/2 and 9/9 on macOS and in the pinned Linux/arm64 Zig 0.16.0 image.
  The execution integration set had 109 passing current-source instrumented
  cases; its two exact source-closure cases passed separately without
  instrumentation. The exact-source Linux process-group and worker-ownership
  integration passed (1 passed in 101.61 seconds). The source-bound macOS
  process probe refused invalid argv, cwd, environment key, and environment
  value before child effects (4 passed).
- The current-source instrumented Linux backend fixture also passed in the
  pinned runtime image, including invalid-input refusal, group cleanup, and
  worker reaping. Its witness SHA-256 is
  `6375bcc942a1873606252f6c0e7924b1adc55fa5ad8ea2ce155462117fefc794`; the
  coverage receipt is `coverage-summary-r15-partial.json` (SHA-256
  `98dbc865ee65a4f8f7d8d58b4f62169dc908dbb0ceecb9482ba20d05d57ecf12`). The
  exact-source Linux integration log SHA-256 is
  `1519a8dba620b7eb2f231d204c8feafeb9653496a4f7428f7861bf35819e12e0`.
  Formatting, `git diff --check`, updated docs lint, and final branch delivery
  checks remain to be run.
