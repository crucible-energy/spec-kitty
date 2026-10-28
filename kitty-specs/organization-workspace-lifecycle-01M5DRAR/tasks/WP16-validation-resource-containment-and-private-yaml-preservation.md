---
work_package_id: WP16
title: Validation resource containment and private YAML preservation
dependencies:
- WP07
- WP14
requirement_refs:
- FR-007
- FR-008
- NFR-001
- NFR-003
- C-001
- C-003
planning_base_branch: codex/organization-workspace-lifecycle-20261020
merge_target_branch: codex/organization-workspace-lifecycle-20261020
branch_strategy: Planning artifacts for this mission were generated on codex/organization-workspace-lifecycle-20261020. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/organization-workspace-lifecycle-20261020 unless the human explicitly redirects the landing branch.
subtasks: []
phase: Prospective validation safety correction
history: []
agent_profile: implementer-ivan
authoritative_surface: tests/_support/run_basetemp.py
create_intent:
- docs/plans/engineering-notes/2026-10-28-pytest-containment-and-private-yaml.md
execution_mode: code_change
owned_files:
- tests/_support/run_basetemp.py
- tests/conftest.py
- tests/_support/test_run_basetemp.py
- docs/development/testing/testing-parallel.md
- src/kernel/yaml_io.py
- tests/kernel/test_yaml_io.py
- tests/specify_cli/core/test_hosted_posture.py
- docs/plans/engineering-notes/2026-10-28-pytest-containment-and-private-yaml.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP16: Validation resource containment and private YAML preservation

Load implementer-ivan through the supported current runtime. Existing Google owner implements; Subsequent independently reviews. Actual implementation claim must come from that owner through the supported command after prospective scope delivery; this prompt fabricates no claim.



## Required outcome

A normal pytest admission must refuse a foreign configuration ancestor before Source-managed HOME/temp/config effects. It must preserve controlled synthetic ancestors inside the actual run's enclosure, including the existing nested read-only Git regression. An atomic YAML update must preserve an existing regular private file's permission before the first payload write, without weakening new-file umask behavior or durable publication.

## One test-resource authority

Extend tests/_support/run_basetemp.py rather than add another root policy. Invoke its admission from the existing pytest_configure before the first worker-HOME mkdir or temp/config effect, and before pytest can clean an explicit basetemp. Preserve conftest definition order. Cover controller/default, explicit, worker and nested routes; explicit selection and caller lifecycle ownership remain, but do not grant a safety exception.

The canonical controller retains a real reserved-enclosure context: physical root, device/inode, owner/private mode, current run identity and actual live producer generation. A worker receives a routing projection through its existing controller handoff. A nested process must validate its candidate against the actual enclosing parent reservation/current process relationship and physical identity; an environment value or owner JSON alone cannot mint or enlarge an enclosure. Absent, copied, stale, forged or mismatched proof refuses before writes. Do not recreate a lifecycle creator or release authority from that projection.

Validate resolved paths, private enclosing permissions and foreign markers above the admitted boundary. Synthetic .git/.kittify markers are allowed only inside the validated run enclosure. Preserve tests/status/test_hermetic_ambient_git.py::test_suite_records_events_under_read_only_ancestor_git unchanged. A blanket marker ban would break its valid owned nested case. The implementation must make the actual handoff verification explicit and independently reviewable; no permissive fallback on unresolved provenance.

This is cooperative test-resource containment, not an OS sandbox against arbitrary code executing as the same user. It grants no sibling sweep, foreign-state cleanup, creator adoption or release permission. Preserve failed/uncertain resources with a named owner and next event.

## Canonical YAML writer

Repair src/kernel/yaml_io.py::write_mapping_atomic; keep a single writer. Inspect destinations without following a symlink and refuse symlink/nonregular or unsupported privilege metadata before payload effects. Preserve permission policy only; do not blindly copy ownership, ACLs or set-id bits. Preserve supported existing regular permission bits on the new descriptor before its first payload write. New destinations keep 0644 filtered by the caller's umask, without an unconditional chmod that overrides that umask.

Retain exclusive temporary creation, serialization fidelity, complete file fsync, atomic replacement, directory fsync behavior and failure propagation. Write the complete payload even when os.write returns a short count; zero progress or failure must not publish partial data. Cleanup may unlink only a temporary actually created by this invocation and still matching its identity; an exclusive-create collision must not delete a pre-existing successor.

Choose detected-preimage refusal rather than add an implicit persistent lock artifact to every YAML writer. Capture destination and parent identity/mode before effects and recheck before publication. Missing-to-present, replaced target, changed mode/type or parent redirection must refuse and retain the successor. This check is not an atomic compare-and-swap and does not protect against a hostile writer racing after the check. Callers remain responsible for coordinating concurrent writes; do not claim stronger guarantees. Use existing no-follow/atomic primitives where applicable and state platform limitations explicitly.

## Exact proposed ownership

- tests/_support/run_basetemp.py
- tests/conftest.py
- tests/_support/test_run_basetemp.py
- docs/development/testing/testing-parallel.md
- src/kernel/yaml_io.py
- tests/kernel/test_yaml_io.py
- tests/specify_cli/core/test_hosted_posture.py
- docs/plans/engineering-notes/2026-10-28-pytest-containment-and-private-yaml.md (create intent)

No hosted-posture implementation or product root-discovery change is needed. Existing assertions stay intact. Source's known chmod/OFF reconciliation is evidence, not the upstream repair.

## Acceptance before delivery

1. A controlled foreign configuration ancestor is refused before a sentinel/config write; exact bytes, identity, permissions and nanosecond times remain unchanged. Never reproduce against the real home.
2. Genuine enclosed-root success plus default/explicit/worker/nested and copied/forged/mismatched context controls; unchanged read-only owned-Git regression passes.
3. Existing private permissions are correct at the first write and after replacement under ordinary/restrictive umasks; new-file umask behavior remains.
4. The canonical hosted-drain caller updates only intended synthetic YAML keys, retaining private mode and unrelated keys/comments.
5. Symlink/nonregular, destination/parent-change refusal, short/zero writes, exclusive-create collision, fsync and cleanup controls preserve original/successor data.
6. Run changed/owning tests and specifically implicated architecture gates, required baseline and quality/changed-statement coverage, then independent exact-candidate review. The bootstrap change is a meaningful validation-input change; do not relabel earlier results as a pass of this new candidate.
7. Normal ready PR/checks and declared-target delivery precede installed acceptance. Mission integration, default-main delivery, installed packaging, ordinary producer integration and119-repository execution adoption remain separate proof stages.

Keep the independently owned engineering note's UX findings, decisions and limitations current. Record actual results externally after candidate freeze; preserve all failures and recovery receipts. No new cloud/model/tier, host action, checkout, competing writer or additional agent is admitted.

## Scope and architectural decision

This repairs the existing Python test bootstrap and canonical YAML writer as bounded migration/compatibility glue. It adds no new Python lifecycle engine. Preserve native lifecycle authority, prior WP states/approvals/events and WP15 five-file scope. WP16 depends on approved WP07/WP14 rather than WP15, avoiding a validation dependency cycle. The declared integration target remains codex/organization-workspace-lifecycle-20261020; delivery there is not default-main or installed adoption.
