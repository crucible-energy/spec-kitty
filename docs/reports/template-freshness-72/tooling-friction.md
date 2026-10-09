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

## Hosted readiness gates

PR 75's archive job compared its published patch target with organization main,
including old archive divergence outside the PR delta. The gate assumed a main
review boundary. [Issue 76](https://github.com/crucible-energy/spec-kitty/issues/76)
records the owning defect; no archive bytes or exemptions are repaired here.
A real Git regression through the existing byte-freeze entry point reproduces
that wrong boundary and pins strict non-main event correlation. Main authority
and its documented empty fork payload compatibility remain unchanged. Non-main
empty payloads and raw heads without target-base ancestry remain unsupported.

The execution-context shard also exposed stubs missing the existing optional
`owned` argument and a record-analysis flag pin missing `--owned-checkout`.
Both complete fixture files and owning CLI modules match exact published
baseline `e6c71493a`; the two unchanged entry points reproduced both failures.
[Issue 78](https://github.com/crucible-energy/spec-kitty/issues/78) records those
stale contracts before their correction. The stubs now assert ordinary placement
and the golden pin admits the already-existing option. These readiness changes
leave runtime implementation, packaging, CI workflows and the separately
qualified source-45a installed consumer unchanged. Source publication and owning
gates remain separate from release or production acceptance; actual incident
actor, model, tokens and cost remain unknown.

The expanded owning fast tier found one more baseline fixture: Rich wraps the
correct recovery recipe between `--to-branch` and its value when the isolated
xdist path is long. The fixture and rendering helper match exact `e6c71493a`.
[Issue 79](https://github.com/crucible-energy/spec-kitty/issues/79) records the
failure before correction. The one assertion now normalizes display whitespace
after ANSI removal, retaining its exact target-branch requirement. This verifies
recipe tokens; multiline command copyability remains a separate UX concern and
is not qualified by that assertion. No recovery recipe or runtime code changes.

## Webhook merge metadata timing

The source-8a archive job returned three refusals solely because optional webhook
merge metadata differed from the checked-out runner merge. The exact graph and
published target had already passed. The earlier equality requirement conflated
background PR mergeability metadata with the workflow's merge branch.
[Issue 76's updated RCA](https://github.com/crucible-energy/spec-kitty/issues/76#issuecomment-6079170114)
records this design mistake before correction. Real Git fixtures reproduce two
refusals using distinct merge SHAs with identical ordered parents and tree.
Optional merge metadata now receives syntax/type validation only. Runner SHA,
actual parent graph, exact raw head, published target, event-file and same-base
archive/exemption checks remain required. No retry, fetch, runtime or CI change
resolves this defect; the independently qualified source-45a runtime stays fixed.

Two inherited recovery fixture families replaced the gate repository with local
Git histories while retaining the runner's unrelated hosted PR event. Both
existing positive entry points reproduced the configured-remote refusal; their
fixture bytes match `e6c71493a`. The issue-76 follow-up records that interaction.
Those two files now explicitly clear only GitHub PR admission metadata per test.
They retain `CI`, including the unreachable-base refusal under literal `true`,
and all archive tamper, receipt, replay and guard self-mutation assertions.
Hosted target authority remains independently exercised in the owning gate.
This declares fixture context; it adds no runtime fallback or archive exemption.

The registry evidence gate also assumed organization `origin/main`, which lacks
its registry on this published patch lineage. [Issue 81](https://github.com/crucible-energy/spec-kitty/issues/81)
records the two actual CI failures. Real Git regressions reproduce wrong review
base selection and caller-checkout admission before correction. T015/T019 now
reuse the archive owner's validated base, with checkout binding and immutable
SHA reads. Local unit context is explicit; capture freshness/parity and actual
routing remain nonvacuous under controlled mutations.

The separately owned status-read corrections in source `07ed5e270` were reviewed
and focused-tested by their owner. Final combined source includes those runtime
changes; this fixture/gate increment does not qualify or rebuild the installed
source-45a consumer. Actual hosted source-695 archive success is root-reported;
actual CI of the final combined source remains required.
