---
title: Project-layer consistency and runtime admission
description: Preserve project policy while qualifying the assigned consistency-check repair.
doc_status: active
updated: '2026-10-28'
---

# Project-layer consistency and runtime admission

Owner: Cmail solo dependency recovery, `codex/issue-141-project-charter-consistency`.
Tracker: [issue 141](https://github.com/crucible-energy/spec-kitty/issues/141).

## User Experience Findings

The current published Spec Kitty release refuses this fork's legacy project
layout before opening a governed operation. Its supported upgrade moves the
project policy and refreshes managed surfaces. The first run completed the
migrations but refused a changed profile input during surface repair. A fresh
preview against those changed inputs followed by the supported command completed.
The first failure remains recorded; no input check was relaxed.

Remote qualification also exposed three concrete integration findings: the
workflow still filtered the retired overlay directory, this note was absent
from the generated documentation inventory/index, and the lint environment's
locked `msgpack==1.2.1` was flagged by the live dependency audit. The source
workspace itself is editable and unpublished, so a package-index audit must
not mistake that workspace for a released dependency. See
[issue 143](https://github.com/crucible-energy/spec-kitty/issues/143).

The broader owning run then exposed a real extractor defect: a valid path
reference invented an uppercased hyphenated directive ID instead of using the
body's declared underscore ID. The canonical graph passed structural checks but
left compiled fallback content unresolved. An independent synthetic graph case
was committed while failing. Extend the existing path-reference helper to read
the declared identity only inside its resolved owner root, preserving filename
fallback when a body is absent. A symlink escape must not read an external body.
Regenerate the overlay-preserving graph and catalog after this repair. Comparing
against the pre-backport source confirms no original node, edge or catalog ID
was removed; the newly fabricated ID is absent. The first serial owning run was
gracefully interrupted after its failure (849 passes, one failure, one auth skip)
and is not an acceptance result. Its intended predecessor used two workers.
The corrected two-worker whole owning run then completed with 4,598 passes,
one unchanged authentication skip and two graph golden-baseline failures. The
reviewed additions are exactly four authored nodes and eleven declared suggests
edges; reaching the existing reconciler removes one pure-graph orphan. Update
only those pinned cardinalities, preserving exact generated/committed graph
equality and the original-ID/edge preservation proofs. These counts describe
a fixture baseline, not mission completion.

Generated YAML also carried trailing whitespace. Removing line-end spaces was
verified to preserve the parsed values before publication.

## Engineering Decisions

Use the current published `4.0.0rc7` executable in an isolated environment.
Preserve the fork's source version `3.2.8`; project admission is not a product
release. Canonical migration moved fourteen legacy artifact files byte for byte,
kept custom activation lists, retired obsolete built-in selections through their
documented successors and repaired five recorded topology values. It did not
approve any work package. Agent projections are managed outputs.

Keep this migration separate from the retained Python correctness repair.
That repair must pass resolved layer roots as data from the existing CLI caller;
the charter package must not import the higher CLI layer or add another scanner.
Preserve the behavior contract for eventual Zig parity.

The migrated-layout correction reuses the existing project-root helper in the
caller, availability scan, canonical-ID scan and graph loader. Current
`charter-packs` directories take precedence; retained `doctrine` overlays and
built-in fallbacks keep their previous relative order. Explicit layer data never
falls back into a built-in source tree. No new scanner or upward import is added.

Raise only the lint `msgpack` floor to `1.2.3` and update that locked dependency.
The normal resolver preserves all other locked packages and the source version.
Keep the enforced audit and pipe failure handling; exclude the editable workspace
from package-index lookup, while continuing to audit its installed third-party
packages. Do not suppress any advisory.

## Validation

The second supported upgrade exited successfully. A genuine current-release
operation loaded the fork's governance. Strict charter preflight passed. Exact
commands, outcomes, source snapshots and resource custody remain in the owner's
external receipts. These results do not establish passing product tests.

The migrated-layout CLI case failed before implementation and was committed as
an executable regression. After the bounded data backport, all twenty
consistency CLI cases and the real maintainer-governance case pass together.
The earlier whole owning run had 4,548 passes, one real governance failure and
three skips; it is retained as a failed run. Two packaging skips were caused by
missing isolated build inputs and were closed by actual offline wheel and fresh installed-consumer proofs (both pass).
The five installed policy assets match source hashes with source fallback disabled.
Strict typing passed the eight changed path modules. Workflow coherence passed
sixteen tests, and canonical documentation generation produced zero freshness
findings. A first docs invocation omitted CI's Python-path setting and failed.

The release validator's init and upgrade writers establish that
`spec_kitty.version` records the executing/target governing CLI. It is independent
of the source product's `[project].version`. New actual-CLI branch/tag and
malformed-record tests were committed before implementation: six failed and
four passed. The repair validates this separate record, reports malformed YAML
or shape without a traceback, and preserves all product lockfile, changelog,
migration-target, tag and progression checks. All thirty-nine release validator
tests pass. This does not authorize a release or establish runtime adoption.

Final owning qualification passes 4,600 tests with one unchanged
connected-account authentication skip. Real wheel build/install tests run and
pass against recorded offline dependency/build inputs. The fresh installed
consumer matches fourteen reviewed code/asset hashes without source fallback.
The final two missing-overlay API controls refuse both forbidden source fallback
layouts; all twenty-two consistency cases pass with implementation unchanged.
Focused architectural/CLI coverage passes 218 cases, and the separate CLI/release
coverage slice passes 59. The combined report represents all ten changed
implementation files and covers all 54 changed executable statements. This is
changed-code coverage, not whole-source or production qualification. An earlier
package-name coverage filter silently omitted standalone/CLI files; explicit
filesystem roots and a mandatory changed-file inventory close that reporting gap.

The original frozen audit reports the `msgpack` advisory. After the targeted
lock update and frozen reinstall, the fresh audit reports no known
vulnerabilities; the only excluded distribution is the editable workspace.
An audit-only `urllib3==1.26.4` fixture is still refused with advisories when the
same editable exclusion is enabled. It is not installed. An initial stdin control
was invalid because the bounded wrapper consumed stdin; its empty report is not
counted as a passing negative control.

The two missing current policy definitions and their declared dependency closure
are backported from the isolated published `4.0.0rc7` distribution into the
retained source's native data layout. The BDD tactic and Given/When/Then style
are byte-exact; only documented source/guide paths change in the boring-review
style, Gherkin toolguide and guide asset. Existing native models accept every
body and existing resolution APIs resolve every declared reference. Preserve
all previous IDs and graph edges, including the old boring-review tactic.
Regenerate graph shards with the existing hand-authored-overlay writer so
rejection and tension edges survive. Compile the native catalog through the
existing compiler/writer; authored activation sections, curated charter prose
and generated governing-runtime metadata remain unchanged. Eighteen available
catalog references are added and none removed; counts are not adoption proof.
Exact source/projected hashes, graph comparison and canonical command receipts
are retained externally. These are bounded data/migration repairs to retained
Python; eventual parity remains part of the Zig mission.

## Known Limitations

The real retained-source coherence gate now passes. The official current
runtime still reports two unresolved toolguides (`rtk-search-tooling` and
`terminology-guard`) and two unreconciled policy tensions. Catalog ID divergences
and graph-kind gaps are absent in that check after the backport. The existing
internal pack has a canonical org-binding route needing separate qualification;
its presence does not prove consumer compatibility. No control is deactivated
to conceal a finding. Publication of this source repair, protected human merge,
package release and Cmail runtime adoption are separate gates.

The repair passes the canonical root map from the CLI through availability,
compiled-catalog parity, graph parity, activation filtering and tension scanning.
A missing map had also silently removed valid project nodes and tension findings.
No scanner, resolver, schema or upward package import is added. Existing callers
retain the default argument and behavior.

Actual CLI tests were committed while failing, before implementation. They cover
valid directive/styleguide bodies with a compiled catalog and graph, missing and
malformed bodies, missing IDs, catalog divergence, missing graph nodes and
advisory tension findings. Explicit root selection is exercised from another
working directory. An overlapping organization artifact with a different
canonical ID must not displace the selected project artifact.

The broader first run exposed missing local distribution metadata and legacy
consumer fixtures coupled to the maintainer's newly migrated policy. Installing
the reviewed local project without changing dependencies fixes the environment.
The four implicated fixture modules passed against actual base `e851d756` in the
same environment. Their corrected cases use minimal retained-consumer settings,
the canonical shipped default for an absent activation, and an independent
tracked synthetic repository for read-only rendering. Positive assertions and
explicit-empty behavior are preserved. The affected cases pass after correction.
Freeze these inputs before the full owning suites and required static gates. The fork's retained source layout
and the current published release's layout differ; source delivery, release and
Cmail runtime adoption require separate evidence. No upstream publication is
authorized by the fork issue. The old source refs, private development runtime,
retained metadata and shared object alternate remain protected until their
owning recovery obligations close.
