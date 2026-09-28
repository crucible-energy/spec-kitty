"""Lane computation algorithm.

Groups work packages into execution lanes using a union-find structure.
Two WPs are placed in the same lane when:

1. They have overlapping owned_files globs (write-scope conflict).
2. They share predicted surface tags and ownership is not provably disjoint.

Dependency edges do not collapse lanes by themselves. They are preserved as
lane-level dependencies so disjoint upstream workstreams can run in parallel and
fan-in WPs become the synchronization point.
"""

from __future__ import annotations

from itertools import combinations, pairwise

from specify_cli.core.dependency_graph import topological_sort
from specify_cli.core.time_utils import now_utc_iso
from specify_cli.lanes.branch_naming import _PLANNING_LANE_ID, _is_planning_lane_id, mission_branch_name
from specify_cli.lanes.models import CollapseEvent, CollapseReport, ExecutionLane, LanesManifest
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.ownership.validation import _globs_overlap


# Canonical lane-id for the first planning-artifact phase. Later planning phases
# use ``lane-planning-phase-N`` and resolve to the same repository-root checkout
# after their declared implementation dependencies complete.
PLANNING_LANE_ID = _PLANNING_LANE_ID


def is_planning_lane(lane: object) -> bool:
    """Return True when *lane* is a repository-root planning-artifact phase.

    This is the single seam where "what counts as a planning lane" is decided.
    Today the backing is the lane-ID grammar in ``branch_naming``; the predicate
    keeps that grammar behind the semantic question. The
    classification is expected to become charter / mission-type-derived and
    surfaced via the shared context objects (domain epic #1666); when that lands
    only the body of this predicate (and :func:`is_planning_artifact_only`) needs
    to change — call sites must keep asking the lane/manifest semantic question
    rather than comparing against the constant or a string literal directly.

    # TODO(#1666): when planning-ness becomes charter/mission-type-derived, this
    # predicate's BACKING (and possibly its signature → context-aware) changes
    # here; callers must keep asking the semantic question via this seam.
    """
    return _is_planning_lane_id(getattr(lane, "lane_id", None))


def is_planning_artifact_only(lanes_manifest: object) -> bool:
    """Return True when every lane in *lanes_manifest* is a planning lane.

    A planning-artifact-only mission has no code lanes; its closeout writes
    directly to the target branch without a mission branch. See
    :func:`is_planning_lane` for the forward-compatibility note on the backing
    of this classification (#1666).
    """
    lanes = list(getattr(lanes_manifest, "lanes", None) or [])
    return bool(lanes) and all(is_planning_lane(lane) for lane in lanes)


class LaneComputationError(Exception):
    """Raised when lane computation cannot produce a valid lane assignment.

    This is a hard failure — no lanes.json is written when this is raised.
    """

# Surface taxonomy for conflict detection.
# If two WPs predict the same surface, they are presumed to overlap.
SURFACE_TAXONOMY: tuple[str, ...] = (
    "dashboard",
    "workspace",
    "app-shell",
    "legacy-cleanup",
    "tests",
    "tracker-integration",
    "artifact-rendering",
    "api",
)

# Keywords that map to surface tags (case-insensitive substring match).
_SURFACE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dashboard": ("dashboard", "landing page", "landing-page"),
    "workspace": ("workspace", "mission workspace"),
    "app-shell": ("app shell", "app-shell", "navigation", "sidebar", "layout"),
    "legacy-cleanup": ("legacy", "cleanup", "deprecat", "remov"),
    "tests": ("test suite", "test infrastructure", "e2e test", "integration test"),
    "tracker-integration": ("tracker", "saas", "sync"),
    "artifact-rendering": ("artifact", "render", "template"),
    "api": ("api", "endpoint", "route", "view"),
}


# ---------------------------------------------------------------------------
# Union-Find
# ---------------------------------------------------------------------------

class _UnionFind:
    """Disjoint-set data structure with union-by-rank and path compression."""

    def __init__(self, elements: list[str]) -> None:
        self._parent: dict[str, str] = {e: e for e in elements}
        self._rank: dict[str, int] = dict.fromkeys(elements, 0)

    def find(self, x: str) -> str:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1

    def groups(self) -> dict[str, list[str]]:
        """Return mapping of root → list of members."""
        result: dict[str, list[str]] = {}
        for element in self._parent:
            root = self.find(element)
            result.setdefault(root, []).append(element)
        return result


# ---------------------------------------------------------------------------
# Surface inference
# ---------------------------------------------------------------------------

def infer_surfaces(wp_body: str) -> list[str]:
    """Infer surface tags from WP body text using keyword matching.

    Args:
        wp_body: The markdown body of a work package.

    Returns:
        List of matched surface taxonomy tags.
    """
    body_lower = wp_body.lower()
    matched: list[str] = []
    for surface, keywords in _SURFACE_KEYWORDS.items():
        if any(kw in body_lower for kw in keywords):
            matched.append(surface)
    return matched


# ---------------------------------------------------------------------------
# Collapse report helpers
# ---------------------------------------------------------------------------


def _describe_overlap(
    manifest_a: OwnershipManifest,
    manifest_b: OwnershipManifest,
) -> str:
    """Return a human-readable description of which globs overlap between two manifests."""
    overlapping: list[str] = []
    for glob_a in manifest_a.owned_files:
        for glob_b in manifest_b.owned_files:
            if _globs_overlap(glob_a, glob_b):
                overlapping.append(f"{glob_a!r} vs {glob_b!r}")
    if overlapping:
        return "overlapping globs: " + ", ".join(overlapping)
    return "write-scope overlap"


def _dependency_relationship_evidence(
    wp_a: str,
    wp_b: str,
    dependency_graph: dict[str, list[str]],
) -> str | None:
    """Return direct-dependency evidence for a pair when present."""
    if wp_b in dependency_graph.get(wp_a, []):
        return f"{wp_a} depends on {wp_b}"
    if wp_a in dependency_graph.get(wp_b, []):
        return f"{wp_b} depends on {wp_a}"
    return None


def _are_disjoint(
    manifest_a: OwnershipManifest,
    manifest_b: OwnershipManifest,
) -> bool:
    """Return True if no glob from manifest_a overlaps with any glob from manifest_b."""
    for glob_a in manifest_a.owned_files:
        for glob_b in manifest_b.owned_files:
            if _globs_overlap(glob_a, glob_b):
                return False
    return True


def _is_dependency_convex(
    group: set[str],
    all_wp_ids: set[str],
    transitive_dependencies: dict[str, set[str]],
    transitive_dependents: dict[str, set[str]],
) -> bool:
    """Return whether every dependency path between group members stays inside.

    Contracting a non-convex set of vertices in a DAG can create a cycle: an
    outside WP between two grouped WPs becomes both an upstream and downstream
    lane dependency. Convex lane groups preserve the acyclic WP ordering.
    """
    for middle in all_wp_ids - group:
        has_group_ancestor = bool(transitive_dependencies.get(middle, set()) & group)
        has_group_descendant = bool(transitive_dependents.get(middle, set()) & group)
        if has_group_ancestor and has_group_descendant:
            return False
    return True


def _merge_preserves_dependency_convexity(
    union_find: _UnionFind,
    wp_a: str,
    wp_b: str,
    all_wp_ids: set[str],
    transitive_dependencies: dict[str, set[str]],
    transitive_dependents: dict[str, set[str]],
) -> bool:
    """Check that merging two code lanes cannot create a quotient-graph cycle."""
    root_a, root_b = union_find.find(wp_a), union_find.find(wp_b)
    if root_a == root_b:
        return True
    groups = union_find.groups()
    candidate = set(groups[root_a]) | set(groups[root_b])
    return _is_dependency_convex(
        candidate,
        all_wp_ids,
        transitive_dependencies,
        transitive_dependents,
    )


def _transitive_deps(
    dependency_graph: dict[str, list[str]],
) -> dict[str, set[str]]:
    """Build the transitive closure of the dependency graph.

    Returns a mapping of WP ID → set of all WPs it transitively depends on.
    """
    cache: dict[str, set[str]] = {}
    visiting: set[str] = set()

    def _reach(wp_id: str) -> set[str]:
        if wp_id in cache:
            return cache[wp_id]
        if wp_id in visiting:
            return set()
        visiting.add(wp_id)
        direct = set(dependency_graph.get(wp_id, []))
        result: set[str] = set(direct)
        try:
            for dep in direct:
                result.update(_reach(dep))
        finally:
            visiting.discard(wp_id)
        cache[wp_id] = result
        return result

    for wp in dependency_graph:
        _reach(wp)
    return cache


def _count_independent_collapses(
    events: list[CollapseEvent],
    dependency_graph: dict[str, list[str]],
) -> int:
    """Count events where wp_a and wp_b have no direct or transitive dependency relationship."""
    if not events:
        return 0
    transitive = _transitive_deps(dependency_graph)
    count = 0
    for event in events:
        if event.rule == "dependency":
            continue  # By definition not independent
        a, b = event.wp_a, event.wp_b
        if b not in transitive.get(a, set()) and a not in transitive.get(b, set()):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Overlap pair detection
# ---------------------------------------------------------------------------

def find_overlap_pairs(
    manifests: dict[str, OwnershipManifest],
) -> list[tuple[str, str]]:
    """Return pairs of WP IDs whose owned_files globs overlap.

    Args:
        manifests: Mapping of WP ID to OwnershipManifest.

    Returns:
        List of (wp_a, wp_b) tuples with overlapping write scopes.
    """
    pairs: list[tuple[str, str]] = []
    wp_ids = sorted(manifests.keys())
    for wp_a, wp_b in combinations(wp_ids, 2):
        for glob_a in manifests[wp_a].owned_files:
            for glob_b in manifests[wp_b].owned_files:
                if _globs_overlap(glob_a, glob_b):
                    pairs.append((wp_a, wp_b))
                    break
            else:
                continue
            break
    return pairs


# ---------------------------------------------------------------------------
# Execution phases
# ---------------------------------------------------------------------------

def _compute_execution_phases(
    dependency_graph: dict[str, list[str]],
    planning_artifact_wp_ids: set[str],
) -> tuple[list[str], dict[str, int]]:
    """Assign monotonic phases across planning/code boundaries.

    WPs with the same execution mode remain in the same phase unless a
    dependency path crosses the other mode. Planning artifacts in different
    phases must use distinct, sequential root-checkout lanes; otherwise one
    canonical planning lane can be both an ancestor and a descendant of a code
    lane.
    """
    order = topological_sort(dependency_graph)
    phase_by_wp: dict[str, int] = {}
    for wp_id in order:
        is_planning = wp_id in planning_artifact_wp_ids
        candidates = [
            phase_by_wp[dependency] + int((dependency in planning_artifact_wp_ids) != is_planning)
            for dependency in dependency_graph.get(wp_id, [])
            if dependency in phase_by_wp
        ]
        phase_by_wp[wp_id] = max(candidates, default=0)
    return order, phase_by_wp


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

def compute_lanes(
    dependency_graph: dict[str, list[str]],
    ownership_manifests: dict[str, OwnershipManifest],
    mission_slug: str,
    target_branch: str = "main",
    wp_bodies: dict[str, str] | None = None,
    mission_id: str | None = None,
) -> LanesManifest:
    """Compute execution lanes from dependency graph and ownership manifests.

    Algorithm:
    1. Separate planning_artifact WPs from code WPs.
    2. Union code WPs with overlapping owned_files (rule 1).
    3. Union code WPs sharing predicted surfaces when ownership is not
       provably disjoint (rule 2).
    4. Preserve dependency edges as lane-level dependencies.
    5. Build ExecutionLane per disjoint set, sorted internally by topo order.
    6. Compute lane-level dependencies and parallel groups.
    7. Group planning_artifact WPs by dependency phase into serialized
       repository-root lanes.

    Planning-artifact WPs are first-class lane-owned entities assigned to one
    lane per phase. The first phase retains the canonical ``PLANNING_LANE_ID``;
    later phases use ``lane-planning-phase-N``. Every planning phase resolves to
    the repository-root checkout, never a ``.worktrees/`` directory.

    Args:
        dependency_graph: WP ID → list of dependency WP IDs.
        ownership_manifests: WP ID → OwnershipManifest.
        mission_slug: Feature identifier.
        target_branch: Branch the mission merges into.
        wp_bodies: Optional WP ID → body text for surface inference.

    Returns:
        A LanesManifest ready for persistence.
    """
    resolved_mission_id = mission_id  # WP04/FR-004: None for legacy; never substitute slug

    # Collect all WP IDs from the graph.
    all_wp_ids = sorted(dependency_graph.keys())
    if not all_wp_ids:
        return _empty_manifest(mission_slug, target_branch, resolved_mission_id, planning_artifact_wps=[])

    # Separate planning_artifact WPs from code WPs. Planning artifacts at
    # different dependency phases receive distinct serialized root lanes.
    code_wp_ids: list[str] = []
    planning_artifact_wp_ids: list[str] = []
    for wp_id in all_wp_ids:
        manifest = ownership_manifests.get(wp_id)
        if manifest and manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT:
            planning_artifact_wp_ids.append(wp_id)
            continue
        if not manifest:
            raise LaneComputationError(
                f"Executable WP '{wp_id}' has no ownership manifest. "
                f"Ensure owned_files and execution_mode are set in WP frontmatter, "
                f"or run finalize-tasks to infer them."
            )
        code_wp_ids.append(wp_id)

    if not code_wp_ids and not planning_artifact_wp_ids:
        return _empty_manifest(mission_slug, target_branch, resolved_mission_id, planning_artifact_wps=[])

    planning_wp_set = set(planning_artifact_wp_ids)
    all_wp_set = set(all_wp_ids)
    transitive_dependencies = _transitive_deps(dependency_graph)
    transitive_dependents: dict[str, set[str]] = {wp_id: set() for wp_id in all_wp_ids}
    for wp_id, dependencies in transitive_dependencies.items():
        for dependency in dependencies:
            transitive_dependents.setdefault(dependency, set()).add(wp_id)
    if planning_wp_set:
        try:
            wp_order, phase_by_wp = _compute_execution_phases(dependency_graph, planning_wp_set)
        except ValueError as exc:
            raise LaneComputationError(
                f"Cannot order planning phases because the WP dependency graph contains a cycle: {exc}"
            ) from exc
    else:
        # Preserve the historical best-effort cycle handling for code-only
        # manifests. No execution-mode boundaries need phase ordering here.
        wp_order = all_wp_ids
        phase_by_wp = dict.fromkeys(all_wp_ids, 0)

    # Build union-find over code WPs.
    uf = _UnionFind(code_wp_ids)
    collapse_events: list[CollapseEvent] = []

    # Rule 1: Overlapping write scopes → same lane.
    code_manifests = {
        wp: ownership_manifests[wp]
        for wp in code_wp_ids
        if wp in ownership_manifests
    }
    for wp_a, wp_b in find_overlap_pairs(code_manifests):
        # Overlapping code from different phases cannot share a lane: a
        # repository-root planning phase may need to run between them.
        if phase_by_wp[wp_a] != phase_by_wp[wp_b]:
            continue
        if uf.find(wp_a) != uf.find(wp_b):
            if not _merge_preserves_dependency_convexity(
                uf,
                wp_a,
                wp_b,
                all_wp_set,
                transitive_dependencies,
                transitive_dependents,
            ):
                continue
            overlap = _describe_overlap(code_manifests[wp_a], code_manifests[wp_b])
            dep_evidence = _dependency_relationship_evidence(wp_a, wp_b, dependency_graph)
            evidence = f"{overlap}; {dep_evidence}" if dep_evidence else overlap
            collapse_events.append(CollapseEvent(
                wp_a=wp_a,
                wp_b=wp_b,
                rule="write_scope_overlap",
                evidence=evidence,
            ))
        uf.union(wp_a, wp_b)

    # Rule 2: Shared predicted surfaces → same lane.
    # Only merges WPs when ownership is NOT provably disjoint. If both WPs have
    # manifests and their owned_files are disjoint, skip the merge — a shared
    # surface keyword is not enough evidence of a real conflict.
    if wp_bodies:
        wp_surfaces: dict[str, list[str]] = {}
        for wp_id in code_wp_ids:
            body = wp_bodies.get(wp_id, "")
            wp_surfaces[wp_id] = infer_surfaces(body)

        for wp_a, wp_b in combinations(code_wp_ids, 2):
            if phase_by_wp[wp_a] != phase_by_wp[wp_b]:
                continue
            surfaces_a = set(wp_surfaces.get(wp_a, []))
            surfaces_b = set(wp_surfaces.get(wp_b, []))
            if surfaces_a & surfaces_b:
                # Only merge if ownership is NOT provably disjoint.
                # Absence of a manifest means we cannot prove disjointness → merge.
                ma = code_manifests.get(wp_a)
                mb = code_manifests.get(wp_b)
                if ma and mb and _are_disjoint(ma, mb):
                    continue  # Disjoint ownership — surface match is not enough
                shared = sorted(surfaces_a & surfaces_b)
                if uf.find(wp_a) != uf.find(wp_b):
                    if not _merge_preserves_dependency_convexity(
                        uf,
                        wp_a,
                        wp_b,
                        all_wp_set,
                        transitive_dependencies,
                        transitive_dependents,
                    ):
                        continue
                    collapse_events.append(CollapseEvent(
                        wp_a=wp_a,
                        wp_b=wp_b,
                        rule="surface_heuristic",
                        evidence=f"shared surfaces {shared} with non-disjoint ownership",
                    ))
                uf.union(wp_a, wp_b)

    # Build lane groups from union-find.
    raw_groups = uf.groups()

    # T010: Assert every executable WP appears in exactly one lane group.
    assigned_wps: set[str] = set()
    for group_members in raw_groups.values():
        assigned_wps.update(group_members)

    missing_wps = set(code_wp_ids) - assigned_wps
    if missing_wps:
        raise LaneComputationError(
            f"Executable WPs not assigned to any lane: {sorted(missing_wps)}. "
            f"Verify that these WPs appear in the dependency_graph and have "
            f"ownership manifests in frontmatter."
        )

    # Order WPs within each lane by topological sort.
    lanes: list[ExecutionLane] = []
    code_lane_by_wp: dict[str, str] = {}
    lane_letter = ord("a")

    # Sort groups deterministically by lowest WP ID in each group.
    sorted_groups = sorted(
        raw_groups.values(),
        key=lambda group: (phase_by_wp[min(group)], min(group)),
    )

    # Build a sub-graph for each group to topologically sort within it.
    for group_wps in sorted_groups:
        group_set = set(group_wps)
        sub_graph = {
            wp: [d for d in dependency_graph.get(wp, []) if d in group_set]
            for wp in group_wps
        }
        ordered_wps = topological_sort(sub_graph)

        # Collect write scopes and surfaces for the lane.
        lane_write_scope: set[str] = set()
        lane_surfaces: set[str] = set()
        for wp_id in ordered_wps:
            m = ownership_manifests.get(wp_id)
            if m:
                lane_write_scope.update(m.owned_files)
            if wp_bodies:
                lane_surfaces.update(infer_surfaces(wp_bodies.get(wp_id, "")))

        lane_id = f"lane-{chr(lane_letter)}"
        lane_letter += 1

        lanes.append(
            ExecutionLane(
                lane_id=lane_id,
                wp_ids=tuple(ordered_wps),
                write_scope=tuple(sorted(lane_write_scope)),
                predicted_surfaces=tuple(sorted(lane_surfaces)),
                depends_on_lanes=(),  # Filled in below.
                parallel_group=0,  # Filled in below.
            )
        )
        for wp_id in ordered_wps:
            code_lane_by_wp[wp_id] = lane_id

    # Assign planning-artifact WPs to one repository-root lane per dependency
    # phase. A single planning lane cannot represent a valid sequence such as
    # planning -> implementation -> post-implementation review.
    planning_phases = sorted({phase_by_wp[wp_id] for wp_id in planning_artifact_wp_ids})
    planning_lane_by_phase = {
        phase: PLANNING_LANE_ID if index == 0 else f"{PLANNING_LANE_ID}-phase-{phase}"
        for index, phase in enumerate(planning_phases)
    }
    planning_lanes: list[ExecutionLane] = []
    planning_lane_by_wp: dict[str, str] = {}
    for phase in planning_phases:
        phase_wp_ids = [
            wp_id for wp_id in wp_order
            if wp_id in planning_wp_set and phase_by_wp[wp_id] == phase
        ]
        lane_id = planning_lane_by_phase[phase]
        planning_lanes.append(_build_planning_lane(phase_wp_ids, ownership_manifests, lane_id=lane_id))
        for wp_id in phase_wp_ids:
            planning_lane_by_wp[wp_id] = lane_id

    # Lane B depends on lane A when any WP in B depends on any WP in A.
    wp_to_lane: dict[str, str] = {**code_lane_by_wp, **planning_lane_by_wp}
    lanes.extend(planning_lanes)
    lane_deps: dict[str, set[str]] = {lane.lane_id: set() for lane in lanes}
    for wp_id in wp_order:
        my_lane = wp_to_lane[wp_id]
        for dep in dependency_graph.get(wp_id, []):
            dep_lane = wp_to_lane.get(dep)
            if dep_lane and dep_lane != my_lane:
                lane_deps[my_lane].add(dep_lane)

    # Planning phases share the repository-root checkout, so serialize them
    # even when their WP-level prerequisites happen to be independent.
    ordered_planning_lane_ids = [planning_lane_by_phase[phase] for phase in planning_phases]
    for previous, current in pairwise(ordered_planning_lane_ids):
        lane_deps[current].add(previous)

    # Code WPs from different phases cannot share a lane. If their file/surface
    # ownership conflicts, preserve a deterministic phase-order dependency.
    code_surfaces = {
        wp_id: set(infer_surfaces(wp_bodies.get(wp_id, ""))) if wp_bodies else set()
        for wp_id in code_wp_ids
    }
    for wp_a, wp_b in combinations(code_wp_ids, 2):
        phase_a, phase_b = phase_by_wp[wp_a], phase_by_wp[wp_b]
        if phase_a == phase_b:
            continue
        manifest_a = ownership_manifests.get(wp_a)
        manifest_b = ownership_manifests.get(wp_b)
        disjoint = bool(manifest_a and manifest_b and _are_disjoint(manifest_a, manifest_b))
        write_conflict = bool(manifest_a and manifest_b and not _are_disjoint(manifest_a, manifest_b))
        surface_conflict = bool(code_surfaces[wp_a] & code_surfaces[wp_b]) and not disjoint
        if write_conflict or surface_conflict:
            earlier_wp, later_wp = (wp_a, wp_b) if phase_a < phase_b else (wp_b, wp_a)
            earlier_lane, later_lane = wp_to_lane[earlier_wp], wp_to_lane[later_wp]
            if earlier_lane != later_lane:
                lane_deps[later_lane].add(earlier_lane)

    lane_depth = _compute_lane_depths(lanes, lane_deps)
    final_lanes = [
        ExecutionLane(
            lane_id=lane.lane_id,
            wp_ids=lane.wp_ids,
            write_scope=lane.write_scope,
            predicted_surfaces=lane.predicted_surfaces,
            depends_on_lanes=tuple(sorted(lane_deps[lane.lane_id])),
            parallel_group=lane_depth[lane.lane_id],
        )
        for lane in lanes
    ]
    all_lanes = sorted(final_lanes, key=lambda lane: (lane.parallel_group, lane.lane_id))
    mission_branch = mission_branch_name(mission_slug, mission_id=mission_id)
    derived_planning_artifact_wps: list[str] = list(planning_artifact_wp_ids)

    # Build the collapse report with independent-WP collapse count.
    independent_collapsed = _count_independent_collapses(collapse_events, dependency_graph)
    collapse_report = CollapseReport(
        events=collapse_events,
        independent_wps_collapsed=independent_collapsed,
    )

    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=resolved_mission_id,
        mission_branch=mission_branch,
        target_branch=target_branch,
        lanes=all_lanes,
        computed_at=now_utc_iso(),
        computed_from="dependency_graph+ownership",
        planning_artifact_wps=derived_planning_artifact_wps,
        collapse_report=collapse_report,
    )


def _build_planning_lane(
    planning_artifact_wp_ids: list[str],
    ownership_manifests: dict[str, OwnershipManifest],
    *,
    lane_id: str = PLANNING_LANE_ID,
    depends_on_lanes: tuple[str, ...] = (),
    parallel_group: int = 0,
) -> ExecutionLane:
    """Build a serialized repository-root lane for one planning phase.

    P2.7: ``depends_on_lanes`` and ``parallel_group`` come from the lane
    DAG calculation in ``compute_lanes`` so cross-mode dependencies
    (code WP → planning WP, or planning WP → code WP) are honoured at lane
    scheduling time. ``lane-planning`` is retained for the first phase; later
    phases use distinct IDs but the same repository-root workspace.
    """
    write_scope: set[str] = set()
    for wp_id in planning_artifact_wp_ids:
        m = ownership_manifests.get(wp_id)
        if m:
            write_scope.update(m.owned_files)

    return ExecutionLane(
        lane_id=lane_id,
        wp_ids=tuple(planning_artifact_wp_ids),
        write_scope=tuple(sorted(write_scope)),
        predicted_surfaces=("planning",),
        depends_on_lanes=depends_on_lanes,
        parallel_group=parallel_group,
    )


def _compute_lane_depths(
    lanes: list[ExecutionLane],
    lane_deps: dict[str, set[str]],
) -> dict[str, int]:
    """Compute the depth (parallel group) of each lane in the lane DAG.

    Lanes with no dependencies get depth 0. A lane's depth is one plus
    the maximum depth of its dependencies.

    Self-loops and cycles in ``lane_deps`` are detected via the
    ``in_progress`` guard and treated as depth-0 anchors rather than
    recursing infinitely. Cycle detection is best-effort: the depth value
    returned for a cycle's lanes may not reflect graph reality, but the
    function will not blow the recursion stack. Callers that need cycle-
    accurate depths should validate the lane graph before invoking.
    """
    depths: dict[str, int] = {}
    in_progress: set[str] = set()

    def _depth(lane_id: str) -> int:
        if lane_id in depths:
            return depths[lane_id]
        if lane_id in in_progress:
            # Cycle (or self-loop) detected: break the recursion by treating
            # the current lane as a depth-0 anchor. This helper has no cycle
            # diagnostic side channel; callers that require cycle-accurate
            # depths must validate the graph before invoking it.
            return 0
        in_progress.add(lane_id)
        try:
            deps = lane_deps.get(lane_id, set())
            # Filter out self-references to prevent depth(L) = 1 + depth(L).
            non_self_deps = {d for d in deps if d != lane_id}
            if not non_self_deps:
                depths[lane_id] = 0
            else:
                depths[lane_id] = 1 + max(_depth(d) for d in non_self_deps)
        finally:
            in_progress.discard(lane_id)
        return depths[lane_id]

    for lane in lanes:
        _depth(lane.lane_id)

    return depths


def _empty_manifest(
    mission_slug: str,
    target_branch: str,
    mission_id: str | None,
    planning_artifact_wps: list[str] | None = None,
) -> LanesManifest:
    """Return an empty LanesManifest (no code WPs to lane)."""
    # WP04/FR-004: mission_id is now str | None from the caller. When it is None
    # (legacy mission without a backfilled ULID) the branch composer uses the
    # legacy naming form (no mid8 suffix). The slug-as-sentinel idiom is removed.
    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=mission_id,
        mission_branch=mission_branch_name(mission_slug, mission_id=mission_id),
        target_branch=target_branch,
        lanes=[],
        computed_at=now_utc_iso(),
        computed_from="dependency_graph+ownership",
        planning_artifact_wps=planning_artifact_wps or [],
    )
