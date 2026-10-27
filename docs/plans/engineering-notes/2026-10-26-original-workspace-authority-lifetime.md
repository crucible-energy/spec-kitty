---
title: Original workspace authority lifetime
description: 'Retain the original workspace creator through one joined foreground producer, with explicit release guards, recovery evidence and scoped RC7 qualification.'
doc_status: draft
updated: '2026-10-27'
---

# Original workspace authority lifetime

## User Experience Findings

An ordinary allocation currently returns a path and branch. A later Op close
records a result but neither retains the original creating object nor joins an
agent process. Restoring an owner from its registry does not recover its live
release capability. Treating those records as release authority could delete
valuable work; refusing every completion forever also leaves useful work without
an executable closeout path.

The existing Source owner independently traced this boundary at
`1a607b3b8241c24458ca8acdfd36c64a34e960ff` against Root
`0ac0a2879498e17e814f6683e1f12510f18a87f8` and the qualified RC7 resume runtime.
The actual `ManagedGitCreator.run_producer` owns a bounded foreground process;
the profile executor explicitly does not own the LLM. These are different
execution boundaries, even when their operation labels match.

## Engineering Decisions

### Retain original authority in a real producer scope

Add an explicit original-workspace run scope in the workspace lifecycle bounded
context. Its factory creates the ordinary workspace through the canonical
creator and privately retains that exact returned object. It must not adopt an
existing path, receive a replacement capability from a caller, or derive
authority from `OperationRoot`, an actor, a receipt or a completed Op.

The intended additive interface is `OriginalWorkspaceRun.create(...)`,
`run_producer(argv, *, timeout)` and `complete(*, pr)`. Allocation arguments are
the existing creator's arguments, with ordinary kind fixed by the factory.
The scope returns observation-only path/branch facts to callers; no public
capability getter or serializable authority is introduced. The final source
signature must be frozen against the real creator before consumer integration.

The run scope owns a single producer attempt and the original creating process
identity. Only the actual creator's bounded foreground runner may establish a
successful joined attempt. Leaving a context manager, returning from a callback
or recording a success label must not do so. The scope refuses copying,
serialization, reconstructed owners, reuse after completion, foreign-process
use, repeated execution and completion before a successful join.

Completion must call an explicit creator-owned ordinary completion method with
the original run witness. That method checks the witness belongs to this exact
creating object and generation, then preserves existing path/common-store,
producer, delivery, ignored data, nested repository and runtime checks. The
ordinary creator's current release refusal remains in force until this complete
path is implemented and qualified together. An adapter stub or synthetic
successful callback cannot count as supported completion.

The creator implementation owner retains its adapter, ordinary allocator,
native caller, completion and installed cleanup work. Root owns the retained
scope, its public lifetime contract and current-release compatibility. The
existing Source lane supplies the read-only API crosswalk; Root reviews that
crosswalk instead of repeating its investigation. No additional execution lane
or producer is needed for this division.

### Preserve unsupported process boundaries

A separate CLI invocation cannot reconstruct the original scope after the
creating process exits. Existing path/branch and Op-close interfaces remain
compatible and nonauthoritative. Without the original live scope and actual
owned producer, work is retained with an accountable recovery obligation.

The first supported positive path is an explicit foreground run whose creating
owner outlives its real child and completion. This is not an automatic claim
about Codex/LLM execution, a new daemon, a scheduler or a hosted service. A future
cross-process lifetime bridge needs its own concrete authenticated ownership
design; an operation ID or process liveness observation is insufficient.

### Qualify against the current release

The newest published non-yanked release including prereleases is RC7. The
qualified resume runtime contains no `workspace_lifecycle` package. Source's RC6
metadata must not simply be relabeled RC7, nor may older whole modules replace
newer runtime guards.

Port the actual component and required primitives explicitly. Preserve typed
`ResidueClassifier` removal/ref operations, ignored-data protection,
`OwnedCheckout.files(follow_links=False)`, current rollback semantics, analysis
currency, expected-issued-step fencing and actor/migration guards. Source's
missing installed imports and differing allocator APIs must be resolved before
the component is imported or executed. Retain all unique Source history and
independently qualify the resulting installed artifact.

### Acceptance sequence

1. Run actual private creator/foreground-process tests for original custody,
   joined completion and same-generation checks. Use no live repository or
   application producer. A successful test callback is not a join witness.
2. Qualify refusal and retained recovery for exceptions, timeout, cancellation,
   incomplete descendants, copying/fork/reopen, path/common-store replacement,
   duplicate completion and ordinary-to-legacy downgrade.
3. Join the creator owner's real ordinary adapter/caller with the retained
   scope. Prove eligible cleanup and preservation of valuable dirty, ignored,
   nested, active and ambiguous state using the actual installed component.
4. Publish exact source/artifact hashes, normal gates and review disposition.
   Only then perform the creator owner's fresh per-repository rollout checks.

### Core candidate and creator handshake

The candidate `workspace_lifecycle.original_run.OriginalWorkspaceRun` now holds
the actual factory result strongly and checks the creating PID before taking
its private mutex. Its phase transitions do not hold that mutex across process
I/O. A successful real producer may change HEAD and lease; stable workspace
generation and exact creating-object identity remain bound.

`complete(*, pr)` enters one finalization and calls the existing creator's
completion with the additive `original_run` witness. The creator must require
the exact canonical class and invoke `require_joined_for(self)`, which refuses
outside that finalization or for a different object/generation/process. Source
owns adding this keyword and ordinary decode/released-proof support together;
its existing unqualified ordinary refusal is not removed by the core scope.

The pending admission callback is required by the actual ordinary factory.
An initial candidate accidentally retained the legacy optional default; six
private tests refused before ordinary Git effects. The core factory now makes
that callback a required argument, preserving the real guard instead of
installing a silent no-op. Callback data does not carry the live scope.

Scope failure poisons later producer/release attempts. A completion hint can
fail after durable release, so core retains the original error and refuses a
second attempt; Source's durable state and recovery remain authoritative. No
completion or retirement is inferred from that exception. Separate private
tests cover real producer failure/timeout, fork with an inherited held mutex,
copy/serialization refusal and post-release hint failure.

### Installed component qualification

The combined creator/core source at
`e5c75f86958a0f5ef7751d9df374b2184ff32be3` now passes all ten
original-run tests against the actual isolated installed RC7 component. The
creator handshake and durable release proof are implemented; the earlier
missing-keyword failures below are retained as historical diagnosis, not the
current result.

The derivative runtime is `4.0.0rc7+crucible.originalrun.1`, wheel SHA-256
`a34884558dc3d09b3b06e03132ae1a6e068eeba70b8d43e412e845bec1939408`.
Its external `installed-qualification.json` digest is
`aa37ec254d1b9ff40ceb35e17ee34e22cac1d91017cb87d1db882bb78e1c8873`.
Verification checked 2,088 installed RECORD entries, unchanged versions for
52 dependencies, and actual module origins outside the Source checkout.
Private fixture checks prove wrong-parent atomic-write refusal, symlink-lock
refusal, typed clean-checkout removal and ignored-data preservation.

Six necessary primitive ports preserve the entire current RC7 baseline AST
under recorded inverse projections. The installed creator uses an explicit
conservative typed removal context: every path remains non-disposable and
ignored-data protection stays enabled. Its inverse restores the exact Source
adapter AST. This is a documented artifact projection, not a claim that the
older Source tree is byte-identical to current RC7.

## Known Limitations

At the initial checkpoint, the decision supplied no implemented scope. The core
candidate remained incomplete until Source's actual creator handshake, private
decoder and release path integrate: the positive release and post-release hint
tests then failed on the absent `original_run` argument. No stub positive,
ready PR, release permission, installed cleanup, operating-system sandbox or
repository adoption is claimed. RC7 resume qualification and the authenticated
119-repository inventory are separate evidence; neither proves this component.

Current installed qualification covers the library lifetime and required
kernel primitives only. The existing creator owner still owns actual ordinary
CLI/native caller wiring and installed cleanup/preservation acceptance.
Organization rollout, whole-Source RC7 convergence and PDB authority/serving
acceptance remain unproved. Initial installation failed on incompatible
installer flags; its raw evidence is retained separately from the corrected
successful installation. The qualified wheel/runtime and receiving-owner
intake evidence remain active recovery obligations, not cleanup candidates.

HELD/v5, protected recovery evidence, existing serving/source ownership and
personal runtime settings are outside this source-only increment. No fit,
unhold, Store, model, provider, host or shared-pruning effect is authorized.
