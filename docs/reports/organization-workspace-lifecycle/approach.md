# Organization workspace lifecycle — implementation log

Owner: this mission coordinator. Branch: `codex/organization-workspace-lifecycle-20261020`. Mission: [organization workspace lifecycle](../../../kitty-specs/organization-workspace-lifecycle-01M5DRAR/spec.md). Start: October20,2026.

Adopts Kaizen’s mission-log procedure at `4ca2672d97ffe34d9a7d9a4df3d6f8b6c93c8b51` through the existing Spec Kitty report/tracer location: one independently owned log, preserved history, the three required sections, and final results in external receipts after source/docs freeze.

## User Experience Findings

Declared-lane cleanup does not account for all external and managed workspaces. Repeated prompts cannot establish deterministic closeout. Previously observed counts are inventory, not eligibility. The new observation command includes non-lane Git registrations and reports coverage gaps without pretending to have cleanup authority.

## Engineering Decisions

Continue in the same borrowed checkout on `codex/organization-workspace-lifecycle-20261020`, stacked on custody repair PR112. The existing `organization-workspace-lifecycle-01M5DRAR` mission owns the specification and plan. Independent review required explicit generation identity, authenticated release and producer fencing, an automatic non-lane positive case, branch disposition and primary preservation; all were added before retirement implementation.

WP01 is a bounded read-only observation increment: authenticated paginated organization inventory, configured local roots, the existing NUL-safe Git registry parser, retained unknown ownership and structured coverage. It does not turn observations into cleanup authorization. Preserve existing native Zig work and all other owners.

## Known Limitations

WP02–WP05 remain incomplete: durable lifecycle, creator adapters, automatic completion/startup execution, branch-first consolidation/guidance and full recovery acceptance. No global runtime installation, plugin trust or actual workspace retirement is claimed. Organization API visibility is limited to the configured credential; local scans are bounded and roots explicit. Production remains held. The current tasks-finalization CLI does not expose an owned-checkout option; this must be resolved through its owning workflow before claiming runtime WP admission. No status event has been fabricated to mark WP01 done.

## Independent review corrections

Two red regressions reproduced ambient Git repository/config redirection and an unbounded directory-entry scan. The repair strips ambient Git overrides, uses the canonical fresh topology authority in an isolated environment, and caps entries and queued directories during enumeration. Symlinked roots/ancestors/children and standalone bare stores produce explicit coverage gaps. Existing cached topology callers retain their contract. The initial intermediate syntax failure is retained as diagnostic evidence, not a final qualification.

## Canonical task admission clarification — October20

The earlier legacy-command limitation is superseded: `agent mission finalize-tasks --owned-checkout` already supports this checkout. Its read-only gate correctly requires machine-readable requirement references. The authored packages now provide them. Source code remains frozen at the validated hashes; these subsequent changes are mission/guidance artifacts only. Final documentation/admission checks precede publication, with executable test evidence reused only for unchanged relevant source and configuration.

## Formal analysis remediation — October20

User Experience Findings: the formal implementation gate exposed missing explicit test paths in all WP validation sections, incomplete adapter deadline mapping and ambiguous visibility/latency promises. Analysis recording separately refused stale user-global spec/plan templates before writing. The external blocked report and failed recorder receipt are preserved.

Engineering Decisions: declare focused test surfaces and red-first sequence in each WP, map NFR-002 to adapter/integrated work, map durable SC-001 to WP02, distinguish known gaps from unobservable scope, and require measured <2-second fresh-process local status/enqueue acceptance. Long scans run in a bounded worker. Use a mission-local `SPEC_KITTY_HOME` selecting the current bundled authority, preserving global templates and project doctrine; independent review must revalidate that authority choice before recording.

Known Limitations: no callback latency pass, durable ledger, creator retirement or automatic adoption is claimed. The original four-finding report was not canonically recorded because exact global-template provenance failed; it remains external evidence, not an accepted analysis event.

## WP01 scoped accounting clarification

User Experience Findings: a successful empty-root scan could be misread as whole-organization completeness. The narrowed formal specification requires explicit unknown scope, distinct from known coverage failures and accessible unmatched repositories.

Engineering Decisions: add `observation_scope` to the actual report with normalized roots, configured scan bounds and the two unobservable categories. A committed failing production CLI test exposes the missing field before implementation. Canonical review admission correctly refused the earlier implementation because task finalization occurred after it; no planning/status backdating or gate bypass is used. This independently necessary scope correction is implemented against the admitted baseline.

Known Limitations: the new metadata does not observe inaccessible repositories or out-of-root stores and does not grant ownership. Durable accounting remains WP02. Prior exact source qualification remains historical; changed source receives fresh required gates.

Independent scope review additionally distinguishes entirely undiscovered stores from external stores discoverable through a linked checkout/registry. The report category and acceptance use that precise boundary. The first cluster result is intermediate evidence; final checks follow the wording correction.

## WP02 durable core and usable accounting

User Experience Findings: independent review and red regressions exposed stale
transactions after lock release, thread/fork capability reuse, blocking malformed
state, hardlinked lock-sidecar mutation, incomplete recovery custody, lost partial
inventory and generation closeout/replay defects. These concern real preservation
and recovery behavior; initial green unit checks were insufficient evidence for
the finished core.

Engineering Decisions: extend the existing kernel atomic writer with opt-in
strict file/directory synchronization and bound parent identity; extend canonical
locking with opt-in private, single-link regular-file validation. Legacy callers
retain default behavior. Transactions bind lifetime, thread and process. Missing
history refuses instead of becoming empty state. Accounted creator generations,
unknown discovery and immutable operation receipts remain distinct. Recovery
receives the complete retained intent, uncertain intents block competing effects,
and a retired generation is terminal across event IDs. Unknown/replaced work is
never discharged by omission or another generation's result.

Minimal out-of-map integration adds the ordinary lazy `workspaces` command group
and its real CLI acceptance tests: initialization, status and durable foreground
accounting. This makes the core usable and avoids shipping a test-only coordinator;
it does not expose arbitrary release JSON or a retirement command. The kernel
primitive extensions and command registration are necessary shared-authority
changes, not parallel implementations. Tests commit before repairs; no source,
review or status gate is bypassed. Static publication refs will carry stacked PR
snapshots while this single-branch mission keeps its bound existing checkout.

Known Limitations: concrete creator authentication, shared producer fencing,
automatic event/worker execution, actual disposable retirement, branch-first
consolidation and integrated adoption remain WP03–WP05. Unsupported strict
filesystem capabilities retain/refuse; no cross-platform success, callback latency,
global install, production retry or actual creator deletion is claimed by core
protocol tests. Final qualification lives in external receipts after freeze.

Final status review exposed admission side effects and misleading unknown counts.
A missing/invalid ledger is checked before lock creation, then read authoritatively
under the lock. Status failure leaves an uninitialized directory admissible.
Known retained generations count as unresolved; unknown ownership is separate.
Both regressions were committed red before repair. Broader draft validation
passed 1,011 tests with five skipped; final frozen qualification is external.
