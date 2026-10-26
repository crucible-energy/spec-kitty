# Owned LANES inspection and continuation: bounded decision

Owner: existing Root source lane, codex/owned-lanes-analysis, ed5e4cdd886af1b82deccb6d02dfc5ef6505723d.

## Decision

First deliver read-only `agent tasks status` for an explicitly validated plain-LANES owned root. Its existing canonical placement/event readers already support this topology; only the command's admission set incorrectly applies the general single-branch mutation restriction. Add a separate status-only capability set, keeping lifecycle, constructors and all mutation gates unchanged. Coordination topologies remain refused by this slice. Root remains the selected checkout, never its stale primary copy.

Do not combine active continuation implementation with this read-only correction. NEXT's finalized-board step recognizes in-progress resumes, but its action selector only previews new planned claims. A genuine continuation must preserve actor/owner and existing lane workspace identity. Its separately reviewed repair must not turn a validated planning root into an implementation workspace. The historical WP09 claim correction is already satisfied; no status rewrite or reapproval is warranted.

## Observable contract

Given a validated plain-LANES owned checkout and a different same-ID primary mission copy, when explicit or cwd-adopted status is requested, only the selected checkout's canonical task/event state is reported and no mission/checkout is created or advanced. Ordinary single-branch status remains unchanged. Invalid branch, missing explicit mission and coordination topology remain refused. Read status grants no implementation, acceptance, consolidation or serving authority.

## Validation

Commit failing-first public CLI real-Git fixture before implementation. Test explicit/cwd selection and stale primary decoy, canonical active state and dependency readiness, original metadata/status bytes, wrong-branch and unsupported-topology refusals. Run owning command/read-status subsystems plus relevant architecture gates and mandatory fast/publication checks on frozen candidate. Keep private outputs and cleanup identities external.

## UX findings, decisions and known limitations

The aggregate NEXT `dependencies_not_satisfied` reason does not prove an active WP is dependency-blocked. PDB WP09's canonical predecessor is approved; planned dependents are blocked on WP09. This inspection increment exposes current evidence without granting resumed execution. Actual retained Source job lifecycle, Auth semantic callback integration and live authority registrations are separate owner obligations. HELD/v5 remains unchanged.
