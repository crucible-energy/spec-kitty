# Register the existing single-shard diagnostic workflow

## User Experience Findings

A cancelled reusable-matrix job could be retried, but its inherited failing
sibling cancelled it again before pytest. An unchanged candidate already has
an independent single-shard workflow, yet it was absent from the default branch
and GitHub returned 404 for its workflow registration. That blocked the supported
manual continuation; a candidate-only declaration was insufficient.

## Engineering Decisions

Register the byte-identical existing module-tests workflow through a small
normal PR. Do not import the larger integration history, CI helpers, registry,
application source, runtime release or branch-protection changes. Its one job
uses the canonical selector, unchanged coverage, failure status and time limit.
The owning migration lane dispatches only the exact core_misc4/5 and5/5 rows,
sequentially, with modepr and no custom test filter.

The selected source ref is an explicit prerequisite. For this continuation,
use codex/owned-lanes-analysis only while it resolves to the qualified immutable
24856332d5bfd7a4ddd71bbcb561172889a4c7d9, then independently verify the resulting
run head and one-job shape before admitting the next job. Required helpers and
registry exist there; they are not supplied to the older default runtime by
this registration. A run against the default's older layout is not qualified.

Repository token policy is currently read-only with PR-review approval disabled.
Check that policy again before dispatch; do not change settings or infer another
capability from workflow availability. No key, grant, source Store or service is
installed. The platform-held Native lane is not retried or probed through this
independent Spec Kitty lifecycle diagnostic.

## Known Limitations and Retained Obligations

Registration is not default RC7 adoption, successful Linux control execution,
complete host visibility or a passing parent matrix. Preserve the earlier failed
and cancelled runs. Actual workflow registration, selected-ref checkout, exact
JUnit cases and results must be verified after the normal PR delivery. Keep
HELD/v5 and all Source/native custody intact, with no fit, unhold or faster-tier
change. Validation and closeout receipts remain external to frozen candidates.
