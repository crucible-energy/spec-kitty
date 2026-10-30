"""Owned retry commits only its verified lifecycle append."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from mission_runtime import CommitTarget
from specify_cli.cli.commands import _owned_retry_lifecycle as retry
from specify_cli.invocation.lifecycle import write_started

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
_MISSION_ID = "01M66G7P348JGSAP9ZYZQK7WQZ"


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def owned_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "feature/retry", str(root)], check=True)
    _git(root, "config", "user.name", "Retry Fixture")
    _git(root, "config", "user.email", "retry@example.invalid")
    _git(root, "config", "commit.gpgsign", "false")
    lifecycle = root / "kitty-ops" / "lifecycle.jsonl"
    lifecycle.parent.mkdir()
    lifecycle.write_text("")
    (root / ".gitignore").write_text("kitty-specs/mission/private.log\n")
    _git(root, "add", ".gitignore", "kitty-ops/lifecycle.jsonl")
    _git(root, "commit", "-qm", "fixture")
    mission = root / "kitty-specs" / "mission"
    mission.mkdir(parents=True)
    owned = SimpleNamespace(owned_root=root, repository_root=root, mission_dir=mission, mission_slug="mission", write_branch="feature/retry")
    monkeypatch.setattr(retry, "placement_seam", lambda *_args, **_kwargs: SimpleNamespace(write_target=lambda *_args: CommitTarget(ref="feature/retry")))
    monkeypatch.setattr(retry, "resolve_mission_identity", lambda *_args: SimpleNamespace(mission_id=_MISSION_ID))
    return owned, lifecycle, mission


def _append(root: Path) -> None:
    write_started(root, canonical_action_id="implement::implement", agent="agent", mission_id=_MISSION_ID, wp_id="WP01")


def _decision():
    return SimpleNamespace(mission_state="implement", action="implement", wp_id="WP01")


def test_owned_retry_commits_only_its_append_and_preserves_other_work(owned_retry) -> None:
    owned, lifecycle, mission = owned_retry
    unrelated = mission / "draft.md"
    ignored = mission / "private.log"
    untracked = mission / "notes.md"
    unrelated.write_text("staged user work\n")
    ignored.write_text("ignored evidence\n")
    untracked.write_text("untracked user work\n")
    _git(owned.owned_root, "add", str(unrelated.relative_to(owned.owned_root)))
    staged_before = _git(owned.owned_root, "diff", "--cached", "--binary")
    capture = retry.capture_owned_retry_lifecycle(owned)
    try:
        retry.commit_owned_retry_lifecycle(capture, _decision(), "agent")
    finally:
        capture.close()
    assert _git(owned.owned_root, "diff", "--name-only", "HEAD^", "HEAD") == "kitty-ops/lifecycle.jsonl"
    assert _git(owned.owned_root, "diff", "--cached", "--binary") == staged_before
    assert ignored.read_text() == "ignored evidence\n"
    assert untracked.read_text() == "untracked user work\n"
    assert _git(owned.owned_root, "status", "--porcelain", "--", "kitty-ops/lifecycle.jsonl") == ""
    assert lifecycle.read_bytes().startswith(capture.before)


def test_owned_retry_refuses_preexisting_dirty_lifecycle(owned_retry) -> None:
    owned, lifecycle, _mission = owned_retry
    lifecycle.write_text("user's pending record\n")
    with pytest.raises(ValueError, match="dirty"):
        retry.capture_owned_retry_lifecycle(owned)
    assert lifecycle.read_text() == "user's pending record\n"


@pytest.mark.parametrize("conflict", ["staged", "extra_append", "mode"])
def test_owned_retry_preserves_concurrent_lifecycle_conflicts(owned_retry, conflict: str) -> None:
    owned, lifecycle, _mission = owned_retry
    head = _git(owned.owned_root, "rev-parse", "HEAD")
    capture = retry.capture_owned_retry_lifecycle(owned)
    if conflict == "staged":
        _append(owned.owned_root)
        _git(owned.owned_root, "add", "kitty-ops/lifecycle.jsonl")
    elif conflict == "extra_append":
        _append(owned.owned_root)
        _append(owned.owned_root)
    else:
        os.chmod(lifecycle, 0o755)
    before = lifecycle.read_bytes()
    staged = _git(owned.owned_root, "diff", "--cached", "--binary")
    try:
        with pytest.raises(ValueError, match="Retry was issued"):
            retry.commit_owned_retry_lifecycle(capture, _decision(), "agent")
    finally:
        capture.close()
    assert lifecycle.read_bytes() == before
    assert _git(owned.owned_root, "diff", "--cached", "--binary") == staged
    assert _git(owned.owned_root, "rev-parse", "HEAD") == head


@pytest.mark.parametrize("swap", ["record", "directory"])
def test_owned_retry_never_follows_replaced_lifecycle_paths(owned_retry, swap: str) -> None:
    owned, lifecycle, mission = owned_retry
    capture = retry.capture_owned_retry_lifecycle(owned)
    outside = mission / "outside"
    outside.mkdir()
    victim = outside / "lifecycle.jsonl"
    victim.write_text("valuable data\n")
    if swap == "record":
        lifecycle.rename(lifecycle.with_name("original.jsonl"))
        lifecycle.symlink_to(victim)
    else:
        lifecycle.parent.rename(owned.owned_root / "original-kitty-ops")
        lifecycle.parent.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises((OSError, ValueError)):
            retry.commit_owned_retry_lifecycle(capture, _decision(), "agent")
    finally:
        capture.close()
    assert victim.read_text() == "valuable data\n"


def test_owned_retry_can_create_new_unignored_lifecycle_record(owned_retry) -> None:
    owned, lifecycle, _mission = owned_retry
    _git(owned.owned_root, "rm", "-q", "kitty-ops/lifecycle.jsonl")
    _git(owned.owned_root, "commit", "-qm", "remove old lifecycle")
    capture = retry.capture_owned_retry_lifecycle(owned)
    try:
        retry.commit_owned_retry_lifecycle(capture, _decision(), "agent")
    finally:
        capture.close()
    assert lifecycle.is_file()
    assert _git(owned.owned_root, "diff", "--name-only", "HEAD^", "HEAD") == "kitty-ops/lifecycle.jsonl"


def test_owned_retry_refuses_new_ignored_lifecycle_record(owned_retry) -> None:
    owned, lifecycle, _mission = owned_retry
    _git(owned.owned_root, "rm", "-q", "kitty-ops/lifecycle.jsonl")
    (owned.owned_root / ".gitignore").write_text("kitty-ops/lifecycle.jsonl\n")
    _git(owned.owned_root, "add", ".gitignore")
    _git(owned.owned_root, "commit", "-qm", "ignore lifecycle")
    with pytest.raises(ValueError, match="ignored"):
        retry.capture_owned_retry_lifecycle(owned)
    assert not lifecycle.exists()


@pytest.mark.parametrize("change", ["symlink", "executable"])
def test_owned_retry_refuses_mode_swap_at_commit_boundary(owned_retry, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    from specify_cli.git import commit_helpers

    owned, lifecycle, _mission = owned_retry
    capture = retry.capture_owned_retry_lifecycle(owned)
    parent = _git(owned.owned_root, "rev-parse", "HEAD")
    real_commit = commit_helpers.safe_commit

    def swap_then_commit(**kwargs):
        if change == "symlink":
            payload = lifecycle.read_text()
            lifecycle.rename(lifecycle.with_name("original.jsonl"))
            lifecycle.symlink_to(payload)
        else:
            lifecycle.chmod(0o755)
        return real_commit(**kwargs)

    monkeypatch.setattr(commit_helpers, "safe_commit", swap_then_commit)
    try:
        with pytest.raises((OSError, RuntimeError, ValueError)):
            retry.commit_owned_retry_lifecycle(capture, _decision(), "agent")
    finally:
        capture.close()
    assert _git(owned.owned_root, "rev-parse", "HEAD") == parent


def test_owned_retry_preserves_executable_lifecycle_mode(owned_retry) -> None:
    owned, lifecycle, _mission = owned_retry
    lifecycle.chmod(0o755)
    _git(owned.owned_root, "add", "kitty-ops/lifecycle.jsonl")
    _git(owned.owned_root, "commit", "-qm", "track executable lifecycle")
    capture = retry.capture_owned_retry_lifecycle(owned)
    try:
        retry.commit_owned_retry_lifecycle(capture, _decision(), "agent")
    finally:
        capture.close()
    assert _git(owned.owned_root, "ls-tree", "HEAD", "kitty-ops/lifecycle.jsonl").startswith("100755 blob ")


@pytest.mark.parametrize("case", ["invalid_mode", "unselected_path", "missing_parent"])
def test_expected_mode_assertions_reject_invalid_contracts(owned_retry, case: str) -> None:
    from specify_cli.git.commit_helpers import safe_commit

    owned, lifecycle, _mission = owned_retry
    root = owned.owned_root
    parent = _git(root, "rev-parse", "HEAD")
    lifecycle.write_text("new record\n")
    kwargs = {
        "repo_root": root,
        "worktree_root": root,
        "target": CommitTarget(ref="feature/retry"),
        "message": "test mode assertion",
        "paths": (lifecycle,),
        "expected_parent_sha": parent,
        "expected_path_modes": {lifecycle: "100644"},
    }
    if case == "invalid_mode":
        kwargs["expected_path_modes"] = {lifecycle: "120000"}
    elif case == "unselected_path":
        kwargs["expected_path_modes"] = {root / ".gitignore": "100644"}
    else:
        kwargs["expected_parent_sha"] = None
    with pytest.raises((RuntimeError, ValueError)):
        safe_commit(**kwargs)
    assert _git(root, "rev-parse", "HEAD") == parent
    assert lifecycle.read_text() == "new record\n"
