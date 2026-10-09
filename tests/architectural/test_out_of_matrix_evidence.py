"""Permanent out-of-matrix evidence, marker-honesty, and selection guards.

Mission decide-out-of-matrix-test-dirs (spec-kitty#4374, WP04, T015-T019) lifts the
mission's load-bearing invariants from a one-time acceptance check
(``kitty-specs/decide-out-of-matrix-test-dirs-01M2TKC7/contracts/acceptance-checks.md``)
into an always-on architectural gate, so the mission's outcome cannot silently rot on
``main`` after the mission branch merges:

* **T015** -- a module whose ``shard_count`` moved (or is a brand-new row) this mission
  carries fresh, parity-checked capture provenance (closes the uniform-weight
  degradation; NFR-003/SC-002).
* **T016** -- a registry reason that claims a marker lane is honest: the tree it
  covers actually carries that ``@pytest.mark.<lane>`` (the #2979 disguised-snapshot
  class).
* **T017** -- a registry reason is a decision, never a snapshot: no deferral phrase,
  no placeholder, and it names a concrete covering surface (NFR-005/SC-001).
* **T018** -- a reason claiming coverage-equivalence via a structured
  ``evidence: analysis/evidence/<f>.json`` pointer resolves to a committed file whose
  stored coverage proves the subset claim (Renata F1). Vacuous when the mission never
  used this claim shape (see ``analysis/evidence/README.md``): never invented here.
* **T019** -- every module row whose ``test_dirs`` this mission expanded (vs
  the base ref) is durably, re-runnably selected per-PR by
  :func:`scripts.ci.gate_selection.select_modules` (Renata F3 / Paula F3).

T015 and T019 both diff the live registry against the resolved base ref (see
``_resolve_base_ref``: ``origin/main`` preferred, ``main`` as fallback -- a fresh
CI checkout via ``actions/checkout`` is a detached HEAD with no local
``refs/heads/main``, only ``refs/remotes/origin/main``, so a bare ``main`` lookup
errors there; this mirrors the ``origin/main``-preferred convention
``test_archive_root_byte_identical.py``'s ``_PORT_BASE_REF`` already uses in the
same arch-heavy CI job). When neither ref resolves in the checkout, that is a
checkout/environment condition, not a code-invariant violation, so the base-diff
tests SKIP rather than hard-error. On ``main`` itself that diff is empty (zero net
diff post-merge) -- both guards are written to pass vacuously in that case rather
than red every PR forever after this mission lands.

**Honest framing: T015/T019 are transitional, not enduring.** Both diff against a
base ref and no-op (return early) once head == base -- so post-merge, on ``main``
itself, they assert nothing. T016 and T017 (and the other 25 lifted gates in this
mission) are ENDURING: they assert against the current tree unconditionally,
regardless of any base ref. Durable, permanent post-merge protection against a
test directory silently falling out of module-shard coverage comes from the
always-on ``test_module_shard_registry.py::test_every_test_directory_is_claimed_once_or_recorded_out_of_matrix``,
not from T015/T019 -- those two exist to prove *this mission's own* registry
changes were captured/selected correctly while they are still a diff.

Loads (registry/timings/base-registry) happen lazily inside each test, mirroring
``test_module_shard_registry.py``'s own discipline, so a missing artefact reds for
the right reason rather than an import-time crash. This file imports that module's
loaders/constants (DRY) and must never edit it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci.gate_selection import select_modules
from tests.architectural.test_module_shard_registry import (
    _REPO_ROOT,
    _load_registry,
    _load_timings,
    _modules,
)

pytestmark = [pytest.mark.architectural]

_MISSION_ROOT = _REPO_ROOT / "kitty-specs" / "decide-out-of-matrix-test-dirs-01M2TKC7"
_MISSION_EVIDENCE_DIR = _MISSION_ROOT / "analysis" / "evidence"
_CAPTURE_FLOOR_PATH = _MISSION_EVIDENCE_DIR / "capture-floor.txt"

_MARKER_LANES = ("corpus", "windows_ci", "performance", "e2e", "interpreter", "stress", "nightly")
# A reason "claims" a marker lane only when it names the marker right after the
# literal `pytest.mark.` prefix or a `-m ` pytest-invocation flag -- not merely by
# mentioning a CI workflow filename (e.g. "ci-nightly.yml") or an excluded-marker
# clause (e.g. "-m \"stress and not windows_ci\"" claims stress, not windows_ci).
_MARKER_CLAIM_RE = re.compile(r'(?:pytest\.mark\.|-m\s+"?)(' + "|".join(_MARKER_LANES) + r")\b")
_DEFERRAL_PHRASES = (
    "recorded deliberately",
    "measured-durations decision, never a silent default",
)
_PLACEHOLDER_WORDS = frozenset({"n/a", "none", "tbd", "todo", "pending"})
_SURFACE_RE = re.compile(r"(tests/|module|corpus|windows_ci|nightly|e2e|architectural|#\d+)")
_EVIDENCE_POINTER_RE = re.compile(r"evidence:\s*(analysis/evidence/[\w.\-/]+\.json)")


# ---------------------------------------------------------------------------
# Shared loading helpers
# ---------------------------------------------------------------------------
# Preference order: ``origin/main`` first, matching the ``_PORT_BASE_REF``
# convention in ``test_archive_root_byte_identical.py`` -- a fresh CI checkout
# (actions/checkout, detached HEAD) only populates ``refs/remotes/origin/main``,
# not a local ``refs/heads/main``. Bare ``main`` is the fallback for a developer
# checkout with no ``origin`` remote configured.
_BASE_REF_CANDIDATES: tuple[str, ...] = ("origin/main", "main")


def _resolve_base_ref(cwd: Path) -> str:
    """Return the first candidate in ``_BASE_REF_CANDIDATES`` that resolves to a commit in ``cwd``.

    A missing base ref is a checkout/environment condition, not a code-invariant
    violation -- when neither candidate resolves, this skips the calling test
    rather than raising, so the base-diff gates (T015/T019) never hard-error on a
    checkout that simply lacks both refs.
    """
    for ref in _BASE_REF_CANDIDATES:
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )
        if probe.returncode == 0:
            return ref
    pytest.skip(f"base ref ({' / '.join(_BASE_REF_CANDIDATES)}) not resolvable in this checkout; pre-merge parity check cannot run")


def _base_registry(*, cwd: Path = _REPO_ROOT) -> dict[str, Any]:
    """The registry as committed on the resolved base ref -- the mission's before-picture."""
    ref = _resolve_base_ref(cwd)
    result = subprocess.run(
        ["git", "show", f"{ref}:.github/ci-module-registry.yml"],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=True,
    )
    payload = yaml.safe_load(result.stdout)
    assert isinstance(payload, dict), f"{ref}:.github/ci-module-registry.yml did not parse to a mapping"
    return payload


def _out_of_matrix_entries(registry: dict[str, Any]) -> list[dict[str, Any]]:
    entries = registry.get("out_of_matrix_test_dirs", [])
    assert isinstance(entries, list), "out_of_matrix_test_dirs must be a list of {reason, dirs} entries"
    return entries


# ---------------------------------------------------------------------------
# T015 -- evidence parity + freshness for changed shard_count rows
# ---------------------------------------------------------------------------
def _changed_shard_count_modules(head: dict[str, Any], base: dict[str, Any]) -> list[str]:
    base_counts = {row["module"]: row.get("shard_count") for row in _modules(base)}
    return [row["module"] for row in _modules(head) if row.get("shard_count") != base_counts.get(row["module"])]


def _capture_floor() -> str:
    assert _CAPTURE_FLOOR_PATH.exists(), f"capture floor missing: {_CAPTURE_FLOOR_PATH.relative_to(_REPO_ROOT)}"
    floor = _CAPTURE_FLOOR_PATH.read_text(encoding="utf-8").strip()
    assert floor, f"capture floor file is empty: {_CAPTURE_FLOOR_PATH}"
    return floor


def _parity_and_freshness_problems(changed: list[str], timings: dict[str, Any], floor: str) -> list[str]:
    provenance = timings.get("module_capture_provenance", {})
    durations = timings.get("module_test_durations", {})
    counts = timings.get("module_test_count", {})
    problems: list[str] = []
    for module in changed:
        prov = provenance.get(module)
        if not prov:
            problems.append(f"{module}: shard_count changed vs main but no module_capture_provenance entry")
            continue
        measured = prov.get("unique_tests_measured")
        n_durations = len(durations.get(module, []))
        n_count = counts.get(module)
        if not (measured == n_durations == n_count):
            problems.append(f"{module}: parity mismatch unique_tests_measured={measured} len(module_test_durations)={n_durations} module_test_count={n_count}")
        captured_at = str(prov.get("captured_at", ""))
        if captured_at < floor:
            problems.append(f"{module}: stale capture captured_at={captured_at!r} < floor {floor!r}")
    return problems


def test_evidence_parity_and_freshness_for_changed_modules() -> None:
    """Every module whose ``shard_count`` moved (or is new) this mission is backed by
    measured, parity-checked, floor-fresh capture provenance -- never a guess.

    Inert when no module's ``shard_count`` differs from ``main`` (including on
    ``main`` itself, post-merge) so this guard never reds an unrelated PR.
    """
    head = _load_registry()
    base = _base_registry()
    changed = _changed_shard_count_modules(head, base)
    if not changed:
        # No shard_count drift vs main -- nothing this mission promoted to verify.
        return

    timings = _load_timings()
    floor = _capture_floor()
    problems = _parity_and_freshness_problems(changed, timings, floor)
    assert not problems, "evidence parity/freshness violations:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# T016 -- marker-presence honesty
# ---------------------------------------------------------------------------
def _marker_claims(reason: str) -> set[str]:
    return {match.group(1) for match in _MARKER_CLAIM_RE.finditer(reason)}


def _tree_carries_marker(dirs: list[str], marker: str) -> bool:
    marker_token = f"pytest.mark.{marker}"
    for entry_dir in dirs:
        tree = _REPO_ROOT / entry_dir
        if not tree.exists():
            continue
        candidates = [tree] if tree.is_file() else list(tree.rglob("*.py"))
        for path in candidates:
            if marker_token in path.read_text(encoding="utf-8"):
                return True
    return False


def test_marker_presence_honesty_for_out_of_matrix_reasons() -> None:
    """A reason naming a marker lane must be backed by a real marker in its tree.

    A reason naming a lane the tree cannot reach (a disguised snapshot, #2979) fails.
    """
    registry = _load_registry()
    problems: list[str] = []
    for entry in _out_of_matrix_entries(registry):
        reason = str(entry.get("reason", ""))
        dirs = [str(d) for d in entry.get("dirs", [])]
        for marker in sorted(_marker_claims(reason)):
            if not _tree_carries_marker(dirs, marker):
                problems.append(f"{dirs[:2]}: reason claims the {marker!r} lane but no file under {dirs} carries pytest.mark.{marker}")
    assert not problems, "marker-presence honesty violations (#2979 disguised-snapshot class):\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# T017 -- reasons are decisions, never deferrals
# ---------------------------------------------------------------------------
def _is_deferral_or_placeholder(reason: str) -> bool:
    if any(phrase in reason for phrase in _DEFERRAL_PHRASES):
        return True
    return reason.strip().lower() in _PLACEHOLDER_WORDS


def test_out_of_matrix_reasons_are_decisions_not_deferrals() -> None:
    """No reason may be a snapshot/deferral, and every reason must name a surface.

    Makes "reasons are decisions, never a silent default" (#4369/#4374 philosophy)
    a permanent invariant rather than a one-time acceptance check.
    """
    registry = _load_registry()
    problems: list[str] = []
    for entry in _out_of_matrix_entries(registry):
        reason = " ".join(str(entry.get("reason", "")).split())
        dirs = [str(d) for d in entry.get("dirs", [])][:2]
        if _is_deferral_or_placeholder(reason):
            problems.append(f"{dirs}: reason is a deferral phrase or placeholder, not a decision")
        if not _SURFACE_RE.search(reason):
            problems.append(f"{dirs}: reason names no concrete covering surface")
    assert not problems, "non-decision out-of-matrix reasons:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# T018 -- coverage-equivalence pointer resolution (vacuous unless used)
# ---------------------------------------------------------------------------
def _subset_problem(dirs: list[str], pointer_rel: str, payload: dict[str, Any]) -> str | None:
    demoted = set(payload.get("demoted_covered", []))
    mirror = set(payload.get("mirror_covered", []))
    if not demoted or not mirror:
        return f"{dirs}: {pointer_rel} does not record both demoted_covered and mirror_covered sets"
    if not demoted <= mirror:
        return f"{dirs}: {pointer_rel} demoted_covered is not a subset of mirror_covered"
    return None


def test_coverage_pointer_reasons_resolve_and_subset() -> None:
    """A reason claiming coverage-equivalence via a structured pointer must resolve.

    The pointer file must exist (committed) and its stored JSON must show the
    demoted tree's covered set is a subset of the named in-matrix mirror -- this
    guard reads the JSON, it never re-runs coverage. Vacuous (auto-pass) when no
    reason uses this claim shape: the mission's evidence README records that
    mirror-equivalence capture was deferred to a follow-up rather than fabricated
    (``analysis/evidence/README.md``), so inventing a pointer here would itself be
    the disguised-snapshot this mission exists to eliminate.
    """
    registry = _load_registry()
    problems: list[str] = []
    pointer_seen = False
    for entry in _out_of_matrix_entries(registry):
        reason = str(entry.get("reason", ""))
        match = _EVIDENCE_POINTER_RE.search(reason)
        if not match:
            continue
        pointer_seen = True
        dirs = [str(d) for d in entry.get("dirs", [])][:2]
        pointer_rel = match.group(1)
        pointer_path = _MISSION_ROOT / pointer_rel
        if not pointer_path.exists():
            problems.append(f"{dirs}: evidence pointer {pointer_rel} does not exist")
            continue
        payload = json.loads(pointer_path.read_text(encoding="utf-8"))
        problem = _subset_problem(dirs, pointer_rel, payload)
        if problem:
            problems.append(problem)
    if not pointer_seen:
        # No reason carries a structured `evidence: analysis/evidence/<f>.json`
        # pointer -- nothing to resolve. Auto-pass; never invent a pointer.
        return
    assert not problems, "coverage-pointer resolution violations:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# T019 -- per-PR selection for this mission's expanded test_dirs
# ---------------------------------------------------------------------------
def _expanded_test_dirs_modules(head: dict[str, Any], base: dict[str, Any]) -> dict[str, dict[str, Any]]:
    base_dirs = {row["module"]: set(row.get("test_dirs") or []) for row in _modules(base)}
    expanded: dict[str, dict[str, Any]] = {}
    for row in _modules(head):
        name = row["module"]
        added = set(row.get("test_dirs") or []) - base_dirs.get(name, set())
        if added:
            expanded[name] = {"added_test_dirs": sorted(added), "roots": list(row.get("roots") or [])}
    return expanded


def _root_probe_path(root: str) -> str:
    """A representative source path under a registry ``roots`` glob (source routing)."""
    stripped = root.rstrip("/")
    if stripped.endswith("/**"):
        return f"{stripped[:-3]}/synthetic_module.py"
    return stripped


def _selection_problems(module: str, info: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for test_dir in info["added_test_dirs"]:
        synthetic_test = f"{test_dir}/synthetic_test.py"
        selected = select_modules([synthetic_test])
        if module not in selected:
            problems.append(f"{module}: test path {synthetic_test} does not select the owning module (got {sorted(selected)})")
    for root in info["roots"]:
        probe = _root_probe_path(root)
        selected = select_modules([probe])
        if module not in selected:
            problems.append(f"{module}: source path {probe} does not select the owning module (got {sorted(selected)})")
    return problems


def test_expanded_test_dirs_are_selected_per_pr() -> None:
    """A module row whose ``test_dirs`` this mission expanded (vs ``main``) is
    durably selected per-PR, for both a test-path change and a source-path change.

    Proves per-PR de-silencing re-runnably with zero net diff (Renata F3 / Paula
    F3), replacing the transient injected-red WP03 demonstrated live. Inert once
    the diff against ``main`` is empty (i.e. on ``main`` itself, post-merge) --
    this guard is about proving the mission's expansions route correctly while
    they are still a diff, not about asserting the mission is perpetually ongoing.
    """
    head = _load_registry()
    base = _base_registry()
    expanded = _expanded_test_dirs_modules(head, base)
    if not expanded:
        # Zero net diff vs main (e.g. running on main itself, post-merge) --
        # nothing this mission expanded to re-verify.
        return

    problems: list[str] = []
    for module, info in expanded.items():
        problems.extend(_selection_problems(module, info))
    assert not problems, "per-PR selection violations:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# Base-ref resolver -- proves the origin/main-preferred fallback (second-opinion
# architect review of this mission's WP04 landing pass: a bare ``main`` lookup
# errors on a fresh CI checkout, which is a detached HEAD with no local
# ``refs/heads/main``). Builds tiny throwaway git repos under ``tmp_path`` rather
# than touching this repo's own ambient refs -- this worktree's local ``main``
# is the real merge target, not a fixture.
# ---------------------------------------------------------------------------
def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Pedro Test",
        "GIT_AUTHOR_EMAIL": "pedro@example.invalid",
        "GIT_COMMITTER_NAME": "Pedro Test",
        "GIT_COMMITTER_EMAIL": "pedro@example.invalid",
        "HOME": str(cwd),
    }
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env, check=True)


def _init_repo_with_registry(repo: Path, *, branch: str, marker: str) -> str:
    """git-init a throwaway repo on ``branch``, commit a minimal registry carrying ``marker``, return HEAD sha."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    github_dir = repo / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)
    (github_dir / "ci-module-registry.yml").write_text(yaml.safe_dump({"out_of_matrix_test_dirs": [], "modules": [], "_test_marker": marker}), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"registry marker {marker}")
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def test_resolve_base_ref_prefers_origin_main_when_both_exist_and_differ(tmp_path: Path) -> None:
    """When ``origin/main`` and local ``main`` both resolve to different commits, origin/main wins."""
    repo = tmp_path / "repo"
    main_sha = _init_repo_with_registry(repo, branch="main", marker="main-branch")
    origin_sha = _init_repo_with_registry(repo, branch="main", marker="origin-branch")
    assert origin_sha != main_sha
    _git(repo, "update-ref", "refs/remotes/origin/main", origin_sha)
    _git(repo, "reset", "-q", "--hard", main_sha)  # move local main back so the two refs diverge

    assert _resolve_base_ref(repo) == "origin/main"
    registry = _base_registry(cwd=repo)
    assert registry["_test_marker"] == "origin-branch"


def test_resolve_base_ref_falls_back_to_main_when_origin_absent(tmp_path: Path) -> None:
    """When no ``origin/main`` ref exists, the resolver falls back to local ``main``."""
    repo = tmp_path / "repo"
    _init_repo_with_registry(repo, branch="main", marker="main-only")

    assert _resolve_base_ref(repo) == "main"
    registry = _base_registry(cwd=repo)
    assert registry["_test_marker"] == "main-only"


def test_resolve_base_ref_skips_when_neither_ref_resolves(tmp_path: Path) -> None:
    """When neither ``origin/main`` nor ``main`` resolves, the resolver SKIPS -- a checkout condition, not a red."""
    repo = tmp_path / "repo"
    _init_repo_with_registry(repo, branch="trunk", marker="trunk-only")

    with pytest.raises(pytest.skip.Exception):
        _resolve_base_ref(repo)
    with pytest.raises(pytest.skip.Exception):
        _base_registry(cwd=repo)


@pytest.fixture
def published_registry_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A real non-main PR target owns a registry absent on old origin/main."""
    import sys
    from scripts.ci import gate_selection
    from tests.architectural import test_archive_root_byte_identical as authority

    repo = tmp_path / "published-registry"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "seed.txt").write_text("old main lacks registry\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "old main")
    main = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "remote", "add", "origin", "https://github.com/crucible-energy/spec-kitty.git")
    _git(repo, "update-ref", "refs/remotes/origin/main", main)
    registry = repo / ".github/ci-module-registry.yml"
    registry.parent.mkdir()
    base_registry = {
        "modules": [{"module": "fixture_module", "shard_count": 1, "test_dirs": ["tests/demo"], "roots": ["src/demo/**"]}],
        "out_of_matrix_test_dirs": [],
        "_test_marker": "published-target",
    }
    registry.write_text(yaml.safe_dump(base_registry))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "published registry baseline")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/patch-registry", base)
    head_registry = json.loads(json.dumps(base_registry))
    head_registry["modules"][0].update(shard_count=2, test_dirs=["tests/demo", "tests/extra"])
    head_registry["_test_marker"] = "head-current"
    registry.write_text(yaml.safe_dump(head_registry))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "PR registry changes")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    tree = _git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
    merge = _git(repo, "commit-tree", tree, "-p", base, "-p", head, "-m", "runner merge").stdout.strip()
    _git(repo, "checkout", "-q", "--detach", merge)
    event = {
        "number": 81,
        "repository": {"full_name": "crucible-energy/spec-kitty"},
        "pull_request": {
            "number": 81,
            "base": {"ref": "patch-registry", "sha": base, "repo": {"full_name": "crucible-energy/spec-kitty"}},
            "head": {"sha": head, "repo": {"full_name": "crucible-energy/spec-kitty"}},
            "merge_commit_sha": None,
        },
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event))
    for key, value in {
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REPOSITORY": "crucible-energy/spec-kitty",
        "GITHUB_BASE_REF": "patch-registry",
        "GITHUB_REF": "refs/pull/81/merge",
        "GITHUB_SHA": merge,
        "GITHUB_EVENT_PATH": str(event_file),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(authority, "REPO_ROOT", repo)
    monkeypatch.setattr(sys.modules[__name__], "_REPO_ROOT", repo)
    monkeypatch.setattr(sys.modules[__name__], "_load_registry", lambda: yaml.safe_load(registry.read_text()))
    monkeypatch.setattr(gate_selection, "DEFAULT_REGISTRY_PATH", registry)
    floor = repo / "capture-floor.txt"
    floor.write_text("2026-10-01T00:00:00Z\n")
    monkeypatch.setattr(sys.modules[__name__], "_CAPTURE_FLOOR_PATH", floor)
    timings = {
        "module_capture_provenance": {"fixture_module": {"unique_tests_measured": 2, "captured_at": "2026-10-09T00:00:00Z"}},
        "module_test_durations": {"fixture_module": [1.0, 2.0]},
        "module_test_count": {"fixture_module": 2},
    }
    monkeypatch.setattr(sys.modules[__name__], "_load_timings", lambda: timings)
    return {
        "root": repo,
        "base": base,
        "head": head,
        "event": event,
        "event_file": event_file,
        "registry": registry,
        "head_registry": head_registry,
        "timings": timings,
    }


@pytest.mark.parametrize("capture", ["fresh", "stale", "parity", "missing"])
def test_non_main_registry_base_keeps_t015_nonvacuous(published_registry_checkout: dict[str, Any], capture: str) -> None:
    case = published_registry_checkout
    assert _resolve_base_ref(case["root"]) == case["base"]
    assert _base_registry(cwd=case["root"])["_test_marker"] == "published-target"
    if capture == "fresh":
        test_evidence_parity_and_freshness_for_changed_modules()
        return
    if capture == "stale":
        case["timings"]["module_capture_provenance"]["fixture_module"]["captured_at"] = "2026-09-01T00:00:00Z"
    elif capture == "parity":
        case["timings"]["module_test_count"]["fixture_module"] = 1
    else:
        case["timings"]["module_capture_provenance"] = {}
    with pytest.raises(AssertionError, match="evidence parity/freshness violations"):
        test_evidence_parity_and_freshness_for_changed_modules()


def test_non_main_registry_base_keeps_t019_nonvacuous(published_registry_checkout: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.ci import gate_selection

    case = published_registry_checkout
    assert _base_registry(cwd=case["root"])["_test_marker"] == "published-target"
    test_expanded_test_dirs_are_selected_per_pr()
    lost_routing = case["root"] / ".github/lost-routing.yml"
    rows = json.loads(json.dumps(case["head_registry"]))
    rows["modules"][0]["test_dirs"] = ["tests/demo"]
    lost_routing.write_text(yaml.safe_dump(rows))
    monkeypatch.setattr(gate_selection, "DEFAULT_REGISTRY_PATH", lost_routing)
    with pytest.raises(AssertionError, match="tests/extra/synthetic_test.py does not select"):
        test_expanded_test_dirs_are_selected_per_pr()


@pytest.mark.parametrize("tamper", ["target-ref", "event-head", "wrong-cwd"])
def test_non_main_registry_base_refuses_tamper(published_registry_checkout: dict[str, Any], tamper: str, tmp_path: Path) -> None:
    case = published_registry_checkout
    if tamper == "target-ref":
        _git(case["root"], "update-ref", "-d", "refs/remotes/origin/patch-registry")
    elif tamper == "event-head":
        case["event"]["pull_request"]["head"]["sha"] = case["base"]
        case["event_file"].write_text(json.dumps(case["event"]))
    cwd = case["root"]
    if tamper == "wrong-cwd":
        cwd = tmp_path / "other-checkout"
        _init_repo_with_registry(cwd, branch="main", marker="different-checkout")
    with pytest.raises(pytest.fail.Exception, match="PR|checkout"):
        _resolve_base_ref(cwd)
