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

- **Hosted patch review frontier (issue 76):** archive preservation uses the
  exact event base for an advertised non-main GitHub PR only after bounded
  event, environment, target repository/remote and local Git correlation.
  The event base must belong to the exact remote target ref’s published history;
  later target advances are allowed.
  Synthetic merges require exact ordered base/head parents; raw head checkouts
  require the exact event head and target-base ancestry. Checkout does not
  rewrite GitHub environment, and a raw head need not have the synthetic merge
  object available. The byte freeze and landed exemption lookup use the same
  base. No fetch, arbitrary base override or archive exemption is introduced.
- **Compatibility boundary:** default-main reviews keep the existing canonical
  main resolver, including GitHub's documented empty fork event payloads.
  Empty non-main payloads refuse because their exact event base/head cannot be
  correlated. Populated fork-head fixtures prove that bounded case, rather than
  all real fork behavior. Missing or malformed advertised target metadata fails.

- **Runner graph authority (observed 2026-10-09):** PR 75's archive job on source
  `8a8e8ead2` passed runner SHA, exact ordered event parents and published target
  checks, then refused a differing optional webhook `merge_commit_sha`. That
  equality assumption was incorrect. GitHub documents [background mergeability
  computation and state-dependent merge metadata](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request),
  while [Actions identifies `GITHUB_SHA` with the workflow merge branch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request).
  The field may be null or stale; its type/format remains validated, but it has
  no baseline or checkout authority. Actual merge HEAD still equals runner SHA
  and has exact ordered base/head parents; raw HEAD still equals event head.

- **Registry review-base authority (issue 81):** T015/T019 reuse the archive
  owner's exact validated non-main event base and require the same checkout.
  Registry bytes read at that SHA ignore Git replacement objects. Ordinary
  `origin/main` then `main` fallback remains unchanged. Only the three toy local
  resolver tests explicitly clear hosted metadata; live evidence/selection
  guards keep it. Real Git fixtures retain changed-row freshness/parity,
  expanded-directory routing and target/head/checkout tamper controls.
