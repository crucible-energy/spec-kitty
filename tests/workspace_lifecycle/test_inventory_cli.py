"""Bounded API pagination and the production doctor command ingress."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from specify_cli.workspace_lifecycle import inventory
from specify_cli.cli.commands.doctor import app


def test_inventory_paginates_and_uses_scoped_host_without_debug_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GH_DEBUG", "api")
    first = [{"id": n, "full_name": f"crucible-energy/repo-{n}"} for n in range(1, 101)]
    second = [{"id": 101, "full_name": "crucible-energy/last"}]
    run = Mock(side_effect=[subprocess.CompletedProcess([], 0, json.dumps(p).encode(), b"") for p in (first, second)])
    monkeypatch.setattr(inventory.subprocess, "run", run)
    result = inventory.fetch_repositories("crucible-energy")
    assert len(result) == 101
    assert run.call_count == 2
    assert "page=2" in run.call_args.args[0][-1]
    assert run.call_args.args[0][2:4] == ["--hostname", "github.com"]
    assert "GH_DEBUG" not in run.call_args.kwargs["env"]
    assert 0 < run.call_args.kwargs["timeout"] <= 30


@pytest.mark.parametrize(
    "response",
    [
        subprocess.CompletedProcess([], 403, b"", b"private diagnostic"),
        subprocess.CompletedProcess([], 0, b"not-json", b""),
        subprocess.CompletedProcess([], 0, b"{}", b""),
    ],
)
def test_inventory_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch, response: subprocess.CompletedProcess[bytes]) -> None:
    monkeypatch.setattr(inventory.subprocess, "run", Mock(return_value=response))
    with pytest.raises(inventory.OrganizationInventoryUnavailable, match="inventory") as error:
        inventory.fetch_repositories("crucible-energy")
    assert "private diagnostic" not in str(error.value)


def test_inventory_timeout_is_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inventory.subprocess, "run", Mock(side_effect=subprocess.TimeoutExpired("gh", 1)))
    with pytest.raises(inventory.OrganizationInventoryUnavailable, match="unavailable"):
        inventory.fetch_repositories("crucible-energy")


def test_doctor_command_reports_without_project_or_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.cli.commands import _organization_workspaces_doctor as command

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(command, "fetch_repositories", lambda org: {f"{org}/absent": 1})
    result = CliRunner().invoke(app, ["organization-workspaces", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["unmatched_repositories"] == ["crucible-energy/absent"]
    assert report["workspaces"] == []
    assert not (tmp_path / ".kittify").exists()


def test_doctor_failure_returns_structured_nonzero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.cli.commands import _organization_workspaces_doctor as command

    monkeypatch.setattr(command, "fetch_repositories", Mock(side_effect=inventory.OrganizationInventoryUnavailable("inventory unavailable")))
    result = CliRunner().invoke(app, ["organization-workspaces", "--root", str(tmp_path)])
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] == "organization_workspace_inventory_unavailable"


@pytest.mark.parametrize("timeout", [0.0, -1.0, float("inf"), float("nan")])
def test_inventory_rejects_nonfinite_or_nonpositive_deadlines(timeout: float) -> None:
    with pytest.raises(ValueError, match="positive and finite"):
        inventory.fetch_repositories("crucible-energy", timeout=timeout)


def test_inventory_page_bound_cannot_return_partial_success(monkeypatch: pytest.MonkeyPatch) -> None:
    page = [{"id": n, "full_name": f"crucible-energy/repo-{n}"} for n in range(1, 101)]
    run = Mock(return_value=subprocess.CompletedProcess([], 0, json.dumps(page).encode(), b""))
    monkeypatch.setattr(inventory.subprocess, "run", run)
    with pytest.raises(inventory.OrganizationInventoryUnavailable, match="page count"):
        inventory.fetch_repositories("crucible-energy")
    assert run.call_count == 100


def test_report_distinguishes_observed_coverage_from_unobservable_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty configured root cannot certify all stores in the organization."""
    from specify_cli.cli.commands import _organization_workspaces_doctor as command

    monkeypatch.setattr(command, "fetch_repositories", lambda org: {f"{org}/absent": 1})
    result = CliRunner().invoke(app, ["organization-workspaces", "--root", str(tmp_path), "--max-depth", "2"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["local_scan_complete"] is True
    assert report["coverage_gaps"] == []
    assert report["unmatched_repositories"] == ["crucible-energy/absent"]
    assert report["observation_scope"] == {
        "roots": [str(tmp_path)],
        "max_depth": 2,
        "max_directories": 10000,
        "max_entries": 100000,
        "unobservable": ["repositories_outside_authenticated_visibility", "stores_outside_configured_roots"],
    }
    assert not (tmp_path / ".kittify").exists()
