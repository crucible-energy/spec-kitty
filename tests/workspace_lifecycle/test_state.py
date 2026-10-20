"""Real private JSON ledger; corrupt state never becomes an empty success."""

from dataclasses import replace
from pathlib import Path

import pytest

from specify_cli.workspace_lifecycle.state import StateError, StateStore


def store(tmp_path: Path) -> StateStore:
    root = tmp_path / "lifecycle"
    root.mkdir(mode=0o700)
    return StateStore(root)


def test_private_state_round_trip_and_monotonic_revision(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    with ledger.locked() as tx:
        assert tx.state.revision == 0
        tx.commit(
            replace(
                tx.state,
                observations=(
                    {
                        "repository": "crucible-energy/example",
                        "repository_id": 1,
                        "common_dir": "/store/.git",
                        "path": "/work/unknown",
                        "head": "a" * 40,
                        "branch": "refs/heads/feature",
                        "bare": False,
                        "exists": True,
                        "disposition": "retained",
                        "reason": "ownership_unknown",
                    },
                ),
            )
        )
        assert tx.state.revision == 1
    assert ledger.read().observations[0]["path"] == "/work/unknown"
    assert ledger.read().observations[0]["repository_id"] == 1
    assert (ledger.root / "state.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "raw", ["not-json", "{}", '{"schema_version":1,"schema_version":1}', '{"schema_version":999,"revision":0,"observations":[],"operations":[]}']
)
def test_corrupt_or_unsupported_ledger_refuses_without_overwrite(tmp_path: Path, raw: str) -> None:
    ledger = store(tmp_path)
    p = ledger.root / "state.json"
    p.write_text(raw)
    p.chmod(0o600)
    with pytest.raises(StateError):
        ledger.read()
    assert p.read_text() == raw


def test_symlinked_state_and_insecure_root_refuse(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    external = tmp_path / "valuable"
    external.write_text("preserve")
    (ledger.root / "state.json").symlink_to(external)
    with pytest.raises(StateError):
        ledger.read()
    assert external.read_text() == "preserve"
    (ledger.root / "state.json").unlink()
    ledger.root.chmod(0o775)
    with pytest.raises(StateError):
        ledger.read()


def test_failed_durable_commit_does_not_report_a_committed_revision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.workspace_lifecycle.state as module

    ledger = store(tmp_path)
    monkeypatch.setattr(module, "atomic_write", lambda *a, **kw: (_ for _ in ()).throw(OSError("sync failed")))
    with ledger.locked() as tx:
        with pytest.raises(StateError):
            tx.commit(tx.state)
        assert tx.state.revision == 0


def test_transaction_cannot_commit_after_lock_release(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    with ledger.locked() as tx:
        tx.commit(tx.state)
    with ledger.locked() as current:
        current.commit(current.state)
    with pytest.raises(StateError):
        tx.commit(tx.state)
    assert ledger.read().revision == 2


def test_transaction_cannot_commit_from_another_thread(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    ledger = store(tmp_path)
    with ledger.locked() as tx, ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(StateError):
            pool.submit(tx.commit, tx.state).result(timeout=3)


def test_missing_previously_committed_ledger_never_becomes_empty_state(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    with ledger.locked() as tx:
        tx.commit(tx.state)
    (ledger.root / "state.json").unlink()
    with pytest.raises(StateError):
        ledger.read()


def test_hardlinked_lock_never_modifies_another_file(tmp_path: Path) -> None:
    import os

    ledger = store(tmp_path)
    external = tmp_path / "valuable"
    external.write_text("preserve")
    external.chmod(0o600)
    os.link(external, ledger.root / "lifecycle.lock")
    try:
        with pytest.raises(StateError):
            ledger.read()
    finally:
        assert external.read_text() == "preserve"


def test_fifo_state_refuses_without_blocking_open(tmp_path: Path) -> None:
    import os
    import subprocess
    import sys

    ledger = store(tmp_path)
    os.mkfifo(ledger.root / "state.json", 0o600)
    script = """from pathlib import Path
import sys
from specify_cli.workspace_lifecycle.state import StateStore, StateError
try:
    StateStore(Path(sys.argv[1])).read()
except StateError:
    print('refused')
"""
    proc = subprocess.Popen([sys.executable, "-c", script, str(ledger.root)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        output, error = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        pytest.fail("Malformed state blocked before type validation")
    assert proc.returncode == 0, error.decode()
    assert output.strip() == b"refused"
