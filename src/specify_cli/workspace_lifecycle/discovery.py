"""Bounded organization accounting. Observation grants no cleanup authority."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit

from kernel.git import GitCommandError, run_git
from kernel.git.worktree_registry import parse_worktree_records
from kernel.git_topology import GitTopologyError, inspect_git_common_dir

_NAME = re.compile(r"[a-z0-9_.-]+/[a-z0-9_.-]+")
_ORGANIZATION = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9-]*")


class CoverageGap(TypedDict):
    path: str
    reason: str


class WorkspaceObservation(TypedDict):
    repository: str
    repository_id: int
    common_dir: str
    path: str
    head: str | None
    branch: str | None
    bare: bool
    exists: bool
    disposition: str
    reason: str


class DiscoveryReport(TypedDict):
    schema_version: str
    organization_inventory_scope: str
    organization_repository_count: int
    local_scan_complete: bool
    entries_scanned: int
    directories_scanned: int
    unmatched_repositories: list[str]
    coverage_gaps: list[CoverageGap]
    workspaces: list[WorkspaceObservation]


def parse_repository_pages(pages: object, organization: str) -> dict[str, int]:
    """Validate the authenticated paginated inventory, never names from folders."""
    if not _ORGANIZATION.fullmatch(organization) or not isinstance(pages, list):
        raise ValueError("Invalid organization inventory")
    repositories: dict[str, int] = {}
    identities: dict[int, str] = {}
    for page in pages:
        if not isinstance(page, list):
            raise ValueError("Expected paginated organization repository arrays")
        for item in page:
            if not isinstance(item, dict):
                raise ValueError("Invalid repository entry")
            name, identity = item.get("full_name"), item.get("id")
            if not isinstance(name, str) or type(identity) is not int or identity <= 0:
                raise ValueError("Repository identity is absent or invalid")
            name = name.lower()
            if not _NAME.fullmatch(name) or name.split("/")[0] != organization.lower():
                raise ValueError("Repository is outside the selected organization")
            if name in repositories and repositories[name] != identity:
                raise ValueError("Conflicting repository identities")
            if identity in identities and identities[identity] != name:
                raise ValueError("Conflicting repository names")
            repositories[name] = identity
            identities[identity] = name
    return repositories


def _origin_identity(raw: str) -> str | None:
    if raw.startswith("git@github.com:"):
        name = raw.removeprefix("git@github.com:")
    else:
        parsed = urlsplit(raw)
        if parsed.hostname != "github.com" or parsed.query or parsed.fragment:
            return None
        if (
            parsed.scheme == "https"
            and parsed.username is None
            and parsed.password is None
            or parsed.scheme == "ssh"
            and parsed.username == "git"
            and parsed.password is None
        ):
            name = parsed.path.removeprefix("/")
        else:
            return None
        if parsed.port is not None:
            return None
    name = name.removesuffix(".git").lower()
    return name if _NAME.fullmatch(name) else None


def _read_git(path: Path, *args: str, env: dict[str, str]) -> str:
    return run_git(path, *args, env=env, timeout=5.0).stdout.decode("utf-8", "surrogateescape").removesuffix("\n")


def _observe_store(
    path: Path,
    repositories: dict[str, int],
    stores: set[str],
    env: dict[str, str],
    gaps: list[CoverageGap],
) -> list[WorkspaceObservation]:
    observations: list[WorkspaceObservation] = []
    try:
        marker = path / ".git"
        if marker.is_symlink():
            gaps.append({"path": str(path), "reason": "symlinked_git_marker"})
        elif marker.exists():
            name = _origin_identity(_read_git(path, "config", "--local", "--get", "remote.origin.url", env=env))
            if name not in repositories:
                gaps.append({"path": str(path), "reason": "origin_identity_unverified"})
            else:
                common = str(inspect_git_common_dir(path, env=env, timeout=5.0))
                if common not in stores:
                    raw = run_git(path, "worktree", "list", "--porcelain", "-z", timeout=5.0, env=env).stdout
                    for record in parse_worktree_records(raw):
                        exists = record.path.is_dir() and not record.path.is_symlink()
                        observations.append(
                            {
                                "repository": name,
                                "repository_id": repositories[name],
                                "common_dir": common,
                                "path": str(record.path),
                                "head": record.head,
                                "branch": record.branch,
                                "bare": record.bare,
                                "exists": exists,
                                "disposition": "retained",
                                "reason": "ownership_unknown" if exists else "workspace_unavailable",
                            }
                        )
                        if not exists:
                            gaps.append({"path": str(record.path), "reason": "workspace_unavailable"})
                    stores.add(common)
    except (OSError, ValueError, GitCommandError, GitTopologyError):
        # Never persist raw origin URLs, stderr, credentials or file content.
        gaps.append({"path": str(path), "reason": "git_inventory_unavailable"})
    return observations


def _scan_children(
    path: Path,
    *,
    entries_scanned: int,
    max_entries: int,
    remaining_slots: int,
    gaps: list[CoverageGap],
) -> tuple[list[Path], int, bool]:
    children: list[Path] = []
    with os.scandir(path) as entries:
        for entry in entries:
            if entries_scanned >= max_entries:
                gaps.append({"path": str(path), "reason": "entry_budget_exhausted"})
                return children, entries_scanned, True
            entries_scanned += 1
            if entry.name == ".git":
                continue
            if entry.is_symlink():
                gaps.append({"path": entry.path, "reason": "symlink_entry_not_followed"})
            elif entry.is_dir(follow_symlinks=False):
                if len(children) >= remaining_slots:
                    gaps.append({"path": str(path), "reason": "directory_budget_exhausted"})
                    return children, entries_scanned, True
                children.append(Path(entry.path))
    return children, entries_scanned, False


def _directory_reason(path: Path) -> str | None:
    try:
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_dir():
            return "root_or_directory_unavailable"
        if (path / "HEAD").is_file() and (path / "objects").is_dir() and (path / "config").is_file():
            return "standalone_bare_store_unsupported"
    except OSError:
        return "root_or_directory_unavailable"
    return None


def discover_workspaces(
    repositories: dict[str, int],
    roots: list[Path],
    *,
    max_depth: int = 6,
    max_directories: int = 10000,
    max_entries: int = 100000,
) -> DiscoveryReport:
    """Observe stores/clones and every registered workspace, including non-lanes.

    Does not follow symlinks, fetch refs, read file content, assign owners, or
    remove anything. Missing/stale/unreadable and scan-bound cases are explicit.
    """
    if max_depth < 0 or max_directories < 1 or max_entries < 1 or not roots:
        raise ValueError("Discovery requires roots and positive finite scan bounds")
    gaps: list[CoverageGap] = []
    observations: dict[tuple[str, str], WorkspaceObservation] = {}
    stores: set[str] = set()
    visited: set[Path] = set()
    pending = [(p.expanduser().absolute(), 0) for p in reversed(roots)]
    scanned = 0
    entries_scanned = 0
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0"})
    while pending:
        path, depth = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        if reason := _directory_reason(path):
            gaps.append({"path": str(path), "reason": reason})
            continue
        if scanned >= max_directories:
            gaps.append({"path": str(path), "reason": "directory_budget_exhausted"})
            break
        scanned += 1
        for observation in _observe_store(path, repositories, stores, env, gaps):
            observations[(observation["common_dir"], observation["path"])] = observation
        try:
            children, entries_scanned, exhausted = _scan_children(
                path,
                entries_scanned=entries_scanned,
                max_entries=max_entries,
                remaining_slots=max_directories - scanned - len(pending),
                gaps=gaps,
            )
            if exhausted:
                break
            if children and depth >= max_depth:
                gaps.append({"path": str(path), "reason": "depth_budget_exhausted"})
            else:
                pending.extend((child, depth + 1) for child in sorted(children, reverse=True))
        except OSError:
            gaps.append({"path": str(path), "reason": "directory_unreadable"})
    matched = {o["repository"] for o in observations.values()}
    return {
        "schema_version": "spec-kitty.organization-workspaces.v1",
        "organization_inventory_scope": "authenticated accessible repositories only",
        "organization_repository_count": len(repositories),
        "local_scan_complete": not gaps,
        "directories_scanned": scanned,
        "entries_scanned": entries_scanned,
        "unmatched_repositories": sorted(set(repositories) - matched),
        "coverage_gaps": gaps,
        "workspaces": sorted(observations.values(), key=lambda w: (w["repository"], w["common_dir"], w["path"])),
    }
