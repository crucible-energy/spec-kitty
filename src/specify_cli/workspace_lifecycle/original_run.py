"""Live original-creator custody; observation records cannot recreate this scope.

The creating process must outlive one actual foreground producer and its join.
This is a cooperative Python ownership boundary, not a sandbox against trusted
code using reflection. Separate CLI invocations cannot restore its authority.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn, SupportsIndex, final

from specify_cli.workspace_lifecycle.adapters import GitHubDelivery, ManagedGitCreator
from specify_cli.workspace_lifecycle.events import Completion
from specify_cli.workspace_lifecycle.state import StateError, StateStore

__all__ = ["OriginalWorkspaceRun"]

_FACTORY_KEY = object()


@final
class OriginalWorkspaceRun:
    """Retain exactly the owner created here, never a reconstructed owner."""

    __slots__ = ("_creator", "_generation", "_pid", "_phase", "_lock", "_path", "_branch")

    def __init__(self, *, _factory_key: object) -> None:
        if _factory_key is not _FACTORY_KEY:
            raise TypeError("Use the original workspace factory")
        self._creator: ManagedGitCreator | None = None
        self._generation = ""
        self._pid = os.getpid()
        self._phase = "creating"
        self._lock = threading.Lock()
        self._path = Path()
        self._branch = ""

    @classmethod
    def create(
        cls,
        store: StateStore,
        *,
        repo_root: Path,
        path: Path,
        branch: str,
        repository: str,
        repository_id: int,
        delivery: GitHubDelivery,
        on_complete: Callable[[Completion], None],
        expected_base_commit: str,
        accountable_owner: str,
        on_admitted: Callable[[dict[str, object]], None],
    ) -> OriginalWorkspaceRun:
        if cls is not OriginalWorkspaceRun:
            raise TypeError("Original workspace scope cannot be replaced")
        # Allocate the retaining scope before the creator's first Git effect.
        result = cls(_factory_key=_FACTORY_KEY)
        owner = ManagedGitCreator.create(
            store,
            repo_root=repo_root,
            path=path,
            branch=branch,
            repository=repository,
            repository_id=repository_id,
            delivery=delivery,
            on_complete=on_complete,
            expected_base_commit=expected_base_commit,
            creator_kind="ordinary_git",
            accountable_owner=accountable_owner,
            on_admitted=on_admitted,
        )
        result._creator = owner
        identity = owner.identity
        result._generation = identity.workspace_generation
        result._path = Path(identity.path)
        result._branch = identity.branch
        result._phase = "created"
        return result

    @property
    def path(self) -> Path:
        """Observation-only original path, not permission to adopt or remove."""
        return self._path

    @property
    def branch(self) -> str:
        """Observation-only full local ref, including ``refs/heads/``."""
        return self._branch

    def _require_process(self) -> None:
        # Check before taking a lock that could have been inherited while held.
        if type(self) is not OriginalWorkspaceRun or getattr(self, "_pid", None) != os.getpid():
            raise StateError("Original creating process required")

    def run_producer(self, argv: list[str], *, timeout: float) -> None:
        self._require_process()
        with self._lock:
            if self._phase != "created" or self._creator is None:
                raise StateError("One original producer attempt required")
            owner = self._creator
            self._phase = "running"
        try:
            owner.run_producer(list(argv), timeout=timeout)
        except BaseException:
            with self._lock:
                self._phase = "retained"
            raise
        with self._lock:
            self._phase = "joined"

    def require_joined_for(self, creator: ManagedGitCreator) -> None:
        """Creator-side check during finalization; never a serializable proof.

        The creator must require this exact canonical class, not a duck-typed
        callback. HEAD and lease may advance during the real producer: stable
        generation, exact object and current process identify this scope.
        """
        self._require_process()
        with self._lock:
            owner = self._creator
            if self._phase != "completing" or owner is None:
                raise StateError("Exact original joined producer scope required")
            if creator is not owner or owner.token != self._generation:
                raise StateError("Exact original joined producer scope required")

    def complete(self, *, pr: int) -> None:
        self._require_process()
        if type(pr) is not int or pr <= 0:
            raise ValueError("Positive PR number required")
        with self._lock:
            if self._phase != "joined" or self._creator is None:
                raise StateError("Original successful joined producer required")
            owner = self._creator
            self._phase = "completing"
        try:
            # The creator owns durable release and validates this exact witness.
            # A hint can fail after release: never retry or mint another proof.
            owner.complete(pr=pr, original_run=self)
        except BaseException:
            with self._lock:
                self._phase = "retained"
            raise
        with self._lock:
            self._phase = "completed"

    def __copy__(self) -> OriginalWorkspaceRun:
        raise TypeError("Original creator authority cannot be copied")

    def __deepcopy__(self, memo: dict[int, object]) -> OriginalWorkspaceRun:
        raise TypeError("Original creator authority cannot be copied")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("Original creator authority cannot be serialized")
