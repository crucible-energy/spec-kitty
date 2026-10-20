"""Read-only organization workspace accounting; never a cleanup command."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from specify_cli.cli.commands._doctor_shared import console
from specify_cli.workspace_lifecycle.discovery import discover_workspaces
from specify_cli.workspace_lifecycle.inventory import OrganizationInventoryUnavailable, fetch_repositories


def run_organization_workspaces(organization: str, roots: list[Path], max_depth: int, max_directories: int, max_entries: int) -> None:
    try:
        repositories = fetch_repositories(organization)
        report = discover_workspaces(repositories, roots, max_depth=max_depth, max_directories=max_directories, max_entries=max_entries)
    except (OrganizationInventoryUnavailable, ValueError) as exc:
        console.print_json(json.dumps({"error": "organization_workspace_inventory_unavailable", "message": str(exc)}))
        raise typer.Exit(2) from exc
    console.print_json(json.dumps(report))
    raise typer.Exit(0 if report["local_scan_complete"] else 1)
