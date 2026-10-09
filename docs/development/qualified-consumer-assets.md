---
title: 'Isolate assets for a pinned CLI consumer'
description: 'Give a qualified consumer its own generated assets without changing native agent configuration.'
doc_status: draft
audience: docs/context/audience/internal/maintainer.md
type: how-to
updated: '2026-10-09'
---

# Isolate assets for a pinned CLI consumer

Audience: operators qualifying a source-pinned CLI alongside another installed
Spec Kitty version. This source candidate adds an explicit consumer asset scope;
it does not upgrade an installed CLI or qualify a consumer automatically.

Use the same pinned executable and a dedicated absolute runtime directory for
every command in the consumer's lifetime:

```sh
SPEC_KITTY_ASSET_SCOPE=consumer \
SPEC_KITTY_HOME="/absolute/private/consumer-runtime" \
/path/to/pinned/spec-kitty agent mission record-analysis \
  --mission <mission-handle> --owned-checkout <checkout> \
  --input-file <findings-file> --agent codex --json

SPEC_KITTY_ASSET_SCOPE=consumer \
SPEC_KITTY_HOME="/absolute/private/consumer-runtime" \
/path/to/pinned/spec-kitty agent action implement WP01 \
  --mission <mission-handle> --owned-checkout <checkout> --agent codex
```

Choose a directory that no other executable or consumer writes. Retain both
settings in the consumer's launch configuration and subprocess environment.
Pin the executable directory in `PATH` for nested launches that call
`spec-kitty` by name.
Changing the directory changes selected-template custody and requires a new
analysis report. Requalify when the executable or package source changes; a
pushed source commit alone does not qualify the installed consumer.

With `consumer` scope, mission templates and runtime state use `SPEC_KITTY_HOME`.
All generated global commands and skills use its `agent-assets/` child, retaining
the agent-relative paths from the canonical agent configuration. For example,
Claude commands use `agent-assets/.claude/commands/` and Codex skills use
`agent-assets/.agents/skills/`.

Consumer scope takes precedence over native agent root overrides, including
`OPENCODE_CONFIG_DIR`, `LLXPRT_CONFIG_HOME` and `XDG_CONFIG_HOME`, for these
generated destinations. It does not change an editor's native configuration or
its skill-discovery paths. Configure an agent deliberately if it must discover
these private generated files.

An unset scope, or `SPEC_KITTY_ASSET_SCOPE=user`, retains existing native user
paths and override precedence. Unknown scope values, a missing or empty consumer
home, relative homes and homes containing `..` refuse before runtime/auth or
asset effects. Existing managed-ownership, ancestry, symlink, content and
apply-time checks remain active in consumer scope.

## Why isolation matters

Two CLI versions using one asset directory can overwrite one another's managed
templates. Restoring equal original bytes afterwards still changes physical
custody. The analysis guard correctly refuses that report. Private consumer
assets prevent another runtime using its own directory from causing that cycle;
they do not make a report valid after actual selected-template tampering.

The controlled reproduction and the unresolved original-writer attribution are
recorded in [issue 72's approach](../reports/template-freshness-72/approach.md).
