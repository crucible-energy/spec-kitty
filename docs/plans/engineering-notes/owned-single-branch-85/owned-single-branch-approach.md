---
title: 'Explicit owned single-branch recovery: approach'
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
