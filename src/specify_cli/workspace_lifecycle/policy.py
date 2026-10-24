"""Pure retention policy. Only an authenticated creator under its hold supplies evidence.

Discovery and untrusted event payloads are not constructors of release authority.
The coordinator consumes this protocol-level evidence; creator authentication and
shared producer exclusion are established by the configured adapter, not booleans
accepted from a CLI or ledger.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Identity:
    repository_id: int
    repository: str
    common_dir: str
    path: str
    head: str
    branch: str
    workspace_generation: str
    lease_generation: str

    def __post_init__(self) -> None:
        if type(self.repository_id) is not int or self.repository_id <= 0:
            raise ValueError("Repository ID is required")
        if not re.fullmatch(r"crucible-energy/[a-z0-9_.-]+", self.repository):
            raise ValueError("Verified organization repository identity is required")
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", self.head) or not self.branch.startswith("refs/heads/"):
            raise ValueError("Exact HEAD and local branch ref are required")
        if not self.workspace_generation or not self.lease_generation:
            raise ValueError("Creator workspace and lease generations are required")
        for value in (self.common_dir, self.path):
            if not Path(value).is_absolute() or ".." in Path(value).parts:
                raise ValueError("Absolute non-traversing identity paths are required")


@dataclass(frozen=True)
class Evidence:
    identity: Identity
    primary: bool
    clean: bool
    valuable_ignored: bool
    nested: bool
    runtime_held: bool
    producer_fenced: bool
    release_id: str | None
    delivery_id: str | None
    delivery_head: str | None
    supported: bool


def decide(expected: Identity, observed: Evidence) -> str | None:
    """Return a retention reason or eligibility; eligibility itself has no effect."""
    checks = (
        (observed.identity != expected, "identity_changed"),
        (observed.primary, "primary_checkout"),
        (not observed.supported, "creator_operation_unsupported"),
        (not observed.clean, "local_changes"),
        (observed.valuable_ignored, "valuable_ignored_state"),
        (observed.nested, "nested_repository"),
        (observed.runtime_held, "runtime_dependency"),
        (not observed.producer_fenced, "producer_fence_unproven"),
        (not observed.release_id, "owner_release_missing"),
        (not observed.delivery_id, "delivery_missing"),
        (observed.delivery_head != expected.head, "delivery_mismatch"),
    )
    return next((reason for refused, reason in checks if refused), None)


def generation_key(identity: Identity, creator_id: str) -> tuple[int, str, str, str, str]:
    """One creator workspace incarnation; a new lease cannot reuse an old release.

    A confirmed retirement ends this incarnation, while operation receipts still
    retain the exact lease, HEAD, ref, release and delivery that authorized it.
    """
    return identity.repository_id, identity.common_dir, identity.path, identity.workspace_generation, creator_id
