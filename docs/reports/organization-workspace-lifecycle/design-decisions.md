---
title: Design decisions
description: Retained design decisions for organization workspace lifecycle.
doc_status: active
updated: '2026-10-24'
---

# Design decisions

The independently owned implementation log is [approach.md](approach.md); these are the mission’s architecture tracer notes.

- Treat organization inventory, local store observation, creator authority and retirement as separate facts. Accessible repository inventory is not a claim about hidden repositories or owner release.
- Reuse the canonical Git topology parser with a fresh bounded isolated-read entry point. Preserve pathname bytes by removing only Git’s output terminator; a valid trailing space distinguishes separate stores.
- Use bounded entries and queued directories, and report excluded symlinks, unsupported bare stores and stale/unreadable registrations. A configured scan may be incomplete; never turn a scan bound into a silently complete inventory.
- Use the canonical owned-mission task-finalization entry point. The legacy `agent tasks finalize-tasks` does not select owned custody; `agent mission finalize-tasks --owned-checkout` does. No new workaround or gate bypass is required.
- Keep existing native Zig work and other owners’ checkouts unchanged. This increment is Python observation/CLI glue in the existing layer. Automatic retirement and the creator event bridge remain subsequent work.
