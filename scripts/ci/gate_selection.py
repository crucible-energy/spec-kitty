"""Local gate-selection authority (FR-016 / #2476).

This module is the one authority for "which shards/gates does a changed-path set
select". By default it reads the versioned local authority at
``tools/validation/gates.json``. The current hosted router remains available as
an explicit migration oracle, not the default routing source:

During migration, an explicit YAML path may still parse:

1. the dorny ``changes`` filter block — ``group -> globs[]`` (path -> group), and
2. the job ``if: needs.changes.outputs.<group>`` gates — group -> job.

It never re-encodes the routing as a second hand-maintained map: that duplication
is the very #2476 hazard this module exists to close. Existing Python consumers,
the completeness oracle, and local parity reuse the same local authority reader.
The hosted workflow digest and parity controls pin migration behavior until its
remaining command and publication mappings are qualified.

Public API:
    ``load_router(path=None) -> Router``   read the local authority by default.
    ``select_gates(changed_paths, *, router=None, mode="pr") -> GateSelection``
                                            answer the selection question.
"""

from __future__ import annotations

import fnmatch
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "DEFAULT_ROUTER_PATH",
    "DEFAULT_LOCAL_AUTHORITY_PATH",
    "PROBE_GROUPS",
    "GateSelection",
    "Router",
    "load_router",
    "router_from_local_document",
    "classify_paths",
    "select_gates",
    "select_modules",
]

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROUTER_PATH = _REPO_ROOT / ".github" / "workflows" / "ci-router.yml"
DEFAULT_REGISTRY_PATH = _REPO_ROOT / ".github" / "ci-module-registry.yml"
DEFAULT_LOCAL_AUTHORITY_PATH = _REPO_ROOT / "tools" / "validation" / "gates.json"

# The ``any_src`` filter row is the FR-004 fail-closed PROBE (matches any
# ``src/**``), consumed only by the router's ``unmatched`` step. It is never a
# routing group and is never gated on a job (contract Invariant 1).
PROBE_GROUPS = frozenset({"any_src"})

_GROUP_REF = re.compile(r"needs\.changes\.outputs\.([A-Za-z0-9_]+)")


@dataclass(frozen=True)
class Router:
    """The two parsed routing authorities of ``ci-router.yml``.

    ``filters`` is authority 1 (path -> group); ``job_gates`` is authority 2
    (job -> the groups its ``if:`` references). Everything else below is derived.
    """

    filters: dict[str, tuple[str, ...]]
    job_gates: dict[str, frozenset[str]]
    non_source_groups: frozenset[str] = frozenset()
    non_conservative_jobs: frozenset[str] = frozenset()
    refuse_unmatched_non_source: bool = False
    check_modes: dict[str, frozenset[str]] = field(default_factory=dict)
    check_dependencies: dict[str, frozenset[str]] = field(default_factory=dict)
    workflow_jobs: frozenset[str] = frozenset()
    unbound_workflow_jobs: frozenset[str] = frozenset()

    @property
    def routing_groups(self) -> frozenset[str]:
        """Every filter group except the fail-closed probe."""
        return frozenset(group for group in self.filters if group not in PROBE_GROUPS)

    @property
    def src_backed_groups(self) -> frozenset[str]:
        """Routing groups carrying at least one ``src/`` glob (code, not data)."""
        return frozenset(
            group for group in self.routing_groups if group not in self.non_source_groups and any(glob.startswith("src/") for glob in self.filters[group])
        )

    @property
    def always_on_jobs(self) -> frozenset[str]:
        """Jobs with no filter-group gate — they run unconditionally."""
        return frozenset(job for job, groups in self.job_gates.items() if not groups)

    @property
    def code_shard_jobs(self) -> frozenset[str]:
        """Gated jobs whose ``if:`` references at least one src-backed group."""
        src = self.src_backed_groups
        return frozenset(job for job, groups in self.job_gates.items() if groups & src)


@dataclass(frozen=True)
class GateSelection:
    """The answer to "what does this diff select", derived from the two authorities."""

    matched_groups: frozenset[str]
    unmatched_src: bool
    selected_jobs: frozenset[str]
    selected_code_shards: frozenset[str]
    unbound_workflow_jobs: frozenset[str] = frozenset()


def _dorny_filters(workflow: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    changes = workflow["jobs"]["changes"]
    for step in changes["steps"]:
        if "dorny/paths-filter" in str(step.get("uses", "")):
            raw = step["with"]["filters"]
            parsed = yaml.safe_load(raw) if isinstance(raw, str) else raw
            return {group: tuple(str(g) for g in (globs or ())) for group, globs in parsed.items()}
    raise ValueError("ci-router.yml `changes` job has no dorny/paths-filter step")


def _job_gates(workflow: dict[str, Any]) -> dict[str, frozenset[str]]:
    gates: dict[str, frozenset[str]] = {}
    for name, job in workflow["jobs"].items():
        if name == "changes" or not isinstance(job, dict):
            continue
        condition = job.get("if")
        gates[name] = frozenset(_GROUP_REF.findall(str(condition))) if condition else frozenset()
    return gates


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate local authority field: {key}")
        result[key] = value
    return result


def _routing_rows(value: object) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, dict) or not value:
        raise ValueError("Local routing rows must be a nonempty object")
    rows: dict[str, tuple[str, ...]] = {}
    for name, entries in value.items():
        if not isinstance(name, str) or not name or not isinstance(entries, list):
            raise ValueError("Local routing rows require names and string arrays")
        if any(not isinstance(entry, str) or not entry for entry in entries):
            raise ValueError("Local routing entries must be nonempty strings")
        rows[name] = tuple(entries)
    return rows


def _workflow_check_names(checks: dict[str, Any]) -> frozenset[str]:
    return frozenset(name for name, check in checks.items() if isinstance(check.get("recipe"), dict) and "workflow_job" in check["recipe"])


def _local_router(document: object) -> Router:
    if not isinstance(document, dict):
        raise ValueError("Local routing authority must be an object")
    version = document.get("schema_version")
    if type(version) is not int or version not in {1, 2, 3, 4, 5}:
        raise ValueError("Unsupported local authority schema version")
    routing = document.get("routing")
    if not isinstance(routing, dict):
        raise ValueError("Local routing authority requires a routing object")
    unknown_policy = routing.get("unknown_surface_policy")
    if (version >= 4 or unknown_policy is not None) and unknown_policy != "refuse-path-sensitive":
        raise ValueError("Unsupported unknown-surface routing policy")
    filters = _routing_rows(routing.get("filters"))
    gates = _routing_rows(routing.get("job_gates"))
    for groups in gates.values():
        if any(group not in filters or group in PROBE_GROUPS for group in groups):
            raise ValueError("Local routing gate references an unknown or probe group")
    data = routing.get("non_source_groups", [])
    if (
        not isinstance(data, list)
        or any(not isinstance(group, str) or group not in filters or group in PROBE_GROUPS for group in data)
        or len(set(data)) != len(data)
    ):
        raise ValueError("Invalid non-source routing groups")
    checks = document.get("checks", {})
    if not isinstance(checks, dict):
        raise ValueError("Invalid local checks")
    non_conservative: set[str] = set()
    check_modes: dict[str, frozenset[str]] = {}
    check_dependencies: dict[str, frozenset[str]] = {}
    for name, check in checks.items():
        if not isinstance(check, dict) or type(check.get("unmatched_source", True)) is not bool:
            raise ValueError("Invalid conservative routing declaration")
        if check.get("unmatched_source") is False:
            if name not in gates or not gates[name] or any(group not in data for group in gates[name]):
                raise ValueError("Only explicit data gates may opt out of conservative routing")
            non_conservative.add(name)
        modes = check.get("modes")
        dependencies = check.get("dependencies")
        if (
            not isinstance(modes, list)
            or not modes
            or any(not isinstance(mode, str) or mode not in {"commit", "full", "platform", "release", "package", "docs"} for mode in modes)
        ):
            raise ValueError("Invalid local check modes")
        if not isinstance(dependencies, list) or any(not isinstance(dependency, str) or dependency not in checks for dependency in dependencies):
            raise ValueError("Invalid local check dependencies")
        check_modes[name] = frozenset(modes)
        check_dependencies[name] = frozenset(dependencies)
    unbound = _workflow_requirements(document, checks) if version == 5 else frozenset()
    return Router(
        filters=filters,
        job_gates={name: frozenset(groups) for name, groups in gates.items()},
        non_source_groups=frozenset(data),
        non_conservative_jobs=frozenset(non_conservative),
        refuse_unmatched_non_source=unknown_policy == "refuse-path-sensitive",
        check_modes=check_modes,
        check_dependencies=check_dependencies,
        workflow_jobs=_workflow_check_names(checks),
        unbound_workflow_jobs=unbound,
    )


def load_router(path: Path | None = None) -> Router:
    """Read local routing by default, or an explicit migration fixture."""
    source = path or DEFAULT_LOCAL_AUTHORITY_PATH
    content = source.read_text(encoding="utf-8")
    if source.suffix == ".json":
        return _local_router(json.loads(content, object_pairs_hook=_unique_fields))
    workflow = yaml.safe_load(content)
    return Router(filters=_dorny_filters(workflow), job_gates=_job_gates(workflow))


def _workflow_requirements(document: dict[str, Any], checks: dict[str, Any]) -> frozenset[str]:
    """Retain unqualified job identities; this does not evaluate hosted contexts."""
    contracts = document.get("workflow_contracts")
    if not isinstance(contracts, list) or not contracts:
        raise ValueError("Missing workflow contracts")
    unbound: set[str] = set()
    for contract in contracts:
        if not isinstance(contract, dict) or not isinstance(contract.get("id"), str) or not isinstance(contract.get("definition"), dict):
            raise ValueError("Invalid workflow contracts")
        jobs = contract.get("jobs")
        original = contract["definition"].get("jobs")
        if not isinstance(jobs, dict) or not jobs or not isinstance(original, dict) or set(jobs) != set(original):
            raise ValueError("Invalid workflow job roster")
        for name, job in jobs.items():
            if not isinstance(job, dict) or job.get("binding_required") is not True or (job.get("check_id") is not None and job["check_id"] not in checks):
                raise ValueError("Invalid workflow binding")
            identifier = f"{contract['id']}.{name}"
            if identifier in unbound:
                raise ValueError("Duplicate workflow job")
            unbound.add(identifier)
    return frozenset(unbound)


def router_from_local_document(document: object) -> Router:
    """Parse an already bound local document without reopening a mutable path."""
    return _local_router(document)


def _match_groups(paths: list[str], router: Router) -> frozenset[str]:
    hit: set[str] = set()
    for group, globs in router.filters.items():
        if group in PROBE_GROUPS:
            continue
        if any(fnmatch.fnmatch(path, pattern) for pattern in globs for path in paths):
            hit.add(group)
    return frozenset(hit)


def classify_paths(changed_paths: Iterable[str | Path], *, router: Router | None = None) -> tuple[frozenset[str], bool]:
    """Classify route groups and source fallback; this cannot accept a gate.

    Corpus and module consumers need their own scoped classification even when
    a whole path-sensitive gate must refuse an unrelated uncovered surface.
    """
    router = router or load_router()
    paths = [str(path) for path in changed_paths]
    matched = _match_groups(paths, router)
    source_patterns = tuple(pattern for group in router.src_backed_groups for pattern in router.filters[group])
    unmatched_src = any(path.startswith("src/") and not any(fnmatch.fnmatch(path, pattern) for pattern in source_patterns) for path in paths)
    return matched, unmatched_src


def select_gates(
    changed_paths: Iterable[str | Path],
    *,
    router: Router | None = None,
    mode: str = "pr",
) -> GateSelection:
    """Return which jobs / code shards a changed-path set selects.

    ``mode="full"`` (or an unmapped ``src/**`` change — the FR-004 fail-closed
    catch-all) forces run-all: every routing group is selected. Otherwise only
    the groups the paths matched are selected. Always-on jobs (no filter group)
    are always included; ``selected_code_shards`` is the src-backed subset.
    """
    router = router or load_router()
    paths = [str(path) for path in changed_paths]
    if mode in {"platform", "release", "package", "docs"}:
        return _select_qualification(router, paths, mode)
    if mode not in {"pr", "commit", "full"}:
        raise ValueError("Unsupported selection mode")
    if router.refuse_unmatched_non_source and mode != "full":
        # Source-context-only declarations cannot establish covered work.
        preview_groups = frozenset(group for job, groups in router.job_gates.items() if job not in router.workflow_jobs for group in groups)
        patterns = tuple(pattern for group in router.routing_groups if (not router.workflow_jobs or group in preview_groups) for pattern in router.filters[group])
        if any(not path.startswith("src/") and not any(fnmatch.fnmatch(path, pattern) for pattern in patterns) for path in paths):
            raise ValueError("Unsupported changed surface; explicit routing or full inspection required")
    matched, unmatched_src = classify_paths(paths, router=router)

    gated_selected = frozenset(
        job
        for job, groups in router.job_gates.items()
        if groups
        and (mode == "full" or (unmatched_src and job not in router.non_conservative_jobs) or groups & matched)
        and (job not in router.workflow_jobs or ("commit" if mode == "pr" else mode) in router.check_modes[job])
    )
    return GateSelection(
        matched_groups=matched,
        unmatched_src=unmatched_src,
        selected_jobs=frozenset(
            job for job in router.always_on_jobs if job not in router.workflow_jobs or ("commit" if mode == "pr" else mode) in router.check_modes[job]
        )
        | gated_selected,
        selected_code_shards=gated_selected & router.code_shard_jobs,
        unbound_workflow_jobs=router.unbound_workflow_jobs,
    )


def _select_qualification(router: Router, paths: list[str], mode: str) -> GateSelection:
    """Inspect declared qualification work only; this cannot execute or accept it."""
    if paths:
        raise ValueError("Qualification mode does not accept changed paths")
    selected = {name for name, modes in router.check_modes.items() if mode in modes}
    if not selected:
        raise ValueError("No applicable checks for qualification mode")
    if router.unbound_workflow_jobs:
        raise ValueError("Unbound workflow context prevents qualification")
    pending = set(router.check_dependencies)
    completed: set[str] = set()
    while pending:
        ready = {name for name in pending if router.check_dependencies[name] <= completed}
        if not ready:
            raise ValueError("Invalid local check dependency cycle")
        completed.update(ready)
        pending.difference_update(ready)
    while True:
        dependencies = {dependency for name in selected for dependency in router.check_dependencies[name]}
        if dependencies <= selected:
            break
        selected.update(dependencies)
    if any(mode not in router.check_modes[name] for name in selected):
        raise ValueError("Unavailable required check for qualification mode")
    jobs = frozenset(selected)
    return GateSelection(matched_groups=frozenset(), unmatched_src=False, selected_jobs=jobs, selected_code_shards=jobs & router.code_shard_jobs)


def _registry_rows(path: Path | None = None) -> list[dict[str, Any]]:
    """The ``modules[]`` rows from the local authority, or an explicit fixture.

    The module universe and route groups are now versioned together in
    ``tools/validation/gates.json``. The old YAML registry remains available as
    an explicit migration fixture until its workflow consumers are reconciled."""
    source = path or DEFAULT_LOCAL_AUTHORITY_PATH
    content = source.read_text(encoding="utf-8")
    registry = json.loads(content, object_pairs_hook=_unique_fields) if source.suffix == ".json" else yaml.safe_load(content)
    if not isinstance(registry, dict) or not isinstance(registry.get("modules"), list):
        raise ValueError("Module authority requires a modules array")
    rows = registry["modules"]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Module authority rows must be objects")
    return [dict(row) for row in rows]


def _registry_module_names(path: Path | None = None) -> frozenset[str]:
    """The module inventory (``modules[].module``) from the registry."""
    return frozenset(str(row["module"]) for row in _registry_rows(path))


def _within(path: str, directory: str) -> bool:
    """Whether ``path`` is ``directory`` itself or a descendant of it."""
    directory = directory.rstrip("/")
    return path == directory or path.startswith(f"{directory}/")


def _canonical_test_mirror(root: str) -> str:
    """The canonical ``tests/`` mirror directory of a registry ``roots`` glob.

    Deterministic transform (the "canonical test mirror"): the mirror of a
    directory glob ``<prefix>/<leaf>/**`` is ``tests/<leaf>``; the mirror of a
    single-file root ``<prefix>/<name>.py`` is ``tests/<name>``. This is how a
    module *without* an explicit ``test_dirs`` declares its test tree — the
    authority stays the registry (its own ``roots``), never a hand-authored
    test-dir->module table (the #2476 hazard).
    """
    root = root.rstrip("/")
    if root.endswith("/**"):
        leaf = root[:-3].rstrip("/").rsplit("/", 1)[-1]
        return f"tests/{leaf}"
    name = root.rsplit("/", 1)[-1]
    stem = name.split("*", 1)[0].rsplit(".", 1)[0]
    return f"tests/{stem}"


def _probe_path(root: str) -> str:
    """A representative concrete path under a registry ``roots`` glob.

    The probe is fed back through the parsed router (:func:`select_gates`) so
    the src-routing answer for a test tree is computed by the ONE routing
    authority, not re-derived here. A directory glob yields a file under it; a
    single-file root yields the file itself.
    """
    root = root.rstrip("/")
    if root.endswith("/**"):
        return f"{root[:-3].rstrip('/')}/__ci_probe__.py"
    return root


def _modules_for_test_paths(
    paths: list[str],
    *,
    router: Router,
    registry_path: Path | None,
    modules: frozenset[str],
) -> frozenset[str]:
    """Modules a tests-only change selects, derived from the registry (#4454).

    ``select_gates`` only matches ``src/`` (and other router) globs, so a diff
    confined to ``tests/<dir>/**`` matches no routing group and selects nothing
    — a false green (the test files run in no per-PR shard). This maps each
    changed test path back to its owning module(s) using the registry, then
    mirrors that back to the SAME module set the corresponding src change would
    select, so a tests-only diff is never narrowed relative to its src twin:

    * **explicit ``test_dirs``** — a module that declares its test directories
      owns any changed path within them (preferred, per the registry);
    * **canonical mirror** — every module ``root`` also declares its test tree
      via :func:`_canonical_test_mirror`, so a module without explicit
      ``test_dirs`` still owns ``tests/<leaf>`` for each ``src/<...>/<leaf>/**``
      root. The matched roots are probed through the router (:func:`select_gates`)
      so the resulting module set equals the src change's set exactly.

    A test path with no derivable owning module contributes nothing (it falls
    through to the caller's src/full behavior) — no module is fabricated.
    """
    test_paths = [path for path in paths if _within(path, "tests")]
    if not test_paths:
        return frozenset()

    owners: set[str] = set()
    probes: set[str] = set()
    for row in _registry_rows(registry_path):
        name = str(row["module"])
        for test_dir in row.get("test_dirs") or ():
            if any(_within(path, str(test_dir)) for path in test_paths):
                owners.add(name)
        for root in row.get("roots") or ():
            mirror = _canonical_test_mirror(str(root))
            if any(_within(path, mirror) for path in test_paths):
                probes.add(_probe_path(str(root)))

    if probes:
        mirrored = select_gates(sorted(probes), router=router).matched_groups & modules
        owners |= mirrored
    return frozenset(owners & modules)


def _selection_authority_paths(registry_path: Path | None) -> frozenset[str]:
    """Spellings of the actual definitions whose changes affect every consumer."""
    spellings: set[str] = set()
    authorities = (DEFAULT_LOCAL_AUTHORITY_PATH, DEFAULT_ROUTER_PATH, DEFAULT_REGISTRY_PATH, registry_path)
    for authority in authorities:
        if authority is None:
            continue
        source = authority if authority.is_absolute() else Path.cwd() / authority
        spellings.update((str(authority), str(source)))
        try:
            spellings.add(source.relative_to(_REPO_ROOT).as_posix())
        except ValueError:
            # An explicit external fixture retains only its actual path
            # spellings; never guess an unrelated repository path by basename.
            continue
    return frozenset(spellings)


def select_modules(
    changed_paths: Iterable[str | Path],
    *,
    router: Router | None = None,
    registry_path: Path | None = None,
    mode: str = "pr",
) -> frozenset[str]:
    """Return which module-registry rows (``.github/ci-module-registry.yml``
    ``modules[].module``) a changed-path set selects.

    The module universe is the registry's own ``modules[].module`` set — NOT
    ``router.src_backed_groups``. Most registry modules are 1:1 with a
    src-backed routing group, but spec-kitty#4386 added the ``ci`` module,
    whose routing group (``scripts/ci/**`` + ``.github/workflows/**``) carries
    no ``src/`` glob and so is NOT src-backed. Intersecting against
    ``src_backed_groups`` would therefore silently drop the ``ci`` module on
    every scoped PR (including one that changes CI infra — the exact diff that
    should run ``tests/ci``). We intersect the router's matched groups against
    the registry inventory instead. Routing still comes from the parsed router
    via :func:`select_gates` — the registry supplies only the module list, so
    no second path->group map is introduced (the #2476 hazard stays closed).
    ``docs``/``corpus``/``e2e`` are non-src routing groups with no registry
    row and are excluded by the intersection.

    ``mode="full"`` or a fail-closed unmatched ``src/**`` diff (FR-004) selects
    every module — run-all, never a silent narrowing of the matrix. Otherwise
    only the matched groups that are registry modules are selected (a docs-only
    diff selects zero modules; overlapping glob ownership between groups, e.g.
    ``core_misc``/``unit``/``execution_context`` each also owning
    ``src/specify_cli/status/**``, is preserved exactly as the router already
    encodes it — never narrowed to a single "owning" module).

    A diff confined to ``tests/<dir>/**`` matches no router glob and would
    otherwise select nothing (spec-kitty#4454 — the test files run in no per-PR
    shard, a false green). Such paths are mapped back to their owning modules
    from the registry (:func:`_modules_for_test_paths`) and unioned in, so a
    tests-only diff selects the SAME module set the corresponding src change
    selects (mirror, never narrow).

    Changes to the actual router or registry definition select every module
    consumer. Without a proved row-level dependency delta, selecting only the
    definition's incidental path group can skip the wiring it changes.
    """
    router = router or load_router()
    modules = _registry_module_names(registry_path)
    paths = [str(path) for path in changed_paths]
    matched, unmatched_src = classify_paths(paths, router=router)
    if mode == "full" or unmatched_src or _selection_authority_paths(registry_path).intersection(paths):
        return modules
    src_selected = matched & modules
    test_selected = _modules_for_test_paths(paths, router=router, registry_path=registry_path, modules=modules)
    return src_selected | test_selected
