"""Charter parsing and configuration extraction.

This subpackage provides tools for:
- Parsing charter markdown into structured sections
- Extracting configuration from markdown tables, YAML blocks, and prose
- Validating extracted config against Pydantic schemas
- Emitting YAML config files for consumption by other modules

Provides:
- load_governance_config() / load_directives_config(): read the
  hand-authored ``governance`` / ``directives`` sections directly from
  ``charter.yaml`` (IC-04 -- the prose->triad scrape is retired).
- sync(): retained for its ``charter.md`` staleness-check contract; no
  longer extracts or writes anything (see ``charter.sync`` module docstring).
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

# Preserve the existing function/submodule collision regardless of import order.
from .sync import sync

if TYPE_CHECKING:
    from .bundle import CANONICAL_MANIFEST, CharterBundleManifest, SCHEMA_VERSION
    from .catalog import DoctrineCatalog, load_doctrine_catalog
    from .compiler import CompiledCharter, CharterReference, WriteBundleResult, compile_charter, write_compiled_charter
    from .context import CharterContextResult, build_charter_context
    from .interview import (
        CharterInterview,
        MINIMAL_QUESTION_ORDER,
        QUESTION_ORDER,
        QUESTION_PROMPTS,
        apply_answer_overrides,
        default_interview,
        read_interview_answers,
        write_interview_answers,
    )
    from .parser import CharterParser, CharterSection
    from .schemas import (
        BranchStrategyConfig,
        CommitConfig,
        DoctrineSelectionConfig,
        Directive,
        DirectivesConfig,
        ExtractionMetadata,
        GovernanceConfig,
        PerformanceConfig,
        QualityConfig,
        SectionsParsed,
        CharterTestingConfig,
        emit_yaml,
    )
    from .scope import CharterScope, CharterScopeConfig, CharterScopeConflict, CharterScopeNotFound
    from .sync import SyncResult, load_directives_config, load_governance_config
    from .org_extends import ExtendsBaseNotFoundError, ExtendsCycleError, resolve_extends_order
    from .mission_type_profiles import (
        CrossGrainDoubleDeclarationError,
        GovernancePayload,
        MissionTypeProfile,
        ResolvedGovernance,
        ResolvedMissionType,
        UnknownMissionTypeError,
        existing_mission_types,
        resolve_mission_type_context,
    )
    from .resolver import (
        GovernanceResolution,
        GovernanceResolutionError,
        collect_governance_diagnostics,
        resolve_governance_for_profile,
        resolve_project_governance,
    )
    from .template_resolver import CharterTemplateResolver
    from .pack_context import PackContext
    from .exceptions import CharterActivationError


# Export bindings are code identities, never cached project or governance data.
_EXPORT_MODULES: dict[str, str] = {
    "CANONICAL_MANIFEST": "bundle",
    "CharterBundleManifest": "bundle",
    "SCHEMA_VERSION": "bundle",
    "DoctrineCatalog": "catalog",
    "load_doctrine_catalog": "catalog",
    "CompiledCharter": "compiler",
    "CharterReference": "compiler",
    "WriteBundleResult": "compiler",
    "compile_charter": "compiler",
    "write_compiled_charter": "compiler",
    "CharterContextResult": "context",
    "build_charter_context": "context",
    "CharterInterview": "interview",
    "QUESTION_ORDER": "interview",
    "MINIMAL_QUESTION_ORDER": "interview",
    "QUESTION_PROMPTS": "interview",
    "default_interview": "interview",
    "read_interview_answers": "interview",
    "write_interview_answers": "interview",
    "apply_answer_overrides": "interview",
    "CharterParser": "parser",
    "CharterSection": "parser",
    "BranchStrategyConfig": "schemas",
    "CommitConfig": "schemas",
    "DoctrineSelectionConfig": "schemas",
    "Directive": "schemas",
    "DirectivesConfig": "schemas",
    "ExtractionMetadata": "schemas",
    "GovernanceConfig": "schemas",
    "PerformanceConfig": "schemas",
    "QualityConfig": "schemas",
    "SectionsParsed": "schemas",
    "CharterTestingConfig": "schemas",
    "emit_yaml": "schemas",
    "CharterScope": "scope",
    "CharterScopeConfig": "scope",
    "CharterScopeConflict": "scope",
    "CharterScopeNotFound": "scope",
    "SyncResult": "sync",
    "load_directives_config": "sync",
    "load_governance_config": "sync",
    "sync": "sync",
    "GovernanceResolution": "resolver",
    "GovernanceResolutionError": "resolver",
    "resolve_governance_for_profile": "resolver",
    "resolve_project_governance": "resolver",
    "collect_governance_diagnostics": "resolver",
    "CrossGrainDoubleDeclarationError": "mission_type_profiles",
    "GovernancePayload": "mission_type_profiles",
    "MissionTypeProfile": "mission_type_profiles",
    "ResolvedGovernance": "mission_type_profiles",
    "ResolvedMissionType": "mission_type_profiles",
    "UnknownMissionTypeError": "mission_type_profiles",
    "existing_mission_types": "mission_type_profiles",
    "resolve_mission_type_context": "mission_type_profiles",
    "CharterTemplateResolver": "template_resolver",
    "PackContext": "pack_context",
    "CharterActivationError": "exceptions",
    "ExtendsBaseNotFoundError": "org_extends",
    "ExtendsCycleError": "org_extends",
    "resolve_extends_order": "org_extends",
}

__all__ = [
    "CANONICAL_MANIFEST",
    "CharterBundleManifest",
    "SCHEMA_VERSION",
    "DoctrineCatalog",
    "load_doctrine_catalog",
    "CompiledCharter",
    "CharterReference",
    "WriteBundleResult",
    "compile_charter",
    "write_compiled_charter",
    "CharterContextResult",
    "build_charter_context",
    "CharterInterview",
    "QUESTION_ORDER",
    "MINIMAL_QUESTION_ORDER",
    "QUESTION_PROMPTS",
    "default_interview",
    "read_interview_answers",
    "write_interview_answers",
    "apply_answer_overrides",
    "CharterParser",
    "CharterSection",
    "BranchStrategyConfig",
    "CommitConfig",
    "DoctrineSelectionConfig",
    "Directive",
    "DirectivesConfig",
    "ExtractionMetadata",
    "GovernanceConfig",
    "PerformanceConfig",
    "QualityConfig",
    "SectionsParsed",
    "CharterTestingConfig",
    "emit_yaml",
    "CharterScope",
    "CharterScopeConfig",
    "CharterScopeConflict",
    "CharterScopeNotFound",
    "SyncResult",
    "load_directives_config",
    "load_governance_config",
    "sync",
    "GovernanceResolution",
    "GovernanceResolutionError",
    "resolve_governance_for_profile",
    "resolve_project_governance",
    "collect_governance_diagnostics",
    "CrossGrainDoubleDeclarationError",
    "GovernancePayload",
    "MissionTypeProfile",
    "ResolvedGovernance",
    "ResolvedMissionType",
    "UnknownMissionTypeError",
    "existing_mission_types",
    "resolve_mission_type_context",
    "CharterTemplateResolver",
    "PackContext",
    "CharterActivationError",
    "ExtendsBaseNotFoundError",
    "ExtendsCycleError",
    "resolve_extends_order",
]


def __getattr__(name: str) -> Any:
    module = _EXPORT_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f"{__name__}.{module}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
