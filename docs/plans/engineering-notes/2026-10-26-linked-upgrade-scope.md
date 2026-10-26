# Linked upgrade compatibility scope and version guidance

## User Experience Findings

The real console preview from a linked checkout used the separate repository
root checkout for compatibility planning while computing pending migrations
from the selected checkout. A future primary schema therefore refused a healthy
selected checkout, and a future selected schema produced a refusal naming the
wrong checkout. Both cases were reproduced with independently staged primary
work retained. A stable-channel query also offered a pinned 3.2.7 installation
command to a 4.0.0rc7 installation, including one with a local qualification tag.

## Engineering Decisions

Bind the existing planner's resolver to the project path already selected by
the upgrade command. Keep both the JSON preview and too-new refusal read-only;
do not change the general planner's canonical root resolution. Use the existing
upgrade-hint factory to compare a known installed version with the selected
release. Return a manual note for older or uncomparable versions. The planner
and agent-check caller pass their existing installed-version observation;
channel selection, package provenance and remediation rendering remain owned
by their existing sources.

The red regressions were committed before the implementation. Public-entry
tests snapshot both checkouts, Git indexes, the isolated home and temporary
state. Equal/newer-version controls preserve the existing hint behavior.

## Known Limitations

This corrects compatibility reporting and guidance; it is not a live project
upgrade or consumer admission. The separately reported legacy-charter startup
refusal still needs exact current-runtime/project-owner evidence. No Aletheia,
Source, Store, runtime, grants or shared primary checkout is changed. HELD/v5
custody remains outside this source repair.

An initial hint-test run was invalidated when its test was relocated during
execution; its own controller stopped and joined its children. It is not red
or green evidence. The unchanged second run reproduced both downgrade hints.
The first implementation commit retained a line-length failure; it was fixed
before qualification and delivery checks. All failed outputs remain retained.
