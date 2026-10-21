"""Workspace-ledger operator commands. No creator retirement authority is exposed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from specify_cli.workspace_lifecycle.coordinator import Coordinator
from specify_cli.workspace_lifecycle.discovery import discover_workspaces
from specify_cli.workspace_lifecycle.inventory import OrganizationInventoryUnavailable, fetch_repositories
from specify_cli.workspace_lifecycle.state import StateError, StateStore

app = typer.Typer(help="Private organization workspace accounting and status.", no_args_is_help=True)
_StateDirectory = Annotated[Path, typer.Option("--state-dir", exists=True, file_okay=False, help="Existing private, owned workspace-ledger directory.")]


def _fail(exc: Exception) -> NoReturn:
    typer.echo(json.dumps({"error": "lifecycle_state_unavailable", "message": str(exc)}))
    raise typer.Exit(2)


@app.command()
def initialize(state_dir: _StateDirectory) -> None:
    """Initialize an explicitly admitted empty private directory; refuse existing contents."""
    try:
        store = StateStore.initialize(state_dir)
        state = store.read()
    except StateError as exc:
        _fail(exc)
    typer.echo(json.dumps({"schema_version": "spec-kitty.workspace-ledger.v1", "action": "initialized", "revision": state.revision}))


@app.command()
def status(state_dir: _StateDirectory) -> None:
    """Report recorded obligations; never infer workflow completion or deletion."""
    try:
        report = Coordinator(StateStore(state_dir)).closeout(workflow_complete=False)
    except StateError as exc:
        _fail(exc)
    typer.echo(json.dumps(report))


@app.command()
def account(
    state_dir: _StateDirectory,
    roots: Annotated[list[Path], typer.Option("--root", help="Bounded local discovery root; repeat for additional roots.")],
    max_depth: Annotated[int, typer.Option(min=0)] = 6,
    max_directories: Annotated[int, typer.Option(min=1)] = 10000,
    max_entries: Annotated[int, typer.Option(min=1)] = 100000,
) -> None:
    """Run foreground inventory and durably merge observations without cleanup.

    This explicit diagnostic scan is not an event callback or automatic worker.
    Incomplete scans retain previous obligations; they never erase missing work.
    """
    try:
        coordinator = Coordinator(StateStore(state_dir))
        # Validate the existing ledger before any external inventory operation.
        coordinator.store.read()
        repositories = fetch_repositories("crucible-energy")
        report = discover_workspaces(repositories, roots, max_depth=max_depth, max_directories=max_directories, max_entries=max_entries)
        coordinator.account(report["workspaces"])
        result = coordinator.closeout(workflow_complete=False)
    except (StateError, OrganizationInventoryUnavailable, ValueError) as exc:
        _fail(exc)
    typer.echo(
        json.dumps(
            {
                **result,
                "observation_scope": report["observation_scope"],
                "coverage_gaps": report["coverage_gaps"],
                "local_scan_complete": report["local_scan_complete"],
            }
        )
    )
    raise typer.Exit(0 if report["local_scan_complete"] else 1)
