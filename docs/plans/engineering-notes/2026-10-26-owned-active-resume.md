---
title: Resume an existing work package through canonical ownership
description: Separate planned claim discovery from same-owner active continuation without changing claims, workspace admission or event history.
type: explanation
doc_status: active
updated: '2026-10-26'
---

# Resume an existing work package through canonical ownership

## User Experience Findings

A finalized mission could report implementation in progress while NEXT emitted
no work package and a dependency refusal. The remaining planned package depended
on an already active package; it did not prevent that package's owner from
continuing. Query and step mapping were incorrectly using planned-only discovery
for both new claims and existing work.

## Engineering Decisions

Keep planned-only auto-claim discovery unchanged. Add one implementation preview
used by finalized-board query and step selection. Preserve dependency-ready new-claim
priority. If no new claim is available, select claimed or in-progress work only
for its canonical implementer of record, using the existing tool-scoped actor
comparison. Missing, generic, other or anonymous ownership does not select an
active package. Structured actor identity remains unchanged in the event log.

Read planning and status through the selected placement contract. Never adopt
cached status or stale primary events. Selection appends no event and does not
repeat claim-time dependency gates for already active work. Unreadable history
refuses selection. Thread the actual requester through both fresh-board and
pre-persist advance resolution, so query and step do not disagree about owner.

## Known Limitations

Selection does not claim, reassign, approve, construct a workspace, grant access
or admit execution. Existing profile, branch, workspace and mutation gates still
apply. Direct owned lifecycle commands remain separately restricted. Synthetic
conformance tests do not establish a downstream producer, Store or model grant.
No runtime installation, canonical status transition or held-data change is
part of this source increment. Validation resources are private and bounded;
retain their terminal receipts, failures and fixtures outside the checkout.

The original owning run retained 1,007 passes, three skips and two failures:
corrupt history reached dependency metadata before a named refusal, and an
existing query test expected the old generic active-work reason. Read canonical
history first; retain the planned-only token assertion while checking the more
specific NEXT owner refusal. The corrected owning run passed 1,009 checks with
three skips. The original failed receipt remains retained, not relabeled green.
