# Research: Global Skill Projection Integrity

## Problem Evidence

The reported agent-host warning named a missing global
`spec-kitty-orchestrator-api-operator/SKILL.md`. The current global tree is
complete after a later installer run, but the former warning remains a valid
reproduction: a current `agent-skills.lock` can coexist with a missing managed
file.

`src/specify_cli/runtime/agent_skills.py::ensure_global_agent_skills()` currently
uses the installed CLI version as its fast-path condition. It checks only
whether a retired skill needs cleanup; it does not compare canonical registry
content to the global roots before returning. That is the direct failure seam.

## Existing Authority and Writers

| Surface | Current responsibility | Reuse decision |
|---------|------------------------|----------------|
| `SkillRegistry` | Discovers the package/local canonical doctrine skill directories and every owned file. | Canonical source for integrity comparison. |
| `_sync_skill_root` | Removes known obsolete package paths, copies each canonical directory, normalizes `SKILL.md`, and makes managed files read-only. | Canonical recovery writer; do not build a second writer. |
| `agent-skills.lock` | Records CLI version after a successful sync. | Retain as cache marker only; not an integrity authority. |
| `.agents/skills` and peer global roots | Host-readable generated compatibility projection. | Continue as derived state only. |
| `.kittify/skills-manifest.json` | Project-local installation snapshot. | Out of scope; do not repurpose as a global manifest. |

## Design Findings

1. A Skill includes referenced files as well as `SKILL.md`; a file-only probe
   would miss a partially copied package and violate the reported architecture's
   deterministic-verification requirement.
2. `_sync_skill_root` normalizes `SKILL.md` frontmatter after copy. The expected
   integrity bytes must use the same normalization or a healthy global tree may
   appear divergent on every run.
3. Global roots can contain user-owned skills. The current broad
   `spec-kitty-` name-prefix cleanup is insufficient ownership proof. Recovery
   must remove only explicitly retired package-owned names and preserve unknown
   directories.
4. Reusing complete-root sync on any mismatch is safer than patching one file:
   it has one writer, restores references, and leaves the lock update atomic at
   the outer successful-completion boundary.
5. A direct registry comparison is preferable to a new global manifest in this
   recovery slice. A manifest would duplicate the canonical source and could
   itself survive an interrupted update.

## Rejected Alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Trust the version lock indefinitely | It is the exact source of the false healthy state. |
| Check only `SKILL.md` | References and other package assets can still be missing. |
| Repair only the first missing file | Leaves unknown partial state and adds a second recovery writer. |
| Introduce a global manifest now | Duplicates authority and expands the migration before the incident is repaired. |
| Treat the global tree as canonical | Conflicts with the harvested architecture: static files are host compatibility projections, not runtime authority. |

## Cross-Repository Architecture Boundary

The harvested ChatGPT thread establishes this future topology:

```text
Technonomicon authored/versioned skills
          ↓ ingest and provenance
Aletheia-backed PolymorphDB runtime authority
          ↓ receipt-pinned compatibility projection
host-discoverable .agents/skills packages
          ↓ invocation evidence
Aletheia-backed PolymorphDB learning records
```

This mission only repairs the final projection arrow. It does not invent a
PolymorphDB endpoint or use the current static Aletheia JSONL export bridge as a
substitute for a runtime query contract.

## Validation Research

Focused tests must start with a current lock so the historical fast path is
exercised. Required controls are: missing `SKILL.md`, divergent referenced
file, healthy no-rewrite tree, custom neighbor preservation, and read-only
retired managed directory cleanup. The command-level smoke is
`spec-kitty doctor skills --json`; project-local doctor output is supplemental,
not proof that the global host root is complete.
