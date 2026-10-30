---
title: Implementation log
description: Retained tooling friction for owned op custody.
doc_status: active
updated: '2026-10-24'
---

# Implementation log

## User Experience Findings

- A standalone command invoked from a feature worktree resolved canonical
  primary, wrote and closed its record there, then refused the main commit.
  The generated close instruction did not retain feature-checkout custody.
- Declared-lane cleanup exists separately. Its presence does not explain which
  externally created workspaces missed registration, completion or retirement.
- Shared Git configuration points to absent `.githooks`, while the installed
  commit guard remains in the common Git hooks directory. Use the existing
  guard through a command-scoped hooks path for delivery; do not alter shared
  configuration or bypass it.

## Engineering Decisions

- See [design decisions](design-decisions.md) and [acceptance](approach.md).
- Keep the repair independently owned and small; do not change global root
  discovery or carry an upstream import into the fork's older default branch.
- The initial reproduction's temporary-path equality assertion needed macOS
  symlink normalization. That corrected the fixture, not product behavior.
- Independent review identified protection bypasses, branch drift and close
  discovery from outside a repository. Four public-command regressions failed
  before the corrections. Durable branch custody and strict target policy
  address these cases without adding an override.
- The required baseline's retired-path failure was four ignored bytecode-only
  directories left by earlier source. Their 32 files were archived with
  verified hashes before clearing those exact directories. The unchanged
  baseline then passed; no test exclusion or gate change was used.

## Known Limitations

- Organization-wide lifecycle discovery/adapters and an actual completed
  workspace trace remain separate work. No active or unknown workspace is
  eligible for removal merely because it appears in an inventory.
- This command-level guard does not migrate historical primary records,
  redesign owned-record doctor/list discovery, or install the source globally.
- Deployment remains paused. Qualification of this tooling repair does not
  authorize production installation, service start or traffic promotion.
