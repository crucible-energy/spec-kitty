# Owned history and authority closeout

Owner: Sam's workspace closeout, Codex Root. Existing lane and
[PR 63](https://github.com/crucible-energy/spec-kitty/pull/63).
This independent log follows
[Kaizen's mission log procedure](https://github.com/crucible-energy/kaizen/blob/4ca2672d97ffe34d9a7d9a4df3d6f8b6c93c8b51/docs/mission-log-procedure.md).

## User Experience Findings

2026-10-15: The interrupted recovery slice has an independently reviewed
checkpoint but remains unmerged. Its newer admission prototype is distinct
unfinished work. Preserve the original commits, exact index, binary patch and
untracked files before resuming this existing checkout; add no checkout.

Self-review reproduced a valid history rejection through the real recovery
command: changing only a claimed event's offset to an equivalent instant
sorted it before planning. Text sorting is not chronological ordering across
valid offsets. The causal acceptance test fails before the correction.

## Engineering Decisions

2026-10-15: Reconcile current main and retain the original red-first/review
history in verified external Git bundles. The nineteen production modules
initially match the reviewed checkpoint exactly. Finish this bounded retained
Python correctness and safety repair; this does not start a new Python stack.
New implementation follows the repository's Zig directive.

Compare parsed aware datetimes when merging history; preserve every original
row field and timestamp string. The real CLI test checks preview purity,
successful application, original record equality and protected sibling/root
checkout bytes. Commit its failing acceptance contract before implementation.

The initial broad diagnostic run found six architecture failures. Checking
actual main in the same checkout proves four already exist: its status router
has replaced the old kind-blind site, leaving an obsolete allowance and stale
census. [Issue 106](https://github.com/crucible-energy/spec-kitty/issues/106)
records the counterfactual before repair. Remove that absent site's allowance,
shrink the cap and align the floor with the three real sites. Retain the
live-site non-vacuity check: suppressing the remaining historical write must
still fail the floor. The two additional candidate failures are a frozen-token
mismatch after a type-only cast; re-pin that same sanctioned site from the
gate's actual diagnostic, without adding an allowance or changing its scanner.

Sam clarified that Blacksmith and CodeRabbit are not QA dependencies. Use
self-review and direct objective tests, address findings, and deliver via PR.
The separate hosted-QA replacement belongs to issue 91 and its active owner;
this lane does not duplicate that migration. Freeze source/docs before final
gates and retain raw logs, identities and outcomes externally.

Focused repair qualification passes 47 tests: the mixed-offset real-command
case and the complete resolution-authority gate, including its mutation
checks. Strict typing passes all nineteen production modules; source and
touched-test lint checks pass. Broader final results belong to their exact
frozen-candidate receipts; earlier partial diagnostics remain preserved.

## Known Limitations

2026-10-15: The same four default-coordination failures in
[issue 64](https://github.com/crucible-energy/spec-kitty/issues/64) reproduce on
actual main and the recovery candidate. Their implementation/assertions are
unchanged here; they are not passing default-lifecycle or release evidence.
The interrupted diagnostic run is partial evidence, never a gate pass.

History integrity does not authenticate an operator or reconstruct missing
private provenance. Existing unsupported-platform and process-death recovery
limits remain in the recovery guides. Newer admission, allocator/DAG issuance,
canonical export and consumer/production acceptance are separate gates; the
preserved admission prototype's 24 focused passes do not qualify those claims.
