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

The repair passes the canonical root map from the CLI through availability,
compiled-catalog parity, graph parity, activation filtering and tension scanning.
A missing map had also silently removed valid project nodes and tension findings.
No scanner, resolver, schema or upward package import is added. Existing callers
retain the default argument and behavior.

Actual CLI tests were committed while failing, before implementation. They cover
valid directive/styleguide bodies with a compiled catalog and graph, missing and
malformed bodies, missing IDs, catalog divergence, missing graph nodes and
advisory tension findings. Explicit root selection is exercised from another
working directory. An overlapping organization artifact with a different
canonical ID must not displace the selected project artifact.

The broader first run exposed missing local distribution metadata and legacy
consumer fixtures coupled to the maintainer's newly migrated policy. Installing
the reviewed local project without changing dependencies fixes the environment.
The four implicated fixture modules passed against actual base `e851d756` in the
same environment. Their corrected cases use minimal retained-consumer settings,
the canonical shipped default for an absent activation, and an independent
tracked synthetic repository for read-only rendering. Positive assertions and
explicit-empty behavior are preserved. The affected cases pass after correction.
Freeze these inputs before the full owning suites and required static gates. The fork's retained source layout
and the current published release's layout differ; source delivery, release and
Cmail runtime adoption require separate evidence. No upstream publication is
authorized by the fork issue. The old source refs, private development runtime,
retained metadata and shared object alternate remain protected until their
owning recovery obligations close.
