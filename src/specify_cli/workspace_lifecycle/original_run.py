"""Live original-creator custody; observation records cannot recreate this scope.

The creating process must outlive one actual foreground producer and its join.
This is a cooperative Python ownership boundary, not a sandbox against trusted
code using reflection. Separate CLI invocations cannot restore its authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn, SupportsIndex, final

from kernel.owned_process import process_budget
from specify_cli.workspace_lifecycle.adapters import GitHubDelivery, ManagedGitCreator, _git_env
from specify_cli.workspace_lifecycle.events import Completion
from specify_cli.workspace_lifecycle.state import StateError, StateStore

__all__ = ["OriginalWorkspaceRun"]

_FACTORY_KEY = object()


@final
class _AdmittedForegroundJob:
    """Live bridge to native admission; its serializable facts grant no release."""

    __slots__ = ("_native", "_digest", "_admission", "_pid", "_run", "_lock")

    def __init__(self, key: object, native: Path, digest: str, policy: dict[str, object]) -> None:
        if key is not _FACTORY_KEY:
            raise TypeError("Native foreground admission required")
        self._native, self._digest = native, digest
        self._pid = os.getpid()
        # Only a live original-object binding: native code owns policy and the
        # existing OriginalWorkspaceRun owns its one-attempt lifecycle phase.
        self._run: object | None = None
        self._lock = threading.Lock()
        self._verify()
        response = subprocess.run([str(native), "admit", json.dumps(policy)], env=_git_env(), capture_output=True, timeout=30, check=True)
        if len(response.stdout) > 65536:
            raise StateError("Native admission response exceeded bound")
        # Keep the native admission immutable. Parsed dictionaries are fresh
        # data views, never mutable deadline state or reconstructed authority.
        self._admission = bytes(response.stdout)

    def _verify(self) -> None:
        if type(self) is not _AdmittedForegroundJob or self._pid != os.getpid():
            raise StateError("Original job process required")
        path = self._native
        if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file() or not os.access(path, os.X_OK):
            raise StateError("Explicit regular native executor required")
        # Executable file integrity, not charter semantic hashing.
        if hashlib.sha256(path.read_bytes()).hexdigest() != self._digest:  # noqa: TID251
            raise StateError("Native foreground executor changed")

    def remaining(self, *, settlement: bool = False) -> float:
        self._verify()
        key = "settlement_deadline_ns" if settlement else "deadline_ns"
        remaining = (json.loads(self._admission)[key] - time.clock_gettime_ns(time.CLOCK_MONOTONIC)) / 1e9
        if remaining <= 0:
            raise StateError("Foreground job admission expired")
        return float(remaining)

    def command(self, run: OriginalWorkspaceRun, owner: ManagedGitCreator, argv: list[str]) -> list[str]:
        self.remaining()
        if self._run is not run:
            raise StateError("Exact original job-bound factory required")
        info = owner.store.root.lstat()
        request = {
            "admission": json.loads(self._admission),
            "argv": argv,
            "result_root": str(owner.store.root),
            "root_device": info.st_dev,
            "root_inode": info.st_ino,
            "generation": owner.token,
        }
        raw = json.dumps(request)
        if len(raw.encode()) > 65536:
            raise StateError("Foreground request exceeded native input bound")
        return [str(self._native), "run", raw]

    def __copy__(self) -> NoReturn:
        raise TypeError("Live foreground admission cannot be copied")

    def __deepcopy__(self, memo: dict[int, object]) -> NoReturn:
        raise TypeError("Live foreground admission cannot be copied")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("Live foreground admission cannot be serialized")


@final
class OriginalWorkspaceRun:
    """Retain exactly the owner created here, never a reconstructed owner."""

    __slots__ = ("_creator", "_generation", "_pid", "_phase", "_lock", "_path", "_branch", "_job")

    @classmethod
    def prepare_lane_allocation(
        cls,
        job: _AdmittedForegroundJob,
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
    ) -> _OriginalLaneAllocation:
        """Retain a live one-shot creator for a future fresh lane allocation."""
        if cls is not OriginalWorkspaceRun or type(job) is not _AdmittedForegroundJob:
            raise TypeError("Original admitted foreground job required")
        job.remaining()
        return _OriginalLaneAllocation(
            _FACTORY_KEY,
            job,
            store,
            repo_root=repo_root,
            path=path,
            branch=branch,
            repository=repository,
            repository_id=repository_id,
            delivery=delivery,
            on_complete=on_complete,
            expected_base_commit=expected_base_commit,
            accountable_owner=accountable_owner,
            on_admitted=on_admitted,
        )

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
        self._job: _AdmittedForegroundJob | None = None

    @classmethod
    def admit_foreground_job(
        cls,
        *,
        native_executor: Path,
        native_sha256: str,
        execution_timeout: float,
        settlement_timeout: float,
        accountable_owner: str,
        purpose: str,
        next_action: str,
        review_event: str,
    ) -> _AdmittedForegroundJob:
        if cls is not OriginalWorkspaceRun:
            raise TypeError("Original job admission cannot be replaced")
        # Conversion only; the native policy owns supported ranges and resources.
        if not all(math.isfinite(value) and value > 0 for value in (execution_timeout, settlement_timeout)):
            raise ValueError("Finite positive job allowances required")
        return _AdmittedForegroundJob(
            _FACTORY_KEY,
            native_executor,
            native_sha256,
            {
                "execution_ms": int(execution_timeout * 1000),
                "settlement_ms": int(settlement_timeout * 1000),
                "accountable_owner": accountable_owner,
                "purpose": purpose,
                "next_action": next_action,
                "review_event": review_event,
            },
        )

    @classmethod
    def create_for_job(
        cls,
        job: _AdmittedForegroundJob,
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
        if cls is not OriginalWorkspaceRun or type(job) is not _AdmittedForegroundJob:
            raise TypeError("Original admitted foreground job required")
        job.remaining()
        with job._lock:
            if job._run is not None or json.loads(job._admission)["policy"]["accountable_owner"] != accountable_owner:
                raise StateError("One original accountable job creation required")
            # Reserve once before the factory. Failure never makes a used
            # admission reusable or reconstructs an original creator.
            job._run = _FACTORY_KEY
        with process_budget(min(30.0, job.remaining())):
            result = cls.create(
                store,
                repo_root=repo_root,
                path=path,
                branch=branch,
                repository=repository,
                repository_id=repository_id,
                delivery=delivery,
                on_complete=on_complete,
                expected_base_commit=expected_base_commit,
                accountable_owner=accountable_owner,
                on_admitted=on_admitted,
            )
        result._job = job
        job._run = result
        return result

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
        if self._job is not None:
            raise StateError("Admitted job requires its original foreground boundary")
        self._run_one(argv, timeout=timeout)

    def run_foreground_job(self, argv: list[str], job: _AdmittedForegroundJob) -> None:
        self._require_process()
        if type(job) is not _AdmittedForegroundJob or self._job is not job:
            raise StateError("Exact live original foreground job required")
        self._run_one(argv, timeout=job.remaining(settlement=True), job=job)

    def _run_one(self, argv: list[str], *, timeout: float, job: _AdmittedForegroundJob | None = None) -> None:
        self._require_process()
        with self._lock:
            if self._phase != "created" or self._creator is None:
                raise StateError("One original producer attempt required")
            owner = self._creator
            self._phase = "running"
        try:
            if job is None:
                owner.run_producer(list(argv), timeout=timeout)
            else:
                command = job.command(self, owner, list(argv))
                owner._run_foreground_job(command, original_run=self, job=job)
        except BaseException:
            with self._lock:
                self._phase = "retained"
            raise
        with self._lock:
            self._phase = "joined"

    def require_running_job(self, job: _AdmittedForegroundJob, creator: ManagedGitCreator) -> None:
        self._require_process()
        if type(job) is not _AdmittedForegroundJob or self._job is not job or job._run is not self or self._creator is not creator or self._phase != "running":
            raise StateError("Exact original running foreground scope required")
        job.remaining()

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


@final
class _OriginalLaneAllocation:
    """Private, process-bound context; paths and receipts alone cannot recreate it."""

    __slots__ = ("_job", "_store", "_repo", "_path", "_branch", "_base", "_args", "_pid", "_run")

    def __init__(
        self,
        key: object,
        job: _AdmittedForegroundJob,
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
    ) -> None:
        if key is not _FACTORY_KEY or type(job) is not _AdmittedForegroundJob:
            raise TypeError("Original admitted foreground job required")
        if not isinstance(expected_base_commit, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", expected_base_commit):
            raise ValueError("Exact starting commit required")
        if json.loads(job._admission)["policy"]["accountable_owner"] != accountable_owner:
            raise StateError("Original accountable owner required")
        self._job, self._store = job, store
        self._repo, self._path, self._branch, self._base = repo_root.absolute(), path.absolute(), branch, expected_base_commit
        self._args: tuple[str, int, GitHubDelivery, Callable[[Completion], None], str, Callable[[dict[str, object]], None]] = (
            repository,
            repository_id,
            delivery,
            on_complete,
            accountable_owner,
            on_admitted,
        )
        self._pid = os.getpid()
        self._run: OriginalWorkspaceRun | None = None

    def _verify_target(self, repo_root: Path, path: Path, branch: str) -> None:
        if type(self) is not _OriginalLaneAllocation or self._pid != os.getpid():
            raise StateError("Original lane-creation process required")
        self._job.remaining()
        if (repo_root.absolute(), path.absolute(), branch) != (self._repo, self._path, self._branch):
            raise StateError("Original lane allocation target changed")
        if self._job._run is not None:
            raise StateError("Original lane allocation already attempted")

    def _create(self, repo_root: Path, path: Path, branch: str, base_commit: str) -> None:
        self._verify_target(repo_root, path, branch)
        if base_commit != self._base:
            raise StateError("Original lane allocation parent changed")
        repository, repository_id, delivery, on_complete, accountable_owner, on_admitted = self._args
        # create_for_job atomically reserves the one original job before any
        # creator effect; a failed admission never makes that job reusable.
        self._run = OriginalWorkspaceRun.create_for_job(
            self._job,
            self._store,
            repo_root=self._repo,
            path=self._path,
            branch=self._branch,
            repository=repository,
            repository_id=repository_id,
            delivery=delivery,
            on_complete=on_complete,
            expected_base_commit=self._base,
            accountable_owner=accountable_owner,
            on_admitted=on_admitted,
        )

    @property
    def original_run(self) -> OriginalWorkspaceRun:
        if type(self) is not _OriginalLaneAllocation or self._pid != os.getpid() or self._run is None or self._job._run is not self._run:
            raise StateError("Original lane creator is not available")
        return self._run

    def __copy__(self) -> NoReturn:
        raise TypeError("Original lane allocation cannot be copied")

    def __deepcopy__(self, memo: dict[int, object]) -> NoReturn:
        raise TypeError("Original lane allocation cannot be copied")

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError("Original lane allocation cannot be serialized")
