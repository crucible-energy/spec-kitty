"""Creator/delivery acceptance through real local Git and bounded API seams."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from specify_cli.workspace_lifecycle.policy import Identity


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
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=b"private-response")

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


def managed_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
    events = []
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

    def transport(argv, **kwargs):
        if argv[0] != "gh":
            return original_run(argv, **kwargs)
        merge = git(mirror, "rev-parse", "refs/heads/main")
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

    def old_accepted(self, expected, pr, deadline):
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

    monkeypatch.setattr(adapters.sys, "platform", "darwin")
    monkeypatch.setattr(adapters, "bounded_run", observe)
    assert adapters._runtime_state(Path("/private/task")) == expected


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

    original = adapters.run_git

    def inspect_before_effect(repo, *args, **kwargs):
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
    from types import SimpleNamespace
    from specify_cli.workspace_lifecycle import adapters

    signals = []
    monkeypatch.setattr(adapters, "signal_owned_process_tree", lambda *args, **kwargs: signals.append(kwargs))
    monkeypatch.setattr(adapters.os, "killpg", lambda *args: signals.append(args))
    reaped = SimpleNamespace(returncode=0, pid=123456, wait=lambda **kwargs: 0)
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
    assert intent.status == "retired"
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

    def forbidden(*args, **kwargs):
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
    assert result.status == "retained" and result.reason == "delivery_missing"
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

    def wrong_branch(argv, **kwargs):
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
def test_malformed_creator_fields_never_establish_owner_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field, value) -> None:
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

    def response(endpoint, deadline, *, query=None):
        data = original(endpoint, deadline, query=query)
        if endpoint == "graphql":
            pull = data["data"]["repository"]["pullRequest"]
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
    assert result.status == "retained" and result.reason == "delivery_missing"
    assert Path(owner.identity.path).exists()
    assert not list(ledger.root.glob("recovery-*.json"))


def test_failed_source_recovery_never_removes_checkout_or_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator
    from specify_cli.workspace_lifecycle import adapters
    from specify_cli.git.ref_advance import RefAdvanceError

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    owner.run_producer([sys.executable, "-c", "pass"], timeout=5)
    owner.complete(pr=9)

    def refuse(*args, **kwargs):
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

    def page(endpoint, deadline, *, query=None):
        calls.append(query)
        index = len(calls)
        pull = {
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
        assert 'after:"page1"' in calls[1]
    else:
        assert result is None
    assert len(calls) <= 10


@pytest.mark.parametrize("case", ["none", "cwd", "exe", "file", "denied", "exited", "other_user", "expired"])
def test_linux_runtime_guard_preserves_dependencies_and_unknown_visibility(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    import os
    import time
    from types import SimpleNamespace
    from specify_cli.workspace_lifecycle import adapters
    import psutil

    class Process:
        def uids(self):
            if case == "denied":
                raise psutil.AccessDenied(123)
            if case == "exited":
                raise psutil.NoSuchProcess(123)
            return SimpleNamespace(real=os.getuid() + (case == "other_user"))

        def cwd(self):
            return str(tmp_path) if case == "cwd" else "/unrelated"

        def exe(self):
            return str(tmp_path / "tool") if case == "exe" else "/unrelated/tool"

        def open_files(self):
            return [SimpleNamespace(path=str(tmp_path / "data"))] if case == "file" else []

    monkeypatch.setattr(adapters.sys, "platform", "linux")
    monkeypatch.setattr(adapters.os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(adapters.psutil, "process_iter", lambda: iter([Process()]))
    if case == "expired":
        monkeypatch.setattr(adapters, "process_deadline", lambda: time.monotonic() - 1)
    actual = adapters._runtime_state(tmp_path)
    assert actual == ((True, True) if case in {"cwd", "exe", "file"} else (False, False) if case in {"denied", "expired"} else (False, True))


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

    def recover_then_advance(state, intent, *, create):
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

    def start():
        child = subprocess.Popen([sys.executable, "-c", "import time; print('ready',flush=True); time.sleep(30)"], cwd=owner.identity.path, stdout=subprocess.PIPE)
        children.append(child)
        assert child.stdout is not None
        assert select.select([child.stdout], [], [], 5)[0]
        assert child.stdout.readline().strip() == b"ready"

    if phase == "before_retire":
        original = owner.retire

        def retire(intent):
            start()
            return original(intent)

        monkeypatch.setattr(owner, "retire", retire)
    else:
        original_recovery = owner._recovery

        def recover(state, intent, *, create):
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

    def current(endpoint, deadline, *, query=None):
        data = original(endpoint, deadline, query=query)
        if endpoint == "graphql":
            data["data"]["repository"]["pullRequest"]["headRef"] = {"target": {"oid": owner.identity.head}}
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
