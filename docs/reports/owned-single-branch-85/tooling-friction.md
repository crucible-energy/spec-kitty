---
title: 'Explicit owned single-branch recovery: tooling friction'
type: explanation
audience: software-engineer
updated: '2026-10-09'
---

Observed: existing `backfill-topology --restamp-single-branch` chooses the repository
root checkout and converts legacy code lanes to `lanes`; owned lifecycle commands
deliberately support `single_branch`. That remedy does not recover this owner.

Observed: dispatch has no owned checkout option. Only its non-mutating resolver was
used; the delegated issue/tracers are the bootstrap record, not an invented Op.

Observed: a dedicated frozen-lock SDK environment was provisioned in this checkout.
The first acceptance run was interrupted during slow collection; no RED proof was
claimed from that interrupted attempt. Full output and startup sample were retained.
