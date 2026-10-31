---
title: Package identity startup repair
description: Preserve supplier and custom-provider contracts while removing stock wheel package discovery from the startup path.
doc_status: active
updated: '2026-10-30'
type: explanation
---

# Package identity startup repair

Owner: dealer runtime recovery task. Branch: `codex/startup-package-provider`.
Tracker: [issue 149](https://github.com/crucible-energy/spec-kitty/issues/149).
This log adopts the independently owned log and three-section structure of
[Kaizen's pinned procedure](https://github.com/crucible-energy/kaizen/blob/4ca2672d97ffe34d9a7d9a4df3d6f8b6c93c8b51/docs/mission-log-procedure.md),
using this repository's canonical engineering-notes directory. Existing logs
and their historical entries remain in place.

## User Experience Findings

### 2026-10-30

The required clean-install startup gate blocks inert qualification asset
[PR 148](https://github.com/crucible-energy/spec-kitty/pull/148). Two coherent
heads with unchanged product source measured medians of 1.153 and 1.168 seconds
against the unchanged 1.050-second ceiling. All five measurements in each
sample exceeded the ceiling. The captured hosted profile attributes 0.389
seconds to package ownership discovery through
`importlib.metadata.packages_distributions`, which enumerates unrelated
installed distributions before identifying the wheel's supplier.

The local reference wheel passes the same unchanged gate, so local timing is
not a reproduction of the hosted absolute failure. It supplies a comparable
before/after measurement on one host; exact required hosted checks remain the
delivery boundary. The profile, failed samples and local baseline are retained
externally. No ceiling, workflow, skip label or retry policy is changed.

The latest published runtime's source profile/context commands refuse
`LEGACY_CHARTER_STATE` on this retained 3.2 project. No busy primary upgrade,
unsafe standalone operation, frozen runtime change or successful governance
admission is claimed. Existing source charter, explicit bounded repair
authority and ordinary validation/review rules remain binding.

## Engineering Decisions

### 2026-10-30

Register the existing stock package-name provider in wheel metadata. The
resolver treats that registration as a fallback beneath custom providers;
custom providers retain their original alphabetical selection rule. Read the
stock fallback's supplier from its attached distribution metadata rather than
returning the static public package name. A renamed wheel therefore retains
its actual supplier identity without a full installed-package scan.

Missing or invalid stock supplier metadata, a broken selected custom provider,
and older wheels without the registration retain the existing import-package
ownership fallback. A custom provider is never silently replaced by stock just
because it failed to load. Runtime environment variables do not choose package
identity. The change repairs the existing NFR-003 contract within the retained
Python boundary; it introduces no new tool, adapter or effect authority.

Red-first tests reproduced naive registration failures for renamed suppliers,
late-named custom providers and invalid supplier metadata. The targeted tests
also cover multiple custom providers, missing registration, unbound metadata,
malformed payloads and provider failures. Installed reference and candidate
wheels use the same dependency pins, canonical fixture and unchanged latency
script. Stock and renamed candidate metadata are checked separately. Real
HOME stays unchanged, private state homes are distinct, and the owner-held OS
policy denies shared native assets for every producer callback.

## Known Limitations

### 2026-10-30

Freeze source and docs before final gates. Exact results and artifact hashes
belong in external receipts and the PR so recording a pass does not change the
validated candidate. The retained source has no `make test-fast` target; use
its declared `make test` surface plus the affected distribution, package-name,
compatibility and clean-install checks. No broad test invocation is invented.

This repair does not deliver or activate the isolated 4.x runtime assets from
PR 148. Source publication, required hosted checks, isolated installation,
customer receiving and upstream release remain separate facts. The existing
supplier audit tracked by issue 143 and the active owner of PR 142 remain
outside this focused repair; no dependency or governance migration is bundled.

The source lane, isolated wheel environments, fixture and caches are owned by
this task. After reviewed merge, fetch and verify exact default-branch delivery,
recheck active dependencies and recoverable state, preserve useful source/proof,
and retire only released eligible resources. Never prune another owner's cache
or restore shared native assets. No capacity recovery or savings is claimed
before measurement.
