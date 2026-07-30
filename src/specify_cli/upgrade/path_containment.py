"""Containment checks for directories an upgrade discovers by name.

``exists()``, ``is_dir()``, ``iterdir()`` and ``glob()`` all follow symlinks, so
a symlinked ``kitty-ops``, glossary directory, or ``.worktrees`` root would let
an upgrade traverse — and rewrite files inside — a checkout it was never asked
to touch. Every directory an upgrade locates by name is resolved through
:func:`contained_subdir` before it is walked.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["contained_subdir"]


def contained_subdir(root: Path, *parts: str) -> Path | None:
    """Return ``root/*parts`` only when it truly lives inside *root*.

    Args:
        root: Directory that must contain the subdirectory.
        parts: Path components of the subdirectory, relative to *root*.

    Returns:
        The resolved directory, or ``None`` when it is missing, is not a
        directory, or resolves outside *root* (for example via a symlink).
    """
    candidate = root.joinpath(*parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved_root = root.resolve(strict=True)
    except OSError:
        return None
    if not resolved.is_dir() or resolved_root not in resolved.parents:
        return None
    return resolved
