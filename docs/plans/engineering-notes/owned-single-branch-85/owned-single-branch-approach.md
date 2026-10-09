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
