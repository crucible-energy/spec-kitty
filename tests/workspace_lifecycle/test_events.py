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


@pytest.mark.parametrize("blocked", [False, True])
def test_fresh_worker_process_resumes_released_owner_and_retains_unmerged_pr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blocked: bool) -> None:
    import json
    import os
    import subprocess
    import sys

    from test_adapters import managed_owner
    from specify_cli.workspace_lifecycle.events import EventQueue

    owner, store, _, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    path = Path(owner.identity.path)
    queue = EventQueue(store)
    queue.notify("completion")
    if blocked:
        malformed = store.root / ("creator-" + "0" * 32 + ".json")
        malformed.write_text("{}")
        malformed.chmod(0o600)
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    metadata = tmp_path / "metadata.json"
    repository = {"id": 7, "full_name": "crucible-energy/example", "default_branch": "main"}
    pull = {
        "number": 9,
        "merged": False,
        "state": "closed",
        "merged_at": "2026-10-20",
        "merge_commit_sha": "b" * 40,
        "head": {"sha": owner.identity.head, "repo": repository},
        "base": {"ref": "main", "repo": repository},
    }
    metadata.write_text(json.dumps({"repo": repository, "pull": pull}))
    gh = binary_dir / "gh"
    gh.write_text(
        f'#!{sys.executable}\nimport json,sys\nv=json.load(open({str(metadata)!r}))\nprint(json.dumps(v["pull" if "/pulls/" in sys.argv[-1] else "repo"]))\n'
    )
    gh.chmod(0o700)
    monkeypatch.setenv("PATH", str(binary_dir) + os.pathsep + os.environ["PATH"])

    def worker():
        return subprocess.run(
            [sys.executable, "-m", "specify_cli.workspace_lifecycle.worker", "--state-dir", str(store.root)], capture_output=True, text=True, timeout=20
        )

    first = worker()
    assert first.returncode == (2 if blocked else 0), first.stderr
    assert json.loads(first.stdout)["results"][-1]["status"] == "retained"
    assert path.exists()
    assert queue.snapshot() == (1, 0 if blocked else 1)
    pull["merged"] = True
    metadata.write_text(json.dumps({"repo": repository, "pull": pull}))
    queue.notify("delivery")
    second = worker()
    assert second.returncode == (2 if blocked else 0), second.stderr
    assert json.loads(second.stdout)["results"][-1]["status"] == "retired"
    assert not path.exists()
    assert queue.snapshot() == (2, 0 if blocked else 2)


def test_completion_dispatch_is_after_durable_wakeup_and_failure_retains_hint(tmp_path: Path) -> None:
    from specify_cli.workspace_lifecycle.events import EventQueue

    queue = EventQueue(ledger(tmp_path))

    def broken_dispatch() -> None:
        # Inspect the atomic payload, not a competing queue lock.
        import json

        assert json.loads((queue.store.root / "events.json").read_text())["generation"] == 1
        raise OSError("worker unavailable")

    with pytest.raises(StateError, match="queue unavailable"):
        queue.notify("completion", dispatch=broken_dispatch)
    assert queue.snapshot() == (1, 0)


def test_worker_entrypoint_is_registered_in_real_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from test_ledger_cli import invoke

    store = ledger(tmp_path)
    result = invoke(monkeypatch, ["worker", "--state-dir", str(store.root)])
    assert result.exit_code == 0, result.output
    import json

    assert json.loads(result.output) == {"worker": "settled", "results": []}
