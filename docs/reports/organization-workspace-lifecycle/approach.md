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

## WP03 creator integration — active draft

User Experience Findings: an initial disposable non-lane retirement case passed,
but its in-process lease did not prove a real producer join. Independent review
also caught missing creation intent and ambiguous duplicate authority keys.
The existing canonical removal policy intentionally disposes of ignored build
state; lifecycle preservation needs a stricter option at that same authority.

Engineering Decisions: commit red regressions before each repair. Exact accepted
PR delivery uses bounded authenticated repository/PR metadata and the exact source
head; local ancestry is insufficient. A new creator owns creation, generation and
participating producer leases. Creation custody precedes Git effects, and an
interrupted creation remains explicit/unproven. Leaving a lease block alone never
certifies success. The owned foreground runner waits under the same fence, and
failure/timeout keeps the generation unreleased. Extract the existing review
process-group signalling authority into the kernel and retain its review wrapper;
no host-wide process scanning or killing. Canonical ignored-state preservation is
opt-in, retaining legacy defaults. Existing unknown/managed backlogs are not adopted.

Known Limitations: final creator/recovery validation, finite deadlines throughout
canonical Git operations, durable completion/startup events, automatic worker and
CLI/service wiring are unfinished. Cooperative foreground production is distinct
from arbitrary detached/scheduled producers; those need their actual owner/fence.
Only disposable fixtures are being created/retired. No WP03 approval, global hook
trust/installation, live backlog deletion or deployment is claimed.

### Completion/worker implementation and operator surface

The producer runner now uses an owned process group and actual joins; canonical
Git subprocesses honor the active finite deadline. Signalling custody ends when
the leader is reaped. Failed/unknown producers remain fenced and unreleased.
Retirement receives the full saved intent and binds its immutable fingerprint in
the creator receipt. Release precedes independent accepted-PR verification.

The queue persists only coalesced wakeups. Its short lock is separate from the
ledger/effect lock. Workers serialize the idle decision and lease release with
enqueue/dispatch so a racing callback cannot lose its wakeup. A malformed/busy
creator produces a durable unknown result without starving healthy creators;
failed obligations retain pending wakeups and require the next real event or
startup/resume. There is no automatic error-spin loop. Diagnostics are observed
state, never release authority.

`worker.py` contains the service class and executable worker in one module,
instead of a separate `service.py` shell: both the CLI and detached child use the
same implementation. This stays within the planned lifecycle authority surface.
The source CLI exposes:

- `workspaces initialize --state-dir DIR`: explicitly admit an empty owned 0700
  directory. Missing prior history refuses rather than silently resetting.
- `workspaces managed-run --state-dir DIR --repo-root REPO --workspace NEW_PATH
  --branch NEW_FEATURE --repository crucible-energy/NAME --repository-id ID
  -- PRODUCER ARGS`: own one new linked checkout, run/join the producer, record
  owner release and enqueue an independent worker. A PR need not exist before
  the producer starts: write private 0600 JSON `{"pr": 123}` to the supplied
  `SPEC_KITTY_LIFECYCLE_RESULT` path. An already allocated PR may instead be
  supplied with `--pr`. Neither hint proves delivery.
- `workspaces resume --state-dir DIR`: enqueue startup recovery and dispatch;
  `workspaces worker --state-dir DIR` runs that same worker in the foreground.
- `workspaces status --state-dir DIR`: report ledger obligations, pending wakeup
  and last worker observation; it does not report workflow completion by guess.

Unknown existing workspaces and external/managed creators are not adopted by the
new Git creator. Source APIs are explicit integration points; installing startup
integration, trust admission and organization-wide adoption belong to WP05.
Remote branch retirement is unsupported and remains separately retained. The
producer profile is bounded POSIX foreground work; arbitrary escaped/scheduled
producers are outside its cooperative fence and never inferred safe.

Review additionally caught a blocked-pass/new-event race: a callback can enqueue
while the incumbent worker holds the lease, then its newly dispatched worker
correctly finds the lease busy. The incumbent must process a newer generation
before exiting, even if its earlier generation was blocked. A synchronized
regression failed once and then passed after the correction; unchanged blocked
generations still do not spin. Public and module workers both exit unsuccessfully
on blocked outcomes. Accepted-PR evidence also binds the source branch name as
well as its commit, repository and default target, so another branch sharing the
same commit is not substituted for this creator's delivery.

The first owning gate found a pre-existing baseline timeout double representing
an already-exited process while expecting it to be signalled. Its timeout case
now models a live/unreaped child (`returncode=None`); the completed-case default
and real process-tree acceptance remain. The no-post-reap signal guard stays.

Coverage is measured with the project's existing source/path configuration plus
subprocess tracing in a retained external config: actual dispatched Python
workers must contribute their executed source, rather than appearing uncovered
merely because they run in a fresh interpreter. No paths are excluded or coverage
thresholds relaxed. Additional refusal tests cover invalid creator/wakeup records
and invalid subprocess-capture configuration. Earlier qualification attempts and
their one failure remain retained; they are not labelled final success.

## WP04 branch-first correction — active

User Experience Findings: live charter/agent instructions direct local-main
consolidation before creating the PR branch, contradicting the owner's PR-only
rule. The existing status-target refusal checks done-bookkeeping policy; target
integration safety must be proved independently through the production path.

Engineering Decisions: canonical occurrence map covers all eight surfaces before
source edits. Preserve historical facts, serialized identities and negative-case
`main` fixtures. Review live guidance/target behaviour individually. No blind
string replacement, global upgrade or new checkout. Reuse the existing owned
lane; inherited four-checkout exception remains bounded to its review checkpoint.

Known Limitations: final unchanged baseline, owning validation, changed-statement
coverage and independent approval remain. Actual feature landing and protected
primary refusal are proven below. Org-wide adoption remains WP05; deployment stays held.

The complete `tests/terminus` harness supplied the actual positive control with no
merge/status/bookkeeping mocks. On the planning candidate, its primary-target run
actually succeeded and advanced local main (red); the feature-target run succeeded
with main unchanged. The new entry gate repairs that concrete defect and the
paired production checks pass. It uses the existing canonical target resolver and
strict ProtectionPolicy decision before status seeding, and rechecks persisted
state before locked effects and after the canonical load.

A symbolic feature alias was admitted by the first entry guard but refused by a
later existing off-target backstop in the retained reproduction. This is not a
claim that that reproduction advanced main. The entry contract now refuses
symbolic landing refs before the writable accessor; concrete feature landing
continues to pass. Primary/configured protection cannot be bypassed with the
operator hatch. Revisions/HEAD cannot substitute for a concrete local branch.

The broader consolidation iteration found legacy successful-landing fixtures that
still target main, as expected under the changed contract. Migrate their target
semantics to actual feature/integration branches with a distinct real primary;
keep primary-refusal cases and all original rollback/reconciliation assertions.
Do not mock or relax the entry guard to preserve the old successful-main path.


The actual acceptance formatter now names an explicit feature/integration target
and PR acceptance, rather than an ambiguous default or direct manual deletion.
Independent review found its minted-branch hint promised removal even under
retention; a new failing regression reproduces that claim, and the repaired hint
refers to the recorded retention/creator cleanup result instead. Acceptance is
not a deletion receipt.

The broader fixture migration preserves original defaults in shared builders;
full-executor positives opt into a feature target with a distinct pinned primary.
Historical issue prose is identified as historical, not rewritten into fabricated
original evidence. Existing content, done/bookkeeping, rollback, resume, refusal
and recovery assertions remain. Boundary-mocked missing-branch units now provide
a real eligible Git target rather than mocking the new protection decision.

Configured narrow mypy exposes three pre-existing import-skip diagnostics in
unchanged acceptance symbols. The exact WP03 base snapshot reproduces the same
three diagnostics, and their ASTs are identical. No suppression, policy change or
claimed clean acceptance type check substitutes for that attributed result.


### Native Git identity and bounded recovery

User Experience Findings: actual late symbolic-ref swaps reproduced both primary
advance/delete and bookkeeping namespace escape. Ordinary OID CAS dereferences
aliases. `--no-deref` alone protects primary but replaces the alias, so it is not
a preservation proof. A real reference-transaction hook also reproduced an
inherited short deadline killing the controller before Git settled its lock.

Engineering Decisions: all canonical ref writes use Git's prepared native
transaction with no dereference, inspect direct identity under that same lock,
and commit only a confirmed direct ref. Refuse aliases, malformed protocol and
unconfirmed commit. Branch writes retain expected-OID CAS; scoped bookkeeping
writes retain their existing single-writer semantics. A parent-owned capture
directory survives abrupt controller termination only until its joining parent
cleans it. The shared process budget supplies an absolute monotonic deadline;
the controller reserves one second for native lock cleanup and owned-group
termination before the outer deadline. No hook overrides or manual lock deletion.

Known Limitations: supported automatic ownership is the documented finite POSIX
profile. Rejected/unknown writes never imply a successful move. Fresh full gates
and independent review must cover the final frozen candidate; earlier full
owning output overlapped these edits and is superseded diagnostic evidence.
The focused actual Git/kernel repair checks passed 18 cases, including a fresh
retry after the injected hook fault is removed.


The first frozen expanded gate found a concrete regression in the existing
expected-parent commit cleanup test: capture cleanup could raise after a native
CAS had returned success, before its caller recorded the landed SHA. Preserve
the joined command's confirmed result and report cleanup separately; never turn
that write into a retryable failure. Before a command result exists, failures
remain unconfirmed. The failing full receipt and direct regression are retained
externally. Admission controls also prove missing capture ownership, nonfinite
or expired deadlines, missing expected old identity, and insufficient outer
cleanup budget cannot start a Git mutation.

## WP05 integration and local adoption boundary

### User Experience Findings

Creator completion/recovery existed, but configuring an organization observation
scope and connecting session events still required an external integrator.
Stale scope reports could look current; a failed registration could suppress
new unknown observations; and a foreground distribution pin did not automatically
pin its detached worker. Integration tests now exercise those boundaries through
real Git stores, scoped fixture GitHub responses and actual joined processes.
The real Spec Kitty acceptance uses a local origin mirror for branch-currentness
checks; it does not disable that gate or contact a production source repository.

### Engineering Decisions

Persist explicit private observation roots and finite bounds. Inventory/discovery
and creator verification run in the background; a session ending is only a
queued hint, never owner release. Bind exact current observations under the real
creator hold, isolate unavailable registrations and preserve historical unknown
rows. Report exact scope, event generation, canonical time and explicit report
currentness. Keep the accessible-inventory and outside-root limits visible.

Pin both hook and worker children to their generating distribution, including
unrelated working directories and hostile ambient module paths. Status/event
operate on the explicit private ledger and skip unrelated global runtime repair
and project-schema checks. Configuration, producer and worker commands retain
normal startup; effects still require independent creator and delivery checks.
The two-second status/enqueue acceptance measures five fresh processes each on
one repository/three registered workspaces/100 settled fixture entries. Preserve
every elapsed sample externally; fixture entries are not real delivery metrics.

### Known Limitations

Source qualification does not install or trust organization hooks. Unsupported
managed creators, unknown history and runtime-dependent work remain retained;
there is no raw Git fallback or inferred adoption. Discovery cooperatively checks
deadlines between directory entries but cannot preempt an uninterruptible
filesystem syscall. The finite POSIX producer profile and remote-branch retention
remain explicit. Deployment is paused. Final frozen gate receipts and canonical
independent verdict are external; intermediate passing checks are not adoption.
