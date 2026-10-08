---
title: 'Owned analysis and implementation: execution evidence'
description: 'Executed command outcomes and exact edited surfaces for the bounded SDK dependency fix in issue 5882, including red-first and harness limits.'
type: reference
updated: '2026-10-08'
---

# Execution Evidence — #5882

Audience: the orchestrator and independent SDK source reviewer. Counts below are
test outcomes, not delivery or performance metrics. No aggregate count is used:
some targeted files were re-run after changes or harness interruptions.

## Reproduction environment

The initial implementation shell commands ran in
`/Users/sam/git/crucible/_worktrees/spec-kitty-owned-checkout-runtime`.
Initial status was clean; branch and HEAD were respectively
`fix/owned-analysis-implementation` and
`1af6a711074e45359ddfe568dd71f057286a13ee`.

The provisioned-source pytest launcher replaces the suite's installer and
narrows its collection-time assertion scan to named files. It changes no
product ownership/path resolver or governance guard. SDK HOME fixtures remain
active. The launcher's complete source is retained in the approved temp parent.

The following shorthand expands to the exact test-command prefix used after
the two collection diagnostics (the first attempt omitted `-u`):

```sh
PYTHONPATH="$PWD/src" TMPDIR=/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode \
  .venv/bin/python -u \
  /var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/owned-analysis-pytest.py
```

The launcher invokes pytest with `-p no:cacheprovider -o addopts=` before the
arguments in the ledger. `TMPDIR` and bytecode suppression are set before suite
imports. There is no installation, source-checkout cleanup or bypass flag.

## Test argument aliases

Each alias denotes one literal path; arguments retain the listed order.

| Alias | Path |
|---|---|
| OWN | `tests/integration/test_owned_analysis_implementation_cli.py` |
| LIFE | `tests/integration/test_owned_lifecycle_acceptance_cli.py` |
| AR | `tests/specify_cli/test_analysis_report.py` |
| TX | `tests/specify_cli/cli/commands/agent/test_analysis_report_transaction.py` |
| CLAIM | `tests/specify_cli/cli/commands/agent/test_implement_runtime_frontmatter_claim.py` |
| STATUS | `tests/status/test_work_package_lifecycle.py` |
| SCOPE | `tests/charter/test_charter_scope.py` |
| RECORD | `tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py` |
| PLACE | `tests/specify_cli/cli/commands/agent/test_record_analysis_placement.py` |
| COORD | `tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py` |
| WP05 | `tests/specify_cli/cli/commands/agent/test_wp05_mission_coordination_routing.py` |
| AUTHORITY | `tests/architectural/test_owned_checkout_single_authority.py` |
| WRITERS | `tests/status/test_concurrent_mission_writers.py` |
| LOCKKEYS | `tests/status/test_status_lock_keys.py` |
| CHECKOUTLOCK | `tests/status/test_checkout_claim_lock.py` |
| OCCUPANCY | `tests/lanes/test_checkout_occupancy.py` |
| WRITEGATE | `tests/architectural/test_mission_write_discipline.py` |
| CLAIMSCOPE | `tests/cli/commands/test_implement_claim_scope_5673.py` |
| WORKFLOW | `tests/specify_cli/cli/commands/agent/test_workflow.py` |
| WRAPPER | `tests/specify_cli/cli/commands/agent/test_wrapper_delegation.py` |
| CORES | `tests/specify_cli/cli/commands/agent/test_workflow_cores.py` |
| CYCLE | `tests/review/test_cycle.py` |
| CYCLEWRITE | `tests/review/test_cycle_write_dir.py` |
| POINTER | `tests/agent/test_workflow_review_cycle_pointer.py` |
| FIXCOORD | `tests/specify_cli/cli/commands/agent/test_review_reject_fix_mode_coord.py` |
| TERMS | `tests/architectural/test_no_legacy_terminology.py` |

## Pytest execution ledger

| Arguments after the prefix | Observed result / disposition |
|---|---|
| `OWN -q` (initial launcher) | Shell timeout at 120s, no test summary. Collection diagnostic, not a test verdict. |
| `OWN -x -vv -o faulthandler_timeout=45` | Shell timeout at 90s; traceback located whole-tree wall-clock AST scan during collection. |
| `OWN -x -q` (scan bounded, unchanged base) | **1 failed**: real CLI exit 2, `No such option: --owned-checkout`. Red-first baseline at the pinned base. |
| `OWN -x -q` (first routing edit) | **1 failed**: implementation used nonexistent `OwnedCheckout.target_branch`; corrected to `write_branch`. |
| `OWN -x -q` (claim routing edit) | **1 failed**: existing owned status transaction had already committed the pair; follow-up unchanged outcome incorrectly refused. |
| `OWN -q` | **3 failed, 12 passed**: unchanged-claim qualification still too narrow; missing WP definition correctly refused earlier than the analysis gate, requiring a precise test assertion. |
| `OWN -k reuses_exact -q` | **2 failed, 13 deselected**: test expected full prompt text on the abbreviated stdout surface; corrected to read the real prompt artifact. |
| `AR TX CLAIM -q` (120s bound) | Shell timeout before summary. No completed pass count claimed. |
| `OWN LIFE AR TX CLAIM -q` (600s bound) | Shell timeout before summary. No completed pass count claimed. |
| `OWN -q` | **28 passed**. Initial owner/report/guard acceptance surface. |
| `AR TX CLAIM -q` | **68 passed**. Ordinary V1 behavior, transaction guards and claim/frontmatter controls. |
| `OWN -k occupancy -q` | **1 failed, 28 deselected**: second WP was incorrectly admitted in the occupied owner checkout. |
| `STATUS SCOPE RECORD PLACE COORD WP05 AUTHORITY -q` | **1 failed, 108 passed**: an existing ordinary-route test fake did not accept the new optional ownership argument. Updated that fake to accept it and assert `owned is None`; no owner-path test was mocked. |
| `OWN -k 'occupancy or resume or claim_commit_failure or stale_primary or partial_staging' -q` | **2 failed, 5 passed, 28 deselected**: owner workspace had no lane ID, so occupancy and dirt guards were still inactive. Fixed the shared predicate using checkout-root semantics. |
| `OWN -k 'occupancy or partial_staging' -q` | **3 passed, 32 deselected** after the guard fix. |
| `OWN -k profile_access -q` | **1 failed, 35 deselected**: CLI succeeded; test passed an EventStream directly to a list-based reducer. Corrected test to pass transitions and annotations separately. |
| `WRITERS LOCKKEYS CHECKOUTLOCK OCCUPANCY WRITEGATE CLAIMSCOPE -q` | Summary: **131 passed**. Shell timed out at 600s after the summary; command exit was not qualified. No product-test failure was printed. |
| `OWN -q` | **37 passed**. Owner scope, resume, rollback, profile access and lock-observer tests included. |
| `LIFE WORKFLOW WRAPPER COORD -q` | **128 passed**. Includes the corrected ordinary-route fake and owned REVIEW/invalid-claim controls. |
| `OWN -k missing_canonical_feedback -q` | **1 failed, 37 deselected**: stale-primary lookup hid the owner's missing canonical feedback and implementation proceeded. Red-first feedback reproduction. |
| `OWN -k canonical_feedback -q` | **2 passed, 37 deselected**: missing owner feedback refuses; valid owner feedback produces fix mode with a stale primary present. |
| `CORES CYCLE CYCLEWRITE POINTER FIXCOORD -q` | **104 passed, 1 skipped**. Skip reason was not printed by that invocation; no coverage of the skipped case is claimed. |
| `OWN AUTHORITY WRITEGATE TERMS -q -rs` | **191 passed**, completed command. Includes 39 owner acceptance cases and the named architectural gates. |
| `OWN -k 'write_intent or sparse_preflight or requires_owner_charter' -q` | **3 passed, 39 deselected**. Real owner sparse configuration, caller-checkout refusal and initial missing-charter refusal. |
| `OWN -k 'reuses_exact or stale_primary_mission' -q` | **4 passed, 38 deselected**. Revalidated both recording modes after additive stale-copy output was wired. |

No unexplained unchanged-base product failure was accepted as baseline context.
Expected red-first cases, implementation defects and test/harness-only failures
are separated above. These are not retry-to-green repetitions: changes or
identified command-budget/collection blockers preceded subsequent runs.

## Other executed commands

- `git status --short && git branch --show-current && git rev-parse HEAD && git worktree list --porcelain`: clean authorized lane at the requested base; four existing registered SDK checkouts observed. No SDK lane was created or removed.
- Environment probes used `PYTHONPATH="$PWD/src" <python> -c` to print `sys.version`, `specify_cli.__file__`, pytest and events/tracker package versions. The initial primary interpreter reported 3.11.3 / 9.0.3 / 6.1.0 / 0.4.3. The corrected lane interpreter reported 3.11.15 / 9.0.3 / 10.4.0 / 0.5.2 and this branch's `src/specify_cli/__init__.py`.
- `PYTHONPATH="$PWD/src" .venv/bin/python -m specify_cli profiles show python-pedro --json`: success; full resolved initialization, role, boundaries and directive/tactic references loaded.
- `PYTHONPATH="$PWD/src" .venv/bin/python -m specify_cli agent profile --help` and `... charter context --help`: success; confirmed the public profile and read-only context surfaces.
- `PYTHONPATH="$PWD/src" .venv/bin/python -m specify_cli charter context --action implement --mission-type software-dev --no-mark-loaded`: success with legacy-governance warning and primary-folded context; no loaded-state write requested.
- `ps -axo pid,ppid,etime,command`: collection-timeout diagnostic; broad output was truncated. The useful blocker evidence came from the subsequent faulthandler traceback, not an inferred process state.
- `PYTHONPATH="$PWD/src" .venv/bin/python -c 'from pathlib import Path; lines=Path("AGENTS.md").read_text().splitlines(); print("\n\n".join(f"{i}: {line}" for i,line in enumerate(lines,1) if len(line)>2000))'`: completed the three reader-truncated AGENTS lines.
- `.venv/bin/python -m ruff check <then-edited source files>`: `No module named ruff`; used the existing system Ruff thereafter, without installation.
- `command -v ruff; command -v mypy`: `/opt/homebrew/bin/ruff`; no mypy executable.
- `ruff check` over the then-edited source paths: first five findings (SIM102, E501, F841); then one C901 finding (freshness function reached 16). Fixed locally, including the input-error helper extraction.
- `ruff check` over source plus the two then-edited acceptance files: four test E501 findings; its chained pytest command did **not** execute. Fixed formatting.
- `ruff format --force-exclude <edited Python paths> && ruff check <same paths>`: successive outputs were `3 files reformatted, 7 files left unchanged` with lint passing; later the same formatter count with one E501 in a formatter-excluded workflow executor; then `1 file reformatted, 10 files left unchanged` with lint passing. The excluded executor line was fixed manually. No exclusion or suppression was added.
- The last four-case owner run chained `ruff check` over all 13 edited source modules and all three edited test files: **All checks passed**.
- `/Users/sam/git/crucible/spec-kitty/.venv/bin/python -m mypy --version` and `.venv/bin/python -m mypy --version`: both `No module named mypy`.
- `PYTHONPATH="$PWD/src" .venv/bin/python -m mypy --strict --no-incremental --cache-dir=/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/mypy-owned-analysis-5882 <all 13 edited source modules>`: blocked before checking files, `No module named mypy`. No strict pass claimed.
- Repeated `git diff --stat`, `git diff --check`, `git status --short`, and exact path-scoped `git diff -- <edited source paths>` inspections were used for self-review. No source staging, commit, push, PR, release or activation command was run.
- Final `ruff format --force-exclude <all edited Python paths> && ruff check <same paths> && ruff format --check --force-exclude <same paths> && git diff --check`: `11 files left unchanged`, `All checks passed`, `11 files already formatted`; whitespace check passed. Existing formatter exclusions account for the remaining explicitly listed paths; no exclusion was added.
- Final `git status --short && git branch --show-current && git rev-parse HEAD && git worktree list --porcelain && git diff --stat && date -u '+%Y-%m-%dT%H:%M:%SZ'`: audited at `2026-10-08T10:55:10Z`; source branch/HEAD remained the authorized branch and pinned base, with only the intended source/tests/docs dirty. The registry now contained an additional external checkout, `/Users/sam/Documents/Codex/2026-10-08/referenced-chatgpt-conversation-this-is-an/work/spec-kitty-zero-wp-accept`, branch `fix/zero-wp-documentation-accept`, HEAD `4196af70fe69d558c729d2e6265be921999b5761`. It appeared concurrently, was not created by this task, and remains protected for its owning workstream. The other initially observed SDK checkout HEADs remained unchanged. No capacity cleanup was attempted.

## Strict typing continuation: unchanged-base attribution

The operator provisioned mypy and declared stubs under
`/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/sdk-owned-analysis-mypy`.
This continuation used that ephemeral `uv --no-project` environment. No global
installation, SDK `.venv` change, SDK checkout/branch creation or worktree reset
was performed. Python Pedro remains the loaded implementation profile.

### Snapshot command

From the authorized SDK lane, `ls` first confirmed the approved parent contained
`cache/` and `type-cache/`. The following command completed with exit 0:

```sh
mkdir /var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/sdk-owned-analysis-mypy/base-1af6a711-src && set -o pipefail && git archive --format=tar 1af6a711074e45359ddfe568dd71f057286a13ee src pyproject.toml | tar -x -C /var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/sdk-owned-analysis-mypy/base-1af6a711-src
```

The snapshot is an extraction of pinned source/configuration, not a Git checkout.
It was not modified during qualification.

### Exact strict command and both results

The **same complete command** below was executed once in each working directory:

1. Candidate: `/Users/sam/git/crucible/_worktrees/spec-kitty-owned-checkout-runtime`.
2. Base: `/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/sdk-owned-analysis-mypy/base-1af6a711-src`.

```sh
env UV_CACHE_DIR=/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/sdk-owned-analysis-mypy/cache \
uv run --no-project --with mypy --with types-jsonschema --with types-psutil --with types-PyYAML --with types-requests --with types-toml \
--python /Users/sam/git/crucible/_worktrees/spec-kitty-owned-checkout-runtime/.venv/bin/python \
mypy --strict --no-incremental \
--python-executable /Users/sam/git/crucible/_worktrees/spec-kitty-owned-checkout-runtime/.venv/bin/python \
--cache-dir=/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/sdk-owned-analysis-mypy/type-cache \
src/charter/activation/context.py \
src/specify_cli/analysis_report.py \
src/specify_cli/cli/commands/agent/mission_record_analysis.py \
src/specify_cli/cli/commands/agent/workflow.py \
src/specify_cli/cli/commands/agent/workflow_executor.py \
src/specify_cli/cli/commands/agent/workflow_cores.py \
src/specify_cli/coordination/status_transition.py \
src/specify_cli/git/report_transaction.py \
src/specify_cli/lanes/checkout_occupancy.py \
src/specify_cli/lanes/implement_support.py \
src/specify_cli/review/cycle.py \
src/specify_cli/status/emit.py \
src/specify_cli/status/work_package_lifecycle.py
```

| Tree | Exact summary | Command exit |
|---|---|---|
| Candidate | `Found 13 errors in 4 files (checked 13 source files)` | 1 |
| Pinned unchanged base | `Found 26 errors in 6 files (checked 13 source files)` | 1 |

Verbatim terminal diagnostics were retained as `current-strict.txt` and
`base-strict.txt` in the approved `sdk-owned-analysis-mypy` artifact directory.
Attribution used `.venv/bin/python <artifact-dir>/attribute-strict.py` from the
SDK lane. The comparator maps current lines to byte-identical source lines in
the pinned snapshot, and requires an exact file/message/error-code match at
that base line. It completed with exit 0: **13 matched unchanged-base findings,
zero introduced findings, 13 base-only findings**. Counts alone were not used
to attribute errors.

### Per-finding mapping

Paths below are relative to `src/`. Every mapped statement is unchanged.

| File | Current line | Base line | Diagnostic |
|---|---:|---:|---|
| `charter/activation/context.py` | 283 | 280 | `no-any-return`: `str`; `missing_pack_diagnostic + "\n\n" + text` |
| Same | 394 | 391 | `no-any-return`: `str`; section include renderer |
| Same | 400 | 397 | `no-any-return`: `str`; generic artifact include renderer |
| Same | 409 | 406 | `no-any-return`: `str`; template include renderer |
| Same | 443 | 440 | `no-any-return`: `str`; agent-profile include renderer |
| Same | 463 | 460 | `no-any-return`: `str`; `return result` |
| `specify_cli/git/report_transaction.py` | 144 | 144 | `comparison-overlap`: `tuple[IndexEntry, ...]` compared with declared `tuple[bytes, ...]` |
| Same | 302 | 297 | `arg-type`: `_guard_unchanged_inputs(index=...)` receives `tuple[IndexEntry, ...]`, annotation expects `tuple[bytes, ...]` |
| `specify_cli/coordination/status_transition.py` | 197 | 197 | `no-any-return`: `str`; coordination-directory name seam |
| Same | 225 | 225 | `no-any-return`: `bool`; branch-existence seam |
| Same | 825 | 825 | `no-any-return`: `Path`; `resolved.primary_anchor` |
| `specify_cli/status/work_package_lifecycle.py` | 113 | 112 | `no-any-return`: `Path`; status-lock root seam |
| Same | 206 | 203 | `no-any-return`: `bool`; implementer-of-record predicate |

The additional base-only diagnostics are in **untouched** runtime modules:

- `runtime/next/_internal_runtime/engine.py`: lines 241, 465, 478, 508, 524,
  876 each lack both `mission_id` and `mission_slug` in their payload call
  (`call-arg`; twelve errors).
- `runtime/next/prompt_builder.py`: line 512 returns Any as `str`
  (`no-any-return`; one error).

Their absence from the candidate output is not claimed as a repair, nor is
26 minus 13 presented as fixed diagnostics. **No production source or tests were
changed in this continuation**; all reported candidate errors predate the fix.
No ignore, suppression, configuration quarantine or checker flag was changed.
Regression reruns were unwarranted without implementation edits; the prior
targeted functional evidence remains recorded above.

### Charter-required public baseline report

[Issue #5917](https://github.com/spec-kitty/spec-kitty/issues/5917) records the
red base, exact reproduction and findings. Owner named in its body: Sam
(`samuelgoff`); next action: independently triage/repair the baseline in its own
bounded workstream. It was opened before accepting the findings as baseline.

Executed GitHub commands/results:

- `gh issue view 5882 --repo spec-kitty/spec-kitty --json number,title,assignees,state,url`:
  issue open, assignee list empty; read-only contextual check.
- `gh api user --jq .login`: `samuelgoff`.
- `gh issue create --repo spec-kitty/spec-kitty --title "Strict mypy baseline is red at 1af6a711 (26 diagnostics; 13 shared with #5882)" --assignee samuelgoff --body-file <artifact-dir>/baseline-issue.md`:
  returned a GraphQL `ReplaceActorsForAssignable` permission error after
  creating #5917. No duplicate create was attempted.
- `gh issue list --repo spec-kitty/spec-kitty --state all --search 'in:title "Strict mypy baseline" author:samuelgoff' --limit 5 --json number,title,url,assignees`:
  confirmed #5917 exists, unassigned.
- `gh issue view 5917 --repo spec-kitty/spec-kitty --json number,title,state,assignees,url,body`:
  confirmed open issue and full submitted reproduction body; assignee remains
  empty. A repository maintainer with assignment permission must add Sam.

Other continuation commands: initial `git status --short && git branch
--show-current && git rev-parse HEAD && git diff --stat && command -v uv`
confirmed the unchanged branch/base and existing candidate edits; `git diff --`
the four diagnosed source modules and `git ls-files '*mypy*' '*py.typed'
'pyproject.toml' 'setup.cfg' 'mypy.ini' '.mypy.ini'` inspected diagnostic
correspondence and tracked checker configuration. No process-argument dump was
performed.

Final continuation audit: `git diff --check && git status --short && git branch
--show-current && git rev-parse HEAD && date -u '+%Y-%m-%dT%H:%M:%SZ'` completed
with exit 0 at `2026-10-08T11:34:55Z`. Branch and HEAD remain
`fix/owned-analysis-implementation` / `1af6a711074e45359ddfe568dd71f057286a13ee`.
Only the three existing evidence/design/tooling documents were updated in this
continuation; production source and tests retain the prior candidate changes.

## Independent-review B1 closeout and concurrency exit qualification

The reviewer rejected the candidate with P1 blocker B1: the owned freshness
reader only checked transaction/manifest fields when present. A canonical
wrapper or stripped failed wrapper could therefore select legacy-only hashes
and admit implementation. The fix is confined to the owned read contract in
`analysis_report.py`; the renderer remains usable without qualification fields,
ordinary V1 optional behavior is preserved, and verdict policy is unchanged.

### Failed-before / passed-after CLI evidence

Using the existing source/HOME-isolated pytest prefix documented above:

| Exact arguments | Outcome |
|---|---|
| `OWN -k b1 -q` before production edits | **3 failed, 42 deselected**. All three real CLI calls returned 0 and actually claimed WP01 in their isolated sandbox, contrary to the refusal assertion. |
| `ruff check src/specify_cli/analysis_report.py tests/integration/test_owned_analysis_implementation_cli.py && <pytest-prefix> OWN -k b1 -q` after read-side enforcement | Lint passed; **3 passed, 42 deselected**. |
| `ruff format --force-exclude src/specify_cli/analysis_report.py tests/integration/test_owned_analysis_implementation_cli.py && ruff check <same two paths> && <pytest-prefix> OWN -k b1 -q` after adding independent manifest controls | Two files formatted; lint passed; **9 passed, 42 deselected**. |

The three reproductions are (1) tokenless owner wrapper emitted through the
actual canonical writer; (2) that wrapper followed by a committed substantive WP
change; (3) an actual failed report transaction whose token and manifest-version
fields were stripped and whose wrapper was subsequently committed. All now
refuse at `analysis_report_required`, with unchanged owner HEAD, event/status
bytes and primary HEAD/index/staged/unstaged/untracked sentinels.

Six additional cases deliberately make the local receipt's byte/commit checks
pass against a real sandbox commit, then exercise manifest validation
independently: absent version, unsupported version, boolean version, missing WP
entry, missing hash field on an absent-input sentinel, and incorrect input path.
No owning source path or carrier reader is mocked.

### Completed whole-process exits

Two independent, non-overlapping file sets ran through the approved-temp driver:

```sh
.venv/bin/python /var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/owned-analysis-bounded-check.py b1-concurrency tests/status/test_concurrent_mission_writers.py tests/status/test_status_lock_keys.py tests/status/test_checkout_claim_lock.py tests/lanes/test_checkout_occupancy.py tests/architectural/test_mission_write_discipline.py tests/cli/commands/test_implement_claim_scope_5673.py -q -rs
.venv/bin/python /var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/owned-analysis-bounded-check.py b1-freshness tests/integration/test_owned_analysis_implementation_cli.py tests/specify_cli/test_analysis_report.py tests/specify_cli/cli/commands/agent/test_analysis_report_transaction.py -q -rs
```

The driver runs `.venv/bin/python -u <approved-temp>/owned-analysis-exit-pytest.py`
with the literal file arguments above, source `PYTHONPATH`, approved `TMPDIR`,
cacheprovider disabled and the same suite installer/collection adaptation as
before. It records pytest main return and normal Python shutdown, then waits
for the actual child exit. Its outer bound is 1800 seconds, with TERM/KILL only
on expiration and timeout reported as exit 124, never exit 0. The SDK's normal
240-second per-test limits are unchanged. No process arguments were dumped.

| Run | Summary | Pytest main / real child exit | Driver timeout |
|---|---|---|---|
| Freshness, including all 51 owner cases and ordinary freshness/transaction cases | **110 passed** in 562.08s | **0 / 0** | false |
| Same six touched concurrency/lock/occupancy/scope gates as the previously interrupted command | **131 passed** in 458.78s | **0 / 0** | false |

The concurrency child ran from `2026-10-08T12:00:36.930302+00:00` through
`2026-10-08T12:08:43.439001+00:00`; freshness ran from
`2026-10-08T12:00:36.929181+00:00` through
`2026-10-08T12:10:05.641506+00:00`. Both logs end with
`PYTEST_MAIN_RETURN_CODE=0` and `PYTHON_ATEXIT_ENTER`. These are new completed
command qualifications, not a reinterpretation of the earlier shell timeout.
The exact earlier shutdown cause remains unknown; no deadlock or source fix is
inferred from that timeout. There was no failing test retried to obtain green.

Logs and actual exit JSON are retained in the approved temp parent as:
`b1-concurrency-exit.log`, `b1-concurrency-exit.json`,
`b1-freshness-exit.log`, `b1-freshness-exit.json`. Both driver scripts are retained
there as well.

### Strict comparison after B1 edits

The exact 13-file ephemeral uv strict command in the previous section was run
against the B1 candidate. It first reported **14 errors in 5 files**: the 13
existing base findings plus an introduced `analysis_report.py:621`
`no-any-return` at the extracted material collector's return. The proper seam
fix was an explicit `dict[str, dict[str, str | None]]` local annotation matching
the collector's existing declared return type; no cast, ignore, suppression or
configuration change was added.

The identical full strict command was then run again against the corrected
candidate and the unchanged archive, from their respective directories:

- Candidate: **13 errors in 4 files**, command exit 1; no analysis-report error.
- Pinned base: **26 errors in 6 files**, command exit 1, unchanged baseline.
- Existing unchanged-line comparator: **13 matched base findings, zero
  introduced findings, 13 base-only findings**, comparison exit 0. The final
  diagnostic outputs are identical to the retained `current-strict.txt` and
  `base-strict.txt`; the per-finding mapping above remains valid.

This is differential strict qualification, not an absolute strict pass.
Baseline #5917 remains honestly red and outside the bounded repair.

Final narrow `ruff check` and `ruff format --check --force-exclude` on the two
edited Python files passed (`2 files already formatted`); `git diff --check`
passed. Self-review confirmed mandatory read-side transaction/receipt checks,
mandatory versioned complete manifest on owned reads, optional ordinary V1
behavior, unchanged verdict policy and refusal before claim. Adoption still
requires the independent reviewer to re-review this corrected candidate.

B1 final audit: `git diff --check && git branch --show-current && git rev-parse
HEAD && git status --short && date -u '+%Y-%m-%dT%H:%M:%SZ'` completed with exit 0
at `2026-10-08T12:19:33Z`. The authorized branch/base are unchanged. B1 source
edits are confined to `src/specify_cli/analysis_report.py` and
`tests/integration/test_owned_analysis_implementation_cli.py`, with the four
existing approach/design/tooling/evidence tracers updated. No source adoption,
commit, push, PR, installation or new SDK checkout/branch was performed.

## Tracked canonical-alias compatibility increment

The operator reported actual native refusal before write, `Analysis authority
contains a symlink`, for the documented tracked alias `zig/docs -> ../docs`.
The clean authorized SDK lane was verified at delivered commit
`e86a792e5338d0b344456f1e1d9e5cfea2259afb`, branch unchanged. The historical pinned
base remains `1af6a711074e45359ddfe568dd71f057286a13ee`. This increment edits only
`analysis_inputs.py`, adds `test_owned_analysis_alias_cli.py`, and updates the
existing approach/design/evidence tracers; it creates no SDK branch/checkout.

The fixture uses a real Git-committed `zig/docs` symlink with mode `120000` and
exact blob `a9594bfe4ab69aca32d7c51b17985ad9ee89e563`. Its canonical target is
independently selected in the real fixture charter. No source authority/path is
monkeypatched. The dirty primary retains raw index/staging, HEAD and sentinels.

| Executed command arguments after the existing source pytest prefix | Result |
|---|---|
| `tests/integration/test_owned_analysis_alias_cli.py -k records_and_qualifies -q` before code edits | **2 failed, 11 deselected**: both default and report-only recording returned `failed_before_write` with the exact symlink refusal. |
| Initial chained `ruff check src/specify_cli/analysis_inputs.py tests/integration/test_owned_analysis_alias_cli.py && <pytest-prefix> ... -q` | Ruff flagged the imported pytest fixture (F401/F811); pytest did not run. Fixed with explicit fixture re-export, without suppression. |
| Same lint and `tests/integration/test_owned_analysis_alias_cli.py -q` after alias closure | Lint passed; **13 passed**. |
| `ruff format --force-exclude <the two edited Python paths> && ruff check <same> && <pytest-prefix> tests/integration/test_owned_analysis_alias_cli.py tests/specify_cli/test_analysis_inputs.py -q -rs` after expanded controls | One file formatted, one unchanged; lint passed; **35 passed, 1 warning** (existing legacy-governance-key fixture). |
| `<pytest-prefix> tests/integration/test_owned_analysis_alias_cli.py tests/integration/test_owned_analysis_implementation_cli.py tests/specify_cli/cli/commands/agent/test_analysis_report_transaction.py -q -rs` | **101 passed**, completed command. |

The expanded alias controls include canonical content change, canonical directory
addition/removal, retargeting to another independently selected authority with
identical content, equivalent-target link-spelling change, and external
retargeting. Material changes are committed before invoking implement, so refusal
is not merely a dirty-checkout fallback. Unsafe-before-write controls include
dangling and self/cross-directory cycles, external and undeclared targets,
untracked/dirty aliases, absolute targets, intermediate root escape and symlink
ancestors. A real pre-commit and post-commit hook changes canonical target content;
both retain a `committed_unqualified` report and cannot unlock freshness.

The collector preserves strict bootstrap configuration checks. Selected canonical
authority endpoints are determined independently before traversal; an alias
cannot select a new secret/cache/mutable subtree just because it is contained.
Only exact selected non-alias directory endpoints qualify. The closure hashes
raw link spelling and canonical target identity, visits canonical content once,
and detects active traversal cycles. Package symlink, external pack, index and
pre/post-transaction guards are retained.

### Narrow strict comparison for the new module

The following exact command was executed in both the SDK lane and the existing
unchanged `base-1af6a711-src` source snapshot:

```sh
env UV_CACHE_DIR=/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/sdk-owned-analysis-mypy/cache uv run --no-project --with mypy --with types-jsonschema --with types-psutil --with types-PyYAML --with types-requests --with types-toml --python /Users/sam/git/crucible/_worktrees/spec-kitty-owned-checkout-runtime/.venv/bin/python mypy --strict --no-incremental --python-executable /Users/sam/git/crucible/_worktrees/spec-kitty-owned-checkout-runtime/.venv/bin/python --cache-dir=/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/sdk-owned-analysis-mypy/type-cache src/specify_cli/analysis_inputs.py
```

- Candidate: `analysis_inputs.py:192`, `no-any-return`, `_entry` returns
  `_artifact_hash_entry(path, root)`; **1 error in 1 checked file**, exit 1.
- Pinned base: identical statement/diagnostic at line 106; **1 error in 1
  checked file**, exit 1.
- **Zero introduced diagnostics** for the new module. No baseline fix, ignore,
  suppression, global installation or SDK `.venv` change was made.

The existing baseline issue was supplemented via `gh issue comment 5917 --repo
spec-kitty/spec-kitty --body <the additional narrow reproduction and unchanged
statement attribution>`:
[public baseline disposition](https://github.com/spec-kitty/spec-kitty/issues/5917#issuecomment-6062274560).

Read-only optional discovery used a file glob for `**/zig/docs` in the primary
API directory (no result) and enumerated the shared `_worktrees` direct children.
A concrete native owning root/Mission path was not established, so no native
collector probe or recording/claim/write was performed. No unrelated authority
class was changed without real refusal evidence. Native adoption still requires
the operator to re-run its actual recording with this reviewed SDK candidate;
these sandbox checks do not establish native release qualification.

Final alias self-review command: `git diff -- src/specify_cli/analysis_inputs.py
&& ruff check src/specify_cli/analysis_inputs.py tests/integration/test_owned_analysis_alias_cli.py
&& ruff format --check --force-exclude <same two paths> && git diff --check
&& git status --short && git branch --show-current && git rev-parse HEAD
&& date -u '+%Y-%m-%dT%H:%M:%SZ'` completed with exit 0 at
`2026-10-08T14:49:36Z`: lint passed, two files already formatted, whitespace
passed, only the intended alias source/test and three tracer documents changed.
HEAD remains `e86a792e5338d0b344456f1e1d9e5cfea2259afb` on the authorized branch.
Self-review checked HEAD-mode/blob provenance, strict bootstrap paths, exact
canonical endpoint selection, cycle rejection before visited-path deduplication,
single canonical content traversal and link-identity hashing. No native edit,
status snapshot manipulation, source commit/push/PR or broader authority-policy
change was performed. Independent review and actual native recording remain
the operator's next steps.

## Independent-review B2 closeout: validate prerequisites before content reads

B2 identified an ordering regression in the alias candidate: Mission metadata
and declarative paths were deferred into `selected`, while template prerequisite
resolution called `_mapping(meta.json)` before closure validation. An eventual
refusal was not sufficient because external content had already been read.

The bounded correction changes only `analysis_inputs.py` and the existing alias
test file, plus approach/design/evidence tracers. `_resolved_template_paths`
strictly validates the metadata path and all ancestors before its content read.
The selected closure is validated before calling the template helper. Resolved
templates then extend the same path/alias containers, preserving one canonical
traversal rather than creating a second master or broadening symlink admission.

### Prerequisite-reader audit

- `_mapping(config.yaml)`: already preceded by strict `_safe_path` bootstrap
  validation; unchanged.
- `_mapping(charter.yaml)` via the configured charter pointer: already preceded
  by strict path/ancestor validation; unchanged.
- `load_pack_registry(root)`: its prerequisite content read is the same validated
  `.kittify/config.yaml`; registration/effective-root selection adds no pack
  content read before that root is placed in the selected closure.
- `_resolved_template_paths`: directly reads Mission metadata, then invokes
  `resolve_mission_type_context` whose activation/governance/template slots can
  read project and pack definitions. Metadata is now explicitly checked at its
  read boundary, and all selected project/pack/authority paths have traversed
  material validation before that resolution runs.
- `_entry` content hashing/WP parsing remains after closure validation.
  Bundled package traversal retains its separate strict symlink check.

### Real read observation and failed-before / passed-after

`test_b2_metadata_refuses_before_content_read` uses the real linked-checkout
fixture and constructs (1) an actual external `meta.json` symlink and (2) an
actual symlinked Mission directory ancestor containing metadata. Its observer
wraps `Path.read_text`, records metadata reads, and delegates to the actual
reader. It does not mock authority selection or manufacture a safe source path.
The observer begins only after fixture construction.

| Exact executed arguments after the existing source pytest prefix | Result |
|---|---|
| `tests/integration/test_owned_analysis_alias_cli.py -k b2 -q` before B2 source edits | **2 failed, 20 deselected**. Refusal occurred, but each case recorded one actual metadata content read before refusal. |
| `ruff check src/specify_cli/analysis_inputs.py tests/integration/test_owned_analysis_alias_cli.py && <pytest-prefix> tests/integration/test_owned_analysis_alias_cli.py -k b2 -q` after validation-order correction | Lint passed; **2 passed, 20 deselected**, zero metadata content reads in both cases. |
| `ruff format --force-exclude <the same two Python paths> && ruff check <same> && <pytest-prefix> tests/integration/test_owned_analysis_alias_cli.py tests/specify_cli/test_analysis_inputs.py tests/specify_cli/cli/commands/agent/test_analysis_report_transaction.py -q -rs` | One file formatted, one unchanged; lint passed; **67 passed, 1 existing legacy-governance warning**, completed command. |

Both read-observation cases also preserve primary HEAD/raw index/staging/worktree
sentinels. The full focused run retains canonical-alias success, target
content/membership/retarget invalidation, cycle/external/unsafe-ancestor refusals
and real report-transaction race controls. No additional policy was introduced.

### Narrow strict comparison

The exact ephemeral uv `analysis_inputs.py` strict command in the preceding
alias section was rerun in the SDK lane and unchanged `base-1af6a711-src`
snapshot, with identical flags, stubs, SDK Python executable and target file.

- Candidate: `analysis_inputs.py:199`, `no-any-return`, unchanged
  `return _artifact_hash_entry(path, root)`; **1 error / 1 checked file**, exit 1.
- Pinned base: same statement/diagnostic at line 106; **1 error / 1 checked
  file**, exit 1.
- **Zero introduced findings**. The documented #5917 baseline remains red; no
  ignore, suppression, baseline code repair or checker configuration change was
  made. The new closure extension and metadata prevalidation add no diagnostics.

Independent re-review is still required before adoption. No global installation,
new source checkout/branch, native write, status snapshot edit, source commit,
push or PR was performed.

B2 final self-review: `ruff check src/specify_cli/analysis_inputs.py
tests/integration/test_owned_analysis_alias_cli.py && ruff format --check
--force-exclude <same two paths> && git diff --check && git branch --show-current
&& git rev-parse HEAD && date -u '+%Y-%m-%dT%H:%M:%SZ'` completed with exit 0 at
`2026-10-08T17:06:46Z`: lint passed, two files already formatted and whitespace
passed. Branch/HEAD remain `fix/owned-analysis-implementation` /
`e86a792e5338d0b344456f1e1d9e5cfea2259afb`. The reviewed B2 ordering changes do
not alter the canonical-alias eligibility conditions or existing transaction
guards. The candidate remains uncommitted pending independent re-review.

## Cold-bootstrap bundled-template provenance continuation

Initial audited source state was clean at
`604c63621c547c9e1f2d29b19171d311a33b39a5`, branch
`fix/owned-analysis-implementation`, in the existing authorized SDK checkout.
Renewed authorization covers this bounded dependency correction. No source
commit, push, branch/checkout creation, installation, CI/gate change, native
artifact edit, or native recording/admission occurred in this continuation.

Python Pedro and implement doctrine were loaded using source `PYTHONPATH`, the
existing `.venv`, isolated HOME, and `--no-mark-loaded`. The separate governed
read-only investigation log is `sdk-template-delegation-source.log`; it loaded
the same profile and identified the canonical package-only API. It is source
investigation evidence, not independent approval. `sdk-template-doctrine.log`
retains the actual implement context and its completed child exit is recorded.

### Executable test prefix and red/green ledger

All runs below used this prefix from the authorized SDK checkout:

```sh
T=/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode
env PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 TMPDIR="$T" \
  .venv/bin/python "$T/sdk-template-bound.py" LABEL LIMIT \
  .venv/bin/python -u "$T/owned-analysis-exit-pytest.py" FILES -q -rs
```

`LABEL`, `LIMIT`, and `FILES` below replace those tokens literally; the red runs
used `-q` without `-rs`. Every listed child completed without outer timeout.
Separate `.log` and `.exit.json` artifacts are retained per label. Do not reuse a
label: the driver deliberately refuses to overwrite prior evidence.

File aliases for this continuation:

| Alias | Literal path |
|---|---|
| COLD | `tests/integration/test_analysis_bootstrap_templates_cli.py` |
| PROOF | `tests/specify_cli/test_analysis_template_provenance.py` |
| INPUT | `tests/specify_cli/test_analysis_inputs.py` |
| ALIAS | `tests/integration/test_owned_analysis_alias_cli.py` |
| OWN | `tests/integration/test_owned_analysis_implementation_cli.py` |
| TX | `tests/specify_cli/cli/commands/agent/test_analysis_report_transaction.py` |
| BOOT | `tests/runtime/test_bootstrap_unit.py` |
| PRUNE | `tests/runtime/test_asset_preparation_prune.py` |
| MEMBERS | `tests/runtime/test_check_assets_membership_tolerance.py` |
| TERMS | `tests/architectural/test_no_legacy_terminology.py` |

| LABEL / LIMIT / FILES | Actual result and child exit |
|---|---|
| `sdk-template-red / 600 / COLD` | 4 failed, exit 1: three real global-template refusals plus an ordinary-default test-envelope error. Original log replaced by marked redacted summary; exit JSON retained. |
| `sdk-template-red-clean / 600 / COLD` | **3 failed, 1 passed**, exit 1, unchanged production source. Both owned modes and ordinary report-only emitted `failed_before_write` with the exact global-template refusal; ordinary default already succeeded. |
| `sdk-template-green-cli / 1800 / COLD` | **15 passed**, exit 0, initial qualifier. |
| `sdk-template-provenance-unit / 600 / PROOF` | **14 passed**, exit 0, first supplemental controls. |
| `sdk-template-final-cli / 2100 / COLD` | 5 failed, 10 passed, exit 1 after over-broad ancestor metadata strengthening. Four printed false provenance refusals; one FIFO readiness failure lacked child diagnostics. Corrected scope and added child-diagnostic capture. |
| `sdk-template-regressions / 1500 / ALIAS OWN INPUT TX BOOT PRUNE MEMBERS` | **160 passed**, one existing legacy-key warning, exit 0. |
| `sdk-template-final-proof / 600 / PROOF INPUT` | **31 passed**, one existing legacy-key warning, exit 0. |
| `sdk-template-qualified-cli / 2100 / COLD` | 1 failed, 14 passed, exit 1: remaining broad-ancestor read-window timestamp sensitivity refused a clean initial recording. Narrowed that metadata guard to the immediate asset directory; descriptor traversal still guards all ancestors. |
| `sdk-template-regression-current / 1500 / ALIAS OWN TX BOOT PRUNE MEMBERS` | **145 passed**, exit 0. Shared provenance seam and existing owned/alias/transaction behavior validated. |
| `sdk-template-final-qualified-cli / 2100 / COLD` | **15 passed** in 1063.59s, pytest main 0, normal shutdown and actual child exit **0**. Includes the native caller's `/var` system-alias HOME spelling. |
| `sdk-template-final-targeted / 1200 / PROOF INPUT ALIAS TX TERMS` | **180 passed** in 651.91s, one existing legacy-key warning, pytest main/actual child exit **0/0**. |
| `sdk-template-type-clean-proof / 240 / PROOF` | **17 passed**, actual exit 0 after strict tuple annotations and removal of an unused observation field. These final edits preserve the tested selection/read algorithm. |

The root CLI tests use cold isolated HOME and actual startup, resolver and Git
transactions. FIFO synchronization pauses at the existing input read *after*
bootstrap; mutable bytes and identical non-mission global copies, leaf/ancestor/
HOME symlinks then refuse before report write. Post-report altered bytes,
equal-byte replacement, HOME retargeting and links cannot claim WP01. Real
pre/post-commit hooks leave `committed_unqualified` reports and admission refuses.
Primary HEAD, raw index and staged/unstaged/untracked sentinels are checked.

Supplemental controls observe real reads, including ancestor retargeting before
descriptor open with **zero content reads**, transient directory ABA during a
read, package-pin/source mismatch, and replica mutation during package pinning.
They do not alter SDK package sources. Unrelated global membership remains
non-material; descriptor-unavailable platforms explicitly fail closed. Complete
project material keys and both package pins remain in successful reports.

### Strict comparison against the actual initial HEAD

An unmodified source/config archive of `604c636` was extracted under the approved
`sdk-owned-analysis-mypy/base-604c636-src` directory with `git archive`; it is not
a Git checkout or branch. The identical command below ran from that archive and
the candidate directory, through the bounded driver with a 240-second limit:

```sh
env UV_CACHE_DIR="$T/sdk-owned-analysis-mypy/cache" PYTHONDONTWRITEBYTECODE=1 \
  uv run --offline --no-project --with mypy --with types-jsonschema \
  --with types-psutil --with types-PyYAML --with types-requests --with types-toml \
  --python /Users/sam/git/crucible/_worktrees/spec-kitty-owned-checkout-runtime/.venv/bin/python \
  mypy --strict --no-incremental \
  --python-executable /Users/sam/git/crucible/_worktrees/spec-kitty-owned-checkout-runtime/.venv/bin/python \
  --cache-dir="$T/sdk-owned-analysis-mypy/type-cache" \
  src/specify_cli/analysis_inputs.py src/specify_cli/runtime/asset_preparation.py
```

Base: **1 error / 2 checked source files**, exit 1, at `analysis_inputs.py:199`.
Initial candidate also had one error; the later final-metadata edit introduced
two tuple-inference errors (3 total), which were fixed with explicit annotations.
Final candidate (`sdk-template-type-clean-strict.log`): **1 error / 2 checked
source files**, exit 1, at line 202. The comparator maps exact unchanged source
lines and requires identical path/message/error code: one matched unchanged
`return _artifact_hash_entry(path, root)` finding, **zero introduced findings**.
This remains differential strict qualification, not an absolute pass; #5917
already tracks the diagnostic. No ignore, suppression or checker flag changed.

Final comparison executed with
`.venv/bin/python "$T/sdk-template-bound.py" sdk-template-type-clean-comparison 30 .venv/bin/python "$T/sdk-template-attribute-strict.py" sdk-template-type-clean-strict.log`:
actual child exit **0**, one exact unchanged match, zero introduced findings,
zero base-only findings. Final Ruff lint, four-file formatter check and
`git diff --check` all passed. The status/branch/HEAD audit lists exactly the
two source files, two new tests and four tracer files below; branch and initial
HEAD remain the requested values.

### Independent verification and remaining scope

From the authorized SDK directory, set `T` as above and use fresh artifact labels:

```sh
env PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 TMPDIR="$T" \
  .venv/bin/python "$T/sdk-template-bound.py" "review-cold-$(date -u +%Y%m%dT%H%M%SZ)" 2100 \
  .venv/bin/python -u "$T/owned-analysis-exit-pytest.py" \
  tests/integration/test_analysis_bootstrap_templates_cli.py -q -rs

env PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 TMPDIR="$T" \
  .venv/bin/python "$T/sdk-template-bound.py" "review-proof-$(date -u +%Y%m%dT%H%M%SZ)" 1200 \
  .venv/bin/python -u "$T/owned-analysis-exit-pytest.py" \
  tests/specify_cli/test_analysis_template_provenance.py \
  tests/specify_cli/test_analysis_inputs.py \
  tests/integration/test_owned_analysis_alias_cli.py \
  tests/specify_cli/cli/commands/agent/test_analysis_report_transaction.py \
  tests/architectural/test_no_legacy_terminology.py -q -rs

ruff check src/specify_cli/analysis_inputs.py src/specify_cli/runtime/asset_preparation.py \
  tests/integration/test_analysis_bootstrap_templates_cli.py tests/specify_cli/test_analysis_template_provenance.py
ruff format --check --force-exclude src/specify_cli/analysis_inputs.py src/specify_cli/runtime/asset_preparation.py \
  tests/integration/test_analysis_bootstrap_templates_cli.py tests/specify_cli/test_analysis_template_provenance.py
git diff --check
```

Only two source files, two new targeted test files, and these four existing
tracers change in this continuation. The extra source seam is justified by reuse
of the existing ancestry/system-alias provenance rule; resolver precedence,
bootstrap installation and canonical status sources receive no edits.
Independent review and the operator's actual native command remain outstanding.
The qualified exception requires descriptor-safe platform support; the package
and full manifest remain the content authority, and local replica replacement
requires re-recording. No native delivery or cross-platform qualification is
claimed by these sandbox results.

## Renata template-provenance re-review: B1/B2 rework

The owned branch and HEAD were re-audited as
`fix/owned-analysis-implementation` /
`604c63621c547c9e1f2d29b19171d311a33b39a5`, with only the existing bounded diff.
Production edits in this pass are confined to metadata-only ancestor
classification in `runtime/asset_preparation.py` and required package-pin row
membership in `analysis_inputs.py`. Tests are appended to the existing untracked
`test_analysis_template_provenance.py`; the root-CLI test file receives no rework
edits. These four existing tracer files record the dispositions.

### Separate failing-first reproductions

Using the same approved-temp source test prefix documented above:

| Driver label / limit | Literal pytest arguments | Actual result / child exit |
|---|---|---|
| `sdk-template-review-b1-red / 240` | `tests/specify_cli/test_analysis_template_provenance.py -k b1 -q` | **2 failed, 17 deselected**, exit 1. Each observer recorded one actual ancestor `Path.read_bytes`; the race replaces the file with an external link after `lstat`. |
| `sdk-template-review-b1-green / 240` | Same arguments after the B1 seam edit | **2 passed, 17 deselected**, exit 0; both path-content and descriptor-content read counts are zero. |
| `sdk-template-review-b2-red / 240` | `tests/specify_cli/test_analysis_template_provenance.py -k b2 -q` | **1 failed, 19 deselected**, exit 1: full collection did not raise despite omission during real traversal. All source observations remained equal after restoration. B2 production code was unchanged for this run. |
| `sdk-template-review-b2-green / 240` | Same arguments after required/contributed membership enforcement | **1 passed, 19 deselected**, exit 0: refuses `Selected bundled template missing from mission-assets pin`. |

B2's fixture uses copied real bundled assets and a copied kernel anchor file
under the test temporary directory. Only the canonical ancestor-walk anchor
input is redirected; canonical path, Mission context and package-only definition
resolution bodies execute unchanged. An observer delegates the real `rglob`
while the actual temporary `software-dev` subtree is renamed out, then restores
it before final observations. Assertions establish that the selected source
still exists, was absent from traversal rows, and has unchanged observed content
and identity. No SDK package source or protected checkout is modified.

### Focused green and regression qualification

The following runs use the exact prefix above with these literal labels,
1200-second limits, named files, arguments and completed exits:

```sh
# LABEL=sdk-template-review-regressions
tests/specify_cli/test_analysis_template_provenance.py
tests/specify_cli/test_analysis_inputs.py
tests/integration/test_owned_analysis_alias_cli.py
tests/specify_cli/cli/commands/agent/test_analysis_report_transaction.py
tests/runtime/test_bootstrap_unit.py
tests/runtime/test_asset_preparation_prune.py
tests/runtime/test_check_assets_membership_tolerance.py
-q -rs

# LABEL=sdk-template-review-cold-cli
tests/integration/test_analysis_bootstrap_templates_cli.py
-k 'cold_owned or cold_ordinary or real_global_template_commit_race' -q -rs
```

- Regression group: **129 passed**, one existing legacy-key warning, in
  588.23s; pytest main and real child exits **0/0**, no outer timeout.
- Root-CLI group: **6 passed, 9 deselected** in 379.81s; pytest main and real
  child exits **0/0**, no outer timeout. This revalidates both ordinary and owned
  cold-bootstrap recording modes and the real pre/post-commit race controls.
- `ruff format --force-exclude` over the four current Python paths reformatted
  only the supplemental test file; all source files and the root-CLI file were
  unchanged by formatting. `ruff check` passed over those four paths. Final
  formatter/whitespace validation is included in the final audit below.

### Necessary strict comparison

The identical two-source-file offline strict command from the preceding section
ran as `sdk-template-review-strict`, with a 240-second whole-child bound. It
reported **1 error / 2 checked files**, actual exit 1: unchanged `_entry` at
`analysis_inputs.py:202`, `no-any-return`. The existing unmodified initial-HEAD
archive reports the identical diagnostic at line 199.

```sh
.venv/bin/python "$T/sdk-template-bound.py" sdk-template-review-strict-comparison 30 \
  .venv/bin/python "$T/sdk-template-attribute-strict.py" sdk-template-review-strict.log
```

The comparator exited **0**: one exact unchanged-source match, **zero introduced
findings**, zero base-only findings. This remains differential qualification
against the documented #5917 baseline, not an absolute strict pass.

### Finding disposition for independent re-review

| Finding | Disposition | Evidence | Remaining action |
|---|---|---|---|
| Renata template B1, P1 | Addressed: metadata-only ancestor classification; descriptor-safe leaf read retained | 2 red → 2 green; zero reads in both green cases; bootstrap regression group passes | Independent reviewer re-checks the corrected diff; no fixing commit exists under the no-commit instruction |
| Renata template B2, P1 | Addressed: selected proof membership must equal digest-verified row membership for each package pin; final observations retained | Full-collector 1 red → 1 green; real resolution/traversal/restoration; regression and cold-root-CLI groups pass | Independent reviewer re-checks completeness enforcement; no adoption or native command has run |

All `sdk-template-review-*` logs and actual exit JSON are retained under `T`.
No commit, push, adoption, native command, new branch/checkout, gate or canonical
status edit occurred. The total bounded diff still has two source files, two new
test files and these four existing tracer files; no path is added by the rework.

Final audit after tracer updates: Ruff lint passed, all four Python files were
already formatted, and `git diff --check` passed. The status/branch/HEAD read
confirmed exactly the eight existing bounded-diff paths on the requested branch
and unchanged initial HEAD. The final source review checked metadata-only
classification, required membership derived before traversal, digest/identity
verification before row contribution, and retained final observations.

## Exact edited surfaces

Source:

```text
src/charter/activation/context.py
src/specify_cli/analysis_report.py
src/specify_cli/analysis_inputs.py
src/specify_cli/cli/commands/agent/mission_record_analysis.py
src/specify_cli/cli/commands/agent/workflow.py
src/specify_cli/cli/commands/agent/workflow_executor.py
src/specify_cli/cli/commands/agent/workflow_cores.py
src/specify_cli/coordination/status_transition.py
src/specify_cli/git/report_transaction.py
src/specify_cli/lanes/checkout_occupancy.py
src/specify_cli/lanes/implement_support.py
src/specify_cli/review/cycle.py
src/specify_cli/status/emit.py
src/specify_cli/status/work_package_lifecycle.py
```

Tests and documentation:

```text
tests/integration/test_owned_analysis_implementation_cli.py
tests/integration/test_owned_analysis_alias_cli.py
tests/integration/test_owned_lifecycle_acceptance_cli.py
tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py
docs/context/execution.md
docs/reports/owned-analysis-5882/approach.md
docs/reports/owned-analysis-5882/design-decisions.md
docs/reports/owned-analysis-5882/tooling-friction.md
docs/reports/owned-analysis-5882/evidence.md
```

Verdict policy, Mission/user artifacts and unrelated SDK lanes received no source
edits. Sandbox Git repositories and linked checkouts
are test fixtures, not additional SDK work lanes.

## Review disposition

Self-review addressed owner branch naming, already-committed claim qualification,
checkout-root guard activation, stale-primary feedback leakage and prompt paths.
The source is ready for independent review as a bounded candidate. Strict typing
now completes in the operator-provisioned ephemeral environment: **zero introduced
findings**, with all 13 candidate errors reproduced on pinned unchanged source.
The full strict command remains red; [#5917](https://github.com/spec-kitty/spec-kitty/issues/5917)
tracks that baseline. This is differential qualification, not an absolute strict
pass. Independent review and delivery remain the orchestrator's responsibility.
The subsequent P1 B1 rejection has been addressed in the read path with real
failed-before/passed-after CLI evidence. Corrected-source independent re-review
is pending; the previously unqualified concurrency exit is now qualified at 0.
No coverage percentage, independent approval, merge or release is claimed.
