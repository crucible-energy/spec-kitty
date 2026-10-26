---
title: Read canonical status from an owned lane planning checkout
description: Inspect a validated plain-LANES checkout without reading a stale primary copy or admitting implementation, mutation or coordinated status recovery.
type: explanation
doc_status: active
updated: '2026-10-26'
---

# Read canonical status from an owned lane planning checkout

## User Experience Findings

An existing plain-LANES mission could be inspected by `next`, but the status
command refused an explicit owned checkout. From that checkout, implicit
selection could instead report a stale same-identity mission in the repository
root checkout. This obscured the actual in-progress package and its owner gates.

## Engineering Decisions

Give the read-only status command its own supported topology set: single-branch
and plain LANES. Reuse the existing ownership validator, placement seam and
canonical event reducer. Do not broaden general lifecycle admission or workspace
constructors. Both explicit selection and cwd adoption read the selected task
board and events; the primary copy remains a diagnostic, never the status source.

```sh
spec-kitty agent tasks status --mission <handle> --owned-checkout <checkout> --json
```

An explicit checkout still requires a mission handle and the correct branch.
Coordination topologies remain refused by this command. Public CLI regression
tests use real linked Git checkouts, an active canonical event and a different
primary task board. They verify that both checkout and mission bytes are retained.

## Known Limitations

Inspection does not claim, resume, approve or migrate a work package. General
owned lifecycle mutation remains single-branch. A separate NEXT selection gap
still confuses planned-claim availability with active continuation; fixing it
must preserve actual actor, owner and lane workspace identity. An aggregate
dependency refusal does not establish that an already active package's own
dependencies are unsatisfied. No retained snapshot is adopted by this change.

Private validation resources are bounded and joined; logs, exact source pins,
red fixtures and recovery evidence are retained outside the checkout. This
source increment does not install a consumer runtime or authorize serving,
Store, model, permission or custody changes.

The broader owning check exposed an existing planning-pin hook fixture defect
(#130): an unqualified `python` command could be absent while the hook still
exited successfully without its intended mutation. Pin the fixture to the
running interpreter with shell-safe quoting and put a rejecting alias on PATH.
Keep every production guard and existing branch, index and retained-edit
assertion unchanged. The original failed aggregate remains a failed receipt;
the repaired fixture receives its own focused proof.
