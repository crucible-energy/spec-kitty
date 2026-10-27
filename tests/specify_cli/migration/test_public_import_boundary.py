"""Read-only schema admission must not initialize migration writers."""

import importlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def test_schema_gate_import_does_not_initialize_migration_writers():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from specify_cli.migration.gate import check_schema_version; "
            "assert callable(check_schema_version); "
            "assert 'specify_cli.migration.normalize_mission_lifecycle' not in sys.modules; "
            "assert 'specify_cli.migration.runner' not in sys.modules; "
            "assert 'specify_cli.status' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_original_public_exports_and_normalization_alias_keep_identity():
    import specify_cli.migration as public

    contract = {
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
        "backfill_ownership": ("backfill_ownership", "backfill_ownership"),
        "NormalizeMissionLifecycleResult": ("normalize_mission_lifecycle", "NormalizeMissionLifecycleResult"),
        "normalize_mission_lifecycle_repo": ("normalize_mission_lifecycle", "normalize_repo"),
        "StripResult": ("strip_frontmatter", "StripResult"),
        "strip_mutable_fields": ("strip_frontmatter", "strip_mutable_fields"),
        "RewriteResult": ("rewrite_shims", "RewriteResult"),
        "rewrite_agent_shims": ("rewrite_shims", "rewrite_agent_shims"),
        "MigrationReport": ("runner", "MigrationReport"),
        "run_migration": ("runner", "run_migration"),
    }
    assert public.__all__ == list(contract)
    assert set(contract) <= set(dir(public))
    for name, (module, target) in contract.items():
        assert getattr(public, name) is getattr(importlib.import_module(f"specify_cli.migration.{module}"), target)
    with pytest.raises(AttributeError):
        _ = public.not_a_migration_export


def test_ownership_callable_survives_same_named_submodule_import():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib; import specify_cli.migration as public; "
            "module=importlib.import_module('specify_cli.migration.backfill_ownership'); "
            "assert public.backfill_ownership is module.backfill_ownership; assert callable(public.backfill_ownership)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
