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

### Bundled global-template replicas at initial HEAD 604c636

- **One canonical package source.** Actual selection stays with
  `resolve_configured_template`; its validated mission/filename is passed to
  `DoctrineService.resolve_package_default_asset_path`. Qualification requires
  the existing `MANAGED_DIRS` ownership declaration, exact global destination,
  a contained bundled source, regular non-link assets, and identical binary
  SHA-256 values. Neither directory naming nor an installer receipt proves it.
  Non-mission `GLOBAL` selections continue to refuse even with identical bytes.
- **Safe read provenance shares the existing seam.** The tightly necessary
  `asset_parent_states` extraction preserves `AssetPreparation.observe` behavior
  and its exact macOS `/var` and `/tmp` system-alias rule. New template reads
  validate ancestry, traverse held non-following directory descriptors, match
  the opened file identity, and verify identity again after reading. This avoids
  copying a second platform-alias policy or using general `Path.resolve()` to
  erase user-link evidence. Platforms without descriptor-safe traversal retain
  fail-closed global-template refusal; no weaker fallback is introduced.
- **Content authority and replica selection are distinct material facts.**
  `package:built-in` and `package:mission-assets` retain complete package content
  pins. `template-selection:<kind>` adds an opaque digest over exact mission,
  filename, package-relative source, bytes, replica location and stable
  filesystem identity. Its `path` is null; no global file is added to project
  Git staging. Package pinning uses the guarded reader for selected sources and
  must match the earlier observation; final source/replica rechecks couple the
  whole collection. Existing complete-key-set and transaction qualification
  checks remain mandatory.
- **Bootstrap repairs cannot silently revive a stale report.** Global file
  identity includes device/inode, mode, size, mtime and ctime; ancestor identity
  includes device/inode/mode. An equal-byte replacement, different HOME, or
  managed rewrite changes the selection digest. A subsequent root CLI may
  repair altered bytes, but that repair cannot recreate the recorded identity.
  Reports are therefore replica-local and must be regenerated after relocation
  or replacement. Package source pins remain content-based.
- **Directory membership is scoped correctly.** Immediate asset-directory
  metadata detects transient changes during a guarded read. Shared/system
  ancestor timestamps and unrelated sibling membership are not durable report
  material. An intermediate implementation over-pinned them and actually
  refused clean recordings during concurrent tests; the read-window guard and
  stable selection identity now have separate responsibilities.

The continuation's two-file strict check reports one unchanged baseline
`_entry` diagnostic at candidate line 202 / initial-HEAD line 199 and zero
introduced diagnostics. The older multi-file baseline counts below describe
earlier increments, not this continuation's validation surface. Independent
review and the operator's actual native recording remain pending.

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

## Renata template-provenance B1/B2 correction

- **B1 — classify ancestors without content.** `asset_parent_states` now calls
  `node_state(parent, read_content=False)`. Regular files and unsafe links refuse
  from their metadata before any byte reader can run, including a regular file
  replaced by an external link after its `lstat`. The leaf reader retains the
  existing non-following descriptor traversal and opened-file identity checks.
  The `node_state` documentation now names both metadata-only ancestry and lock
  classification rather than claiming that only lock files use this mode.
- **B2 — observation equality does not prove row membership.** Before each
  package traversal, `_package_inputs` derives the required proof paths confined
  to that canonical package root. It separately records paths that contribute
  rows after the guarded digest/identity comparison and refuses unless those
  sets match. Thus selected bundled sources cannot disappear from the
  `mission-assets` pin while leaving their endpoint observations unchanged.
  The same completeness check applies to the enclosing `built-in` pin. Required
  membership never depends on traversal results or current existence checks.
  Existing final source/replica observations still run after complete pinning.
- **Reproduction preserves source authority.** B2's test copies real package
  definitions into a temporary packaged layout and changes only the canonical
  ancestor-walk anchor input. Path, Mission definition and package-only template
  resolution execute their real bodies. The selected source subtree is actually
  renamed out during the real `rglob` iterator, then restored in `finally`.
  Its source observations remain equal; omission alone must refuse. No SDK asset
  subtree is moved or edited, and no successful manifest is substituted.

Both findings are addressed with red/green evidence; independent re-review is
still required. No mutable template tier, status source or gate is broadened.

## Repository source membership: ignored outputs are not implicit source

1. **Git owns exclusion, not cache names.** The narrowly necessary
   `kernel.git.listing.repository_ignored_paths` query uses NUL-delimited
   `ls-files --others --ignored --directory --exclude-per-directory=.gitignore`.
   It deliberately omits `--exclude-standard`. Only repository ignore policy
   can prune implicit untracked descendants; personal `core.excludesFile` and
   mutable `info/exclude` are not source authority. Inputs hidden only by those
   external policies remain material and the existing untracked-input dirt guard
   refuses recording. Changes to unused external excludes do not change source
   membership or become new external material dependencies.
2. **Explicit and tracked ownership wins.** The closure protects explicit roots
   and references, index/HEAD members, and their ancestors before pruning. An
   explicitly selected ignored directory retains its subtree. Tracked ignored
   source remains material, even after removal from the index. Missing tracked
   descendants receive missing-file sentinels so disk traversal cannot conceal
   dirty deletions. Nonignored untracked additions remain material and cannot
   acquire authority through a successful report transaction.
3. **Membership policy is itself material.** Relevant ancestor and visited-directory
   `.gitignore` files are included even outside the declared source subtree,
   with absent-file sentinels. Their content is subject to ordinary dirt checks.
   `git:source-membership` pins included-path HEAD/index membership, mode, stage
   and tag. It excludes blob IDs so mutable WP bookkeeping does not become a
   second content authority; the existing static WP-content hash remains canonical.
4. **One collection must be coherent.** A fresh Git membership observation and
   closure replay verify included paths, alias identity and membership after
   hashing. Policy hashes are checked again. Excluded output content, timestamps
   and incidental membership are never pinned. Failed, malformed, warning-bearing
   or unsupported Git/index classification refuses. Recognized non-Git library
   callers retain the original inclusive closure and receive no ignore pruning.
5. **Source guards precede policy use.** Root and tracked `.gitignore` paths are
   validated before the ignore query; user symlinks do not become policy sources.
   Visible source aliases retain exact tracked canonical-alias validation. An
   already-pruned generated directory is not traversed, including any link inside
   it. Explicit/tracked descendants prevent pruning and remain subject to the
   existing strict path and alias rules. Package pins and descriptor-safe global
   template proof are unaffected.

This changes the complete input key set: existing reports must be regenerated
under the corrected collector. Git redirection through `GIT_DIR`, `GIT_WORK_TREE`,
`GIT_INDEX_FILE` or `GIT_COMMON_DIR`, non-root collection inside a Git checkout,
and unsupported index flags/conflicts refuse rather than supply ambiguous source
membership. Independent review and actual native recording are still pending for
this continuation; the approved parent commit is preserved.

## B3 correction: separate selection policy from inventory

- **Live inventory is not an explicit-directory verdict.** With a tracked child,
  `ls-files --others --ignored --directory` returns ignored child files rather
  than the ignored directory. Inferring forced subtree retention from those
  records silently omitted explicit authority. Staged removal changed the record
  shape again, demonstrating that the old behavior depended on index membership.
- **Git still owns policy evaluation.** `repository_ignored_paths` adds
  `index_independent=True` for selection policy. That read-only query evaluates
  the same repository `.gitignore` rules with a private nonexistent index so
  tracked entries cannot suppress directory-policy records. It uses the original
  repository/worktree and never creates a checkout, copies Git metadata or edits
  ignore files. Temporary-directory ownership and cleanup are scoped to the call;
  tests verify real-index bytes and cleanup on success and failure.
- **The two views have distinct jobs.** `_SourceMembership.selection_policy`
  determines forced explicit subtrees in both closure passes and final replay.
  Its live `ignored` inventory continues to prune only implicit untracked
  descendants. Broad `docs`/`zig` authority therefore remains selective, while
  an explicitly selected ignored directory retains all authority children,
  including ignored uncommitted additions.
- **External policy is not promoted.** Both queries deliberately omit
  `--exclude-standard`. A direct effective `check-ignore` experiment showed
  `info/exclude` shadowing the repository child rule; that mechanism was not used
  as the fix. Local and global parent excludes cannot force the broad `zig` root
  or conceal explicit-child authority. No cache-name condition or dirt-guard
  exemption is introduced.

B3 is addressed with genuine red-first collector and root-CLI evidence. The
existing policy/membership snapshot and transaction rechecks remain mandatory;
independent re-review is pending and no fixing commit exists under the operator's
no-commit instruction.
