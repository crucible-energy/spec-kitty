---
title: Configured agent command migration detection
description: Repair legacy command population eligibility without creating unused agent surfaces.
doc_status: active
updated: '2026-10-26'
---

# Configured agent command migration detection

Owner: Dream Walker dependency recovery, `codex/issue-127-agent-migration`.
Tracker: [issue 127](https://github.com/crucible-energy/spec-kitty/issues/127).
Follow-up: [issue 129](https://github.com/crucible-energy/spec-kitty/issues/129).

## User Experience Findings

A Codex-only consumer could not finish upgrading because the legacy command
population migration always detected missing Claude commands. Current mission
assets lack its retired command templates, so the upgrade stopped before later
migrations. Conversely, complete unselected Claude commands hid an incomplete
configured Gemini surface. Invalid agent configuration was never consulted.

## Engineering Decisions

Use the canonical configuration-aware directory resolver for both detection and
application, retaining the existing parent-presence boundary. Codex uses skills,
so it has no eligible legacy command directory. No unused Claude or Copilot
surface is created. Configured legacy command agents still require real templates
and preserve existing custom commands. Missing templates for an eligible surface
remain an error; invalid configuration remains an error.

Regression tests extend the existing migration robustness module. Three original
failures reproduce Codex-only upgrade rejection, missed configured-agent repair
and ignored invalid configuration. The actual migration runner records a truthful
not-applicable result; no metadata success is manufactured by the caller. Tests
also cover real template copying, dry-run preservation and existing legacy roots.
This is a bounded correctness repair to retained Python, not a second migration
implementation. The eventual Zig parity surface must preserve these contracts.

The actual isolated RC7-derived consumer upgrade passed that migration and then
exposed a second defect: the earlier canonical-context runner stripped an
existing assignment before the later runtime-state cutover could verify it.
The runner now calls the sole seed/verify/phase-flip helper for every mission
before stripping any frontmatter. A refusal restores its existing backup;
neither rebuilding lane transitions nor an existing seed substitutes for verified
runtime-state cutover. A real corrupt assignment seed exercises rollback with
the original mission files preserved. The existing migration commit helper also
retried rejected hooks with verification disabled; a real rejecting-hook
regression reproduces that bypass, and the helper now returns failure after the
normal attempt. These are bounded retained-Python safety repairs, with the same
ordering and hook boundaries required of the eventual Zig implementation.

## Known Limitations

The migration retains its existing eight-command completeness threshold and
parent-presence policy. Missing agent roots are left to the canonical setup and
repair surfaces. This change does not repair all historical migrations or prove
an entire consumer upgrade; actual isolated downstream upgrade and runtime
identity verification remain required. The frozen installed runtime is preserved;
any derived package must be built from pinned source with an honest distinct
version. Canonical dispatch was subsequently admitted in the same owned lane
after replacing its linked checkout with an independent root at the same path
and running the supported RC7 project migrations. The dirty shared primary
remained unchanged. The complete upgrade still reports failure for preserved
edited global assets and a profile-root repair that needs a fresh plan; project
admission does not assert complete global upgrade or default-branch adoption.
No audio consumer, production admission or storage-recovery claim follows from
these framework tests.

## Hosted check admission

PR128's existing jobs remained unassigned on vendor-specific Ubuntu and Windows
labels. This lane replaces those labels in the six workflows triggered by the
repair with standard hosted Ubuntu 24.04 and Windows 2025 labels. No job, check
name, command, condition, permission, timeout or dependency version is removed
or weakened. Parsed before/after workflow comparison verifies that only runner
selection and its matching operating-system matrix entry change. Hosted jobs
must still execute and pass before delivery; a queued or locally green result
does not substitute for them.

The canonical invocation executor already emits `op(profile): action [id]`
commits, covered by its producer contract tests. The existing type registry
omitted `op` and rejected the real governed record created during this repair.
The registry now recognizes that domain type. Unknown types, empty types and
empty subjects remain rejected; no commit-lint rule or job is disabled. The
actual configured registry contract reproduced the rejection before the change;
the hosted commitlint invocation remains the final consumer check.

The declared strict bootstrap typecheck also exposed `Any` propagation from
imports skipped by the configured type analysis. Explicit local `str` and
`Path` annotations preserve the existing canonical constant and asset-resolver
contracts across all three return branches. This is a bounded typing repair to
retained Python: no path coercion, exception suppression or analyzer override
is introduced. Existing resolver and doctor tests exercise the runtime behavior;
the unchanged strict typecheck must pass.

The project upgrade's generated governance effects are preserved separately
from this bounded CI change. They are not a shortcut to importing another
owner's unpublished platform or CI architecture. The isolated validation
environment uses the committed frozen dependency lock with third-party builds
disabled. Python tests import this checkout's source; the governed CLI remains
the separately identified RC7-derived runtime. No installed wheel is patched.

The upgrade command's `--project --json` combination reports its compatibility
plan and does not apply it, even with `--yes`; the applying form was run
separately and its actual output retained. Migration history, preserved shared
edits and incomplete repair state remain explicit recovery obligations.

Hosted execution then exposed four existing docs without required descriptions
and two raw historical fixtures flagged by canonical-producer lint. The docs
receive only the required descriptive frontmatter. The fixtures retain exactly
the same event bytes and assertions: the decision input exercises an install
fence and its normal reentrancy control; the historical intake exercises
defensive recovery of incomplete legacy data. The linter's existing, validated
`exception-flow` test category documents those inputs. No baseline entry,
production exemption, producer model or gate rule is added or changed.

The hosted lock-freshness check reproduced a stale editable self-entry:
`pyproject.toml` already declared 3.2.8, while `uv.lock` retained 3.2.7. The
canonical offline resolver updates only that self-version; parsed comparison
verifies every third-party package, artifact hash and other lock field remains
identical. This does not add or upgrade a third-party dependency.

A superseded PR128 run also retained queued `always()` jobs and held the
workflow concurrency slot. After capturing its old source identity and proving
that none of its 54 jobs had an assigned runner or was running, normal cancel
was attempted. Its queue remained; the supported force-cancel endpoint then
retired only that obsolete run. Current-source checks subsequently executed.
No other owner's workflow was cancelled and no required result was replaced
with a manual success status.

The now-running full pipeline also reports older merge/read-surface regressions
and vulnerable dependencies. Those remain failed gates, with retained hosted
logs and a follow-up repair obligation; this metadata/fixture increment does
not claim to resolve them. Four changelog emphasis delimiters and two excess
blank lines are corrected to the existing Markdown policy without changing
their content.

The next bounded repair resolves six audited lock versions (anyio, certifi,
cryptography, filelock, pip and urllib3), with safe minimum floors for the two
direct security dependencies. All other resolved packages stay unchanged. The
actual frozen isolated environment reports no known vulnerabilities; 98 locking,
encrypted-storage, transport and dependency-drift checks pass with three existing
platform skips. This is environment evidence, not a release or global upgrade.

The zero-reader gate previously treated literal `.history-boundary` paths as
frontmatter consumers. AST expression recognition now excludes literal examples,
comments and imports and detects multiline mapping reads; syntax errors refuse
the proof. Existing writer exclusions and attribute-domain heuristic remain
unchanged: this is not whole-program type or data-flow analysis. A retained old
scanner control reproduces the false positive. Current resolver tests no longer
require a repaired production seam to retain its old bug: an explicit injected
nonexistent coordination result must fail the same existing-primary assertion.
All 72 read/contract/containment checks pass. The orchestrator contract also names
the workspace-containment error its existing producer already emits.

Six advisory type findings are repaired using local contracts and a distinct
prompt-path variable, without casts or suppressions; full mypy reports zero
issues in 1,143 source files. Relevant suites report 189 passes, one existing
skip and one failed negative setup-plan test. Loading the exact pre-change
setup-plan module reproduces the identical failure: template validation refuses
the injected typeless coordination surface before the test's expected missing
spec refusal. That result remains red, not an overall suite pass or a waiver.

The subsequent docs gate exposed stale page inventory/retrieval indexes and
seven existing recovery commands absent from their references. Their source
signatures and preview/apply boundaries are documented, and the canonical index
writers refresh the derived records. No CLI behavior or authority is added.
Dedicated merge/rollback and noninteractive-plan P0 repairs remain separate
from these bounded gate corrections; their hosted regression failures are not
reclassified as passing or silently skipped.

A dedicated product repair now addresses the explicit noninteractive plan
contract. The retained real command reproduction emits the approach prompt
under `SPEC_KITTY_NON_INTERACTIVE=1`. Its cause is an unconditional optional
interview after scaffolding. The public interview boundary now uses the existing
canonical truthy-environment parser and returns no answers before actor lookup,
decision creation, network discovery or stdin access. It does not infer answers,
approval or TTY intent; ordinary interactive/piped input remains unchanged when
the explicit flag is unset. The existing red-first command assertions are
unchanged. This is a bounded retained-Python correctness repair; a future Zig
port must preserve this boundary. Other merge/rollback P0s remain separate.

The next dedicated repair establishes the materialized-coordinate failure with
the unchanged two-WP real-Git harness. The classifier compared its selected
coordination directory to an identity already normalized to that same directory,
misidentifying it as primary and skipping the durable commit. Merely consuming
the resolver's anchor did not suffice: that fast path also returned the
coordination candidate as its supposedly primary anchor. Both retained reds are
preserved. The resolver now carries the topology-blind primary metadata anchor
separately, and the transaction classifier consumes those explicit roles.
Status candidate selection remains single-pass; deleted/corrupt-state refusal,
verified primary snapshot priority and create-window read fallback remain intact.

All 17 unchanged merge, rollback, strand-repair and adversarial refusal tests now
pass. A new real registered-worktree case pins the distinct status and metadata
roles. Broader preservation checks have 114 passes and 18 failures; executing the
same checks against an exact published 09941d7b5 source export has 113 passes and
19 failures. All 18 remaining failures are identical; the only difference is the
new anchor regression, red on the old source and green on the repair. This is
not an overall preservation-suite pass. Older unmaterialized-coordinate and
stale resolver-fixture expectations remain owned follow-up work. Full mypy has
zero issues in 1,143 files, and changed-source/test lint and formatting pass.
No existing regression assertion, unknown-state refusal or required CI gate was
relaxed. No audio producer, archive or approval is involved in these fixtures.

Dependency and CLI repairs activated four further PR workflows whose seven
validation jobs still used the unavailable vendor host. The post-merge
direct-push compliance check had the same host dependency. Their eight labels
now select the official Ubuntu 24.04 host. Parsed comparison preserves every
other event, path filter, command, condition, permission, dependency and timeout.
Deployment, release-publishing and manual audit workflows keep their separate
owners; this correction targets the current validation and delivery checks.
Actual hosted execution and all remaining product findings still gate PR128.

The newly executable release-readiness check found the tracked project metadata
still declared 3.2.7 while the package, lock and changelog declared 3.2.8. Only
that release identity is synchronized; migration history and upgrade timestamps
are not manufactured or refreshed as a release-validation shortcut.

The unchanged #2804 regression reproduces accepted gate evidence being replaced
by an untouched mission scaffold during a real squash merge. The bounded repair
pins source and target Git identities, inspects both-side divergence before
creating a merge workspace, and restores the exact authored blob after Git's
planning conflict resolution and before committing. Both-authored conflicts,
deletion conflicts, symlinks and unknown scaffold shapes refuse without advancing
the target. Only the known empty issue table and single generic AC-001 TODO
scaffold qualify for automatic preservation; new requirement-specific criteria
are not discardable placeholders. This does not assess evidence or grant
acceptance. Other merge strategies keep their existing conflict handling.

This is a bounded correctness repair to existing Python Git integration. A future
Zig migration must preserve opaque evidence custody and these refusal contracts;
it must not synthesize QA, merge arbitrary evidence fields, or grant approval.
The original regression and real Git tests cover both source/target directions,
ambiguous authored data, deletion, nonregular input and joined workspace cleanup.

Hosted fast-mission checks exposed outdated routing fixtures: six private-helper
calls omitted the explicit coordination metadata argument; the exception-relay
test actually selected a readable primary create window. The helper tests now
provide their legacy metadata explicitly, and the exception test injects a real
resolver error at its intended boundary. New complementary cases preserve the
real create-window primary selection and the verified phase-1 cutover grid.
Six surface-path fixtures also asserted coordination paths without a materialized
canonical event log. They now create registered Git worktrees and an empty valid
event stream, preserving every original path assertion. A missing coordination
stream separately keeps primary authority. All 50 checks pass; no production
resolver, expected refusal, selector, skip or xfail was changed. Remaining legacy
transaction/read contracts and audit-inventory findings are separate blockers.

Those transaction failures exposed a second physical-path/authority conflation:
a primary read fallback hid planned events already committed on an unmaterialized
legacy coordination branch. The transaction classifier now distinguishes fresh
create windows from existing canonical branch history, using the shared metadata,
topology and event parser. Explicit phase-1 primary cutover and stored flat
topology keep primary authority. Legacy history is read at a pinned commit;
unknown read failures and nonregular blobs refuse. The existing stream reader's
strict internal option keeps its default compatibility behavior unchanged.
BookkeepingTransaction still owns real materialization, commit, rollback and
fanout; no unregistered directory becomes writable authority by path selection.

Deleted-branch read fallback remains distinct from write admission: the read
shape stays coordination until its existing deleted-ref arm returns primary,
while a missing bookkeeping branch still refuses writes with no fanout. The
structured-invalid-root fixture now contains actual committed history, so it
tests recovery rather than the legitimate empty create window. Shared write-side
fixtures use canonical branch/path constructors and a real canonical event log,
replacing an externally placed, incorrectly cased path-only husk. Phase-1 and
create-window controls, rollback, atomic append, binding and postcommit fanout
are retained. Earlier partial runs and the original failures remain in receipts.

Architecture inventories are freshened through the recorded composite-identity
converter. The diagnostic-only untrusted-path row keeps its existing unreachable
disposition and rationale; only its tool-derived identity is updated. The routed
metadata floor is tightened, not relaxed. Three glossary casing findings use
the committed canonical form. These audits keep their undercount, overcount and
unknown-path tripwires. Remaining hosted findings and complete PR delivery still
gate adoption; this framework repair is not audio progress.

Actual #2404 integration and kind-read trials exposed a separate overreach of
status authority into QA placement. A registered coordination worktree can carry
an acceptance/issue matrix before it has a status event stream. The existing
read primitive now receives the stream requirement from the declared artifact
kind. Its kind-blind/default and STATUS_STATE paths still require the event log;
other coordination-owned kinds retain the same registration, topology and
containment checks without requiring that unrelated file. Unknown kinds refuse.
PRIMARY kinds and explicit status cutover behavior retain their own partition.
No new resolver, writer, worktree materialization or acceptance authority is added.

Five real Git QA trials were red before the repair. The complete kind-read,
migration and gate-preservation slice passes 61 tests; the placement grid passes
121 checks with real registered/event-bearing fixtures. The integration harness
now calls the actual acceptance gate adapter rather than its retired kind-blind
status-path sequence, preserving all three write/read freshness assertions.
Complementary tests prove that QA selection does not promote a streamless
coordination directory to status authority and that undeclared kinds cannot opt
into a new scope. This remains a bounded existing-Python correctness repair;
Zig parity must preserve these separate kind/status contracts.

The materialized primary metadata anchor folds through the existing canonical
handle seam. Existing audit allowlist identities are re-pinned to their exact
live call sites without adding exemptions. Migration-copy assertions now compare
expected filenames and contents from independent template inputs and preserve
the unselected Claude surface byte-for-byte; temporary-workspace cleanup checks
the exact retained checkout identity rather than a golden count. No baseline is
grown or detector weakened. Other actual hosted failures remain owned blockers.

The remaining workflow replay reproduced 19 failures on the published source.
The local SUT environment lacked the editable project installation that CI
performs, so three upgrade-prompt controls could not discover a package version.
The normal frozen editable install adds only the test SUT `spec-kitty-cli` 3.2.8;
all dependency versions are unchanged. This environment is not the workflow
governor: the explicitly addressed, pinned 4.0.0rc7 derived governor remains
unchanged and is the only admitted governance runtime. No shared installation
or live producer is changed.

Upgrade flag fixtures now use real Git repositories, matching charter root
requirements. Planning-artifact fixtures persist their actual `lane-planning`
WP02 records instead of asking the product to accept an absent lane. Topology
checks pin the declared primary target branch for that first-class planning lane
while still requiring an unavailable diff without a deterministic claim commit.
The full CLI scenario now verifies committed nonempty spec/plan/tasks blobs,
independent of commit-message wording. No refusal is suppressed. The planning
contract mirrors the already-emitted containment refusal without removing any
existing codes. All 117 workflow/contract/graph/end-to-end checks pass.

The supported graph generator repairs two stale fragments: it removes two
suggestion edges absent from the authored directive and reflects the authored
procedure's requires edge. No nodes or hand-authored tension/anti-pattern data
are removed. Source-root validation excludes the privately retained supported
upgrade effects, so the checked project inputs match publication; those exact
effects are restored only for canonical governance operations.

Tests that now create real Git worktrees are classified as `git_repo`, not
`fast`; the marker and same-tier selection gates verify their routing. The
historical routed-census witness records the actual primary-anchor fold and its
tightened floor. Git tree enumeration uses the canonical mission-directory
constant. Thirty-two focused architecture and real merge-preservation checks
pass. The latest hosted clean-install latency measurement remains a real blocker:
1.278s median against its unchanged 1.050s ceiling. Startup profiling/repair and
other current hosted integration findings remain required before PR delivery;
these fixtures and projections are not a whole-pipeline or audio-success claim.

The actual clean-install command profile contradicts the historical attribution
to step projection: projection takes less than a millisecond in this trace,
while eager schema-engine loading compiles 38 URI parsers on an unrelated read.
Six existing validators now import that engine inside their validation function.
Every call still loads the same schema and executes the same validator and error
loop; there is no new cache, invalidation rule, dependency change or validation
bypass. The bounded Python repair's Zig parity obligation is to preserve this
demand boundary and every refusal, not to copy eager initialization.

A fresh-process regression is red on the published source, then green after the
repair; it also proves invalid profile data actually loads the engine and fails
validation. Fifty-five service/projection/profile checks and 130 existing schema,
inline-reference and invalid-input checks pass. Exact command JSON differs only
in its observed timestamp. The unchanged five-run latency gate passes locally
at 0.645s median against 1.050s. This is Python 3.11 on this host, not the hosted
clean-install Python 3.13 qualification, render throughput or exclusive savings.
The hosted gate and other current integration findings remain mandatory.

The next bounded replay reproduces 27 failures among 173 status/CLI/gate checks.
The positive cases now supply real registered worktrees and explicit canonical
event logs instead of directory-shaped husks or status cache files. A shared
private-fixture helper refuses to adopt an existing directory, creates only its
named branch/worktree, and excludes nested execution workspaces from source Git
links. The unexpected-empty trials retain their absent mission directory, live
branch and warning assertion; deleted-branch controls still refuse. No production
resolver or refusal changes in this slice.

The two-surface net now tests ANALYSIS_REPORT on its already-declared PRIMARY
partition while retaining every artifact-kind trial and the primary/coordination
anti-mutant assertions. The review scanner mock is scoped to that scanner's
process adapter so it cannot intercept unrelated environment/Git probes. Real
Git fixture modules are classified `git_repo` rather than `fast`. Initial setup
errors and the original reds are retained; after these repairs all 173 checks
pass, including the real divergent-surface regressions and dirty-worktree gate.
These are fixture qualifications, not additional product acceptance or audio QA.
The full shard census additionally caught an unclassified fresh-process schema
regression from the preceding slice. It is explicitly routed to the doctrine
integration gate; no selector, orphan threshold or assertion is relaxed.

The subsequent 134-test replay exposes six further fixture/parity failures.
Retrospective divergence now uses a registered worktree with its independent
event log; the exact warning/handle matrix supplies a registered empty window
with a live branch instead of an unregistered directory. A first edit hit a
similarly shaped, different test; the retained partial run caught that mistake,
and the intended warning case was corrected before publication. Warning and
deleted-branch assertions remain intact. All 135 checks now pass.

The committed-spec parity harness now follows setup-plan's two actual read steps:
status-aware mission lookup followed by its kind-aware planning adapter. Its
coordination fixtures commit distinct primary and stale shadow specs, preserving
both positive parity verdicts. A new negative control proves a committed shadow
cannot supply a removed primary spec. This changes no production authority.
The latest hosted doctrine red also exposes a stale cardinality expectation from
the graph regeneration already delivered in 5e24a1851: two DIRECTIVE_046
suggestions have no authored source. The expectation is reconciled by exactly
those two edges; all node/orphan counts, exact regenerated/shipped edge-set
equality and the hand-authored overlay remain enforced. Full current hosted
gates, protection/review/default delivery and audio continuation remain pending.
Five graph projection/freshness checks pass with the reconciled cardinality,
and the full shard census reports 18 passes with no orphan or duplicate routing.

The hosted integration ordering exposed three package-default template trials
that inherited another test's populated global runtime. A private populated-home
control deterministically reproduces all three failures. Each package-default
trial now owns an empty runtime home, as the existing software-development trial
already does; other precedence and unknown-type controls retain their own scope.
All 75 template-resolution/integration checks pass with the populated outer
control still present. No production resolver precedence or shared home changes.
The hosted clean-install gate on 49ab182d8 reports 0.840s median against the
unchanged 1.050s ceiling; local and hosted timings are separate measurements.

The long next-shard investigation does not establish a runtime defect. A bounded
two-worker diagnostic reports 274 passes and three timeouts under an explicitly
diagnostic 30-second per-case ceiling. Independent observations of the same
synthetic research fixture show forward progress through all seven steps to
terminal with no guard failures. Under the original test configuration, all
three cases pass: 34.63s, 47.15s and 46.75s call time, 162.25s total including
setup. The whole-process 900s/4GiB/1GiB-swap/32GiB-reserve guard remains unchanged
and completed with nonzero samples. The 30-second results remain retained
diagnostics, not product regressions or discarded required-gate failures. No
runtime code, compat spy, scenario, cap or required selector is changed. Full
hosted validation remains the merge gate. Private fixture Op records and prompts
are synthetic test output and confer no real mission, audio or human authority.

The published protect-main contract required clean-install enforcement, but
fresh live reads showed no branch protection or effective rules. The owning
admin workflow adds that exact GitHub Actions check context (app 15368), requires
the PR path with zero reviewer approvals, and enforces it for admins. No existing
rule was removed, check result overwritten or approval requirement inferred.
The runbook now distinguishes the displayed check context from its internal
workflow job identifier. All project-required gates still apply independently;
this configuration repair is not a PR merge, audio qualification or capacity
milestone. Review/default-branch delivery and eligible resource custody remain.

The next hosted wheel run on fbde8e4a3 misses NFR-003 at 1.245s against the
unchanged 1.050s ceiling. Its 49 installed package versions match the preceding
0.840s run, but uncontrolled runner differences prevent an exclusive cause or
savings claim. The earlier pass is retained, not promoted to delivery. Remaining
import profiling identifies eager charter compiler/interview initialization and
the project installer loaded before an already next-only command registration.

The charter package now binds its original public exports on demand. An ordered
contract captured from the published pre-repair import declarations pins every
export name, target module and object identity. The existing `sync` function is
eagerly retained because its name collides with a submodule; both import orders
keep the original callable identity. Unknown names still raise. Only standard
per-process code bindings are retained, never project data, governance decisions
or input-dependent results. Static type exports and full mypy remain intact.
The catalog import regression is an actual pre-repair red, then green.

An initial trial deferred imports inside the installer and passed 141 checks;
it was superseded and `init.py` restored exactly. The final root repair instead
avoids installer registration on the existing next-only route. Its fresh-process
test is red before that repair. The normal command surface is preserved, and a
real Typer invocation proves the next-only app still executes pin validation and
propagates a schema refusal before dispatch. Final charter/compiler/interview/init
parity passes 141 tests; 11 import/safety checks and the unchanged local doctor
timing plus removed-alias controls pass. These are local results, not hosted NFR
qualification. The local five-run next median is 0.614s with concurrent owned
validation; no causal improvement is inferred from other local runs.

The hosted wheel job now captures a profile and exact decision JSON after the
original latency samples, including when that measurement fails. Every original
workflow step, selector, baseline, ceiling and job timeout is unchanged; the two
diagnostic steps and a step identifier are the sole semantic YAML additions.
Raw profile artifacts contain only the synthetic clean-install fixture, not
credentials or production audio. The full hosted gate remains authoritative.
This is bounded repair of retained Python contracts; Zig parity must preserve
the same demand boundary, public identities and all admission/error behavior.
Other observed positive-fixture and obsolete-husk-helper failures remain owned
before merge, as do hosted doctor timing and current-head startup qualification.

The last observed acceptance/husk replay is red on current source (six failures,
59 passes). The acceptance split now materializes its declared coordination
branch as a real worktree and moves the inherited bare mission directory to the
existing composed layout, preserving its exact content without a second identity.
Its missing-primary-planning and coord-only-clarification assertions are unchanged.
The five husk rows explicitly supply the required coordination metadata; no
obsolete signature or permissive default is restored. Two paired controls prove
a verified primary snapshot rejects legacy coordination metadata while matching
snapshot authority retains the stored topology decision. All 67 checks pass;
no production resolver, acceptance criterion or original assertion changes.

The next hosted run on 006f60f03 again fails clean-install startup: median
1.158s versus the unchanged 1.050s ceiling. Doctor timing and the repaired
acceptance/husk jobs pass. Its newly retained wheel profile shows package-name
metadata inference and eager distribution upgrade transports on the version
lookup path. The profile is diagnostic, not a comparable latency measurement.

Distribution package exports now bind their original objects on demand, so
importing the package-name resolver does not initialize upgrade providers or
their HTTP transport. Ordered export names, object identities, unknown-name
errors and static type exports remain intact. The package-name/provider
selection functions are unchanged, including entry-point precedence, failures,
environment rules and existing caches. A fresh-process import control fails
before the repair. This bounded retained-Python import repair needs equivalent
Zig dependency boundaries; it grants no audio, runtime or merge authority.
Hosted clean-install qualification and all outstanding current-head gates remain
required. The installed-distribution metadata scan remains a measured follow-up;
its ownership and fork precedence must not be weakened to improve timing.

The same hosted profile attributes a separate eager model-construction cost to
the optional event adapter, loaded when the decision log requests only the
sanitizer submodule. The event package now binds its five existing public
objects on demand. A fresh-process sanitizer import is red before the repair;
the identity test pins original ordering and exact adapter/sanitizer objects.
Adapter availability detection, its missing-library errors, sanitization,
decision journaling, event emission and startup admission remain in their
original implementations. Only code imports are deferred, never event capture
or input validation. The hosted timing limit remains unchanged and must pass on
the published candidate; this is not an audio milestone or an external model
quality claim. Zig parity must retain the same public/error and capture rules.

The completed 006 hosted CLI job exposes eight additional failures, reproduced
locally with 38 passing checks. Four positive coordination trials supplied an
empty or unregistered surface; their fixtures now own real worktrees and use the
canonical store to append a typed status event. The modern merge trial likewise
materializes its actual coordination branch, so pre-target done bookkeeping is
tested through the real transaction surface and asserted in target history.
The setup-plan mutant includes its required mission type and retains the exact
missing-spec refusal. Original primary/coord divergence assertions are preserved.
Two strict flattened-topology XFAIL rows actually pass under the explicit-root
transaction target repair, so their markers are retired and all original
assertions become required passing checks.

The eighth failure is a real cold-import regression: decision and retrospective
event modules import status orchestration merely to bind its lock. Those two
imports now occur inside their existing append functions, before any write.
The exact locks, covered write/count regions, journal formats and sanitization
remain unchanged. The existing charter cold-import test passes without changing
its expected absence of status/workspace orchestration. The repaired 46-check
replay passes; further event-lock parity and the complete hosted candidate remain
delivery gates. This is bounded repair of retained Python contracts and fixture
custody; Zig migration must preserve their transactional boundaries. No new
retirement, audio payload, inference or listening approval is credited.
