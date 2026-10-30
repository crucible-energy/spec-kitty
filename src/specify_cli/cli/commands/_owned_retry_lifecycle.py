"""Narrow, fail-closed lifecycle persistence for an owned failed-step retry."""

from __future__ import annotations

import os
import stat
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kernel.git import blob_at, index_entries, run_git, status_entries, tree_entry
from kernel.no_follow import fd_relative_dir_ops_supported
from mission_runtime import MissionArtifactKind, placement_seam
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git.commit_helpers import preflight_commit
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.invocation.lifecycle import LIFECYCLE_LOG_RELATIVE_PATH
from specify_cli.mission_metadata import resolve_mission_identity

if TYPE_CHECKING:
    from mission_runtime import OwnedCheckout

_LIFECYCLE = LIFECYCLE_LOG_RELATIVE_PATH.as_posix()
_MAX_BYTES = 16 * 1024 * 1024


@dataclass
class OwnedRetryLifecycle:
    """The exact clean record and branch observed before issuing a retry."""

    owned: OwnedCheckout
    target: Any
    parent: str
    before: bytes
    mission_id: str
    tracked: bool
    index_identity: tuple[str, str] | None
    executable: bool
    root_fd: int
    directory_fd: int | None
    record_fd: int | None
    descriptors: ExitStack

    def close(self) -> None:
        """Join every file descriptor acquired for this retry."""
        self.descriptors.close()


def _read_regular(fd: int) -> bytes:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > _MAX_BYTES:
        raise ValueError("Owned retry needs a bounded regular single-link lifecycle record")
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = _MAX_BYTES + 1
    while remaining:
        chunk = os.read(fd, min(remaining, 1024 * 1024))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
    after = os.fstat(fd)
    if len(data) != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("Lifecycle record changed during inspection")
    return data


def _record_path(root: Path) -> Path:
    parent = root / "kitty-ops"
    if parent.is_symlink() or not parent.resolve().is_relative_to(root.resolve()):
        raise ValueError("Owned retry refuses a linked or escaping lifecycle directory")
    return parent / "lifecycle.jsonl"


def _pin_lifecycle(root: Path, *, tracked: bool, before: bytes, executable: bool) -> tuple[ExitStack, int, int | None, int | None]:
    descriptors = ExitStack()
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        root_fd = os.open(root, directory_flags)
        descriptors.callback(os.close, root_fd)
        try:
            directory_fd = os.open("kitty-ops", directory_flags, dir_fd=root_fd)
        except FileNotFoundError:
            if tracked:
                raise ValueError("Tracked lifecycle directory disappeared") from None
            directory_fd = None
        if directory_fd is not None:
            descriptors.callback(os.close, directory_fd)
        record_fd = None
        if tracked:
            assert directory_fd is not None
            record_fd = os.open("lifecycle.jsonl", os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=directory_fd)
            descriptors.callback(os.close, record_fd)
            if _read_regular(record_fd) != before or bool(os.fstat(record_fd).st_mode & 0o111) != executable:
                raise ValueError("Lifecycle file does not exactly match its committed history")
        return descriptors, root_fd, directory_fd, record_fd
    except BaseException:
        descriptors.close()
        raise


def capture_owned_retry_lifecycle(owned: OwnedCheckout) -> OwnedRetryLifecycle:
    """Check ownership, clean lifecycle bytes and commit policy before mutation."""
    root = owned.owned_root
    if not fd_relative_dir_ops_supported() or os.stat not in os.supports_dir_fd or os.stat not in os.supports_follow_symlinks:
        raise ValueError("Owned retry needs supported descriptor-relative no-follow operations")
    path = _record_path(root)
    target = placement_seam(owned.repository_root, owned.mission_slug, owned=owned).write_target(MissionArtifactKind.PRIMARY_METADATA)
    branch = run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD", timeout=10).stdout.decode().strip()
    if branch != target.ref or branch != owned.write_branch:
        raise ValueError("Owned retry checkout is not on its declared write branch")
    policy = ProtectionPolicy.resolve(root)
    if branch in policy.protected_branches:
        raise ValueError("Owned retry refuses a protected write branch")
    preflight_commit(
        repo_root=root,
        worktree_root=root,
        target=target,
        message=f"chore(next): persist {owned.mission_slug} retry [skip ci]",
        paths=(path,),
        capability=GuardCapability.STANDARD,
        owned=owned,
    )
    identity = resolve_mission_identity(owned.mission_dir)
    if identity.mission_id is None:
        raise ValueError("Owned retry requires a canonical mission identity")
    parent = run_git(root, "rev-parse", "--verify", "HEAD^{commit}", timeout=10).stdout.decode("ascii").strip()
    if status_entries(root, pathspecs=(_LIFECYCLE,), untracked="all", ignored=True, optional_locks=False, timeout=10):
        raise ValueError("Owned retry refuses a dirty, untracked or ignored lifecycle record")
    tree = tree_entry(root, parent, _LIFECYCLE, timeout=10)
    index = index_entries(root, pathspecs=(_LIFECYCLE,), tags=True, timeout=10)
    if tree is None:
        if index or path.exists() or path.is_symlink():
            raise ValueError("Untracked lifecycle data must be preserved before retry")
        ignored = run_git(root, "check-ignore", "--quiet", "--no-index", "--", _LIFECYCLE, timeout=10, check=False)
        if ignored.returncode != 1:
            raise ValueError("Owned retry cannot create an ignored or indeterminate lifecycle record")
        before, index_identity, executable = b"", None, False
    else:
        if tree.type != "blob" or tree.mode not in ("100644", "100755") or len(index) != 1:
            raise ValueError("Owned retry needs one ordinary lifecycle file")
        entry = index[0]
        if entry.tag != "H" or entry.stage != 0 or (entry.mode, entry.oid) != (tree.mode, tree.oid):
            raise ValueError("Lifecycle index differs from the current commit or has hidden flags")
        before = blob_at(root, parent, _LIFECYCLE, timeout=10, max_bytes=_MAX_BYTES)
        if before is None or (before and not before.endswith(b"\n")):
            raise ValueError("Lifecycle committed history is missing or incomplete")
        index_identity, executable = (entry.mode, entry.oid), tree.mode == "100755"
    descriptors, root_fd, directory_fd, record_fd = _pin_lifecycle(root, tracked=tree is not None, before=before, executable=executable)
    return OwnedRetryLifecycle(
        owned,
        target,
        parent,
        before,
        identity.mission_id,
        tree is not None,
        index_identity,
        executable,
        root_fd,
        directory_fd,
        record_fd,
        descriptors,
    )


def _verify_anchors(capture: OwnedRetryLifecycle, *, record: bool) -> None:
    root_stat = os.stat(capture.owned.owned_root, follow_symlinks=False)
    pinned_root = os.fstat(capture.root_fd)
    if (root_stat.st_dev, root_stat.st_ino) != (pinned_root.st_dev, pinned_root.st_ino):
        raise ValueError("Owned retry checkout changed; inspect the original run")
    if capture.directory_fd is not None:
        current = os.stat("kitty-ops", dir_fd=capture.root_fd, follow_symlinks=False)
        pinned = os.fstat(capture.directory_fd)
        if (current.st_dev, current.st_ino) != (pinned.st_dev, pinned.st_ino):
            raise ValueError("Owned retry lifecycle directory changed; inspect the original run")
    if record:
        assert capture.directory_fd is not None and capture.record_fd is not None
        current = os.stat("lifecycle.jsonl", dir_fd=capture.directory_fd, follow_symlinks=False)
        pinned = os.fstat(capture.record_fd)
        if (current.st_dev, current.st_ino) != (pinned.st_dev, pinned.st_ino):
            raise ValueError("Owned retry lifecycle record changed; inspect the original run")


def commit_owned_retry_lifecycle(capture: OwnedRetryLifecycle, decision: Any, agent: str) -> None:
    """Append and commit only this retry's lifecycle record using pinned descriptors."""
    from specify_cli.git.commit_helpers import safe_commit
    from specify_cli.invocation.lifecycle import build_started_record, make_canonical_action_id

    root = capture.owned.owned_root
    path = _record_path(root)
    _verify_anchors(capture, record=capture.tracked)
    index = index_entries(root, pathspecs=(_LIFECYCLE,), tags=True, timeout=10)
    if capture.tracked:
        if len(index) != 1 or index[0].tag != "H" or index[0].stage != 0 or (index[0].mode, index[0].oid) != capture.index_identity:
            raise ValueError("Retry was issued, but lifecycle index state changed; preserve it and inspect the original run")
    elif index:
        raise ValueError("Retry was issued, but lifecycle index state changed; preserve it and inspect the original run")
    if capture.directory_fd is None:
        os.mkdir("kitty-ops", dir_fd=capture.root_fd)
        capture.directory_fd = os.open("kitty-ops", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=capture.root_fd)
        capture.descriptors.callback(os.close, capture.directory_fd)
    if capture.record_fd is None:
        capture.record_fd = os.open(
            "lifecycle.jsonl",
            os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o666,
            dir_fd=capture.directory_fd,
        )
        capture.descriptors.callback(os.close, capture.record_fd)
    _verify_anchors(capture, record=True)
    if _read_regular(capture.record_fd) != capture.before or bool(os.fstat(capture.record_fd).st_mode & 0o111) != capture.executable:
        raise ValueError("Retry was issued, but lifecycle content or mode changed; inspect the original run")
    record = build_started_record(
        canonical_action_id=make_canonical_action_id(decision.mission_state, decision.action),
        agent=agent,
        mission_id=capture.mission_id,
        wp_id=decision.wp_id,
    )
    payload = (record.to_json_line() + "\n").encode("utf-8")
    if len(capture.before) + len(payload) > _MAX_BYTES:
        raise ValueError("Retry was issued, but its lifecycle record exceeds the bound; inspect the original run")
    if os.write(capture.record_fd, payload) != len(payload):
        raise ValueError("Retry was issued, but its lifecycle append was incomplete; inspect the original run")
    os.fsync(capture.record_fd)
    after = _read_regular(capture.record_fd)
    if after != capture.before + payload:
        raise ValueError("Retry was issued, but concurrent lifecycle data changed; inspect the original run")
    _verify_anchors(capture, record=True)
    safe_commit(
        repo_root=root,
        worktree_root=root,
        target=capture.target,
        message=f"chore(next): persist {capture.owned.mission_slug} retry [skip ci]",
        paths=(path,),
        capability=GuardCapability.STANDARD,
        expected_parent_sha=capture.parent,
        expected_path_bytes={path: after},
        expected_path_modes={path: "100755" if capture.executable else "100644"},
        owned=capture.owned,
    )
