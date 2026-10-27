"""CLI distribution identity and upgrade-source resolvers for packager hooks.

Stock Spec Kitty registers nothing under these entry-point groups. Absence of
registrations preserves public-PyPI / ``spec-kitty-cli`` behaviour.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from specify_cli.distribution.installed_version import (
        resolve_installed_distribution_version,
    )
    from specify_cli.distribution.package_name import (
        CLI_PACKAGE_GROUP,
        DEFAULT_CLI_PACKAGE_NAME,
        clear_cli_package_name_cache,
        resolve_cli_package_name,
    )
    from specify_cli.distribution.profile import (
        DISTRIBUTION_PROFILE_GROUP,
        DistributionProfile,
        clear_distribution_profile_cache,
        resolve_distribution_profile,
        stock_distribution_profile,
    )
    from specify_cli.distribution.upgrade_provider import (
        PROVIDER_SELECT_ENV_VAR,
        UPGRADE_PROVIDER_GROUP,
        clear_upgrade_provider_cache,
        resolve_upgrade_provider,
    )

# Bind each existing public object only when requested. Package-name reads run
# during every CLI startup and do not need network upgrade transports.
_EXPORT_MODULES = {
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

__all__ = [
    "CLI_PACKAGE_GROUP",
    "DEFAULT_CLI_PACKAGE_NAME",
    "DISTRIBUTION_PROFILE_GROUP",
    "DistributionProfile",
    "PROVIDER_SELECT_ENV_VAR",
    "UPGRADE_PROVIDER_GROUP",
    "clear_cli_package_name_cache",
    "clear_distribution_profile_cache",
    "clear_upgrade_provider_cache",
    "resolve_cli_package_name",
    "resolve_distribution_profile",
    "resolve_installed_distribution_version",
    "resolve_upgrade_provider",
    "stock_distribution_profile",
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
