---
doc_status: active
updated: '2026-10-08'
---

# Validation and delivery evidence

The earlier production qualification is fixed at
`0de4fdda43c6bd1baf48066a5fdde0cb45fa69d6`;
`2cc7a3311` adds public recovery/identity refusal tests; `21afc9300` adds shared
owned review-base authority and command quoting. The final source has a normalized
file ending and is held unchanged throughout final qualification.
The explicit review base is PR67 head
`4196af70fe69d558c729d2e6265be921999b5761`, not the fork default branch.
Python 3.11.15 and the existing checkout environment were used. Nothing was
installed globally, and active sibling missions were not advanced by these tests.

## Behaviors demonstrated

- Supported agent reentry refreshes a finalized shared lane from one member to
  two, then ownership resolves the actual active second WP. Saved creation/base
  provenance and an in-flight file remain byte-identical. Existing ancestry
  operations are mocked in this focused contract case; context persistence,
  finalized metadata and canonical status reduction are real.
- Allocator reuse uses the same context operation. Invalid identity refuses
  before ancestry callbacks. Duplicate finalized membership, corrupt authority
  and member drift expose specific ownership refusals. Missing context remains
  absent for supported recovery; outside mission/WP requests cannot rewrite it.
- Explicit action context and warmed same-slug caches retain their selected
  checkout. Real native next progresses discovery → specify → plan → tasks →
  implement with actual composition and guards. Its physical workspace, WP path
  and issued lifecycle options all reference the selected checkout. Primary and
  sibling HEAD/index/status/file snapshots remain unchanged after every step.
  This is an isolated Git fixture, not proof of installed runtime adoption.

## Checks

The stable source run passes 744 cases across these affected packages:

```text
tests/integration/test_explicit_checkout_commands.py
tests/specify_cli/cli/commands/agent/test_owned_checkout_move_task.py
tests/runtime/test_workspace_context_unit.py
tests/next/test_next_command_integration.py
tests/runtime/test_bridge_engine.py
tests/runtime/test_bridge_composition.py
tests/next/test_prompt_builder_unit.py
tests/next/test_runtime_bridge_blocked_paths.py
tests/next/test_runtime_bridge_unit.py
tests/specify_cli/lanes/test_for_review_gate_parity.py
tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py
```

Run with `PYTHONPATH=src .venv/bin/python -m pytest <paths> -n4 --dist loadfile
-q -p no:cacheprovider`. The four additional recovery/identity cases pass in the
31-case workspace suite. Both new context helpers exercise all 27 executable
statement lines; this measures statements, not semantic completeness or branches.
Final isolated measurement exercises 169 of 173 added executable statement lines
(97.69%), including moved statements. It does not measure branches or semantic
completeness; four unexercised lines remain listed in the receipt.

Strict mypy checks all nine changed production files with zero issues; Ruff
checks those files and both changed test files with no suppression additions.
`git diff --check` passes. Ten terminology cases pass after the report updates.
214 architecture cases pass with one existing skip, covering read-side placement,
status import boundaries, dead symbols, layer rules, inline metadata reads,
mission-type readers and architecture shard markers. A complete repository suite
was not run; the charter specifies affected packages for scoped delivery.

## Retained failed attempts

The original shared-lane reentry cases are red before their source fix. The owned
native regression is also red on the immutable PR67 source archive: it looks for
WP01 under the protected checkout's task directory. To bind that reproduction,
set pytest's `-o pythonpath=<archive>/src`; the earlier environment-only override
was misbound and passed candidate source, so it is not counted as a red receipt.

An intermediate 364-case run had 363 passes and a source-inspection failure while
its source file was concurrently reformatted. The exact assertion passes on both
stable candidate and immutable baseline, and the complete stable rerun passes.
That failed run remains available with the misbound baseline and initial invalid
suite-path attempt. No test, warning policy or hook was removed to get green.

Modern owned review cases use the actual finalized planning commit; invalid
missing/unresolvable/HEAD/nonancestor bases refuse without side effects. The
historical formatter compatibility case supplies only the prior nullable-lane
workspace-resolution port and uses real Git history/scopes; it does not claim
modern native legacy-checkout support. Current finalization rejects its historical
planning ownership declaration. The other workflow and owner cases use actual
resolution and admission, including displayed scoped commands executed on spaced
paths with unrelated work excluded.

Private operator logs and coverage JSON are retained in the parent chat's `work/`
directory under `spec-kitty-*`. Review requires this fixed aggregate diff; these
checks grant neither review approval nor permission to overwrite an installed CLI.

## Explicit-owned local completion follow-up

The separate red test commit `1ac27b7a4` reaches a genuinely finalized,
implemented, independently approved and accepted disposable mission through
public commands. The pre-fix public merge parser refuses `--owned-checkout`.
The actual owner missing-primary-lanes preview remains retained as a distinct
baseline failure, with before/after source, HEAD and index preservation proofs.

Source validation for the follow-up is recorded separately in the final PR
receipt. The earlier 744-case/214-case qualification above is not approval of
this later source. No qualified installed source or actual 3body owner state is
changed by the fixtures.

The stable follow-up passes 30 public owned-completion cases, including actual
approval/acceptance, read-only preview, repeated completion, two-WP atomic
completion, dirty primary/sibling preservation, source arrival before lock,
commit-hook rollback, drift and unsupported-option refusals. It also passes 136
adjacent cases across transactional status emission, transaction rollback,
legacy routing, context guards, ordinary merge and agent delegation/goldens.
Architecture passes 148 cases with two existing skips. Strict mypy passes ten
source files (including the required typed dependencies); Ruff and whitespace
checks pass. Extended structural lint checks 799 pages with zero violations.

The stock Typer 0.27.3 parser vendors Click. Both immutable c32 golden-only and
full adjacent baseline runs reproduce 15 false helper failures (13 and 121
passes respectively). Test-only compatibility commit `7165559e1` uses native
public Typer classes and the parser's own context, preserving all prior exact
option/default/visibility assertions: 28 unchanged golden cases pass against
immutable c32. The completion increment separately adds only its explicit merge
options to the two golden sets. No dependency, production shim, assertion or
skip policy is changed to repair that helper.

The two default architecture skips are existing performance-marked tests. An
explicit run of their semantic content caught three new deep status imports in
the completion leaf and eight pre-existing sites. The new leaf now consumes the
already-exported canonical facade. A new unmarked focused rule requires this
boundary without timing opt-in; it passes, as do cold-import and metadata timing
checks. The corrected facade source reruns all 30 owned cases successfully and
passes strict mypy/Ruff. The repository-wide unskipped status scan still fails
on exactly eight sites reproduced against immutable c32: this is an outstanding
baseline gate, tracked in [owner-assigned issue71](https://github.com/crucible-energy/spec-kitty/issues/71).
No exemption, assertion or skip policy is changed to conceal it.

## Independent completion-history rejection and correction

Independent review rejected `ce8aa3664`: after a genuine public approval and
acceptance, committing a source edit and then its exact restoration allowed the
public owned preview to bind an unaccepted later HEAD. The endpoint diff lost
those intervening changes. That rejected source and its original passing suites
remain distinct from a corrected candidate; neither qualifies runtime adoption.

Causal red commits `926f3552f` and `4d809ce09` retain the source/contract/criteria/
metadata edit-and-restoration controls, including both public entry points,
preview, real completion and repeated completion. An additional red control
rebuilds only a disposable fixture's two acceptance follow-ups: correct producer
labels and restored final bytes conceal an intermediate metadata change. It
also fails against the rejected implementation.

The correction validates each bounded linear producer commit's paths and
content, rather than trusting its label or endpoint equality. After the
acceptance boundary it admits only the exact boundary HEAD or one single-parent
canonical terminal transaction containing both the event stream and snapshot.
Terminal evidence must reference that exact boundary; arbitrary empty commits,
restored source history and later reuse of an old completion proof refuse.
The normal real acceptance residual and multi-WP transaction remain required
positive controls. Independent fixed-source review remains a separate gate.

Corrected-source checks pass all 50 initial public cases and two additional
refusals for rewritten canonical events and status-only formatting. The two
complementary coverage cohorts (24 and 28 cases) exercise all 52 current cases:
all 34 changed executable lines versus rejected ce8 are covered. This is line
coverage, not branch or semantic completeness; the whole leaf measures 178/202
statements (88%). All 136 adjacent regressions and the fresh 180-case architecture
cohort pass, with two existing timing skips. The canonical-reader floor rises
156 to 157 against measured live usage 161, retaining its four-site margin.
Strict mypy passes the same ten-file closure, Ruff passes and extended docs lint
checks 799 pages without violations. The exact independent history probe also
passes its required refusal after the repair.

The initial append measurement emits two warnings because report filenames
shared the SQLite data prefix. They remain retained; a byte-identical database
copy passes SQLite integrity checking and produces the final report from an
isolated data filename without those warnings. No test or source rule changes
to repair this operator reporting mistake.

## Substantive evidence probes adopted from independent review

Independent cycle-two review runs the frozen 52 owned cases and 28 parser
goldens, then supplies seven additional public fault probes. The author adopts
these tests without changing the production bytes at `95852e720`. Four faults
exercise actual terminal evidence: a real earlier commit instead of the exact
acceptance boundary, a different repository, a mismatched actual review reference
and missing repository evidence. Two faults exercise accepted-record coherence:
an existing acceptance commit substituted for its actual parent and a history
actor differing from the current record. The seventh corrupts a genuine producer
verification command and restores the final matrix bytes in a later commit.
All require the specific refusal and preservation of every fixture checkout.
Canonical materialization is used only in disposable terminal fault fixtures.

Author validation passes these seven cases with exact observed refusal codes,
all 28 unchanged parser goldens, strict typing and Ruff. The combined 52-case and
seven-case coverage data measures 182/202 statements (90.099%), with no excluded
lines, satisfying the charter's 90% new-code requirement for this leaf. It uses
separate SQLite/report filenames and emits no append/report-prefix warnings.
The earlier 178/202 measurement remains retained as its own outcome. Applicable
docs/terminology checks and the exact test-only delivery recheck remain separate
from production-source review and any runtime qualification or adoption.
