---
title: Retained status query reconciliation
description: Explain why split coordination queries with retained history and no canonical WP state withhold progress until their existing owner verifies reconciliation.
type: explanation
doc_status: active
updated: '2026-10-26'
---

# Retained status query reconciliation

## User Experience Findings

Issue #60 has a second software boundary after retained runtime preview:
the canonical coordination home can contain no WP state while the selected
task-board home retains history. Real registered Git fixtures reproduced
`no actionable wp` and zero classified lanes rather than identifying that
reconciliation gap. This is not evidence that the retained work never happened.

The initial fixture attempts failed before reaching the query because their
coordination worktree lacked its Mission directory. Those setup failures are
retained separately from the subsequent two failing query assertions. Creating
the disposable fixture's real status home exposes the actual query defect.

## Engineering Decisions

Extend the existing shared task/status consistency check, not the placement
resolver or canonical event reader. Read canonical WP state first. Only when
it is absent or empty, the status and task-board homes differ, and retained
event bytes exist, return `retained_status_reconciliation_required`. The query
then uses its existing blocked-query envelope with null progress and no preview
step. The advancing board uses the same consistency refusal.

Presence of retained bytes is a reason to inspect, never authority to reduce
them as current state. Current canonical WP state wins. Empty retained history
preserves the existing genesis path. Invalid retained bytes stay preserved and
unadopted; invalid canonical history keeps the existing visible reader error.
Six real Git cases exercise those boundaries and verify unchanged content,
heads and staged entries across primary, owned and sibling checkouts.

The owning surface then exposed two existing real-Git retry failures:
deliberately empty sibling `commondir` fixtures report `Result too large` on
this Mac. The classifier recognized only `Success` and `Undefined error: 0`,
so it refused without allowing the simulated sibling to finish. Issue
[#124](https://github.com/crucible-energy/spec-kitty/issues/124) records the
failed run, exact source identity and separate installed baseline classifier
probe. The lifecycle owner confirmed no competing retry edit.

Recognize that additional observed diagnostic only for a registry `commondir`
path and exit 128. This permits the existing bounded retry, not success or
repair: persistent failure still rethrows the exact error after twenty attempts.
Permission errors, unrelated paths and checkout directories stay non-retryable.
The retry change is directly connected to the owning gate and belongs in this
existing lane; no global prune, forced reattachment or new recovery writer is
introduced.

## Known Limitations

This is a consistency refusal, not a migration or approval reconstruction.
It neither adopts retained status nor changes lifecycle write capabilities,
`status_phase`, consumer installations or the live coordination store. A
partially populated canonical board is not compared against retained history
by this narrow check; exact reconciliation remains the existing owner's work.
It makes no freshness, authority, current consumer recovery or default-branch
delivery claim. HELD/v5 and all Source, Store, model and host boundaries remain
unchanged.

The underlying reason this Git executable chose that errno wording is not
established. The tested failure mechanism is the classifier rejecting the
actual zero-byte-fixture diagnostic. The earlier 83-pass/two-failure owning
result and subsequent one-failure classifier reproduction remain failures,
not passes or waivers. A nonempty permanently broken registry can also emit
this wording; it receives only the bounded retry and still refuses unless Git
itself can read the registry successfully.

The red-test commit's formatting check reported a required reformat before the
commit command continued. The formatting defect was corrected in the source
increment; final format, lint and relevant gates must validate the frozen
candidate. That earlier check is not recorded as passing.

The first hosted architectural fast gate caught this increment importing the
event filename directly from the internal status store. The constant already
exists on the public status interface, so route the import through that existing
export. No public symbol, exception, allowlist, threshold or boundary test is
changed. The failed hosted result remains retained; the named status-boundary
gate and affected source qualifications must validate the corrected candidate.

Private qualification reuse first stopped before installation because the prior
exclusive installation log already existed. The subsequent probe correctly
rejected the unchanged old version; its six behavioral passes are not new-version
proof. Preserve those failures and the original log, resume the exact prepared
wheel with a distinct installation receipt, and verify that all pinned dependency
versions remain unchanged before qualifying the new subject.
