# Data Model: Global Skill Projection Integrity

## Existing Entities

| Entity | Authority | Relevant fields / invariants |
|--------|-----------|------------------------------|
| `CanonicalSkill` | `SkillRegistry` | `name`, `skill_dir`, `all_files`; every file below the directory is package-owned source evidence. |
| Global skill root | Host configuration | One root per distinct installable agent path; may contain both managed and user-owned sibling directories. |
| Managed projection file | Global root | Relative path mirrors `CanonicalSkill.all_files`; `SKILL.md` is frontmatter-normalized; files are read-only after sync. |
| Version lock | `$SPEC_KITTY_HOME/cache/agent-skills.lock` | CLI version written after full successful sync; cache marker only. |
| Retired canonical name | `RETIRED_CANONICAL_SKILL_NAMES` | Explicit package-owned removal eligibility; no prefix inference. |

## Derived Integrity State

`ProjectionIntegrity` is computed, never persisted:

| Field | Meaning |
|-------|---------|
| `root` | The inspected distinct global root. |
| `complete` | Every canonical file has a readable counterpart with expected normalized content. |
| `failure_kind` | Missing, unreadable, or content mismatch; internal diagnostic only. |
| `affected_path` | First or collected relative managed path for logging/test evidence. |

No global manifest is introduced. The canonical registry and current files are
the input pair; integrity is a deterministic derived view.

## State Transitions

| From | Condition | To | Writer |
|------|-----------|----|--------|
| Unknown | Lock absent/wrong or any root incomplete | Recovering | `ensure_global_agent_skills` |
| Recovering | Every `_sync_skill_root` succeeds | Integral | Runtime writes the lock after all roots finish. |
| Recovering | Registry unavailable or a sync fails | Unverified | No new success lock; error remains visible. |
| Integral | Canonical file later disappears or diverges | Incomplete | Next bootstrap derives this state from registry comparison. |

## Ownership Rule

Only paths named by the active registry or explicit retired-name set are
package-managed. A neighboring path with a similar name is user-owned unless a
separate manifest or explicit managed-path contract proves otherwise.
