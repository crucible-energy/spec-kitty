---
affected_files: []
cycle_number: 1
mission_slug: organization-workspace-lifecycle-01M5DRAR
reproduction_command:
reviewed_at: '2026-10-24T21:32:23Z'
reviewer_agent: reviewer-renata
wp_id: WP08
---

# WP08 independent review — changes requested

Reviewer: Lynn mission coordinator, Reviewer Renata role
Source: f131e0df2fb66f73f22489d7ad73f26f866b93f452fd5c1c337ae0982c636687
Evidence: lifecycle-wp08-independent-review.json

## Finding 1: Record publishes unreadable/non-private-mode history under restrictive umask

Initialize a0700 store with umask077; record with umask0200; record exits0 but finish.json is0400; subsequent status refuses PrivateFileRequired.

Set and verify required metadata on the newly owned descriptor before publication (or fail safely without replacing incumbent). Add real restrictive-umask record/reopen regression; never chmod an existing untrusted file.

## Finding 2: Missing persisted header/history fields are accepted as initialized empty history

After a real initialized revision1, replace only owned fixture finish.json with{} at0600. status exits0 revision0/events[], and record expected_revision0 succeeds, despite absence of mandatory schema/revision/events.

Require all persisted envelope fields through a dedicated mandatory wire shape or explicit presence validation; reject incomplete history before any write. Keep internal convenient initialization separate. Do not claim cryptographic rollback detection beyond that.
