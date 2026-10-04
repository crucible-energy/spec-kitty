"""Identity-bound IO for an owned history batch, using canonical no-follow opens."""

from __future__ import annotations

import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path

from specify_cli.coordination.transaction import _open_confined_parent_fd

from .owned_history_sources import HistoryRestoreError

__all__ = ["BoundHistoryDirectory", "FileImage"]


@dataclass(frozen=True)
class FileImage:
    """Bytes plus inode/metadata identity observed through a bound directory fd."""

    data: bytes | None
    identity: tuple[int, int, int, int, int, int] | None = None

    @property
    def mode(self) -> int:
        """Preserve observed permission bits; new generated files default to 0644."""
        return self.identity[2] & 0o777 if self.identity is not None else 0o644

    def is_installed(self, staged: FileImage) -> bool:
        """Rename changes ctime: inode and exact bytes establish our installed file."""
        return self.data == staged.data and self.identity is not None and staged.identity is not None and self.identity[:5] == staged.identity[:5]


def _supported() -> bool:
    return all(operation in os.supports_dir_fd for operation in (os.open, os.stat, os.rename, os.unlink)) and all(
        hasattr(os, attribute) for attribute in ("O_DIRECTORY", "O_NOFOLLOW", "fchmod")
    )


def _image(raw: bytes, info: os.stat_result) -> FileImage:
    return FileImage(raw, (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns))


def _basename(name: str) -> None:
    if not name or name in (".", "..") or Path(name).name != name:
        raise HistoryRestoreError("Bound history IO requires a single safe basename")


class BoundHistoryDirectory:
    """Hold root/ancestor/dossier descriptors for staging, install and rollback.

    Reopening each parent uses the coordination transaction's existing canonical
    O_NOFOLLOW traversal. Every write, rename and cleanup uses only the captured
    final directory fd; namespace substitution cannot redirect them to primary.
    The creator PID alone owns file mutation and temporary cleanup. Inherited
    child frames refuse IO and close only their descriptor copies.
    """

    def __init__(self, root: Path, directory: Path) -> None:
        """Pin the no-follow directory chain, closing partial opens on failure."""
        self._owner_pid = os.getpid()
        if not _supported():
            raise HistoryRestoreError("Owned history apply requires fd-relative no-follow IO; unsupported platform refused")
        self.root = root
        self.directory = directory
        self.parents: dict[Path, int] = {}
        self.temporary: dict[str, tuple[int, int]] = {}
        try:
            parent = root
            self.parents[parent] = _open_confined_parent_fd(root, parent / ".history-boundary")
            for part in directory.relative_to(root).parts:
                parent = parent / part
                self.parents[parent] = _open_confined_parent_fd(root, parent / ".history-boundary")
            self.fd = self.parents[directory]
            self.check_directory()
        except BaseException:
            self.close()
            raise

    @property
    def owner_pid(self) -> int:
        """Return the creator PID; forked copies never acquire transaction ownership."""
        return self._owner_pid

    def _require_owner(self) -> None:
        """Detach inherited descriptors and refuse IO before touching parent files."""
        if self.owner_pid != os.getpid():
            self.close()
            raise HistoryRestoreError("Owned history IO refused in fork child; exec a fresh interpreter")
        if not self.parents:
            raise HistoryRestoreError("Bound history transaction is closed")

    def close(self) -> None:
        """Creator cleans known temporary inodes; children close only copied fds.

        Copied install frames may reach this finally after a fence refusal or an
        arbitrary exception. No inherited cleanup may stat/unlink parent staging.
        Clearing bookkeeping also makes a repeated close harmless.
        """
        try:
            for name, identity in self.temporary.items() if self.owner_pid == os.getpid() else ():
                try:
                    info = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if (info.st_dev, info.st_ino) == identity:
                    os.unlink(name, dir_fd=self.fd)
        finally:
            self.temporary.clear()
            for fd in self.parents.values():
                os.close(fd)
            self.parents.clear()

    def check_directory(self) -> None:
        """Refuse changed identities or symlink substitutions anywhere in the chain."""
        self._require_owner()
        if self.root != self.root.resolve():
            raise HistoryRestoreError("Owned checkout directory chain changed during history installation")
        for parent, original in self.parents.items():
            try:
                fresh = _open_confined_parent_fd(self.root, parent / ".history-boundary")
            except (OSError, ValueError) as exc:
                raise HistoryRestoreError("Owned dossier directory chain changed during history installation") from exc
            try:
                old, new = os.fstat(original), os.fstat(fresh)
                if (old.st_dev, old.st_ino) != (new.st_dev, new.st_ino):
                    raise HistoryRestoreError("Owned dossier directory identity changed during history installation")
            finally:
                os.close(fresh)

    def read(self, name: str) -> FileImage:
        """Read a regular file relative to the pinned directory, never a symlink."""
        self._require_owner()
        _basename(name)
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.fd)
        except FileNotFoundError:
            return FileImage(None)
        with os.fdopen(fd, "rb") as file:
            before = os.fstat(file.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise HistoryRestoreError(f"Non-regular owned history artifact refused: {name}")
            raw = file.read()
            after = os.fstat(file.fileno())
            if _image(raw, before) != _image(raw, after):
                raise HistoryRestoreError(f"Owned history artifact changed during read: {name}")
            return _image(raw, after)

    def capture(self, names: tuple[str, ...]) -> dict[str, FileImage]:
        """Capture content and inode identities through this creator-owned directory."""
        self._require_owner()
        return {name: self.read(name) for name in names}

    def verify(self, expected: dict[str, FileImage]) -> None:
        """Check identity AND content immediately before/after every install step."""
        self.check_directory()
        for name, image in expected.items():
            if self.read(name) != image:
                raise HistoryRestoreError(f"Owned history destination changed during installation: {name}")

    def stage(self, raw: bytes, mode: int) -> tuple[str, FileImage]:
        """Create a unique staged inode via the captured fd; no pathname mkstemp."""
        self.check_directory()
        staged = self._stage_bytes(raw, mode)
        self.check_directory()
        return staged

    def _stage_bytes(self, raw: bytes, mode: int) -> tuple[str, FileImage]:
        """One fd-relative staging core, shared by installation and rollback."""
        self._require_owner()
        name = f".history-{uuid.uuid4().hex}.tmp"
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        with os.fdopen(fd, "wb") as file:
            info = os.fstat(file.fileno())
            self.temporary[name] = (info.st_dev, info.st_ino)
            os.fchmod(file.fileno(), mode)
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
            image = _image(raw, os.fstat(file.fileno()))
        return name, image

    def replace(self, source: str, destination: str) -> None:
        """Both rename operands are relative to the same validated directory fd."""
        self._require_owner()
        _basename(source)
        _basename(destination)
        os.replace(source, destination, src_dir_fd=self.fd, dst_dir_fd=self.fd)

    def rollback(self, attempted: dict[str, tuple[str, FileImage]], originals: dict[str, FileImage], installed: dict[str, FileImage]) -> None:
        """Creator undoes unchanged installed inodes, preserving later writer edits.

        A copied child must refuse even when its image ledger still matches the
        parent's installed files; matching bytes/inodes do not transfer ownership.
        """
        self._require_owner()
        preserved = []
        for name, (_, staged) in reversed(list(attempted.items())):
            try:
                current = self.read(name)
            except (OSError, HistoryRestoreError):
                preserved.append(name)
                continue
            original = originals[name]
            if current == original:
                continue  # A failed replacement did not install anything.
            unchanged = current == installed[name] if name in installed else current.is_installed(staged)
            if not unchanged:
                preserved.append(name)
                continue
            if original.data is None:
                os.unlink(name, dir_fd=self.fd)
            else:
                # Rollback stays on the original descriptor even if its pathname
                # has been renamed/substituted; it can never follow the new path.
                temporary, _ = self._stage_bytes(original.data, original.mode)
                self.replace(temporary, name)
        os.fsync(self.fd)
        if preserved:
            raise HistoryRestoreError(f"Rollback preserved concurrent changes; inspect owned artifacts: {', '.join(preserved)}")
