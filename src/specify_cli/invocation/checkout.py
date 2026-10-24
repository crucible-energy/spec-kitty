"""Standalone Op custody through the canonical ownership minter."""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.core.owned_mission import OperationCheckout


def resolve_operation_checkout(primary: Path, owned_claim: Path | None, *, writing: bool) -> OperationCheckout:
    # Preserve the command cold-import boundary; claims have one authority.
    from specify_cli.core.owned_mission import resolve_operation_checkout as resolve

    return resolve(primary, owned_claim, writing=writing)
