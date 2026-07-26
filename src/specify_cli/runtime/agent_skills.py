"""Bootstrap user-global canonical doctrine skills."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path

from specify_cli.runtime.bootstrap import _get_cli_version, _lock_exclusive
from specify_cli.runtime.home import get_kittify_home
from specify_cli.skills.command_renderer import ensure_skill_frontmatter
from specify_cli.skills.paths import get_primary_global_skill_root, iter_installable_agents
from specify_cli.skills.registry import CanonicalSkill, SkillRegistry
from specify_cli.skills.retired import RETIRED_CANONICAL_SKILL_NAMES
from specify_cli.template import get_local_repo_root

logger = logging.getLogger(__name__)

_VERSION_FILENAME = "agent-skills.lock"
_LOCK_FILENAME = ".agent-skills.lock"


def _make_path_writable(path: str | Path) -> None:
    path = Path(path)
    try:
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
    except OSError:
        logger.debug("Could not make skill path writable: %s", path, exc_info=True)


def _force_writable_and_retry(function: Callable[[str], object], path: str, _exc_info: object) -> None:
    _make_path_writable(path)
    function(path)


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except PermissionError:
        _make_path_writable(path)
        path.unlink()


def _safe_rmtree(path: Path) -> None:
    shutil.rmtree(path, onerror=_force_writable_and_retry)


def _discover_registry() -> SkillRegistry | None:
    """Resolve the canonical bundled skill registry."""
    try:
        registry = SkillRegistry.from_package()
        if registry.discover_skills():
            return registry
    except Exception:
        logger.debug("Package skill registry unavailable", exc_info=True)

    local_repo = get_local_repo_root()
    if local_repo is not None:
        registry = SkillRegistry.from_local_repo(local_repo)
        if registry.discover_skills():
            return registry

    return None


def _unique_global_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    for agent_key in iter_installable_agents():
        root = get_primary_global_skill_root(agent_key)
        if root is None or root in seen:
            continue
        seen.add(root)
        roots.append(root)

    return roots


def _retired_skill_cleanup_needed(roots: list[Path]) -> bool:
    for root in roots:
        for skill_name in RETIRED_CANONICAL_SKILL_NAMES:
            dest = root / skill_name
            if dest.exists() or dest.is_symlink():
                return True
    return False


def _expected_skill_file_content(skill: CanonicalSkill, source_file: Path) -> bytes:
    if source_file == skill.skill_md:
        content = source_file.read_text(encoding="utf-8")
        normalized: str = ensure_skill_frontmatter(content, skill.name)
        return normalized.encode("utf-8")
    return source_file.read_bytes()


def _content_digest(content: bytes) -> bytes:
    return hashlib.sha256(content).digest()  # noqa: TID251 - file-integrity checksum of raw skill bytes, not charter freshness


def _is_integral_skill_root(root: Path, skills: list[CanonicalSkill]) -> bool:
    for skill in skills:
        for source_file in skill.all_files:
            try:
                relative_path = source_file.relative_to(skill.skill_dir)
                installed_file = root / skill.name / relative_path
                expected_content = _expected_skill_file_content(skill, source_file)
                if _content_digest(installed_file.read_bytes()) != _content_digest(expected_content):
                    return False
            except (OSError, UnicodeDecodeError, ValueError):
                return False
    return True


def _write_skill_file(source_file: Path, dest: Path, content: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=dest.parent,
        prefix=f".{dest.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(content)
        mode = source_file.stat().st_mode & ~0o222
        temporary_path.chmod(mode)
        os.replace(temporary_path, dest)
    except OSError:
        _safe_unlink(temporary_path)
        raise


def _sync_skill_root(root: Path, registry: SkillRegistry) -> None:
    root.mkdir(parents=True, exist_ok=True)
    skills = registry.discover_skills()

    retired_names = RETIRED_CANONICAL_SKILL_NAMES - {skill.name for skill in skills}
    for existing in root.iterdir():
        if existing.name in retired_names:
            if existing.is_symlink() or existing.is_file():
                _safe_unlink(existing)
            elif existing.is_dir():
                _safe_rmtree(existing)

    for skill in skills:
        for source_file in skill.all_files:
            relative_path = source_file.relative_to(skill.skill_dir)
            _write_skill_file(
                source_file,
                root / skill.name / relative_path,
                _expected_skill_file_content(skill, source_file),
            )


def ensure_global_agent_skills() -> None:
    """Ensure user-global canonical skill roots are populated for this CLI version."""
    kittify_home = get_kittify_home()
    kittify_home.mkdir(parents=True, exist_ok=True)
    cache_dir = kittify_home / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    version_file = cache_dir / _VERSION_FILENAME
    cli_version = _get_cli_version()
    registry = _discover_registry()
    if registry is None:
        logger.error("Cannot verify global agent skills: canonical registry is unavailable")
        return

    skills = registry.discover_skills()
    roots = _unique_global_roots()
    if (
        version_file.exists()
        and version_file.read_text().strip() == cli_version
        and not _retired_skill_cleanup_needed(roots)
        and all(_is_integral_skill_root(root, skills) for root in roots)
    ):
        return

    lock_path = cache_dir / _LOCK_FILENAME
    lock_fd = open(lock_path, "w")  # noqa: SIM115
    try:
        _lock_exclusive(lock_fd)
        if (
            version_file.exists()
            and version_file.read_text().strip() == cli_version
            and not _retired_skill_cleanup_needed(roots)
            and all(_is_integral_skill_root(root, skills) for root in roots)
        ):
            return

        for root in roots:
            _sync_skill_root(root, registry)
        version_file.write_text(cli_version)
    finally:
        lock_fd.close()
