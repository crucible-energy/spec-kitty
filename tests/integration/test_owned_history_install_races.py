"""Post-validation P1 reproductions for owned recovery (independent review #60)."""

from __future__ import annotations

import json
import os
import tempfile
import subprocess
import sys
from threading import Event, Thread, current_thread
from pathlib import Path

import pytest

from tests.integration.test_restore_owned_mission_history import (
    MANIFEST,
    MID,
    SLUG,
    Checkouts,
    checkouts as checkouts,  # Re-export the shared pytest fixture.
    history,
    tree,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _append_live(directory: Path) -> dict:
    from specify_cli.status.lifecycle_events import append_lifecycle_event

    result = append_lifecycle_event(
        directory / "status.events.jsonl",
        "PlanStarted",
        {"mission_slug": SLUG, "actor": "live writer", "at": "2026-10-03T12:00:00Z"},
        aggregate_id=MID,
        aggregate_type="Mission",
    )
    assert result is not None, "real supported lifecycle append must succeed"
    return result


def _silence_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.status import lifecycle_events

    monkeypatch.setattr(lifecycle_events, "_queue_lifecycle_event_if_enabled", lambda *args, **kwargs: None)


@pytest.mark.skipif(os.name != "posix", reason="Descriptor-bound install requires POSIX no-follow IO")
def test_dossier_swap_after_locked_plan_never_writes_dirty_primary(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch):
    protected = checkouts.primary / "kitty-specs" / SLUG
    protected.mkdir(parents=True)
    for name in ("status.events.jsonl", "status.json", MANIFEST):
        (protected / name).write_text(f"protected primary user bytes: {name}\n")
    before = tree(checkouts.primary)
    original_stage = tempfile.mkstemp
    original_open = os.open
    attacked = False

    def swap():
        nonlocal attacked
        if not attacked:
            attacked = True
            checkouts.directory.rename(checkouts.directory.with_name(SLUG + ".retained"))
            checkouts.directory.symlink_to(protected, target_is_directory=True)

    def stage(*args, **kwargs):
        swap()  # Exact rejected-head reproducer, after the locked _plan.
        return original_stage(*args, **kwargs)

    def open_stage(path, flags, *args, **kwargs):
        if ".history-" in str(path) and flags & os.O_CREAT:
            swap()  # Also exercise the corrected fd-relative staging seam.
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(tempfile, "mkstemp", stage)
    monkeypatch.setattr(os, "open", open_stage)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, open_stage})
    result = checkouts.invoke("--apply")
    assert attacked
    assert tree(checkouts.primary) == before, "recovery followed the swapped dossier into protected primary"
    assert result.exit_code == 1, result.output


@pytest.mark.skipif(os.name != "posix", reason="Descriptor-bound install requires POSIX no-follow IO")
def test_real_lifecycle_append_during_first_stage_is_not_lost(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch):
    _silence_transport(monkeypatch)
    original_stage = tempfile.mkstemp
    original_open = os.open
    appended: list[dict] = []

    def append_once():
        if not appended:
            appended.append(_append_live(checkouts.directory))

    def stage(*args, **kwargs):
        append_once()
        return original_stage(*args, **kwargs)

    def open_stage(path, flags, *args, **kwargs):
        if ".history-" in str(path) and flags & os.O_CREAT:
            append_once()
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(tempfile, "mkstemp", stage)
    monkeypatch.setattr(os, "open", open_stage)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, open_stage})
    result = checkouts.invoke("--apply")
    assert appended
    rows = [json.loads(line) for line in (checkouts.directory / "status.events.jsonl").read_text().splitlines()]
    assert appended[0] in rows, "restoration erased a successfully persisted supported lifecycle event"
    assert result.exit_code == 1, result.output


def _during_first_stage(monkeypatch: pytest.MonkeyPatch, action) -> None:
    original_open = os.open
    called = False

    def intercept(path, flags, *args, **kwargs):
        nonlocal called
        if not called and ".history-" in str(path) and flags & os.O_CREAT:
            called = True
            action()
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", intercept)
    # The wrapper forwards dir_fd unchanged, so it has the original capability.
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, intercept})


@pytest.mark.skipif(os.name != "posix", reason="Descriptor-bound install requires POSIX no-follow IO")
@pytest.mark.parametrize("fail_install", [False, True])
def test_concurrent_supported_append_waits_and_survives_apply(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch, fail_install: bool):
    from specify_cli.status import locking

    _silence_transport(monkeypatch)
    attempted, finished = Event(), Event()
    appended: list[dict] = []
    errors: list[BaseException] = []
    shared_key = locking.feature_status_lock_path(checkouts.primary, SLUG)
    original_acquire = locking.FileLock.acquire
    original_replace = os.replace
    original_snapshot = (checkouts.directory / "status.json").read_bytes()
    replace_calls = 0

    def replace(source, destination, **kwargs):
        nonlocal replace_calls
        replace_calls += 1
        if fail_install and replace_calls == 2:
            raise OSError("concurrent writer waits through failed install and rollback")
        original_replace(source, destination, **kwargs)

    def acquire(lock, *args, **kwargs):
        if current_thread().name == "owned-history-live-writer" and Path(lock.lock_file) == shared_key:
            attempted.set()
        return original_acquire(lock, *args, **kwargs)

    def append():
        try:
            appended.append(_append_live(checkouts.directory))
        except BaseException as exc:
            errors.append(exc)
        finally:
            finished.set()

    writer = Thread(target=append, name="owned-history-live-writer", daemon=True)

    def start_live_writer():
        writer.start()
        assert attempted.wait(5), "supported appender did not acquire the canonical shared key"
        assert not finished.is_set(), "supported appender escaped the held recovery lock"

    monkeypatch.setattr(locking.FileLock, "acquire", acquire)
    monkeypatch.setattr(os, "replace", replace)
    _during_first_stage(monkeypatch, start_live_writer)
    result = checkouts.invoke("--apply")
    writer.join(5)
    assert finished.is_set() and not errors, errors
    assert result.exit_code == (1 if fail_install else 0), result.output
    rows = [json.loads(line) for line in (checkouts.directory / "status.events.jsonl").read_text().splitlines()]
    assert appended[0] in rows
    if fail_install:
        assert (checkouts.directory / "status.json").read_bytes() == original_snapshot
        assert not (checkouts.directory / MANIFEST).exists()
    else:
        assert json.loads((checkouts.directory / "status.json").read_text())["work_packages"]["WP01"]["lane"] == "approved"


def test_read_only_plan_preserves_a_real_append_and_refuses_stale_inputs(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.migration import owned_history

    _silence_transport(monkeypatch)
    original = owned_history._protect_outputs
    appended: list[dict] = []
    old_snapshot = (checkouts.directory / "status.json").read_bytes()

    def append_while_reading(ownership, outputs):
        if not appended:
            appended.append(_append_live(checkouts.directory))
        original(ownership, outputs)

    monkeypatch.setattr(owned_history, "_protect_outputs", append_while_reading)
    result = checkouts.invoke("--dry-run")
    assert result.exit_code == 1, result.output
    rows = [json.loads(line) for line in (checkouts.directory / "status.events.jsonl").read_text().splitlines()]
    assert appended[0] in rows
    assert (checkouts.directory / "status.json").read_bytes() == old_snapshot
    assert not (checkouts.directory / MANIFEST).exists()


@pytest.mark.skipif(os.name != "posix", reason="Descriptor-bound install requires POSIX no-follow IO")
def test_separate_process_appender_uses_shared_git_lock_and_survives(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.status.locking import feature_status_lock_path

    shared_key = feature_status_lock_path(checkouts.primary, SLUG)
    child: subprocess.Popen[str] | None = None
    # The child uses the candidate's real public appender and native FileLock;
    # its acquisition notification is the causal barrier, not a sleep budget.
    script = f"""
import sys, json
sys.path = {sys.path!r}
from pathlib import Path
from specify_cli.status import lifecycle_events, locking
original_acquire = locking.FileLock.acquire
def acquire(lock, *args, **kwargs):
    print('LOCK:' + lock.lock_file, flush=True)
    return original_acquire(lock, *args, **kwargs)
locking.FileLock.acquire = acquire
lifecycle_events._queue_lifecycle_event_if_enabled = lambda *args, **kwargs: None
row = lifecycle_events.append_lifecycle_event(
    Path({str(checkouts.directory / "status.events.jsonl")!r}), 'PlanStarted',
    {{'mission_slug': {SLUG!r}, 'actor': 'separate process'}},
    aggregate_id={MID!r}, aggregate_type='Mission')
assert row is not None
print(json.dumps(row), flush=True)
"""

    def start_process():
        nonlocal child
        child = subprocess.Popen([sys.executable, "-u", "-B", "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "LOCK:" + str(shared_key)
        assert child.poll() is None

    _during_first_stage(monkeypatch, start_process)
    try:
        result = checkouts.invoke("--apply")
        assert child is not None
        stdout, stderr = child.communicate(timeout=15)
        assert child.returncode == 0, stderr
        assert result.exit_code == 0, result.output
        row = json.loads(stdout)
        records = [json.loads(line) for line in (checkouts.directory / "status.events.jsonl").read_text().splitlines()]
        assert row in records
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait(timeout=5)


@pytest.mark.parametrize("ancestor", ["dossier", "kitty-specs", "checkout"])
@pytest.mark.skipif(os.name != "posix", reason="Descriptor-bound install requires POSIX no-follow IO")
def test_namespace_swap_during_install_and_rollback_never_follows_primary(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch, ancestor: str):
    protected = checkouts.primary / "protected-history"
    protected.mkdir()
    for name in ("status.events.jsonl", "status.json", MANIFEST):
        (protected / name).write_text(f"protected {name}\n")
    before_primary = tree(checkouts.primary)
    original_replace = os.replace
    swapped = False
    original_directory = checkouts.directory
    moved = {"dossier": checkouts.directory, "kitty-specs": checkouts.directory.parent, "checkout": checkouts.owned}[ancestor]
    retained = moved.with_name(moved.name + ".retained")

    def replace(source, destination, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            moved.rename(retained)
            moved.symlink_to(protected, target_is_directory=True)
        original_replace(source, destination, **kwargs)

    original_bytes = {name: (original_directory / name).read_bytes() for name in ("status.events.jsonl", "status.json")}
    monkeypatch.setattr(os, "replace", replace)
    result = checkouts.invoke("--apply")
    assert swapped
    assert tree(checkouts.primary) == before_primary
    assert result.exit_code == 1, result.output
    retained_directory = retained / original_directory.relative_to(moved)
    assert all((retained_directory / name).read_bytes() == raw for name, raw in original_bytes.items())
    assert not (retained_directory / MANIFEST).exists()


@pytest.mark.skipif(os.name != "posix", reason="Descriptor-bound install requires POSIX no-follow IO")
def test_supported_reentrant_writer_during_rename_refuses_instead_of_deadlocking(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch):
    _silence_transport(monkeypatch)
    original_replace = os.replace
    tried = False

    def replace(source, destination, **kwargs):
        nonlocal tried
        if not tried:
            tried = True
            _append_live(checkouts.directory)
        original_replace(source, destination, **kwargs)

    monkeypatch.setattr(os, "replace", replace)
    before = tree(checkouts.owned)
    result = checkouts.invoke("--apply")
    assert tried
    assert result.exit_code == 1, result.output
    assert "reentrant" in json.loads(result.stdout)["error"]
    assert tree(checkouts.owned) == before


@pytest.mark.skipif(os.name != "posix", reason="Descriptor-bound install requires POSIX no-follow IO")
@pytest.mark.parametrize("edit", ["bytes", "mode"])
def test_rollback_preserves_a_later_destination_edit(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch, edit: str):
    original_replace = os.replace
    calls = 0
    latest = b"concurrent user snapshot bytes\n"

    def replace(source, destination, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            if edit == "bytes":
                (checkouts.directory / "status.json").write_bytes(latest)
            else:
                (checkouts.directory / "status.json").chmod(0o600)
            raise OSError("injected failure after external snapshot edit")
        original_replace(source, destination, **kwargs)

    original_log = (checkouts.directory / "status.events.jsonl").read_bytes()
    monkeypatch.setattr(os, "replace", replace)
    result = checkouts.invoke("--apply")
    assert result.exit_code == 1, result.output
    assert "preserved concurrent changes" in json.loads(result.stdout)["error"]
    if edit == "bytes":
        assert (checkouts.directory / "status.json").read_bytes() == latest
    else:
        assert (checkouts.directory / "status.json").stat().st_mode & 0o777 == 0o600
    assert (checkouts.directory / "status.events.jsonl").read_bytes() == original_log


def test_unsupported_fd_platform_refuses_apply_before_staging(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.migration import owned_history_io

    monkeypatch.setattr(owned_history_io, "_supported", lambda: False)
    before = tree(checkouts.owned)
    result = checkouts.invoke("--apply")
    assert result.exit_code == 1
    assert "unsupported platform" in json.loads(result.stdout)["error"]
    assert tree(checkouts.owned) == before


def _write_family(directory: Path, family: str) -> None:
    from specify_cli.status import store
    from specify_cli.status.models import InnerStateChanged, StatusEvent

    event = StatusEvent.from_dict(history()[0])
    annotation = InnerStateChanged.from_dict(history()[-1])
    if family == "lifecycle":
        _append_live(directory)
    elif family == "single":
        store.append_event_verified(directory, event)
    elif family == "batch":
        store.append_events_atomic_verified(directory, [event])
    elif family == "annotation":
        store.append_annotations_atomic_verified(directory, [annotation])
    elif family == "mixed":
        store.append_event_stream_atomic_verified(directory, [event, annotation])
    elif family == "snapshot":
        from specify_cli.status.reducer import materialize

        materialize(directory)
    elif family == "decision":
        from specify_cli.decisions.emit import _append_raw_event

        _append_raw_event(directory / "status.events.jsonl", {"event_type": "DecisionPointOpened", "payload": {"decision_point_id": MID}})
    elif family == "retro-lifecycle":
        from specify_cli.retrospective.lifecycle_events import _append_retro_lifecycle_event

        _append_retro_lifecycle_event(directory, {"type": "RetrospectiveSkipped", "event_id": MID})
    else:
        from specify_cli.retrospective.events import StartedPayload, emit_retrospective_event
        from specify_cli.retrospective.schema import ActorRef

        emit_retrospective_event(
            feature_dir=directory,
            mission_slug=SLUG,
            mission_id=MID,
            mid8=MID[:8],
            actor=ActorRef(kind="runtime", id="test-runtime"),
            event_name="retrospective.started",
            payload=StartedPayload(facilitator_profile_id="retrospective-facilitator", action_id="retrospect"),
        )


@pytest.mark.parametrize("family", ["lifecycle", "single", "batch", "annotation", "mixed", "snapshot", "decision", "retro-lifecycle", "retrospective"])
def test_supported_writer_families_use_same_key_and_remain_normally_reentrant(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch, family: str):
    from specify_cli.status import locking

    _silence_transport(monkeypatch)
    key = locking.feature_status_lock_path(checkouts.primary, SLUG)
    observed: list[Path] = []
    original_lock = locking.feature_status_lock

    def same_lock(root, slug, **kwargs):
        observed.append(locking.feature_status_lock_path(root, slug))
        return original_lock(root, slug, **kwargs)

    with original_lock(checkouts.owned, SLUG, timeout=1):
        monkeypatch.setattr(locking, "feature_status_lock", same_lock)
        _write_family(checkouts.directory, family)
    assert observed and all(path == key for path in observed)


@pytest.mark.parametrize("family", ["lifecycle", "single", "batch", "annotation", "mixed", "snapshot", "decision", "retro-lifecycle", "retrospective"])
def test_supported_writer_families_refuse_inside_install_fence(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch, family: str):
    from specify_cli.status import locking

    _silence_transport(monkeypatch)
    before = tree(checkouts.directory)
    with locking.feature_status_lock(checkouts.owned, SLUG, timeout=1), locking.status_replacement_fence(checkouts.owned, SLUG) as fence:
        # Verified store wrappers may translate the conflict to a persistence
        # error; every family must still fail before writing and latch it.
        with pytest.raises(Exception, match="reentrant"):
            _write_family(checkouts.directory, family)
        with pytest.raises(locking.StatusReplacementConflict):
            fence.check()
    assert tree(checkouts.directory) == before


def test_first_append_lock_key_is_stable_before_and_after_directory_creation(checkouts: Checkouts):
    from specify_cli.status.locking import feature_status_lock_path
    from specify_cli.status.models import StatusEvent
    from specify_cli.status.store import append_event

    missing = checkouts.owned / "new-ad-hoc-parent" / SLUG
    assert not missing.exists()
    before_key = feature_status_lock_path(missing, SLUG)
    append_event(missing, StatusEvent.from_dict(history()[0]))
    assert before_key == feature_status_lock_path(missing, SLUG)
    assert before_key == feature_status_lock_path(checkouts.primary, SLUG)


@pytest.mark.parametrize("failure", [1, 2, 3])
@pytest.mark.skipif(os.name != "posix", reason="Descriptor-bound install requires POSIX no-follow IO")
def test_fd_bound_replace_failures_restore_exact_originals(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch, failure: int):
    original_replace = os.replace
    calls = 0

    def fail_once(source, destination, **kwargs):
        nonlocal calls
        calls += 1
        if calls == failure:
            raise OSError(f"injected replacement {failure}")
        original_replace(source, destination, **kwargs)

    monkeypatch.setattr(os, "replace", fail_once)
    before = tree(checkouts.owned)
    result = checkouts.invoke("--apply")
    assert calls >= failure
    assert result.exit_code == 1, result.output
    assert tree(checkouts.owned) == before
