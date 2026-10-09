"""Explicit owned single-branch recovery CLI boundary (#85)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from specify_cli.cli.commands._owned_checkout import OwnedCheckoutOption
from specify_cli.core.paths import locate_project_root
from specify_cli.coordination.transaction_errors import BookkeepingError
from specify_cli.status import StoreError

__all__ = ["owned_single_branch"]


def owned_single_branch(
    mission: Annotated[str, typer.Option("--mission", help="Exact mission handle to recover.")],
    proof: Annotated[Path, typer.Option("--proof", help="Closed JSON evidence with pinned owner, history, archive and claim refs.")],
    owned_checkout: OwnedCheckoutOption = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Verify the conversion without writing or committing.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit conversion or refusal evidence as JSON.")] = False,
) -> None:
    """Explicitly recover one archived legacy code lane in its owned checkout.

    Example: spec-kitty migrate owned-single-branch --mission H --owned-checkout P
    --proof evidence.json --dry-run --json. Never refreshes a planning pin.
    """
    from specify_cli.cli.commands._owned_checkout import resolve_owned_or_refuse
    from specify_cli.core.owned_mission import LIFECYCLE_OWNED_TOPOLOGIES
    from specify_cli.migration.owned_single_branch import recover_owned_single_branch

    try:
        root = locate_project_root()
        if root is None or owned_checkout is None:
            raise ValueError("An explicit --owned-checkout and repository context are required")
        owned = resolve_owned_or_refuse(
            root,
            owned_checkout,
            mission,
            cwd=Path.cwd(),
            allowed_topologies=LIFECYCLE_OWNED_TOPOLOGIES,
            json_output=json_output,
            envelope=lambda code, message: {"success": False, "error_code": code, "error": message},
        )
        if owned is None:
            raise ValueError("Owned checkout could not be resolved")
        payload = recover_owned_single_branch(owned, proof, dry_run=dry_run)
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, StoreError, BookkeepingError):
        payload = {
            "success": False,
            "error_code": "OWNED_RECOVERY_REFUSED",
            "error": "Owned recovery refused: verify the closed proof, pinned inputs and inactive historical workspace.",
        }
        print(json.dumps(payload) if json_output else str(payload["error"]))
        raise typer.Exit(1) from None
    print(json.dumps(payload) if json_output else str(payload["result"]))
