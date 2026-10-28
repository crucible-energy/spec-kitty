"""Shared DoctrineService project-root candidate resolution.

Both ``src/charter/compiler.py::_default_doctrine_service`` and
``src/charter/context.py::_build_doctrine_service`` use the same candidate-list
ordering.  This module is the **single source of truth** for that ordering so
the two call-sites cannot drift apart.

Candidate ordering (FR-009 / T024 / T025):

1. ``.kittify/charter-packs/`` — current supported upgrade target.
2. ``.kittify/doctrine/``   — Phase 3 synthesis target; present only after a
                              successful ``spec-kitty charter synthesize`` run.
3. ``src/doctrine/``        — code-local built-in-layer path (legacy 3.x default).
4. ``doctrine/``            — flat built-in-layer fallback.

Discovery is **conditional on directory presence**: if neither project overlay
exists the resolver returns the next matching candidate, preserving
byte-identical behaviour for legacy (pre-synthesis) projects (R-2 mitigation).
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Candidate list (ordered: synthesis-aware first, built-in-layer fallbacks after)
# ---------------------------------------------------------------------------

_OVERLAY_ROOT_CANDIDATES: tuple[str, ...] = ("charter-packs", "doctrine")
_PROJECT_ROOT_CANDIDATES: tuple[str, ...] = tuple(
    f".kittify/{name}" for name in _OVERLAY_ROOT_CANDIDATES
) + ("src/doctrine", "doctrine")


def resolve_project_root(repo_root: Path, *, layer_root: Path | None = None) -> Path | None:
    """Return the first existing project-doctrine directory for *repo_root*.

    Returns ``None`` when none of the candidates exist on disk, which means
    ``DoctrineService`` will be constructed with ``project_root=None`` (built-in
    layer only — identical to the pre-Phase-3 default).

    The function is intentionally a thin directory-presence check: it does
    **not** inspect the directory's contents.  An empty ``.kittify/doctrine/``
    directory is still a valid candidate (the ``DoctrineService`` will simply
    surface an empty project layer with no built-in-layer impact).

    Args:
        repo_root: Absolute path to the repository root.
        layer_root: Caller-selected project layer container. When supplied,
            resolve only its current/retained overlay directories, without
            falling back to a built-in source tree. Roots remain caller data.

    Returns:
        The first matching :class:`~pathlib.Path` or ``None``.
    """
    candidates = (
        (layer_root / name for name in _OVERLAY_ROOT_CANDIDATES)
        if layer_root is not None
        else (repo_root / name for name in _PROJECT_ROOT_CANDIDATES)
    )
    for path in candidates:
        if path.is_dir():
            return path
    return None


# _PROJECT_ROOT_CANDIDATES: demoted — internal path constant; no cross-module
# src/ from-import callers (WP01 harden-dead-symbol-gate-01KW0RJR).
__all__ = ["resolve_project_root"]
