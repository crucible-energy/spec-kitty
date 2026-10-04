"""Real-fork regressions: a child must not borrow its parent's status lock."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from tests.integration.test_restore_owned_mission_history import (
    MID,
    SLUG,
    Checkouts,
    checkouts as checkouts,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.skipif(not hasattr(os, "fork"), reason="Requires real POSIX fork")]


def _run_fork_script(checkouts: Checkouts, body: str, *, pre_import: str = "") -> dict:
    # Only the harness starts a fresh interpreter. The tested child is an actual
    # os.fork() of a process holding the candidate's real canonical FileLock.
    script = f"""
import os, sys, json, select, signal
from pathlib import Path
sys.path = {sys.path!r}
from filelock import FileLock, Timeout
{pre_import}
from specify_cli.status import locking, lifecycle_events
from specify_cli.migration import owned_history, owned_history_io
ROOT = Path({str(checkouts.owned)!r})
PRIMARY = Path({str(checkouts.primary)!r})
DIRECTORY = Path({str(checkouts.directory)!r})
SLUG = {SLUG!r}
MID = {MID!r}
PINS = {[checkouts.target, checkouts.source]!r}
KEY = locking.feature_status_lock_path(ROOT, SLUG)
lifecycle_events._queue_lifecycle_event_if_enabled = lambda *args, **kwargs: None
def receive(fd):
    raw = b''
    while not raw.endswith(b'\\n'):
        if not select.select([fd], [], [], 10)[0]:
            raise RuntimeError('fork pipe barrier timed out')
        chunk = os.read(fd, 4096)
        if not chunk:
            raise RuntimeError('fork pipe closed before result')
        raw += chunk
    return json.loads(raw)
def send(fd, value):
    os.write(fd, (json.dumps(value) + '\\n').encode())
def native_blocked():
    probe = FileLock(str(KEY), timeout=0)
    try:
        probe.acquire()
    except Timeout:
        return True
    else:
        probe.release()
        return False
def append_live():
    return lifecycle_events.append_lifecycle_event(
        DIRECTORY / 'status.events.jsonl', 'PlanStarted',
        {{'mission_slug': SLUG, 'actor': 'fork child'}}, aggregate_id=MID, aggregate_type='Mission')
{body}
"""
    try:
        process = subprocess.run([sys.executable, "-u", "-B", "-c", script], capture_output=True, text=True, timeout=35)
    except subprocess.TimeoutExpired:
        pytest.fail("Causal real-fork subprocess timed out; possible fork/transition deadlock", pytrace=False)
    assert process.returncode == 0, process.stderr
    return json.loads(process.stdout)


def test_fork_does_not_deadlock_an_admitted_native_acquisition(checkouts: Checkouts):
    result = _run_fork_script(
        checkouts,
        """
original_acquire = FileLock.acquire
def acquire(lock, *args, **kwargs):
    if current_thread().name == 'canonical-acquirer':
        native = lock._acquire
        def paused_native():
            entered.set()
            assert resume.wait(10)
            return native()
        lock._acquire = paused_native
    return original_acquire(lock, *args, **kwargs)
FileLock.acquire = acquire
errors = []
def holder():
    try:
        with locking.feature_status_lock(ROOT, SLUG, timeout=10):
            pass
    except BaseException as exc:
        errors.append(str(exc))
worker = Thread(target=holder, name='canonical-acquirer', daemon=True)
worker.start()
assert entered.wait(10)
# The intermediate before-hook below resumes the already-admitted transition.
# On the rejected code, our later-registered before-hook has locked _fork_guard
# first; upstream's earlier hook then waits for the transition needing that guard.
child = os.fork()
if child == 0:
    os._exit(0)
_, status = os.waitpid(child, 0)
worker.join(10)
assert status == 0 and not worker.is_alive() and not errors, errors
print(json.dumps({'completed': True, 'active': len(locking._active_locks)}))
""",
        pre_import="""
from threading import Thread, Event, current_thread
entered, resume = Event(), Event()
def resume_admitted_transition():
    resume.set()
# Registration order is essential: upstream -> causal barrier -> our module.
# POSIX before callbacks run in reverse order.
os.register_at_fork(before=resume_admitted_transition)
""",
    )
    assert result == {"completed": True, "active": 0}


def test_fork_during_staging_cannot_erase_successful_child_append(checkouts: Checkouts):
    result = _run_fork_script(
        checkouts,
        """
go_read, go_write = os.pipe()
result_read, result_write = os.pipe()
child = None
reply = None
original_stage = owned_history_io.BoundHistoryDirectory.stage
original_replace = owned_history_io.BoundHistoryDirectory.replace
def stage(bound, raw, mode):
    global child
    if child is None:
        # Parent holds the shared lock; replacement fence has NOT been created.
        child = os.fork()
        if child == 0:
            os.close(go_write)
            os.close(result_read)
            receive(go_read)
            try:
                row = append_live()
                send(result_write, {'kind': 'appended', 'row': row})
            except RuntimeError as exc:
                send(result_write, {'kind': 'refused', 'error': str(exc)})
            os._exit(0)
        os.close(go_read)
        os.close(result_write)
    return original_stage(bound, raw, mode)
def replace(bound, source, destination):
    global reply
    if destination == 'status.events.jsonl' and reply is None:
        # Release the already-forked child at the precise overwrite window.
        send(go_write, {'go': True})
        reply = receive(result_read)
    return original_replace(bound, source, destination)
owned_history_io.BoundHistoryDirectory.stage = stage
owned_history_io.BoundHistoryDirectory.replace = replace
try:
    report = owned_history.restore_owned_mission_history(PRIMARY, ROOT, SLUG, PINS, apply=True)
    assert child is not None
    _, status = os.waitpid(child, 0)
    assert status == 0
    rows = [json.loads(line) for line in (DIRECTORY / 'status.events.jsonl').read_text().splitlines()]
    print(json.dumps({'report': report['applied'], 'reply': reply,
                      'retained': reply['row'] in rows if reply['kind'] == 'appended' else None}))
finally:
    for fd in (go_write, result_read):
        os.close(fd)
""",
    )
    assert result["report"] is True
    assert result["reply"]["kind"] == "refused" or result["retained"] is True, "parent overwrite lost a successful inherited-lock append"
    if result["reply"]["kind"] == "refused":
        assert "fork child" in result["reply"]["error"]


@pytest.mark.parametrize("unwind", [False, True])
def test_fork_child_never_unlocks_parent_when_inherited_context_exits(checkouts: Checkouts, unwind: bool):
    result = _run_fork_script(
        checkouts,
        f"""
result_read, result_write = os.pipe()
child = None
try:
    with locking.feature_status_lock(ROOT, SLUG, timeout=1):
        child = os.fork()
        if child == 0:
            os.close(result_read)
            try:
                append_live()
                reply = {{'kind': 'appended'}}
            except RuntimeError as exc:
                reply = {{'kind': 'refused', 'error': str(exc)}}
            if {unwind!r}:
                raise ValueError('child-only unwind')
        else:
            os.close(result_write)
            reply = receive(result_read)
            blocked = native_blocked()
            _, status = os.waitpid(child, 0)
            assert status == 0
except ValueError:
    if child != 0:
        raise
if child == 0:
    # Both normal and exceptional exits have run inherited finally blocks.
    send(result_write, reply)
    os._exit(0)
print(json.dumps({{'reply': reply, 'parent_still_locked': blocked}}))
""",
    )
    assert result["parent_still_locked"] is True, "child cleanup released/unlinked the parent's native lock"
    assert result["reply"]["kind"] == "refused"


def test_inherited_fence_and_native_fd_are_detached_without_parent_reset(checkouts: Checkouts):
    result = _run_fork_script(
        checkouts,
        """
import errno
result_read, result_write = os.pipe()
with locking.feature_status_lock(ROOT, SLUG, timeout=1):
    held = locking._get_thread_locks()
    lock = held[str(KEY)][0]
    descriptor = lock._context.lock_file_fd
    with locking.status_replacement_fence(ROOT, SLUG) as fence:
        # Calling the hook in the parent is deliberately a no-op.
        locking._discard_inherited_state()
        assert locking._get_thread_locks() is held
        assert lock._context.lock_file_fd == descriptor
        assert locking._replacement_fences()[str(KEY)] is fence
        child = os.fork()
        if child == 0:
            os.close(result_read)
            try:
                os.fstat(descriptor)
                closed = False
            except OSError as exc:
                closed = exc.errno == errno.EBADF
            try:
                fence.check()
                fence_refused = False
            except locking.StatusLockForkRefused:
                fence_refused = True
            # Public release must not unlock/unlink an inherited parent lock.
            lock.release(force=True)
            send(result_write, {'closed': closed, 'fence_refused': fence_refused})
            os._exit(0)
        os.close(result_write)
        reply = receive(result_read)
        blocked = native_blocked()
        _, status = os.waitpid(child, 0)
        assert status == 0
        assert lock._context.lock_file_fd == descriptor
print(json.dumps({'reply': reply, 'parent_still_locked': blocked}))
""",
    )
    assert result["reply"] == {"closed": True, "fence_refused": True}
    assert result["parent_still_locked"] is True


def test_fork_closes_status_descriptor_owned_by_another_parent_thread(checkouts: Checkouts):
    result = _run_fork_script(
        checkouts,
        """
from threading import Thread, Event
import errno
ready, release = Event(), Event()
descriptors = []
def holder():
    with locking.feature_status_lock(ROOT, SLUG, timeout=1):
        descriptors.append(locking._get_thread_locks()[str(KEY)][0]._context.lock_file_fd)
        ready.set()
        release.wait(15)
worker = Thread(target=holder)
worker.start()
assert ready.wait(10)
result_read, result_write = os.pipe()
try:
    child = os.fork()  # Forking thread has NO thread-local held lock entry.
    if child == 0:
        os.close(result_read)
        try:
            os.fstat(descriptors[0])
            closed = False
        except OSError as exc:
            closed = exc.errno == errno.EBADF
        try:
            append_live()
            refused = False
        except locking.StatusLockForkRefused:
            refused = True
        send(result_write, {'closed': closed, 'refused': refused})
        os._exit(0)
    os.close(result_write)
    reply = receive(result_read)
    blocked = native_blocked()
    _, status = os.waitpid(child, 0)
    assert status == 0
finally:
    release.set()
    worker.join(10)
assert not worker.is_alive()
print(json.dumps({'reply': reply, 'parent_still_locked': blocked}))
""",
    )
    assert result["reply"] == {"closed": True, "refused": True}
    assert result["parent_still_locked"] is True


def test_fork_without_active_status_context_can_acquire_own_native_lock(checkouts: Checkouts):
    result = _run_fork_script(
        checkouts,
        """
result_read, result_write = os.pipe()
child = os.fork()
if child == 0:
    os.close(result_read)
    row = append_live()
    send(result_write, {'row': row})
    os._exit(0)
os.close(result_write)
reply = receive(result_read)
_, status = os.waitpid(child, 0)
assert status == 0
rows = [json.loads(line) for line in (DIRECTORY / 'status.events.jsonl').read_text().splitlines()]
print(json.dumps({'retained': reply['row'] in rows}))
""",
    )
    assert result["retained"] is True


def test_parent_nested_exception_cleanup_keeps_depth_and_releases_owned_fd(checkouts: Checkouts):
    result = _run_fork_script(
        checkouts,
        """
import errno
try:
    with locking.feature_status_lock(ROOT, SLUG, timeout=1):
        lock = locking._get_thread_locks()[str(KEY)][0]
        descriptor = lock._context.lock_file_fd
        try:
            with locking.feature_status_lock(ROOT, SLUG, timeout=1):
                assert locking._get_thread_locks()[str(KEY)][1] == 2
                raise ValueError('nested cleanup')
        except ValueError:
            pass
        assert locking._get_thread_locks()[str(KEY)][1] == 1
        raise ValueError('outer cleanup')
except ValueError:
    pass
try:
    os.fstat(descriptor)
    closed = False
except OSError as exc:
    closed = exc.errno == errno.EBADF
print(json.dumps({'closed': closed, 'held': len(locking._get_thread_locks()),
                  'active': len(locking._active_locks), 'blocked': native_blocked()}))
""",
    )
    assert result == {"closed": True, "held": 0, "active": 0, "blocked": False}


def test_fork_inside_native_attempt_detaches_before_canonical_yield(checkouts: Checkouts):
    result = _run_fork_script(
        checkouts,
        """
import errno
result_read, result_write = os.pipe()
original_acquire = locking.FileLock._acquire
child = None
descriptor = None
upstream_refusal = None
def acquire(lock):
    global child, descriptor, upstream_refusal
    original_acquire(lock)
    descriptor = lock._context.lock_file_fd
    if child is None and upstream_refusal is None:
        try:
            child = os.fork()
        except RuntimeError as exc:
            # Modern filelock safely refuses fork inside its ownership change.
            # Do not mask an unrelated RuntimeError or remove the causal attempt.
            if 'fork' not in str(exc) or 'ownership' not in str(exc):
                raise
            upstream_refusal = str(exc)
locking.FileLock._acquire = acquire
try:
    with locking.feature_status_lock(ROOT, SLUG, timeout=1):
        assert child != 0, 'child crossed canonical yield with inherited acquisition'
        if upstream_refusal is not None:
            assert child is None
            reply = {'upstream_refused': True, 'error': upstream_refusal}
            blocked = native_blocked()
        else:
            os.close(result_write)
            reply = receive(result_read)
            blocked = native_blocked()
            _, status = os.waitpid(child, 0)
            assert status == 0
except locking.StatusLockForkRefused as exc:
    assert child == 0
    os.close(result_read)
    try:
        os.fstat(descriptor)
        closed = False
    except OSError as error:
        closed = error.errno == errno.EBADF
    send(result_write, {'closed': closed, 'refused': True})
    os._exit(0)
print(json.dumps({'reply': reply, 'parent_still_locked': blocked, 'active': len(locking._active_locks)}))
""",
    )
    assert result["parent_still_locked"] is True
    assert result["active"] == 0
    if result["reply"].get("upstream_refused"):
        assert "fork" in result["reply"]["error"] and "ownership" in result["reply"]["error"]
    else:
        assert result["reply"] == {"closed": True, "refused": True}


def test_native_backend_downgrade_refuses_and_cleans_pending_ownership(checkouts: Checkouts):
    result = _run_fork_script(
        checkouts,
        """
def unsupported(lock):
    if locking._UPSTREAM_FORK_PROTOCOL:
        raise RuntimeError('upstream native acquisition refused')
    lock._fallback_to_soft_lock()
locking.FileLock._acquire = unsupported
try:
    with locking.feature_status_lock(ROOT, SLUG, timeout=1):
        raise AssertionError('unsupported native backend was accepted')
except RuntimeError as exc:
    error = str(exc)
print(json.dumps({'error': error, 'active': len(locking._active_locks), 'held': len(locking._get_thread_locks())}))
""",
    )
    assert "soft-lock fallback is unsupported" in result["error"] or result["error"] == "upstream native acquisition refused"
    assert result["active"] == result["held"] == 0
