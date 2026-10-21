"""Creator/delivery acceptance through real local Git and bounded API seams."""

from __future__ import annotations

import json
import subprocess
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
                "head": {"sha": head, "repo": {"id": 7, "full_name": "crucible-energy/example"}},
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
        if argv[-1].endswith("/pulls/9"):
            value = {
                "number": 9,
                "merged": True,
                "state": "closed",
                "merged_at": "2026-10-20T00:00:00Z",
                "merge_commit_sha": "b" * 40,
                "head": {"sha": owner.identity.head, "repo": {"id": 7, "full_name": "crucible-energy/example"}},
                "base": {"ref": "main", "repo": {"id": 7, "full_name": "crucible-energy/example"}},
            }
        else:
            value = {"id": 7, "full_name": "crucible-energy/example", "default_branch": "main"}
        return subprocess.CompletedProcess(argv, 0, json.dumps(value).encode(), b"")

    monkeypatch.setattr(subprocess, "run", transport)
    return owner, ledger, events, repo


def test_owned_non_lane_producer_releases_then_real_worktree_retires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.coordinator import Coordinator

    owner, ledger, events, repo = managed_owner(tmp_path, monkeypatch)
    path = Path(owner.identity.path)
    with owner.producer():
        (path / "result.md").write_text("delivered result\n")
        git(path, "add", "result.md")
        git(path, "commit", "-m", "result")
    owner.complete(pr=9)
    assert len(events) == 1
    assert path.exists(), "Completion callback must not retire inline"
    coordinator = Coordinator(ledger)
    coordinator.account_owned(owner.identity, owner)
    assert coordinator.reconcile(events[0].event_id, owner.identity, owner).status == "retired"
    assert not path.exists()
    assert git(repo, "branch", "--list", "task") == ""
    assert owner.branch_disposition == "local_retired;remote_retained"


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
    with owner.producer():
        pass
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
    import sys

    owner, _, events, _ = managed_owner(tmp_path, monkeypatch)
    path = Path(owner.identity.path)
    script = "import time; from pathlib import Path; time.sleep(.05); Path('joined.md').write_text('finished')"
    owner.run_producer([sys.executable, "-c", script], timeout=5)
    assert (path / "joined.md").read_text() == "finished"
    assert events == []
    owner.complete(pr=9)
    assert len(events) == 1
