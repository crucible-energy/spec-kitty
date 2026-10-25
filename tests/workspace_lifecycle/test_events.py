"""Durable hints survive exit without granting creator authority."""

from pathlib import Path

import pytest

from specify_cli.workspace_lifecycle.state import StateError, StateStore


def _review_evidence(source: str) -> dict[str, object]:
    """Bounded API evidence for the real local mirror's exact source/merge."""
    return {
        "data": {
            "repository": {
                "databaseId": 7,
                "pullRequest": {
                    "headRefOid": source,
                    "headRef": None,
                    "mergeCommit": {"oid": source},
                    "reviewThreads": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}},
                },
            }
        }
    }


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

    from test_adapters import git, managed_owner
    from specify_cli.workspace_lifecycle.events import EventQueue

    owner, store, _, repo = managed_owner(tmp_path, monkeypatch)
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
    source = git(repo, "rev-parse", "main")
    assert source == git(tmp_path / "origin.git", "rev-parse", "refs/heads/main")
    reviews = _review_evidence(source)
    pull = {
        "number": 9,
        "merged": False,
        "state": "closed",
        "merged_at": None,
        "merge_commit_sha": source,
        "head": {"ref": "task", "sha": owner.identity.head, "repo": repository},
        "base": {"ref": "main", "repo": repository},
    }
    metadata.write_text(json.dumps({"repo": repository, "pull": pull, "reviews": reviews}))
    gh = binary_dir / "gh"
    gh.write_text(
        f"#!{sys.executable}\nimport json,sys\nv=json.load(open({str(metadata)!r}))\n"
        'key = "reviews" if sys.argv[-1] == "graphql" else "pull" if "/pulls/" in sys.argv[-1] else "repo"\n'
        "print(json.dumps(v[key]))\n"
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
    pull["merged_at"] = "2026-10-20T00:00:00Z"
    metadata.write_text(json.dumps({"repo": repository, "pull": pull, "reviews": reviews}))
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    children = []
    original_popen = subprocess.Popen

    def capture_child(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", capture_child)
    service = LifecycleService(store)
    service.resume()
    assert len(children) == 1
    assert children[0].wait(timeout=20) == (2 if blocked else 0)
    report = service.status()
    assert report["last_worker_observation"]["results"][-1]["status"] == "retired"
    assert report["pending_wakeup"] is blocked
    assert not path.exists()
    assert git(repo, "branch", "--list", owner.identity.branch.removeprefix("refs/heads/")) == ""
    assert git(repo, "rev-parse", "main") == source
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


def test_managed_run_cli_joins_reports_pr_and_automatically_retires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    import os
    import subprocess
    import sys

    from test_adapters import git, managed_owner
    from test_ledger_cli import invoke
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    original_owner, store, _, repo = managed_owner(tmp_path, monkeypatch)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    repository = {"id": 7, "full_name": "crucible-energy/example", "default_branch": "main"}
    source = git(repo, "rev-parse", "main")
    assert source == git(tmp_path / "origin.git", "rev-parse", "refs/heads/main")
    reviews = _review_evidence(source)
    pull = {
        "number": 9,
        "merged": True,
        "state": "closed",
        "merged_at": "2026-10-20",
        "merge_commit_sha": source,
        "head": {"ref": "automatic-job", "sha": git(repo, "rev-parse", "HEAD"), "repo": repository},
        "base": {"ref": "main", "repo": repository},
    }
    gh = bindir / "gh"
    gh.write_text(
        f"#!{sys.executable}\nimport json,sys\nv={json.dumps({'repo': repository, 'pull': pull, 'reviews': reviews})!r}\n"
        'v=json.loads(v)\nprint(json.dumps(v["reviews" if sys.argv[-1] == "graphql" else "pull" if "/pulls/" in sys.argv[-1] else "repo"]))\n'
    )
    gh.chmod(0o700)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    children = []
    original_popen = subprocess.Popen

    def capture(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        if any("specify_cli.workspace_lifecycle.worker" in arg for arg in args[0]):
            children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", capture)
    path = tmp_path / "automatic-job"
    script = "import os; f=os.open(os.environ['SPEC_KITTY_LIFECYCLE_RESULT'],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.write(f,b'{\"pr\":9}'); os.close(f)"
    result = invoke(
        monkeypatch,
        [
            "managed-run",
            "--state-dir",
            str(store.root),
            "--repo-root",
            str(repo),
            "--workspace",
            str(path),
            "--branch",
            "automatic-job",
            "--repository",
            "crucible-energy/example",
            "--repository-id",
            "7",
            "--",
            sys.executable,
            "-c",
            script,
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["action"] == "released_and_queued"
    assert len(children) == 1
    assert children[0].wait(timeout=20) == 0
    assert not path.exists()
    assert git(repo, "branch", "--list", "automatic-job") == ""
    assert git(repo, "rev-parse", "main") == source
    assert Path(original_owner.identity.path).exists(), "Unreleased sibling creator must remain preserved"
    assert LifecycleService(store).status()["pending_wakeup"] is False


def test_blocked_worker_reconsiders_new_completion_before_releasing_lease(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    from test_adapters import managed_owner
    from specify_cli.workspace_lifecycle.coordinator import Coordinator
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    owner, store, _, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    malformed = store.root / ("creator-" + "0" * 32 + ".json")
    malformed.write_text("{}")
    malformed.chmod(0o600)
    service = LifecycleService(store)
    service.queue.notify("completion")
    original = Coordinator.reconcile
    seen = []

    def concurrent_event(self, event_id, expected, creator):
        seen.append(event_id)
        if len(seen) == 1:
            service.queue.notify("completion")
        return original(self, event_id, expected, creator)

    monkeypatch.setattr(Coordinator, "reconcile", concurrent_event)
    result = service.run()
    assert result["worker"] == "blocked"
    assert len(seen) == 2, "New completion must not be abandoned behind a blocked generation"
    assert service.status()["last_worker_observation"]["generation"] == 2
    assert service.queue.snapshot() == (2, 0)


def test_public_worker_reports_blocked_as_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    from test_ledger_cli import invoke

    store = ledger(tmp_path)
    malformed = store.root / ("creator-" + "0" * 32 + ".json")
    malformed.write_text("{}")
    malformed.chmod(0o600)
    result = invoke(monkeypatch, ["worker", "--state-dir", str(store.root)])
    assert result.exit_code == 2
    assert json.loads(result.output)["worker"] == "blocked"


@pytest.mark.parametrize(
    "record",
    [
        {"schema_version": 2, "generation": 1, "acknowledged": 0},
        {"schema_version": 1, "generation": True, "acknowledged": 0},
        {"schema_version": 1, "generation": 0, "acknowledged": 1},
        {"schema_version": 1, "generation": 1, "acknowledged": 0, "release": True},
    ],
)
def test_corrupt_wakeup_cannot_certify_completion(tmp_path: Path, record) -> None:
    import json
    from specify_cli.workspace_lifecycle.events import EventQueue

    store = ledger(tmp_path)
    path = store.root / "events.json"
    path.write_text(json.dumps(record))
    path.chmod(0o600)
    with pytest.raises(StateError, match="history"):
        EventQueue(store).snapshot()


def test_exhausted_and_unknown_events_refuse_without_reset(tmp_path: Path) -> None:
    import json
    from specify_cli.workspace_lifecycle.events import EventQueue

    store = ledger(tmp_path)
    queue = EventQueue(store)
    with pytest.raises(StateError, match="Unsupported"):
        queue.notify("anything-else")
    path = store.root / "events.json"
    path.write_text(json.dumps({"schema_version": 1, "generation": 2**63 - 1, "acknowledged": 0}))
    path.chmod(0o600)
    before = path.read_bytes()
    with pytest.raises(StateError, match="exhausted"):
        queue.notify("completion")
    assert path.read_bytes() == before


def test_resume_cli_dispatches_a_joined_real_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess
    from test_ledger_cli import invoke
    from specify_cli.workspace_lifecycle.events import EventQueue

    store = ledger(tmp_path)
    children = []
    original = subprocess.Popen

    def capture(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", capture)
    result = invoke(monkeypatch, ["resume", "--state-dir", str(store.root)])
    assert result.exit_code == 0, result.output
    assert len(children) == 1
    assert children[0].wait(timeout=20) == 0
    assert EventQueue(store).snapshot() == (1, 1)


@pytest.mark.parametrize("command", ["resume", "worker"])
def test_execution_cli_refuses_missing_history_without_admission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str) -> None:
    from test_ledger_cli import invoke

    root = tmp_path / "empty"
    root.mkdir(mode=0o700)
    result = invoke(monkeypatch, [command, "--state-dir", str(root)])
    assert result.exit_code == 2
    assert list(root.iterdir()) == []


def test_managed_cli_refuses_primary_before_workspace_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    from test_adapters import managed_owner
    from test_ledger_cli import invoke

    _, store, _, repo = managed_owner(tmp_path, monkeypatch)
    path = tmp_path / "forbidden"
    result = invoke(
        monkeypatch,
        [
            "managed-run",
            "--state-dir",
            str(store.root),
            "--repo-root",
            str(repo),
            "--workspace",
            str(path),
            "--branch",
            "main",
            "--repository",
            "crucible-energy/example",
            "--repository-id",
            "7",
            "--pr",
            "9",
            "--",
            sys.executable,
            "-c",
            "pass",
        ],
    )
    assert result.exit_code == 2, result.output
    assert not path.exists()


def test_busy_worker_keeps_pending_wakeup_without_competing_effect(tmp_path: Path) -> None:
    from kernel.locks import machine_file_lock
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    store = ledger(tmp_path)
    service = LifecycleService(store)
    service.queue.notify("completion")
    with machine_file_lock(store.root / "worker.lock", blocking=False, private=True):
        assert service.run() == {"worker": "already_running", "results": []}
    assert service.queue.snapshot() == (1, 0)


def test_sidecar_read_cannot_escape_ledger(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    with pytest.raises(StateError, match="Invalid private"):
        store.read_private("../outside")
