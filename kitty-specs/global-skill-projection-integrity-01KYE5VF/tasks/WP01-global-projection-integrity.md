---
work_package_id: WP01
title: Recover and verify global managed skill projections
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-001
- C-003
- C-004
planning_base_branch: fix/global-skill-projection-integrity
merge_target_branch: fix/global-skill-projection-integrity
branch_strategy: Planning artifacts for this mission were generated on fix/global-skill-projection-integrity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/global-skill-projection-integrity unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-global-skill-projection-integrity-01KYE5VF
base_commit: 70b9c342ab500ed433289534574bc35eb51204df
created_at: '2026-07-26T03:14:07.986539+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/runtime/agent_skills.py
- tests/runtime/test_agent_skills.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Recover and verify global managed skill projections

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is available, run `spec-kitty agent profile list` and select the best match for this work package's Python runtime and test surface.

---

## Objective

Make a current global skill version lock trustworthy only when the complete
registry-owned projection is present and content-correct. Recover an incomplete
managed root with the existing synchronizer while preserving every user-owned
sibling skill.

## Context

The user observed a host warning for a missing
`spec-kitty-orchestrator-api-operator/SKILL.md` after an interrupted migration.
`agent-skills.lock` currently short-circuits bootstrap based on version only.
The canonical registry and `_sync_skill_root` already provide the correct
source and writer boundaries; this WP adds an integrity gate around them rather
than a second installer or manifest. See `plan.md`, `research.md`, and
`contracts/global-projection-integrity.md`.

### Subtask T001: Establish current-lock regression fixtures first

**Purpose**: Prove the historical skip path is unsafe before changing runtime
behavior.

**Steps**:

1. Extend `tests/runtime/test_agent_skills.py` with an isolated-home fixture
   pattern that creates a small canonical registry and writes the current CLI
   version to `agent-skills.lock`.
2. Seed an initial complete global projection, remove the canonical
   `SKILL.md` equivalent under `.agents/skills`, invoke bootstrap, and assert
   the file is restored.
3. Make this test red against the planning base before editing runtime logic;
   record the exact focused command and result in WP history.

**Files**: `tests/runtime/test_agent_skills.py` (modify, focused fixture and red test).

**Validation**: The new test fails on the unmodified runtime because a current
lock skips synchronization and leaves the file absent.

### Subtask T002: Define normalized expected-content comparison

**Purpose**: Build a small private, deterministic comparison between the
registry-owned source tree and one global root.

**Steps**:

1. Add a helper that iterates every discovered skill and every `all_files`
   member, preserving each file's path relative to its canonical skill root.
2. Normalize canonical `SKILL.md` content through `ensure_skill_frontmatter`
   with the skill name before computing expected bytes; compare other files as
   raw canonical content.
3. Use a stable content digest or direct byte-equivalence helper. Missing,
   unreadable, malformed, or mismatched target files must return unhealthy.
4. Keep helpers private, typed, and below the project complexity ceiling.

**Files**: `src/specify_cli/runtime/agent_skills.py` (modify, private helper set).

**Validation**: Focused tests distinguish integral, missing, and divergent
managed files, including a missing file below `references/`.

### Subtask T003: Gate the version-lock fast path on all global roots

**Purpose**: Ensure current-version state does not suppress integrity checking.

**Steps**:

1. Resolve the canonical registry before accepting the current-lock early
   return.
2. Run the new integrity predicate for every unique root returned by the
   existing supported-agent root resolver.
3. Return without rewrite only when every root is integral. If a root is
   incomplete, invoke the existing complete-root synchronizer for that root.
4. Keep the current lock write after all roots synchronize successfully. Do not
   write a success lock if discovery or synchronization fails.

**Files**: `src/specify_cli/runtime/agent_skills.py` (modify).

**Validation**: A current lock plus one missing file repairs; a healthy current
lock does not invoke synchronization; multiple distinct roots are evaluated.

### Subtask T004: Preserve user-owned siblings during recovery

**Purpose**: Align global cleanup with the charter's explicit ownership rule.

**Steps**:

1. Audit `_sync_skill_root` cleanup conditions.
2. Replace any broad package-name-prefix deletion with removal limited to the
   explicit retired canonical name set.
3. Retain existing read-only recovery behavior for known retired managed paths.
4. Do not add a heuristic, manifest, or automatic deletion path for unknown
   siblings.

**Files**: `src/specify_cli/runtime/agent_skills.py` (modify).

**Validation**: A custom sibling remains byte-identical after damaged managed
projection recovery; an explicitly retired managed directory is still removed.

### Subtask T005: Cover divergent, healthy, and permission boundaries

**Purpose**: Turn the recovery contract into executable evidence beyond the
reported missing-file case.

**Steps**:

1. Add a current-lock divergent-content test that proves canonical content is
   restored.
2. Add a current-lock healthy-tree test that spies on or otherwise proves no
   managed tree copy occurs.
3. Extend the Windows-like read-only-tree boundary where necessary so cleanup
   remains recoverable without weakening permissions.
4. Assert generated `SKILL.md` remains frontmatter-normalized and read-only.

**Files**: `tests/runtime/test_agent_skills.py` (modify).

**Validation**: All focused cases pass with no dependence on the developer's
real home directory or global skill tree.

### Subtask T006: Run focused quality gates and capture evidence

**Purpose**: Verify behavior, typing, formatting, and ownership posture before
the documentation handoff.

**Steps**:

1. Run `pytest tests/runtime/test_agent_skills.py`.
2. Run `ruff check src/specify_cli/runtime/agent_skills.py tests/runtime/test_agent_skills.py`.
3. Run `mypy --strict src/specify_cli/runtime/agent_skills.py`.
4. Run the repository's relevant doctor command against an isolated disposable
   setup, never by deleting a real user skill.
5. Record commands, outcomes, and any baseline failure attribution in the WP
   activity history.

**Files**: No additional source files unless a focused test exposes an
in-scope defect in the owned runtime/test surfaces.

**Validation**: All named commands pass or any unrelated red is proven against
the planning base and reported through the required project workflow.

## Definition of Done

- A current lock never suppresses recovery of a missing or divergent
  registry-owned global file.
- Every canonical file, including references, participates in integrity
  checking with `SKILL.md` normalization parity.
- Healthy current-lock roots are not rewritten.
- Custom sibling skills are preserved; only explicit retired package paths are
  cleaned.
- Focused pytest, ruff, and strict mypy evidence is recorded.
- Every subtask has a `spec-kitty agent tasks mark-status <Txxx> --status done`
  event after its evidence exists.

## Risks

- Comparing raw source `SKILL.md` bytes would create a permanent false mismatch
  after installer frontmatter normalization; test this explicitly.
- A broad cleanup rule would violate user customization preservation; retain
  only explicit retired-name removal.
- Do not expand this WP into PolymorphDB networking or static-authority changes.

## Reviewer Guidance

- Verify the red-to-green test actually uses a current version lock.
- Review all filesystem mutations for explicit ownership proof.
- Confirm errors cannot write a fresh success lock.
- Confirm no project-local projection or public CLI contract regresses.

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent codex
```

## Activity Log

- 2026-07-26T03:19:37Z – codex – shell_pid=82136 – T001 red-first evidence: .venv/bin/pytest tests/runtime/test_agent_skills.py::test_global_bootstrap_repairs_missing_managed_file_with_current_lock -vv -s failed as expected on the planning runtime (1 failed, assertion that the deleted managed SKILL.md was not restored). Test-only commit bc054d24a created before runtime changes.
