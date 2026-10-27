"""Distribution identity reads must not initialize upgrade transports."""

import importlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.fast


def test_package_identity_import_does_not_initialize_upgrade_transports():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from specify_cli.distribution.package_name import resolve_cli_package_name; "
            "assert callable(resolve_cli_package_name); "
            "assert 'specify_cli.distribution.profile' not in sys.modules; "
            "assert 'specify_cli.compat.provider' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_public_exports_keep_original_order_and_object_identity():
    import specify_cli.distribution as public

    contract = {
        "CLI_PACKAGE_GROUP": "package_name",
        "DEFAULT_CLI_PACKAGE_NAME": "package_name",
        "DISTRIBUTION_PROFILE_GROUP": "profile",
        "DistributionProfile": "profile",
        "PROVIDER_SELECT_ENV_VAR": "upgrade_provider",
        "UPGRADE_PROVIDER_GROUP": "upgrade_provider",
        "clear_cli_package_name_cache": "package_name",
        "clear_distribution_profile_cache": "profile",
        "clear_upgrade_provider_cache": "upgrade_provider",
        "resolve_cli_package_name": "package_name",
        "resolve_distribution_profile": "profile",
        "resolve_installed_distribution_version": "installed_version",
        "resolve_upgrade_provider": "upgrade_provider",
        "stock_distribution_profile": "profile",
    }
    assert public.__all__ == list(contract)
    assert set(contract) <= set(dir(public))
    for name, module in contract.items():
        assert getattr(public, name) is getattr(importlib.import_module(f"specify_cli.distribution.{module}"), name)
    with pytest.raises(AttributeError):
        _ = public.not_a_distribution_export
