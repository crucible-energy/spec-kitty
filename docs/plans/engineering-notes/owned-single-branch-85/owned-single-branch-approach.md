---
title: 'Explicit owned single-branch recovery: approach'
description: 'Records delegated scope, governance context and the initial failing acceptance test for explicit recovery of one archived legacy code lane.'
type: explanation
audience: software-engineer
doc_status: point_in_time
updated: '2026-10-09'
---

Issue: https://github.com/crucible-energy/spec-kitty/issues/85. Parent-approved
scope: one independently owned SDK checkout, `codex/owned-single-branch-recovery`,
based on `1fbdfe965cb8c7c16b07e79664bd5b282154d126`. Python Pedro was resolved
through the supported profile CLI; implementation follows the source charter.
The existing dispatch was run with `--dry-run`: it resolves the profile but has
no owned checkout support, so no Op was claimed or opened on a protected checkout.
The assigned issue and delegated implementation scope are the truthful work record.

RED first: the real migration subgroup acceptance fixture requests an explicit
`owned-single-branch` conversion. It includes five code WPs, an archived raw status
stream and distinct historical/current source trees. Ordinary finalization must
remain fail-closed before explicit conversion and succeed afterward without refresh.

Complete local check output lives in an independently owned external release-receipt
store, outside the candidate. Exact locations are recorded in the external receipts.
Source review, PR publication and consumer qualification belong to the parent.

## Preserved source successor

The strict source slice merged through
https://github.com/crucible-energy/spec-kitty/pull/86. Actual consumer qualification
then correctly refused two scoped historical output changes. The owner selected a
separate `preserved_unapplied` custody contract on the same issue: retain every raw
version and ref while leaving current source untouched. This does not establish
absorption, generation, freshness or independent implementation approval.

Outside-in acceptance now starts through the actual root CLI. Its fixture has five
code WPs, two regular scoped projection modifications, a two-parent historical
merge and separate current source versions. The schema-1 control must refuse with
zero effects; explicit schema-2 custody must account for every commit and parent
edge before preview or conversion. The initial root acceptance reproduced RED;
source implementation and successor qualification are pending.

Implementation uses the existing canonical Git entry/tree queries and closed
typed custody models. Every parent edge is reconstructed before manifest equality
and raw byte verification. Root CLI counterexamples cover incomplete/extra census,
privacy, raw corruption, unsafe paths, active history, races and repeat/rollback.
Hidden merges and intermediate reverts require their actual raw variants even when
the final historical tree is unchanged. Full successor qualification remains an
external receipt so recording its outcome cannot change the frozen candidate.

## Hosted boundary correction

Observed: source candidate `c663dcf` passed its recorded local source, baseline,
owning and documentation gates, then the hosted checks on
https://github.com/crucible-energy/spec-kitty/pull/87 exposed two additional
boundaries. The existing DRG discovery gate rejected model serialization over
the custody parent-edge collection. An imported disposable-repository helper
also inherited the real workflow's non-main PR event, even though that fixture
deliberately has no configured remote. The two named counterfactuals reproduced
RED; the full external logs remain tied to the original source.

The correction compares original wire history only after duplicate-key rejection
and strict closed-model validation. Git evidence has no DRG serialization policy.
The shared recovery helper declares its temporary local fixture context and
restores the real hosted context after its checks. Real PR identity and archive
preservation guards remain unchanged. Revised-source qualification stays external.

## Local qualification boundaries

Observed: complete upgrade qualification of the correction for
https://github.com/crucible-energy/spec-kitty/pull/87 exposed detached fixture
setup maintenance: Git 2.55 changed `.git/objects` and its maintenance lock
after the read-only before-snapshot. The same three notice counterfactuals
passed with per-invocation synchronous maintenance and unchanged complete
filesystem snapshots. Global and repository-user settings remain untouched.

The complete canonical run then passed 1,210 cases and skipped two, with one
240-second timeout during a healthy full-corpus control audit. That integrated
case performs eleven independent public CLI audits plus preservation checks;
its serial call took 236.57 seconds. A finite 600-second marker applies only to
this case. Every assertion, full-corpus membership check, attack and healthy
control remains, as does the 180-second limit on each CLI call. The default
240-second authority remains unchanged. Targeted and complete qualification
of this test change remains pending in the external receipt store.
