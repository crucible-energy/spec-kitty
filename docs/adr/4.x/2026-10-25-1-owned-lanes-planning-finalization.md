---
title: 'ADR: owned planning finalization accepts plain lanes'
description: 'Admit plain lanes only for planning finalization through the canonical owned-checkout resolver while preserving branch, index and started-membership guards.'
status: Proposed
date: '2026-10-25'
---

**Status:** Proposed

## Context

An explicitly owned plain-lanes Mission can be analyzed but cannot finalize an
ownership amendment because the finalizer selects the general lifecycle's
single-branch topology set. The real CLI rejects it before planning validation.
That prevents a safe amendment to unstarted work while existing owners continue
their separate lanes. It does not justify bypassing dependency or custody guards.

## Decision

Give the finalizer its own closed topology set: `SINGLE_BRANCH` and `LANES`.
Continue using the sole canonical owned-checkout minter, its branch and identity
checks, and the existing finalizer transaction. Keep coordination unsupported.
Do not widen the general lifecycle set or couple finalization to analysis's set.

Preserve validate-only behavior, staged-index refusals and frozen started-WP
membership. A successful planning amendment does not grant implementation,
acceptance, cleanup or serving authority. Existing workflows must still satisfy
their own dependency and currentness checks.

## Validation and consequences

Real registered checkout fixtures reproduce the plain-lanes refusal before the
change and exercise both admitted topologies afterward. Negative cases cover
coordination, protected or mismatched branches and staged work without writes.
Re-finalization preserves an active WP's lane and status history, and refuses
removal of that active WP. Tests inspect both the selected checkout and invoking
repository; synthetic fixtures confer no actual producer authority.

Installed release qualification and downstream adoption are separate gates from
source tests. No existing Store, data custody, grants or runtime are changed by
this capability. The old single-branch lifecycle ADR remains historical context;
this decision extends only planning finalization.
