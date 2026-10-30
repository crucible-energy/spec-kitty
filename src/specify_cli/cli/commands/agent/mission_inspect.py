"""Read-only immutable mission inspection; never an ownership/advance shortcut."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from kernel.git import GitCommandError
from specify_cli.context.mission_resolver import AmbiguousHandleError, MissionNotFoundError, inspect_mission_at


def inspect_mission(
    mission: Annotated[str, typer.Option("--mission", help="Canonical mission handle in the selected commit")],
    at: Annotated[str, typer.Option("--at", help="Git revision resolved once to an immutable commit")],
    json_output: Annotated[bool, typer.Option("--json", help="Emit immutable observations as JSON")] = False,
) -> None:
    """Inspect saved planning identity/facts without changing the active checkout."""
    try:
        payload = inspect_mission_at(Path.cwd(), mission, at)
    except AmbiguousHandleError as exc:
        error: dict[str, object] = {
            "result": "error",
            "error_code": "MISSION_AMBIGUOUS_SELECTOR",
            "error": str(exc),
            "candidates": [{"mission_id": item.mission_id, "mission_slug": item.mission_slug} for item in exc.candidates],
        }
    except (GitCommandError, MissionNotFoundError, OSError, ValueError) as exc:
        error = {"result": "error", "error_code": "PINNED_PLANNING_INSPECTION_REFUSED", "error": str(exc)}
    else:
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo(f"{payload['mission_slug']} ({payload['mission_id']}) at {payload['commit']}")
            typer.echo("Saved planning observations only; current readiness is unqualified.")
        return
    typer.echo(json.dumps(error, ensure_ascii=False, indent=2) if json_output else str(error["error"]))
    raise typer.Exit(1)
