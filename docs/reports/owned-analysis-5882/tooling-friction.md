---
title: 'Owned analysis and implementation: tooling friction'
description: 'Observed governance placement, test-harness and static-tooling limits during the bounded dependency implementation.'
type: explanation
updated: '2026-10-08'
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
