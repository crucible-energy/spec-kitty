# Implementation Plan: Global Skill Projection Integrity

**Branch**: `fix/global-skill-projection-integrity` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)
**Input**: Interrupted global skill projection migration, the missing `spec-kitty-orchestrator-api-operator/SKILL.md` warning, and the harvested Technonomicon architecture record.

## Summary

Treat `agent-skills.lock` as a cache marker rather than proof that a user-global skill projection is usable. When the lock version is current, resolve the canonical `SkillRegistry`, compare every registry-owned projected file in every distinct global skill root with expected normalized content, and skip only if all comparisons pass. A missing, divergent, or unreadable managed file triggers the existing complete managed-root synchronizer. The version lock is written only after every root synchronizes successfully.

This creates a reliable compatibility projection for hosts that can only discover on-disk `SKILL.md` packages. It does not claim that static files are canonical: the Aletheia-backed PolymorphDB runtime-authority design remains a separately governed cross-repository program.

## Planning Decisions

| Decision | Resolution | Evidence |
|----------|------------|----------|
| Integrity scope | Verify every registry-owned file, including `references/`, rather than `SKILL.md` alone. | `01KYE5YK94DW10SSX2H55CKNS1`: a Skill is the complete registry-owned artifact and must be deterministically verified. |
| Recovery granularity | Synchronize the complete managed root when one managed file fails integrity. | `01KYE5YM2CXZYNJ0MF1XY66PD2`: the existing synchronizer is the canonical writer and does not leave partial repair state. |
| Health state | Compare directly with the canonical registry; add no global projection manifest. | `01KYE5YMW4WEH1G43A02H50CRT`: a manifest would duplicate authority and introduce another recovery surface. |

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Existing `SkillRegistry`, `ensure_skill_frontmatter`, global-root resolver, runtime lock helpers, and standard-library hashing  
**Storage**: Existing generated global roots and `$SPEC_KITTY_HOME/cache/agent-skills.lock`; no new schema  
**Testing**: Targeted `pytest tests/runtime/test_agent_skills.py`, then `ruff` and `mypy --strict` on changed files  
**Target Platform**: Linux, macOS, and Windows 10+  
**Project Type**: Python CLI/runtime package  
**Performance Goals**: Healthy current-lock verification under 500 ms on the focused local fixture; no copy when every root is integral  
**Constraints**: Preserve user-owned skills; no release, CI, hosted-service, credential, or direct-main change  
**Scale/Scope**: Current bundled doctrine skill pack across all distinct installable user-global roots

## Charter Check

| Gate | Result | Rationale |
|------|--------|-----------|
| Single canonical authority | PASS | The registry remains canonical; lock and local trees are derived state. |
| User customization preservation | PASS | Unknown skill directories are preserved; removal requires explicit retired package ownership. |
| ATDD-first | PASS | The implementation begins with a current-lock missing-file regression test. |
| Cross-platform | PASS | Uses existing `pathlib` and read-only recovery conventions. |
| Branch discipline | PASS | Named branch only; no publication to `origin/main`. |

## Project Structure

```text
src/specify_cli/runtime/agent_skills.py       global bootstrap, integrity predicate, safe sync
tests/runtime/test_agent_skills.py            red-to-green recovery coverage
docs/guides/diagnose-installation.md          operator diagnosis and recovery semantics
kitty-specs/global-skill-projection-integrity-01KYE5VF/
  spec.md, plan.md, research.md, data-model.md, quickstart.md, contracts/, tasks/
```

This mission changes one existing runtime module, its focused tests, and one operator guide. It adds no package or long-lived state layer.

## Design

### Failure being removed

`ensure_global_agent_skills()` currently returns early when the cached version equals the installed CLI version. Apart from retired-skill cleanup, it does not prove managed file presence or equality. An interrupted migration or later deletion can therefore produce a current-looking lock beside an invalid tree that the agent host reports as a skipped or missing skill.

### Integrity predicate

Add small private helpers in `runtime/agent_skills.py`:

1. Enumerate every `CanonicalSkill` and every member of `skill.all_files`.
2. For `SKILL.md`, normalize canonical source text with `ensure_skill_frontmatter` exactly as the existing synchronizer does; use canonical bytes directly for other files.
3. Compare a deterministic content hash of those expected bytes to the counterpart file in a supplied global root.
4. Return unhealthy for a missing, unreadable, or mismatched counterpart; do not convert an `OSError` into a healthy result.

The current-version short circuit obtains the registry first and returns only if every distinct root passes. Registry unavailability or a failed copy must not write a fresh success lock; the existing logger must retain the failure context.

### Recovery and ownership

An unhealthy root calls the existing `_sync_skill_root(root, registry)`, which copies the complete managed tree, applies `SKILL.md` frontmatter, and removes write bits. The existing lock write stays after all roots complete.

Tighten cleanup so it removes only names in the explicit retired package-owned set. It must not delete an unknown sibling merely because its name resembles `spec-kitty-*`; name shape is not ownership evidence.

```text
current version lock + all roots integral  -> no rewrite
lock absent/wrong OR any root not integral -> canonical complete-root sync
successful complete sync                  -> write current lock
sync failure                              -> no new success lock; visible error path
```

## Implementation Concern Map

### IC-01 — Global projection integrity

- **Purpose**: Gate the version-lock skip path on registry-owned file integrity.
- **Requirements**: FR-001, FR-002, FR-004, FR-005; NFR-001, NFR-002.
- **Surfaces**: `src/specify_cli/runtime/agent_skills.py`.
- **Risks**: `SKILL.md` normalization must be included in expected bytes or a healthy tree would be re-copied indefinitely.

### IC-02 — Ownership-safe synchronization

- **Purpose**: Recover managed content without broad name-based deletion.
- **Requirements**: FR-002, FR-003, FR-005; C-003, C-004.
- **Surfaces**: `src/specify_cli/runtime/agent_skills.py`.
- **Depends on**: IC-01.
- **Risks**: Explicit retired package names still require cleanup; unrelated custom skills must stay byte-identical.

### IC-03 — Regression proof

- **Purpose**: Pin the reported missing-file incident and prove healthy current-lock behavior stays non-mutating.
- **Requirements**: FR-001 through FR-005; NFR-003, NFR-004.
- **Surfaces**: `tests/runtime/test_agent_skills.py`.
- **Depends on**: Tests are committed red before IC-01 and IC-02 implementation.
- **Risks**: Tests must exercise current lock, missing file, divergent file, custom neighbor, and read-only path cases.

### IC-04 — Operator guidance

- **Purpose**: Explain that a lock is not integrity proof and name the supported repair flow.
- **Requirements**: FR-006, SC-004.
- **Surfaces**: `docs/guides/diagnose-installation.md`.
- **Depends on**: IC-01 through IC-03.
- **Risks**: Must call generated local trees compatibility projections, not canonical runtime skill authority.

## Validation Plan

1. Add a focused red test with a current lock and a deleted `spec-kitty-orchestrator-api-operator/SKILL.md` equivalent before runtime code changes.
2. Prove the implementation restores missing and divergent files in every distinct global root and preserves a user-owned neighbor unchanged.
3. Prove an intact current-lock tree makes no copy call and preserves the cache marker.
4. Run `pytest tests/runtime/test_agent_skills.py`.
5. Run `ruff check src/specify_cli/runtime/agent_skills.py tests/runtime/test_agent_skills.py` and `mypy --strict src/specify_cli/runtime/agent_skills.py`.
6. Run `spec-kitty doctor skills --json` after an isolated disposable projection-recovery exercise and verify the restored skill is discovered without manual copying.

## Complexity Tracking

No charter exception is needed. Keep the integrity check as small pure enumeration and byte-comparison helpers; extract rather than allowing either helper to cross the complexity ceiling.
