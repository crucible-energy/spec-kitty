---
title: Zig implementation language correction
description: Record the migration of repository language guidance to Zig, its validation, and remaining compatibility obligations.
doc_status: active
updated: '2026-10-26'
---

# Zig implementation language correction

## User Experience Findings

- Sam reported that sibling guidance lets new work land in Go instead of Zig.
- Spec Kitty's charter described Python 3.11+ as required for all CLI and
  library code, which would make an `AGENTS.md`-only Zig rule contradictory.

## Engineering Decisions

- Record Zig as the language for new repo-owned implementation in the charter
  interview answer, runtime charter directive and its local selection, curated
  charter, and agent guide.
- Keep the current Python CLI and PyPI release as a retained reference. Permit
  bounded Python repairs until a reviewed Zig replacement proves parity.
- Align the charter's interview answer and approval count with Sam's
  self-review rule; independent review remains optional, while validation and
  no-regression evidence remain required.

## Known Limitations

- This governance correction does not implement or validate a Zig CLI port.
- Existing Python test and release tooling remains necessary for retained code.
  The generated catalog still lists Python because the active CLI remains
  Python; the runtime language directive governs new implementation.
- The installed charter CLI resolved the primary checkout and lacked a selected
  doctrine toolguide. The repository-local runtime generated and validated the
  charter in this branch. The targeted terminology guard passed.
