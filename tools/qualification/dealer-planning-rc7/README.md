# Isolated planning acceptance repair for published rc7

This directory preserves an inert, complete source patch for the published
`spec-kitty-cli 4.0.0rc7` archive. It adds no CI, installer, activation, hook or
shared-runtime change. The fork default branch remains a separate 3.2.8 source
line; applying these 4.x source files directly to that line is unsupported.

Use `dealer-planning-rc7.patch` only on a fresh verified released archive:
SHA256 `91e98774b7a69a273f9146656482e1e2bddd274a2178dfc6ac9c1f3bcede0c80`,
release source `1b0fe9fc388b095f9964471b0177b4213e9c6c98`.
The patch reports the honest private version
`4.0.0rc7+crucible.dealerrecovery.2`; it does not borrow unpublished rc8 identity.
`qualification.json` pins every port, pack file, product file, patch and proof.
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
runtime. `owned-acceptance-context.patch` shows the final incremental correction:
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
uv venv --python python3.11 "$OUTPUT/venv"
uv pip install --python "$OUTPUT/venv/bin/python" --constraint "$CONSTRAINTS" .
"$OUTPUT/venv/bin/spec-kitty" --version
```

`ASSETS` is this reviewed asset directory, `OUTPUT` is a new owner-scoped external
build directory, and `CONSTRAINTS` contains the supplier-pinned dependencies from
a verified published rc7 runtime, excluding the CLI distribution itself. Retain
the archive, constraints, complete output, wheel, executable/source hashes and
installed dependency identities. Do not replace shared environments or use a
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
