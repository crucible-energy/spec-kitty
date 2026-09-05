---
title: 'Spec Kitty agent ergonomics: recommendations for upstream maintainers'
description: A source-pinned review of agent-facing friction and the smallest improvements that preserve Spec Kitty governance and runtime ownership.
doc_status: draft
updated: '2026-09-05'
---

# Spec Kitty agent ergonomics: recommendations for upstream maintainers

**Recommendation:** make the existing workflow easier to observe and harder to
misread. Preserve the runtime, governance, identity, and review gates; improve the
information crossing their agent-facing boundaries before adding another layer.

**First slice to validate:** preserve the meaning of conditional guidance when formatting
deferred-context fetch instructions. It is a small, testable improvement in an
existing renderer. Next, reconcile context JSON projections and their consumer
contracts. Measure agent outcomes before committing to a broader interface redesign.

This is a standalone report for **Spec Kitty upstream maintainers**, requested
following Lynn Cole's agent-ergonomics critique. It is published for review in
**`crucible-energy/spec-kitty` only**. Audience is not publication authorization:
this work does not request an upstream PR, issue, comment, or policy change.

Research date: **2026-09-05**. Source baseline:
[`Priivacy-ai/spec-kitty` at `614c52cb382d6bbd4ae8d4daab060320502fc14c`](https://github.com/Priivacy-ai/spec-kitty/tree/614c52cb382d6bbd4ae8d4daab060320502fc14c).
All upstream code links below are pinned to that commit. This report is research,
not an accepted design, implemented fix, runtime certification, or benchmark.
The document's draft status does not prescribe GitHub's draft-PR state.

## The decision in one page

Agent ergonomics is the cost of choosing and completing the correct next action:
finding applicable instructions, distinguishing observation from mutation,
understanding a result, recovering from failure, and handing off without losing
authority or evidence. Fewer words help only when those tasks become easier.

The design objective is to reduce unnecessary decisions, tool round trips, and
operator intervention **subject to** correct scope, explicit authorization,
complete applicable governance, compatible interfaces, and reliable recovery.
These constraints can conflict. This report proposes a small, measurable path;
it does not claim a mathematically proven global optimum.

| Priority | Agent-visible outcome | Existing owner; smallest next action | Evidence before expansion |
| --- | --- | --- | --- |
| 1 / F1 | Know exactly when to fetch a deferred rule | Fetch-stanza renderer; preserve authored applicability while retaining valid syntax | Trace production exposure; semantic assertions for authored clauses alongside format tests |
| 2 / F2 | Receive an unambiguous context response | Charter context producer and CLI adapter; specify their projection relationship and handle repeated prose compatibly | Consumer fixtures for action and include paths; version-ledger checks |
| 3 / F3 | Distinguish generated context from context a session actually received | Context-state and host-orientation owners; expose their existing meanings clearly before designing any new receipt | Fresh-session, repeat-load, handoff, and configuration-change scenarios |
| 4 / F4 | Know what a host integration actually supports | Existing roster and session-presence adapters; separate installation from verified loading | Version-pinned installation and effective-context probes |
| Maintainer decision / F5 | Read one consistent publication policy | Upstream governance owners decide policy and reconcile derived instructions | Consistent instructions with explicit authority; no imported fork rule |

The first two are bounded source-level improvement candidates. F3 and F4 need
conformance evidence; F5 needs a maintainer policy decision, not another subsystem.
The connected resume journey below evaluates how these boundaries work together.
Maintainers can stop after any validated slice if its benefit does not justify
the next cost.

## What already works architecturally

Spec Kitty is not starting from a blank slate. The following are source-confirmed
at the pinned revision, not newly proposed capabilities:

- **Progressive disclosure already exists and is the default.** Required
  dependencies are inline; other delivered artifacts remain named and linked
  with applicability guidance. The union of inline and linked artifacts retains
  the delivered set. `--include-all` is already an explicit escape hatch.
  Preserve these completeness and ownership rules.
  [Delivery partition](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/charter/activation/progressive_disclosure.py#L94-L108),
  [CLI option](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/cli/commands/charter/context.py#L56-L64).
- **Context already has a version ledger.** `context_schema_version` is `1.2.0`.
  Its activation-scoped contract is explicitly tracking, not frozen; the ledger
  is a superset of keys that may be emitted, not a requirement that every action
  return every key. Procedures have a typed place; assets are reference-only.
  A new agent-oriented projection should extend this owner, not create a rival
  schema or silently freeze the current one.
  [Context contract](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/charter/activation/context_contract.py).
- **External orchestration already has a versioned boundary.** Contract `1.4.0`
  includes read-only workspace resolution and design/decision operations.
  Runtime decisions distinguish step, query, blocked, decision-required, and
  terminal results; a step requires a valid prompt file. Build on these results,
  not a parallel scheduler or a second next-action protocol.
  [Orchestrator envelope](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/orchestrator_api/envelope.py#L19-L33),
  [Runtime decisions](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/runtime/next/decision.py#L63-L145).
- **Work-package status has one mutation authority.** The event log and its
  status-emission seam already carry transitions and structured review evidence.
  An agent-facing summary must derive from that authority, never become a second
  status store.
  [Status emission](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/status/emit.py#L1-L25).

## Findings and minimal remedies

### F1. Formatting can erase the reason to fetch guidance

**Source-confirmed:** the canonical fetch-stanza normalizer replaces a leading
gerund clause with a generic code-change condition. Authored graph guidance
includes architecture-documentation and design/review conditions. The renderer
therefore has a path that preserves its closed-format grammar while discarding
the domain-specific applicability text. Existing normalization tests protect the
format; that alone cannot establish preservation of meaning.
[Normalizer](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/charter/activation/context_renderers/fetch_stanza.py#L40-L95),
[Authored conditions](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/packs/built-in/agent_profile.graph.yaml#L110-L125),
[Normalization tests](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/tests/charter/test_fetch_stanza_normalization.py).

For example, passing “documenting or reviewing system architecture” to this
normalizer produces “are about to apply a code change.” The cited profile graph
edges are marked composition-only, so this example establishes the transformation
of an authored condition, not that a live session receives that edge's transformed
output. Trace production exposure before prioritizing a runtime fix.

**Inference:** a generic condition makes the agent decide whether a named rule
matters without the specific guidance the graph already supplied. This is a
plausible source of missed or unnecessary fetches, not a measured failure rate.

**Proposed fix:** keep the existing formatter and two-line fetch contract. Choose
a valid grammatical wrapper or explicitly authored normalized clause that retains
the condition's meaning; do not attempt a general English inflector. Add semantic
tests using actual graph inputs, including documentation-only work, alongside the
existing regex tests. Preserve selectors and fallback behavior for genuinely
missing guidance. Confirm the affected production rendering path before claiming
an end-to-end repair.

### F2. The context adapter repeats prose and projects only part of its producer

**Source-confirmed:** action JSON emits the same `result.text` under `context`
and `text`; the include path similarly repeats `included_text`. The producer's
contract includes `procedures` and `directives_source`, but the action CLI
wrapper does not copy those keys. This establishes a projection difference, not
by itself a broken consumer contract or a measured token saving.
[CLI serialization](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/cli/commands/charter/context.py#L97-L194),
[Producer](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/charter/activation/context.py#L470-L631),
[Contract ledger](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/charter/activation/context_contract.py).

**Proposed fix:** document which fields the CLI promises and test that projection
against realistic producer output. Establish whether each omission is intentional
before adding keys. Inventory consumers of both prose aliases; then select a
canonical field with an explicit compatibility/deprecation path, or introduce a
justified compact projection within the existing contract. Do not simply delete
an alias because it looks redundant. Keep machine IDs, provenance, applicability,
errors, and fetch references even when reducing prose.

The near-term win is one explainable producer-to-adapter relationship. A new
command, schema family, or context compiler is unnecessary unless a concrete
consumer need proves otherwise.

One follow-up contract question is reference identity: reference entries retain
bare IDs rather than full target URNs, while generic artifact lookup rejects
cross-kind ambiguity. No shipped collision was established. If a consumer needs
unambiguous standalone retrieval, derive a target URN or supported selector from
the existing edge; distinguish reference-only assets from fetchable artifacts.
Do not broaden the first slice to solve an unproven collision.
[Reference projection](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/charter/activation/progressive_disclosure.py#L40-L71),
[Ambiguity handling](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/charter/activation/context_renderers/template_include.py#L205-L243).

### F3. First-load bookkeeping is not proof of session receipt

**Source-confirmed:** `--mark-loaded` defaults true. First-load bookkeeping is
stored by repository and action; explicit depth overrides the default, otherwise
the first-load path uses depth two and later loads depth one. Applicable builders
write the timestamp only when both marking and first-load conditions hold.
`--no-mark-loaded` suppresses that acknowledgment write; it still reads existing
state. It does not mean fresh-session context or prove the entire command has no
side effects.
[CLI defaults](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/cli/commands/charter/context.py#L28-L43),
[State semantics](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/charter/activation/context_state.py#L79-L109),
[Conditional writes](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/charter/activation/context_result_builders.py).

**Important counterevidence:** upstream already tests that active directives,
styleguides, and toolguides remain available on subsequent loads. A depth change
is not evidence of wholesale governance loss.
[Repeat-load tests](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/tests/charter/test_every_load_delivery.py#L114-L138).

**Proposed fix:** first document and expose the distinction between generated,
marked, installed, and actually received context in existing diagnostics. Test a
new agent session after another session has marked an action. Only introduce a
session receipt if that experiment demonstrates a need. A receipt would need
explicit scope and invalidation on relevant authority changes; it must not cache
permission, replace governance resolution, or imply model understanding. No new
receipt store is required by this report.

### F4. A support label hides different integration capabilities

**Source-confirmed:** the session-presence registry names four `NullWriter`
entries (`qwen`, `kilocode`, `auggie`, and legacy `q`); unknown keys also fall back
to the null writer. This is an orientation-subsystem fact, not evidence that
these hosts cannot use Spec Kitty commands. A non-null writer similarly does
not prove the host loaded its output. Skill-only host fallbacks deserve their
own verification rather than an assumption of parity.
[Registry](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/session_presence/writers/registry.py#L30-L62),
[Null writer](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/session_presence/writers/null_writer.py),
[Skills preamble fallback](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/session_presence/writers/skills_preamble.py).

Separately, upstream's maintainer instructions announce six skill agents but
list four; the canonical skill-only roster contains four. That is documentation
drift, not proof that two integrations are broken.
[Maintainer roster](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/AGENTS.md#L80-L109),
[Canonical roster](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/skills/_agent_roster.py#L23-L29).

**Proposed fix:** derive or check roster documentation against its existing owner.
Report separate capabilities for command installation, orientation delivery,
effective-context verification, and resume behavior. Record host version and
probe date. Use existing setup/orientation diagnostics; do not create another
independent supported-host list. Vendor lineage and current host behavior must
be verified before prioritizing a legacy adapter.

### F5. Startup instructions should reduce authority choices, not add them

**Static document measurement:** the pinned upstream maintainer `AGENTS.md` and
charter Markdown total **77,497 bytes across 1,238 lines**. These are file sizes,
not tokens, actual injected context, consumer-project startup volume, or evidence
of slow execution. Individual counts and reproduction commands are below.

**Source-confirmed instruction tension:** `AGENTS.md` conditions publication on
an explicit user request, while a charter workflow passage directs immediate
branch publication and PR creation. The documented charter-precedence rule
resolves which document governs, but does not eliminate the confusing competing
instructions. Upstream also has a draft-first instruction; that is different
from this fork's non-draft policy. This report does not transplant fork policy
into upstream or claim the prose conflict is a runtime authorization bypass.
[Publication instruction](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/AGENTS.md#L51-L66),
[Charter workflow](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/.kittify/charter/charter.md#L350-L365),
[Charter PR instruction](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/.kittify/charter/charter.md#L165-L180).

**Proposed fix:** maintainers decide the intended upstream publication policy,
then reconcile derived instructions through their canonical source. Shorten
orientation by eliminating duplicated explanations and routing to action-scoped
details, not by removing binding constraints. Keep an explicit authority map:
runtime project-charter metadata keys on `charter.yaml`; `charter.md` is its
display surface, and the repository still instructs agents to read it. Do not
promote a compact summary into a competing governing artifact.
[Charter metadata boundary](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/specify_cli/cli/commands/charter/context.py#L175-L187).

## One connected experience, not another workflow

Use the following as an **acceptance scenario**, not a new CLI or serialized
schema. The existing owners supply each part:

1. **Observe:** identify the Mission, work package, resolved workspace, applicable
   authority, current decision, and whether an operation reads or changes state.
2. **Act:** execute the existing runtime-supplied action within its authorization;
   fetch linked guidance when its preserved condition applies.
3. **Verify:** inspect result and evidence; distinguish a valid query, blocker,
   decision request, rejection, and successful transition. A successful tool
   exit is not automatically an approved work package.
4. **Resume:** resolve current authority again after interruption. Retain durable
   evidence, not a chat summary as state. Human approval and publication remain
   separate, explicit boundaries.

Do not hand-construct workspace paths or infer authority from an open worktree.
Do not infer a Git commit from the word “committed”: upstream's committed-state
resolver explicitly defines its working-tree semantics and distinguishes merged
from in-flight Mission ownership.
[Authority resolver](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/src/runtime/next/committed_authority.py).

This connected scenario should consume the existing next decision, orchestrator
envelope, charter output, and status evidence. If an adapter must join them, keep
it a derived view with owner/version provenance, not a write-capable coordinator.

## Transferable lessons from other approaches

The relevant comparison is interface behavior, not a leaderboard of brands.
Three public sources offer useful experiments without adding harness dependencies:

- **Agent-computer interface research:** SWE-agent studies how interface design
  changes agent behavior and software-task performance. Transfer the practice of
  testing the interaction surface itself, not its historical benchmark scores or
  a claim of current leadership.
  [SWE-agent paper, version 3](https://arxiv.org/abs/2405.15793v3).
- **Tool design and evaluation:** Anthropic recommends purposeful tool boundaries,
  relevant results, actionable errors, and task-based evaluations. Transfer these
  principles to existing Spec Kitty outputs. A concise format is a hypothesis to
  test; neither JSON nor fewer tools is universally optimal.
  [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents).
- **Progressive skill loading:** the Agent Skills specification separates discovery
  metadata, activated instructions, and supporting resources. This supports
  Spec Kitty's existing disclosure direction. It does not prove any particular
  host loads every file correctly or enforces experimental permission metadata.
  [Agent Skills specification](https://agentskills.io/specification).

An MCP facade, a new implementation language, a larger context window, persistent
memory, or more agents would not by itself fix lost applicability, inconsistent
projections, or ambiguous authority. Those options remain possible, but should
answer a measured bottleneck. Broad ecosystem comparison belongs in a separate
landscape study; this upstream decision does not depend on private organizational
repositories, unpublished harnesses, or the companion fork report.

## Evaluation and rollout: proposed, not run

First reproduce F1 and F2 with deterministic, narrow fixtures at a pinned revision.
Retain existing syntax, completeness, identity, and authority tests. Establish the
current contract before changing it; a fixture for proposed behavior is not proof
the current branch already passes.

Deterministic semantic, syntax, and completeness checks can close the small F1
slice on their own. The host/model experiments below support broader interaction
and performance claims; they are not an automatic new gate on every formatter fix.

Then compare baseline and candidate on fresh disposable consumer projects using
the same Mission inputs, source/install versions, doctrine configuration, host
versions, model settings, permissions, and environment. Separate cold start,
warm start, and resumed sessions. Do not mix installed CLI output with a different
source checkout or import a fork measurement as an upstream baseline.

The minimum journey set is first orientation, implement, review rejection and
repair, interrupted resume, read-only inspection, missing optional integration,
and configuration change after a prior context load. Use one slash-command host
and one skill-based host first, then expand according to actual usage and risk.

Record:

- Time and tool calls to the **first valid task action**; speculative edits and
  skipped required context do not count as success.
- End-to-end completion, retries, wrong-command attempts, unnecessary fetches,
  operator interventions, and interruption-recovery success.
- Serialized bytes and actual model-input tokens separately, with tokenizer and
  host-capture method; distinguish an emitted file from confirmed receipt.
- Required-guidance completeness, stable machine identity, unchanged read-only
  state, preserved permissions, and durable review evidence as hard constraints.
- Costs and latency distributions, sample size, failures, timeouts, excluded runs,
  and uncertainty. Freeze the evaluation cases and success rules before scoring;
  retain held-out tasks and unsuccessful runs rather than retrying to green.

Set numerical performance targets after a reproducible baseline, not by choosing
an attractive percentage now. Ship only with the hard constraints preserved and
a demonstrated improvement whose complexity is justified. If a smaller response
causes more fetching, mistakes, or operator work, revise or reject it. Compatibility
changes require consumer coverage and a documented rollback/deprecation path.

## Evidence boundary and reproduction

The review inspected fetched upstream source without executing that upstream CLI,
running its tests, or conducting model/host experiments. Findings labeled
source-confirmed are static claims only. Proposed runtime effects remain
hypotheses. Public external sources were consulted on the research date; they
support transferable practices, not a current comparative ranking.

Reproduce the static document counts from a checkout containing the pinned commit:

```sh
git show 614c52cb382d6bbd4ae8d4daab060320502fc14c:AGENTS.md | wc -lc
git show 614c52cb382d6bbd4ae8d4daab060320502fc14c:.kittify/charter/charter.md | wc -lc
```

| Document | Newline count | Bytes |
| --- | ---: | ---: |
| Upstream maintainer AGENTS.md | 630 | 40,293 |
| Upstream charter Markdown | 608 | 37,204 |
| Combined | 1,238 | 77,497 |

Do not reuse the earlier fork report's CLI timings, payload sizes, installed-version
mismatch, or Researcher Robbie/Rosa discrepancy as upstream findings. At this
upstream revision the Robbie identity and initialization agree, and built-in
doctrine assets live under `packs/built-in/` rather than the fork's older paths.
[Current researcher profile](https://github.com/Priivacy-ai/spec-kitty/blob/614c52cb382d6bbd4ae8d4daab060320502fc14c/packs/built-in/agent_profiles/researcher-robbie.agent.yaml).

For review disposition and document-validation results, see the
[QA record](2026-09-05-agent-ergonomics-upstream-qa.md). That record is evidence
about this report, not a certification of the proposed product changes.
