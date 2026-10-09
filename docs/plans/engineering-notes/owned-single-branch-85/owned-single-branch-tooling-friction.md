---
title: 'Explicit owned single-branch recovery: tooling friction'
description: 'Records SDK recovery tooling failures, corrected validation environments and retained evidence from the owned single branch repair.'
type: explanation
audience: software-engineer
doc_status: point_in_time
updated: '2026-10-09'
---

Observed: existing `backfill-topology --restamp-single-branch` chooses the repository
root checkout and converts legacy code lanes to `lanes`; owned lifecycle commands
deliberately support `single_branch`. That remedy does not recover this owner.

Observed: dispatch has no owned checkout option. Only its non-mutating resolver was
used; the delegated issue/tracers are the bootstrap record, not an invented Op.

Observed: a dedicated frozen-lock SDK environment was provisioned in this checkout.
The first acceptance run was interrupted during slow collection; no RED proof was
claimed from that interrupted attempt. Full output and startup sample were retained.

Observed: the initial Python 3.11 diagnostic was interrupted while the repository's
wall-clock AST scanner ran; it did not establish a runtime qualification failure.
The independently owned environment
was rebuilt from the frozen lock with the existing pinned Python 3.13.11 interpreter;
no global interpreter, installed SDK package or consumer configuration was changed.
The dedicated source CLI uses a private consumer asset home.

Observed: the first focused authority gate reported raw status listing and workspace
output parsing outside `kernel.git`, after 122 checks passed. Those introduced
findings were fixed through canonical status entries and a narrow Git-owner inventory
reader. No allowance or suppression was added. The rerun before the final bounded
blob change passed 95 checks; that earlier receipt is not the final candidate's gate.

Measured: intermediate new-module statement coverage was 89%, below the required
acceptance bar. Material owner-head, dirty-work, membership, ownership, idempotency
qualification and bounded-read refusal cases were added. Final results are recorded
externally after the source/docs freeze, so a passing receipt cannot modify its
validated candidate. Independent source review and actual consumer qualification
remain the parent's responsibility.

Observed: the first shared baseline invocation incorrectly injected the private
consumer asset home into tests that already isolate HOME. It reported 12 failures
and 2,437 passes in 318.62 seconds; it also reused Python 3.13 against the source's
tracked 3.11.15 request. The invocation was corrected, without editing valid tests,
using a separate frozen-lock 3.11.15 environment and the canonical fixture homes.
The final `make test-fast` passed 2,449 tests with five skips and three existing
warning emissions in 254.36 seconds. The original failure output remains retained.

Observed: the owning subsystem gate caught the new workspace query inside
`kernel.git` through C-007 after 848 passes. The query moved to the guarded caller;
the kernel keeps byte/path parsing, with literal protocol labels rather than argv
encoding. Both guards stayed unchanged. The final full kernel/migration run passed
850 tests with six skips in 111.13 seconds.

Measured: the earlier 372-line coverage report omitted the existing command
registration module, so it was limited evidence. The final fresh measurement
includes all six changed source files: 346 of 373 executable changed lines covered
(92.76%), passing the 90% diff gate. The final relevant regression/authority/layer
run passed 254 tests in 200.09 seconds; strict typing passed for five source files.
These source results precede the final lightweight documentation checks. Complete
logs and frozen-source hashes are external; no source result was reused across a
meaningful code change. Token usage and cost are unknown.

Observed: PR CI reported six introduced contract failures after the local gates:
the new JSON command lacked classification, one metadata helper bypassed the
already exported status facade, parser fixtures used a shared temporary-root
literal, completion data was stale, and the five new pages lacked lifecycle
frontmatter with one guide outside sanctioned sections. The six named gates
reproduced RED in 9.71 seconds. Repairs use the existing facade and explicit JSON
case, virtual wire paths, the canonical completion generator, active guide routing
and point-in-time engineering-note routing. No gate exemptions or CI changes were
introduced. Subsequent source and documentation qualification is recorded externally.

Observed: a later hosted architectural run found a transaction identity slice,
manual lane-prefix recognition and an exported record type without an external
caller. Four named regressions reproduced these failures locally in 72.69 seconds.
The repair routes identity and recognition through the canonical naming authority
and keeps the parser record internal. No dead-symbol allowlist or gate suppression
was added. Qualification of this source increment is retained in external receipts.

Observed: the strict merged command refused the actual consumer's two scoped
historical projection changes. A prior lane-only audit was insufficient for the
expanded ownership union. The complete parent-edge diagnostic retained both the
modifying commit and the merge edge, plus base/tip/current raw variants, without
claiming admission. The successor's real root CLI acceptance reproduced one
schema-2 refusal in 58.26 seconds; its schema-1 zero-effect control also refused.
The initial RED log remains external. Test fixture hashing uses the canonical
content-digest helper rather than a parallel algorithm or lint suppression.

Observed: the canonical digest helper returns a provenance prefix, while the
closed custody wire format requires bare hexadecimal SHA-256 values. A root CLI
diagnostic retained exception classes and source locations only; it exposed the
format mismatch without logging source bytes or malformed proof values. The
fixture and wire comparison now remove that formatting prefix explicitly.

Observed: a repeat control changed authored WP ownership while the retained lane
kept the same scope union. Scope equality alone did not bind the original authored
inputs. The verifier now also checks the qualifying receipt's frozen input hashes,
excluding the intentionally converted manifest. The first matrix retained 32
passes and this one failure. Subsequent focused boundaries passed 18 tests in
167.77 seconds, including unchanged executable modes, hidden/reverted history,
unsupported changes and same-input repeat/finalization. Final gates remain pending.
