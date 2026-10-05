---
title: Submit and claim an owned review
description: Explicit review handoff on registered coordination authority, using immutable code evidence, canonical gates, and independent identities.
doc_status: active
updated: '2026-10-04'
---

# Submit and claim an owned review

## Current boundary

These are narrow status operations on the same authority established by
[owned coordinated recovery](owned-coordinated-authority.md):

```text
in_progress --submit-owned-review--> for_review
for_review  --claim-owned-review---> in_review
in_review   --review-owned---------> approved / in_progress
```

`review-owned` still requires `in_review`. Submission and claim do not approve,
issue a runtime step, acquire/reassign a process lease, allocate a workspace or
select a dependent base. Default lifecycle commands keep their existing behavior.

Every invocation explicitly names the registered checkout on its declared
coordination branch. The clean/inactive ownership, recovery-anchor, immutable
planning/history and creator-PID IO rules remain in force. Dirty/staged work,
foreign or hidden authority, live recorded leases and issued runtime steps refuse.

## Evidence and identities

Supply the actual known implementer and, at claim, the actual independent reviewer.
The command records those identities; it does not authenticate a human or infer
an agent profile/model from the text. For this parent workstream the supplied
labels are `node-norris/OpenCode independent implementation` and
`reviewer-renata/OpenCode independent AI`. Existing historical codex, null and
unknown bindings remain in the immutable log and untouched runtime slots.

`--code-commit` is a full immutable commit in the same repository. Its dossier
identity and authored WP-owned regular-file paths must match the selected mission.
`--reference` must be an HTTPS GitHub commit URL matching that code pin and the
repository's `origin`. This verifies the URL's local object/repository binding,
not network reachability, publication permissions or reviewer authentication.

Optional `--scope-proof` identifies a tracked regular blob at that code pin.
The event records its path, Git blob ID and SHA-256 as **opaque operator evidence**.
It is not converted into a successful test run, aggregate approval or synthesized
gate receipt. Preserve a tracked receipt's actual scoped-pass/baseline-blocked
distinction and provide the actual independent review reference later.

## Submit after actual implementation qualification

From the mission-owning repository:

```bash
spec-kitty agent status submit-owned-review \
  --mission "$MISSION" --owned-checkout "$COORD_CHECKOUT" --wp-id WP02 \
  --implementer 'node-norris/OpenCode independent implementation' \
  --code-commit "$CODE_PIN" --reference "$PUBLIC_CODE_COMMIT_URL" \
  --scope-proof data/benchmarks/cross-repo-memory-verification.json \
  --json
# Inspect preview, then add --apply. Commit/push the two status outputs on coord.
```

Preview reads and validates evidence but does not execute tests or write outputs.
The FSM uses the canonical authored subtask roster and event-sourced completion,
plus existing implementation evidence; it never sets completion to true from a
CLI flag or a raw tasks.md checkbox. An incomplete roster blocks submission.

Pre-review bindings resolve through the existing mission-type/doctrine resolver,
named handler registry, scope-source factory, baseline reader and verdict
aggregator. An optional uncovered edge is explicitly reported as `no_coverage`;
it is never labeled green. The owned door exposes no force or gate-disable flag.

For an active gate, supply `--code-checkout "$EXISTING_CODE_CHECKOUT"` if code is
not already at the coordination checkout's HEAD. That code checkout must already
be registered, clean, inactive, unprotected and at the exact immutable code pin.
It must carry the same committed gate configuration as the status authority;
hidden index flags cannot qualify test inputs. No extra worktree is created and
the command never switches either checkout.

Apply runs the actual configured gate against that code checkout. A captured
baseline must be a committed regular blob for the same WP; the command does not
capture or invent a baseline. Gate-created dirt is preserved and causes refusal.
Required `review.fail_on_pre_review_regression` policy is conservatively enforced
at this owned door: missing coverage, unknown baseline, mismatched scope or any
remaining failure blocks submission. A baseline failure can therefore remain
explicitly blocking even when a scoped regression run has no *new* failures.
The output always says `aggregate_approval=false`.

## Claim the submitted review

After committing/pushing submission:

```bash
spec-kitty agent status claim-owned-review \
  --mission "$MISSION" --owned-checkout "$COORD_CHECKOUT" --wp-id WP02 \
  --implementer 'node-norris/OpenCode independent implementation' \
  --reviewer 'reviewer-renata/OpenCode independent AI' \
  --code-commit "$CODE_PIN" --reference "$PUBLIC_CODE_COMMIT_URL" --json
# Add --apply only for the actual claim, then commit/push its status outputs.
```

Claim requires the current owned submission, matching implementer/code pin and a
reviewer distinct from recorded implementation/submission identities. The canonical
`for_review -> in_review` FSM edge is used with force disabled. Queued submission
is not itself a reviewer lease; historical runtime metadata is preserved rather
than overwritten to manufacture a claim.

After actual independent review, use the existing `review-owned` command with
the same claimed reviewer/code pin and its real verdict/reference. A different
reviewer or changed code pin cannot silently use that claim to approve.

## Idempotence and known limits

An exact committed request retry returns `changed=false`, `applied=false`, with
the recorded event and current lane; it never rolls status back to an earlier
phase. Different requests must satisfy the current phase/claim guards. Generated
event IDs may not collide with any retained transition, annotation or lifecycle ID.

Apply revalidates under the existing shared mission lock and binds install and
cleanup to creator-owned directory descriptors. A stale checkout/ref or directory
refuses; other-owner changes are preserved. Status log/snapshot replacement retains
the existing conditional-rollback and host-crash limitations, not a new filesystem
transaction guarantee. A test runner may create files; they are not swept away.

The commands require a genuine coordination checkout. If the parent is currently
on the code lane, the parent owns any existing-slot branch switch before invoking
the status commands. An active gate also needs an already available pinned code
checkout; absence is an explicit blocker, not permission to run older coord code.

Owned next remains query-only. Reviewer prompt/issuance, advancing the blocked DAG,
canonical allocation, planning-pin/base qualification and WP03 slot reuse remain
separate next seams. Handoff does not establish canonical export or consumer/
production acceptance.
