---
title: Restore pinned coordinated mission history
description: Recover retained status records into an explicitly Git-owned target checkout without advancing workflow or synthesizing approvals.
doc_status: active
updated: '2026-10-03'
---

# Restore pinned coordinated mission history

## Contract

`spec-kitty migrate restore-owned-mission-history` imports an existing mission's
historical status records into its explicitly selected target checkout. The
default is a read-only preview. `--apply` writes exactly these dossier artifacts:

- `status.events.jsonl`: the verified union of committed target and pinned logs;
- `status.json`: the supported decoder/reducer's derived projection;
- `history-restoration.json`: immutable commit/blob pins, SHA-256 fingerprints,
  source counts, projection additions, and output hashes.

The input mission must have an existing identity, coordinated topology (`coord`
or `lanes_with_coord`), target branch, and coordination branch. The caller and
selected checkout must belong to the same Git repository. The selected checkout
must be an exact registered root on its unprotected target branch.

This is **historical intake into the target checkout**, not coordination-branch
placement or runtime advancement. It preserves topology and branch refs. It does
not generate events, infer missing actor/model metadata, create execution
workspaces, assign lane bases, stamp `planning_commit_sha`, flip `status_phase`,
or qualify a retained approval as a current review or production proof.

## Preview and apply

Invoke from a checkout of the repository owning the mission. Resolve source refs
with `git rev-parse <ref>^{commit}` first; pass full lowercase commit SHAs, never
branch names, tags, or abbreviated hashes.

```bash
spec-kitty migrate restore-owned-mission-history \
  --mission "$MISSION" \
  --owned-checkout "$OWNED_CHECKOUT" \
  --source-commit "$TARGET_COMMIT" \
  --source-commit "$COORD_COMMIT" \
  --source-commit "$LANE_A_COMMIT" \
  --source-commit "$LANE_B_COMMIT" \
  --dry-run --json
```

Review `lanes`, `counts`, each source's `projection_additions`, and the pins/hashes.
When ready, use the same inputs with `--apply` instead of `--dry-run`. Inspect,
validate, and commit the three output artifacts through the repository's normal
delivery workflow. The command never stages or commits them itself.

An exact rerun is byte-stable, including after the output commit. An immediate
rerun accepts only the exact verified generated output dirt and writes nothing;
staged changes, unrelated dirt, or divergent outputs refuse. Ignored files are
preserved; a pre-existing divergent ignored output also refuses.

## Validation and provenance

All sources must contain regular-file `meta.json`, `status.events.jsonl`, and
`status.json` blobs at the selected relative dossier path. Identity, mission
type, topology, target branch, and coordination branch must match. Source logs
are strict UTF-8 JSON: duplicate keys, non-finite numbers, invalid records, and
conflicting lane chains fail closed.

Each pinned snapshot must match its supported replay by counts, lane values,
runtime values, and recorded review values. The only compatibility allowances
are the old unset display-number spelling and absent derived `review_result`
fields; review additions are reported explicitly. Retrospective projections and
mixed lifecycle/transition discriminator formats require their separate
contracts and are refused by this focused command.

Equal event IDs deduplicate only when the entire record is equivalent, including
evidence, structured actors, null metadata, and extension fields. Differing IDs
are retained. Conflicting duplicate IDs refuse before installation. Lifecycle
envelopes and annotations remain in the log; no historical approval is re-emitted.
The receipt pins the original blobs so exact old log bytes remain independently
retrievable with `git cat-file blob <blob-id>`.

Preview creates no lock or temporary files. Apply uses the canonical per-mission
status lock shared across Git worktrees and pins the checkout/ancestor/dossier
directory identities **before** its final locked plan. Staging, replacement,
rollback and cleanup all operate relative to the pinned dossier descriptor;
reopening the directory chain uses the existing coordination no-follow opener.
Every install step checks directory identity and destination bytes/inode metadata
before and after replacement. A late parent symlink cannot redirect writes into
another checkout.

Apply requires fd-relative `open`, `stat`, `rename` and `unlink`, `O_DIRECTORY`,
`O_NOFOLLOW`, and `fchmod` support (qualified on POSIX). Unsupported platforms,
including current Windows implementations, refuse apply before staging; there
is no pathname fallback. Read-only preview remains available.

Supported lane, annotation, lifecycle, decision and retrospective appenders, and
snapshot materialization, acquire the **same existing mission lock/key**. Another
thread/process waits until installation finishes, then appends against the new
log. Ordinary nested operations remain reentrant. A same-thread append during
staging may succeed, but destination-change detection then refuses restoration
without losing that record. During the short install/rollback phase, reentrant
writes raise a locking conflict instead of deadlocking or returning false success;
that conflict is latched even if an intermediate caller catches it.

POSIX `fork()` is a separate ownership boundary, not ordinary reentrance. A
child forked while any canonical status lock is active (including another parent
thread's lock or an acquisition/cleanup window) closes only its inherited native
descriptor copies, clears its copied thread/fence bookkeeping, and explicitly
refuses canonical status writes until it executes a fresh interpreter. Child
cleanup never calls `LOCK_UN`, unlinks the parent's lock file, or runs the parent's
release/fence-finally logic. The parent keeps its original state and native lock.
Idle forks and fresh-interpreter processes acquire their own native locks normally.

The directory transaction independently belongs to its **creator PID**. A forked
child continuing a copied install frame may unwind through ordinary exception and
finally handlers, but it never rolls back the parent's installed-image ledger or
unlinks the parent's staging files. Inherited directory operations refuse and
close only that child's descriptor copies. Repeated close is harmless; the creator
retains its directory descriptors, installed artifacts, temporary inodes and lock
until it completes or performs its own conditional rollback.

Modern filelock owns its native descriptor transitions, PID checks, and at-fork
cleanup. The CLI uses that public lock API unwrapped and never holds its own
mutex in a before-fork callback or across upstream acquire/release. Only the
CLI's process-local held-lock/fence state and explicit inherited-operation refusal
are maintained above it. This avoids reversed before-hook ordering deadlocking
an upstream transition that needs the CLI mutex.

For older supported filelock backends without the native fork/PID protocol, the
legacy descriptor guard and child-only close remain in use; native-to-soft backend
downgrades refuse rather than bypass that instrumentation. Protocol selection is
a bounded capability check, not a dependency pin. A PID fallback remains available
where `os.register_at_fork` is absent. Upstream may safely refuse `os.fork()` during
a native ownership change; that refusal must not be mistaken for a successful
fork or weakened to make a test pass.

Files are replaced atomically individually. An ordinary installation exception
rolls back only unchanged inodes installed by recovery; a later append/edit is
preserved and reported for inspection, never overwritten with the old snapshot.
Legacy bulk rewrites and raw file writes must not run concurrently with recovery:
the shared-lock serialization contract belongs to the supported writers listed
above, not arbitrary filesystem mutation.

## Known limits

The event log is installed last. This is not a filesystem-wide crash-atomic
three-file transaction: a process/host interruption can leave a stale snapshot
or receipt, which their hashes expose. Preserve that state for inspection; do
not force past the dirty-checkout refusal.

Native lock detachment alone is insufficient for copied install-frame unwind.
Use a wheel qualified with the creator-PID directory-transaction regression;
earlier recovery/coordination wheel qualification does not prove this correction.
The deterministic tests fork after an existing snapshot or new receipt is
installed, let the child fully unwind, and check parent output/staging identities,
native-lock retention and child-only descriptor closure before parent completion.

## Using this fork slice before release

Build a wheel from the validated **3.2.7 fork branch**, then run that artifact in
an isolated tool environment:

```bash
uv build --wheel --out-dir "$ARTIFACT_DIR"
# From the mission-owning repository, with WHEEL set to the built wheel:
uv run --no-project --with "$WHEEL" spec-kitty migrate \
  restore-owned-mission-history \
  --mission "$MISSION" --owned-checkout "$OWNED_CHECKOUT" \
  --source-commit "$TARGET_COMMIT" --source-commit "$COORD_COMMIT" \
  --source-commit "$LANE_A_COMMIT" --source-commit "$LANE_B_COMMIT" \
  --dry-run --json
```

Record the wheel hash and producing commit. A stock installed 3.2.7 does not
contain this fork command. Do not substitute a 4.x source-tree override: that
line requires a different events-package contract.

## Observed Subsequent intake boundary

The next explicit authority/query and real-review boundary is documented in
[owned coordinated authority](owned-coordinated-authority.md).

On 2026-10-03, the pinned target/coordination/lane histories for
`subsequent-progress-intake-01M204R7` reconstruct 53 records: 22 transitions,
21 annotations, and 10 lifecycle envelopes. Historical lanes are WP01 approved,
WP02 in review, WP03 planned. WP02's genuine review disposition remains a
dependency gate for WP03. Coordinated lifecycle routing, runtime-run recovery,
lane-base qualification, canonical registration/export, and consumer/production
acceptance are separate remaining obligations.
