"""Real private JSON ledger; corrupt state never becomes an empty success."""

from dataclasses import replace
from pathlib import Path

import pytest

from specify_cli.workspace_lifecycle.state import StateError, StateStore


def store(tmp_path: Path) -> StateStore:
    from kernel.no_follow import fd_relative_dir_ops_supported

    if not fd_relative_dir_ops_supported():
        pytest.skip("Strict persistence is unavailable on this platform")
    root = tmp_path / "lifecycle"
    root.mkdir(mode=0o700)
    return StateStore.initialize(root)


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
    (ledger.root / "state.json").unlink()
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
    with ledger.locked() as tx, ThreadPoolExecutor(max_workers=1) as pool, pytest.raises(StateError):
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
    (ledger.root / "lifecycle.lock").unlink()
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
    (ledger.root / "state.json").unlink()
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


def test_transaction_cannot_survive_owner_process(tmp_path: Path) -> None:
    import multiprocessing
    import os

    if not hasattr(os, "fork"):
        pytest.skip("fork capability is not present on this platform")
    ledger = store(tmp_path)
    context = multiprocessing.get_context("fork")
    released = context.Event()
    with ledger.locked() as tx:

        def child_commit() -> None:
            assert released.wait(5)
            try:
                tx.commit(tx.state)
            except StateError:
                return
            raise AssertionError("Forked transaction committed after owner released its lock")

        child = context.Process(target=child_commit)
        child.start()
    released.set()
    child.join(timeout=5)
    if child.is_alive():
        child.terminate()
        child.join(timeout=5)
        pytest.fail("Forked capability test did not terminate")
    assert child.exitcode == 0


def test_replaced_state_directory_is_not_adopted(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    original = ledger.root.with_name("original")
    ledger.root.rename(original)
    ledger.root.mkdir(mode=0o700)
    with pytest.raises(StateError):
        ledger.read()
    assert not (ledger.root / "lifecycle.lock").exists()
    assert (original / "state.json").exists()


def test_nonempty_initialization_preserves_foreign_content(tmp_path: Path) -> None:
    root = tmp_path / "foreign"
    root.mkdir(mode=0o700)
    content = root / "valuable.json"
    content.write_text('{"preserve":true}')
    with pytest.raises(StateError):
        StateStore.initialize(root)
    assert content.read_text() == '{"preserve":true}'
    assert not (root / "lifecycle.lock").exists()


def test_unsupported_private_state_capability_refuses_before_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.workspace_lifecycle.state as module

    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(module, "fd_relative_dir_ops_supported", lambda: False)
    with pytest.raises(StateError):
        StateStore.initialize(root)
    assert list(root.iterdir()) == []


def test_initialization_sync_failure_is_not_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel.no_follow import fd_relative_dir_ops_supported

    if not fd_relative_dir_ops_supported():
        pytest.skip("Strict persistence is unavailable on this platform")
    import specify_cli.workspace_lifecycle.state as module

    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(module, "atomic_write", lambda *a, **kw: (_ for _ in ()).throw(OSError("sync failed")))
    with pytest.raises(StateError):
        StateStore.initialize(root)
    with pytest.raises(StateError):
        StateStore(root).read()


def test_hardlinked_or_public_state_is_refused_without_changes(tmp_path: Path) -> None:
    import os

    ledger = store(tmp_path)
    path = ledger.root / "state.json"
    before = path.read_bytes()
    os.link(path, tmp_path / "alias.json")
    with pytest.raises(StateError):
        ledger.read()
    assert path.read_bytes() == before
    (tmp_path / "alias.json").unlink()
    path.chmod(0o644)
    with pytest.raises(StateError):
        ledger.read()
    assert path.read_bytes() == before


def test_state_size_and_entry_limits_are_enforced(tmp_path: Path) -> None:
    import json
    from specify_cli.workspace_lifecycle.state import MAX_BYTES, MAX_ENTRIES

    ledger = store(tmp_path)
    path = ledger.root / "state.json"
    original = json.loads(path.read_text())
    oversized = dict(original, observations=[None] * (MAX_ENTRIES + 1))
    path.write_text(json.dumps(oversized))
    with pytest.raises(StateError):
        ledger.read()
    path.write_bytes(b" " * (MAX_BYTES + 1))
    with pytest.raises(StateError):
        ledger.read()


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(revision=True),
        lambda d: d.update(revision=-1),
        lambda d: d.update(observations={}),
        lambda d: d.update(operations={}),
        lambda d: d["operations"][0].update(identity=[]),
        lambda d: d["operations"][0]["identity"].update(repository_id=True),
        lambda d: d["operations"][0]["identity"].update(head="not-a-commit"),
        lambda d: d["operations"][0].update(event_id=3),
        lambda d: d["operations"][0].update(status="done"),
        lambda d: d["operations"][0].update(creator_id=""),
        lambda d: d["operations"][0].update(release_id=7),
        lambda d: d["operations"][0].update(evidence_sha256="bad"),
        lambda d: d["operations"].append(d["operations"][0].copy()),
    ],
)
def test_malformed_operation_ledger_refuses_without_reset(tmp_path: Path, change) -> None:
    import json
    from specify_cli.workspace_lifecycle.policy import Identity
    from specify_cli.workspace_lifecycle.state import Operation

    ledger = store(tmp_path)
    identity = Identity(1, "crucible-energy/example", str(tmp_path / ".git"), str(tmp_path / "work"), "a" * 40, "refs/heads/feature", "workspace", "lease")
    operation = Operation("event", identity, "a" * 64, "retained", "owner_release_missing", "creator", None, None)
    with ledger.locked() as tx:
        tx.commit(replace(tx.state, operations=(operation,)))
    path = ledger.root / "state.json"
    data = json.loads(path.read_text())
    change(data)
    encoded = json.dumps(data).encode()
    path.write_bytes(encoded)
    with pytest.raises(StateError):
        ledger.read()
    assert path.read_bytes() == encoded
