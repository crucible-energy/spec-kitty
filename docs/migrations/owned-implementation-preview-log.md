---
title: Owned implementation preview closeout
description: Record implementation-preview ownership decisions, validation results, and remaining admission and cleanup limitations.
doc_status: active
updated: '2026-10-26'
---

# Owned implementation preview closeout

Owner: Sam's workspace closeout, Codex Root. Existing
`fix/owned-implementation-admission` lane in the retained recovery checkout.
This independent log follows [Kaizen's mission log procedure](https://github.com/crucible-energy/kaizen/blob/4ca2672d97ffe34d9a7d9a4df3d6f8b6c93c8b51/docs/mission-log-procedure.md).

## User Experience Findings

2026-10-15: PR 63 delivered the historical recovery and authority repair. The
same checkout retained an interrupted implementation preview: one original red
acceptance commit and four dirty/untracked prototype files. Exact bundles,
index, binary patch, untracked archive and stash preserve those original bytes.
Resume them here without creating another checkout or competing workstream.

Self-review found the prototype returned `admitted=true` while declaring no
allocation or runtime effects, null execution bindings and no base qualification.
The actual root CLI fails the corrected acceptance contract before repair.
A usable proof must never impersonate canonical admission.

## Engineering Decisions

Finish this retained Python contract and safety repair using the existing
implementation, canonical authority resolver and public status APIs. This is not
a new Python stack; new implementation remains subject to the Zig directive.
Rebase only the saved prototype test commit onto the actual merged PR 63 result;
retain all original source and recovery artifacts. Keep Sam's self-review and
direct proof policy; Blacksmith and CodeRabbit are not dependencies.

Return `proof_ready=true`, `admitted=false` and an explicit preview kind. Preserve
all no-effect flags and missing bindings. On refusal both readiness and admission
are false. Human output says preview and does not claim an admitted lane.

Reuse planning ancestry and target-history counts computed by the canonical
resolver, without substituting later coordination counts. Route status reads
through its public facade. Reuse immutable Git blobs only for full commit IDs in
one request-scoped context; retain fresh mutable authority, code-slot, index,
working-file and activity checks. Copy returned metadata and reset the context
on refusal. Bound retained cache entries. Real Git tests cover HEAD movement,
metadata isolation, refusal reset and rechecking in a subsequent query.

## Validation and Findings

The original positive acceptance fails without the command. The restored
prototype independently fails the corrected false-admission contract before
implementation. Initial strict typing and lint pass after public API repairs;
iteration and frozen-source results are retained externally with exact input
hashes. Interrupted runs remain partial receipts, never completed passes.

The retained fixture has three WPs and two dependencies. An initial configured
full CLI measurement takes 5.93 seconds. Profiling identifies repeated immutable
Git reads. Initial HOME setup additionally renders global agent commands, so its
cost is recorded separately; it is not a comparable speedup baseline. After bounded object reuse and removal of redundant immutable planning reads,
the configured full native CLI measures 1.93 seconds on the same fixture and
toolchain. First-use HOME bootstrap takes 7.31 seconds and remains separate.
This is one observed configuration, not a percentile or universal latency
guarantee. All intermediate over-budget receipts remain preserved.

## Known Limitations

This proof does not qualify a lane base, authenticate reviewers, allocate a lane,
issue a prompt, acquire an execution lease or advance a runtime DAG. Concurrent
changes after return remain possible. No canonical admission or production
qualification is claimed. Root startup can initialize global HOME assets.
Existing main failures remain honestly recorded under issue 107; this scoped
change must add no unexplained regression. No universal absence of future bugs
is asserted. Exact final receipts, PR result and post-merge cleanup belong to the
external closeout record so recording a gate does not change its candidate.
