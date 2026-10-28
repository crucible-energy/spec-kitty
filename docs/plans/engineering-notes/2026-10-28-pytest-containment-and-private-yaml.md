# WP16: test containment and private YAML

## Objective and ownership

Current: the existing Google integration owner claimed WP16 through the supported
Spec Kitty command. Normal status commits end at `5f846fb070`. The original WP15
working files and claim history remain protected. The public validate-only and
normal finalization commands admitted one existing ninth release-note path,
preserving the original eight paths and claim. That planning commit is
`fc0abfc555`; it does not deliver the implementation. Only these nine WP16
paths may change; the integration target remains the existing lifecycle mission
branch. Integration delivery, default-branch delivery and installed adoption are
separate gates.

This is a bounded safety repair of retained Python test bootstrap and YAML
serialization code. It introduces no alternative backend or lifecycle engine.
Any later Zig migration must preserve these permission, complete-write and
successor-preservation contracts rather than introduce a second active writer.

## Measured defect evidence

The first focused attempt stopped at its 1 GiB resource bound before pytest
produced assertions or JUnit. It is a failed resource attempt, not a test RED.
Its original failure and joined cleanup are retained externally.

The distinct existing Source observer, using the established 4 GiB envelope,
completed the unchanged owning YAML suite with **five failures and fourteen
passes**. The named failures reproduced permission widening before the first
payload write, truncated short writes, zero-progress publication, deletion of a
foreign temporary after exclusive-create collision, and overwriting a replaced
destination. All pre-existing assertions passed. Original pytest exit, JUnit,
source freeze, private-settings preservation and process joins are retained in
external receipts; recording this note is not a new validation result.

The first GREEN candidate exposed sixteen failures and twelve passes: Darwin's
ACL getter reports an absent ACL property as `ENOENT` even for an existing
directory. That candidate is a retained regression, not a pass. The correction
uses the existing no-follow opener and the descriptor ACL getter, and recognizes
property absence only while descriptor/path preimages still match. Other native
errors remain refusals; the corrected candidate requires a fresh complete run.

## Decisions and UX findings

- Keep the canonical `kernel.yaml_io.write_mapping_atomic` entry point. Callers
  need no new option or prompt to preserve supported existing permissions.
- Apply existing regular-file permissions to the new descriptor before writing
  payload. New files keep the caller's umask. Refuse unsupported access-control
  metadata instead of silently discarding it or copying privileged ownership.
- Complete every short write and refuse zero progress. Keep file fsync, atomic
  replacement and the existing best-effort directory-fsync behavior.
- Recheck destination and parent preimages before publication. Preserve a
  foreign successor and clean only the exact temporary created by this call.
- Inspect Darwin ACLs through the native API because ordinary mode bits and
  extended-attribute enumeration do not establish their absence. Apple's
  [API documentation](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/acl_get_entry.3.html)
  and [implementation](https://github.com/apple-oss-distributions/Libc/blob/main/posix1e/acl_entry.c)
  were checked on 2026-10-28; its iteration return values differ from Linux.
  The separate [file getter](https://github.com/apple-oss-distributions/Libc/blob/main/posix1e/acl_file.c)
  and [property getter](https://github.com/apple-oss-distributions/Libc/blob/main/gen/filesec.c)
  explain why ACL-property absence must not be confused with a missing path.

Candidate implementation: test-resource admission now precedes Source-managed
HOME/temp effects through the existing `run_basetemp` authority. A controller
holds a private physical root, exclusive reservation descriptor and positive
process generation. Its bounded local observation channel checks actual kernel
connection ownership and ancestry; xdist uses the existing workerinput handoff.
Environment values and owner records alone cannot create that controller.
Fixed data/temp prefixes protect other retained runs sharing a namespace.
The held descriptor is the exclusive reservation file: fresh root identity,
private-permission checks and the descriptor/path preimage bind that reservation
to its physical root. No filesystem compare-and-swap or hostile same-user
containment is inferred from those observations.

Actual unprivileged Darwin experiments established the per-process observation
API for direct children, grandchildren and one genuine xdist/execnet worker,
including wrong-PID/port/generation controls and transport/thread closeout.
Those are capability experiments, not integrated admission qualification.
Six new admission failures were then reproduced against the unchanged owning
helper suite: twenty-five old controls passed and two original inner probes
were skipped. The subsequent integrated run passed seventy-three cases with
only those two inner probes skipped. It covered the whole helper/YAML/status
suites, real Source xdist handoff, changed reservation/root/generation/nonce/
endpoint/scope refusal, symbolic-link escape, foreign Source-home refusal
before effects, explicit descriptor/listener/thread closeout, and the unchanged
read-only Git regression. Its original session and joined resource evidence
are retained externally. This is focused proof, not delivery qualification.

The existing private metadata inspection is shared with the repaired YAML
writer; it is not a second enclosure policy. Windows privacy checks inspect
native owner/DACL data rather than ordinary Unix mode bits. Windows execution
and native ACL compatibility remain unmeasured here. No new service is installed;
the temporary local channel belongs only to its pytest controller and grants no
cleanup or creator-adoption rights.

## Known limitations and remaining gates

The destination preimage check is not atomic compare-and-swap. Callers coordinate
concurrent writers, including the interval after the final check. Ordinary
extended attributes and native Windows ACL preservation are outside the
permission-only contract. The existing descriptor-chmod helper has a path
fallback on platforms without descriptor chmod. A redirected parent can retain
an owned temporary in its former directory; failure does not grant a sweep of
that directory or permission to delete its successor.

The hosted-drain caller's synthetic private-file permission and unrelated
content controls passed under ordinary/restrictive umasks. The nine whole-file
caller/architecture run passed 189 cases, including canonical-home ownership,
census/budget/isolation and kernel/layer rules. These measured focused results
do not replace the combined WP15/WP16 baseline, quality and
changed-statement coverage, independent review, normal publication and delivery
remain open. No production or organization-wide
adoption is claimed. Token and cost measurements are unknown.
