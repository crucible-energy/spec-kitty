# Inspect immutable planning without borrowing write authority

## User experience findings

A useful PDB mission remained committed on its planning revision while the active
owned checkout had moved to another branch. `next` correctly refused that branch
as a write owner; querying through the primary inventory missed the historical
mission. There was no supported pinned inspection command. Actual public CLI
invocation returned `No such command 'inspect'`; the failing native acceptance
control was committed before implementation.

## Engineering decisions

`spec-kitty agent mission inspect --mission HANDLE --at REF --json` returns saved
planning observations at one resolved commit. It never simulates `next`, creates
an ownership claim, qualifies analysis, changes branches or advances a mission.
The existing advancing-mode guard remains unchanged.

The adapter reuses the canonical kernel Git object readers, metadata decoder,
exact-byte digest and the existing mission handle resolution ladder. It does not
fork identity policy or materialize a fake checkout. Any derived `ResolvedMission`
paths are local selection inputs only; no `OwnedCheckout` or write capability is
returned. Unindexable legacy missions retain the canonical index behavior.

Resolve the revision once, then enumerate the actual Git tree and read that
immutable commit throughout. Actual testing rejected a glob-listing assumption
that returned no missions; refusal tests now require specific reasons as well as
unchanged useful state. Metadata
reads are bounded to 1,024 objects, 64 KiB per metadata blob and 4 MiB aggregate;
selected planning observations have a separate 4 MiB aggregate bound. The existing
owned-process budget encloses the complete query with the same absolute cleanup
horizon. Git lazy fetching, optional locks and terminal prompts are disabled only
in this child's environment. No config file or shared runtime is changed.

The JSON includes exact commit/tree, mission identity, metadata digest, selected
artifact byte/digest observations and saved status when present. It explicitly
sets `current_readiness_qualified` false. A historical analysis report never gains
current qualification without its legitimate report transaction.

New actual acceptance/refusal assertions live in `tools/zig/mission_inspect.zig`.
Python is the narrow adapter to the existing canonical readers/resolver. Normal
registration and distribution include the command; there is no new native runtime
policy executable, runner, daemon or installation-time compilation dependency.

## Known limitations

Source implementation requires exact validation, installed qualification and
independent review before publication. Immutable inspection is not historical
runtime simulation and does not let a caller advance from an incompatible branch.
Corrupt/unsafe selected inputs, excessive input or incomplete identity refuse;
this operation cannot repair metadata or resurrect missing dirty/ignored state.

This useful-work blocker correction proves neither ordinary foreground producer
integration nor automatic cleanup adoption across organization repositories.
Those lifecycle gates and original creator/recovery requirements remain open.
