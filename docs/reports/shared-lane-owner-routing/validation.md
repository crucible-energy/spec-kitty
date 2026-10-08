---
doc_status: active
updated: '2026-10-08'
---

# Validation and delivery evidence

Production source is fixed at `0de4fdda43c6bd1baf48066a5fdde0cb45fa69d6`;
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
