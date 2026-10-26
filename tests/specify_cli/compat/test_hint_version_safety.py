"""A channel query must never render an older release as an upgrade."""

from pathlib import Path

import pytest

from specify_cli.compat.planner import ProjectState, plan
from specify_cli.compat.provider import FakeLatestVersionProvider
from tests.specify_cli.compat.test_planner import _make_invocation, _make_nag_cache_tmp, _make_project_root_resolver, _NOW

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.mark.parametrize("installed", ["4.0.0rc7", "4.0.0rc7+crucible.1"])
def test_selected_stable_channel_never_suggests_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, installed: str) -> None:
    from dataclasses import replace

    from specify_cli.compat._detect.install_method import InstallMethod
    from specify_cli.compat._detect.runtime import detect_runtime

    runtime = replace(detect_runtime(), install_method=InstallMethod.UV_TOOL)
    monkeypatch.setattr("specify_cli.compat._detect.runtime.detect_runtime", lambda: runtime)
    monkeypatch.setattr("specify_cli.compat.planner._get_installed_version", lambda: installed)
    monkeypatch.setattr("specify_cli.core.channel.prerelease_enabled", lambda: False)
    provider = FakeLatestVersionProvider(version="3.2.7")
    result = plan(
        _make_invocation(),
        latest_version_provider=provider,
        nag_cache=_make_nag_cache_tmp(tmp_path),
        now=_NOW,
        project_root_resolver=_make_project_root_resolver(tmp_path),
        read_only=True,
        query_latest=True,
    )
    assert result.project_status.state == ProjectState.COMPATIBLE
    assert result.cli_status.latest_version == "3.2.7"
    assert result.cli_status.is_outdated is False
    assert result.upgrade_hint.command is None
    assert "older" in result.upgrade_hint.note
