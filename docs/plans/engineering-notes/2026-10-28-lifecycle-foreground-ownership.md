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
