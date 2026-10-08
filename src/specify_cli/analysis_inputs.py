"""Conservative declarative dependency closure for report-only analysis.

Runtime/status/cache outputs are deliberately not inputs. Explicit authority
references are included even when absent; directory membership is represented
by the set of entries, so adding a new authority also invalidates a report.
"""

from __future__ import annotations

import json
import os
import hashlib
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from charter.activation.context_renderers.authority_paths import DEFAULT_AUTHORITY_PATHS
from charter.activation.pack_context import resolve_charter_yaml_pointer
from charter.bundle import CHARTER_MD, CHARTER_YAML
from charter.drg import load_pack_registry
from charter.pack_paths import PackRootNotFound, built_in_root
from kernel.paths import get_package_asset_root


class MaterialInputError(ValueError):
    """The declared dependency closure cannot be safely represented."""


def _mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        raise MaterialInputError(f"Malformed material input: {path.name}") from exc
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise MaterialInputError(f"Expected mapping in {path.name}")
    return value


def _safe_path(root: Path, path: Path) -> Path:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise MaterialInputError("External mutable analysis authority is unsupported") from exc
    cursor = root
    for part in relative.parts:
        if part == "..":
            raise MaterialInputError("Analysis authority escapes repository")
        cursor /= part
        if cursor.is_symlink():
            raise MaterialInputError("Analysis authority contains a symlink")
    return path


def _contained_alias_target(root: Path, alias: Path, raw_target: str) -> Path:
    """Walk a relative link without permitting an intermediate escape or link."""
    target = Path(raw_target)
    if target.is_absolute():
        raise MaterialInputError("Analysis authority symlink target must be a contained relative reference")
    cursor = _safe_path(root, alias.parent)
    for part in target.parts:
        cursor = cursor.parent if part == ".." else cursor / part
        try:
            cursor.relative_to(root)
        except ValueError as exc:
            raise MaterialInputError("Analysis authority symlink escapes repository") from exc
        if cursor.is_symlink():
            raise MaterialInputError("Analysis authority symlink chain or cycle is unsupported")
        if not cursor.is_dir():
            raise MaterialInputError("Analysis authority symlink target is dangling or not a directory")
    if cursor == root or alias.is_relative_to(cursor):
        raise MaterialInputError("Analysis authority symlink creates a directory cycle")
    return cursor


def _require_tracked_alias(root: Path, alias: Path, raw_target: str) -> None:
    """HEAD must contain this exact link, not an untracked authority proposal."""
    from kernel.git import GitCommandError, run_git, tree_entry

    relative = alias.relative_to(root).as_posix()
    try:
        entry = tree_entry(root, "HEAD", relative)
        if entry is None or entry.mode != "120000" or entry.type != "blob":
            raise MaterialInputError("Analysis authority symlink is not a committed canonical alias")
        blob = run_git(root, "cat-file", "blob", entry.oid).stdout
    except (GitCommandError, OSError) as exc:
        raise MaterialInputError("Analysis authority symlink ownership cannot be established") from exc
    if blob != os.fsencode(raw_target):
        raise MaterialInputError("Analysis authority symlink differs from its committed target")


def _canonical_alias_entry(root: Path, alias: Path, canonical: set[Path]) -> tuple[Path, dict[str, str | None]]:
    from specify_cli.analysis_report import _sha256_text

    _safe_path(root, alias.parent)
    raw_target = os.readlink(alias)
    target = _contained_alias_target(root, alias, raw_target)
    if target not in canonical:
        raise MaterialInputError("Analysis authority symlink target is not independently selected canonical authority")
    _require_tracked_alias(root, alias, raw_target)
    identity = {"kind": "canonical-directory-alias/v1", "target": raw_target, "canonical": target.relative_to(root).as_posix()}
    return target, {"path": alias.relative_to(root).as_posix(), "sha256": _sha256_text(json.dumps(identity, sort_keys=True))}


def _material_closure(
    root: Path,
    selected: list[Path],
    canonical: set[Path],
    *,
    paths: set[Path] | None = None,
    aliases: dict[Path, dict[str, str | None]] | None = None,
) -> tuple[set[Path], dict[Path, dict[str, str | None]]]:
    """Visit canonical content once, retaining link identity without alias copies."""
    paths = set() if paths is None else paths
    aliases = {} if aliases is None else aliases
    active: set[Path] = set()

    def include(path: Path) -> None:
        if path in active:
            raise MaterialInputError("Analysis authority symlink creates a directory cycle")
        if path in paths:
            return
        if path.is_symlink():
            target, entry = _canonical_alias_entry(root, path, canonical)
            paths.add(path)
            aliases[path] = entry
            include(target)
            return
        path = _safe_path(root, path)
        if path.is_dir():
            paths.add(path)
            active.add(path)
            try:
                for child in sorted(path.iterdir()):
                    include(child)
            finally:
                active.remove(path)
        else:
            if path.exists() and not path.is_file():
                raise MaterialInputError("Non-regular analysis authority is unsupported")
            paths.add(path)

    for path in selected:
        include(path)
    return paths, aliases


def _declared_paths(charter: dict[str, Any]) -> list[str]:
    from charter.activation.sync import apply_legacy_governance_selection_key_compat

    governance = charter.get("governance", {})
    charter_cfg = apply_legacy_governance_selection_key_compat(governance).get("charter", {}) if isinstance(governance, dict) else {}
    if not isinstance(charter_cfg, dict):
        raise MaterialInputError("governance.charter must be a mapping")
    paths = list(DEFAULT_AUTHORITY_PATHS)
    for key in ("authority_paths", "governance_references"):
        declared = charter_cfg.get(key, [])
        if not isinstance(declared, list) or not all(isinstance(value, str) for value in declared):
            raise MaterialInputError(f"{key} must be a list of paths")
        paths.extend(declared)
    return paths


def _references(value: Any, field: str) -> list[str]:
    paths = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key == field and isinstance(nested, str) and nested:
                paths.append(nested)
            else:
                paths.extend(_references(nested, field))
    elif isinstance(value, list):
        for nested in value:
            paths.extend(_references(nested, field))
    return paths


def _entry(path: Path, root: Path, feature_dir: Path) -> dict[str, str | None]:
    from specify_cli.analysis_report import _artifact_hash_entry, _sha256_text
    from specify_cli.frontmatter import FrontmatterError, FrontmatterManager
    from specify_cli.migration.strip_frontmatter import MUTABLE_FIELDS

    relative = path.relative_to(root).as_posix()
    if path.is_dir():
        return {"path": relative, "sha256": "directory"}
    if not path.exists():
        return {"path": relative, "sha256": None}
    if path.parent == feature_dir / "tasks" and path.suffix == ".md" and path.name.startswith("WP"):
        try:
            metadata, body = FrontmatterManager().read(path)
        except FrontmatterError as exc:
            raise MaterialInputError(f"Invalid WP definition: {path.name}") from exc
        static = {key: value for key, value in metadata.items() if key not in MUTABLE_FIELDS}
        return {"path": relative, "sha256": _sha256_text(json.dumps(static, sort_keys=True, default=str) + "\n" + body)}
    return _artifact_hash_entry(path, root)


def _source_paths(charter: dict[str, Any], root: Path) -> list[Path]:
    paths = []
    for value in _references(charter, "source_path"):
        # Bundled provenance is covered by its digest; URL provenance is
        # declarative charter text, not a filesystem dependency.
        if value.startswith("${SPEC_KITTY_PACKS_ROOT}/") or "://" in value:
            continue
        if "$" in value:
            raise MaterialInputError("Unresolved external authority source is unsupported")
        paths.append(root / value)
    return paths


@dataclass(frozen=True)
class _TemplateObservation:
    sha256: str
    identity: tuple[tuple[int, ...], ...]


def _template_identity(path: Path) -> tuple[tuple[int, ...], ...]:
    from specify_cli.runtime.asset_preparation import asset_parent_states

    parents = asset_parent_states(path)
    rows: list[tuple[int, ...]] = []
    for parent, state in parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) and not (state.kind == "symlink" and stat.S_ISLNK(info.st_mode) and os.readlink(parent) == state.target):
            raise MaterialInputError("Selected template ancestry changed before content read")
        identity: tuple[int, ...] = (info.st_dev, info.st_ino, info.st_mode)
        # Descriptor traversal prevents ancestor-link reads. Only the immediate
        # asset directory's metadata participates in the read-window guard;
        # system/shared ancestor membership is unrelated to this selection.
        if parent == path.parent:
            identity += (info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        rows.append(identity)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise MaterialInputError("Selected template is not a regular non-symlink asset")
    rows.append((info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
    return tuple(rows)


def _open_template(path: Path) -> int:
    """Hold non-following ancestor descriptors where the platform supports them."""
    from specify_cli.runtime.asset_preparation import asset_parent_states

    canonical = path
    # Only the existing provenance seam's exact macOS system aliases qualify.
    # Resolve those spellings explicitly, never arbitrary user symlinks.
    for parent, state in asset_parent_states(path):
        if state.kind == "symlink":
            canonical = parent.parent / str(state.target) / path.relative_to(parent)
    asset_parent_states(canonical)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    if os.open not in os.supports_dir_fd or not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise MaterialInputError("Descriptor-safe selected template reads are unsupported on this platform")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(canonical.anchor, directory_flags)
    try:
        for part in canonical.parts[1:-1]:
            child = os.open(part, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return os.open(canonical.name, flags, dir_fd=descriptor)
    finally:
        os.close(descriptor)


def _observe_template(path: Path) -> _TemplateObservation:
    """Read exact bytes with a stable, non-link source/destination identity."""
    try:
        before = _template_identity(path)
        with os.fdopen(_open_template(path), "rb") as stream:
            info = os.fstat(stream.fileno())
            opened = (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if opened != before[-1]:
                raise MaterialInputError("Selected template changed before content read")
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if _template_identity(path) != before:
            raise MaterialInputError("Selected template changed during content read")
        # Parent timestamps guard only this read; sibling writes during package
        # traversal are not changes to selected authority. Identity and content
        # are rechecked across the full collection and pinned in the report.
        stable = tuple(row[:3] for row in before[:-1]) + (before[-1],)
        return _TemplateObservation(digest, stable)
    except MaterialInputError:
        raise
    except (OSError, ValueError) as exc:
        raise MaterialInputError("Selected template provenance is unsafe or unverifiable") from exc


def _package_inputs(proofs: dict[Path, _TemplateObservation] | None = None) -> dict[str, dict[str, str | None]]:
    """Content-pin bundled authority without embedding machine-local paths."""
    from specify_cli.analysis_report import _sha256_file, _sha256_text

    if os.environ.get("SPEC_KITTY_PACKS_ROOT") or os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        raise MaterialInputError("Environment-selected mutable package authority is unsupported")
    result = {}
    try:
        roots = (("built-in", built_in_root()), ("mission-assets", get_package_asset_root()))
    except (PackRootNotFound, OSError) as exc:
        raise MaterialInputError("Bundled analysis authority unavailable") from exc
    for label, root in roots:
        rows = []
        # Required membership comes from the selected proofs, not traversal or
        # present-file probes: a temporarily missing source must remain required.
        required = {path for path in (proofs or {}) if path.is_relative_to(root)}
        contributed: set[Path] = set()
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise MaterialInputError("Bundled analysis authority contains a symlink")
            if path.is_file() and "__pycache__" not in path.parts:
                if proofs is not None and path in proofs:
                    observed = _observe_template(path)
                    if observed != proofs[path]:
                        raise MaterialInputError("Selected bundled template changed before package pinning")
                    digest = observed.sha256
                    contributed.add(path)
                else:
                    digest = _sha256_file(path)
                rows.append(f"{path.relative_to(root).as_posix()}:{digest}")
        if contributed != required:
            raise MaterialInputError(f"Selected bundled template missing from {label} pin")
        result[f"package:{label}"] = {"path": None, "sha256": _sha256_text("\n".join(rows))}
    return result


def _qualify_global_template(mission: str, name: str, path: Path, proofs: dict[Path, _TemplateObservation]) -> dict[str, str | None]:
    from charter.activation.resolver import DoctrineService
    from kernel.paths import get_kittify_home
    from specify_cli.analysis_report import _sha256_text
    from specify_cli.runtime.merge import MANAGED_DIRS

    if os.environ.get("SPEC_KITTY_PACKS_ROOT") or os.environ.get("SPEC_KITTY_TEMPLATE_ROOT"):
        raise MaterialInputError("Environment-selected mutable package authority is unsupported")
    assets = get_package_asset_root()
    source = DoctrineService.resolve_package_default_asset_path(missions_root=assets, mission=mission, subdir="templates", name=name)
    expected = get_kittify_home() / "missions" / mission / "templates" / name
    if not path.is_absolute() or ".." in path.parts:
        raise MaterialInputError("Selected global template has an unsafe path identity")
    if f"missions/{mission}" not in MANAGED_DIRS or path != expected or source is None or not source.is_relative_to(assets):
        raise MaterialInputError("External mutable global template authority is unsupported")
    bundled = _observe_template(source)
    replica = _observe_template(path)
    if replica.sha256 != bundled.sha256:
        raise MaterialInputError("Selected global template differs from its exact bundled source")
    for selected, observed in ((source, bundled), (path, replica)):
        if selected in proofs and proofs[selected] != observed:
            raise MaterialInputError("Selected template changed during input collection")
        proofs[selected] = observed
    # The bytes remain pinned by package:mission-assets; this digest additionally
    # binds actual selection and replica identity, so even equal-byte retargeting
    # cannot reuse a report from another selection. No external path is writable.
    identity = {
        "kind": "bundled-global-template/v1",
        "mission": mission,
        "name": name,
        "source": source.relative_to(assets).as_posix(),
        "sha256": bundled.sha256,
        "replica": str(path.absolute()),
        "identity": replica.identity,
    }
    return {"path": None, "sha256": _sha256_text(json.dumps(identity, sort_keys=True))}


def _resolved_template_paths(root: Path, feature_dir: Path, selections: dict[str, dict[str, str | None]], proofs: dict[Path, _TemplateObservation]) -> list[Path]:
    from charter.activation.mission_type_profiles import resolve_mission_type_context
    from charter.activation.pack_context import CharterPackConfigError
    from specify_cli.runtime.resolver import ResolutionTier, resolve_configured_template

    metadata = _mapping(_safe_path(root, feature_dir / "meta.json"))
    mission_type = metadata.get("mission_type")
    if mission_type is None:
        return []
    try:
        context = resolve_mission_type_context(root, mission_type=mission_type)
    except CharterPackConfigError as exc:
        raise MaterialInputError("Configured charter activation is invalid") from exc
    paths = []
    template_set = context.template_set or {}
    for kind in template_set:
        resolved = resolve_configured_template(kind, root, context)
        if resolved.tier is ResolutionTier.GLOBAL:
            raise MaterialInputError("External mutable global template authority is unsupported")
        if resolved.tier is ResolutionTier.GLOBAL_MISSION:
            if resolved.mission != context.mission_type:
                raise MaterialInputError("Selected global template has a foreign mission identity")
            selections[f"template-selection:{kind}"] = _qualify_global_template(resolved.mission, template_set[kind], resolved.path, proofs)
            continue
        if resolved.tier is not ResolutionTier.PACKAGE_DEFAULT:
            paths.append(resolved.path)
    return paths


def collect_material_inputs(feature_dir: Path, repo_root: Path) -> dict[str, dict[str, str | None]]:
    """Collect project-owned material inputs, using canonical path authorities.

    This mode rejects external mutable org packs rather than pretending that a
    project Git transaction can establish their committed state.
    Committed relative directory aliases may reference an independently selected
    canonical authority in this same root. Their link identity is material;
    content is visited only at the canonical path. Other symlinks remain unsafe.
    """
    from specify_cli.analysis_report import _hash_inputs

    root = repo_root.absolute()
    # Bootstrap configuration remains strict: aliases cannot select the charter
    # or add authority declarations through a different configuration source.
    config_path = _safe_path(root, root / ".kittify/config.yaml")
    config = _mapping(config_path)
    charter_path = _safe_path(root, resolve_charter_yaml_pointer(root, config) or root / CHARTER_YAML)
    charter = _mapping(charter_path)
    selected = [config_path, charter_path]
    for name in (*_hash_inputs(), "meta.json", "wps.yaml"):
        selected.append(feature_dir / name)
    selected.append(feature_dir / "tasks")
    # Only declarative subtrees: no charter context-state, synthesis manifest,
    # operation logs, runtime cache, status streams or generated task state.
    for name in ("missions", "overrides", "doctrine", "templates", "command-templates"):
        selected.append(root / ".kittify" / name)
    for name in (CHARTER_MD.name, "interview/answers.yaml", "_LIBRARY"):
        selected.append(charter_path.parent / name)
    declared = [root / value for value in _declared_paths(charter)]
    # Only independently declared, non-alias authority endpoints qualify. Being
    # somewhere under the root (or under a broad selection) is not permission.
    canonical = {_safe_path(root, path) for path in declared if not path.is_symlink()}
    selected.extend(declared)
    for pack in load_pack_registry(root).packs:
        selected.append(pack.effective_root(root))

    for value in _references(charter, "local_path"):
        selected.append(charter_path.parent / value)
    selected.extend(_source_paths(charter, root))
    # Resolution may read Mission metadata and project/pack definitions. Restore
    # validation of all selected prerequisites before those content readers run.
    paths, aliases = _material_closure(root, selected, canonical)
    selections: dict[str, dict[str, str | None]] = {}
    proofs: dict[Path, _TemplateObservation] = {}
    templates = _resolved_template_paths(root, feature_dir, selections, proofs)
    paths, aliases = _material_closure(root, templates, canonical, paths=paths, aliases=aliases)
    result: dict[str, dict[str, str | None]] = {}
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        # Directory sentinels and missing-file sentinels are distinct. The
        # complete key set detects additions/removals without hashing outputs.
        result[f"material:{relative}"] = aliases[path] if path in aliases else _entry(path, root, feature_dir)
    result.update(_package_inputs(proofs))
    # Couple equality to the exact package material pins returned in this pass.
    # Recheck after the full closure read, including ancestry and replica identity.
    for path, observed in proofs.items():
        if _observe_template(path) != observed:
            raise MaterialInputError("Selected template changed during input collection")
    result.update(selections)
    return result
