"""Real lazy command registration and private ledger operator operations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import NoReturn

import pytest
import typer
from typer.testing import CliRunner
from click.testing import Result
from kernel.no_follow import fd_relative_dir_ops_supported

from specify_cli.cli.commands import register_commands


def invoke(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> Result:
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "workspaces", *args])
    app = typer.Typer()
    register_commands(app)
    return CliRunner().invoke(app, ["workspaces", *args])


def test_initialize_then_status_through_real_registered_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    result = invoke(monkeypatch, ["initialize", "--state-dir", str(root)])
    if not fd_relative_dir_ops_supported():
        assert result.exit_code == 2
        assert json.loads(result.output)["error"] == "lifecycle_state_unavailable"
        return
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["action"] == "initialized"
    result = invoke(monkeypatch, ["status", "--state-dir", str(root)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["workflow_complete"] is False
    assert report["cleanup_complete"] is False
    assert report["unknown_observations"] == 0


def test_account_command_persists_real_observation_and_unknown_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not fd_relative_dir_ops_supported():
        pytest.skip("Strict persistence is unavailable on this platform")
    from specify_cli.cli.commands import workspaces

    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    assert invoke(monkeypatch, ["initialize", "--state-dir", str(root)]).exit_code == 0
    observation = {
        "repository": "crucible-energy/example",
        "repository_id": 1,
        "common_dir": "/store/.git",
        "path": "/work/unknown",
        "head": "a" * 40,
        "branch": "refs/heads/feature",
        "bare": False,
        "exists": True,
        "disposition": "retained",
        "reason": "ownership_unknown",
    }
    from specify_cli.workspace_lifecycle.discovery import discover_workspaces

    report = discover_workspaces({"crucible-energy/example": 1}, [tmp_path])
    report["workspaces"] = [observation]
    monkeypatch.setattr(workspaces, "fetch_repositories", lambda org: {"crucible-energy/example": 1})
    monkeypatch.setattr(workspaces, "discover_workspaces", lambda *args, **kw: report)
    result = invoke(monkeypatch, ["account", "--state-dir", str(root), "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["observation_scope"] == report["observation_scope"]
    result = invoke(monkeypatch, ["status", "--state-dir", str(root)])
    assert json.loads(result.output)["unknown_observations"] == 1
    assert json.loads(result.output)["cleanup_complete"] is False
    assert json.loads((root / "state.json").read_text())["observations"][0]["path"] == "/work/unknown"


def test_uninitialized_status_refuses_without_claiming_empty_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    result = invoke(monkeypatch, ["status", "--state-dir", str(root)])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] == "lifecycle_state_unavailable"
    assert not (root / "state.json").exists()


def test_initialize_again_never_resets_a_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not fd_relative_dir_ops_supported():
        pytest.skip("Strict persistence is unavailable on this platform")
    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    assert invoke(monkeypatch, ["initialize", "--state-dir", str(root)]).exit_code == 0
    before = (root / "state.json").read_bytes()
    result = invoke(monkeypatch, ["initialize", "--state-dir", str(root)])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] == "lifecycle_state_unavailable"
    assert (root / "state.json").read_bytes() == before


def test_failed_inventory_preserves_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not fd_relative_dir_ops_supported():
        pytest.skip("Strict persistence is unavailable on this platform")
    from specify_cli.cli.commands import workspaces
    from specify_cli.workspace_lifecycle.inventory import OrganizationInventoryUnavailable

    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    assert invoke(monkeypatch, ["initialize", "--state-dir", str(root)]).exit_code == 0
    before = (root / "state.json").read_bytes()

    def unavailable(org: str) -> NoReturn:
        raise OrganizationInventoryUnavailable("inventory unavailable")

    monkeypatch.setattr(workspaces, "fetch_repositories", unavailable)
    result = invoke(monkeypatch, ["account", "--state-dir", str(root), "--root", str(tmp_path)])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] == "lifecycle_state_unavailable"
    assert (root / "state.json").read_bytes() == before


def test_uninitialized_status_leaves_directory_admissible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not fd_relative_dir_ops_supported():
        pytest.skip("Strict persistence is unavailable on this platform")
    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    assert invoke(monkeypatch, ["status", "--state-dir", str(root)]).exit_code == 2
    assert list(root.iterdir()) == []
    result = invoke(monkeypatch, ["initialize", "--state-dir", str(root)])
    assert result.exit_code == 0, result.output
