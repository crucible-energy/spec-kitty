---
title: 'Advisory attribution decisions'
description: 'Preserve audit history and require genuine execution evidence.'
doc_status: draft
audience: docs/context/audience/internal/maintainer.md
type: reference
updated: '2026-10-09'
---

# Advisory attribution decisions

- Keep recommendation and execution distinct. A catalog winner is useful local
  advice, not an observed model call. Do not invent an execution marker or
  infer a provider from a recommendation.
- Preserve append-only historical JSONL. The consumer excludes historical
  advisory values rather than silently migrating them into actuals.
- Reuse existing model/provider absence sentinels. They already clear stale
  slots through emission and reconstruction; no second status schema is needed.
- Keep advisory fields local. The dormant hosted projection excludes both
  legacy and new fields; this repair adds no transport or hosted contract.
- Remove the unused provider lookup. Keep the existing profile resolver and
  all mission/WP/action/embedded-ID consistency checks.
- Reuse the current clean source lane and accepted fork target. Installed
  consumers and unrelated dirty checkouts have separate custody.
- Scope validation to required fast tiers and named gates. Whole heavy suites
  remain owned by existing CI, with no new enforcement surface.
