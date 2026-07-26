# Mission Specification: Global Skill Projection Integrity

**Mission Branch**: `fix/global-skill-projection-integrity`  
**Created**: 2026-07-26  
**Status**: Draft  
**Input**: An interrupted migration left a user-global managed skill projection
marked current even though a host could not load
`spec-kitty-orchestrator-api-operator/SKILL.md`. The deployment must recover
from incomplete or later-damaged global projections without making the static
projection an authority.

## Scope

This is the first, independently shippable recovery slice of the organization’s
agent/skill architecture. It hardens the generated global compatibility
projection used by hosts that discover `SKILL.md` files on disk.

It does not make static files canonical, add a PolymorphDB API, or alter a
user-authored skill. The follow-on cross-repository program will make the
Aletheia-backed PolymorphDB instance the runtime authority and will treat these
files as receipt-pinned compatibility projections.

## User Scenarios & Testing

### User Story 1 - Recover an interrupted global projection (Priority: P1)

An operator starts a supported agent after a prior global skill installation
was interrupted or a managed file was removed. The runtime detects that the
version lock is insufficient evidence of a complete projection, restores the
canonical managed files, and the agent can discover the missing skill.

**Why this priority**: A version lock that masks missing managed files makes
the user-facing agent surface unreliable and directly caused the reported
warning.

**Independent Test**: With a current version lock and a missing canonical
`SKILL.md`, run the bootstrap and verify the file is restored from the registry,
is read-only, and contains valid generated frontmatter.

**Acceptance Scenarios**:

1. **Given** a current global version lock and a missing managed `SKILL.md`,
   **When** global bootstrap runs, **Then** it re-projects the canonical skill
   tree and restores the missing file.
2. **Given** a complete global projection and a current version lock,
   **When** global bootstrap runs, **Then** it performs no managed-tree rewrite.
3. **Given** a current version lock and a stale or altered managed file,
   **When** global bootstrap runs, **Then** it restores the canonical content
   rather than trusting the lock alone.

---

### User Story 2 - Preserve user-owned skills during recovery (Priority: P1)

An operator has user-authored skills beside Spec Kitty-managed skills in the
same global root. Repairing a damaged managed projection never deletes,
rewrites, or changes permissions on those user-owned skills.

**Why this priority**: The repair surface shares host directories with
user-owned content. Recoverability cannot come at the cost of custom skills.

**Independent Test**: Seed a global root with a current lock, a damaged managed
skill, and an unrelated custom skill. After repair, the canonical file is
restored and the custom file is byte-identical.

**Acceptance Scenarios**:

1. **Given** a custom skill in a global skill root, **When** managed recovery
   runs, **Then** the custom skill remains untouched.
2. **Given** a retired package-owned skill and a custom skill, **When**
   recovery runs, **Then** only the retired package-owned path is removed.

---

### User Story 3 - Diagnose the actual projection state (Priority: P2)

An operator or support tool can distinguish an intact current projection from
a current-looking but incomplete one and receives a deterministic repair path
without manually copying files.

**Why this priority**: The prior version-only state made diagnosis misleading.
The recovery rule must be directly testable and explainable.

**Independent Test**: Focused unit tests prove the integrity predicate returns
false for a missing or content-divergent managed file and true only for a
complete canonical tree.

**Acceptance Scenarios**:

1. **Given** a global root with every canonical file at the expected hash,
   **When** the integrity predicate runs, **Then** it reports healthy.
2. **Given** one missing or divergent canonical file, **When** the predicate
   runs, **Then** it reports unhealthy and bootstrap performs recovery.

### Edge Cases

- A global root is absent or contains only user-owned skill directories.
- The canonical registry is unavailable; bootstrap must not claim a healthy
  projection or delete user-owned content.
- A managed skill directory or file is read-only when repair begins.
- A canonical skill contains files below `references/`; completeness covers
  every registry-owned file, not only `SKILL.md`.
- A process is interrupted during repair; the version lock is written only
  after successful synchronization, and the next bootstrap re-verifies the
  tree before skipping work.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Verify before skipping | The global bootstrap shall skip synchronization only when the installed CLI version matches the lock and every registry-owned global file exists with canonical content. | High | Open |
| FR-002 | Repair incomplete projection | When the version lock is current but any registry-owned global file is missing, divergent, or unreadable, bootstrap shall re-project the managed canonical skills before returning. | High | Open |
| FR-003 | Preserve user ownership | Recovery shall mutate only package-managed canonical or retired paths and shall preserve unrelated user-owned skills byte-for-byte. | High | Open |
| FR-004 | Cover all installable roots | Integrity verification and repair shall apply to every distinct user-global skill root used by installable supported agents, including the shared `.agents/skills` root. | High | Open |
| FR-005 | Preserve managed normalization | A recovered `SKILL.md` shall retain required generated frontmatter and read-only managed-file mode. | Medium | Open |
| FR-006 | Document recovery semantics | Operator documentation shall state that the global version lock is a cache marker, not a completeness guarantee, and identify the supported repair command. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Deterministic integrity | The integrity check shall produce the same result for unchanged registry and filesystem inputs and use content hashes for managed files. | Reliability | High | Open |
| NFR-002 | Bounded startup cost | For the bundled skill pack, a healthy-lock integrity check shall complete without copying files and within 500 ms in focused test measurement on the supported local fixture. | Performance | Medium | Open |
| NFR-003 | Cross-platform recovery | Focused tests shall cover a current lock plus missing file, divergent file, and read-only retired directory without platform-specific path assumptions. | Compatibility | High | Open |
| NFR-004 | Regression-proof behavior | The changed runtime module and its focused test surface shall pass `ruff`, `mypy --strict`, and targeted pytest with no newly introduced failures. | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical source boundary | Canonical skill source remains the packaged or local doctrine registry; generated global and project trees are projections and are never manually edited. | Architecture | High | Accepted |
| C-002 | Static compatibility boundary | This mission must not present static files as the long-term skill authority; the Aletheia-backed PolymorphDB runtime-authority contract is a separately planned cross-repository change. | Architecture | High | Accepted |
| C-003 | User customization boundary | Name heuristics alone do not prove ownership; cleanup must preserve any path not known to be package-managed or retired. | Safety | High | Accepted |
| C-004 | No silent degradation | Registry unavailability or recovery failure must remain observable; bootstrap must not write a success lock after an unsuccessful managed sync. | Reliability | High | Accepted |
| C-005 | No release change | This mission does not publish a package, modify CI, or change hosted service/credential authority. | Delivery | High | Accepted |

### Key Entities

- **Canonical skill registry**: The bundled or local doctrine-derived set of
  package-owned skill directories and files.
- **Global skill projection**: The read-only host-visible copy of canonical
  skills in a user-global root such as `.agents/skills`.
- **Version lock**: A cache marker recording the CLI version after a successful
  global synchronization; it is not independent proof of projection health.
- **Projection integrity predicate**: The deterministic comparison of every
  registry-owned file with the corresponding global projection path.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A focused test with a current lock and a missing
  `spec-kitty-orchestrator-api-operator/SKILL.md` restores that file on the next
  bootstrap invocation.
- **SC-002**: Focused tests cover missing, divergent, healthy, and
  user-owned-neighbor cases, with all assertions passing.
- **SC-003**: An intact projection with a current lock performs no sync rewrite
  while a damaged projection performs exactly one repair and writes the lock
  only after success.
- **SC-004**: The documented supported repair path restores a deliberately
  removed managed skill without manual copying and leaves an unrelated custom
  skill unchanged.
