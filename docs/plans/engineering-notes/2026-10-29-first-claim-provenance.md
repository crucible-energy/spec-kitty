---
title: Conservative attribution and unknown origins
description: Preserve strict attribution fences and explain recovery when historical origin evidence is missing.
doc_status: active
updated: 2026-10-29
---

# Unknown origin is a recovery obligation, not attribution authority

## User experience findings

Partially stamped historical lanes can contain genuine earlier implementation
events without a recorded lane head. The first later stamped reclaim is a known
observation, not proof of creation. Calling it the first origin misleads operators
when strict reconciliation refuses older content.

## Engineering decisions

Keep the existing conservative attribution fence and the upstream dependent-lane
protections ported from `2db04ded1fd877041457b60f1a1109304be738a7` and
`3bde34db17ad841c86e6a9c26f8fdb29dd2457dd`. Returning an unknown fence instead
silently enables the legacy full-spine path and admits rejected dependency
content. A real-Git counterexample reproduces that regression even after the
current dependency is merged through a second parent. Approval and ancestry
cannot supply missing historical authorship.

The existing teardown gate now supplements an **already failing** unattributed
commit/blob result when the first genuine event lacks a stamp and failing
content occurs at or before a known later fence. It names the dependent code
lane, work packages, exact first event and later fence, and directs the mission
owner to preserve source, working state and history and recover genuine evidence
through the owning workflow. If evidence cannot be recovered, retain an explicit
blocked obligation and advance useful work through a genuinely governed,
validated and independently reviewed increment. Never manufacture an old event,
broaden attribution or treat this diagnostic as deletion authority.

The original verdict, divergence, rollback and teardown ordering remain intact.
A safe passing claim does not read the diagnostic event path and is not refused
just because old creation evidence is missing. The diagnostic grants no new
attestation or recovery mechanism. No new Python helper or schema is introduced.

Native regression controls exercise the actual collector and teardown gate with
real Git and canonical event reads. They preserve modern and conservative legacy
fences, migration filtering, independent-lane behavior, canceled and rewritten
dependency rejection, approved-content presence and exact branch/event state.
The failing early-content case and safe post-fence passing case share the same
missing-original-origin condition. The original gate fails the diagnostic test;
the corrected gate passes all ten native controls.

## Known limitations

The diagnostic does not reconstruct missing evidence, admit the historical
content, retry consolidation, change historical review warnings or recover a
vanished workspace's dirty/ignored state. It currently supplements commit/blob
attribution failures with a readable pre-mutation base; deletion-only failures
and unreadable optional evidence retain the existing strict failure guidance.
Other unrelated missing-approved-content failures are not relabeled.

Source native success is not installed receiving, full required-gate approval,
default-branch delivery or ordinary lifecycle adoption. The genuine whole-agent
launch/join/handback contract remains a separate prerequisite; all 121 last
verified repository adoption rows remain pending. Required validation and
independent installed receiving are recorded externally against the exact
candidate before publication. No original project, shared runtime or host
resource was changed to produce these controls.
