"""Bounded reconstruction of retained history through canonical Git listings."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kernel.git import TreeEntry, changed_entries, run_git, tree_entries
from mission_runtime import OwnedCheckout
from specify_cli.migration.owned_single_branch_proof import RecoveryError

__all__ = ["reconstruct_source_history", "source_history_env"]


def source_history_env() -> dict[str, str]:
    """Pinned objects must never mean replacement objects."""
    return {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"}


def _text(owned: OwnedCheckout, *args: str) -> str:
    return run_git(owned.owned_root, *args, env=source_history_env(), timeout=15).stdout.decode("ascii").strip()


def _require_complete_history(owned: OwnedCheckout) -> None:
    if any(os.environ.get(name) for name in ("GIT_GRAFT_FILE", "GIT_SHALLOW_FILE", "GIT_REPLACE_REF_BASE")):
        raise RecoveryError("History environment is ambiguous")
    if _text(owned, "rev-parse", "--is-shallow-repository") != "false" or _text(owned, "for-each-ref", "--format=%(refname)", "refs/replace"):
        raise RecoveryError("History is shallow or replaced")
    raw = run_git(owned.owned_root, "rev-parse", "--git-path", "info/grafts", timeout=15).stdout.decode("utf-8").strip()
    grafts = Path(raw)
    if not grafts.is_absolute():
        grafts = owned.owned_root / grafts
    if os.path.lexists(grafts):
        raise RecoveryError("Grafted history cannot establish complete custody")


def _commits(owned: OwnedCheckout, base: str, refs: dict[str, str]) -> tuple[list[dict[str, Any]], set[str]]:
    rows: list[dict[str, Any]] = []
    all_commits: set[str] = set()
    for ref, tip in sorted(refs.items()):
        run_git(owned.owned_root, "merge-base", "--is-ancestor", base, tip, env=source_history_env(), timeout=15)
        selected = _text(owned, "rev-list", "--max-count=257", base + ".." + tip).splitlines()
        if len(selected) > 256 or any(not re.fullmatch(r"[0-9a-f]{40}", commit) for commit in selected):
            raise RecoveryError("History commit census is invalid or exceeds its bound")
        rows.append({"ref": ref, "sha": tip, "commits": sorted(selected)})
        all_commits.update(selected)
        if len(all_commits) > 256:
            raise RecoveryError("Combined history exceeds its commit bound")
    return rows, all_commits


def _parents(owned: OwnedCheckout, commit: str) -> list[str]:
    size = int(_text(owned, "cat-file", "-s", commit))
    if size > 262_144:
        raise RecoveryError("Historical commit object exceeds its byte bound")
    words = _text(owned, "rev-list", "--parents", "-n1", commit).split()
    if not words or words[0] != commit or not 1 <= len(words[1:]) <= 16 or any(not re.fullmatch(r"[0-9a-f]{40}", parent) for parent in words[1:]):
        raise RecoveryError("Historical parent census is absent or exceeds its bound")
    return words[1:]


def _trees(owned: OwnedCheckout, revision: str, scope: list[str]) -> dict[str, TreeEntry]:
    rows = tree_entries(owned.owned_root, revision, pathspecs=scope, env=source_history_env(), timeout=15)
    if len(rows) > len(scope) or any(row.type != "blob" or row.mode not in ("100644", "100755") for row in rows):
        raise RecoveryError("Custody scope requires literal regular files")
    return {str(row.path): row for row in rows}


def _identity(row: TreeEntry) -> dict[str, str]:
    return {"mode": row.mode, "oid": row.oid}


@dataclass(frozen=True)
class _Census:
    refs: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    tips: list[dict[str, Any]]
    objects: dict[str, tuple[str, str]]
    owner_tree: dict[str, TreeEntry]


def reconstruct_source_history(owned: OwnedCheckout, base: str, owner_head: str, refs: dict[str, str], scope: list[str]) -> _Census:
    """Enumerate every post-base commit and parent edge, including empty edges."""
    _require_complete_history(owned)
    if not 1 <= len(scope) <= 256 or any(any(char in path for char in "*?[]") for path in scope):
        raise RecoveryError("Custody scope must contain bounded literal file selectors")
    ref_rows, commits = _commits(owned, base, refs)
    trees: dict[str, dict[str, TreeEntry]] = {}
    objects: dict[str, tuple[str, str]] = {}

    def tree(revision: str) -> dict[str, TreeEntry]:
        if revision not in trees:
            trees[revision] = _trees(owned, revision, scope)
        return trees[revision]

    def preserve(revision: str, path: str) -> dict[str, str]:
        row = tree(revision).get(path)
        if row is None:
            raise RecoveryError("Changed source must exist at every pinned version")
        objects.setdefault(row.oid, (revision, path))
        if len(objects) > 1024:
            raise RecoveryError("Source custody exceeds its distinct blob bound")
        return _identity(row)

    edges: list[dict[str, Any]] = []
    changed: set[str] = set()
    for commit in sorted(commits):
        for parent in _parents(owned, commit):
            before, after = tree(parent), tree(commit)
            rows = changed_entries(owned.owned_root, parent, commit, pathspecs=scope, renames=True, env=source_history_env(), timeout=15)
            changes: list[dict[str, Any]] = []
            for row in rows:
                path = str(row.path)
                if row.status != "M" or row.orig_path is not None or path not in before or path not in after or before[path].mode != after[path].mode:
                    raise RecoveryError("Custody supports unchanged-mode regular modifications only")
                changes.append({"path": path, "before": preserve(parent, path), "after": preserve(commit, path)})
                changed.add(path)
            edges.append({"commit": commit, "parent": parent, "changes": sorted(changes, key=lambda row: row["path"])})
    tips: list[dict[str, Any]] = []
    for revision in sorted({base, owner_head, *refs.values()}):
        for path in sorted(changed):
            tips.append({"revision": revision, "path": path, **preserve(revision, path)})
    return _Census(ref_rows, sorted(edges, key=lambda row: (row["commit"], row["parent"])), tips, objects, tree(owner_head))
