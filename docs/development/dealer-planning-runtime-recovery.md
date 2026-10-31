---
title: Planning runtime recovery and owned acceptance
description: Build the isolated published-release planning repair and verify owned acceptance without changing customer authorization gates.
doc_status: active
updated: "2026-10-30"
type: reference
---

# Isolated planning acceptance repair for published rc7

The [qualification assets](../../tools/qualification/dealer-planning-rc7/) preserve an inert, complete source patch for the published
`spec-kitty-cli 4.0.0rc7` archive. It adds no CI, installer, activation, hook or
shared-runtime change. The fork default branch remains a separate 3.2.8 source
line; applying these 4.x source files directly to that line is unsupported.

The earlier planning and software layers below are historical source inputs,
not admission for an uncontained CLI invocation. Use the complete private
consumer closure and mandatory contained launch before invoking any SDK.

Use `dealer-planning-rc7.patch` only on a fresh verified released archive:
SHA256 `91e98774b7a69a273f9146656482e1e2bddd274a2178dfc6ac9c1f3bcede0c80`,
release source `1b0fe9fc388b095f9964471b0177b4213e9c6c98`.
The patch reports the honest private version
`4.0.0rc7+crucible.dealerrecovery.2`; it does not borrow unpublished rc8 identity.
[qualification.json](../../tools/qualification/dealer-planning-rc7/qualification.json) pins every port, pack file, product file, patch and proof.
The original source formats remain preserved inside the unified diff.

## Correction and authority

The bounded source closure provides the existing startup/custody fixes, planning
profile defaults, four canonical plan contracts, their matching expected-artifact
manifest, and non-WP acceptance with its canonical kernel dependency. The pack
bytes come from `spec-kitty-open-packs@af1c370f34601f2aa00d45a7a9597ab8d6a46ea1`.

Actual receiving then found a context propagation defect: a completed plan in a
linked owned checkout fell back to WP checks. The read-only runtime resolver
used the generic identity seam, which folds the linked checkout into the
repository-root checkout. That checkout had no mission, so acceptance found no
runtime. [owned-acceptance-context.patch](../../tools/qualification/dealer-planning-rc7/owned-acceptance-context.patch) shows the final incremental correction:
thread the already validated `OwnedCheckout` into the read-only resolver and
reuse the existing `_run_mission_id` authority. Non-owned callers retain their
previous behavior. The complete patch already includes this increment.

No runtime index or frozen state is rewritten. No dummy WPs, lanes, acceptance
waivers or lenient flags are added. A real WP continues through ordinary WP gates.
Standalone Op custody and broad agent-asset isolation are outside this closure;
use explicit owned-mission commands only. Customer authorization, contracts and
multiple human approvals remain prerequisites to any target access or testing.

## Build and validation

Follow the isolated archive/constraints/environment pattern pinned at
`crucible-energy/spec-kitty@c2c6c15f5b44565128ae1b0bf1bea0b9dfad1727:tools/qualification/`.
Do not run that other recipe's unrelated analysis patch. Against a new extracted
archive, inspect and apply this patch without fuzz:

```sh
patch --dry-run --batch --fuzz=0 -p1 -i "$ASSETS/dealer-planning-rc7.patch"
patch --batch --fuzz=0 -p1 -i "$ASSETS/dealer-planning-rc7.patch"
patch --batch --fuzz=0 -p1 -i "$ASSETS/owned-software-rc7.patch"
patch --batch --fuzz=0 -p1 -i "$ASSETS/consumer-assets-rc7.patch"
uv venv --python python3.11 "$OUTPUT/venv"
uv pip install --python "$OUTPUT/venv/bin/python" --constraint "$CONSTRAINTS" .
SPEC_KITTY_ASSET_SCOPE=consumer SPEC_KITTY_HOME="$CONSUMER_HOME" \
PATH="$OUTPUT/venv/bin:$PATH" \
/usr/bin/sandbox-exec -f "$DENY_PROFILE" \
  "$OUTPUT/venv/bin/spec-kitty" --version
```

`ASSETS` is the reviewed `tools/qualification/dealer-planning-rc7/` directory,
`OUTPUT` is a new owner-scoped external
build directory, and `CONSTRAINTS` contains the supplier-pinned dependencies from
a verified published rc7 runtime, excluding the CLI distribution itself. Retain
the archive, constraints, complete output, wheel, executable/source hashes and
installed dependency identities. `CONSUMER_HOME` is an absolute owner-scoped
private runtime root; `DENY_PROFILE` is the separately verified, owner-held OS
policy described below. Keep the real `HOME` unchanged. Do not replace shared environments or use a
bare cached PATH executable. An applying owner must repeat relevant receiving
and source gates for their exact toolchain and dependency context.

The recorded corrective candidate passed the canonical release `make test-fast`
(2318 passed, 5 skipped), 295 focused planning/acceptance/startup/kernel tests, and
source-locked Ruff 0.15.12 on the final two touched source files. Missing sdist
source-gate inputs were restored byte-for-byte from the released Git commit;
no assertion or ignore list was weakened. A later canonical plan-composition
module needs a post-rc7 activation-ledger API; it was not falsely reported green.
Actual installed public CLI controls cover the receiving boundary instead.

The real CLI fixture used a ULID mission created by the CLI, a completed frozen
four-step plan, a distinct repository-root checkout with no copy of the mission,
and a genuine linked checkout holding the mission. Correction.1 reproduced the
WP fallback. Correction.2 accepted the completed plan; each missing required
artifact and an unfinished canonical WP refused acceptance. Earlier receiving
also proved unfinished review and frozen-template tampering refuse acceptance.
This corrects the earlier overbroad claim that repository-root fixture proof
qualified linked owned acceptance.

Strict typing is **not green**: with the declared YAML stubs and supplier pins,
14 transitive diagnostics are byte-identical in correction.1 and correction.2.
They concern existing event payload construction and Any returns in three
unchanged files. [Issue 147](https://github.com/crucible-energy/spec-kitty/issues/147)
tracks that source obligation. No type diagnostic was suppressed. These assets
record bounded receiving proof, not full release or production qualification.

## Bounded owned software increment

Apply [owned-software-rc7.patch](../../tools/qualification/dealer-planning-rc7/owned-software-rc7.patch)
after the complete planning patch to obtain the separately identified
`4.0.0rc7+crucible.dealerrecovery.3` candidate. Its
[structured proof](../../tools/qualification/dealer-planning-rc7/owned-software-qualification.json)
retains the exact source/installed identities and actual controls. Published
latest non-yanked resolution remained `4.0.0rc7` at 2026-10-31T02:29:53Z.

This increment reuses four necessary hunks of the existing owning-analysis
recipe: bind currency to the validated owned root, use the existing qualified
transaction for ordinary owned recording, and check that transaction's own Git
operation markers. Other status callers retain their conservative shared-root
check. Single-branch admission is unchanged; the recipe's unrelated plain-lanes
expansion and the later charter-root extension are deliberately excluded.

Admission requires **both** repository-root and owned project canonical charter
directories and YAML/Markdown files to be absent, rechecked before actual use.
A newly present canonical charter requires a separately qualified successor.
This proof does not establish general canonical-charter adoption.

The corrected installed CLI recorded structured ready analysis and issued
implementation for a real ULID mission in a genuine linked checkout. The prior
build rejected that same report transaction. Each changed planning input and a
tampered transaction receipt redirected execution to analysis. An owned Git
operation refused recording before write; an unrelated repository-root operation
marker remained untouched and did not block owner-local recording.

Supported `next`, owned `mark-status` and `move-task` completed planned → doing
→ for_review → in_review → approved, with a durable review verdict. Unfinished
subtasks and missing committed owned implementation both refused review. The
fixture inherited its validator code before planning; its later real in-scope
documentation increment proves lifecycle handling, not new code implementation.
Its pre-review test command was undeclared and explicitly nonblocking/skipped by
the existing runtime; no force/skip flag or configuration change was used.

The final source passed 93 focused analysis/transaction tests, canonical
`make test-fast` (2318 passed, 5 skipped), and Ruff for all four changed modules.
Strict mypy output is byte-identical to the prior candidate; unchanged transitive
type errors remain visible under issue 147. The private published-archive-derived
build, source asset delivery, release and actual consumer acceptance stay distinct.

## Mandatory private consumer containment

The separately identified `4.0.0rc7+crucible.dealerrecovery.4` adds the exact
six-file consumer-routing closure from accepted source
`c9f90a3a7f67176608f2284316a7a290c6688d86`, also present in the independent
Phoenix-qualified `60d1168` source. Apply
[consumer-assets-rc7.patch](../../tools/qualification/dealer-planning-rc7/consumer-assets-rc7.patch)
after the first two layers. The
[contained qualification](../../tools/qualification/dealer-planning-rc7/consumer-assets-qualification.json)
binds all 20 product source/installed identities, the wheel and exact proof.

Every SDK entry, including version/profile/Git callbacks, requires consumer
scope and an absolute private `SPEC_KITTY_HOME` before interpreter startup.
Generated commands and skills route below its `agent-assets/` child. Keep real
`HOME` unchanged; do not redirect an editor's native configuration. Pin the
qualified executable's directory first in `PATH` for bare Git callbacks.
Repeat those bindings and the OS deny on every Git operation that can invoke
such a callback. An unprefixed executable or default user scope is not admitted.
A changed consumer root requires a fresh analysis report; do not edit a report
or frozen state to conceal changed template custody.

This macOS receiving used an exact owner-held copy of the existing profile,
SHA256 `3d0c18f367f092f37cd201c846917bd3d3cb0f74c40063f8d3bf9e26834a92c8`.
It denies read/write/exec on the three shared native command/skill roots.
The profile remains an external receipt, not a new repository enforcement rule.
No shared Git configuration, workflow, protection or native asset rollback was
changed. This is observed macOS containment, not a claim of deployed cross-platform
isolation or automatic native-editor discovery of private skills.

The earlier uncontained corrective SDK replaced 14 native command files. That
incident is retained. A broad subsequent observation window also found eight
unassigned equal-byte inode/mtime replacements; their actor remains unknown.
A fresh bounded window spanning private version/profile/report/review and Git
callbacks observed all 279 native nodes unchanged. The OS-denial proof and
physical observations remain distinct; no other producer was stopped or undone.

All seven driver entrypoints passed 13 authored positive/refusal cases, and a
real Git merge invoked the pinned bare SDK callback. A fresh CLI-created mission
completed its full supported local review lifecycle with the same `codex` actor
and an explicit Sam-authorized self-review note; its approval verdict persisted
durably. No independent reviewer is claimed. A backward transition without a
required feedback artifact refused and was repeated through the supported
feedback-file path, without force or status editing.

The final contained source passed 179 focused tests, `make test-fast`
(2318 passed, 5 skipped), Ruff and strict mypy for all six consumer-routing
modules. The initial installer failures were the exact already-fixed issue 73
fixture inconsistency; its canonical capability-metadata patch is preserved in
[consumer-assets-test-fixture.patch](../../tools/qualification/dealer-planning-rc7/consumer-assets-test-fixture.patch).
Assertions and production no-follow protections remain unchanged. The first
fast run supplied an explicit home override to a test asserting no override;
the corrected launcher restores that declared test context under the same OS
deny. Both red receipts remain retained. These are diagnosed corrections, not
skipped cases or a repeat-until-green claim.

The owned acceptance-verdict criterion writer and post-merge ledger closeout
are not qualified by this increment. Actual receiving found that the retained
criterion CLI lacks owned placement propagation. Approval and delivered PR
evidence must not be represented as a completed acceptance matrix or done
ledger; a separately isolated corrective increment is required. Do not edit
matrix JSON or event logs to bypass these missing supported surfaces.

## Owned criterion authoring and acceptance increment

[owned-criterion-rc7.patch](../../tools/qualification/dealer-planning-rc7/owned-criterion-rc7.patch)
adds the separately qualified fifth increment on the private consumer layer.
Its canonical ownership closure comes from `a6f8add16f` and `c3d26bd566`:
the CLI validates the checkout once, carries that fact through matrix placement
and the shared locked writer, and classifies explicit WP execution modes from
the owned checkout. A code WP cannot disappear into planning-only matrix skips.
Ordinary and coordination routes, lock refusal and negative-invariant integrity
remain covered. The distribution honestly identifies its local `.5` repair.

Criterion mode also accepts explicit `--description` and `--notes` updates.
Use the actual requirement definition and verification findings to replace
scaffold prose through this command; do not hand-edit matrix JSON. Omitted
metadata remains unchanged. Identical row state, including both metadata fields,
produces no timestamp or commit change. Row identifiers and sibling criteria or
negative invariants remain intact. Evidence must bind the actual reviewed source
and checks; a pass records the named actor's judgement, not an authority grant.

The [qualification record](../../tools/qualification/dealer-planning-rc7/owned-criterion-qualification.json)
pins all 23 matching product/installed identities and the complete delta.
The [test patch](../../tools/qualification/dealer-planning-rc7/owned-criterion-tests.patch)
retains canonical owner-only, concurrency, negative, lock and stale-copy controls.
Final gates passed 68 focused tests, `make test-fast` (2318 passed, 5 skipped)
and Ruff. Strict types show zero new errors against the identical baseline's
single existing Any-return error. Interrupted and failing intermediate evidence
is retained with its diagnosis; no cases or assertions were skipped to qualify.

Actual installed linked-checkout controls showed all-pass acceptance with zero
skipped checks; pending and failed criteria refused. Unknown rows, foreign claims
and a held mission lock refused without changing matrix bytes or HEAD. A valid
all-pass matrix still refused a planned WP. Primary HEAD and status stayed
unchanged. The fixture inherits its code; this is runtime routing proof, while
the parent mission owns actual implementation verification. Both canonical R/P
charters must freshly remain absent before receiving. Use a distinct private
consumer home for this increment, preserving every live earlier consumer.

The broad native observation has nine metadata changes by an unknown actor.
It is not an unchanged-world claim; enforced producer isolation remains separate.
Owned post-merge `done` recording is still unsupported in published rc7 and is
tracked by an active owner in [issue 49](https://github.com/crucible-energy/spec-kitty/issues/49).
PR delivery, acceptance and ledger completion remain separate facts. Never use
raw events, forced transitions or primary checkout writes to simulate closeout.

## Mission creation admission

For a new mission, invoke the explicitly addressed runtime from the actual
repository-root checkout and pass the linked checkout via `--owned-checkout`.
The retained create command passes its located project root directly to the
ownership minter; invoking create from inside the linked checkout treats that
checkout as the repository root and correctly refuses the self-claim. Root-CWD
explicit admission validates the real repository-root-to-linked relationship and
runs startup gates on the validated linked checkout. Preserve and recheck the
repository-root HEAD and work state around creation. This supported invocation
requires no metadata, frozen-state or shared-installation changes.

## Delivery and closeout

Owner: the dealer-security-modernization-01M67NQS runtime recovery task,
coordinated with its parent mission owner. Build source, installed runtime,
private synthetic fixture histories and all failed/passing logs remain external
for actual Phalanx receiving. The active consumer runtime must remain available
until its owner releases it. After this asset PR merges, fetch and verify its
actual default-branch delivery, recheck the isolated asset lane's cleanliness,
refs, nested state and active users, then retire only that eligible lane through
Git. This asset commit, installing a runtime, source publication, upstream release,
and successful customer operation remain separate facts.
