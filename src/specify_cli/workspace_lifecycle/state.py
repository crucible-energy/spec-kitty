"""Bounded private JSON ledger, serialized by the canonical local file lock.

A local lock protects bookkeeping only. It does not certify producer fencing,
creator authority, accepted delivery, or eligibility to remove a workspace.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import stat
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Literal, NotRequired, cast

from kernel.atomic import atomic_write
from kernel.locks import LockAcquireTimeout, LockNotAcquired, machine_file_lock
from kernel.no_follow import NoFollowPathError, fd_relative_dir_ops_supported, open_no_follow
from specify_cli.workspace_lifecycle.discovery import WorkspaceObservation
from specify_cli.workspace_lifecycle.policy import Identity, generation_key

Status = Literal["intent", "retained", "retired", "unknown"]
MAX_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 10000


class StateError(RuntimeError):
    """Ledger unavailable or changed; no authority may be inferred from failure."""


class AccountedObservation(WorkspaceObservation):
    workspace_generation: NotRequired[str]
    lease_generation: NotRequired[str]
    creator_id: NotRequired[str]
    retirement_event_id: NotRequired[str]


_BINDING_FIELDS = frozenset({"workspace_generation", "lease_generation", "creator_id"})
_OBSERVATION_FIELDS = frozenset(WorkspaceObservation.__annotations__)


def bound_identity(row: AccountedObservation) -> Identity | None:
    if not _BINDING_FIELDS.issubset(row):
        return None
    if not isinstance(row["head"], str) or not isinstance(row["branch"], str):
        raise StateError("Bound observation requires exact source identity")
    try:
        return Identity(
            row["repository_id"],
            row["repository"],
            row["common_dir"],
            row["path"],
            row["head"],
            row["branch"],
            row["workspace_generation"],
            row["lease_generation"],
        )
    except ValueError as exc:
        raise StateError("Invalid bound observation identity") from exc


@dataclass(frozen=True)
class Operation:
    event_id: str
    identity: Identity
    evidence_sha256: str
    status: Status
    reason: str
    creator_id: str
    release_id: str | None
    delivery_id: str | None

    def authorization_fingerprint(self) -> str:
        """Bind every immutable dispatch input; result status/reason may evolve."""
        payload = asdict(self)
        payload.pop("status")
        payload.pop("reason")
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()  # noqa: TID251 -- lifecycle authorization integrity, not charter hashing.


@dataclass(frozen=True)
class State:
    revision: int = 0
    observations: tuple[AccountedObservation, ...] = ()
    operations: tuple[Operation, ...] = ()


def _mapping(value: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys or not all(isinstance(k, str) for k in value):
        raise StateError("Unexpected ledger shape")
    return cast(dict[str, object], value)


def _pairs(rows: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in rows:
        if key in result:
            raise StateError("Duplicate ledger key")
        result[key] = value
    return result


def _identity(raw: object) -> Identity:
    fields = set(Identity.__dataclass_fields__)
    d = _mapping(raw, fields)
    if type(d["repository_id"]) is not int or any(not isinstance(d[k], str) for k in fields - {"repository_id"}):
        raise StateError("Invalid operation identity")
    try:
        return Identity(
            d["repository_id"],
            *(cast(str, d[k]) for k in ("repository", "common_dir", "path", "head", "branch", "workspace_generation", "lease_generation")),
        )
    except ValueError as exc:
        raise StateError("Invalid operation identity") from exc


def _observation(raw: object) -> AccountedObservation:
    if not isinstance(raw, dict):
        raise StateError("Invalid observation shape")
    keys = set(raw)
    if not _OBSERVATION_FIELDS.issubset(keys) or not keys.issubset(_OBSERVATION_FIELDS | _BINDING_FIELDS | {"retirement_event_id"}):
        raise StateError("Invalid observation fields")
    d = _mapping(raw, keys)
    bindings = _BINDING_FIELDS & keys
    if bindings and bindings != _BINDING_FIELDS:
        raise StateError("Incomplete creator observation binding")
    for key in keys & (_BINDING_FIELDS | {"retirement_event_id"}):
        if not isinstance(d[key], str) or not d[key]:
            raise StateError("Invalid creator observation binding")
    if d["disposition"] not in ("retained", "retired") or (d["disposition"] == "retired") != ("retirement_event_id" in keys):
        raise StateError("Invalid observation disposition")
    if type(d["repository_id"]) is not int or d["repository_id"] <= 0:
        raise StateError("Invalid observation repository")
    for key in ("repository", "common_dir", "path", "disposition", "reason"):
        if not isinstance(d[key], str):
            raise StateError("Invalid observation value")
    for key in ("head", "branch"):
        if d[key] is not None and not isinstance(d[key], str):
            raise StateError("Invalid observation ref")
    if any(type(d[k]) is not bool for k in ("bare", "exists")):
        raise StateError("Invalid observation flags")
    result = cast(AccountedObservation, d)
    bound_identity(result)
    return result


def _require_terminal_order(operations: list[Operation]) -> None:
    closed = set()
    for operation in operations:
        token = generation_key(operation.identity, operation.creator_id)
        if token in closed:
            raise StateError("Operation recorded after terminal generation retirement")
        if operation.status == "retired":
            closed.add(token)


def _decode(raw: bytes) -> State:
    if len(raw) > MAX_BYTES:
        raise StateError("Ledger size limit exceeded")
    try:
        value: object = json.loads(raw, object_pairs_hook=_pairs)
        data = _mapping(value, {"schema_version", "revision", "observations", "operations"})
        if type(data["schema_version"]) is not int or data["schema_version"] != 1 or type(data["revision"]) is not int or data["revision"] < 0:
            raise StateError("Unsupported ledger schema or revision")
        observations, operations = data["observations"], data["operations"]
        if not isinstance(observations, list) or not isinstance(operations, list) or len(observations) + len(operations) > MAX_ENTRIES:
            raise StateError("Invalid ledger entry count")
        parsed = []
        seen = set()
        for row in operations:
            op = _mapping(row, {"event_id", "identity", "evidence_sha256", "status", "reason", "creator_id", "release_id", "delivery_id"})
            if any(not isinstance(op[k], str) for k in ("event_id", "evidence_sha256", "status", "reason", "creator_id")):
                raise StateError("Invalid operation values")
            if not op["creator_id"] or any(op[k] is not None and not isinstance(op[k], str) for k in ("release_id", "delivery_id")):
                raise StateError("Invalid creator evidence identities")
            event_id = cast(str, op["event_id"])
            if not event_id or event_id in seen or op["status"] not in ("intent", "retained", "retired", "unknown"):
                raise StateError("Invalid or duplicate operation")
            digest = cast(str, op["evidence_sha256"])
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise StateError("Invalid evidence digest")
            parsed.append(
                Operation(
                    event_id,
                    _identity(op["identity"]),
                    digest,
                    op["status"],
                    cast(str, op["reason"]),
                    cast(str, op["creator_id"]),
                    cast(str | None, op["release_id"]),
                    cast(str | None, op["delivery_id"]),
                )
            )
            seen.add(event_id)
        _require_terminal_order(parsed)
        rows = tuple(_observation(row) for row in observations)
        by_event = {op.event_id: op for op in parsed}
        for row in rows:
            if row["disposition"] == "retired":
                identity = bound_identity(row)
                retirement = by_event.get(row["retirement_event_id"])
                if (
                    identity is None
                    or retirement is None
                    or retirement.status != "retired"
                    or generation_key(identity, row["creator_id"]) != generation_key(retirement.identity, retirement.creator_id)
                ):
                    raise StateError("Observation retirement lacks its exact creator generation receipt")
        return State(data["revision"], rows, tuple(parsed))
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise StateError("Corrupt lifecycle ledger") from exc


def _encode(state: State) -> bytes:
    data = {"schema_version": 1, "revision": state.revision, "observations": state.observations, "operations": [asdict(op) for op in state.operations]}
    try:
        raw = (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    except (ValueError, TypeError) as exc:
        raise StateError("Invalid lifecycle state payload") from exc
    _decode(raw)
    return raw


class Transaction:
    def __init__(self, store: StateStore, state: State) -> None:
        self.store, self.state = store, state
        self._active = True
        self._thread = threading.get_ident()
        self._pid = os.getpid()

    def commit(self, candidate: State) -> None:
        if not self._active or threading.get_ident() != self._thread or os.getpid() != self._pid:
            raise StateError("Transaction is outside its owning lock lifetime or thread")
        self.store._check_root()
        updated = replace(candidate, revision=self.state.revision + 1)
        raw = _encode(updated)
        try:
            atomic_write(self.store.root / "state.json", raw, durable=True, expected_parent=self.store._root_identity)
        except OSError as exc:
            raise StateError("Lifecycle state durability unconfirmed") from exc
        self.state = updated


class StateStore:
    def __init__(self, root: Path, *, timeout: float = 2.0) -> None:
        if not math.isfinite(timeout) or timeout <= 0:
            raise StateError("Finite positive lock timeout required")
        if not fd_relative_dir_ops_supported():
            raise StateError("Strict lifecycle persistence unsupported on this platform")
        self.root = root.absolute()
        self.timeout = timeout
        self._root_identity = self._check_root()

    def _check_root(self) -> tuple[int, int]:
        try:
            if ".." in self.root.parts or any(p.is_symlink() for p in (self.root, *self.root.parents)):
                raise StateError("Symlinked or traversing lifecycle state path")
            info = self.root.lstat()
            if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid():
                raise StateError("Lifecycle state directory must be owned and private")
            identity = (info.st_dev, info.st_ino)
            if hasattr(self, "_root_identity") and identity != self._root_identity:
                raise StateError("Lifecycle state directory identity changed")
            return identity
        except OSError as exc:
            raise StateError("Lifecycle state directory unavailable") from exc

    def read_private(self, name: str, *, limit: int = MAX_BYTES) -> bytes:
        """Read one bounded private, single-link sidecar under the bound root."""
        self._check_root()
        if Path(name).name != name or name in (".", "..") or not 0 < limit <= MAX_BYTES:
            raise StateError("Invalid private lifecycle record")
        fd = open_no_follow(self.root / name, os.O_RDONLY | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
                raise StateError("Lifecycle state file must be owned and private")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise StateError("Lifecycle record size exceeded")
            return raw
        finally:
            os.close(fd)

    def read_json_private(self, name: str, *, limit: int = MAX_BYTES) -> object:
        """Decode bounded owned JSON with the ledger's duplicate-key refusal."""
        try:
            value: object = json.loads(self.read_private(name, limit=limit), object_pairs_hook=_pairs)
            return value
        except (ValueError, TypeError) as exc:
            raise StateError("Invalid private lifecycle JSON") from exc

    def _read(self) -> State:
        try:
            return _decode(self.read_private("state.json"))
        except FileNotFoundError as exc:
            raise StateError("Lifecycle ledger missing; explicit recovery required") from exc
        except (OSError, NoFollowPathError) as exc:
            raise StateError("Lifecycle state unavailable") from exc

    @classmethod
    def initialize(cls, root: Path, *, timeout: float = 2.0) -> StateStore:
        """Explicit first admission into an existing empty, private directory.

        Missing previously committed state is never initialized implicitly.
        The caller owns directory creation and its durable parent admission.
        """
        store = cls(root, timeout=timeout)
        with os.scandir(store.root) as entries:
            if next(entries, None) is not None:
                raise StateError("Initialization requires an empty private directory")
        with store._guard():
            if (store.root / "state.json").exists() or (store.root / "state.json").is_symlink():
                raise StateError("Lifecycle state already initialized")
            try:
                atomic_write(store.root / "state.json", _encode(State()), durable=True, expected_parent=store._root_identity)
            except OSError as exc:
                raise StateError("Lifecycle initialization durability unconfirmed") from exc
        return store

    @contextmanager
    def _guard(self) -> Iterator[None]:
        self._check_root()
        try:
            with machine_file_lock(self.root / "lifecycle.lock", blocking=True, timeout_s=self.timeout, private=True):
                self._check_root()
                yield
        except (LockAcquireTimeout, LockNotAcquired, NoFollowPathError, OSError) as exc:
            raise StateError("Lifecycle state lock or IO unavailable") from exc

    @contextmanager
    def locked(self) -> Iterator[Transaction]:
        # Refuse absent/invalid history without creating an admission side effect.
        # The authoritative read is repeated under the lock; this preflight does
        # not establish currentness or replace serialization.
        self._check_root()
        self._read()
        with self._guard():
            transaction = Transaction(self, self._read())
            try:
                yield transaction
            finally:
                transaction._active = False

    def observe(self) -> State:
        """Atomic observation only; no lock acquisition, mutation or effect authority."""
        self._check_root()
        return self._read()

    def read(self) -> State:
        with self.locked() as transaction:
            return transaction.state
