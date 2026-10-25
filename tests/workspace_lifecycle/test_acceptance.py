"""Integrated organization lifecycle: real Git, actual workers and bounded hints."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from specify_cli.workspace_lifecycle.coordinator import Coordinator
from specify_cli.workspace_lifecycle.events import EventQueue
from specify_cli.workspace_lifecycle.state import StateStore
from tests.workspace_lifecycle.test_adapters import git, managed_owner
from tests.workspace_lifecycle.test_ledger_cli import invoke


def configure(monkeypatch: pytest.MonkeyPatch, store: StateStore, root: Path, *, timeout: float = 30) -> None:
    result = invoke(monkeypatch, ["configure", "--state-dir", str(store.root), "--root", str(root), "--max-depth", "0", "--worker-timeout", str(timeout)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["action"] == "configured"
    assert report["runtime_installed"] is False


def fake_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner: Any, *, hung: bool = False) -> Path:
    directory = tmp_path / "fixture-bin"
    directory.mkdir()
    marker = tmp_path / "inventory-processes.json"
    repository = {"id": 7, "full_name": "crucible-energy/example", "default_branch": "main"}
    source = git(Path(owner.identity.path), "rev-parse", "HEAD")
    # Accepted server delivery is a real bare-remote commit, independent of the
    # checked-out local default branch and the API fixture response.
    git(Path(owner.identity.path), "push", str(tmp_path / "origin.git"), "HEAD:refs/heads/main")
    reviews = {
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
    pull = {
        "number": 9,
        "merged": True,
        "state": "closed",
        "merged_at": "2026-10-21",
        "merge_commit_sha": source,
        "head": {"ref": owner.identity.branch.removeprefix("refs/heads/"), "sha": git(Path(owner.identity.path), "rev-parse", "HEAD"), "repo": repository},
        "base": {"ref": "main", "repo": repository},
    }
    script = f"#!{sys.executable}\nimport json,os,subprocess,sys,time\nfrom pathlib import Path\nrepository={repository!r}\npull={pull!r}\nreviews={reviews!r}\n"
    if hung:
        script += (
            "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(5)'])\n"
            f"Path({str(marker)!r}).write_text(json.dumps([os.getpid(),child.pid]))\n"
            "time.sleep(5)\n"
        )
    script += (
        "endpoint=sys.argv[-1]\n"
        "value=[repository] if endpoint.startswith('orgs/') else reviews if endpoint == 'graphql' else pull if '/pulls/' in endpoint else repository\n"
        "print(json.dumps(value))\n"
    )
    tool = directory / "gh"
    tool.write_text(script)
    tool.chmod(0o700)
    monkeypatch.setenv("PATH", str(directory) + os.pathsep + os.environ["PATH"])
    return marker


def test_session_end_enqueues_while_coordinator_is_busy_and_never_releases_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    owner, store, _, _ = managed_owner(tmp_path, monkeypatch)
    before = owner._read()
    with store.locked():
        result = invoke(monkeypatch, ["event", "--state-dir", str(store.root), "--kind", "session-end"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"action": "enqueued", "trigger": "session-end", "cleanup_complete": False}
    assert EventQueue(store).snapshot() == (1, 0)
    assert owner._read() == before
    assert Path(owner.identity.path).exists()
    assert not (store.root / "worker-result.json").exists(), "SessionEnd must not synchronously scan, dispatch retirement or mint release."


def test_configuration_and_hook_definition_are_private_scoped_and_not_installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, store, _, repo = managed_owner(tmp_path, monkeypatch)
    configure(monkeypatch, store, repo)
    config = store.root / "organization.json"
    assert config.stat().st_mode & 0o777 == 0o600
    value = json.loads(config.read_text())
    assert value["roots"] == [str(repo)] and value["organization"] == "crucible-energy"
    result = invoke(monkeypatch, ["hook-definition", "--state-dir", str(store.root)])
    assert result.exit_code == 0, result.output
    hooks = json.loads(result.output)["hooks"]
    assert set(hooks) == {"SessionStart", "SessionEnd"}
    for event, kind in [("SessionStart", "session-start"), ("SessionEnd", "session-end")]:
        handler = hooks[event][0]["hooks"][0]
        argv = shlex.split(handler["command"])
        assert Path(argv[0]).is_absolute()
        assert argv[-4:] == ["--state-dir", str(store.root), "--kind", kind]
        assert handler["timeout"] == 3
    assert not (repo / ".codex").exists()
    assert not (repo / ".claude").exists()


def test_current_registered_observation_binds_only_through_real_creator_hold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.discovery import discover_workspaces
    from specify_cli.workspace_lifecycle.state import bound_identity

    owner, store, _, repo = managed_owner(tmp_path, monkeypatch)
    observations = discover_workspaces({"crucible-energy/example": 7}, [repo], max_depth=0)["workspaces"]
    Coordinator(store).account(observations, registered=[(owner.identity, owner)])
    rows = store.read().observations
    owned = [row for row in rows if row["path"] == owner.identity.path]
    assert len(owned) == 1 and bound_identity(owned[0]) == owner.identity
    assert all(bound_identity(row) is None for row in rows if row["path"] != owner.identity.path)
    assert Path(owner.identity.path).exists(), "Accounting never grants retirement."


def test_startup_accounts_non_lane_work_and_retires_released_delivered_creator_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    owner, store, _, repo = managed_owner(tmp_path, monkeypatch)
    unknown = tmp_path / "legacy-unregistered"
    git(repo, "worktree", "add", "-b", "legacy/non-lane", str(unknown))
    main = git(repo, "rev-parse", "main")
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)  # Deliberately lost completion: the fixture callback only records it.
    fake_gh(tmp_path, monkeypatch, owner)
    configure(monkeypatch, store, repo)
    children: list[subprocess.Popen[Any]] = []
    original = subprocess.Popen

    def observe_child(*args: Any, **kwargs: Any) -> Any:
        child = original(*args, **kwargs)
        if any("specify_cli.workspace_lifecycle.worker" in arg for arg in args[0]):
            children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", observe_child)
    for iteration in range(2):
        result = invoke(monkeypatch, ["event", "--state-dir", str(store.root), "--kind", "session-start"])
        assert result.exit_code == 0, result.output
        assert len(children) == iteration + 1
        assert children[-1].wait(timeout=20) == 0
    report = LifecycleService(store).status()
    inventory = report["organization_observation"]
    assert inventory["status"] == "observed" and inventory["local_scan_complete"] is True
    assert not Path(owner.identity.path).exists() and unknown.exists()
    assert git(repo, "rev-parse", "main") == main
    assert git(repo, "branch", "--list", "task") == ""
    state = store.read()
    retired = [op for op in state.operations if op.status == "retired"]
    assert len(retired) == 1
    assert {row["path"] for row in state.observations if row["disposition"] != "retired"} == {str(repo), str(unknown)}
    assert report["pending_wakeup"] is False


@pytest.mark.timing
def test_hung_inventory_records_unknown_diagnostic_and_joins_its_process_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time
    from kernel.owned_process import bounded_run
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    owner, store, _, repo = managed_owner(tmp_path, monkeypatch)
    marker = fake_gh(tmp_path, monkeypatch, owner, hung=True)
    configure(monkeypatch, store, repo, timeout=2)
    EventQueue(store).notify("startup")
    started = time.monotonic()
    result = bounded_run([sys.executable, "-m", "specify_cli.workspace_lifecycle.worker", "--state-dir", str(store.root)], timeout=10, text=True)
    elapsed = time.monotonic() - started
    assert result.returncode == 2, result.stdout + result.stderr
    report = LifecycleService(store).status()
    assert report["organization_observation"]["status"] == "unknown"
    assert report["organization_observation"]["reason"] == "inventory_unavailable"
    assert report["pending_wakeup"] is True
    assert Path(owner.identity.path).exists()
    assert elapsed < 4, f"Worker deadline did not bound the actual hung inventory: {elapsed}"
    for pid in json.loads(marker.read_text()):
        status = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, timeout=2, check=False).stdout.strip()
        assert not status or status.startswith("Z"), f"Inventory descendant remains active: {pid} {status}"


def test_account_preserves_historical_unknown_and_refuses_changed_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace
    from specify_cli.workspace_lifecycle.discovery import discover_workspaces
    from specify_cli.workspace_lifecycle.state import bound_identity

    owner, store, _, repo = managed_owner(tmp_path, monkeypatch)
    rows = discover_workspaces({"crucible-energy/example": 7}, [repo], max_depth=0)["workspaces"]
    coordinator = Coordinator(store)
    coordinator.account(rows)
    original = store.read().observations
    coordinator.account(rows, registered=[(replace(owner.identity, lease_generation="different"), owner)])
    assert all(bound_identity(row) is None for row in store.read().observations)
    assert {row["path"] for row in store.read().observations} == {row["path"] for row in original}
    coordinator.account(rows, registered=[(owner.identity, owner)])
    same_path = [row for row in store.read().observations if row["path"] == owner.identity.path]
    assert len(same_path) == 2
    assert sum(bound_identity(row) is None for row in same_path) == 1
    assert sum(bound_identity(row) == owner.identity for row in same_path) == 1
    assert Path(owner.identity.path).exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("roots", []),
        ("roots", ["relative"]),
        ("roots", ["/safe/../other"]),
        ("max_depth", True),
        ("max_depth", 65),
        ("max_entries", 0),
        ("max_directories", 100001),
        ("worker_timeout", True),
        ("worker_timeout", float("inf")),
        ("worker_timeout", 0),
        ("organization", "other"),
        ("schema_version", True),
    ],
)
def test_configuration_refuses_invalid_scope_without_modifying_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object) -> None:
    from specify_cli.workspace_lifecycle.configuration import OrganizationScope
    from specify_cli.workspace_lifecycle.state import StateError

    _, store, _, repo = managed_owner(tmp_path, monkeypatch)
    scope = OrganizationScope((str(repo),))
    record = scope.record()
    record[field] = value
    (store.root / "organization.json").write_text(json.dumps(record))
    (store.root / "organization.json").chmod(0o600)
    with pytest.raises(StateError):
        OrganizationScope.read(store)
    assert store.read().revision == 0


def test_emitted_session_hook_executes_generating_distribution_outside_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    canonical_home: None,
) -> None:
    _, store, _, repo = managed_owner(tmp_path, monkeypatch)
    configure(monkeypatch, store, repo)
    definition = invoke(monkeypatch, ["hook-definition", "--state-dir", str(store.root)])
    command = json.loads(definition.output)["hooks"]["SessionEnd"][0]["hooks"][0]["command"]
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    # A hostile ambient module path must not choose a different lifecycle CLI.
    (unrelated / "specify_cli.py").write_text("raise RuntimeError('wrong distribution')")
    env = {**os.environ, "PYTHONPATH": str(unrelated)}
    result = subprocess.run(shlex.split(command), cwd=unrelated, env=env, capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["trigger"] == "session-end"
    assert EventQueue(store).snapshot() == (1, 0)
    assert not (store.root / "worker-result.json").exists()


def test_reconfiguration_and_new_hint_mark_previous_scope_observation_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.configuration import OrganizationScope
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    owner, store, _, repo = managed_owner(tmp_path, monkeypatch)
    fake_gh(tmp_path, monkeypatch, owner)
    configure(monkeypatch, store, repo)
    EventQueue(store).notify("startup")
    LifecycleService(store).run()
    assert LifecycleService(store).status()["organization_observation_current"] is True
    OrganizationScope((str(tmp_path),), max_depth=0).admit(store)
    assert LifecycleService(store).status()["organization_observation_current"] is False
    OrganizationScope((str(repo),), max_depth=0, worker_timeout=30).admit(store)
    assert LifecycleService(store).status()["organization_observation_current"] is True
    EventQueue(store).notify("session-end")
    assert LifecycleService(store).status()["organization_observation_current"] is False


@pytest.mark.timing
def test_fresh_cli_status_and_enqueue_each_meet_two_second_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    canonical_home: None,
) -> None:
    import time
    from dataclasses import replace
    from specify_cli.workspace_lifecycle.adapters import ManagedGitCreator
    from specify_cli.workspace_lifecycle.state import Operation

    first, store, _, repo = managed_owner(tmp_path, monkeypatch)
    second = ManagedGitCreator.create(
        store,
        repo_root=repo,
        path=tmp_path / "second",
        branch="second",
        repository="crucible-energy/example",
        repository_id=7,
        delivery=first.delivery,
        on_complete=lambda hint: None,
    )
    # Explicit fixture history, never a claimed real retirement receipt.
    operations = tuple(
        Operation(
            f"fixture:{i}", replace(first.identity, workspace_generation=f"fixture-{i}"), "a" * 64, "retained", "fixture_settled", first.authority_id, None, None
        )
        for i in range(100)
    )
    with store.locked() as tx:
        tx.commit(replace(tx.state, operations=operations))
    assert len(git(repo, "worktree", "list", "--porcelain").split("worktree ")) - 1 == 3
    assert Path(second.identity.path).exists()
    source = str(Path(__file__).resolve().parents[2] / "src")
    env = {**os.environ, "PYTHONPATH": source}
    samples: dict[str, list[float]] = {}
    for name, args in [("status", ["status"]), ("enqueue", ["event", "--kind", "session-end"])]:
        samples[name] = []
        for _ in range(5):
            started = time.monotonic()
            result = subprocess.run(
                [sys.executable, "-m", "specify_cli", "workspaces", *args, "--state-dir", str(store.root)],
                cwd=tmp_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            elapsed = time.monotonic() - started
            samples[name].append(elapsed)
            assert result.returncode == 0, result.stdout + result.stderr
            assert elapsed < 2, {"operation": name, "elapsed_seconds": elapsed}
    print(json.dumps({"fresh_process_elapsed_seconds": samples, "repositories": 1, "registered_workspaces": 3, "settled_fixture_entries": 100}))
    assert EventQueue(store).snapshot() == (5, 0)


def test_real_spec_kitty_consolidation_is_joined_before_creator_completion_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    canonical_home: None,
) -> None:
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery, ManagedGitCreator
    from tests.terminus.conftest import build_coord_mission

    mission = build_coord_mission(tmp_path, target_branch="feature/integration")
    repo = mission.repo
    git(repo, "branch", "main", "feature/integration")
    # A real local origin mirror supplies branch-currentness evidence without
    # contacting a production repository or disabling the origin check.
    mirror = tmp_path / "origin.git"
    subprocess.run(["git", "clone", "--bare", str(repo), str(mirror)], check=True, capture_output=True, timeout=10)
    git(repo, "config", f"url.{mirror.as_uri()}.insteadOf", "https://github.com/crucible-energy/example.git")
    git(repo, "remote", "add", "origin", "https://github.com/crucible-energy/example.git")
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    primary = git(repo, "rev-parse", "main")
    ledger = tmp_path / "ledger"
    ledger.mkdir(mode=0o700)
    store = StateStore.initialize(ledger)
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    children: list[subprocess.Popen[Any]] = []
    original_popen = subprocess.Popen

    def observe(*args: Any, **kwargs: Any) -> Any:
        child = original_popen(*args, **kwargs)
        if any("specify_cli.workspace_lifecycle.worker" in arg for arg in args[0]):
            children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", observe)
    owner = ManagedGitCreator.create(
        store,
        repo_root=repo,
        path=tmp_path / "integration",
        branch="feature/driver",
        repository="crucible-energy/example",
        repository_id=7,
        delivery=GitHubDelivery(),
        on_complete=LifecycleService(store).completion,
    )
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[2] / "src"))
    before = owner.identity.head
    log = tmp_path / "consolidation.log"
    producer = (
        "import subprocess,sys; "
        f"out=open({str(log)!r},'w'); "
        f"r=subprocess.run([sys.executable,'-m','specify_cli','consolidate','--mission',{mission.slug!r},'--yes'],stdout=out,stderr=subprocess.STDOUT); "
        "out.close(); "
        "r.returncode == 0 and subprocess.run(['git','merge','--ff-only','feature/integration'],check=True); "
        "sys.exit(r.returncode)"
    )
    try:
        owner.run_producer([sys.executable, "-c", producer], timeout=30)
    except Exception:
        pytest.fail(log.read_text() if log.exists() else "No consolidation diagnostic was produced")
    assert not children and Path(owner.identity.path).exists()
    assert git(Path(owner.identity.path), "show", "HEAD:src/pkg/wp01.py")
    fake_gh(tmp_path, monkeypatch, owner)
    owner.complete(pr=9)
    assert owner.identity.head != before
    assert len(children) == 1 and git(repo, "rev-parse", "main") == primary
    assert children[0].wait(timeout=20) == 0
    assert not Path(owner.identity.path).exists(), (store.read().operations, json.loads((store.root / "worker-result.json").read_text()))
    assert git(repo, "rev-parse", "main") == primary
    assert git(repo, "branch", "--list", "feature/driver") == ""
    assert sum(op.status == "retired" for op in store.read().operations) == 1


def test_failed_competing_registration_taints_only_its_current_observation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace
    from specify_cli.workspace_lifecycle.discovery import discover_workspaces
    from specify_cli.workspace_lifecycle.state import bound_identity

    owner, store, _, repo = managed_owner(tmp_path, monkeypatch)
    rows = discover_workspaces({"crucible-energy/example": 7}, [repo], max_depth=0)["workspaces"]
    Coordinator(store).account(rows, registered=[(owner.identity, owner), (replace(owner.identity, lease_generation="stale"), owner)])
    current = store.read().observations
    assert len(current) == len(rows)
    assert all(bound_identity(row) is None for row in current)
    assert next(row for row in current if row["path"] == owner.identity.path)["reason"] == "creator_registration_unavailable"
    assert Path(owner.identity.path).exists()


def test_discovery_expired_budget_preserves_explicit_incomplete_scope(tmp_path: Path) -> None:
    import time
    from kernel.owned_process import process_budget
    from specify_cli.workspace_lifecycle.discovery import discover_workspaces

    with process_budget(0.001):
        time.sleep(0.002)
        report = discover_workspaces({"crucible-energy/example": 7}, [tmp_path])
    assert report["local_scan_complete"] is False
    assert report["coverage_gaps"] == [{"path": str(tmp_path), "reason": "worker_deadline_exhausted"}]
    assert "undiscovered_stores_outside_configured_roots" in report["observation_scope"]["unobservable"]


def test_hook_generation_requires_scope_and_duplicate_scope_keys_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.configuration import OrganizationScope
    from specify_cli.workspace_lifecycle.state import StateError

    _, store, _, _ = managed_owner(tmp_path, monkeypatch)
    result = invoke(monkeypatch, ["hook-definition", "--state-dir", str(store.root)])
    assert result.exit_code == 2
    assert "Configure explicit organization roots" in result.output
    path = store.root / "organization.json"
    path.write_text('{"roots": [], "roots": []}')
    path.chmod(0o600)
    with pytest.raises(StateError, match="Duplicate"):
        OrganizationScope.read(store)


def test_session_start_worker_keeps_distribution_outside_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    owner, store, _, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    fake_gh(tmp_path, monkeypatch, owner)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / "specify_cli.py").write_text("raise RuntimeError('wrong worker distribution')")
    monkeypatch.chdir(unrelated)
    monkeypatch.setenv("PYTHONPATH", str(unrelated))
    children: list[subprocess.Popen[Any]] = []
    original = subprocess.Popen

    def observe(*args: Any, **kwargs: Any) -> Any:
        child = original(*args, **kwargs)
        if any("specify_cli.workspace_lifecycle.worker" in arg for arg in args[0]):
            children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", observe)
    result = invoke(monkeypatch, ["event", "--state-dir", str(store.root), "--kind", "session-start"])
    assert result.exit_code == 0, result.output
    assert len(children) == 1 and children[0].wait(timeout=15) == 0
    assert LifecycleService(store).status()["pending_wakeup"] is False
    assert not Path(owner.identity.path).exists()


@pytest.mark.parametrize("subcommand,fast", [("status", True), ("event", True), ("configure", False), ("managed-run", False), ("worker", False)])
def test_only_explicit_ledger_observation_commands_use_bounded_startup(subcommand: str, fast: bool) -> None:
    from specify_cli import _is_workspace_observation_invocation

    assert _is_workspace_observation_invocation(["spec-kitty", "workspaces", subcommand, "--state-dir", "/private/ledger"]) is fast
    assert _is_workspace_observation_invocation(["spec-kitty", "other", subcommand]) is False
    assert _is_workspace_observation_invocation(["spec-kitty", "--help"]) is False
