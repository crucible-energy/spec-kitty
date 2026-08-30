"""Canonical admission checks for code-change workspace paths.

Lane workspaces are persistent execution state.  The path carries authority:
it is used by implementation and review commands as their working directory.
Keep its physical containment rule independent from the creator and resolver
modules so every path lineage can enforce the same boundary.
"""

from __future__ import annotations

from pathlib import Path

from .constants import WORKTREES_DIR


def canonical_worktree_root(repo_root: Path) -> Path:
    """Resolve the only permitted physical root for code-change worktrees."""
    resolved_repo_root = repo_root.resolve()
    canonical_root = Path(resolved_repo_root / WORKTREES_DIR).resolve()
    if canonical_root.parent != resolved_repo_root:
        raise ValueError(f"canonical worktree root must be a direct child of the repository root; refusing escaped root: {canonical_root}")
    return canonical_root


def validate_canonical_workspace_path(repo_root: Path, workspace_path: Path) -> Path:
    """Require a code-change workspace to be directly below ``.worktrees``.

    ``Path.resolve`` deliberately follows existing symlinks and normalizes
    traversal, so both a redirected ``.worktrees`` root and an unsafe persisted
    relative or absolute workspace path fail before a command changes directory
    or creates parent directories.
    """
    canonical_root = canonical_worktree_root(repo_root)
    resolved_workspace_path = workspace_path.resolve()
    if resolved_workspace_path.parent != canonical_root:
        raise ValueError(f"code-change workspace must be directly inside the canonical worktree root; expected parent: {canonical_root}")
    return resolved_workspace_path
