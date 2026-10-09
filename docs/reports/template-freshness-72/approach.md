---
title: 'Template freshness: controlled reproduction'
description: 'Separate the observed incident from the reproduced shared-runtime collision.'
type: explanation
updated: '2026-10-09'
---

# Template freshness: controlled reproduction

Audience: the source reviewer and the operator qualifying the blocked consumer.
Owner: Implementer Ivan on `issue-72-template-freshness`.
Baseline: `e6c71493a38851737c9e131a158f535430dcef4d`, the published
`fix/owned-analysis-implementation` candidate, rather than organization `main`.
Tracker: [crucible-energy/spec-kitty issue 72](https://github.com/crucible-energy/spec-kitty/issues/72).

## Observed incident

A Retrust owned-checkout report committed successfully, then the same candidate
executable refused implementation with `stale_analysis_report`, naming only
`template-selection:spec` and `template-selection:plan`. Two subsequent material
collections agreed with each other. Full before/after template identities were
not retained. The original intervening actor remains **UNKNOWN**.

Later retained observations reconstruct the reported current fingerprints and
match the candidate's bundled template bytes. A subsequent read-only inspection
found the shared runtime stamped `3.2.7`, with spec/plan bytes matching the
separately installed 3.2.7 package. That observation establishes cross-version
shared state, without identifying who invoked that writer during the incident.

## Reproduced mechanism

The pre-existing cold root-CLI acceptance test records and admits successfully
with one candidate runtime. A Python audit trace confirmed that the following
implementation command makes no selected-template writes and retains exact leaf
inode, mode, size, mtime and ctime.

A controlled private fixture then ran:

1. Candidate root CLI records current analysis and commits its report.
2. The actual separately installed 3.2.7 root CLI starts using that same fixture
   asset directory. Its legacy `ensure_runtime` observes a version mismatch and
   calls `populate_from_package` plus `merge_package_assets`; the latter replaces
   managed directories with `rmtree` and `copytree`.
3. Candidate implementation restores its canonical template bytes, then refuses
   the report with the same stale spec/plan selection result.

This proves a sufficient causal mechanism. It does not prove the original
incident actor. The freshness guard detects real changes to selected custody;
removing inode/timestamp checks would weaken its contract.

## Repair contract

The approved repair explicitly scopes every generated consumer asset into one
private lifetime directory. Before the source change, real root-CLI acceptance
reported shared native command/skill effects and accepted malformed scope
settings. The separate failing-contract commit is
`2354c8cb35683d98dbdac9f375bfb6b1860b2de2`.

The self-contained regression retains the same legacy directory writer behavior
without requiring a particular globally installed package. It verifies unchanged
shared user assets during scoped startup, stable private template/command/skill
custody across the independent shared writer, successful record-to-implement,
and preserved primary-checkout sentinels. Genuine selected-content, equal-byte
replacement, root retarget and symlink controls continue to refuse.

Detailed local command output and audit traces are retained by the owning
orchestrator under its approved `spec-freshness72` evidence directory. Validation
and installed-consumer qualification are separate gates; the original consumer
is not repointed by this source work.

## Issue disposition

| Issue | Source disposition | Remaining delivery boundary |
|---|---|---|
| [72](https://github.com/crucible-energy/spec-kitty/issues/72) | Explicit consumer asset scope; fresh report survives an independent shared-root writer | Root owns installed-consumer cutover and the actual blocked command; original actor unknown |
| [73](https://github.com/crucible-energy/spec-kitty/issues/73) | Unsupported-host fixture now declares unsupported chmod/utime capabilities | Published source review and integration |
| [74](https://github.com/crucible-energy/spec-kitty/issues/74) | Historical checkout assumption replaced with a real, isolated single-branch owner | Published source review and integration |

## Validation ledger

Commands ran from the repair checkout, using its frozen `.venv`, with complete
outputs in the orchestrator's approved evidence directory. Counts are per run;
there is no aggregate claim because some focused cases appear in more than one
required gate.

| Command or surface | Observed result |
|---|---|
| New consumer scope unit and root-CLI files | 12 passed; malformed settings, retained-scope drift and four selected-custody negatives included |
| Actual installed 3.2.7 writer injected into the scoped root-CLI positive | 1 passed; private assets and the shared post-writer snapshot remained unchanged during candidate implementation |
| `PYTEST_XDIST_AUTO_NUM_WORKERS=4 make test-fast` | 2449 passed, 5 skipped; baseline source behavior qualified |
| Owning fast tier: kernel, runtime and CLI skills | Initially 4 failed, 2109 passed, 1 skipped, 1 xfailed; all findings explicitly reproduced or attributed before remediation |
| Full installer and advance-guard test files after fixture correction | 98 passed |
| Analysis inputs, template provenance, bootstrap/home plus named architectural gates below | 333 passed, 1 skipped |
| `mypy --strict --follow-imports=silent` on all six touched source modules | No issues; dependency internals are outside this scoped strict result |
| `make format-check`, `make docs-lint`, changed-file Ruff and `git diff --check` | Passed; 19 pre-existing advisory changelog-length warnings |

The focused architecture invocation names:
`test_bootstrap_import_purity.py`, `test_layer_rules.py`,
`test_no_dead_symbols.py`, `test_no_retired_subsystems.py`,
`test_no_legacy_terminology.py` and `test_spec_kitty_home_pin_census.py`.
It runs no complete architecture, e2e, performance or heavy suite.

The owning fast tier's clean-source upgrade-preview case remains the mandatory
post-commit gate. Its initial dirty-source refusal is retained, without a test
exclusion or readiness claim. The final owning-tier outcome is recorded after
that committed-source execution.
