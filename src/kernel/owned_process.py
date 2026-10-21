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
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from pathlib import Path
from typing import Literal, TypeVar, overload

__all__ = ["bounded_run", "budget_active", "process_budget", "signal_owned_process_tree"]
_deadline: ContextVar[float | None] = ContextVar("owned_process_deadline", default=None)
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
def process_budget(seconds: float) -> Iterator[None]:
    """Bound actual subprocess calls in this context; nested budgets only tighten."""
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Finite positive process budget required")
    deadline = time.monotonic() + seconds
    outer = _deadline.get()
    token = _deadline.set(min(deadline, outer) if outer is not None else deadline)
    try:
        yield
    finally:
        _deadline.reset(token)


def budget_active() -> bool:
    return _deadline.get() is not None


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
    encoding: str | None = None,
    errors: str | None = None,
) -> subprocess.CompletedProcess[bytes]: ...


@overload
def bounded_run(
    argv: Sequence[str],
    *,
    text: Literal[True],
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
    if os.name != "posix" or not capture_output:
        raise OSError("Owned bounded capture unsupported on this platform or mode")
    deadline = _deadline.get()
    remaining = deadline - time.monotonic() if deadline is not None else None
    limit = min(timeout, remaining) if timeout is not None and remaining is not None else timeout if timeout is not None else remaining
    if limit is None or not math.isfinite(limit):
        raise ValueError("Finite process timeout or active budget required")
    if limit <= 0:
        raise subprocess.TimeoutExpired(argv, max(limit, 0))
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        encoding=encoding,
        errors=errors,
        start_new_session=True,
    )
    try:
        try:
            stdout, stderr = process.communicate(timeout=limit)
        except subprocess.TimeoutExpired:
            # Do not poll/reap before signalling: an unreaped child reserves the
            # identifier even if it has already exited while a descendant holds IO.
            signal_owned_process_tree(process, force=True)
            try:
                process.communicate(timeout=0.5)
            except subprocess.TimeoutExpired:
                _close_capture(process)
                process.wait(timeout=0.5)
            raise
        result = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
        if check:
            result.check_returncode()
        return result
    finally:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                signal_owned_process_tree(process, force=True)
            try:
                process.wait(timeout=0.5)
            finally:
                _close_capture(process)
        else:
            _close_capture(process)


def _close_capture(process: subprocess.Popen[str] | subprocess.Popen[bytes]) -> None:
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            with suppress(OSError):
                stream.close()
