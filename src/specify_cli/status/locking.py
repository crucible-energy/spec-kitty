"""Per-feature status locking for shared planning artifacts.

Serializes access to feature-level status artifacts that are written on the
planning checkout (`status.events.jsonl`, `status.json`, and `tasks.md`).
Parallel agents may run from separate worktrees, but they still converge on
the same planning repo paths, so these writes need an inter-process lock.
"""

from __future__ import annotations

import subprocess
import threading
import os
from dataclasses import dataclass, field
from contextlib import contextmanager, suppress
from pathlib import Path
from collections.abc import Iterator

from filelock import FileLock, Timeout

_thread_state = threading.local()
_process_id = os.getpid()
_fork_refused = False
_fork_guard = threading.RLock()
_active_locks: dict[int, FileLock] = {}
# Modern filelock owns descriptor fork transitions and inherited-instance PID
# checks. Detect that bounded capability rather than pinning dependency versions.
# Our protocol remains only for older supported backends without those hooks.
_UPSTREAM_FORK_PROTOCOL = callable(getattr(FileLock, "_acquire_with_fork_tracking", None)) and callable(getattr(FileLock, "_raise_if_inherited", None))


class FeatureStatusLockTimeoutError(RuntimeError):
    """Raised when the feature status lock cannot be acquired."""


class StatusReplacementConflict(RuntimeError):
    """A reentrant writer attempted to append during an exclusive replacement."""


class StatusLockForkRefused(RuntimeError):
    """A fork child inherited active status operations; use a fresh interpreter."""


def _discard_inherited_state() -> None:
    """Child-only detach/close, NEVER release(), LOCK_UN or unlink a parent lock."""
    global _thread_state, _process_id, _fork_refused, _fork_guard, _active_locks
    if _process_id == os.getpid():
        return  # This is not a public reset seam in the owning parent process.
    inherited = list(_active_locks.values())
    _fork_refused = _fork_refused or bool(inherited)
    for lock in inherited if not _UPSTREAM_FORK_PROTOCOL else ():
        # Legacy-only: modern filelock's earlier child hook has already detached
        # its owned descriptors with inode/PID safeguards. Do not close them twice
        # or modify its private transition/context bookkeeping.
        fd = lock._context.lock_file_fd
        lock._context.lock_file_fd = None
        lock._context.lock_counter = 0
        if fd is not None:
            with suppress(OSError):
                os.close(fd)  # close duplicate only; flock ownership stays with parent
    _active_locks = {}
    _thread_state = threading.local()
    _process_id = os.getpid()
    _fork_guard = threading.RLock()


def _check_process() -> None:
    _discard_inherited_state()  # PID fallback for hosts without register_at_fork
    if _fork_refused:
        raise StatusLockForkRefused("Status writes refused in fork child with inherited active locks; exec a fresh interpreter")


class _ProcessFileLock(FileLock):
    """Track each NONBLOCKING native acquire/release under the at-fork guard."""

    owner_pid: int = 0

    def _acquire(self) -> None:
        if self.owner_pid != os.getpid():
            raise StatusLockForkRefused("Cannot acquire an inherited native status lock")
        # Do not hold this guard across FileLock.acquire()'s wait/poll loop: a
        # parent thread must remain able to release the competing native lock.
        with _fork_guard:
            super()._acquire()
            if self.owner_pid != os.getpid():
                # Also cover a reentrant fork/signal hook inside the native
                # attempt, before the backend published its newly opened fd.
                fd = self._context.lock_file_fd
                self._context.lock_file_fd = None
                if fd is not None:
                    with suppress(OSError):
                        os.close(fd)
                raise StatusLockForkRefused("Fork interrupted a native status lock acquisition")

    def _release(self) -> None:
        if self.owner_pid != os.getpid():
            _discard_inherited_state()
            self._context.lock_file_fd = None
            self._context.lock_counter = 0
            return
        with _fork_guard:
            super()._release()

    def _fallback_to_soft_lock(self) -> None:
        # A backend class mutation would bypass the native acquisition/fork
        # instrumentation. Refuse it rather than weaken this ownership contract.
        raise StatusLockForkRefused("Canonical status locks require a native backend; soft-lock fallback is unsupported")


def _before_fork() -> None:
    if not _UPSTREAM_FORK_PROTOCOL:
        _fork_guard.acquire()


def _after_fork_parent() -> None:
    if not _UPSTREAM_FORK_PROTOCOL:
        _fork_guard.release()  # No parent tables, fences or native descriptors reset.


if hasattr(os, "register_at_fork"):
    os.register_at_fork(before=_before_fork, after_in_parent=_after_fork_parent, after_in_child=_discard_inherited_state)


@dataclass
class StatusReplacementFence:
    """Same-lock reentrancy guard; never a second lock or status authority."""

    conflicted: bool = False
    owner_pid: int = field(default_factory=os.getpid)

    def check(self) -> None:
        if self.owner_pid != os.getpid():
            raise StatusLockForkRefused("Cannot use an inherited replacement fence in a fork child")
        if self.conflicted:
            raise StatusReplacementConflict("Status writer attempted a reentrant append during history installation")


def _replacement_fences() -> dict[str, StatusReplacementFence]:
    _check_process()
    fences = getattr(_thread_state, "replacement_fences", None)
    if fences is None:
        fences = {}
        _thread_state.replacement_fences = fences
    return fences


def _get_thread_locks() -> dict[str, tuple[FileLock, int]]:
    """Return per-thread lock bookkeeping for re-entrant acquisitions."""
    _check_process()
    locks = getattr(_thread_state, "locks", None)
    if locks is None:
        locks = {}
        _thread_state.locks = locks
    return locks


def _git_common_dir(repo_root: Path) -> Path:
    """Resolve the git common dir shared by the repo and its worktrees."""
    # First append may start from a missing directory. Probe Git from its nearest
    # existing parent so the canonical common-dir key remains identical before
    # and after mkdir. Non-Git callers keep the same original .git fallback.
    probe = repo_root
    while not probe.is_dir() and probe.parent != probe:
        probe = probe.parent
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=probe,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return repo_root / ".git"

    common_dir = result.stdout.strip()
    if not common_dir:
        return repo_root / ".git"

    resolved = Path(common_dir)
    if not resolved.is_absolute():
        resolved = (probe / resolved).resolve()
    return resolved


def feature_status_lock_path(repo_root: Path, mission_slug: str) -> Path:
    """Return the per-feature lock file path under the git common dir."""
    common_dir = _git_common_dir(repo_root)
    return common_dir / "spec-kitty-locks" / f"{mission_slug}.status.lock"


@contextmanager
def feature_status_lock(
    repo_root: Path,
    mission_slug: str,
    *,
    timeout: float = -1,
) -> Iterator[Path]:
    """Acquire the per-feature status lock.

    Uses the git common dir so main checkouts and worktrees coordinate on the
    same lock file. Locking is re-entrant within a single thread so callers can
    safely wrap a larger transaction around helpers that also acquire the lock.
    """
    _check_process()
    owner_pid = os.getpid()
    lock_path = feature_status_lock_path(repo_root, mission_slug)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    held_locks = _get_thread_locks()
    lock_key = str(lock_path)
    held = held_locks.get(lock_key)
    if held is not None:
        lock, depth = held
        held_locks[lock_key] = (lock, depth + 1)
        try:
            yield lock_path
        finally:
            if owner_pid == os.getpid():
                lock, depth = held_locks[lock_key]
                held_locks[lock_key] = (lock, depth - 1)
        return

    # There is still one distinct instance per thread/key. Only legacy cleanup
    # needs a non-thread-local backend context; upstream tracks its own threads.
    if _UPSTREAM_FORK_PROTOCOL:
        # Use the supported public API unwrapped. Its native transition protocol
        # must never wait for a mutex held by our before-fork callback.
        lock = FileLock(str(lock_path), timeout=timeout)
    else:
        lock = _ProcessFileLock(str(lock_path), timeout=timeout, thread_local=False)
        lock.owner_pid = owner_pid
    if owner_pid != os.getpid():
        raise StatusLockForkRefused("Fork interrupted canonical status lock construction")
    with _fork_guard:
        _active_locks[id(lock)] = lock  # Includes acquisition and cleanup windows.
    try:
        try:
            lock.acquire()
        except Timeout as exc:
            raise FeatureStatusLockTimeoutError(f"Timed out acquiring feature status lock for {mission_slug}: {lock_path}") from exc
        except RuntimeError as exc:
            if owner_pid != os.getpid():
                raise StatusLockForkRefused("Native status lock acquisition refused in fork child") from exc
            raise
        _check_process()
        held_locks[lock_key] = (lock, 1)
        try:
            yield lock_path
        finally:
            if owner_pid == os.getpid():
                del held_locks[lock_key]
    finally:
        if owner_pid == os.getpid():
            try:
                if _UPSTREAM_FORK_PROTOCOL:
                    lock.release()
                else:
                    with _fork_guard:
                        lock.release()
            finally:
                with _fork_guard:
                    _active_locks.pop(id(lock), None)


@contextmanager
def status_log_write_lock(feature_dir: Path) -> Iterator[Path]:
    """Serialize supported low-level appenders on the canonical mission key.

    Ordinary nested writes remain reentrant. During a replacement's install or
    rollback phase, a same-thread append refuses instead of deadlocking or being
    overwritten; other threads/processes wait on the existing FileLock.
    """
    from specify_cli.workspace.root_resolver import resolve_status_lock_root

    root = resolve_status_lock_root(feature_dir)
    with feature_status_lock(root, feature_dir.name) as lock_path:
        fence = _replacement_fences().get(str(lock_path))
        if fence is not None:
            fence.conflicted = True
            fence.check()
        yield lock_path


@contextmanager
def status_replacement_fence(root: Path, mission_slug: str) -> Iterator[StatusReplacementFence]:
    """Prevent reentrant appends while installing/rolling back under the same lock."""
    _check_process()
    owner_pid = os.getpid()
    key = str(feature_status_lock_path(root, mission_slug))
    if key not in _get_thread_locks():
        raise StatusReplacementConflict("History installation requires the canonical mission lock")
    fences = _replacement_fences()
    if key in fences:
        raise StatusReplacementConflict("Nested history installation is unsupported")
    fence = StatusReplacementFence()
    fences[key] = fence
    try:
        yield fence
    finally:
        if owner_pid == os.getpid():
            del fences[key]
