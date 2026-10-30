---
title: "Finite original foreground ownership"
description: "Documents bounded native foreground ownership, original execution horizons, descendant retention and the remaining ordinary launcher integration requirements."
doc_status: active
updated: "2026-10-29"
---

# Finite original foreground ownership

WP09 implementation is in progress. This note describes the source boundary;
it does not certify an installed release or organization adoption.

## User experience findings

The existing creator's short Git/API allowance also encloses its legacy producer.
Raising that allowance to accommodate real work would silently change the short
operation contract. Governance invocation results and returned workspace paths
do not retain the actual producer or original creator.

The native acceptance test first reproduced this missing contract: the actual
legacy owner refuses a producer allowance larger than its short allowance, while
the new foreground admission API was absent. That test was committed before
implementation. The fixture lowers only its actual owner instance's allowance,
after creation; production retains its 30-second cap.

## Engineering decisions

The new native policy admits finite execution and settlement allowances and
accountable owner, purpose, next action and review event before creation. It uses
the same explicit POSIX monotonic clock in both native and Python bridges. Setup
consumes the original execution horizon; invoking the producer does not restart
it. Serialized admission data carries no workspace release authority.
The bridge retains the native admission as immutable bytes; parsed dictionary
views cannot modify its deadlines or recreate the live original-object binding.

The private live job binds once to the actual original factory result in the
creating process. Copy, serialization, substitution and a second creation cannot
restore that binding. The creator fence remains held across the real foreground
producer. Short private/Git effects retain the original operation cap; the wait
has a distinct, previously admitted horizon.
Creator-fence acquisition consumes that same remaining execution horizon rather
than borrowing the store's longer lock timeout. The real contention regression
reproduced a 1.257-second wait with only 0.424 seconds of original settlement
time remaining; the job path now bounds acquisition without changing legacy
fence defaults. A refusal retains the creator and starts no producer.

The native helper reuses `validation_process_darwin.runLogged`, including its
existing wall, cleanup, process, sampled memory, output and original-process
group observations. Output goes to exclusive private regular files in the
existing creator store, tied to its exact directory identity and generation.
No new store, general Python runner, background daemon or deletion authority is
introduced. The canonical Python runner still owns its direct helper process;
the helper owns its actual foreground child through the existing native runner.
Neither a successful callback nor JSON claiming a join grants release.

The actual parent-exit/live-descendant regression exposed a further distinction:
the reused validation primitive can successfully dispose remaining processes
after its leader exits. Its additional terminal-group quiescence observation
records whether the original group was already empty before disposal. The
foreground policy requires that observation as well as real join/disposal; the
primitive's existing validation cleanup semantics stay unchanged. Raw output
stays in its bounded files instead of being copied or decoded into JSON.

Independent review reproduced two original-horizon leaks in core122390. Actual
post-wait Git bookkeeping spent 2.131 seconds with only0.309 seconds remaining;
failed persistence spent1.057 seconds with0.312 seconds remaining before stop.
An actual macOS log-creation interposer then delayed setup900ms and observed the
producer write after its execution deadline. The earlier setup test whose hook
did not fire is explicitly not accepted as the intended failing reproduction.

The correction carries the original absolute settlement horizon through the
existing shared kernel budget context, including nested short Git/persistence
calls. Its optional cleanup deadline distinguishes absent legacy behavior from
zero/expired refusal, rejects nonfinite values, and only tightens when nested.
Actual captures reserve join time inside that original horizon; they do not add
fresh half-second waits. Failure stops before bookkeeping and preserves the
original error plus uncertainty when persistence or join cannot finish. The
creating object stays unconfirmed and cannot release useful work.

The ordinary lane allocator can now accept a private, process-bound creation
context prepared from the original admitted foreground job. The context binds
the expected repository, path, branch, starting commit and accountable owner.
The allocator resolves its selected parent and requires that exact commit
before the original creator registers custody and creates the worktree. The
same context is carried through the implement and orchestrator workspace
resolvers. Returned paths remain observations; they cannot reconstruct or
transfer the creator. Copying, serialization, a second attempt, a different
target, and adopting an existing or recovered lane are refused.

When planning-commit reconciliation encounters a real conflict after an
original creator has created the worktree, the allocator leaves that worktree
and branch under the creator's existing custody. An interrupted admission
retains its pending creator record rather than retrying with a new generation.
These rules do not change the existing unmanaged allocation path.

The native bridge samples its destination clock before the admission clock,
conservatively converting both original horizons once before log setup. Existing
pre-spawn/loop absolute deadline checks enforce that conservative horizon. The native
process primitive accepts an optional absolute cleanup cap, including aggregate
check-scope disposal. Legacy callers without that field retain their behavior.
These source corrections still require exact-candidate validation and independent
review; they are not installed acceptance or repository rollout.

## Known limitations and remaining validation

This is a cooperative original POSIX-group profile. Availability on macOS or
Linux is not proof of platform-wide physical closure or containment of detached
session escapes. Unsupported, failed, uncertain or unjoined work remains held;
do not reconstruct or signal a numeric group after reaping its actual leader.

The helper bounds process resources and its own output. General producer
workspace/cache allocation and volume-reserve monitoring still need qualification
at the actual harness boundary. The current source fixture profile is not a
production admission for arbitrary disk-writing commands.

The actual configured ordinary Codex producer-owning harness remains unidentified.
Existing CLI/API integration, negative real-process checks, required source gates,
installed artifact qualification and independent review remain pending. A direct
fixture or opt-in command is not organization adoption. The worker's independent
default-branch delivery, review, recovery, runtime-use and retirement checks remain
mandatory. Useful work is retained until those conditions and original release
are proved.

The new allocation context is a private integration seam, not a host launcher.
The source fixtures exercise direct, implement and orchestrator allocation with
a joined foreground producer; they do not show that an ordinary external agent
host retains this context across its own lifetime. Existing allocator setup and
reconciliation also include legacy operations outside the native foreground
runner; their complete deadline and descendant behavior is not qualified by
these fixtures. An expired job cannot grant creator release, and uncertain
state remains retained. Installed creator integration, cancellation modes beyond
the tested cooperative signal, and automatic post-delivery cleanup remain gates.
