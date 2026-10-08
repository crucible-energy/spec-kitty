---
title: 'Owned analysis and implementation: engineering decisions'
description: 'Rationale and assumptions for carrying validated checkout ownership through analysis transactions and guarded implementation.'
type: explanation
updated: '2026-10-08'
---

# Engineering Decisions — #5882

Audience: the independent SDK source reviewer.

1. **One ownership authority.** CLI inputs go through the existing shared
   `resolve_owned_or_refuse` seam with `LIFECYCLE_OWNED_TOPOLOGIES` (single_branch).
   Downstream paths carry the immutable `OwnedCheckout`; no second minter,
   persisted root hint or parallel workspace resolver is introduced.
2. **Both owned recording modes qualify a transaction.** Default mode first
   checks the owner for dirt, then uses the same report transaction as
   report-only mode. Placement, preflight and commit consume the fact; rendering,
   material closure, receipt directory and post-commit verification use the
   owner checkout. Ordinary default recording keeps its existing behavior.
3. **Charter hashing is explicitly owned-aware.** Rendering and freshness
   checking select the owner charter only when given the validated fact.
   Ordinary callers retain canonical-root charter hashing. Owned recording
   requires a charter. The existing material collector already accepts the
   write-checkout root correctly; the initial ownership fix needed no collector
   extension. The later tracked canonical-alias correction is described below.
4. **Reuse guarded implementation.** Owner admission selects the existing
   checkout/write branch and threads the fact through dependency, analysis,
   sparse, workspace, status, feedback, ancestry and commit paths. Write intent
   still requires invocation inside the owner checkout. There is no branch
   switch, worktree allocation or lane-tip merge for owned single_branch work.
5. **Preserve serialization and rollback.** The checkout claim lock is keyed on
   the owner checkout, before the existing common-Git-dir Mission lock. Scoped
   status transactions may commit the claim themselves. An unchanged follow-up
   router result is qualified against exact HEAD bytes and a stable HEAD before
   recording its receipt; it is not blindly accepted as a successful commit.
6. **Scoped charter context uses its selected authority.** The existing explicit
   `CharterScope` selects the owner charter for the implementation prompt;
   unscoped calls keep canonical-root behavior. A scope is not folded back to
   another checkout after selection.
7. **Feedback extends shared read context only.** The canonical review pointer
   reader forwards the fact to the existing owned-aware cycle-directory seam.
   Missing/invalid feedback still refuses, and valid owner-local feedback
   produces fix mode. Owned REVIEW admission and verdict policy are unchanged.
8. **B1: ownership requires qualification on every freshness read.** A canonical
   wrapper is not sufficient evidence of a successful owned recording. Owned
   reads require a transaction token and a qualifying receipt, then integer
   manifest version 1, the complete recomputed input-key set, and well-formed
   path/hash entries. Hash freshness still runs after structural validation.
   Missing fields cannot select legacy-only hashing. The non-owned V1 optional
   transaction/manifest contract and verdict policy retain their prior behavior.
   The canonical renderer stays available to prepare unqualified wrappers.
9. **Contained canonical directory aliases preserve one authority.** Native
   recording produced a real refusal on tracked `zig/docs -> ../docs`, whose
   canonical `docs` target was independently selected. The material collector
   now accepts only relative directory links committed as Git mode 120000 with
   exact matching HEAD blob bytes, terminating at an exact independently declared
   non-alias authority endpoint in the same root. Every intermediate component
   must stay inside the root and be a real directory, with no symlink ancestor or
   chain. Absolute, external, dangling, undeclared, untracked, dirty, cyclic and
   intermediate-escape references still refuse. Recursive graph cycles refuse
   rather than being silently deduplicated.
   Link spelling plus canonical target identity are hashed as an alias entry;
   canonical content and directory membership remain represented only under the
   canonical path. This retains the native link without dereferencing copies or
   narrowing the charter. Package symlink and external-pack guards are unchanged.
   No broader file-alias or alias-chain trust policy is admitted without separate
   concrete refusal evidence and policy resolution.
10. **B2: prerequisite validation precedes content resolution.** Deferred alias
    traversal must not defer checks on metadata or other inputs used to select
    templates. `_resolved_template_paths` strictly checks `meta.json` and every
    ancestor before `_mapping` reads it. The selected material closure is also
    validated before template-context resolution can read project/pack
    definitions; newly resolved template paths extend the same visited closure.
    Configuration and charter bootstrap checks remain before their own readers.
    This restores refusal-before-read ordering without changing alias eligibility
    or widening trust. External metadata links and linked Mission ancestors are
    tested with an observer that delegates the actual reader and records zero
    metadata content reads after refusal.

## Known Limitations

- The operator subsequently provisioned mypy and declared stubs in an ephemeral
  `uv --no-project` environment. The identical strict check now completes:
  candidate **13 errors / 4 files**, pinned unchanged base **26 errors / 6 files**.
  All 13 candidate findings match unchanged base statements and diagnostics;
  **zero introduced findings** were identified. The full strict gate remains
  honestly red, tracked in [#5917](https://github.com/spec-kitty/spec-kitty/issues/5917).
  No baseline source, ignore or suppression was changed. See the evidence ledger
  for exact commands and per-diagnostic attribution.
- The newly touched material collector has one additional unchanged baseline
  `no-any-return`: `_entry` returns the skipped-import artifact hash helper at
  current line 199 / pinned-base line 106 after B2. The identical narrow strict command
  reproduces it, with zero introduced findings. It is documented under #5917.
- No standalone Op or admitted WP could be opened safely in this lane with
  the current standalone dispatch placement. The explicit delegated scope and
  these tracers are the honest bootstrap record.
- Tests establish local behavior in the provisioned source environment. They
  do not establish merge, release, deployment or production qualification.
- Independent review and source delivery belong to the orchestrator. The operator
  committed/pushed the earlier repair as `e86a792e`; this agent's subsequent alias
  compatibility changes remain uncommitted, without push or PR publication.
