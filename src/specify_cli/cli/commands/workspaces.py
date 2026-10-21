"""Workspace-ledger operator commands. No creator retirement authority is exposed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from kernel.no_follow import NoFollowPathError

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
        from specify_cli.workspace_lifecycle.worker import LifecycleService

        store = StateStore(state_dir)
        report = {**Coordinator(store).closeout(workflow_complete=False), **LifecycleService(store).status()}
    except (StateError, OSError, ValueError, NoFollowPathError) as exc:
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


@app.command()
def resume(state_dir: _StateDirectory) -> None:
    """Recover missed completion events through the independently verifying worker."""
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    try:
        service = LifecycleService(StateStore(state_dir))
        service.resume()
    except (StateError, OSError, ValueError, NoFollowPathError) as exc:
        _fail(exc)
    typer.echo(json.dumps({"action": "queued", "cleanup_complete": False}))


@app.command("worker")
def run_worker(state_dir: _StateDirectory) -> None:
    """Drain pending hints; the creator, not event JSON, authorizes every effect."""
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    try:
        report = LifecycleService(StateStore(state_dir)).run()
    except (StateError, OSError, ValueError, NoFollowPathError) as exc:
        _fail(exc)
    typer.echo(json.dumps(report))
    if report["worker"] == "blocked":
        raise typer.Exit(2)


@app.command("managed-run")
def managed_run(
    state_dir: _StateDirectory,
    repo_root: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    workspace: Annotated[Path, typer.Option(help="New linked checkout path; existing work cannot be adopted.")],
    branch: Annotated[str, typer.Option(help="New feature branch.")],
    repository: Annotated[str, typer.Option(help="Exact crucible-energy repository slug.")],
    repository_id: Annotated[int, typer.Option(min=1)],
    command: Annotated[list[str], typer.Argument(help="Producer argv, after --; no shell interpretation.")],
    timeout: Annotated[float, typer.Option(min=0.01, max=30.0)] = 30.0,
    pr: Annotated[int | None, typer.Option(min=1, help="Optional allocated PR hint; otherwise producer writes scoped result JSON.")] = None,
) -> None:
    """Run one joined producer in a registered checkout and enqueue closeout.

    The producer receives SPEC_KITTY_LIFECYCLE_RESULT for an owned 0600 JSON
    {"pr": number} result. No existing checkout is registered by this admission. Failed or
    unconfirmed producers retain their workspace; main is never a merge target.
    """
    from specify_cli.workspace_lifecycle.adapters import GitHubDelivery, ManagedGitCreator
    from specify_cli.workspace_lifecycle.worker import LifecycleService

    try:
        store = StateStore(state_dir)
        service = LifecycleService(store)
        creator = ManagedGitCreator.create(
            store,
            repo_root=repo_root,
            path=workspace,
            branch=branch,
            repository=repository,
            repository_id=repository_id,
            delivery=GitHubDelivery(),
            on_complete=service.completion,
        )
        creator.run_producer(command, timeout=timeout)
        creator.complete(pr=pr)
    except (StateError, OSError, ValueError, NoFollowPathError) as exc:
        _fail(exc)
    typer.echo(json.dumps({"action": "released_and_queued", "creator": creator.authority_id, "cleanup_complete": False}))
