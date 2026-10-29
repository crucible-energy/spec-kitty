---
title: Private owned-runtime qualification
description: Qualify actual owned SDK behavior and preserve native agent state before consumer receiving.
doc_status: active
updated: 2026-10-29
---

# Qualify the installed owner and its effects

## User experience findings

Private runtime configuration alone does not isolate agent commands and skills.
The published RC7 runtime selected native agent directories during actual SDK
startup. Even after applying the accepted consumer asset closure, its upgrade
checker created `~/.kittify/last-cli-check.json` despite `SPEC_KITTY_HOME`.
Getter-only checks missed this second writer. The installed startup and complete
owned-mission fixtures exposed it before consumer admission.

## Engineering decisions

Reuse the existing canonical owned-analysis RC7 patch: it already selects the
owned analysis root. Retain the separately qualified operation-specific
finalization port. Port the six live asset paths from accepted source
`c9f90a3a7f67176608f2284316a7a290c6688d86` without fuzz. Its additional historical
workflow API hunks do not match the published runtime and are not force-ported.

Repair the existing upgrade cache writer by delegating to
`kernel.paths.get_kittify_home`; do not introduce another resolver. Include this
same small correction as a seventh path in the compatibility data patch. The
canonical resolver retains platform-specific default runtime location policy.

Independent review questioned whether the direct cache import could bypass
consumer admission. Actual fresh-process controls for relative, parent-segment,
missing-home and invalid-scope inputs all refused before filesystem effects.
Their trace identifies the existing authority: package import loads the operator
environment through `bootstrap.env_file`, which calls
`kernel.paths.get_runtime_state_root` and `consumer_agent_asset_root` before the
cache module is reached. Retain that regression; do not add a duplicate guard or
switch the cache to the different default runtime-state directory.

Build a new private wheel and executable instead of modifying a retained runtime.
Record the published archive, exact ports, wheel and installed file hashes, all
dependency identities, dependency supplier and executable in external evidence.
The supplier is a pinned, retained private runtime; dependencies are not claimed
to be independently copied or equivalent to a vanished historical installation.

Use native tests that call the actual installed SDK: private command and skill
paths, real startup, an SDK-created disposable owned mission, recorded analysis,
advancement, material-drift refusal, and the existing three-argument workflow
freshness helper. Public owned `agent action implement` currently refuses with
`OWNED_ACTION_UNSUPPORTED`; prove its state invariance rather than claim dispatch.
Protect the fixture primary and native home. Exercise actual foreground cache
refresh with a local provider fixture and check default user path resolution.

Resolve the current published release independently before bounded offline
qualification. Use the existing explicit `SPEC_KITTY_NO_UPGRADE_CHECK` opt-out
for those CLI invocations: the default background checker detaches a process,
which an original process-group join cannot certify. The foreground cache test
exercises its actual writer separately without a background process or network.
Do not silently change the default upgrade-check behavior.

Compile the native harness under the existing compiler resource envelope, then
execute its exact hashed binary under the separate execution envelope. Retain
failed stages and their original settlement uncertainty. A passing process
receipt does not qualify an artifact written outside its declared resource root.
Bind the artifact root before the builder's first filesystem effect.

## Known limitations

These are private compatibility and fixture proofs. Exact independent receiving
and the named consumer's own checks precede any runtime replacement. They do not
prove unrestricted SDK descendant ownership, successful unsupported dispatch,
production readiness, Windows execution, or organization-wide adoption.

Ordinary full-agent launch and handback integration remains a separate blocker.
Each repository retains its own pending execution and useful-work recovery
obligations. Missing historical artifacts, unknown original worktree state and
unresolved attribution authority remain preserved; neither age nor a new runtime
grants deletion permission. External receipts record actual test outcomes and
failed stages without changing a frozen candidate merely to record a pass.
