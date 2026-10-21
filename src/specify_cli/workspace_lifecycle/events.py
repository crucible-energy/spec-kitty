"""Untrusted completion hints carry identity, never owner release authority."""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from kernel.atomic import atomic_write
from kernel.locks import LockAcquireTimeout, LockNotAcquired, machine_file_lock
from kernel.no_follow import NoFollowPathError
from specify_cli.workspace_lifecycle.state import StateError, StateStore

from specify_cli.workspace_lifecycle.policy import Identity


@dataclass(frozen=True)
class Completion:
    event_id: str
    identity: Identity
    creator_id: str


class EventQueue:
    """Coalesced durable wakeup counter, never a release/effect payload.

    Short queue transactions are independent of the long coordinator hold. A
    worker acknowledges only the generation it processed; later hints survive.
    """

    def __init__(self, store: StateStore) -> None:
        self.store = store

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.store.observe()
        try:
            with machine_file_lock(self.store.root / "events.lock", blocking=True, timeout_s=0.05, private=True):
                self.store.observe()
                yield
        except (OSError, NoFollowPathError, LockAcquireTimeout, LockNotAcquired) as exc:
            raise StateError("Lifecycle event queue unavailable") from exc

    def _read(self) -> tuple[int, int]:
        try:
            raw = self.store.read_private("events.json", limit=4096)
        except FileNotFoundError:
            return (0, 0)
        try:
            value = json.loads(raw, object_pairs_hook=_pairs)
            if not isinstance(value, dict) or set(value) != {"schema_version", "generation", "acknowledged"}:
                raise ValueError("Invalid event history")
            if any(type(v) is not int for v in value.values()) or value["schema_version"] != 1:
                raise ValueError("Invalid event version")
            generation, acknowledged = value["generation"], value["acknowledged"]
            if not 0 <= acknowledged <= generation <= 2**63 - 1:
                raise ValueError("Invalid event order")
            return generation, acknowledged
        except (ValueError, TypeError) as exc:
            raise StateError("Lifecycle event history invalid") from exc

    def _write(self, generation: int, acknowledged: int) -> None:
        atomic_write(
            self.store.root / "events.json",
            json.dumps({"schema_version": 1, "generation": generation, "acknowledged": acknowledged}).encode(),
            durable=True,
            expected_parent=self.store._root_identity,
        )

    def notify(self, trigger: str, *, dispatch: Callable[[], None] | None = None) -> int:
        if trigger not in ("completion", "startup", "delivery"):
            raise StateError("Unsupported lifecycle wakeup")
        with self.locked():
            generation, acknowledged = self._read()
            if generation == 2**63 - 1:
                raise StateError("Lifecycle event generation exhausted")
            self._write(generation + 1, acknowledged)
            if dispatch is not None:
                dispatch()
            return generation + 1

    def snapshot(self) -> tuple[int, int]:
        with self.locked():
            return self._read()

    def acknowledge(self, generation: int) -> None:
        with self.locked():
            current, prior = self._read()
            if type(generation) is not int or not 0 <= generation <= current:
                raise StateError("Invalid lifecycle acknowledgment")
            self._write(current, max(prior, generation))


def _pairs(rows: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in rows:
        if key in result:
            raise ValueError("Duplicate event key")
        result[key] = value
    return result
