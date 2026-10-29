"""Shared signalling for a process group created by the calling runner.

The caller owns child creation, deadlines and joining. This helper never scans
host processes or widens its target beyond that child's dedicated process group.
"""

from __future__ import annotations

import math
import os
import time
import signal
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from pathlib import Path
from typing import Literal, TypeVar, overload

__all__ = ["bounded_run", "budget_active", "process_budget", "process_deadline", "signal_owned_process_tree"]
_deadline: ContextVar[float | None] = ContextVar("owned_process_deadline", default=None)
_cleanup_deadline: ContextVar[float | None] = ContextVar("owned_process_cleanup_deadline", default=None)
_Output = TypeVar("_Output", str, bytes)


def _run_windows_taskkill(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def signal_owned_process_tree(
    process: subprocess.Popen[_Output],
    *,
    force: bool,
    platform: str | None = None,
    windows_tree_kill: Callable[[Sequence[str]], subprocess.CompletedProcess[str]] = (_run_windows_taskkill),
) -> None:
    """Signal only the process group created for this runner-owned child."""
    if process.returncode is not None:
        return
    platform = platform or os.name
    if platform == "nt":
        command = ["taskkill", "/PID", str(process.pid), "/T"]
        if force:
            command.append("/F")
        result = windows_tree_kill(command)
        if result.returncode != 0 and process.poll() is None:
            # The tree-aware authority can race a naturally exiting child. If
            # it genuinely fails while the parent is still alive, ensure at
            # least that direct child receives the requested signal; the
            # non-zero taskkill diagnostic remains captured by the caller's
            # process output rather than widening to unrelated host PIDs.
            (process.kill if force else process.terminate)()
        return
    try:
        os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
    except (OSError, ProcessLookupError):
        (process.kill if force else process.terminate)()


@contextmanager
def process_budget(seconds: float, *, cleanup_deadline: float | None = None) -> Iterator[None]:
    """Bound actual subprocess calls in this context; nested budgets only tighten."""
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Finite positive process budget required")
    if cleanup_deadline is not None and not math.isfinite(cleanup_deadline):
        raise ValueError("Finite absolute cleanup deadline required")
    deadline = time.monotonic() + seconds
    outer = _deadline.get()
    inherited_cleanup = _cleanup_deadline.get()
    if inherited_cleanup is not None:
        cleanup_deadline = min(inherited_cleanup, cleanup_deadline) if cleanup_deadline is not None else inherited_cleanup
    if cleanup_deadline is not None:
        deadline = min(deadline, cleanup_deadline)
    token = _deadline.set(min(deadline, outer) if outer is not None else deadline)
    cleanup_token = _cleanup_deadline.set(cleanup_deadline)
    try:
        yield
    finally:
        _cleanup_deadline.reset(cleanup_token)
        _deadline.reset(token)


def process_deadline() -> float | None:
    """Read the caller's absolute monotonic deadline without extending its budget."""
    return _deadline.get()


def budget_active() -> bool:
    return process_deadline() is not None


def _capture_deadline(limit: float, deadline: float | None, cleanup_deadline: float | None) -> float:
    execution = time.monotonic() + limit
    if deadline is not None:
        execution = min(execution, deadline)
    if cleanup_deadline is not None:
        # Reserve join time inside the original horizon, never a fresh wait.
        remaining = max(0.0, cleanup_deadline - time.monotonic())
        execution = min(execution, cleanup_deadline - min(0.5, remaining / 2))
    return execution


def _cleanup_allowance(deadline: float | None) -> float:
    return 0.5 if deadline is None else min(0.5, max(0.0, deadline - time.monotonic()))


@overload
def bounded_run(
    argv: Sequence[str],
    *,
    timeout: float | None = None,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    capture_output: bool = True,
    check: bool = False,
    text: Literal[False] = False,
    input: bytes | None = None,
    encoding: str | None = None,
    errors: str | None = None,
) -> subprocess.CompletedProcess[bytes]: ...


@overload
def bounded_run(
    argv: Sequence[str],
    *,
    text: Literal[True],
    input: str | None = None,
    encoding: str | None = None,
    errors: str | None = None,
    timeout: float | None = None,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    capture_output: bool = True,
    check: bool = False,
) -> subprocess.CompletedProcess[str]: ...


def bounded_run(
    argv: Sequence[str],
    *,
    timeout: float | None = None,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    capture_output: bool = True,
    check: bool = False,
    text: bool = False,
    input: str | bytes | None = None,
    encoding: str | None = None,
    errors: str | None = None,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    """Capture a finite noninteractive POSIX operation and join its owned child.

    This deliberately supports the capture/check/text subset used by Git/API
    authorities, not shell execution or arbitrary standard-stream plumbing.
    Timeout signals finish before reaping; reused process IDs are never targets.
    A descendant retaining a pipe cannot make the final drain unbounded.
    """
    if not text and (encoding is not None or errors is not None):
        raise ValueError("Encoding options require explicit text capture")
    if input is not None and not isinstance(input, str if text else bytes):
        raise TypeError("Process input must match explicit text or bytes capture")
    if os.name != "posix" or not capture_output:
        raise OSError("Owned bounded capture unsupported on this platform or mode")
    deadline = _deadline.get()
    remaining = deadline - time.monotonic() if deadline is not None else None
    limit = min(timeout, remaining) if timeout is not None and remaining is not None else timeout if timeout is not None else remaining
    if limit is None or not math.isfinite(limit):
        raise ValueError("Finite process timeout or active budget required")
    if limit <= 0:
        raise subprocess.TimeoutExpired(argv, max(limit, 0))
    cleanup_deadline = _cleanup_deadline.get()
    execution_deadline = _capture_deadline(limit, deadline, cleanup_deadline)
    if cleanup_deadline is not None and time.monotonic() >= execution_deadline:
        raise subprocess.TimeoutExpired(argv, 0)
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        encoding=encoding,
        errors=errors,
        start_new_session=True,
    )
    try:
        try:
            stdout, stderr = process.communicate(input=input, timeout=limit if cleanup_deadline is None else max(0.0, execution_deadline - time.monotonic()))
        except subprocess.TimeoutExpired as exc:
            # Do not poll/reap before signalling: an unreaped child reserves the
            # identifier even if it has already exited while a descendant holds IO.
            signal_owned_process_tree(process, force=True)
            try:
                process.communicate(timeout=_cleanup_allowance(cleanup_deadline))
            except subprocess.TimeoutExpired:
                _close_capture(process)
                try:
                    process.wait(timeout=_cleanup_allowance(cleanup_deadline))
                except subprocess.TimeoutExpired:
                    if cleanup_deadline is None:
                        raise
                    exc.add_note("Owned child join unconfirmed within original cleanup horizon")
            raise
        result = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
        if check:
            result.check_returncode()
        return result
    finally:
        original_failure = sys.exception()
        if process.returncode is None:
            with suppress(ProcessLookupError):
                signal_owned_process_tree(process, force=True)
            try:
                process.wait(timeout=_cleanup_allowance(cleanup_deadline))
            except subprocess.TimeoutExpired as exc:
                if original_failure is None or cleanup_deadline is None:
                    raise
                original_failure.add_note(f"Owned child join unconfirmed: {exc}")
            finally:
                _close_capture(process)
        else:
            _close_capture(process)


def _close_capture(process: subprocess.Popen[str] | subprocess.Popen[bytes]) -> None:
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            with suppress(OSError):
                stream.close()
