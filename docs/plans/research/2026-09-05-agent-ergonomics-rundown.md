---
title: 'Agent Ergonomics Rundown: Spec Kitty'
description: Evidence-backed audit of what agents see, where interaction cost accumulates, and how to make the canonical Mission workflow faster and clearer.
doc_status: draft
updated: '2026-09-05'
---

# Agent ergonomics rundown: Spec Kitty

Research snapshot: **2026-09-05**. Requested by Sam following Lynn Cole
(`lynncoleart`)'s request to evaluate what an agent sees and recommend a faster,
cleaner experience.

**Decision status:** research and recommendations, not an approved architecture,
a new governing policy, an implemented improvement, or a comparative benchmark.
“Draft” is this document's research status, not a GitHub draft-PR instruction.

## Executive recommendation

Make Spec Kitty's existing deterministic runtime the agent's small, dependable
working interface. Keep the governance and evidence; stop making the model
reconstruct their application from multiple large instruction surfaces.

The first investment should be **orientation, effective-context visibility,
compact machine output, and error recovery**, followed by cross-harness
conformance and continuity tests. A language rewrite or another orchestrator is
not the first answer. Spec Kitty already has next-action decisions, canonical
workspace resolution, event-sourced work-package state, and a versioned
orchestrator envelope. These are valuable foundations to expose more clearly.

Lynn's concern has concrete support in this audit:

- The fork's required startup documents contain **69,147 UTF-8 bytes across
  1,185 lines** before the agent reads its task-specific profile, skills, or
  source. This measures document volume, not tokens or proof of model failure.
- A compact action-context JSON response contains **21,442 bytes**, including
  identical prose in `context` and `text`. One duplicate value accounts for
  7,623 bytes before JSON escaping.
- A version query emits 2,775 bytes over 29 lines, including artwork, even with
  captured output and color disabled.
- Session-orientation integration is explicitly a `NullWriter` for Qwen,
  Kilocode, Augment, and the legacy Amazon Q key at the inspected revision.
  Command installation is therefore not equivalent to working orientation.
- Canonical profile output identifies Researcher Robbie but declares Researcher
  Rosa. The mismatch is small, but demonstrates why checking the agent's actual
  input matters.
- Runtime, skill, command, profile, and host versions must be distinguished. This
  session found source version 3.2.7 alongside an installed distribution at 3.2.6.

Do not “fix” this by deleting safety rules or letting agents skip required
governance. Compile the applicable constraints into a compact, inspectable view,
retain authoritative sources, and validate that each supported harness actually
receives and respects the intended scope.

## Reading map

| Need | Read |
| --- | --- |
| Decide the first implementation slice | [Prioritized findings](#prioritized-findings) and [delivery sequence](#delivery-sequence) |
| Check the evidence | [Local observations](#local-observations) and [source register](#source-register) |
| Understand the proposed interface | [Agent-facing contract](#agent-facing-contract-proposed) |
| Compare external and Crucible alternatives | [Transferable comparisons](#transferable-comparisons) |
| Design a credible speed/quality experiment | [Evaluation protocol](#evaluation-protocol-not-run) |
| Explore the full ecosystem | Kaizen landscape report at the repository path below; publication not assumed |

The Kaizen report is available in the paired local checkout at
`docs/research/agent-ergonomics/2026-09-05-landscape.md`. The path identifies
the companion artifact without assuming a remote branch has been published.

## Scope and evidence discipline

The source authority for this audit is the **Crucible fork**, commit
`50207b4333fdc886ed67fb27757dfb75e5b3b153`, based on its fetched
`origin/main`. The original working checkout contained unrelated user edits;
research and report changes were isolated in a separate worktree.

Upstream is useful read-only reference material. Reading or fetching upstream
does not authorize publishing there. No upstream issue, comment, branch, or PR
is part of this recommendation. Shared-project improvements can be proposed
separately, with explicit permission and without fork-specific governance noise.

Evidence labels used throughout:

- **Observed:** output collected locally with the described environment.
- **Source-confirmed:** behavior visible in code at a specified revision; not
  necessarily rerun end to end.
- **Documented:** an owning project's published contract, retrieved on the
  research date; not a reliability certification.
- **Inference:** our explanation or design conclusion from evidence.
- **Proposed:** unimplemented work or an unrun experiment.

This is not a complete production journey benchmark. No fresh Mission was
advanced, no implementation agent was launched against a provider, and no paid
comparison was run. The report cannot recover every past conversation, inspect
closed vendor internals, or establish that every branch of every sibling has
been audited. Kaizen retains the broad inventory and explicit coverage gaps.

## What the agent sees

A fresh agent is asked to do useful work but first has to determine several
different things: which rules bind, which executable is active, which command
family applies, which Mission and workspace own the task, and what it may change.

The existing journey is not entirely linear. Different entry points can deliver
different amounts of already-resolved context:

| Entry point | Useful affordance | Burden or uncertainty to inspect |
| --- | --- | --- |
| Repository bootstrap | AGENTS and charter make rules durable | Large starting surface; repeated explanations; harness-specific loading semantics |
| Skill discovery | Short metadata routes to canonical procedures | Many visible skills/aliases can compete for the same intent |
| Profile lookup | Structured role, directive, and tactic references | Human name, identifier, and initialization declaration can drift |
| `charter context` | Action-scoped context and provenance | Duplicate prose; load-cache side effect by default; action/type distinction |
| `next` | Deterministic query/step/blocked/decision-required/terminal result | Agent must know this is the canonical loop rather than infer workflow from prose |
| Action prompt | Resolved workspace and governance payload contract | Need evidence of final rendered content, not only template text |
| Host integration | Native commands, skills, rules, hooks | Installed artifacts do not prove effective instruction loading |
| Review/publish handoff | Repository policy requires closure and operator merge | Transcript summaries are insufficient receipts for remote state |

The inspected implementation prompt already states that action-critical
governance is included or replaced by conditional fetch instructions when a
budget is exceeded. That is a good existing design, not a missing capability to
reinvent. Likewise, REASONS blocks are rendered conditionally by the SPDD
template renderer; seeing a block in source is not proof that every agent
unconditionally receives it. Audit the **rendered prompt** for the selected
Mission, charter, profile, host, and action. [S06, S07]

An interaction error during this research illustrates the discovery problem:
a researcher guessed `agent profile load`, but the canonical command is
`agent profile show`. The parent similarly tried placing
`orchestrator-api` under `agent`; it is a top-level group. These were agent
guesses, not evidence that documented commands are broken. The product
opportunity is to make such guesses unnecessary and recovery immediate.

## Local observations

### Method

Measurements are retained in
[the machine-readable evidence file](2026-09-05-agent-ergonomics-measurements.json).

The environment was macOS 26.6.2 on ARM64, using the installed Spec Kitty entry
point and interpreter/dependencies with `PYTHONPATH` pinned to the fork's
3.2.7 source. Installed distribution metadata reported 3.2.6. This mixed
development environment is useful for a local interaction observation but is
**not** a clean release-performance benchmark.

Each command ran in three sequential fresh processes with stdout/stderr
captured, `NO_COLOR=1`, and `TERM=dumb`. OS/import/filesystem caches were not
reset. Timings are descriptive medians, not p95 estimates or statistically
established comparative results. No tokenizer was used. The final context
measurements used `--no-mark-loaded`; an earlier exploratory call used the
default load-cache behavior. Both final context variants reported
`first_load=false` and `references_count=0`.

| Command suffix after `spec-kitty` | Median seconds | Output bytes | Lines | Observation |
| --- | ---: | ---: | ---: | --- |
| `--version` | 0.8410 | 2,775 | 29 | Artwork in a machine-captured version query |
| `--help` | 0.8027 | 2,957 | 56 | Top-level discovery |
| `next --help` | 0.4847 | 3,012 | 34 | Rich layout; canonical loop described |
| `agent --help` | 0.8743 | 2,352 | 22 | Additional discovery layer |
| `agent profile show researcher-robbie --json` | 1.2228 | 2,491 | 60 | Valid JSON; identity mismatch |
| `charter context --action implement --no-mark-loaded --json` | 3.8632 | 21,442 | 120 | Duplicate `context`/`text` |
| Same, with `--mission-type software-dev` | 4.0132 | 21,442 | 120 | Same size in this repo-root observation |
| `orchestrator-api contract-version` | 0.8593 | 300 | 1 | Compact, valid, versioned JSON |

All listed commands exited zero. The explicit Mission-type run ranged from
3.9505 to 5.8564 seconds; it is particularly inappropriate to infer stable tail
performance from three observations. Neither context result demonstrates the
size of a live work-package action prompt.

| Required source | Bytes | Whitespace words | Lines |
| --- | ---: | ---: | ---: |
| `AGENTS.md` | 37,402 | 4,544 | 650 |
| `.kittify/charter/charter.md` | 31,745 | 4,351 | 535 |
| Combined | 69,147 | 8,895 | 1,185 |

The JSON file retains all three runs and document SHA-256 values. For
reproduction, use a disposable checkout at the pinned revision, record the
interpreter and installed distribution, capture each listed command with a
monotonic subprocess timer, and count UTF-8 bytes and newline-delimited lines.
Run a separate clean-install baseline before attributing latency to product
code. Never advance a real Mission merely to measure startup.

### What these observations do and do not show

They establish avoidable output duplication and a high-volume starting surface.
They suggest investigating context-building and import/setup overhead. They do
not show where those seconds are spent internally, what a model actually
attended to, or how much faster a task would finish with a smaller prompt.

A static command can be slow but rarely called; a tiny error can be cheap once
but repeated twenty times. End-to-end useful progress is the optimization
target. Measure call frequency and repeated discovery before prioritizing a
rewrite on wall-clock microbenchmarks alone.

## Existing strengths to retain

1. **One state authority:** append-only status events and materialized views,
   rather than frontmatter becoming a second live lane-state owner. [S08]
2. **Deterministic next action:** `DecisionKind` represents query, step,
   blocked, decision-required, and terminal outcomes. An invalid step cannot
   quietly omit a usable prompt file. [S03]
3. **Canonical workspace resolution:** action/runtime code resolves the
   execution workspace; an agent need not synthesize a path from a slug. [S03]
4. **A versioned machine envelope:** contract version 1.3.0 has seven canonical
   keys, correlation identity, success/error separation, and structured data.
   The 300-byte contract-version response demonstrates the desired direction.
   This does not mean every CLI command already uses that contract. [S04]
5. **Generated integrations:** one renderer can produce consistent command
   bodies for skill-based agents; source templates remain authoritative. [S05]
6. **Action-critical governance budgets:** the implementation prompt contract
   already describes bounded payloads and conditional retrieval. [S06]
7. **Honest stop states:** ambiguous selectors, missing prerequisites, and
   permission barriers should remain explicit—not bypassed for apparent speed.
8. **Review closure policy:** answering findings and reconciling GitHub state is
   an explicit completion obligation, a strong basis for a useful final receipt.

## Prioritized findings

Priorities reflect expected leverage and safety, not measured implementation
effort. Each row identifies a concrete seam and an acceptance condition for a
future implementation. No row is a claim that its fix has shipped.

| ID / priority | Evidence and consequence | Recommended change | Acceptance evidence |
| --- | --- | --- | --- |
| E01 / P0 | 69,147 bytes in mandatory bootstrap sources; task relevance must be reconstructed [S01–S02] | Keep a short always-on safety/authority kernel and compile action-specific context from the charter | Required rules survive; no competing authority; measured bytes/tokens by source |
| E02 / P0 | Duplicate `context` and `text` JSON values [S09] | Add an explicitly versioned compact representation with one content body and references | Legacy consumers remain compatible; golden output has no duplicate body |
| E03 / P0 | Multiple entry-point namespaces and witnessed command guesses [S03–S05] | Supply a small orientation response with exact existing next invocation | Fresh agent reaches first legal action without namespace guessing |
| E04 / P0 | Runtime/source mismatch observed | Include executable, source/package version, contract version, and relevant drift diagnosis in orientation | Stale-install fixture names one safe remedy; no blind upgrade/install |
| E05 / P0 | Fork read and publication authority are different [S01–S02] | Carry explicit repository identity and allowed effect destinations in action receipts | Compaction/resume never authorizes upstream; shell/API paths tested within stated enforcement coverage |
| E06 / P0 | Code completion does not close review threads [S02] | Emit finding-by-finding closeout evidence and unresolved count | Each actionable thread has disposition/reply; resolution verified or exact blocker reported |
| E07 / P1 | Four named session-orientation entries use `NullWriter` [S10] | Refresh capability research, then implement/test writers through canonical surfaces | Harness loads a scope sentinel; unsupported orientation is reported, not silently “supported” |
| E08 / P1 | Generated file semantics differ between hosts | Use a capability/version matrix with precedence and effective-context probes | Root and nested rules, custom profiles, resume, and missing credentials tested per host |
| E09 / P1 | Robbie/Rosa identity mismatch [S11] | Validate profile identifier/name/declaration consistency and resolve intended naming | Canonical source corrected with focused regression evidence; no copied profile edits |
| E10 / P1 | Context command marks loaded by default [S09] | Make observation versus load acknowledgment explicit in the machine contract | Inspection can be repeated without changing cache or workflow state |
| E11 / P1 | Action/type and generic context are distinguishable [S09] | Return effective action/type and resolution provenance clearly | Typeless root request is explicit; no false software-dev inference |
| E12 / P1 | `--version` artwork and differing help presentation observed | Offer plain version plus consistent machine-safe output conventions | One bounded version result; no ANSI/artwork in machine mode; useful human mode retained |
| E13 / P1 | AGENTS states six skill agents but its table/renderer roster enumerate four [S01, S05] | Generate capability documentation from a single roster plus dated conformance receipts | Counts, paths, and maturity labels agree; no unsupported parity claim |
| E14 / P1 | Resume can otherwise depend on conversational summaries | Rehydrate goal, corrections, current state, constraints, and evidence from authoritative records | Interrupted work resumes without repeated mutation or lost fork boundary |
| E15 / P2 | Dynamic context may compete with provider prefix caching | Budget stable policy/tool prefix separately from changing work state | Compare actual cached/input tokens and verified completion, not bytes alone |
| E16 / P2 | Error recovery often requires additional prose/search | Return cause, preserved state, retry classification, and one exact recovery action | Injected failures do not cause repeated identical failed calls |
| E17 / P2 | A broad workflow can overwhelm a tiny scoped task | Apply explicit charter-approved rigour tiers | Small edits retain evidence/authority while avoiding unnecessary orchestration |
| E18 / P2 | Current local timings are coarse subprocess observations | Profile imports, resolver, context assembly, and I/O independently | Clean release baseline and reproducible traces precede performance architecture decisions |
| E19 / P0 | AGENTS and charter say to file an upstream gap, while fork policy requires specific publication permission; a later AGENTS section also omits the earlier publication condition [S01–S02] | Propose permission-first wording through governance review; compile effective scope without contradictory action advice | Missing-command and post-local-merge fixtures record findings locally and do not publish without the specific grant |

P0 is a recommendation ordering, not a declaration that every row is a current
security exploit. Runtime enforcement must be scoped honestly: a prompt or a
single hook cannot constrain arbitrary shell/network access in an uncontrolled
host. Where Spec Kitty cannot intercept an effect, say so and rely on the host's
actual policy boundary, with a visible residual-risk statement.

## Agent-facing contract (proposed)

This is an **additive projection over existing authority**, not another Mission
database, a replacement orchestrator, or new commands that already exist.

### The common path

~~~text
user intent + current corrections
             |
canonical identity / state / workspace / charter resolution
             |
small action capsule + capability/authority receipt
             |
native harness: inspect -> edit -> validate (bounded inner loop)
             |
evidence + state transition -> next capsule
             |
authorized fork publication -> checks -> thread closure -> operator merge
~~~

Research/read-only tasks can end with durable findings without entering the
publication path. A local merge, a pushed branch, a reviewed PR, and an operator
merge are distinct states. The diagram's last path requires its own authority.

A conceptual capsule might contain:

~~~json
{
  "projection_version": "proposed-1",
  "source_revision": "opaque-state-revision",
  "mission_id": "resolved-canonical-id-or-null-for-ad-hoc-work",
  "goal": "one current bounded objective",
  "workspace_ref": "resolved-workspace-handle",
  "authority": {
    "repository": "verified-fork-repository-identity",
    "publication": "not-authorized-by-this-task",
    "constraints_ref": "content-addressed-effective-constraints"
  },
  "decision": {
    "kind": "query",
    "next_invocation": ["an", "existing", "canonical", "command"]
  },
  "blockers": [],
  "evidence_refs": [],
  "context_ref": "inspectable-effective-context-receipt",
  "changed_since": null
}
~~~

These illustrative fields are **not a supported API schema**. Select exact
names through the existing orchestrator contract and glossary. In particular,
do not repurpose display numbers as Mission identity or invent a new meaning
for `primary` or `merge`.

### Context should be explainable

For each item entering the model's active context, retain:

- Source owner, path/handle, content hash, retrieval time, and applicability.
- Whether it is binding instruction, user correction, source evidence,
  derived summary, or untrusted external content.
- Why it was included; why another candidate was omitted, superseded, or
  deduplicated.
- Estimated size versus tokenizer/provider-measured size.
- Which host loaded it, which rule took precedence, and whether its restriction
  is merely guidance or technically enforced.

Do not inject this entire receipt every turn. Supply a small summary and a
drill-through handle. Keep the full, access-controlled trace for diagnosis.
Never export raw prompts, credentials, private transcripts, or provider-internal
reasoning by default.

### Durable continuity without transcript worship

Keep current task identity and state in canonical records. Keep accepted user
corrections and granted scope as versioned facts. Retain raw session evidence
subject to access/retention policy. Reconstruct the active context as a bounded
view rather than treating a generated summary as permanent truth.

A resume must distinguish:

1. A command never started.
2. It started and failed before a durable change.
3. A durable change happened but its response was lost.
4. An external effect has an ambiguous outcome.
5. Work is waiting for input, capacity, review, or a real permission grant.
6. Work completed locally but has not been published or externally reconciled.

Safe retries need idempotency or effect reconciliation. A file checkpoint cannot
undo a GitHub comment, sent message, remote push, database write, or paid model
call. Avoid claiming exactly-once external execution from an event log alone.

### Rigour should be proportional

Propose tiers through the charter, not by silently bypassing it:

| Work shape | Minimal useful proof | Extra structure only when justified |
| --- | --- | --- |
| Read-only question or research | Sources, uncertainty, durable answer if requested | No implementation workspace or release workflow solely to answer |
| Small local prose/config correction | Scoped diff and relevant existing checks | No model council merely because delegation exists |
| Ordinary behavioral change | Red-first evidence, code/tests, review-ready result | Full discovery only for unresolved material requirements |
| Cross-package/domain Mission | Specification, dependencies, owned workspaces, architectural evidence | Parallel packages where genuinely independent |
| Protected external effect | Exact target, current grant, policy decision, effect receipt, recovery | Additional approval only when existing authority is insufficient |

## Transferable comparisons

This table selects lessons for Spec Kitty; Kaizen's evidence appendices retain
the wider product coverage and detailed limitations.

| Comparison | What to borrow | What not to infer |
| --- | --- | --- |
| Codex / Agent Skills | Metadata-first discovery, bounded delegated exploration, native resume | Skills are not universal technical permission enforcement; delegation has cost |
| Claude Code / SDK | Effective-context inspection, scoped rules, native loop/tool reuse | CLAUDE.md automatically means AGENTS.md was loaded; rewind covers all effects |
| Cursor | Lazy tool/output discovery and hybrid retrieval experiments | Vendor token reduction is our forecast; hooks always fail closed |
| Qwen Code | Structured dual output and explicit fork-context semantics | Narrowed tool execution necessarily means a smaller model-visible tool schema |
| Gemini CLI | Policy-shaped tool availability and trace-based behavioral evals | A checkpoint or telemetry switch proves complete rollback/privacy |
| DeepSeek Harness preview | Reconstructable model-input event projection and explicit compaction seams | Preview contracts are stable release compatibility guarantees |
| Kimi / Pi / mini-SWE-agent | Small task boundaries and minimal-loop comparison baselines | Minimality alone proves production suitability |
| Kiro / Antigravity | Task-size modes and decision-ready artifacts | Fast mode grants new external authority |
| Junie / Zed / external ACP agents | Explicit instruction precedence and runtime ownership | A host automatically passes all its rules to an external harness |
| Kaizen | Changed-field projections, provenance, honest unresolved state | Kaizen should become a second Mission-state owner |
| Nano Kitty | Resident session handles, inspect/steer/cancel/result, replay-bound control | Its narrow personal safe-echo tool is already a general coding runtime |
| Zig Kitty | Native startup/parity experiments and safe unsupported refusal | v3.2.5-scoped audit proves full parity with this 3.2.7 source |
| Elastic Fog Chorus | Versioned admission tiers, correlated client/router traces | T0/T1 launch evidence proves T4 coding or T6 production readiness |
| ThickTicket | Small workflow kernel and missing-evidence rejection | A new second kernel is needed in Spec Kitty |
| SugarFang / historical Qwench / OpenAI Codex snapshot | Inspectable context budgets, durable-memory separation, compaction fixtures | Local directory names establish repository ownership, or historical/private source proves deployment |
| PDB / Technonomicon | Immutable admitted guidance, provenance, applicability, leakage controls | Successful generated advice may self-promote into authority |

External primary references:
[Codex skills](https://learn.chatgpt.com/docs/build-skills),
[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Claude instructions](https://code.claude.com/docs/en/memory),
[Cursor dynamic discovery](https://cursor.com/blog/dynamic-context-discovery),
[Qwen subagents](https://qwenlm.github.io/qwen-code-docs/en/users/features/sub-agents/),
[Gemini behavioral evaluations](https://geminicli.com/docs/behavioral-evals/),
[DeepSeek architecture](https://deepseek-harness.github.io/deepseek-harness/en/reference/),
[Junie instruction lookup](https://junie.jetbrains.com/docs/junie-ide-plugin.html),
[Zed external agents](https://zed.dev/docs/ai/external-agents).
Crucible commit-pinned evidence is collected in the Kaizen companion.

A relevant paper tested repository context files and found no general success
improvement and increased inference cost in its studied setting. That is a
reason to measure relevance, not permission to remove this repository's binding
charter. Likewise, interface-design and long-context papers motivate experiments
without forecasting current model behavior.
[Evaluating AGENTS.md, v2](https://arxiv.org/abs/2602.11988v2),
[SWE-agent ACI study](https://arxiv.org/abs/2405.15793),
[Lost in the Middle](https://arxiv.org/abs/2307.03172).

## Evaluation protocol (not run)

### Keep the comparison identifiable

Pin separately: task and repository revision; harness version; model/provider
revision and auth route; prompt/profile/skill versions; tool-schema hash;
permission mode; execution image/resources; cache state; network policy; and
budget. Compare the same model under native and governed paths when feasible.
Run a separate same-task comparison across models. Do not confound both changes
and call the result a harness effect.

Use Elastic Fog/Kaizen's existing admission and outcome seams, not a new
leaderboard. Start with no-spend deterministic fixtures and prerecorded,
rights-cleared traces. Real provider trials need explicit spending authority.

### Initial task suite

| Case | Required result | Main friction metric |
| --- | --- | --- |
| Fresh agent, tiny prose edit | Correct scoped artifact and existing validation | Calls/time before first useful action |
| Existing Mission resume | Correct state/workspace with no duplicate transition | Repeated reads and lost constraints |
| Source/install drift | Diagnose active executable before changing environment | False failure attribution and needless installs |
| Invalid/ambiguous selector | One precise disambiguation path; no silent fallback | Failed command loops |
| Nested instructions | Fork rule survives host precedence | Effective-rule coverage |
| Large tool catalog/log | Retrieve relevant slice without losing constraints | Irrelevant context and repeated output |
| User correction then compaction | Latest scope wins after resume/model switch | Constraint retention |
| Interrupted mutation | Reconcile outcome before retry | Duplicate effect count |
| Parallel independent packages | No user-edit loss or ownership collision | Verified wall-clock savings and merge cost |
| Permission denial | Safe in-scope progress plus exact unmet requirement | Repeated asks and false completion |
| Review thread | Evidence reply and actual resolution, or exact blocker | Findings without disposition |
| Protected publication | No upstream write without specific grant | Any unauthorized effect is a hard failure |

Record verified-completion rate, time to first useful action, total completion
latency, input/output/cached tokens, actual spend, failed/duplicate tool calls,
human interruptions, evidence quality, review-closure latency, and recovery
success. Report all attempts and failure categories; do not retry until green
or hide failed runs. Distinguish infrastructure failures from harness defects,
but retain both in user-experienced reliability.

Define the first useful action **before** each fixture runs: the first correct,
task-specific action that acquires relevant evidence or advances its authorized
artifact. Help, orientation output, a greeting, and an empty edit do not qualify.
Record both task-arrival-to-action and harness-ready-to-action clocks, so
installation/startup cost is visible rather than silently excluded.

### Proposed acceptance targets

These are **initial experiment targets**, not current performance promises:

- One orientation request supplies a correct existing next invocation and
  resolved identity/workspace for the supported case.
- Zero namespace-guessing calls on deterministic onboarding fixtures.
- Zero duplicated full context bodies in the new compact representation.
- At least 50% lower bootstrap/context bytes for the scoped candidate, with
  complete required-constraint retention; measure real tokens separately.
- At least 25% lower median time to first useful action in the paired task
  sample, with no decrease in verified success.
- Zero unauthorized effects or false “all reviews resolved” claims.
- Every injected lost-response case either reconciles safely or explicitly
  reports ambiguity; no blind remote retry.
- Cold/warm latency and p95 budgets are set only after adequate sample sizes.
  The three-run observations above cannot establish those budgets.

Use held-out task variants and independent verification. A speed gain that
loses a safety boundary or degrades accepted artifacts fails regardless of
its aggregate score.

## Delivery sequence

### Slice 1: see and bound the actual interface

Owner seams: charter context, orchestrator envelope, command renderer,
profile registry, and local ergonomics fixtures.

1. Capture effective-context provenance and active executable/contract identity.
2. Add an explicit compact response representation without removing legacy
   fields from existing consumers.
3. Remove decorative output from a deliberate machine-safe version path.
4. Correct the profile identity drift and generate an accurate capability roster.
5. Retain a small deterministic golden suite covering those observations.

This is a coherent first implementation proposal. It does not require a new
daemon, provider calls, a new model, or an org-wide workflow migration.

### Slice 2: make orientation and recovery unsurprising

Project one existing next action with current scope, blockers, legal tools,
and evidence handles. Implement compact error recovery and verify Mission,
workspace, and permission ambiguity cases. Preserve current runtime authority.

### Slice 3: prove portability and continuity

Refresh the session-presence gaps against current primary sources, implement
supported adapters in canonical source, and run effective-context/resume
conformance per harness. Test instruction shadowing and external-runtime
permission gaps explicitly. Add durable effect/review reconciliation only at
owned seams with appropriate authority.

### Slice 4: optimize with evidence

Run paired context, caching, retrieval, delegation, and native-runtime
experiments through existing Kaizen/Elastic Fog machinery. Profile before
choosing Zig substitution or resident caching. Promote only replayable gains
with rollback and no loss of required governance.

A charter change to the mandatory bootstrap is a separate reviewed governance
decision. This report does not amend AGENTS, remove the charter-read requirement,
install hooks, create enforcement automation, or authorize publishing upstream.

## Open questions

- Which actual action prompts dominate real agent input and repeat most often?
- How much context-builder latency is imports, pack resolution, cache access,
  serialization, or filesystem work?
- Which current consumers rely on both `context` and `text`?
- Which harness versions can prove effective instruction loading without a
  paid model call? Where is a controlled behavioral probe required?
- Can existing operation/invocation records carry an effect receipt without
  duplicating another owner's authority?
- Which role/tool distinctions improve outcomes enough to justify their
  discovery cost?
- What real-task distribution should weight small changes versus long Missions?
- How should private prompt evidence be retained/redacted while preserving
  reproducibility?
- Which shared-core fixes would the operator choose to offer upstream?
  That choice must precede any upstream publication.

## Source register

All local paths below are relative to this repository. Audit source pin:
`50207b4333fdc886ed67fb27757dfb75e5b3b153`. Subsequent edits can change a
working file; use that commit for reproduction.

| ID | Source | What was checked |
| --- | --- | --- |
| S01 | [AGENTS](../../../AGENTS.md) | Bootstrap volume, fork boundary, integration roster, workflow guidance |
| S02 | [Project charter](../../../.kittify/charter/charter.md) | Binding governance, tiered rigour, review closure |
| S03 | [Decision engine](../../../src/runtime/next/decision.py) | Existing deterministic decision kinds and workspace seam |
| S04 | [Orchestrator envelope](../../../src/specify_cli/orchestrator_api/envelope.py) | Contract version and canonical keys |
| S05 | [Command renderer](../../../src/specify_cli/skills/command_renderer.py), [skill-agent roster](../../../src/specify_cli/skills/_agent_roster.py) | Shared rendering and current skill-agent entries |
| S06 | [Implementation prompt source](../../../src/doctrine/missions/mission-steps/software-dev/implement/prompt.md) | Governance payload and conditional fetch contract |
| S07 | [SPDD renderer](../../../src/doctrine/spdd_reasons/template_renderer.py) | Conditional REASONS blocks, not unconditional source-text inference |
| S08 | [Status store](../../../src/specify_cli/status/store.py) | Existing event authority; charter describes required usage |
| S09 | [Charter context command](../../../src/specify_cli/cli/commands/charter/context.py) | Duplicate fields, load-state option, action/type help |
| S10 | [Orientation writer registry](../../../src/specify_cli/session_presence/writers/registry.py), [earlier gap research](session-presence-harness-gaps.md) | Named no-op writers and dated research backlog |
| S11 | [Researcher profile](../../../src/doctrine/agent_profiles/built-in/researcher-robbie.agent.yaml) | Identifier/name/initialization mismatch |
| S12 | [Earlier harness research method](../3-2-doc-publication/3-2-harness-research-method.md) | Existing coverage and evidence-tier precedent |
| S13 | [Raw local measurements](2026-09-05-agent-ergonomics-measurements.json) | Three runs, environment limits, document hashes |

The durable outcome of this research is a specific recommendation: **reduce
agent decision burden by exposing what Spec Kitty already knows, and prove the
improvement on real authorized work.** More prose, more agents, and faster
subprocesses are means to test—not substitutes for that outcome.
