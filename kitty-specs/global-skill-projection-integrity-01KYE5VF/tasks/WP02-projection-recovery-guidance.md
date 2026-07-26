---
work_package_id: WP02
title: Document global projection diagnosis and recovery
dependencies:
- WP01
requirement_refs:
- FR-006
- C-002
- C-005
planning_base_branch: fix/global-skill-projection-integrity
merge_target_branch: fix/global-skill-projection-integrity
branch_strategy: Planning artifacts for this mission were generated on fix/global-skill-projection-integrity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/global-skill-projection-integrity unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
history: []
agent_profile: curator-carla
authoritative_surface: docs/guides/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/guides/diagnose-installation.md
role: curator
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Document global projection diagnosis and recovery

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`
- **Agent/tool**: `codex`

If no profile is available, run `spec-kitty agent profile list` and select the best match for documentation and validation work.

---

## Objective

Give operators one accurate diagnostic path for a skipped or missing global
managed skill. Explain the distinction between a current version lock and an
integral compatibility projection, and direct repair through supported commands
instead of manual file copying.

## Context

This WP follows WP01 so documentation reflects shipped behavior. The harvested
architecture makes Aletheia-backed PolymorphDB the future runtime authority;
the current global files are host compatibility projections. Do not collapse
that distinction or promise an endpoint that does not exist.

### Subtask T007: Audit existing installation guidance

**Purpose**: Locate the closest missing-skill and managed-surface sections so
the new guidance extends rather than duplicates existing operator flow.

**Steps**:

1. Read `docs/guides/diagnose-installation.md` and linked setup/doctor docs.
2. Identify existing supported commands and confirm their help/output against
the local CLI before documenting them.
3. Record the appropriate insertion point and avoid stale paths or legacy
symlink instructions.

**Files**: `docs/guides/diagnose-installation.md` (inspect, then modify).

**Validation**: Every documented command exists and is appropriate for a
managed skill recovery scenario.

### Subtask T008: Add integrity-aware recovery guidance

**Purpose**: Make the lock-versus-content failure mode visible and actionable.

**Steps**:

1. Explain that `agent-skills.lock` records a completed sync version but is not
   operator proof that every generated file still exists.
2. Document the supported diagnosis and repair sequence from the validated CLI
   surface, including host refresh/restart after repair.
3. State that generated global/project trees must not be hand-edited or copied
   manually; user-owned custom skills are separate and preserved.
4. Use the concrete missing `SKILL.md` warning as an example without exposing
   user-specific home paths.

**Files**: `docs/guides/diagnose-installation.md` (modify).

**Validation**: A reader can follow the guide to detect and repair an isolated
missing projection using only supported commands.

### Subtask T009: Preserve architecture truth and validate prose

**Purpose**: Ensure the guide describes current and target authority boundaries
honestly.

**Steps**:

1. Label local skill files as generated compatibility projections.
2. State that the future runtime authority is the Aletheia-backed PolymorphDB
   contract, but do not claim it has landed in this recovery slice.
3. Run the documentation checks required by nearby guidance and the focused
   doctor command after WP01 evidence is available.
4. Review all commands, paths, and claims for copy/paste correctness.

**Files**: `docs/guides/diagnose-installation.md` (modify).

**Validation**: The guide contains no false canonical-authority claim, no
nonexistent command, and no manual mutation instruction.

## Definition of Done

- The operator guide explains the current lock/integrity distinction.
- It names only supported command paths validated in the local CLI.
- It tells operators to preserve custom skills and avoid hand-editing generated
  trees.
- It accurately separates current compatibility recovery from the planned PDB
  runtime-authority migration.
- Every subtask has a `spec-kitty agent tasks mark-status <Txxx> --status done`
  event after its evidence exists.

## Risks

- Do not describe project-local doctor success as proof of global host health.
- Do not revive the superseded absolute-symlink model.
- Do not make a runtime PDB claim until the cross-repository contract is real.

## Reviewer Guidance

- Execute every documented command or compare it to current CLI help.
- Check that operator actions are non-destructive to user-authored skills.
- Check that the target architecture is presented as target, not current fact.

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent codex
```
