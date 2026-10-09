---
title: 'Consumer asset isolation decisions'
description: 'The approved scope and the trust boundaries it preserves.'
doc_status: draft
audience: docs/context/audience/internal/maintainer.md
type: reference
updated: '2026-10-09'
---

# Consumer asset isolation decisions

Audience: the source reviewer and consumer operator.

- **Approved:** `SPEC_KITTY_ASSET_SCOPE=consumer` requires an explicit absolute
  `SPEC_KITTY_HOME`. All generated global commands and skills project under its
  `agent-assets/` child using canonical agent-relative shapes. Native agent
  overrides cannot escape that scope. Default user behavior is retained.
- **Canonical authority:** the pure selector belongs to `kernel.paths`.
  `get_runtime_state_root` validates before pre-import environment/auth access;
  the CLI runtime-home seam validates before direct owner bootstrap. Command and
  skill owners reuse the same selector and existing safety mechanisms.
- **Retained state:** global asset preparations retain the scope environment.
  Project skill preparations include the selected global asset root in their
  existing configuration identity, so scope changes cannot reuse old evidence.
- **Custody stays material:** no analysis-input, report-verdict, selection,
  content, identity or race guard is weakened. Private roots prevent interference
  by consumers using different roots; sharing a private root still permits it.
- **Publication boundary:** source is based on the existing published candidate.
  No large historical transplant to organization `main`, PR creation, merge,
  global upgrade or installed-consumer cutover occurs in this worker lane.
- **Known limitation:** the original incident actor is unknown. The controlled
  cross-version mechanism and later shared-runtime state do not establish actor
  attribution. Actual model, cost and consumer acceptance remain unknown here.

- **Required validation cleanup:** fix stale fixture assumptions rather than
  change correct production guards. This extends only two existing test files:
  installer unsupported-host capability simulation and the advance-guard's
  historical live-checkout assumption. The asset-path source scope is unchanged.
