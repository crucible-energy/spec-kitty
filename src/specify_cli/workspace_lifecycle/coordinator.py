"""Intent-before-effect coordination through an authenticated creator boundary.

Creators implement the shared producer fence and fresh preservation checks.
Untrusted event JSON is never accepted as creator authority. An interrupted
intent is inspected through recover(), never blindly sent to retire() again.
"""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, replace
from typing import Protocol, cast
from collections.abc import Sequence

from kernel.git import GitCommandError
from kernel.locks import LockAcquireTimeout, LockNotAcquired
from kernel.no_follow import NoFollowPathError

from specify_cli.workspace_lifecycle.discovery import WorkspaceObservation
from specify_cli.workspace_lifecycle.policy import Evidence, Identity, decide, generation_key
from specify_cli.workspace_lifecycle.state import AccountedObservation, Operation, StateError, StateStore, Status, Transaction, bound_identity


@dataclass(frozen=True)
class Result:
    status: Status
    reason: str

    def __post_init__(self) -> None:
        if self.status not in ("retained", "retired", "unknown") or not self.reason:
            raise ValueError("Creator must return an explicit settled or unknown outcome")


@dataclass(frozen=True)
class Recovered:
    intent: Operation
    result: Result


class Creator(Protocol):
    authority_id: str

    def hold(self, identity: Identity) -> AbstractContextManager[None]: ...
    def inspect(self, identity: Identity) -> Evidence: ...
    def retire(self, intent: Operation) -> Result: ...
    def recover(self, intent: Operation) -> Recovered: ...


def _record(tx: Transaction, operation: Operation) -> Operation:
    operations = tuple(op for op in tx.state.operations if op.event_id != operation.event_id) + (operation,)
    observations = []
    for row in tx.state.observations:
        identity = bound_identity(row)
        if (
            operation.status == "retired"
            and identity is not None
            and generation_key(identity, row["creator_id"]) == generation_key(operation.identity, operation.creator_id)
        ):
            row = row.copy()
            row["disposition"] = "retired"
            row["reason"] = "creator_generation_retirement_confirmed"
            row["exists"] = False
            row["retirement_event_id"] = operation.event_id
        observations.append(row)
    tx.commit(replace(tx.state, operations=operations, observations=tuple(observations)))
    return operation


def _observation_key(row: AccountedObservation) -> tuple[int, str, str, str, str, str, str, str]:
    generation = row.get("workspace_generation", "")
    return (
        row["repository_id"],
        row["common_dir"],
        row["path"],
        generation,
        row.get("lease_generation", ""),
        row.get("creator_id", ""),
        "" if generation else row["head"] or "",
        "" if generation else row["branch"] or "",
    )


class Coordinator:
    def __init__(self, store: StateStore) -> None:
        self.store = store

    def account(self, observations: list[WorkspaceObservation], *, registered: Sequence[tuple[Identity, Creator]] = ()) -> None:
        """Merge unknown observations; omission never discharges prior work."""
        with self.store.locked() as tx:
            current: dict[tuple[int, str, str, str, str, str, str, str], AccountedObservation] = {}
            bindings: dict[tuple[object, ...], list[tuple[Identity, str]]] = {}
            unavailable_bindings: set[tuple[object, ...]] = set()
            binding_key: tuple[object, ...]
            for expected, creator in registered:
                if any(
                    op.status in ("retired", "intent", "unknown")
                    and generation_key(op.identity, op.creator_id) == generation_key(expected, creator.authority_id)
                    for op in tx.state.operations
                ):
                    continue
                matching = [row for row in observations if self._matches(row, expected)]
                if not matching:
                    continue
                binding_key = (expected.repository_id, expected.repository, expected.common_dir, expected.path, expected.head, expected.branch)
                try:
                    with creator.hold(expected):
                        if creator.inspect(expected).identity != expected:
                            raise StateError("Creator accounting identity changed")
                        proof = (expected, creator.authority_id)
                        if proof not in bindings.setdefault(binding_key, []):
                            bindings[binding_key].append(proof)
                except (StateError, GitCommandError, OSError, ValueError, NoFollowPathError, LockNotAcquired, LockAcquireTimeout):
                    # Failed competing authority taints this observation only.
                    unavailable_bindings.add(binding_key)
                    continue
            for row in observations:
                # A discovery payload cannot mint creator bindings or retirement.
                unbound = cast(AccountedObservation, {k: v for k, v in row.items() if k in WorkspaceObservation.__annotations__})
                unbound["disposition"] = "retained"
                binding_key = (row["repository_id"], row["repository"], row["common_dir"], row["path"], row["head"], row["branch"])
                matches = bindings.get(binding_key, [])
                if binding_key in unavailable_bindings:
                    unbound["reason"] = "creator_registration_unavailable"
                elif len(matches) == 1 and row["exists"] and not row["bare"]:
                    identity, authority = matches[0]
                    unbound["workspace_generation"] = identity.workspace_generation
                    unbound["lease_generation"] = identity.lease_generation
                    unbound["creator_id"] = authority
                    unbound["reason"] = "registered_creator_observation"
                elif len(matches) > 1:
                    unbound["reason"] = "ambiguous_creator_registration"
                key = _observation_key(unbound)
                if key in current and current[key] != unbound:
                    raise StateError("Conflicting observations for one workspace")
                current[key] = unbound
            for prior in tx.state.observations:
                key = _observation_key(prior)
                if key not in current:
                    unavailable = prior.copy()
                    if unavailable["disposition"] != "retired":
                        unavailable["reason"] = "not_observed_in_latest_scope"
                    current[key] = unavailable
            tx.commit(replace(tx.state, observations=tuple(current[k] for k in sorted(current))))

    @staticmethod
    def _matches(row: WorkspaceObservation, expected: Identity) -> bool:
        return (
            (row["repository_id"], row["repository"], row["common_dir"], row["path"], row["head"], row["branch"])
            == (expected.repository_id, expected.repository, expected.common_dir, expected.path, expected.head, expected.branch)
            and row["exists"] and not row["bare"]
        )

    def account_owned(self, expected: Identity, creator: Creator) -> None:
        """Capture a registered creator generation under its authenticated hold.

        Unknown historical observations stay unknown; this is not an adoption
        procedure for an unregistered or replaced checkout.
        """
        with self.store.locked() as tx, creator.hold(expected):
            if any(
                op.status == "retired" and generation_key(op.identity, op.creator_id) == generation_key(expected, creator.authority_id)
                for op in tx.state.operations
            ):
                raise StateError("A retired creator generation cannot be readmitted")
            observed = creator.inspect(expected)
            if observed.identity != expected:
                raise StateError("Creator accounting identity changed")
            if any(
                op.status in ("intent", "unknown") and generation_key(op.identity, op.creator_id) == generation_key(expected, creator.authority_id)
                for op in tx.state.operations
            ):
                raise StateError("Recover uncertain intent before creator accounting")
            row: AccountedObservation = {
                "repository": expected.repository,
                "repository_id": expected.repository_id,
                "common_dir": expected.common_dir,
                "path": expected.path,
                "head": expected.head,
                "branch": expected.branch,
                "bare": False,
                "exists": True,
                "disposition": "retained",
                "reason": "registered_creator_observation",
                "workspace_generation": expected.workspace_generation,
                "lease_generation": expected.lease_generation,
                "creator_id": creator.authority_id,
            }
            rows = {_observation_key(prior): prior for prior in tx.state.observations}
            rows[_observation_key(row)] = row
            tx.commit(replace(tx.state, observations=tuple(rows[k] for k in sorted(rows))))

    def reconcile(self, event_id: str, expected: Identity, creator: Creator) -> Operation:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", event_id):
            raise StateError("Invalid lifecycle event identity")
        with self.store.locked() as tx:
            prior = next((op for op in tx.state.operations if op.event_id == event_id), None)
            if prior is not None and (prior.identity != expected or prior.creator_id != creator.authority_id):
                raise StateError("Event identity conflicts with retained generation")
            if prior is not None and prior.status in ("retired", "retained"):
                return prior
            terminal = next(
                (
                    op
                    for op in tx.state.operations
                    if op.status == "retired" and generation_key(op.identity, op.creator_id) == generation_key(expected, creator.authority_id)
                ),
                None,
            )
            if terminal is not None:
                if terminal.identity != expected:
                    raise StateError("A terminated generation cannot be reused with changed identity")
                # Reuse the sole canonical receipt; this new request is not a
                # second operation and must never produce another creator effect.
                return terminal
            if any(
                op.event_id != event_id
                and op.status in ("intent", "unknown")
                and generation_key(op.identity, op.creator_id) == generation_key(expected, creator.authority_id)
                for op in tx.state.operations
            ):
                raise StateError("Recover prior uncertain intent before another effect")
            with creator.hold(expected):
                if prior is not None:
                    recovered = creator.recover(prior)
                    if recovered.intent != prior:
                        raise StateError("Recovery result does not bind the retained intent")
                    return _record(tx, replace(prior, status=recovered.result.status, reason=recovered.result.reason))
                observed = creator.inspect(expected)
                digest = hashlib.sha256(json.dumps(asdict(observed), sort_keys=True, separators=(",", ":")).encode()).hexdigest()  # noqa: TID251 -- creator evidence integrity, not charter content hashing.
                reason = decide(expected, observed)
                if reason:
                    return _record(tx, Operation(event_id, expected, digest, "retained", reason, creator.authority_id, observed.release_id, observed.delivery_id))
                intent = _record(
                    tx, Operation(event_id, expected, digest, "intent", "creator_effect_pending", creator.authority_id, observed.release_id, observed.delivery_id)
                )
                try:
                    result = creator.retire(intent)
                except Exception:
                    result = Result("unknown", "creator_effect_unconfirmed")
                return _record(tx, replace(intent, status=result.status, reason=result.reason))

    def closeout(self, *, workflow_complete: bool) -> dict[str, object]:
        state = self.store.read()
        latest = {generation_key(op.identity, op.creator_id): op for op in state.operations}
        unresolved_observations = sum(row["disposition"] != "retired" for row in state.observations)
        unresolved_operations = sum(op.status != "retired" for op in latest.values())
        return {
            "workflow_complete": workflow_complete,
            "cleanup_complete": bool(latest or state.observations) and not unresolved_observations and not unresolved_operations,
            "unknown_observations": sum(row["disposition"] != "retired" and bound_identity(row) is None for row in state.observations),
            "unresolved_observations": unresolved_observations,
            "unresolved_operations": unresolved_operations,
            "scope": "recorded lifecycle state only; organization coverage remains separately bounded",
        }
