---
title: Owned acceptance verdict implementation log
description: Records the owned acceptance verdict repair, its validation and the documentation taxonomy correction required by CI.
type: explanation
doc_status: point_in_time
updated: 2026-10-10
audience: ../../context/audience/internal/maintainer.md
---
# Owned acceptance verdict repair

Issue: https://github.com/crucible-energy/spec-kitty/issues/59

## Objective and scope

Make the existing `agent mission acceptance-verdict` command record a criterion or
negative invariant in an explicitly validated linked checkout, or adopt a valid
invoking checkout. Keep the installed consumer SDK unchanged during source work.
This repair does not attest any consumer mission or release the SDK.

## User Experience Findings

- **Observed:** the CLI rejects `--owned-checkout` before lookup. A mission held
  only in its owning linked checkout cannot record acceptance evidence through
  the supported command. The actual Typer command reproduced this on
  `34114b4a81cf401bf09aea39fbcfd8167c98903d`; the failing test was committed first
  at `7eb7c0f36`.
- **Observed:** an invariant's check formerly received the repository root,
  which can inspect a different source revision from the mission owner.
- **Observed:** the action-context CLI reanchors the older primary checkout and
  reports no directives. That output is not mutation authority for this source
  slot; the retained current charter, delegated Python Pedro profile, and exact
  root admission govern this repair.

## Engineering Decisions

- Reuse `OwnedCheckoutOption` and `resolve_owned_or_refuse`: validation mints one
  typed fact per invocation. No new ownership resolver or topology set exists.
- Derive mission slug and repository identity from that fact, resolve one
  `ACCEPTANCE_MATRIX` write location through `placement_seam(..., owned=owned)`,
  and preserve it through the bounded lock, reread, splice and downstream writer.
- Pass the identical fact through `write_and_commit_acceptance_matrix` to the
  existing `write_artifact` commit boundary. Unowned callers retain their existing
  optional-argument behavior; the raw non-commit leg remains non-committing.
- Execute negative-invariant checks against `owned.owned_root`. Preserve the
  existing judgment/provenance engine and sibling matrix rows; do not fabricate
  semantic evidence or terminal provenance from routing alone.
- Explicit claims select the mission identity within the claimed checkout.
  Flagless adoption refuses a same-selector/different-identity primary copy,
  according to the canonical minter. These are intentionally distinct contracts.
- Add stale-copy metadata only for owned successes, using the shared helper;
  non-owned payload shape remains unchanged.
- Target the compatible `fix/owned-analysis-implementation` source line following
  https://github.com/crucible-energy/spec-kitty/pull/87. The fork default branch
  lacks this command and has divergent history. No unrelated fork transplant or
  default-branch/released-SDK claim is made.

- Extend the canonical `docs/api/agent-subcommands.md` hand-authored companion
  and regenerate only the two affected verdict help sections using the existing
  `scripts.docs.build_cli_reference.capture_help` and `render_section` helpers.
  The exact source CLI supplies `--help`; unrelated sections and generated agent
  copies remain intact. This directly connected documentation file is the only
  ownership-map extension.

## Executable contracts and guard map

| Contract | Authority | Proof |
|---|---|---|
| Explicit/adopted owner, one validation | `_owned_checkout.py` / `OwnedCheckout` | Real registered-checkout CLI tests plus claim counter |
| Owner-only matrix commit | placement seam / existing write seam | Owner commit content, primary/sibling HEAD/files/index snapshots |
| Criterion idempotence | existing row equality and commit seam | Repeated bytes, HEAD, clean index remain identical |
| Checks inspect owner source | existing invariant executor | Owner-only tracked file absent from repository root |
| Refusals have no effects | canonical validator before execution | Root/foreign/missing-selector/topology controls and snapshots |
| Same-selector identity conflicts | canonical adoption | Wrong identity and stale-copy controls |
| Shared lock and concurrent splice | `locked_reread_splice_and_write` | Existing owning subsystem concurrency/timeout regressions |
| One ownership/writer authority | AST architectural gates | Named single-authority, self-mutation and matrix-write-seam gates |

## Approach tracer

Outside-in: real command RED on compatible base, separate failing-first commit,
then minimal typed carrier extension in the command and shared locked writer.
Existing source `.venv` uses pinned CPython 3.13.11 and the checkout source import;
`uv.lock` and dependency definitions remain unchanged. Final validation diagnostics
and receipts are external so recording a pass does not modify the frozen source.

## Tooling-friction tracer

Configured `core.hooksPath=.githooks` points to an absent directory in this
checkout. No hook is bypassed or configured; required publication checks are run
explicitly. Initial lint caught the missing typed negative-mode parameter before
qualification; the diagnostic run was retained, joined and corrected. A test
initially assumed explicit claims reject unrelated primary identities; live
canonical-minter evidence corrected the test to preserve explicit selection and
flagless conflict refusal, rather than changing ownership semantics.

`make test-fast` initially selected the repository's Python 3.11.15 pin and
replaced the inspected Python 3.13.11 environment. Both owned live gate groups
were explicitly terminated and joined (143), with their diagnostic logs retained;
neither qualifies validation. The environment was restored through
`uv sync --frozen --all-extras` with the existing 3.13.11 interpreter explicitly
selected. Subsequent uv commands pin `UV_PYTHON` to that interpreter. No source,
dependency lock or private consumer installation was changed. No cache clearing
or cache/config mutation was requested; exact cache-byte preservation is
unverified.
The pre-drift distribution inventory was not captured: exact package restoration
is unknown. uv reported 67 packages for the drifted 3.11 environment and 127
for the pinned all-extras 3.13 environment. Final gates compare the complete
interpreter/distribution inventory and lock/config fingerprints before and after
each sequential run; a mismatch invalidates qualification.

## Known Limitations

- Source validation is not consumer SDK installation, actual consumer acceptance,
  default-branch publication, or SDK release. Those need independent review and
  owner-managed integration after delivery.
- Owned lifecycle topologies remain the existing `single_branch` support set.
  Coordinated and lane callers without an owned claim keep their existing paths;
  this repair does not expand owned topology support.
- Negative-invariant command execution retains the existing configured-command
  authority and semantics; routing a command does not qualify its authored proof.
- Provider tokens and cost for this repair are unavailable.


## Documentation CI correction — 2026-10-10

### User Experience Findings

- **Observed:** the documentation job `114227612628` for
  https://github.com/crucible-energy/spec-kitty/pull/88 failed the two live
  structural-lint tests on source `c3d26bd566b429a469c9b4892531af094829586f`.
  This log lacked `doc_status`, lived outside the canonical point-in-time
  section, and introduced an unsanctioned `implementation-log/` section.
- **Observed:** the same two failures were reproduced locally before this
  correction. Original focused acceptance/ownership gates did not cover the
  documentation subsystem; that omitted gate allowed these defects through
  local qualification. Their passing evidence remains valid for its recorded
  scope and does not establish documentation or CI readiness.

- **Observed:** an additional exact-page metadata check rejected the first
  repository-relative audience reference. The canonical audience checker resolves
  references relative to the page directory, so the corrected metadata uses
  `../../context/audience/internal/maintainer.md`. The structural suite alone does
  not prove this audience-reference contract.

### Engineering Decisions

- Move this independently owned record to
  `docs/plans/engineering-notes/2026-10-10-59-owned-acceptance-verdict.md`.
  The policy's `plans/engineering-notes/` home is relative to the `docs/` root;
  a repository-root `plans/` directory would not satisfy that taxonomy.
- Preserve the historical body above and accepted source/receipt history.
  Add honest `doc_status: point_in_time`, a title, a description, and the
  existing maintainer audience catalog reference. No linter policy, allowlist,
  test, product code, or automated enforcement is changed.
- Run the owning documentation subsystem and its structural checks for this
  correction, plus the required increment gates in the pinned environment.
  Record the resulting proof externally after this document is frozen.

### Known Limitations

- The original accepted source commit and receipts remain historical evidence;
  their old log path is not the current canonical home.
- Local checks and publication do not prove the replacement GitHub job passed,
  that this PR merged, or that a consumer SDK was installed. Those require
  fresh owner-qualified evidence for the corrected source revision.

## CLI golden-contract correction — 2026-10-10

### User Experience Findings

- **Observed:** execution-context shard `114227615309` for
  https://github.com/crucible-energy/spec-kitty/pull/88 failed the exact
  acceptance-verdict flag-surface test and its removal control: the registered
  command exposed the intentionally implemented `--owned-checkout` option,
  while the expected flag mirror omitted it.
- **Observed:** both failures were reproduced locally on delivered revision
  `37c5247360d50b617d956e8e2baef1dde7ef3957` before editing the contract.
  The earlier local qualification omitted this full mission CLI golden module;
  the source/ownership checks and their review did not prove that golden
  contract was current. Their narrower evidence is preserved honestly.

### Engineering Decisions

- Add only `--owned-checkout` to the acceptance-verdict expected flag set.
  Its authority remains the implemented, ownership-validated command and
  canonical public help. This is a contract mirror amendment, not an expansion
  of runtime authority, topology support, or an execution allowlist.
- Preserve exact full-set equality and its missing/extra diagnostics. Keep the
  existing `--negative-invariant` removal control and parameterize it with the
  new `--owned-checkout` control. Each starts from the real introspected command,
  verifies the complete contract, and proves a removed flag is reported as
  missing and makes that exact equality fail. Remove obsolete flag-count wording.
- Run the entire registered mission CLI golden module, changed-log metadata and
  documentation checks, formatting/lint and the required pinned baseline.
  Product code, other expected flag sets, policy and prior receipts stay intact.

### Known Limitations

- The canceled CLI shards in the failed aggregate have no passing qualification;
  cancellation is not evidence of successful tests.
- Local correction gates do not prove replacement GitHub jobs passed or grant
  whole-PR merge, SDK release, consumer installation or Aletheia acceptance.
  Those require fresh evidence bound to the corrected published revision.

### Real-checker review correction

- **Observed:** root review found that the inherited removal control only
  computed copied set differences and asserted inequality. It never invoked the
  actual flag-surface checker with the missing option, so future weakening of
  that checker could pass the control despite breaking its intended guarantee.
- **Decision:** retain real-command introspection and its exact sanity check,
  then supply the captured surface minus each removed flag through the existing
  getter. Invoke the actual `test_command_exposes_exact_flag_surface` checker
  under `pytest.raises(AssertionError)` and assert its exact missing/extra
  diagnostics for both flags. No product code or policy changes are required.
- **Limitation:** the earlier golden/docs checks qualify only their weaker
  captured candidate. The already-started baseline was deliberately terminated
  and joined before the test/log amendment; its diagnostic output is retained
  and is not passing baseline evidence. Final proof binds the strengthened
  frozen candidate after review.
