"""Explicit private observation scope; configuration grants no creator authority."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from kernel.atomic import atomic_write
from specify_cli.workspace_lifecycle.state import StateError, StateStore


@dataclass(frozen=True)
class OrganizationScope:
    roots: tuple[str, ...]
    max_depth: int = 6
    max_directories: int = 10000
    max_entries: int = 100000
    worker_timeout: float = 60.0
    organization: str = "crucible-energy"
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1 or type(self.schema_version) is not int or self.organization != "crucible-energy":
            raise StateError("Unsupported organization scope")
        if not isinstance(self.roots, tuple) or not 1 <= len(self.roots) <= 32:
            raise StateError("One to 32 explicit observation roots required")
        if any(not isinstance(root, str) or not root or "\0" in root or not Path(root).is_absolute() or ".." in Path(root).parts for root in self.roots):
            raise StateError("Absolute non-traversing observation roots required")
        for value, lower, upper in [(self.max_depth, 0, 64), (self.max_directories, 1, 100000), (self.max_entries, 1, 1000000)]:
            if type(value) is not int or not lower <= value <= upper:
                raise StateError("Invalid finite organization scan bounds")
        if type(self.worker_timeout) not in (int, float) or not math.isfinite(self.worker_timeout) or not 1 <= self.worker_timeout <= 300:
            raise StateError("Worker timeout must be finite and between 1 and 300 seconds")

    def record(self) -> dict[str, object]:
        return {**asdict(self), "roots": list(self.roots)}

    def admit(self, store: StateStore) -> None:
        # An initialized ledger and its existing lock admit the atomic scope
        # update. An active worker retains the exact scope it already loaded.
        with store.locked():
            atomic_write(store.root / "organization.json", json.dumps(self.record()).encode(), durable=True, expected_parent=store._root_identity)

    @classmethod
    def read(cls, store: StateStore) -> OrganizationScope | None:
        try:
            value = store.read_json_private("organization.json", limit=65536)
        except FileNotFoundError:
            return None
        keys = {"schema_version", "organization", "roots", "max_depth", "max_directories", "max_entries", "worker_timeout"}
        if not isinstance(value, dict) or set(value) != keys or not isinstance(value["roots"], list):
            raise StateError("Invalid organization scope record")
        try:
            return cls(**{**value, "roots": tuple(value["roots"])})
        except (TypeError, ValueError) as exc:
            raise StateError("Invalid organization scope record") from exc
