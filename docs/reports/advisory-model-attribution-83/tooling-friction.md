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

The subsequent contract-tools gate found the reference Ops reader's exhaustive
field-classification contract had not named `recommended_model_id`. The reader
already builds a closed whitelist and does not serve advice. Its fixture now
plants the new field, the exclusion classification and schema description name
it, and the existing row proves it is withheld and rejected by the closed schema.
This qualifies a contract/reference seam, not a live hosted read service.
The description checker now matches whole field names, preventing `model_id`
from matching the suffix of `recommended_model_id`; independent review and a
direct negative/control regression cover that collision.

## Known Limitations

There is no genuine model-execution evidence producer on this dispatch path.
Actual model/provider therefore remain unknown; adding one needs a separately
reviewed execution contract. Historical ledger advice is preserved and does not
retroactively establish execution. Hosted compatibility and transport are
unqualified. The installed protected consumer is not upgraded by a source merge.
Actual model tokens, provider cost and savings are unknown for this repair.
