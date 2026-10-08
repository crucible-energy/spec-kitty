"""Explicit-owned single-branch completion; no branch integration or publish."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from kernel.meta_decode import decode_meta
from mission_runtime import ActionContextError
from specify_cli.acceptance import collect_feature_summary, resolve_acceptance_actor
from specify_cli.acceptance.matrix import read_acceptance_matrix
from specify_cli.coordination.status_transition import emit_status_transition_batch_transactional
from specify_cli.core.owned_mission import OwnedMission, require_unstaged_index, resolve_owned_mission
from specify_cli.core.paths import load_meta_fail_closed
from specify_cli.task_utils.support import run_git
from specify_cli.status.models import DoneEvidence, RepoEvidence, ReviewApproval, TransitionRequest, actor_identity_str
from specify_cli.status.reducer import materialize_snapshot, review_result_from_state
from specify_cli.status.store import read_event_stream
from specify_cli.sync.feature_flags import is_saas_sync_enabled

__all__ = ["complete_owned_mission"]


def _refuse(code: str, message: str) -> NoReturn:
    raise ActionContextError(code, message)


def _git(root: Path, *args: str) -> str:
    return str(run_git(list(args), cwd=root, check=True).stdout).strip()


def _commit(root: Path, value: object) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        _refuse("OWNED_ACCEPTANCE_REFUSED", "Acceptance requires full, existing commit identities.")
    assert isinstance(value, str)
    if _git(root, "rev-parse", f"{value}^{{commit}}") != value:
        _refuse("OWNED_ACCEPTANCE_REFUSED", "Acceptance commit identity does not resolve exactly.")
    return value


def _ancestor(root: Path, ancestor: str, head: str) -> None:
    if run_git(["merge-base", "--is-ancestor", ancestor, head], cwd=root, check=False).returncode != 0:
        _refuse("OWNED_SOURCE_DRIFT", "Accepted source must remain in the target history.")


def _at(owned: OwnedMission, commit: str, name: str) -> str:
    path = (owned.directory / name).relative_to(owned.root).as_posix()
    return _git(owned.root, "show", f"{commit}:{path}")


def _changed(owned: OwnedMission, before: str, after: str) -> set[str]:
    return set(_git(owned.root, "diff", "--name-only", "-z", before, after).split("\0")) - {""}


def _matrix_subject(data: dict[str, Any]) -> dict[str, Any]:
    """Bind criteria and verification configuration, allowing producer results."""
    result = json.loads(json.dumps(data))
    result.pop("overall_verdict", None)
    outputs = {
        "criteria": {"evidence", "pass_fail", "verified_by", "verified_at", "notes"},
        "negative_invariants": {"result", "evidence", "verified_ref", "verified_surface_kind",
                                "deferred_reason", "deferred_to_phase", "provenance_origin"},
    }
    for key, fields in outputs.items():
        result[key] = [{name: value for name, value in row.items() if name not in fields}
                       for row in result.get(key, [])]
    return dict(result)


def _acceptance_boundary(owned: OwnedMission, accepted: str, head: str) -> str:
    """Consume the existing accept producer's bounded local commit sequence.

    This checks custody/shape of local owner history, not external issuer auth.
    Subsequent source changes are not acceptance bookkeeping, even when clean.
    """
    prefix = owned.directory.relative_to(owned.root).as_posix()
    boundary = accepted
    for message, allowed in (
        (f"Record acceptance commit for {owned.slug}", {f"{prefix}/meta.json"}),
        (f"Finalize acceptance artifacts for {owned.slug}", {
            f"{prefix}/{name}" for name in ("meta.json", "status.json", "status.events.jsonl", "acceptance-matrix.json")
        }),
    ):
        following = _git(owned.root, "rev-list", "--reverse", "--first-parent", f"{boundary}..{head}").splitlines()
        if not following or _git(owned.root, "show", "-s", "--format=%s", following[0]) != message:
            continue
        candidate = following[0]
        if _git(owned.root, "show", "-s", "--format=%P", candidate) != boundary or not _changed(owned, boundary, candidate) <= allowed:
            _refuse("OWNED_SOURCE_DRIFT", "Acceptance bookkeeping changed source or target history.")
        boundary = candidate
    before_matrix = json.loads(_at(owned, accepted, "acceptance-matrix.json"))
    after_matrix = json.loads(_at(owned, boundary, "acceptance-matrix.json"))
    if _matrix_subject(before_matrix) != _matrix_subject(after_matrix):
        _refuse("OWNED_SOURCE_DRIFT", "Acceptance changed criterion or verification configuration.")
    if _at(owned, accepted, "status.events.jsonl").splitlines() != _at(owned, boundary, "status.events.jsonl").splitlines():
        _refuse("OWNED_SOURCE_DRIFT", "Acceptance bookkeeping changed the already canonical review/event inputs.")
    return boundary


def _accepted_source(owned: OwnedMission, meta: dict[str, Any], head: str) -> str:
    accepted = _commit(owned.root, meta.get("accept_commit"))
    source = _commit(owned.root, meta.get("accepted_from_commit"))
    history = meta.get("acceptance_history")
    keys = ("accepted_at", "accepted_by", "accepted_from_commit", "acceptance_mode", "accept_commit")
    if (
        not isinstance(history, list) or not history or not isinstance(history[-1], dict)
        or any(not isinstance(meta.get(key), str) or not meta[key].strip() for key in keys)
        or any(history[-1].get(key) != meta.get(key) for key in keys)
        or meta.get("acceptance_mode") not in {"pr", "local"}
        or _git(owned.root, "show", "-s", "--format=%P", accepted) != source
    ):
        _refuse("OWNED_ACCEPTANCE_REFUSED", "A coherent committed acceptance record is required.")
    _ancestor(owned.root, accepted, head)
    prefix = owned.directory.relative_to(owned.root).as_posix()
    accept_changes = _changed(owned, source, accepted)
    if accept_changes != {f"{prefix}/meta.json"}:
        _refuse("OWNED_SOURCE_DRIFT", "Acceptance commit must contain only its canonical metadata record.")
    boundary = _acceptance_boundary(owned, accepted, head)
    changed = _changed(owned, boundary, head)
    allowed = {f"{prefix}/{name}" for name in ("status.json", "status.events.jsonl")}
    if not changed <= allowed:
        _refuse("OWNED_SOURCE_DRIFT", "Source or acceptance evidence changed after acceptance; accept the new source first.")
    committed_meta = decode_meta(_at(owned, accepted, "meta.json"), on_malformed="raise")
    if not isinstance(committed_meta, dict):
        _refuse("OWNED_ACCEPTANCE_REFUSED", "Recorded acceptance metadata must be a mapping.")
    expected = json.loads(json.dumps(committed_meta))
    expected["accept_commit"] = accepted
    expected["acceptance_history"][-1]["accept_commit"] = accepted
    expected["status_phase"] = "1"
    if meta != expected:
        _refuse("OWNED_SOURCE_DRIFT", "Mission metadata changed after acceptance.")
    if any(committed_meta.get(key) != meta[key] for key in keys if key != "accept_commit"):
        _refuse("OWNED_ACCEPTANCE_REFUSED", "Current acceptance differs from its recorded commit.")
    return boundary


def _terminal_tail(owned: OwnedMission, accepted: str, states: dict[str, dict[str, Any]], head: str) -> str:
    original = _at(owned, accepted, "status.events.jsonl").splitlines()
    current = (owned.directory / "status.events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    if current[:len(original)] != original:
        _refuse("OWNED_SOURCE_DRIFT", "The accepted canonical event prefix changed.")
    tail = [json.loads(line) for line in current[len(original):]]
    if not tail:
        if any(state.get("lane") != "approved" for state in states.values()):
            _refuse("OWNED_APPROVAL_REFUSED", "Every work package must have a real canonical approval.")
        return head
    seen: set[str] = set()
    integration: str | None = None
    for row in tail:
        wp = row.get("wp_id")
        proof = row.get("evidence", {})
        repos = proof.get("repos", []) if isinstance(proof, dict) else []
        if (wp not in states or wp in seen or row.get("from_lane") != "approved"
            or row.get("to_lane") != "done" or row.get("force")
            or row.get("mission_slug") != owned.slug
            or states[wp].get("lane") != "done" or len(repos) != 1):
            _refuse("OWNED_SOURCE_DRIFT", "Only canonical approved-to-done completion may follow acceptance.")
        repo = repos[0]
        commit = _commit(owned.root, repo.get("commit"))
        _ancestor(owned.root, accepted, commit)
        _ancestor(owned.root, commit, head)
        if repo.get("branch") != owned.target or repo.get("repo") != owned.primary.name:
            _refuse("OWNED_SOURCE_DRIFT", "Completion evidence belongs to another repository or target.")
        if integration is not None and integration != commit:
            _refuse("OWNED_SOURCE_DRIFT", "Completion must bind one actual target commit.")
        integration = commit
        seen.add(wp)
    if seen != set(states):
        _refuse("OWNED_SOURCE_DRIFT", "A partial completion is not an accepted mission completion.")
    assert integration is not None
    if _at(owned, integration, "status.events.jsonl").splitlines() != original:
        _refuse("OWNED_SOURCE_DRIFT", "Integration proof must precede terminal bookkeeping.")
    return integration


@dataclass(frozen=True)
class _Completion:
    owned: OwnedMission
    head: str
    integration: str
    requests: list[TransitionRequest]
    wp_ids: list[str]


def _inspect(primary: Path, checkout: Path, handle: str | None, target: str | None, actor: str) -> _Completion:
    owned = resolve_owned_mission(primary, checkout, handle, target_override=target)
    require_unstaged_index(owned)
    if _git(owned.root, "status", "--porcelain", "--untracked-files=all"):
        _refuse("OWNED_DIRTY_REFUSED", "The selected checkout must be clean before completion.")
    if is_saas_sync_enabled():
        _refuse("OWNED_SYNC_UNSUPPORTED", "Explicit-owned completion does not support SaaS sync.")
    head = _git(owned.root, "rev-parse", "HEAD")
    if _git(owned.root, "rev-parse", f"refs/heads/{owned.target}") != head:
        _refuse("OWNED_BRANCH_REFUSED", "The real local target ref must equal the selected checkout HEAD.")
    meta = load_meta_fail_closed(owned.directory)
    assert meta is not None
    accepted = _accepted_source(owned, meta, head)
    summary = collect_feature_summary(owned.root, owned.slug, mutate_matrix=False, effective_root=owned.root)
    matrix = read_acceptance_matrix(owned.directory)
    if not summary.ok or matrix is None or matrix.overall_verdict != "pass":
        _refuse("OWNED_ACCEPTANCE_REFUSED", "Current acceptance checks and the complete matrix must pass without overrides.")
    states = materialize_snapshot(owned.directory).work_packages
    if not states or set(states) != {wp.work_package_id for wp in summary.work_packages}:
        _refuse("OWNED_APPROVAL_REFUSED", "Canonical status must cover every declared work package.")
    persisted = json.loads((owned.directory / "status.json").read_text(encoding="utf-8"))
    if persisted.get("work_packages") != states:
        _refuse("OWNED_APPROVAL_REFUSED", "Persisted status disagrees with the canonical event stream.")
    integration = _terminal_tail(owned, accepted, states, head)
    requests: list[TransitionRequest] = []
    stream = read_event_stream(owned.directory)
    if not meta.get("mission_id") or any(
        event.mission_slug != owned.slug or event.mission_id != meta["mission_id"]
        for event in stream.transitions
    ) or any(annotation.wp_id not in states for annotation in stream.annotations):
        _refuse("OWNED_APPROVAL_REFUSED", "Canonical events must belong to the selected mission identity.")
    for wp_id, state in sorted(states.items()):
        review = review_result_from_state(state).result
        if (review is None or review.verdict != "approved"
            or not isinstance(review.reviewer, str) or not review.reviewer.strip()
            or not isinstance(review.reference, str) or not review.reference.strip()):
            _refuse("OWNED_APPROVAL_REFUSED", f"{wp_id} has no complete canonical approval verdict.")
        assert review is not None
        evidence = DoneEvidence(
            review=ReviewApproval(review.reviewer, review.verdict, review.reference),
            repos=[RepoEvidence(owned.primary.name, owned.target, integration)],
        )
        implemented = [actor_identity_str(event.actor) for event in stream.transitions
                       if event.wp_id == wp_id and event.to_lane == "in_progress"]
        if not implemented or implemented[-1] == review.reviewer or state.get("force_count", 0):
            _refuse("OWNED_APPROVAL_REFUSED", f"{wp_id} requires actual independent, unforced review.")
        if state.get("lane") == "done":
            terminal = [event for event in stream.transitions if event.wp_id == wp_id and event.to_lane == "done"]
            if not terminal or terminal[-1].evidence is None or terminal[-1].evidence.to_dict() != evidence.to_dict():
                _refuse("OWNED_APPROVAL_REFUSED", f"{wp_id} terminal proof differs from its actual review/integration.")
            continue
        requests.append(TransitionRequest(
            feature_dir=owned.directory, mission_slug=owned.slug, repo_root=owned.primary,
            wp_id=wp_id, to_lane="done", actor=actor, execution_mode="single_branch",
            evidence=evidence.to_dict(), effective_root=owned.root,
            reason="Accepted source is already committed to the declared local target ref.",
        ))
    return _Completion(owned, head, integration, requests, sorted(states))


def complete_owned_mission(
    primary: Path, checkout: Path, handle: str | None, *, target: str | None = None,
    dry_run: bool = False, actor: str | None = None,
) -> dict[str, Any]:
    """Close genuinely accepted work on its existing target, through normal DONE guards."""
    identity = resolve_acceptance_actor(actor)
    if not identity:
        _refuse("OWNED_INPUT_INVALID", "Completion actor must be nonempty.")
    plan = _inspect(primary, checkout, handle, target, identity)

    def revalidate() -> None:
        current = _inspect(primary, checkout, handle, target, identity)
        if current != plan:
            _refuse("OWNED_SOURCE_DRIFT", "Owned source or canonical evidence changed before completion.")

    if not dry_run and plan.requests:
        emit_status_transition_batch_transactional(
            plan.requests, operation=f"complete owned mission {plan.owned.slug}",
            completion_precondition=revalidate, ensure_sync_daemon=False, sync_dossier=False,
        )
    return {
        "mission_slug": plan.owned.slug, "owned_checkout": str(plan.owned.root),
        "consolidation": "already_on_target", "dry_run": dry_run,
        "integration": {"kind": "local_target_ref", "branch": plan.owned.target, "commit": plan.integration},
        "completed_wps": [] if dry_run else plan.wp_ids,
        "pending_wps": [request.wp_id for request in plan.requests] if dry_run else [],
        "bookkeeping_commit": None if dry_run else _git(plan.owned.root, "rev-parse", "HEAD"),
        "remote_delivery": "separate_operator_gate",
    }
