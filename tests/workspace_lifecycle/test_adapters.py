"""Creator/delivery acceptance through real local Git and bounded API seams."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn, TYPE_CHECKING

import pytest

from specify_cli.workspace_lifecycle.policy import Identity

if TYPE_CHECKING:
    from kernel.git import GitResult
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery, ManagedGitCreator, _OwnerState
    from specify_cli.workspace_lifecycle.coordinator import Result
    from specify_cli.workspace_lifecycle.events import Completion
    from specify_cli.workspace_lifecycle.state import Operation, StateStore


def object_at(value: object, *path: str) -> dict[str, Any]:
    """Assert a JSON object's shape before inspecting its variable fixture data."""
    for key in path:
        assert isinstance(value, dict)
        value = value[key]
    assert isinstance(value, dict) and all(isinstance(key, str) for key in value)
    return value


def identity() -> Identity:
    return Identity(7, "crucible-energy/example", "/repo/.git", "/work/task", "a" * 40, "refs/heads/task", "workspace", "lease")


def responses(monkeypatch: pytest.MonkeyPatch, *, head: str = "a" * 40, merged: bool = True, base: str = "main") -> list[list[str]]:
    commands: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        commands.append(argv)
        timeout = kwargs["timeout"]
        assert isinstance(timeout, (int, float)) and timeout > 0
        if argv[-1].endswith("/pulls/9"):
            value = {
                "number": 9,
                "merged": merged,
                "state": "closed",
                "merged_at": "2026-10-20T00:00:00Z",
                "merge_commit_sha": "b" * 40,
                "head": {"ref": "task", "sha": head, "repo": {"id": 7, "full_name": "crucible-energy/example"}},
                "base": {"ref": base, "repo": {"id": 7, "full_name": "crucible-energy/example"}},
            }
        else:
            value = {"id": 7, "full_name": "crucible-energy/example", "default_branch": "main"}
        return subprocess.CompletedProcess(argv, 0, json.dumps(value).encode(), b"")

    monkeypatch.setattr(subprocess, "run", run)
    return commands


def test_accepted_pr_binds_exact_source_and_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery

    calls = responses(monkeypatch)
    receipt = GitHubDelivery(timeout=1).verify(identity(), 9)
    assert receipt == "github:7:pr:9:merge:" + "b" * 40
    assert len(calls) == 2
    assert all("--hostname" in command and "github.com" in command for command in calls)


@pytest.mark.parametrize("head,merged,base", [("c" * 40, True, "main"), ("a" * 40, False, "main"), ("a" * 40, True, "other")])
def test_stale_unmerged_or_other_target_pr_is_not_delivery(monkeypatch: pytest.MonkeyPatch, head: str, merged: bool, base: str) -> None:
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery

    responses(monkeypatch, head=head, merged=merged, base=base)
    assert GitHubDelivery(timeout=1).verify(identity(), 9) is None


def test_delivery_deadline_is_finite_and_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery
    from specify_cli.workspace_lifecycle.state import StateError

    def timeout(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        timeout_seconds = kwargs["timeout"]
        assert isinstance(timeout_seconds, (int, float))
        raise subprocess.TimeoutExpired(argv, timeout_seconds, output=b"private-response")

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(StateError, match="Delivery authority unavailable") as failure:
        GitHubDelivery(timeout=0.01).verify(identity(), 9)
    assert "private-response" not in str(failure.value)


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_delivery_refuses_unbounded_configuration(timeout: float) -> None:
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery

    with pytest.raises(ValueError, match="finite positive"):
        GitHubDelivery(timeout=timeout)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True, timeout=5)
    return result.stdout.strip()


def managed_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ManagedGitCreator, StateStore, list[Completion], Path]:
    from kernel.no_follow import fd_relative_dir_ops_supported
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery, ManagedGitCreator
    from specify_cli.workspace_lifecycle.state import StateStore

    if not fd_relative_dir_ops_supported():
        pytest.skip("Strict persistence is unavailable on this platform")
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Lifecycle Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "commit", "--allow-empty", "-m", "base")
    git(repo, "remote", "add", "origin", "https://github.com/crucible-energy/example.git")
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    mirror = tmp_path / "origin.git"
    git(repo, "clone", "--bare", str(repo), str(mirror))
    git(repo, "config", f"url.{mirror.as_uri()}.insteadOf", "https://github.com/crucible-energy/example.git")
    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    ledger = StateStore.initialize(root)
    events: list[Completion] = []
    owner = ManagedGitCreator.create(
        ledger,
        repo_root=repo,
        path=tmp_path / "task",
        branch="task",
        repository="crucible-energy/example",
        repository_id=7,
        delivery=GitHubDelivery(timeout=1),
        on_complete=events.append,
    )
    original_run = subprocess.run

    def transport(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        if argv[0] != "gh":
            return original_run(argv, **kwargs)
        merge = git(mirror, "rev-parse", "refs/heads/main")
        value: dict[str, Any]
        if argv[-1] == "graphql":
            value = {
                "data": {
                    "repository": {
                        "databaseId": 7,
                        "pullRequest": {
                            "headRefOid": owner.identity.head,
                            "headRef": None,
                            "mergeCommit": {"oid": merge},
                            "reviewThreads": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}},
                        },
                    }
                }
            }
        elif argv[-1].endswith("/pulls/9"):
            value = {
                "number": 9,
                "merged": True,
                "state": "closed",
                "merged_at": "2026-10-20T00:00:00Z",
                "merge_commit_sha": merge,
                "head": {"ref": "task", "sha": owner.identity.head, "repo": {"id": 7, "full_name": "crucible-energy/example"}},
                "base": {"ref": "main", "repo": {"id": 7, "full_name": "crucible-energy/example"}},
            }
        else:
            value = {"id": 7, "full_name": "crucible-energy/example", "default_branch": "main"}
        return subprocess.CompletedProcess(argv, 0, json.dumps(value).encode(), b"")

    from specify_cli.workspace_lifecycle import adapters

    monkeypatch.setattr(subprocess, "run", transport)
    monkeypatch.setattr(adapters, "bounded_run", transport, raising=False)
    return owner, ledger, events, repo


def test_owned_non_lane_producer_releases_then_real_worktree_retires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    path = Path(owner.identity.path)
    script = (
        "from pathlib import Path; import subprocess; Path('result.md').write_text('delivered result'); "
        "subprocess.run(['git','add','result.md'],check=True); subprocess.run(['git','commit','-m','result'],check=True)"
    )
    owner.run_producer([sys.executable, "-c", script], timeout=5)
    git(path, "push", str(tmp_path / "origin.git"), "HEAD:refs/heads/main")
    owner.complete(pr=9)
    assert len(events) == 1
    assert path.exists(), "Completion callback must not retire inline"
    coordinator = Coordinator(ledger)
    coordinator.account_owned(owner.identity, owner)
    assert coordinator.reconcile(events[0].event_id, owner.identity, owner).status == "retired"
    assert not path.exists()
    assert git(repo, "branch", "--list", "task") == ""
    assert owner.branch_disposition == "local_retired;remote_retained"


def test_old_merged_api_response_without_current_default_delivery_preserves_creator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    unrelated = git(repo, "commit-tree", tree, "-m", "replacement default history")
    git(repo, "update-ref", "refs/heads/main", unrelated)
    git(repo, "push", "--force", str(tmp_path / "origin.git"), "main:refs/heads/main")
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery

    original_accepted = GitHubDelivery._accepted

    def old_accepted(self: GitHubDelivery, expected: Identity, pr: int, deadline: float) -> tuple[str, str, str] | None:
        value = original_accepted(self, expected, pr, deadline)
        return (value[0], owner.identity.head, value[2]) if value else None

    monkeypatch.setattr(GitHubDelivery, "_accepted", old_accepted)
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained", "An old merged API response is not current default-branch delivery."
    assert Path(owner.identity.path).exists()
    assert git(repo, "rev-parse", "refs/heads/task") == owner.identity.head


@pytest.mark.parametrize("holder", ["cwd", "open_file", "git_admin"])
def test_released_creator_preserves_another_live_runtime_holder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, holder: str) -> None:
    import select
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    path = Path(owner.identity.path)
    script = "import time; print('ready',flush=True); time.sleep(30)"
    if holder == "open_file":
        script = f"import time; f=open({str(path / '.git')!r}); print('ready',flush=True); time.sleep(30)"
    if holder == "git_admin":
        metadata = Path(git(path, "rev-parse", "--absolute-git-dir"))
        script = f"import time; f=open({str(metadata / 'HEAD')!r}); print('ready',flush=True); time.sleep(30)"
    child = subprocess.Popen([sys.executable, "-c", script], cwd=path if holder == "cwd" else tmp_path, stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout is not None
        readable, _, _ = select.select([child.stdout], [], [], 3)
        assert readable and child.stdout.readline().strip() == "ready", "Owned fixture runtime did not become ready."
        result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
        assert result.status == "retained", "A creator release cannot erase another live cwd/open-file dependency."
        assert path.exists()
        assert child.poll() is None
    finally:
        child.terminate()
        child.communicate(timeout=5)
    assert owner.branch_disposition == "local_retained;remote_retained"


@pytest.mark.parametrize(
    "code,stdout,stderr,expected",
    [
        (1, b"", b"", (False, True)),
        (0, b"p123\0\nfcwd\0n/private/task\0", b"", (True, True)),
        (0, b"unrecognized output", b"", (False, False)),
        (0, b"p123\0", b"visibility incomplete", (False, False)),
        (2, b"", b"", (False, False)),
    ],
)
def test_runtime_observation_distinguishes_no_holders_from_unavailable_visibility(
    monkeypatch: pytest.MonkeyPatch, code: int, stdout: bytes, stderr: bytes, expected: tuple[bool, bool]
) -> None:
    from specify_cli.workspace_lifecycle import adapters

    def observe(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        assert argv == ["/usr/sbin/lsof", "-nP", "+D", "/private/task", "-F0pfnt"]
        assert kwargs["timeout"] == 5
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    from types import SimpleNamespace

    monkeypatch.setattr(adapters, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(adapters, "bounded_run", observe)
    diagnostic: dict[str, object] = {}
    token = adapters._runtime_diagnostic.set(diagnostic)
    try:
        assert adapters._runtime_state(Path("/private/task")) == expected
    finally:
        adapters._runtime_diagnostic.reset(token)
    assert diagnostic["processes_observed"] is None, "Uninstrumented lsof process count must remain unknown."


def test_unavailable_runtime_visibility_preserves_released_creator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle import adapters
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    monkeypatch.setattr(adapters, "_runtime_state", lambda path: (False, False))
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained"
    assert result.reason == "creator_operation_unsupported"
    assert Path(owner.identity.path).exists()
    assert git(repo, "rev-parse", "refs/heads/task") == owner.identity.head


@pytest.mark.parametrize("kind", ["dirty", "ignored", "nested"])
def test_completed_creator_preserves_late_local_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, _ = managed_owner(tmp_path, monkeypatch)
    path = Path(owner.identity.path)
    with owner.producer():
        if kind == "ignored":
            (path / ".gitignore").write_text("valuable.bin\n")
            git(path, "add", ".gitignore")
            git(path, "commit", "-m", "ignore build data")
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    if kind == "nested":
        nested = path / "child"
        nested.mkdir()
        git(nested, "init")
    else:
        (path / ("valuable.bin" if kind == "ignored" else "unfinished.md")).write_text("preserve")
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained"
    assert path.exists()


def test_new_producer_cannot_reacquire_released_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.state import StateError

    owner, _, _, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    with pytest.raises(StateError, match="released"), owner.producer():
        pytest.fail("Released owner admitted a new producer")


def test_failed_producer_is_not_implicitly_released(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.state import StateError

    owner, _, events, _ = managed_owner(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match="producer failed"), owner.producer():
        raise RuntimeError("producer failed")
    with pytest.raises(StateError, match="successful producer"):
        owner.complete(pr=9)
    assert events == []


def test_creator_persists_creation_custody_before_git_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle import adapters

    from kernel.git import run_git

    original = run_git

    def inspect_before_effect(repo: Path, *args: str, **kwargs: Any) -> GitResult:
        if args[:2] == ("worktree", "add"):
            records = list((tmp_path / "ledger").glob("creator-*.json"))
            assert len(records) == 1, "Creation must have durable custody before Git runs"
            assert json.loads(records[0].read_text())["status"] == "creating"
        return original(repo, *args, **kwargs)

    monkeypatch.setattr(adapters, "run_git", inspect_before_effect)
    managed_owner(tmp_path, monkeypatch)


def test_creator_authority_rejects_duplicate_history_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.state import StateError

    owner, ledger, _, _ = managed_owner(tmp_path, monkeypatch)
    record = next(ledger.root.glob("creator-*.json"))
    raw = record.read_text()
    record.write_text('{"status":"active",' + raw[1:])
    with pytest.raises(StateError, match="duplicate|invalid"):
        _ = owner.identity


def test_active_creator_cannot_carry_released_proof(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.state import StateError

    owner, ledger, _, _ = managed_owner(tmp_path, monkeypatch)
    record = next(ledger.root.glob("creator-*.json"))
    data = json.loads(record.read_text())
    data["release_id"] = "forged-release"
    record.write_text(json.dumps(data))
    with pytest.raises(StateError, match="invalid"):
        _ = owner.identity


def test_creator_owns_and_joins_the_actual_producer_before_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    owner, _, events, _ = managed_owner(tmp_path, monkeypatch)
    path = Path(owner.identity.path)
    script = "import time; from pathlib import Path; time.sleep(.05); Path('joined.md').write_text('finished')"
    owner.run_producer([sys.executable, "-c", script], timeout=5)
    assert (path / "joined.md").read_text() == "finished"
    assert events == []
    owner.complete(pr=9)
    assert len(events) == 1


def test_leaving_a_lease_alone_does_not_certify_a_joined_producer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.state import StateError

    owner, _, events, _ = managed_owner(tmp_path, monkeypatch)
    with owner.producer():
        pass
    with pytest.raises(StateError, match="successful producer"):
        owner.complete(pr=9)
    assert events == []


def test_timed_out_owned_producer_is_joined_without_releasing_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.state import StateError

    owner, _, events, _ = managed_owner(tmp_path, monkeypatch)
    with pytest.raises(StateError, match="producer"):
        owner.run_producer([sys.executable, "-c", "import time; time.sleep(20)"], timeout=0.05)
    with pytest.raises(StateError, match="released|unavailable|producer"):
        owner.complete(pr=9)
    assert events == []
    assert Path(owner.identity.path).is_dir()


def test_reaped_producer_never_authorizes_later_process_group_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle import adapters

    # A real joined child proves this boundary without pretending a namespace
    # object is a Popen or manufacturing authority for an arbitrary live PID.
    reaped = subprocess.Popen([sys.executable, "-c", "pass"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        reaped.wait(timeout=5)
    finally:
        if reaped.poll() is None:
            reaped.kill()
            reaped.wait(timeout=5)
    signals: list[object] = []
    monkeypatch.setattr(adapters, "signal_owned_process_tree", lambda *args, **kwargs: signals.append(kwargs))
    monkeypatch.setattr(os, "killpg", lambda *args: signals.append(args))
    adapters.ManagedGitCreator._stop_producer(reaped)
    assert signals == [], "A reaped PID/PGID is no longer owned signalling authority"


def test_creator_hold_bounds_actual_git_observation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os
    import time
    from kernel.git import GitCommandError

    owner, _, _, _ = managed_owner(tmp_path, monkeypatch)
    monkeypatch.setattr(owner, "operation_timeout", 0.1, raising=False)
    tools = tmp_path / "tools"
    tools.mkdir()
    tool = tools / "git"
    tool.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(20)\n")
    tool.chmod(0o700)
    monkeypatch.setenv("PATH", str(tools) + os.pathsep + os.environ["PATH"])
    expected = owner.identity
    before = time.monotonic()
    with pytest.raises(GitCommandError), owner.hold(expected):
        owner.inspect(expected)
    assert time.monotonic() - before < 2


@pytest.mark.parametrize("field", ["release_id", "delivery_id", "evidence_sha256"])
def test_recovery_requires_original_creator_receipt_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    from dataclasses import replace
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    intent = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert intent.status == "retired", json.dumps({"reason": intent.reason, "runtime_diagnostic": owner.runtime_diagnostic}, sort_keys=True)
    with owner.hold(owner.identity):
        assert owner.recover(intent).result.status == "retired"
        assert owner.recover(replace(intent, **{field: "f" * 64 if field == "evidence_sha256" else "other-receipt"})).result.status == "unknown"


@pytest.mark.parametrize("mutation", ["generation", "remote_disposition"])
def test_creator_history_cannot_impersonate_another_generation_or_remote_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    from specify_cli.workspace_lifecycle.state import StateError

    owner, ledger, _, _ = managed_owner(tmp_path, monkeypatch)
    record = next(ledger.root.glob("creator-*.json"))
    data = json.loads(record.read_text())
    if mutation == "generation":
        data["identity"]["workspace_generation"] = "other-generation"
    else:
        data["branch_disposition"] = "local_retired;remote_retired"
    record.write_text(json.dumps(data))
    with pytest.raises(StateError, match="Creator|creator"):
        _ = owner.identity


def test_joined_owner_release_does_not_wait_for_delivery_or_run_network_inline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    owner, _, events, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        pytest.fail("Completion must persist release/enqueue; delivery belongs to worker")

    monkeypatch.setattr(owner.delivery, "verify_current", forbidden)
    owner.complete(pr=9)
    assert len(events) == 1
    assert Path(owner.identity.path).exists()


def test_released_owner_waits_safely_for_accepted_delivery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    original = owner.delivery.verify_current
    monkeypatch.setattr(owner.delivery, "verify_current", lambda *args: None)
    owner.complete(pr=9)
    coordinator = Coordinator(ledger)
    result = coordinator.reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained" and result.reason == "delivery_missing", json.dumps(
        {"reason": result.reason, "runtime_diagnostic": owner.runtime_diagnostic}, sort_keys=True
    )
    assert Path(owner.identity.path).exists()
    monkeypatch.setattr(owner.delivery, "verify_current", original)
    assert coordinator.reconcile("accepted-later", owner.identity, owner).status == "retired"


def test_creator_never_admits_primary_even_with_empty_protection_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.git.protection_policy import ProtectionPolicy
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery, ManagedGitCreator
    from specify_cli.workspace_lifecycle.state import StateError

    _, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/release")
    monkeypatch.setattr(ProtectionPolicy, "resolve", lambda _: ProtectionPolicy(frozenset(), True))
    before = set(ledger.root.iterdir())
    with pytest.raises(StateError, match="Protected branch"):
        ManagedGitCreator.create(
            ledger,
            repo_root=repo,
            path=tmp_path / "primary",
            branch="release",
            repository="crucible-energy/example",
            repository_id=7,
            delivery=GitHubDelivery(timeout=1),
            on_complete=events.append,
        )
    assert not (tmp_path / "primary").exists()
    assert set(ledger.root.iterdir()) == before


def test_joined_producer_reports_allocated_pr_without_predicting_number(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    owner, _, _, _ = managed_owner(tmp_path, monkeypatch)
    script = (
        "import os; p=os.environ['SPEC_KITTY_LIFECYCLE_RESULT']; fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.write(fd,b'{\"pr\":9}'); os.close(fd)"
    )
    owner.run_producer([sys.executable, "-c", script], timeout=5)
    owner.complete()
    assert owner.identity.path
    assert json.loads(owner._path.read_text())["pr"] == 9


def test_allocated_pr_result_never_accepts_duplicate_authority_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.state import StateError

    owner, _, _, _ = managed_owner(tmp_path, monkeypatch)
    script = (
        "import os; fd=os.open(os.environ['SPEC_KITTY_LIFECYCLE_RESULT'],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); "
        'os.write(fd,b\'{"pr":9,"pr":10}\'); os.close(fd)'
    )
    owner.run_producer([sys.executable, "-c", script], timeout=5)
    with pytest.raises(StateError, match="producer PR"):
        owner.complete()


def test_same_commit_on_another_pr_branch_is_not_creator_delivery(monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery

    responses(monkeypatch)
    transport = subprocess.run

    def wrong_branch(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        result = transport(argv, **kwargs)
        if argv[-1].endswith("/pulls/9"):
            data = json.loads(result.stdout)
            data["head"]["ref"] = "unrelated-branch"
            result.stdout = json.dumps(data).encode()
        return result

    monkeypatch.setattr(subprocess, "run", wrong_branch)
    assert GitHubDelivery(timeout=1).verify(identity(), 9) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 2),
        ("identity", []),
        ("device", -1),
        ("repo_root", "relative"),
        ("release_hash", "not-a-digest"),
        ("status", "unknown-status"),
        ("producer_succeeded", "true"),
        ("release_cap", 9),
        ("pr", True),
        ("schema_version", True),
    ],
)
def test_malformed_creator_fields_never_establish_owner_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object) -> None:
    from specify_cli.workspace_lifecycle.state import StateError

    owner, _, _, _ = managed_owner(tmp_path, monkeypatch)
    data = json.loads(owner._path.read_text())
    data[field] = value
    owner._path.write_text(json.dumps(data))
    with pytest.raises(StateError, match="history"):
        _ = owner.identity


def test_squash_retirement_restores_exact_unique_source_after_local_branch_removal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    path = Path(owner.identity.path)
    base = git(repo, "rev-parse", "main")
    script = (
        "from pathlib import Path; import subprocess; Path('useful.md').write_text('unique useful result'); "
        "subprocess.run(['git','add','useful.md'],check=True); subprocess.run(['git','commit','-m','unique source'],check=True)"
    )
    owner.run_producer([sys.executable, "-c", script], timeout=5)
    source = git(path, "rev-parse", "HEAD")
    source_tree = git(path, "rev-parse", "HEAD^{tree}")
    squash = git(repo, "commit-tree", source_tree, "-p", base, "-m", "accepted squash delivery")
    assert squash != source
    git(repo, "push", str(tmp_path / "origin.git"), squash + ":refs/heads/main")
    owner.complete(pr=9)
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retired"
    assert not path.exists() and not git(repo, "branch", "--list", "task")
    manifests = list(ledger.root.glob("recovery-*.json"))
    assert len(manifests) == 1
    proof = json.loads(manifests[0].read_text())
    assert proof["restore_verified"] is True
    assert proof["source"]["head"] == source and proof["source_tree"] == source_tree
    assert git(repo, "rev-parse", proof["recovery_ref"]) == source
    # A clean consumer can independently restore the retained source, not just
    # read an API response or locally verify a bundle prerequisite header.
    restored = tmp_path / "restored"
    git(repo, "clone", "--no-local", "--single-branch", "--branch", proof["recovery_ref"].removeprefix("refs/heads/"), str(repo), str(restored))
    assert git(restored, "rev-parse", "HEAD") == source
    assert git(restored, "rev-parse", "HEAD^{tree}") == source_tree
    assert (restored / "useful.md").read_text() == "unique useful result"
    assert git(repo, "rev-parse", "main") == base


@pytest.mark.parametrize("disposition", ["unresolved", "unavailable", "advanced_source", "missing_source_observation"])
def test_current_review_and_remote_source_disposition_is_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, disposition: str) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery

    owner, ledger, events, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    original = GitHubDelivery._get

    def response(endpoint: str, deadline: float, *, query: str | None = None) -> dict[str, object]:
        data = original(endpoint, deadline, query=query)
        if endpoint == "graphql":
            pull = object_at(data, "data", "repository", "pullRequest")
            if disposition == "unresolved":
                pull["reviewThreads"]["nodes"] = [{"id": "thread1", "isResolved": False}]
            elif disposition == "unavailable":
                data["errors"] = [{"message": "read refused"}]
            elif disposition == "advanced_source":
                pull["headRef"] = {"target": {"oid": "c" * 40}}
            else:
                pull.pop("headRef")
        return data

    monkeypatch.setattr(GitHubDelivery, "_get", staticmethod(response))
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained" and result.reason == "delivery_missing", json.dumps(
        {"reason": result.reason, "runtime_diagnostic": owner.runtime_diagnostic}, sort_keys=True
    )
    assert Path(owner.identity.path).exists()
    assert not list(ledger.root.glob("recovery-*.json"))


def test_failed_source_recovery_never_removes_checkout_or_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator
    from specify_cli.workspace_lifecycle import adapters
    from specify_cli.git.ref_advance import RefAdvanceError

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)

    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise RefAdvanceError("injected exact ref persistence failure")

    monkeypatch.setattr(adapters, "advance_branch_ref", refuse)
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained" and result.reason == "exact_source_recovery_unconfirmed"
    assert Path(owner.identity.path).exists()
    assert git(repo, "rev-parse", "task") == owner.identity.head
    assert json.loads(next(ledger.root.glob("recovery-*.json")).read_text())["restore_verified"] is False


def test_replace_refs_cannot_fabricate_default_delivery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    source = Path(owner.identity.path)
    base = git(repo, "rev-parse", "HEAD")
    program = (
        "from pathlib import Path; import subprocess; Path('useful.md').write_text('not delivered'); "
        "subprocess.run(['git','add','useful.md'],check=True); subprocess.run(['git','commit','-m','source not delivered'],check=True)"
    )
    owner.run_producer([sys.executable, "-c", program], timeout=5)
    tree = git(source, "rev-parse", "HEAD^{tree}")
    replacement = git(repo, "commit-tree", tree, "-m", "local replacement fabricates merge tree")
    git(repo, "replace", base, replacement)
    owner.complete(pr=9)
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained", "Local replace refs must not fabricate accepted default content."
    assert source.exists()


def test_grafted_graph_is_retained_without_treating_it_as_delivery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    graft = repo / ".git" / "info" / "grafts"
    graft.write_text(owner.identity.head + "\n")
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained" and Path(owner.identity.path).exists()
    assert graft.read_text() == owner.identity.head + "\n"


@pytest.mark.parametrize("case", ["complete", "cycle", "exhausted", "malformed", "changed_head"])
def test_review_pagination_never_turns_partial_or_changed_evidence_into_disposition(monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    import time
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery

    calls = []

    def page(endpoint: str, deadline: float, *, query: str | None = None) -> dict[str, object]:
        calls.append(query)
        index = len(calls)
        pull: dict[str, Any] = {
            "headRefOid": "a" * 40,
            "headRef": None,
            "mergeCommit": {"oid": "b" * 40},
            "reviewThreads": {
                "nodes": [{"id": "thread" + str(index), "isResolved": True}],
                "pageInfo": {"hasNextPage": index == 1, "endCursor": "page" + str(index)},
            },
        }
        if case == "cycle":
            pull["reviewThreads"]["pageInfo"] = {"hasNextPage": True, "endCursor": "same"}
        elif case == "exhausted":
            pull["reviewThreads"]["pageInfo"]["hasNextPage"] = True
        elif case == "malformed":
            pull["reviewThreads"] = {"nodes": None}
        elif case == "changed_head":
            pull["headRefOid"] = "c" * 40
        return {"data": {"repository": {"databaseId": 7, "pullRequest": pull}}}

    monkeypatch.setattr(GitHubDelivery, "_get", staticmethod(page))
    result = GitHubDelivery()._reviews(identity(), 9, "b" * 40, time.monotonic() + 5)
    if case == "complete":
        assert result == [{"id": "thread1", "isResolved": True}, {"id": "thread2", "isResolved": True}]
        second_query = calls[1]
        assert second_query is not None
        assert 'after:"page1"' in second_query
    else:
        assert result is None
    assert len(calls) <= 10


@pytest.mark.parametrize("case", ["none", "cwd", "exe", "file", "denied", "denied_cwd", "denied_exe", "denied_files", "exited", "other_user", "expired", "empty"])
def test_linux_runtime_guard_preserves_dependencies_and_unknown_visibility(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    import os
    import time
    from types import SimpleNamespace
    from specify_cli.workspace_lifecycle import adapters
    import psutil

    class Process:
        pid = 123

        def uids(self) -> SimpleNamespace:
            if case == "denied":
                raise psutil.AccessDenied(123)
            if case == "exited":
                raise psutil.NoSuchProcess(123)
            uid = os.getuid() + (case == "other_user")
            return SimpleNamespace(real=uid, effective=uid, saved=uid)

        def status(self) -> str:
            return "sleeping"

        def cwd(self) -> str:
            if case == "denied_cwd":
                raise psutil.AccessDenied(123)
            return str(tmp_path) if case == "cwd" else "/unrelated"

        def exe(self) -> str:
            if case == "denied_exe":
                raise psutil.AccessDenied(123)
            return str(tmp_path / "tool") if case == "exe" else "/unrelated/tool"

        def open_files(self) -> list[SimpleNamespace]:
            if case == "denied_files":
                raise psutil.AccessDenied(123)
            return [SimpleNamespace(path=str(tmp_path / "data"))] if case == "file" else []

    monkeypatch.setattr(adapters, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([] if case == "empty" else [Process()]))
    if case == "expired":
        monkeypatch.setattr(adapters, "process_deadline", lambda: time.monotonic() - 1)
    diagnostic: dict[str, object] = {}
    token = adapters._runtime_diagnostic.set(diagnostic)
    try:
        actual = adapters._runtime_state(tmp_path)
    finally:
        adapters._runtime_diagnostic.reset(token)
    assert actual == (
        (True, True)
        if case in {"cwd", "exe", "file"}
        else (False, False)
        if case in {"denied", "denied_cwd", "denied_exe", "denied_files", "expired"}
        else (False, True)
    )
    assert diagnostic["provider"] == "psutil"
    assert diagnostic["complete"] is actual[1]
    assert diagnostic["processes_observed"] == (0 if case == "empty" else 1)
    if case.startswith("denied"):
        assert diagnostic["stage"] == {"denied": "uids", "denied_cwd": "cwd", "denied_exe": "exe", "denied_files": "open_files"}[case]
        assert diagnostic["error_type"] == "AccessDenied"
        denied = object_at(diagnostic, "denied_process_observation")
        assert denied["pid"] == 123
        assert denied["state"] == "sleeping" and denied["state_observation"] == "observed"
        assert denied["uid_matches_owner"] == dict.fromkeys(("real", "effective", "saved"), None if case == "denied" else True)
    else:
        assert "denied_process_observation" not in diagnostic
    if case == "expired":
        assert diagnostic["outcome"] == "budget_exhausted"
    assert str(tmp_path) not in json.dumps(diagnostic)
    assert adapters._runtime_diagnostic.get() is None


@pytest.mark.parametrize("case", ["zombie", "gone", "state_denied", "invalid_state", "effective_other", "invalid_pid", "deadline", "timed_state", "no_context"])
def test_denied_process_observation_never_grants_visibility(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    import time
    from types import SimpleNamespace

    import psutil

    from specify_cli.workspace_lifecycle import adapters

    clock = [10.0]
    state_calls: list[int] = []

    class Process:
        pid = True if case == "invalid_pid" else 321

        def uids(self) -> SimpleNamespace:
            return SimpleNamespace(real=1000, effective=1001 if case == "effective_other" else 1000, saved=1000)

        def cwd(self) -> NoReturn:
            if case == "deadline":
                clock[0] = 16.0
            raise psutil.AccessDenied(321, name=str(tmp_path))

        def status(self) -> str:
            state_calls.append(321)
            if case == "timed_state":
                clock[0] = 12.0
            if case == "gone":
                raise psutil.NoSuchProcess(321)
            if case == "state_denied":
                raise psutil.AccessDenied(321, name=str(tmp_path))
            return str(tmp_path) if case == "invalid_state" else "zombie" if case == "zombie" else "sleeping"

    monkeypatch.setattr(adapters, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([Process()]))
    if case in {"deadline", "timed_state"}:
        monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    diagnostic: dict[str, object] = {}
    token = adapters._runtime_diagnostic.set(None if case == "no_context" else diagnostic)
    try:
        assert adapters._runtime_state(tmp_path) == (False, False)
        if case == "no_context":
            assert not state_calls and not diagnostic
            return
        denied = object_at(diagnostic, "denied_process_observation")
        assert denied["pid"] == (None if case == "invalid_pid" else 321)
        assert object_at(denied, "uid_matches_owner") == {"real": True, "effective": case != "effective_other", "saved": True}
        assert denied["state_observation"] == (
            "unavailable" if case in {"gone", "state_denied"} else "invalid" if case == "invalid_state" else "deadline" if case == "deadline" else "observed"
        )
        if case in {"gone", "state_denied"}:
            assert denied["state"] is None
            assert denied["state_error_type"] == ("NoSuchProcess" if case == "gone" else "AccessDenied")
        if case == "deadline":
            assert not state_calls and denied["state"] is None
        if case == "zombie":
            assert denied["state"] == "zombie"
        if case == "timed_state":
            assert diagnostic["elapsed_seconds"] == 2.0
        assert str(tmp_path) not in json.dumps(diagnostic)
        monkeypatch.setattr(psutil, "process_iter", lambda: iter([]))
        assert adapters._runtime_state(tmp_path) == (False, True)
        assert "denied_process_observation" not in diagnostic
    finally:
        adapters._runtime_diagnostic.reset(token)


@pytest.mark.parametrize("case", ["owner", "root", "foreign", "unavailable", "gone", "deadline", "no_context", "invalid_pid", "timed_probe", "state_deadline"])
def test_denied_process_directory_observation_is_bounded_and_non_authoritative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    import time
    from types import SimpleNamespace

    import psutil

    from specify_cli.workspace_lifecycle import adapters

    clock = [10.0]
    probes: list[int] = []

    class Process:
        pid = True if case == "invalid_pid" else 321

        def uids(self) -> SimpleNamespace:
            return SimpleNamespace(real=1000, effective=1000, saved=1000)

        def cwd(self) -> NoReturn:
            if case == "deadline":
                clock[0] = 16.0
            raise psutil.AccessDenied(321, name=str(tmp_path))

        def status(self) -> str:
            if case == "gone":
                raise psutil.NoSuchProcess(321)
            if case == "state_deadline":
                clock[0] = 16.0
            return "sleeping"

    def process_directory_owner(pid: int) -> int:
        probes.append(pid)
        if case == "unavailable":
            raise PermissionError(str(tmp_path))
        if case == "timed_probe":
            clock[0] = 12.5
        return 0 if case == "root" else 2000 if case == "foreign" else 1000

    monkeypatch.setattr(adapters, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(psutil, "process_iter", lambda: iter([Process()]))
    monkeypatch.setattr(adapters, "_process_directory_owner", process_directory_owner, raising=False)
    diagnostic: dict[str, object] = {}
    token = adapters._runtime_diagnostic.set(None if case == "no_context" else diagnostic)
    try:
        assert adapters._runtime_state(tmp_path) == (False, False)
        if case == "no_context":
            assert not diagnostic and not probes
            return
        directory = object_at(object_at(diagnostic, "denied_process_observation"), "process_directory")
        if case in {"deadline", "state_deadline", "gone", "invalid_pid"}:
            assert not probes
            assert directory == {"observation": "process_unavailable" if case == "gone" else "invalid_pid" if case == "invalid_pid" else "deadline"}
        else:
            assert probes == [321]
            if case == "unavailable":
                assert directory == {"observation": "unavailable", "error_type": "PermissionError"}
            else:
                assert directory == {"observation": "observed", "owner_uid_matches": case != "root" and case != "foreign", "root_uid_matches": case == "root"}
        if case == "timed_probe":
            assert diagnostic["elapsed_seconds"] == 2.5
        assert str(tmp_path) not in json.dumps(diagnostic)
        monkeypatch.setattr(psutil, "process_iter", lambda: iter([]))
        assert adapters._runtime_state(tmp_path) == (False, True)
        assert "denied_process_observation" not in diagnostic
    finally:
        adapters._runtime_diagnostic.reset(token)


def test_process_directory_owner_observes_only_a_real_pid_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import psutil

    from specify_cli.workspace_lifecycle import adapters

    process_directory = tmp_path / "321"
    process_directory.mkdir()
    (tmp_path / "322").symlink_to(process_directory, target_is_directory=True)
    monkeypatch.setattr(psutil, "PROCFS_PATH", str(tmp_path), raising=False)
    assert adapters._process_directory_owner(321) == process_directory.lstat().st_uid
    for invalid_pid in (True, 0, -1):
        with pytest.raises(ValueError, match="Process directory observation unavailable"):
            adapters._process_directory_owner(invalid_pid)
    with pytest.raises(ValueError, match="Process directory observation unavailable"):
        adapters._process_directory_owner(322)
    monkeypatch.setattr(psutil, "PROCFS_PATH", "relative/proc")
    with pytest.raises(ValueError, match="Process directory observation unavailable"):
        adapters._process_directory_owner(321)


@pytest.mark.parametrize("previous", ["exited", "other_user"])
def test_enumeration_failure_does_not_attribute_the_previous_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, previous: str) -> None:
    from collections.abc import Iterator
    from types import SimpleNamespace

    import psutil

    from specify_cli.workspace_lifecycle import adapters

    class Process:
        pid = 777

        def uids(self) -> SimpleNamespace:
            if previous == "exited":
                raise psutil.NoSuchProcess(777)
            return SimpleNamespace(real=1001)

        def status(self) -> NoReturn:
            pytest.fail("A failed enumeration cannot inspect the preceding process.")

    def processes() -> Iterator[Process]:
        yield Process()
        raise psutil.AccessDenied(None)

    monkeypatch.setattr(adapters, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(psutil, "process_iter", processes)
    diagnostic: dict[str, object] = {}
    token = adapters._runtime_diagnostic.set(diagnostic)
    try:
        assert adapters._runtime_state(tmp_path) == (False, False)
    finally:
        adapters._runtime_diagnostic.reset(token)
    assert diagnostic["stage"] == "enumeration"
    assert "denied_process_observation" not in diagnostic


def test_shallow_recovery_obligation_preserves_checkout_and_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    (repo / ".git" / "shallow").write_text(owner.identity.head + "\n")
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained" and Path(owner.identity.path).exists()
    assert git(repo, "rev-parse", "task") == owner.identity.head


def test_source_advanced_during_recovery_is_retained_with_old_ancestry_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    original = owner._recovery
    path = Path(owner.identity.path)

    def recover_then_advance(state: _OwnerState, intent: Operation, *, create: bool) -> bool:
        result = original(state, intent, create=create)
        if create and result:
            git(path, "commit", "--allow-empty", "-m", "new owner work after recovery")
        return result

    monkeypatch.setattr(owner, "_recovery", recover_then_advance)
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained" and path.exists()
    proof = json.loads(next(ledger.root.glob("recovery-*.json")).read_text())
    assert git(repo, "rev-parse", proof["recovery_ref"]) == owner.identity.head
    assert git(path, "rev-parse", "HEAD") != owner.identity.head


@pytest.mark.parametrize("phase", ["before_retire", "after_recovery"])
def test_new_live_holder_at_retirement_boundary_is_preserved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    import select
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, _ = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    children = []

    def start() -> None:
        child = subprocess.Popen([sys.executable, "-c", "import time; print('ready',flush=True); time.sleep(30)"], cwd=owner.identity.path, stdout=subprocess.PIPE)
        children.append(child)
        assert child.stdout is not None
        assert select.select([child.stdout], [], [], 5)[0]
        assert child.stdout.readline().strip() == b"ready"

    if phase == "before_retire":
        original = owner.retire

        def retire(intent: Operation) -> Result:
            start()
            return original(intent)

        monkeypatch.setattr(owner, "retire", retire)
    else:
        original_recovery = owner._recovery

        def recover(state: _OwnerState, intent: Operation, *, create: bool) -> bool:
            result = original_recovery(state, intent, create=create)
            if create and result:
                start()
            return result

        monkeypatch.setattr(owner, "_recovery", recover)
    try:
        result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
        assert result.status == "retained" and Path(owner.identity.path).exists()
    finally:
        for child in children:
            child.terminate()
            child.wait(timeout=5)
            if child.stdout:
                child.stdout.close()


def test_borrowed_object_store_requires_separate_custody(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    objects = repo / ".git" / "objects"
    borrowed = tmp_path / "separate-owner-objects"
    objects.rename(borrowed)
    (objects / "info").mkdir(parents=True)
    (objects / "info" / "alternates").write_text(str(borrowed) + "\n")
    assert "alternate:" in git(repo, "count-objects", "-v")
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained", "Local recovery ref does not retain a separately owned alternate store."
    assert Path(owner.identity.path).exists()


@pytest.mark.parametrize("metadata", ["config", "promisor_pack", "objects_symlink"])
def test_partial_or_external_store_is_retained_until_full_recovery_is_proved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, metadata: str) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    objects = repo / ".git" / "objects"
    if metadata == "config":
        git(repo, "config", "remote.origin.promisor", "true")
    elif metadata == "promisor_pack":
        (objects / "pack").mkdir(exist_ok=True)
        (objects / "pack" / "unresolved.promisor").write_bytes(b"")
    else:
        borrowed = tmp_path / "borrowed-objects"
        objects.rename(borrowed)
        objects.symlink_to(borrowed, target_is_directory=True)
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained" and Path(owner.identity.path).exists()
    assert git(repo, "rev-parse", "task") == owner.identity.head


def test_current_source_branch_is_retained_remotely_after_local_retirement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    git(repo, "push", str(tmp_path / "origin.git"), "task:refs/heads/task")
    owner.complete(pr=9)
    original = GitHubDelivery._get

    def current(endpoint: str, deadline: float, *, query: str | None = None) -> dict[str, object]:
        data = original(endpoint, deadline, query=query)
        if endpoint == "graphql":
            object_at(data, "data", "repository", "pullRequest")["headRef"] = {"target": {"oid": owner.identity.head}}
        return data

    monkeypatch.setattr(GitHubDelivery, "_get", staticmethod(current))
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retired" and not Path(owner.identity.path).exists()
    assert git(tmp_path / "origin.git", "rev-parse", "task") == owner.identity.head
    assert not git(repo, "branch", "--list", "task")


@pytest.mark.parametrize("shape", ["pack_directory", "pack_file", "pack_index", "loose_object", "info_directory"])
def test_nested_external_object_storage_is_not_retained_by_a_local_ref(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shape: str) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    objects = repo / ".git" / "objects"
    external = tmp_path / "separate-object-storage"
    if shape.startswith("pack_"):
        git(repo, "repack", "-ad")
        pack = objects / "pack"
        if shape == "pack_directory":
            pack.rename(external)
            pack.symlink_to(external, target_is_directory=True)
        else:
            external.mkdir()
            suffix = ".pack" if shape == "pack_file" else ".idx"
            original = next(pack.glob("*" + suffix))
            target = external / original.name
            original.rename(target)
            original.symlink_to(target)
    elif shape == "loose_object":
        original = objects / owner.identity.head[:2] / owner.identity.head[2:]
        original.rename(external)
        original.symlink_to(external)
    else:
        original = objects / "info"
        original.rename(external)
        original.symlink_to(external, target_is_directory=True)
    assert git(repo, "cat-file", "-t", owner.identity.head) == "commit"
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retained" and Path(owner.identity.path).exists()
    assert git(repo, "rev-parse", "task") == owner.identity.head
    assert external.exists()
    assert not list(ledger.root.glob("recovery-*.json"))


def test_regular_hardlinked_packs_retain_their_own_inode_after_retirement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)
    git(repo, "repack", "-ad")
    external = tmp_path / "other-link"
    external.mkdir()
    for file in (repo / ".git" / "objects" / "pack").iterdir():
        os.link(file, external / file.name)
        assert file.stat().st_nlink >= 2
    result = Coordinator(ledger).reconcile(events[0].event_id, owner.identity, owner)
    assert result.status == "retired" and not Path(owner.identity.path).exists()
    for file in external.iterdir():
        file.unlink()
    proof = json.loads(next(ledger.root.glob("recovery-*.json")).read_text())
    assert git(repo, "cat-file", "-t", proof["recovery_ref"]) == "commit"
    assert git(repo, "rev-parse", proof["recovery_ref"]) == owner.identity.head


def test_worker_explains_visibility_retention_without_authorizing_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle import adapters
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    owner, ledger, _, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)

    def unavailable(path: Path) -> tuple[bool, bool]:
        diagnostic = adapters._runtime_diagnostic.get()
        assert diagnostic is not None
        diagnostic.update(provider="psutil", stage="open_files", error_type="AccessDenied", complete=False)
        return False, False

    monkeypatch.setattr(adapters, "_runtime_state", unavailable)
    report = LifecycleService(ledger).run()
    rows = report["results"]
    assert isinstance(rows, list)
    row = rows[-1]
    assert row["status"] == "retained" and row["reason"] == "creator_operation_unsupported"
    assert object_at(row, "runtime_diagnostic")["error_type"] == "AccessDenied"
    assert adapters._runtime_diagnostic.get() is None
    assert Path(owner.identity.path).exists()
    assert git(repo, "rev-parse", "task") == owner.identity.head
    assert not list(ledger.root.glob("recovery-*.json"))


def test_unsupported_runtime_provider_has_unknown_process_count(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    from specify_cli.workspace_lifecycle import adapters

    monkeypatch.setattr(adapters, "sys", SimpleNamespace(platform="unsupported"))
    diagnostic: dict[str, object] = {}
    token = adapters._runtime_diagnostic.set(diagnostic)
    try:
        assert adapters._runtime_state(Path("/unobserved")) == (False, False)
    finally:
        adapters._runtime_diagnostic.reset(token)
    assert diagnostic["processes_observed"] is None


def test_metadata_failure_does_not_relabel_checkout_process_measurements(monkeypatch: pytest.MonkeyPatch) -> None:
    from kernel.git import GitResult
    from specify_cli.workspace_lifecycle import adapters

    diagnostic: dict[str, object] = {}

    def visible(path: Path) -> tuple[bool, bool]:
        diagnostic.update(provider="psutil", processes_observed=17, elapsed_seconds=0.25)
        return False, True

    monkeypatch.setattr(adapters, "_runtime_state", visible)
    monkeypatch.setattr(adapters, "run_git", lambda *args, **kwargs: GitResult(0, b"relative-metadata\n", b""))
    token = adapters._runtime_diagnostic.set(diagnostic)
    try:
        assert adapters._creator_runtime_state(identity()) == (False, False)
    finally:
        adapters._runtime_diagnostic.reset(token)
    assert diagnostic["scope"] == "git_admin"
    assert diagnostic["processes_observed"] is None
    assert diagnostic["elapsed_seconds"] is None
