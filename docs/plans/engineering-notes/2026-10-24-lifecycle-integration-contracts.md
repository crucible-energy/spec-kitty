---
title: Lifecycle integration acceptance corrections
type: explanation
audience: software-engineer
updated: 2026-10-24
---

# Lifecycle integration acceptance corrections

## User Experience Findings

Hosted PR120 checks exposed inherited feature-integration regressions. WP04 correctly added PR-only target validation but older rollback, content and attestation success fixtures still use main/develop, so they abort before their intended checks. Four selected exact-source tests failed before repair: rollback, unprotected-target positive, internal Op field completeness, and canonical Windows detection. External failed fixtures and logs remain retained.

## Engineering Decisions

Keep the strict canonical protection policy and real failure injections. Distinguish actual protected/default-branch and historical references from positive feature-consolidation targets before editing. A successful feature fixture needs a distinct real primary branch whose ref remains unchanged; changing a branch label alone is insufficient.

The inherited direct-ref cleanup predicate delegates Windows detection to kernel.paths.is_windows without changing its signalling or join behavior. OpStartedEvent.checkout_branch is internal custody identity; the closed public status schema deliberately omits it. The shared real-record fixture carries a nonempty private branch, so existing schema rejection, omission and mutation checks exercise that boundary rather than only adjusting a field-set assertion.

## Known Limitations

The fixture migration, complete owning validation and independent review are still in progress. These corrections do not qualify automatic cleanup, source delivery to actual default, runtime installation or organization execution adoption. Root separately owns generator and CI-selection corrections. No other owner's checkout, process, cache or host resource was removed.

The first bounded correction passed 57 focused checks: canonical OS-door scan, real native-ref lock/timeout/descendant controls, and non-timing public Op contract rows including the new private branch value. Ruff and configured mypy for the production file passed; the final formatter-only change was executable-AST-equivalent. These focused results do not replace the required final baseline, remaining fixture checks, independent review or hosted gates. The failed four-case reproduction and successful private validation tree are retained under this owner's closeout obligation; no automatic cleanup claim is made.
