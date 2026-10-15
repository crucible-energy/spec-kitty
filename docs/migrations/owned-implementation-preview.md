# Preview an existing owned implementation slot

Use this bounded query after [owned coordination recovery](owned-coordinated-authority.md)
and actual independent dependency review. It checks an existing registered code
checkout; it does not create a worktree, grant admission, or start implementation.

```bash
spec-kitty migrate preview-owned-implementation \
  --mission "$MISSION" --owned-checkout "$STATUS_CHECKOUT" --wp-id WP03 \
  --code-checkout "$EXISTING_CODE_CHECKOUT" --code-commit "$FULL_CODE_SHA" \
  --dependency-pin "WP01=$ACTUAL_REVIEWED_SHA" \
  --dependency-pin "WP02=$ACTUAL_REVIEWED_SHA" --json
```

Supply exactly the desired WP's declared dependencies. Pins must be full,
lowercase immutable commit IDs. The code checkout must be the already declared
lane on its exact requested HEAD: clean, registered, inactive, and in the same
repository. Planning, authored prompts, canonical status and the declared roster
must agree. Hidden index entries, active processes or issued runtime steps refuse
proof. A dependency's latest actual approval must bind its exact WP, code pin,
independent reviewer and recorded request; a proposed pin or prose review link
cannot supply a missing machine binding.

A successful result has `kind=owned_implementation_preview`, `proof_ready=true`
and **`admitted=false`**. It reports real Git roots, refs, immutable object/blob
identities, planning ancestry and dependency review bindings. `counts` describes
the pinned target history, not later coordination events. `base_qualified=false`
and null profile/tool/model bindings remain explicit. These checks validate
recorded facts; they do not authenticate a reviewer or perform the actual review.

Exit 1 returns a precise refusal with `proof_ready=false`, `admitted=false` and
all effect flags false. There is no apply mode. Project checkouts, Git objects,
status, runtime progress and lane allocations remain untouched. The ordinary
root CLI can initialize or refresh its global runtime and agent commands under
HOME; repository purity does not claim an unchanged HOME on first use.

The proof is an observation, not a lock or an admission token. Live refs, files
and activity are checked again before return. Immutable object reads are reused
only inside that query, with bounded entries and independent metadata copies;
mutable refs, worktree files and process checks are never cached. The context is
cleared on success or refusal. Subsequent allocation or execution requires the
owning workflow's fresh admission, lane-base qualification and runtime checks.
