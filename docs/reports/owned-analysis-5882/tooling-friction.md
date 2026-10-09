---
title: 'Owned analysis and implementation: tooling friction'
description: 'Observed governance placement, test-harness and static-tooling limits during the bounded dependency implementation.'
doc_status: draft
audience: docs/context/audience/internal/maintainer.md
type: explanation
updated: '2026-10-09'
---

# Tooling Friction — #5882

Audience: the SDK orchestrator.

- `dispatch._get_repo_root` calls `find_repo_root`, which folds linked checkouts
  to the repository root. Dispatch has no owned-checkout option and its executor
  auto-commits Op records. Opening or closing an Op could therefore mutate the
  protected dirty primary, contrary to the operator's scope and no-commit rule.
  No mutating standalone command was invoked.
- `charter context --action implement --mission-type software-dev
  --no-mark-loaded` succeeded, but named the primary doctrine root and an older
  charter section set. It emitted `LegacyGovernanceKeyWarning`. The branch's
  fully read charter remains the binding context. No charter sync/activation was
  run against the SDK.
- The first environment probe accidentally targeted the primary `.venv`:
  Python 3.11.3, events 6.1.0, tracker 0.4.3. This environment was not used for
  product tests. The lane `.venv` is Python 3.11.15, pytest 9.0.3,
  events 10.4.0, tracker 0.5.2; `PYTHONPATH` selects this branch's `src`.
- The root suite fixture normally creates/installs a separate test environment.
  The approved-temp launcher replaces only that installer with the provisioned
  lane environment. It keeps SDK HOME fixtures and product resolution active.
- The suite's collection hook parses the entire test tree even for named files.
  Two bounded attempts timed out before tests. A traceback located the whole-tree
  wall-clock assertion scan. The launcher limits that assertion scan to this
  invocation's named files, without changing assertions or product guards.
- Cacheprovider is disabled; test temporary state lives under the approved
  `opencode` temp parent. The launcher is
  `/var/folders/4g/1bsytq914tscfrn82thwf0r40000gn/T/opencode/owned-analysis-pytest.py`.
- Some combined runs exceeded their shell budget before a result summary. One
  concurrency run printed `131 passed` before the shell timed out after the
  summary. These command outcomes are distinguished from completed green runs.
  B1 closeout subsequently qualified the same six concurrency/lock/occupancy
  files through a bounded subprocess driver: `131 passed`, pytest main return 0,
  normal Python shutdown and actual child exit 0. The earlier timeout's precise
  cause cannot be recovered; the completed run needed more wall time than its
  test-summary duration. The new driver permits 1800 seconds for the whole
  process, preserves the normal 240-second per-test limit, records shutdown
  diagnostics if needed and never treats a summary as an exit status.
- `ruff` is available at `/opt/homebrew/bin/ruff`; it is absent from the lane
  Python environment. `mypy` is absent from PATH and both SDK environments.
  This describes the initial session. In the continuation the operator supplied
  an ephemeral uv mypy/stub environment under `sdk-owned-analysis-mypy` in the
  approved temp parent; the SDK `.venv` and global installations remain unchanged.
  The typing blocker is now a reproduced red base, not unavailable tooling.
  All 13 candidate findings reproduce on unchanged source; the base run also
  reports 13 transitive findings absent from the candidate output. No repair of
  those transitive findings is claimed.
- The charter-required baseline report was created as GitHub issue #5917.
  `gh issue create --assignee samuelgoff` returned a GraphQL
  `ReplaceActorsForAssignable` permission error **after creating the issue**.
  A query confirmed the issue and its full body, so no duplicate was created.
  Its body names Sam as owner, but the assignee list is empty. A repository
  maintainer with assignment permission must add `samuelgoff` as assignee.
- The file reader truncated three long lines of `AGENTS.md`; a bounded Python
  read retrieved those lines in full. No instruction was inferred from a
  truncated suffix.

## Cold-bootstrap continuation at 604c636

- An initial default-model delegated investigation returned a tools-unavailable
  response without loading its profile. It is not counted as governed
  delegation. The explicit `openai/gpt-6.1-sol` invocation then loaded Python
  Pedro via the existing source CLI, read the branch charter and implement
  context, and completed a bounded read-only source investigation. Both actual
  process exits and logs are retained under the approved temp parent.
- The implement-context command initially exceeded a 60-second shell budget.
  The whole-child bounded invocation subsequently exited 0 in 31.88 seconds.
  Its existing primary-folded doctrine-root/legacy-key diagnostic remains
  visible; the fully read owned branch charter governs the change.
- The first pytest failure-local repr included inherited environment credentials.
  That unsanitized log was removed and replaced with a clearly marked redacted
  outcome record; its actual exit JSON is retained. Cold CLI environments now
  use an explicit non-secret process-variable set. A second unchanged-source
  red-first run preserved complete clean diagnostics: three product failures,
  one ordinary-default pass. No raw credential values are retained in these
  tracer documents.
- An ordinary-default test initially assumed the report-only `commit_status`
  envelope. The unchanged command already returned success; the assertion now
  checks its actual success envelope and report artifact. This was a test error,
  not a fourth product failure.
- The approved `sdk-template-bound.py` driver creates a separate child session,
  waits through actual shutdown, and TERM/KILLs that session only at its bound.
  It never converts a pytest summary or timeout into exit 0. The existing source
  pytest launcher and provisioned `.venv` are reused without installation.
- A broad ancestor-timestamp proof generated real false refusals under parallel
  targeted runs. It was corrected in code, not retried unchanged. Descriptor-safe
  traversal and immediate-directory read-window checks now preserve authority
  safety while excluding unrelated shared ancestor membership.
- The final strict pass first exposed two introduced tuple-inference errors.
  Explicit variable-length tuple annotations fixed both without suppression.
  The final differential command has only the previously reported #5917
  unchanged `_entry` diagnostic. Offline uv reused the provisioned ephemeral
  mypy/stub environment; no installed/global CLI or SDK environment was changed.

## Renata template-provenance rework

- Eventual B1 refusal hid an actual content read. The new observers delegate
  `Path.read_bytes`, `Path.lstat` and descriptor hashing to their real bodies;
  each pre-fix case recorded one ancestor byte read. Post-fix cases record zero
  path-content and descriptor-content reads, including file-to-link retargeting.
- Endpoint observations also hid B2 traversal omission. Moving the SDK's own
  package subtree would violate scope, so the test uses a temporary copied
  packaged layout with the real kernel ancestor-walk and definition resolvers.
  Its real traversal is observed while the selected subtree is absent; cleanup
  restores that subtree even on assertion failure. The pre-fix collector
  actually returned without refusal, and every retained source observation
  compared equal. The test does not substitute a pin or successful result.
- This rework reused the existing bounded source launchers and offline strict
  environment. No additional test/tooling failure or new baseline diagnostic
  was accepted. All targeted children reached actual exits without timeout.

## Source-membership continuation

- The operator's native command progressed past template provenance but listed
  compiler caches/emitted binaries as `DIRTY_ANALYSIS_INPUT`. Both real SDK
  root-CLI recording modes reproduced this on a clean Git fixture with 200
  ignored artifacts. This was membership failure, not a dirty native source
  checkout; no cache cleanup or native workaround was attempted.
- A read-only delegated Python Pedro investigation loaded its actual profile and
  implement doctrine, and identified that effective-ignore status alone cannot
  establish repository policy provenance. The canonical listing seam is extended
  by one repository-only ignore query; no alternate Git parser is added to the
  collector. Its completed log is `sdk-membership-delegated-investigation.log`.
- A probe confirmed that verbose `check-ignore -z` requires stdin. That route was
  not introduced: the repository-only `ls-files` query expresses the required
  authority directly, reusing existing NUL parsing and excluding mutable personal
  policy without staging temporary repositories or rewriting Git configuration.
- A new kernel test initially triggered Ruff PT011 for a broad `ValueError`
  assertion; its chained CLI test command did not run. The assertion now names
  the expected malformed-path/classification diagnostics. No rule was suppressed.
- Strict mypy exposed one introduced snapshot-return inference error. An explicit
  typed digest local fixed it; the final check has only the unchanged #5917
  `_entry` diagnostic. Offline uv reused the provisioned checker environment.
- A later alias regression safely refused a linked metadata ancestor, but the
  membership helper had obscured its original symlink diagnostic. It now
  preserves `MaterialInputError` directly. The final focused regression run
  passes the original zero-read alias controls without weakening their assertions.
- Tracked missing descendants cannot be recovered from disk traversal alone.
  The closure now retains HEAD/index-owned missing source as sentinels. The
  associated control includes a tracked ignored file deleted from disk and a
  staged index removal. Locality cleanup kept the closure under the existing
  complexity ceiling with a source-membership descendant query; no gate or
  checker configuration changed.

## B3 explicit-directory rework

- Read the operator's exact B3 note and retained
  `renata-membership-explicit-dir-cli-20261008T235100Z.log` / `.exit.json`.
  The real CLI returned 0 / `committed`, with `EXPLICIT_CHILD_RETAINED: False`
  and `TRACKED_CHILD_RETAINED: True`. This was an actual omitted-authority
  acceptance, not an eventual-refusal diagnostic problem.
- New red-first tests produced four failures and one pass. Both recording modes
  accepted the omitted authority; tracked/deleted-child collector snapshots
  ignored byte changes. Staged removal passed because it changed enumeration
  into a directory record, exposing the membership-dependent policy inference.
- A direct effective-policy probe initially assumed repository provenance but
  observed the external `info/exclude` parent rule. That diagnostic assumption
  was corrected into a regression control for the repository-only policy view.
  The fix uses no effective-exclude shortcut, second ignore-pattern parser or
  temporary Git repository.
- The index-independent query owns only a temporary directory and absent-index
  pathname, with cleanup on success and error. The source/HEAD/index snapshots
  continue to use the actual index. Existing source launchers and offline typing
  environment were reused; no installation, native operation or heavyweight
  sweep was performed.
