---
title: 'Advisory attribution implementation log'
description: 'UX findings, engineering decisions and known limitations.'
doc_status: draft
audience: docs/context/audience/internal/maintainer.md
type: reference
updated: '2026-10-09'
---

# Advisory attribution implementation log

## User Experience Findings

Claim help previously made a dispatch model label look authoritative. It now
states that model assertions require execution evidence. A rejected `--model`
explains that the operator should omit it. Resolved profile provenance remains
available even when actual model/provider are unknown.

## Engineering Decisions

See [design decisions](design-decisions.md). The causal defect crosses producer,
claim consumer and dormant projection, so contracts cover all three plus status
reconstruction. Local records and authored metadata remain byte-stable during
claim reads. No model calls are needed to reproduce this defect.

The first published candidate formatted two formerly excluded files but left
their exclusions in place. CI's existing formatter ratchet rejected both stale
entries. Removing those entries strengthens the existing format gate; no test
or enforcement is added. The named ratchet is included in repair validation.

## Known Limitations

There is no genuine model-execution evidence producer on this dispatch path.
Actual model/provider therefore remain unknown; adding one needs a separately
reviewed execution contract. Historical ledger advice is preserved and does not
retroactively establish execution. Hosted compatibility and transport are
unqualified. The installed protected consumer is not upgraded by a source merge.
Actual model tokens, provider cost and savings are unknown for this repair.
