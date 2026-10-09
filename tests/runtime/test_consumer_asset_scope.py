"""Qualified consumer assets must never share native user destinations."""

from pathlib import Path

import pytest

from kernel.paths import get_kittify_home
from specify_cli.core.config import AGENT_COMMAND_CONFIG
from specify_cli.runtime.agent_commands import get_global_command_dir
from specify_cli.skills.paths import get_primary_global_skill_root, iter_installable_agents

pytestmark = pytest.mark.unit


def test_consumer_paths_share_one_explicit_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, canonical_home: None) -> None:
    home = get_kittify_home()
    monkeypatch.setenv("SPEC_KITTY_ASSET_SCOPE", "consumer")
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "external-opencode"))
    monkeypatch.setenv("LLXPRT_CONFIG_HOME", str(tmp_path / "external-llxprt"))
    for agent in AGENT_COMMAND_CONFIG:
        assert get_global_command_dir(agent) == home / "agent-assets" / str(AGENT_COMMAND_CONFIG[agent]["dir"])
    for agent in iter_installable_agents():
        root = get_primary_global_skill_root(agent)
        assert root is not None and root.is_relative_to(home / "agent-assets")
    assert not list(home.iterdir()), "path selection is read-only"
