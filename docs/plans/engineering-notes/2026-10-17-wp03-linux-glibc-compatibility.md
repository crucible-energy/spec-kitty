---
title: WP03 Linux/glibc Compatibility
description: Native local-validation portability across Linux libc interfaces.
doc_status: active
updated: '2026-10-17'
---

# WP03 Linux/glibc Compatibility

## Objective And State

This entry extends the WP03 history in
[`2026-10-16-wp03-native-local-validation.md`](2026-10-16-wp03-native-local-validation.md)
and its original engineering notes in
[`2026-10-12-native-local-validation.md`](2026-10-12-native-local-validation.md).
The active lane is `codex/native-local-validation`, based on
`d7f7eb5ae3053223898c5b62bf8b8e28680c3ef0` in the existing checkout at
`/Users/sam/git/crucible/_worktrees/spec-kitty-owned-single-branch-recovery`.
The separate test-first increment is committed and pushed as
`e84bcb45a` (`test(WP03): cover sampler lifetime boundaries`).

The change closes a real Linux/glibc build gap in the native executor and keeps
the platform-specific test boundary explicit. WP03 remains active: its last
measured statement-coverage checkpoint was 1,253/1,626 (77.0603%) for the
previous source map. That map predates this source change and is not a current
coverage result. The 90% gate and independent WP03 review remain open.

The separate PDB 178-row/16-original checkpoint-source-release-r1 packet remains
intake-only in this lane. No Store, source, producer, model, GPU, or grant action
was selected.

## User Experience Findings

- Native source that had passed Linux/musl controls failed to compile against
  Linux/glibc headers. Zig's C importer evaluated glibc's fortified `open` and
  `openat` wrappers as invalid call sites; subsequent errors exposed different
  glibc layouts for `sigaction` and `getpeername`. The existing Linux controls
  used musl and therefore did not reveal these common-distribution failures.
- The test helper accepted Darwin's `arm64` machine label but not Linux's
  `aarch64`, causing Linux tests to fail before reaching their assertion. The
  architecture map now accepts both labels.
- A read-only checkout cannot host Zig's test-runner temporary directory:
  `std.testing.tmpDir()` creates `.zig-cache/tmp` under the current directory.
  Linux tests therefore ran from a writable external source copy, keeping the
  managed checkout and its ignored state untouched.
- The recipe-level capture controls are Darwin-specific. On Linux the candidate
  capture path correctly refuses with `PlatformUnqualified`; those controls are
  now marked Darwin-only, while Linux sampler behavior is exercised through its
  own native tests.

## Engineering Decisions

- Set `_FORTIFY_SOURCE` to `0` only inside the relevant Zig `@cImport` blocks.
  Zig calls the imported libc functions with explicit, typed argument counts;
  the imported glibc C-call-site fortify wrappers are not compiled C code and
  cannot be meaningfully applied to those Zig call sites. This keeps runtime
  calls and their argument checks unchanged while allowing the headers to be
  translated.
- Select the glibc `sigaction` handler union by field reflection and retain the
  existing musl and Darwin layouts. For `getpeername`, pass glibc's transparent
  `sockaddr_un` union member when it exists and retain the pointer form on
  musl/Darwin. No local ABI layout was invented.
- Keep the Linux probe and sampler fixtures native to their declared platform.
  Darwin foundation tests are not treated as Linux qualification; the Linux
  memory-sampler path carries its own runtime controls.
- Refactor the test fixture's document-fault setup into a small helper after
  Ruff identified excess branching in the setup function. Add an explicit
  lifetime precondition for the mismatch fixture so strict mypy can verify the
  access.

## Validation

- Linux ARM64/glibc, Zig 0.16.0: the native memory-sampler module passed 322
  tests; 7 were skipped and 34 Linux-container integration cases were
  deselected because this inner container has no Docker CLI. Output:
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261017-r17/linux-output-r2/memory-sampler-linux-r4.log`
  (SHA-256 `926fb1e21a099ab0d1b79a32e87e01ca9657157cc50bf61a82d758ea19ced4f8`).
- macOS, Zig 0.16.0: the full native memory-sampler module passed 334 tests and
  skipped 29; the run included the existing Linux-container controls through
  the Mac host's Docker runner. Output:
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261017-r17/mac-output-r1/memory-macos-r1.log`
  (SHA-256 `a42e471e62102ff5044993e553ea228fa23b41ef5fd1e5ab0afacb25690ff1a7`).
  Pytest reported no failures; the surrounding zsh wrapper then hit its
  read-only `status` variable while propagating the result.
- macOS recipe regressions for lost worker cleanup, replaced output directory,
  and unsafe sampler startup passed 4/4. Output:
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261017-r17/mac-output-r1/execution-macos-r2.log`
  (SHA-256 `469454d7b597cdd2734ac324b000bef21225b9e39c4fdf245e9abe76eef637f9`).
- The sampler-lifetime refusal matrix passed 28/28 on macOS. Output:
  `/private/tmp/spec-kitty-wp03-statement-coverage-20261017-r17/mac-output-r1/lifetime-fault-macos-r1.log`
  (SHA-256 `50a7d0e71107b5fa4786a5700b5412b1e1fd751f2213e63951699b02b2b5f4a5`).
- Ruff check, Ruff format, strict mypy for `test_execution.py`, Zig formatting,
  and `git diff --check` passed. `make docs-lint` reported zero findings and
  zero errors; it surfaced 19 existing changelog entry-length warnings outside
  this change.

## Known Limitations

- The 90% changed-native-statement coverage gate is still open. The previous
  77.0603% result is stale for this source; regenerate the source map and
  instrumented traces before making a current percentage claim.
- The 34 nested Linux-container controls were not run from inside the Linux
  test container because it lacks a Docker CLI. The Mac-hosted test run covered
  the existing pinned Linux container controls; no nested daemon was introduced.
- The Linux execution-recipe tests remain outside platform qualification where
  candidate capture returns `PlatformUnqualified`. The native Linux sampler
  controls provide the applicable evidence; they do not establish broader
  Linux recipe qualification.
- Independent review, the remaining WP03 coverage gate, and the mission's other
  qualification requirements remain outstanding. This increment does not
  establish hook installation, hosted retirement, deployed integration, model
  quality, or production readiness.
