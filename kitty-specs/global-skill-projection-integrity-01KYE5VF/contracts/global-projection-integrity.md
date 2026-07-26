# Global Skill Projection Integrity Contract

## Purpose

Define the generated user-global skill projection contract used by file-based agent hosts. It is a compatibility contract, not a canonical knowledge or runtime-authority contract.

## Inputs

| Input | Authority | Required condition |
|-------|-----------|--------------------|
| Canonical skill registry | Bundled/local `SkillRegistry` | Discovers every package-owned skill and file. |
| Global root set | Supported-agent root resolver | Deduplicated paths are available for verification and recovery. |
| Version lock | Runtime cache | May be absent or stale; never replaces content verification. |

## Integrity Rule

For every canonical `skill.all_files` entry, the counterpart below each global root must exist, be readable, and hash to expected canonical bytes. Expected `SKILL.md` bytes include the same frontmatter normalization used by synchronization. A projection is integral only when every global root passes.

## State and Actions

| Condition | Action | Lock outcome |
|-----------|--------|--------------|
| Lock version differs or is absent | Synchronize every managed root. | Write current version only after all syncs succeed. |
| Lock is current and all roots are integral | Return without a managed-tree rewrite. | Preserve existing lock. |
| Lock is current and any file is missing, unreadable, or divergent | Synchronize every managed root. | Write current version only after all syncs succeed. |
| Registry unavailable or any sync fails | Surface failure and do not claim health. | Do not create or replace a success lock. |

## Ownership

- The active registry and explicit retired-name set identify package-managed paths.
- User-owned siblings remain untouched even when their names resemble a managed package.
- Recovery may remove only explicitly retired package-owned directories.
- Generated projection files are read-only after a successful synchronization.

## Non-goals

- No manual copying of individual skills.
- No project-local projection policy change.
- No PDB schema, endpoint, credential, or telemetry operation.
- No claim that disk projections are long-term authority; the future Aletheia-backed PolymorphDB contract owns versioned retrieval and invocation evidence.
