"""Durable hints survive exit without granting creator authority."""

from pathlib import Path

import pytest

from specify_cli.workspace_lifecycle.state import StateError, StateStore


def ledger(tmp_path: Path) -> StateStore:
    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    return StateStore.initialize(root)


def test_callback_coalesces_and_does_not_wait_for_full_ledger_transaction(tmp_path: Path) -> None:
    from specify_cli.workspace_lifecycle.events import EventQueue

    store = ledger(tmp_path)
    queue = EventQueue(store)
    with store.locked():
        assert queue.notify("completion") == 1
        assert queue.notify("startup") == 2
    assert queue.snapshot() == (2, 0)
    queue.acknowledge(1)
    assert queue.snapshot() == (2, 1)
    queue.acknowledge(2)
    assert queue.snapshot() == (2, 2)


def test_no_history_never_initializes_or_enqueues(tmp_path: Path) -> None:
    from specify_cli.workspace_lifecycle.events import EventQueue

    root = tmp_path / "empty"
    root.mkdir(mode=0o700)
    with pytest.raises(StateError):
        EventQueue(StateStore(root)).notify("startup")
    assert list(root.iterdir()) == []


def test_queue_refuses_untrusted_or_replayed_acknowledgment(tmp_path: Path) -> None:
    from specify_cli.workspace_lifecycle.events import EventQueue

    queue = EventQueue(ledger(tmp_path))
    queue.notify("startup")
    with pytest.raises(StateError):
        queue.acknowledge(2)
    queue.acknowledge(1)
    queue.notify("completion")
    queue.acknowledge(0)
    assert queue.snapshot() == (2, 1)
    path = queue.store.root / "events.json"
    path.write_text('{"generation":2,"generation":9,"acknowledged":1,"schema_version":1}')
    with pytest.raises(StateError):
        queue.snapshot()


def test_observation_is_non_authoritative_and_never_creates_lock(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    lock = store.root / "lifecycle.lock"
    lock.unlink()
    assert store.observe().revision == 0
    assert not lock.exists()
    with store.locked():
        assert store.observe().revision == 0
