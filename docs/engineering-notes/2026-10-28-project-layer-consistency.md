---
title: Project-layer consistency and runtime admission
description: Preserve project policy while qualifying the assigned consistency-check repair.
doc_status: active
updated: '2026-10-28'
---

# Project-layer consistency and runtime admission

Owner: Cmail solo dependency recovery, `codex/issue-141-project-charter-consistency`.
Tracker: [issue 141](https://github.com/crucible-energy/spec-kitty/issues/141).

## User Experience Findings

The current published Spec Kitty release refuses this fork's legacy project
layout before opening a governed operation. Its supported upgrade moves the
project policy and refreshes managed surfaces. The first run completed the
migrations but refused a changed profile input during surface repair. A fresh
preview against those changed inputs followed by the supported command completed.
The first failure remains recorded; no input check was relaxed.

Generated YAML also carried trailing whitespace. Removing line-end spaces was
verified to preserve the parsed values before publication.

## Engineering Decisions

Use the current published `4.0.0rc7` executable in an isolated environment.
Preserve the fork's source version `3.2.8`; project admission is not a product
release. Canonical migration moved fourteen legacy artifact files byte for byte,
kept custom activation lists, retired obsolete built-in selections through their
documented successors and repaired five recorded topology values. It did not
approve any work package. Agent projections are managed outputs.

Keep this migration separate from the retained Python correctness repair.
That repair must pass resolved layer roots as data from the existing CLI caller;
the charter package must not import the higher CLI layer or add another scanner.
Preserve the behavior contract for eventual Zig parity.

## Validation

The second supported upgrade exited successfully. A genuine current-release
operation loaded the fork's governance. Strict charter preflight passed. Exact
commands, outcomes, source snapshots and resource custody remain in the owner's
external receipts. These results do not establish passing product tests.

## Known Limitations

The three consistency joins still need failing-first CLI tests, implementation,
owning test suites, static checks and review. The fork's retained source layout
and the current published release's layout differ; source delivery, release and
Cmail runtime adoption require separate evidence. No upstream publication is
authorized by the fork issue. The old source refs, private development runtime,
retained metadata and shared object alternate remain protected until their
owning recovery obligations close.
