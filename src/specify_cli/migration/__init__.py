"""Migration helpers for Spec Kitty canonical context architecture.

Provides schema version gate (WP11), one-shot migration steps (WP12), and
the state rebuild + atomic runner (WP13).
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

# This callable shares a name with its submodule. Retain its eager identity,
# as before, so importing the submodule cannot replace the public function.
from .backfill_ownership import backfill_ownership

if TYPE_CHECKING:
    from .schema_version import (
        REQUIRED_SCHEMA_VERSION,
        SCHEMA_CAPABILITIES,
        CompatibilityResult,
        CompatibilityStatus,
        check_compatibility,
        get_project_schema_version,
    )
    from .gate import check_schema_version

    # WP12: one-shot migration helpers
    from .backfill_identity import (
        backfill_mission_ids,
        backfill_project_uuid,
        backfill_wp_ids,
    )
    from .normalize_mission_lifecycle import (
        NormalizeMissionLifecycleResult,
        normalize_repo as normalize_mission_lifecycle_repo,
    )
    from .strip_frontmatter import StripResult, strip_mutable_fields
    from .rewrite_shims import RewriteResult, rewrite_agent_shims

    # WP13: atomic runner. The per-mission event rebuild is exposed through the
    # canonical ``mission_state.rebuild_mission_event_log`` entry (#1754); the
    # underlying ``rebuild_state`` implementation is an internal detail and is no
    # longer re-exported from this package.
    from .runner import MigrationReport, run_migration

_EXPORT_MODULES = {
    "REQUIRED_SCHEMA_VERSION": ("schema_version", "REQUIRED_SCHEMA_VERSION"),
    "SCHEMA_CAPABILITIES": ("schema_version", "SCHEMA_CAPABILITIES"),
    "CompatibilityResult": ("schema_version", "CompatibilityResult"),
    "CompatibilityStatus": ("schema_version", "CompatibilityStatus"),
    "check_compatibility": ("schema_version", "check_compatibility"),
    "get_project_schema_version": ("schema_version", "get_project_schema_version"),
    "check_schema_version": ("gate", "check_schema_version"),
    "backfill_project_uuid": ("backfill_identity", "backfill_project_uuid"),
    "backfill_mission_ids": ("backfill_identity", "backfill_mission_ids"),
    "backfill_wp_ids": ("backfill_identity", "backfill_wp_ids"),
    "NormalizeMissionLifecycleResult": ("normalize_mission_lifecycle", "NormalizeMissionLifecycleResult"),
    "normalize_mission_lifecycle_repo": ("normalize_mission_lifecycle", "normalize_repo"),
    "StripResult": ("strip_frontmatter", "StripResult"),
    "strip_mutable_fields": ("strip_frontmatter", "strip_mutable_fields"),
    "RewriteResult": ("rewrite_shims", "RewriteResult"),
    "rewrite_agent_shims": ("rewrite_shims", "rewrite_agent_shims"),
    "MigrationReport": ("runner", "MigrationReport"),
    "run_migration": ("runner", "run_migration"),
}

__all__ = [
    # schema version (WP11)
    "REQUIRED_SCHEMA_VERSION",
    "SCHEMA_CAPABILITIES",
    "CompatibilityResult",
    "CompatibilityStatus",
    "check_compatibility",
    "get_project_schema_version",
    "check_schema_version",
    # identity backfill (WP12)
    "backfill_project_uuid",
    "backfill_mission_ids",
    "backfill_wp_ids",
    # ownership backfill (WP12)
    "backfill_ownership",
    # lifecycle normalization
    "NormalizeMissionLifecycleResult",
    "normalize_mission_lifecycle_repo",
    # frontmatter strip (WP12)
    "StripResult",
    "strip_mutable_fields",
    # shim rewrite (WP12)
    "RewriteResult",
    "rewrite_agent_shims",
    # atomic runner (WP13)
    "MigrationReport",
    "run_migration",
]


def __getattr__(name: str) -> Any:
    target = _EXPORT_MODULES.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = target
    value = getattr(import_module(f"{__name__}.{module}"), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
