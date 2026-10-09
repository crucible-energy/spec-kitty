---
title: 'Advisory model attribution repair'
description: 'Dispatch advice must not become evidence of model execution.'
doc_status: draft
audience: docs/context/audience/internal/maintainer.md
type: explanation
updated: '2026-10-09'
---

# Advisory model attribution repair

Audience: source reviewers and operators qualifying downstream consumers.
Mission: `advisory-model-attribution-83`.
Owner: Implementer Ivan; independent review: Reviewer Renata.
Claim: [issue 83](https://github.com/crucible-energy/spec-kitty/issues/83),
branch `issue-83-advisory-model-attribution`, baseline
`c9f90a3a7f67176608f2284316a7a290c6688d86` on the accepted
`fix/owned-analysis-implementation` target.

## Reproduced failure

The executor explicitly makes no model call, but saved a catalog recommendation
as `OpStartedEvent.model_id`. The claim consumer interpreted it as an actual
model and inferred a provider from the catalog. Mission/WP/action correlation
authenticated the dispatch relationship, not a model execution.

Three focused contracts failed before the repair: a real local dispatch
persisted advice as actual execution; historical advice populated actual slots;
and a matching caller model label was accepted without execution evidence.
Two further contracts reproduced propagation of local model fields into the
dormant hosted envelope. Test fixture collection was corrected before these
failing behavioral results; the collection error is not a product reproduction.

## Repair and validation scope

New local records use `recommended_model_id`. Historical `model_id` remains
readable for audit but cannot populate actual model/provider slots. Claims
retain profile resolution and correlation guards, reject explicit model labels,
and use existing absence sentinels. Reconstruction clears stale actual slots
without rewriting historical records or authored WP metadata.

Propagation omits both advisory fields. Production has no registered hosted
transport; injected clients test the projection seam, not a shipped service.
Required baseline, owning fast-tier, named architecture, formatting, lint and
type checks precede publication. Exact commands/results belong to the PR and
external receipts so recording a pass does not change the validated candidate.

This source repair does not repoint the separately qualified installed
consumer, call a model, prove a provider bill, or qualify default-branch release.
