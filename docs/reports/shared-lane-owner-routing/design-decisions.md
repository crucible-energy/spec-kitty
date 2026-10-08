---
doc_status: active
updated: '2026-10-08'
---

# Engineering decisions

- Finalized lanes own membership and exact mission/lane/branch/path identity.
  Canonical status owns which member is active. A membership mismatch refuses
  ownership with a specific diagnostic until supported action reentry refreshes it.
- One owner operation validates identity before ancestry work and refreshes only
  current WP, complete members and dependencies after success. Base/creation,
  branch/path and environment provenance are retained. Missing context remains
  missing for the existing recovery lifecycle; no new provenance is fabricated.
- Dirty in-flight work remains protected by the existing reentry/ancestry contract.
  Allocator reuse retains its distinct clean-workspace check for a new package.
- Explicit checkout is propagated only from the opted-in owner boundary. WP cache
  identity uses the actual resolved task directory, preventing same-slug or
  flagless-worktree cache entries from crossing into an explicitly selected root.
- A selected single-branch checkout remains the WP execution workspace. No child
  lane is guessed or allocated. Completion/review instructions retain supported
  explicit-checkout lifecycle flags; this is not authority to approve work.
- The source policy is three checkouts and three active non-default streams.
  Five owner checkouts already existed. Dirty repository-root and two dirty lanes,
  plus unrelated closure work, were preserved. We reused this chat's clean PR67
  checkout on a new branch; PR67 local/remote refs and evidence remain fixed.
  Conservatively counting the preserved dirty repository-root and two dirty
  lanes as active, this repair is a temporary fourth stream under the parent's
  explicit necessary-owner-repair authorization. It is a bounded exception, not permission inferred
  from an absent config knob. No checkout was added or another owner evicted;
  the parent/operator owns post-delivery branch/workspace disposition.

- Modern status transitions commit event records rather than WP frontmatter. The
  existing owned admission resolver already checks the finalized planning commit
  as an actual ancestor distinct from HEAD. That resolver is extracted once into
  the existing lane review-gate leaf and consumed by both transition and prompt
  code. Unknown/invalid current owned authority refuses; it never falls back to
  historical commit markers. The retained flagless renderer fallback is tested
  as historical compatibility with its workspace-resolution port supplied.
- Copied commands quote checkout paths, pathspecs and revision ranges. Tests use
  actual spaced paths/files and run the displayed scoped diff: the reviewed file
  is included and unrelated concurrent work is excluded.
- Strict checking exposed one pre-existing Any return in the owned pre-review
  workspace projection, reproduced against the immutable base. Its known Path
  field now uses the module's existing annotated-local idiom. No runtime coercion,
  cast, check suppression or relaxed configuration was introduced.

- Explicit-owned merge is a separate single-branch completion leaf. The ordinary
  lane executor and flagless location guard retain their existing behavior.
  Completion has no branch-consolidation effects, never retargets the mission,
  preserves refs/worktrees, and binds a present local target commit. Remote PR
  delivery and generic birth-number/audit/retrospective gates remain separate.
- The existing status batch retains its same-WP default. Owned completion opts
  into distinct unforced DONE requests and a read-only precondition rechecked
  under the existing mission lock. Every request uses the canonical preparation
  guard, and all events share the transaction's commit/rollback unit. No reviewer
  is synthesized: the event-sourced `review_result` supplies actual approval.
- Local acceptance custody is not external issuer authentication. Only the
  producer's bounded acceptance record/residual shape is admitted; metadata,
  criterion/verification inputs and canonical review history stay bound. Later
  substantive drift refuses even on a clean target branch.
