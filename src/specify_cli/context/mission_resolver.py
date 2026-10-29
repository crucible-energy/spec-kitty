"""Mission handle resolver: maps user-supplied handles to canonical mission identity.

Resolution priority (most-specific → least-specific):

1. **Full mission_id** (26-char ULID): exact match on ``meta.json.mission_id``
2. **mid8 prefix** (8 chars): match on ``mission_id[:8]``
3. **Full slug with numeric prefix** (e.g. ``"083-foo-bar"``): directory name match
4. **Human slug without prefix** (e.g. ``"foo-bar"``): stripped slug match
5. **Numeric prefix alone** (e.g. ``"083"``): directory prefix match

If a handle unambiguously identifies one mission at any priority level, it is
returned immediately.  If it matches multiple missions, ``AmbiguousHandleError``
is raised with the full candidate list.  If it matches zero missions at any
level, the resolver falls through to the next level; if all levels are
exhausted without a match, ``MissionNotFoundError`` is raised.

Missions whose ``meta.json`` lacks a ``mission_id`` are silently skipped during
index construction (they cannot be resolved by identity).  To fix such missions,
run ``spec-kitty migrate backfill-identity``.

Implementation note: ``kitty-specs/`` is walked once per ``resolve_mission``
call.  The resulting in-memory index is not cached across calls because the
resolver is used in short-lived CLI commands; caching can be added later if
profiling shows it is needed.

``MissionResolver`` port (mission-resolver-port-01KX1C05 WP02, FR-001/FR-005):
this module hosts the two concrete adapters for the ``MissionResolver``
Protocol defined in ``mission_runtime.mission_resolver_port`` — the real
``FsMissionResolver`` (wrapping the walk below) and the in-memory
``FakeMissionResolver`` stub (zero filesystem access, for FS-free tests). The
free ``resolve_mission`` function accepts an optional ``resolver`` so the walk
is injectable at its single call site; existing callers that omit ``resolver``
get exactly the previous behavior via a default-constructed
``FsMissionResolver``. No adapter is cached at module or process scope
(C-005) — each is request-scoped and re-walks (or re-reads its in-memory list)
on every ``resolve``/``all_missions`` call.
"""

from __future__ import annotations

from specify_cli.core.constants import KITTY_SPECS_DIR
import re
import os
import time
from os.path import normcase
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from kernel.git import blob_at, is_tracked, run_git, tracked_paths, tree_entries, tree_entry
from kernel.content_digest import sha256_digest
from kernel.meta_decode import decode_meta
from kernel.owned_process import process_budget
from mission_runtime import MissionResolver
from specify_cli.lanes.branch_naming import resolve_mid8, strip_numeric_prefix
from specify_cli.mission_metadata import load_meta

# NOTE: this module deliberately declares no ``__all__``. The dead-symbol gate
# (``tests/architectural/test_no_dead_symbols.py``) treats an ``__all__`` member
# with no cross-file ``src/`` caller as dead and — critically — never rescues an
# ``__all__`` member via intra-module use. ``FakeMissionResolver`` is green today
# ONLY because it is grandfathered as a *widened* (non-``__all__``) name in
# ``_WIDENED_SCOPE_GRANDFATHERED_470``; promoting it into ``__all__`` would strip
# that rescue and regress a pre-existing public symbol. The selection seam below
# (``MissionListing`` / ``list_missions_for_selection`` /
# ``sole_mission_for_selection`` / ``MISSION_NOT_FOUND_MESSAGE`` /
# ``mission_not_found_message``) is green on its own real cross-file callers in
# ``next_cmd.py`` / ``research.py`` / ``merge.py``; it stays out of ``__all__``
# only to keep the widened-name posture consistent, not for lack of callers.

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ULID_RE = re.compile(r"^[0-9A-Z]{26}$")
_MID8_RE = re.compile(r"^[0-9A-Z]{8}$")
_PREFIX_RE = re.compile(r"^(\d{3})-")

# Canonical not-found message template (capital ``M``), matching the
# ``materialize.py`` exemplar. This is the SINGLE source the four fixed commands
# (plan, tasks, research, merge fresh/resume) adopt so a bad ``--mission`` handle
# reads identically across them. It is deliberately NOT applied to:
#   * :class:`MissionNotFoundError` -- keeps its FR-005 identity-aware
#     ``spec-kitty migrate backfill-identity`` remediation; collapsing it would
#     regress the identity model.
#   * ``reconcile`` -- its "mission dossier not found" wording is semantically
#     distinct (a dossier, not a mission directory).
#   * ``next``'s explicit-handle path -- its ``_emit_mission_not_found_error``
#     keeps a richer, *quoted* envelope (``Mission not found: '<handle>'`` plus a
#     remediation line). ``next`` was not in the four-command unification scope;
#     it consumes the shared *selection* helpers below, not this string constant.
MISSION_NOT_FOUND_MESSAGE = "Mission not found: {handle}"


def mission_not_found_message(handle: str) -> str:
    """Render the canonical :data:`MISSION_NOT_FOUND_MESSAGE` for *handle*.

    Thin wrapper over the template so callers never re-spell the format string
    (Sonar S1192); the *handle* is inserted verbatim.
    """
    return MISSION_NOT_FOUND_MESSAGE.format(handle=handle)


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedMission:
    """Canonical resolved identity for a single mission.

    Attributes:
        mission_id: Full 26-character ULID string from ``meta.json``.
        mission_slug: Directory name in ``kitty-specs/`` (e.g. ``"083-foo-bar"``).
        feature_dir: Absolute path to the mission directory.
        mid8: First 8 characters of ``mission_id`` (short disambiguator).
    """

    mission_id: str
    mission_slug: str
    feature_dir: Path
    mid8: str


@dataclass(frozen=True)
class MissionListing:
    """One row per existing mission, for selection/discovery surfaces.

    Distinct from :class:`ResolvedMission`: a listing is legacy-tolerant (it
    counts missions that lack a ``mission_id`` and so cannot be resolved by
    identity), and it carries the human ``friendly_name`` that
    :class:`ResolvedMission` does not.

    Attributes:
        mission_slug: Directory name in ``kitty-specs/`` -- the copy-pasteable
            handle.
        mid8: First 8 characters of ``mission_id`` (short disambiguator), or
            ``None`` for a legacy mission whose ``meta.json`` lacks a
            ``mission_id``.
        friendly_name: Human title from ``meta.json``; falls back to
            ``mission_slug`` when absent so a listing never blanks.
    """

    mission_slug: str
    mid8: str | None
    friendly_name: str


class AmbiguousHandleError(Exception):
    """Raised when a handle matches more than one mission.

    Attributes:
        handle: The user-supplied handle that was ambiguous.
        candidates: All missions matched by the handle.
    """

    def __init__(self, handle: str, candidates: list[ResolvedMission]) -> None:
        self.handle = handle
        self.candidates = candidates
        super().__init__(str(self))

    def __str__(self) -> str:
        lines = [
            f'Error: mission handle "{self.handle}" matches multiple missions.',
            "",
            "Candidates:",
        ]
        for c in self.candidates:
            lines.append(f"  {c.mission_slug} (mission_id {c.mission_id}, mid8 {c.mid8})")
        lines.append("")
        lines.append("Re-run with a more specific handle:")
        for c in self.candidates:
            lines.append(f"  spec-kitty <command> --mission {c.mid8}")
            lines.append(f"  spec-kitty <command> --mission {c.mission_slug}")
        lines.append("")
        lines.append("For JSON output of all candidates:")
        lines.append(f"  spec-kitty doctor identity --mission {self.handle} --json")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable error payload for ``--json`` callers."""
        return {
            "error": "MISSION_AMBIGUOUS_SELECTOR",
            "handle": self.handle,
            "candidates": [
                {
                    "mission_id": c.mission_id,
                    "mid8": c.mid8,
                    "slug": c.mission_slug,
                    "feature_dir": str(c.feature_dir),
                }
                for c in self.candidates
            ],
        }


class MissionNotFoundError(Exception):
    """Raised when no mission matches the supplied handle.

    Fail-closed-loud (FR-005): the message always names
    ``spec-kitty migrate backfill-identity`` as a candidate remediation,
    since a cold-miss is indistinguishable, from the resolver's viewpoint,
    from "the mission exists but was silently skipped during indexing because
    its ``meta.json`` lacks a ``mission_id``" (see :func:`_build_index`). There
    is deliberately no ``is None`` / ``or slug`` fallback here — a miss always
    raises.

    Attributes:
        handle: The user-supplied handle that matched nothing.
    """

    def __init__(self, handle: str) -> None:
        self.handle = handle
        super().__init__(
            f'No mission found for handle "{handle}". '
            "If this is a legacy mission whose meta.json lacks a mission_id, "
            "run `spec-kitty migrate backfill-identity` to backfill it."
        )


# ---------------------------------------------------------------------------
# Internal: index construction
# ---------------------------------------------------------------------------


def _iter_mission_dirs(repo_root: Path) -> Iterator[Path]:
    """Yield each ``kitty-specs/`` child directory once, in slug order.

    The SINGLE ``kitty-specs/`` enumeration primitive for this module: both the
    identity index (:func:`_build_index`) and the legacy-tolerant selection
    listing (:func:`list_missions_for_selection`) consume it, so there is no
    second independent scan to drift (or to trip
    ``tests/architectural/test_mission_resolver_walker_gate.py``). Non-directory
    entries (e.g. a stray ``README.md``) are skipped; the population/identity
    predicate is left to each caller.
    """
    specs_dir = repo_root / KITTY_SPECS_DIR
    if not specs_dir.exists():
        return
    # All entries share a parent: normalize each child name once instead of
    # repeatedly comparing full Paths. normcase preserves platform ordering.
    for entry in sorted(specs_dir.iterdir(), key=lambda path: normcase(path.name)):
        if entry.is_dir():
            yield entry


_MISSION_MARKER_FILES = ("spec.md", "meta.json")


def _git_prefix(repo_root: Path) -> str | None:
    """``git rev-parse --show-prefix`` for *repo_root* (``""`` at the toplevel); ``None`` outside a work tree."""
    result = run_git(repo_root, "rev-parse", "--is-inside-work-tree", "--show-prefix", check=False)
    if result.returncode != 0:
        return None
    lines = result.stdout.decode("utf-8", "replace").split("\n")
    return lines[1] if lines[0].strip() == "true" and len(lines) > 1 else None


def tracked_mission_paths(repo_root: Path) -> frozenset[str] | None:
    """Return every git-tracked path under ``kitty-specs/`` (*repo_root*-relative, ``/``-joined).

    One batch ``git ls-files`` for the whole tree, so :func:`is_mission_dir`
    needs no subprocess per directory. ``kernel.git.tracked_paths`` yields
    toplevel-relative paths, so the ``git rev-parse --show-prefix`` of
    *repo_root* is stripped: a project nested in a larger repository compares
    on the same base as :func:`is_mission_dir`. ``None`` only when *repo_root*
    is not inside a git work tree (or git is unavailable); callers pass it as
    ``tracked=`` and the predicate then degrades to its existence rule. Any
    other git failure propagates.
    """
    try:
        prefix = _git_prefix(repo_root)
        if prefix is None:
            return None
        paths = (str(path) for path in tracked_paths(repo_root, pathspecs=[KITTY_SPECS_DIR]))
        return frozenset(p.removeprefix(prefix) for p in paths)
    except OSError:
        return None


def _carries_identity(path: Path) -> bool:
    """True when ``path/meta.json`` parses and holds a non-empty string ``mission_id``."""
    data = load_meta(path, on_malformed="none")
    mission_id = data.get("mission_id") if data else None
    return isinstance(mission_id, str) and bool(mission_id)


def is_mission_dir(path: Path, *, repo_root: Path, tracked: frozenset[str] | None = None) -> bool:
    """Whether the ``kitty-specs/`` child *path* is a Mission rather than residue (#5812).

    A directory holding only untracked or gitignored files (a stray ``*.lock``,
    a deleted Mission's leftovers) is not a Mission. The rule, in order:

    1. ``meta.json`` parses and carries a non-empty ``mission_id`` -> True. A
       fresh ``mission create`` writes this before anything is committed, so a
       genuine uncommitted Mission is never residue; residue never has one.
    2. ``spec.md`` or ``meta.json`` is git-tracked -> True. *tracked* is an
       optional precomputed set from :func:`tracked_mission_paths` (batch use);
       without it each marker is probed with ``git ls-files``.
    3. Otherwise False.

    Outside a git work tree (or when git is unavailable), rule 2 falls back to
    the population rule of :func:`list_missions_for_selection` (``spec.md`` or
    ``meta.json`` exists), so a non-git scan root never errors out of
    enumeration. Any other git failure propagates. This is a per-directory test
    applied to what :func:`_iter_mission_dirs` yields, never a second scan.
    """
    if _carries_identity(path):
        return True
    try:
        base = repo_root.resolve()
        rels = [(path.resolve() / name).relative_to(base).as_posix() for name in _MISSION_MARKER_FILES]
        if tracked is not None:
            return any(rel in tracked for rel in rels)
        if _git_prefix(base) is None:
            return _markers_exist(path)
        return any(is_tracked(base, rel) for rel in rels)
    except (OSError, ValueError):
        return _markers_exist(path)


def _markers_exist(path: Path) -> bool:
    return any((path / name).exists() for name in _MISSION_MARKER_FILES)


def _build_index(repo_root: Path) -> list[ResolvedMission]:
    """Walk ``kitty-specs/`` and return a list of indexable missions.

    Missions whose ``meta.json`` lacks a ``mission_id`` are silently skipped.
    Non-directory entries (e.g. ``README.md``) are also skipped. A ``meta.json``
    that parses to a non-object (e.g. a JSON array) is skipped here rather than
    crashing the index: per-mission topology validation belongs to the consumer
    (``status.aggregate._read_meta``), which fails the *targeted* mission closed
    with ``MissionMetadataUnavailable``.
    """
    missions: list[ResolvedMission] = []
    for entry in _iter_mission_dirs(repo_root):
        data = load_meta(entry, on_malformed="none")
        if data is None:
            # Missing, malformed, or a non-object meta.json (e.g. a JSON array)
            # — not indexable by identity. The consumer validates and fails
            # the targeted mission closed.
            continue
        mission_id: str | None = data.get("mission_id") or None
        if not mission_id:
            # Legacy mission without mission_id — cannot be resolved by identity.
            # Operator must run `spec-kitty migrate backfill-identity`.
            continue
        missions.append(
            ResolvedMission(
                mission_id=mission_id,
                mission_slug=entry.name,
                feature_dir=entry,
                mid8=resolve_mid8(entry.name, mission_id=mission_id),
            )
        )
    return missions


# ---------------------------------------------------------------------------
# Public selection/discovery seam (mission-handle-resolution WP01, FR-006/012)
# ---------------------------------------------------------------------------


def list_missions_for_selection(main_repo: Path) -> list[MissionListing]:
    """List every existing mission for selection/discovery, legacy included.

    The population rule counts any ``kitty-specs/`` directory bearing
    ``spec.md`` **or** ``meta.json`` — the SAME rule the agent-layer
    ``_list_feature_spec_candidates`` uses — so ``next`` and plan/tasks never
    disagree on the count. It deliberately includes legacy missions whose
    ``meta.json`` lacks a ``mission_id`` (and missions with only a ``spec.md``),
    which :meth:`FsMissionResolver.all_missions` silently drops.

    ``mission_id`` / ``mid8`` / ``friendly_name`` are read best-effort via
    :func:`load_meta` (tolerating a missing, malformed, or non-object
    ``meta.json``); ``mid8`` is ``None`` when no ``mission_id`` can be
    authoritatively derived, and ``friendly_name`` falls back to the slug so a
    listing never blanks. Ordering is deterministic (by ``mission_slug``) via
    :func:`_iter_mission_dirs`.

    Args:
        main_repo: Repository root containing the ``kitty-specs/`` tree.

    Returns:
        The mission listings in ``mission_slug`` order; empty when
        ``kitty-specs/`` is absent or holds no spec/meta-bearing directory.
    """
    listings: list[MissionListing] = []
    for entry in _iter_mission_dirs(main_repo):
        if not (entry / "spec.md").exists() and not (entry / "meta.json").exists():
            continue
        data = load_meta(entry, on_malformed="none") or {}
        # A syntactically valid meta.json can carry a non-string ``mission_id``
        # (e.g. a JSON number); guard the type so ``resolve_mid8``'s ``len()``
        # never crashes discovery for the whole repo over one odd file. This
        # keeps the ``str | None`` annotation honest.
        raw_mission_id = data.get("mission_id")
        mission_id: str | None = raw_mission_id if isinstance(raw_mission_id, str) else None
        mid8 = resolve_mid8(entry.name, mission_id=mission_id) or None
        friendly_raw = data.get("friendly_name")
        friendly_name = str(friendly_raw) if friendly_raw else entry.name
        listings.append(MissionListing(mission_slug=entry.name, mid8=mid8, friendly_name=friendly_name))
    return listings


def sole_mission_for_selection(main_repo: Path) -> str | None:
    """Return the sole mission's slug, or ``None`` for zero or more than one.

    FR-004 convention: a command with a missing ``--mission`` may auto-select
    when exactly one mission exists, but must NEVER silently pick among
    several. Thin over :func:`list_missions_for_selection` so every consumer
    (``next`` and the plan/tasks/merge gates) shares one population definition.
    """
    listings = list_missions_for_selection(main_repo)
    if len(listings) == 1:
        return listings[0].mission_slug
    return None


# ---------------------------------------------------------------------------
# Internal: form classifiers
# ---------------------------------------------------------------------------


def _is_full_ulid(handle: str) -> bool:
    """Return True if the handle looks like a full 26-char ULID."""
    return bool(_ULID_RE.match(handle))


def _is_mid8(handle: str) -> bool:
    """Return True if the handle looks like a mid8 (8 uppercase alphanumeric chars)."""
    return bool(_MID8_RE.match(handle))


def _is_numeric_prefix(handle: str) -> bool:
    """Return True if the handle is a pure digit string (e.g. '083')."""
    return handle.isdigit()


# ---------------------------------------------------------------------------
# Public resolver
# ---------------------------------------------------------------------------


def _resolve_from_index(handle: str, missions: list[ResolvedMission]) -> ResolvedMission:
    """Resolve ``handle`` against an already-built in-memory mission index.

    This is the priority ladder shared by :class:`FsMissionResolver` (over a
    fresh ``_build_index`` walk) and :class:`FakeMissionResolver` (over a
    caller-supplied in-memory list) — the single fail-closed-loud resolution
    algorithm (FR-005), independent of where ``missions`` came from.

    Resolution priority (see module docstring):
    1. Full mission_id (26-char ULID)
    2. mid8 prefix (8 chars of upper alphanumeric)
    3. Full slug with numeric prefix (directory name)
    4. Human slug without prefix
    5. Numeric prefix alone (all-digits handle)

    Raises:
        AmbiguousHandleError: The handle matches more than one mission.
        MissionNotFoundError: The handle matches no mission.
    """
    # ------------------------------------------------------------------
    # Priority 1: Full mission_id (exact 26-char ULID)
    # ------------------------------------------------------------------
    if _is_full_ulid(handle):
        matches = [m for m in missions if m.mission_id == handle]
        return _resolve_or_raise(handle, matches)

    # ------------------------------------------------------------------
    # Priority 2: mid8 prefix (8 uppercase alphanum chars)
    # Note: also catches shorter unique prefixes (partial mid8) via startswith.
    # ------------------------------------------------------------------
    if _is_mid8(handle):
        matches = [m for m in missions if m.mission_id.startswith(handle)]
        return _resolve_or_raise(handle, matches)

    # ------------------------------------------------------------------
    # Priority 3: Full slug with numeric prefix (e.g. "083-foo-bar")
    # ------------------------------------------------------------------
    matches = [m for m in missions if m.mission_slug == handle]
    if matches:
        return _resolve_or_raise(handle, matches)

    # ------------------------------------------------------------------
    # Priority 4: Human slug without numeric prefix (e.g. "foo-bar")
    # ------------------------------------------------------------------
    if not _is_numeric_prefix(handle):
        human_matches = [m for m in missions if strip_numeric_prefix(m.mission_slug) == handle]
        if human_matches:
            return _resolve_or_raise(handle, human_matches)

    # ------------------------------------------------------------------
    # Priority 5: Numeric prefix (all-digits string, e.g. "083")
    # ------------------------------------------------------------------
    if _is_numeric_prefix(handle):
        prefix_matches = [
            m
            for m in missions
            if _PREFIX_RE.match(m.mission_slug) and _PREFIX_RE.match(m.mission_slug).group(1) == handle  # type: ignore[union-attr]
        ]
        return _resolve_or_raise(handle, prefix_matches)

    raise MissionNotFoundError(handle)


# ---------------------------------------------------------------------------
# MissionResolver port adapters (mission-resolver-port-01KX1C05 WP02)
# ---------------------------------------------------------------------------


class FsMissionResolver:
    """Real :class:`~mission_runtime.MissionResolver` adapter.

    Wraps the existing ``kitty-specs/`` walk (:func:`_build_index`) and the
    priority-ladder resolution (:func:`_resolve_from_index`). Bound to a
    single ``repo_root`` at construction so callers pass only the handle.

    Request-scoped: every call to :meth:`resolve` / :meth:`all_missions`
    re-walks ``kitty-specs/`` — there is no module or process-level cache
    (C-005); an instance may be reused across calls within one request without
    changing this contract, since the walk itself is not memoized.
    """

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def resolve(self, handle: str) -> ResolvedMission:
        """Resolve ``handle`` via a fresh walk of ``kitty-specs/``.

        Raises:
            AmbiguousHandleError: The handle matches more than one mission.
            MissionNotFoundError: The handle matches no mission. The error
                message names ``spec-kitty migrate backfill-identity`` for
                legacy missions missing ``mission_id``.
        """
        return _resolve_from_index(handle, _build_index(self._repo_root))

    def all_missions(self) -> list[ResolvedMission]:
        """Return every identity-bearing mission found by a fresh walk.

        Missions whose ``meta.json`` lacks a ``mission_id`` are silently
        skipped, exactly as :func:`_build_index` does today (C-001) — this
        preserves ``status/identity_audit.py``'s separate, non-routed walk as
        the only surface that finds them.
        """
        return _build_index(self._repo_root)


class FakeMissionResolver:
    """In-memory :class:`~mission_runtime.MissionResolver` stub.

    Constructed from a caller-supplied list of canonical-shaped
    :class:`ResolvedMission` fixtures. Performs **zero** filesystem access,
    enabling FS-free tests of consumers built against the ``MissionResolver``
    Protocol (NFR-001) — including with no ``kitty-specs/`` tree present at
    all.

    Applies the same fail-closed-loud priority ladder as
    :class:`FsMissionResolver` (:func:`_resolve_from_index`): ambiguous
    handles raise :class:`AmbiguousHandleError`; cold-misses raise
    :class:`MissionNotFoundError`.
    """

    def __init__(self, missions: list[ResolvedMission]) -> None:
        self._missions = list(missions)

    def resolve(self, handle: str) -> ResolvedMission:
        """Resolve ``handle`` against the in-memory fixture list."""
        return _resolve_from_index(handle, self._missions)

    def all_missions(self) -> list[ResolvedMission]:
        """Return the in-memory fixture list, unfiltered (already canonical)."""
        return list(self._missions)


def resolve_mission(
    handle: str,
    repo_root: Path,
    *,
    resolver: MissionResolver | None = None,
) -> ResolvedMission:
    """Resolve a user-supplied handle to a canonical mission.

    This is the single injection site for the ``MissionResolver`` port
    (mission-resolver-port-01KX1C05 WP02): callers that pass no ``resolver``
    get exactly the previous behavior (a fresh :class:`FsMissionResolver` over
    ``repo_root``); callers threading a resolver (e.g. a
    :class:`FakeMissionResolver` in a test) get theirs instead.

    Args:
        handle: A mission handle in any supported form (see module docstring
            for the full priority ladder).
        repo_root: Absolute path to the repository root. Ignored when
            ``resolver`` is supplied (the resolver owns its own scope).
        resolver: Optional :class:`~mission_runtime.MissionResolver` to
            delegate to. Defaults to a fresh ``FsMissionResolver(repo_root)``.

    Returns:
        The uniquely resolved :class:`ResolvedMission`.

    Raises:
        AmbiguousHandleError: The handle matches more than one mission.
        MissionNotFoundError: The handle matches no mission.
    """
    active_resolver: MissionResolver = resolver or FsMissionResolver(repo_root)
    # The Protocol return type is the structural ResolvedMissionLike (D-Q2):
    # mission_runtime cannot reference this module's concrete ResolvedMission.
    # Every MissionResolver implementation in this codebase (FsMissionResolver,
    # FakeMissionResolver — the only two that exist) is constructed here and
    # is known, by this module's own construction, to return ResolvedMission.
    return cast(ResolvedMission, active_resolver.resolve(handle))


# ---------------------------------------------------------------------------
# Internal: resolve-or-raise helper
# ---------------------------------------------------------------------------


def _resolve_or_raise(handle: str, matches: list[ResolvedMission]) -> ResolvedMission:
    """Return the single match, raise on zero or multiple matches."""
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise AmbiguousHandleError(handle, matches)
    raise MissionNotFoundError(handle)


def _pinned_blob(root: Path, commit: str, relative: str, env: dict[str, str], limit: int) -> bytes | None:
    entry = tree_entry(root, commit, relative, env=env, timeout=5)
    if entry is None:
        return None
    if entry.type != "blob" or entry.mode not in {"100644", "100755"}:
        raise ValueError(f"Pinned inspection requires a regular blob: {relative}")
    return blob_at(root, commit, relative, env=env, timeout=5, max_bytes=limit)


def _pinned_mission_index(root: Path, commit: str, env: dict[str, str]) -> tuple[list[ResolvedMission], dict[str, tuple[bytes, dict[str, Any]]]]:
    subtree = tree_entry(root, commit, KITTY_SPECS_DIR, env=env, timeout=5)
    if subtree is None:
        return [], {}
    if subtree.type != "tree":
        raise ValueError("Pinned planning root must be a Git tree")
    entries = tree_entries(root, f"{commit}:{KITTY_SPECS_DIR}", pathspecs=(), env=env, timeout=5)
    if len(entries) > 1024:
        raise ValueError("Pinned planning metadata index exceeds 1024 objects")
    missions: list[ResolvedMission] = []
    metadata: dict[str, tuple[bytes, dict[str, Any]]] = {}
    remaining = 4 * 1024 * 1024
    for entry in entries:
        slug = str(entry.path)
        if entry.type != "tree" or len(Path(slug).parts) != 1:
            continue
        relative = f"{KITTY_SPECS_DIR}/{slug}/meta.json"
        raw = _pinned_blob(root, commit, relative, env, min(65536, remaining))
        if raw is None:
            continue
        remaining -= len(raw)
        meta = decode_meta(raw, on_malformed="none")
        if meta is None:
            continue  # Same unindexable legacy posture as the filesystem index.
        identity = meta.get("mission_id")
        if not identity:
            continue
        if not isinstance(identity, str) or not _is_full_ulid(identity):
            raise ValueError(f"Pinned mission identity unavailable: {relative}")
        if meta.get("mission_slug", slug) != slug:
            raise ValueError(f"Pinned mission slug differs from its tree path: {relative}")
        # The existing priority ladder consumes these locally. No synthetic
        # path or reconstructed OwnedCheckout escapes as creator/write authority.
        missions.append(ResolvedMission(identity, slug, root / KITTY_SPECS_DIR / slug, resolve_mid8(slug, mission_id=identity)))
        metadata[slug] = (raw, meta)
    return missions, metadata


def _pinned_planning_artifacts(root: Path, commit: str, slug: str, env: dict[str, str]) -> tuple[list[dict[str, object]], dict[str, Any] | None]:
    artifacts: list[dict[str, object]] = []
    status: dict[str, Any] | None = None
    remaining = 4 * 1024 * 1024
    for name in ("meta.json", "spec.md", "plan.md", "tasks.md", "status.json", "analysis-report.md"):
        relative = f"{KITTY_SPECS_DIR}/{slug}/{name}"
        raw = _pinned_blob(root, commit, relative, env, min(1024 * 1024, remaining))
        if raw is None:
            artifacts.append({"path": relative, "present_at_commit": False})
            continue
        remaining -= len(raw)
        artifacts.append({"path": relative, "present_at_commit": True, "bytes": len(raw), "sha256": sha256_digest(raw).removeprefix("sha256:")})
        if name == "status.json":
            status = decode_meta(raw)
    return artifacts, status


def inspect_mission_at(repo_root: Path, handle: str, ref: str) -> dict[str, object]:
    """Read immutable planning facts using the canonical Git/identity authorities.

    This is not a MissionContext or OwnedCheckout factory. It neither simulates
    next nor carries a current report qualification, claim or mutation capability.
    """
    if not handle.strip() or not ref.strip() or len(handle) > 1024 or len(ref) > 1024 or "\0" in handle or "\0" in ref:
        raise ValueError("Explicit bounded mission handle and Git revision required")
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    with process_budget(30, cleanup_deadline=time.monotonic() + 30):
        root = Path(run_git(repo_root, "rev-parse", "--show-toplevel", env=env, timeout=5).stdout.decode("utf-8").strip())
        commit = run_git(root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}", env=env, timeout=5).stdout.decode("ascii").strip()
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit) is None:
            raise ValueError("Git did not resolve one immutable commit")
        missions, metadata = _pinned_mission_index(root, commit, env)
        selected = _resolve_from_index(handle, missions)
        raw, meta = metadata[selected.mission_slug]
        artifacts, status = _pinned_planning_artifacts(root, commit, selected.mission_slug, env)
        tree = run_git(root, "rev-parse", f"{commit}^{{tree}}", env=env, timeout=5).stdout.decode("ascii").strip()
    return {
        "result": "success",
        "read_only": True,
        "observation_scope": "immutable_committed_planning_facts",
        "requested_ref": ref,
        "commit": commit,
        "tree": tree,
        "mission_id": selected.mission_id,
        "mission_slug": selected.mission_slug,
        "meta_sha256": sha256_digest(raw).removeprefix("sha256:"),
        "metadata": meta,
        "artifacts": artifacts,
        "saved_status_at_commit": status,
        "current_readiness_qualified": False,
    }
