---
title: 'Consumer asset isolation implementation findings'
description: 'Observed UX effects and execution constraints for issue 72.'
doc_status: draft
audience: docs/context/audience/internal/maintainer.md
type: reference
updated: '2026-10-09'
---

# Consumer asset isolation implementation findings

Audience: maintainers and the orchestrator qualifying the consumer.

- **UX:** refreshing analysis after each cross-version overwrite is ineffective;
  the next foreign startup can recreate the same custody loss. A stable private
  consumer lifetime is the deterministic remedy.
- **Observed startup limit:** `SPEC_KITTY_HOME` alone isolates templates/cache,
  while most generated agent commands and skills still select native user roots.
  An initial profile resolver attempt using only the private runtime home refused
  with `STARTUP_ASSET` on a shared agent command. Automatic effects before that
  refusal were not fully characterized. Further investigation used controlled
  pytest fixtures; no live consumer asset repair was attempted.
- **Early-admission defect:** validating only at ordinary runtime bootstrap was
  too late: malformed configuration had already created an auth session lock.
  The canonical state-root boundary now admits scope before that access.
- **Test harness:** repository fixtures own temporary HOME isolation. An early
  resolver attempt used subprocess-local HOME/XDG isolation before the root
  instructed fixture-only execution; retained evidence preserves that attempt.
  The shipped workflow and all subsequent task commands do not repurpose HOME
  or CODEX_HOME. Standard test-venv construction and local artifacts remain
  private to the repair checkout or approved evidence directory.
- **Evidence discipline:** the external installed-version collision is retained
  as a controlled observation. The durable regression uses the retained legacy
  writer, avoiding a machine-specific installed-package dependency. No repeated
  green baseline, whole-repository heavy suite, CI or automation was added.

## Required-gate fixture remediation

The owning fast tier first reported four failures. The two unsupported-host
installer simulations were independently reproduced on exact baseline source;
[issue 73](https://github.com/crucible-energy/spec-kitty/issues/73) records the
capability-metadata mismatch. The fixture now removes chmod/utime from the
advertised supported set while retaining the rejecting behavior spies.

The historical advance-guard case passed in an independent reference but failed
in the linked repair checkout: its anchored read correctly selected the real
repository root, whose old mission task directory was absent.
[Issue 74](https://github.com/crucible-energy/spec-kitty/issues/74) records that
checkout-dependent assumption. A real temporary single-branch Git owner now
provides a task and committed status, with explicit placement and blocked-state
assertions. Production no-follow, placement and missing-task guards stay intact.
Both affected complete test files pass: 98 tests. The private baseline reference
was retired after exact source, digest and result preservation.

The fourth case requires a clean committed source checkout; it remains a required
post-commit gate, without an exclusion or bypass.

## Documentation structural gate and scoped consumer acceptance

PR 75's docs shard found missing `doc_status` on the four new documents and
four inherited owned-analysis reports. The two existing live structural checks
reproduced the eight violations on source `45a4afa0a`; exact baseline `e6c71493a`
already lacked the four owned-analysis status fields.
[Issue 77](https://github.com/crucible-energy/spec-kitty/issues/77) records that
inherited metadata gap. All eight pages now carry `draft`, a canonical maintainer
audience reference, and a current metadata review date. These metadata changes
make no completion or default-release claim.

**Root-reported consumer acceptance:** the separately installed, noneditable
source-45a wheel and its 2149-file installation manifest were verified. Scoped
current analysis returned exit 0, `ready`, `stale: false`, committing
`a19d8346e41eb7bad163c3286be66b9f6849293c`. The same configuration's canonical
owned `implement WP01` returned exit 0 and claimed focused `fix-cycle1`.
This qualifies that source candidate's consumer window. It establishes no
native/default installed CLI or production qualification. The docs-only
coherence increment does not rebuild or repoint that qualified runtime.

The metadata correction runs the complete structural-lint test file and normal
docs lint, rather than treating spelling/changelog lint as structural proof.
Implementation, packaging and archive bytes remain unchanged in this increment.
