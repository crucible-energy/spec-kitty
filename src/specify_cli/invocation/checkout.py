"""Choose operation custody without changing canonical project discovery."""

from __future__ import annotations

from pathlib import Path

from kernel.git_topology import NotAGitRepositoryError, git_toplevel
from specify_cli.core.checkout_ownership import error_for_claim, resolve_ownership_claim
from specify_cli.core.git_ops import get_current_branch, resolve_primary_branch
from specify_cli.git.protection_policy import ProtectionPolicy


def resolve_operation_checkout(
    primary: Path,
    owned_checkout: Path | None,
    *,
    writing: bool,
) -> Path:
    """Validate explicit custody and refuse unsafe branches before construction.

    Without opt-in, retain canonical-primary discovery. Non-Git legacy callers
    still reach the existing context-resolution error. An explicit ownership
    claim always requires a verified checkout and an attached writable branch.
    Read-only routing can inspect protected branches without opening an Op.
    """
    checkout = primary
    if owned_checkout is not None:
        claim = resolve_ownership_claim(owned_checkout, resolved_primary=primary)
        error = error_for_claim(claim)
        if error is not None:
            raise error
        checkout = claim.claimed_checkout
    if writing:
        try:
            git_toplevel(checkout)
        except NotAGitRepositoryError:
            # Existing uninitialized-project callers get their established
            # actionable context error; explicit claims already failed above.
            return checkout
        branch = get_current_branch(checkout)
        if branch is None:
            raise ValueError("Operation records require an attached feature branch; detached HEAD is read-only.")
        # Check before registry construction, including a repository that has
        # not created .kittify yet. A feature's config cannot weaken the
        # primary checkout's protection policy.
        primary_branch = resolve_primary_branch(primary, bias=False)
        if any(ProtectionPolicy.resolve(root).is_protected_target(branch, primary_branch=primary_branch, allow_bypass=False) for root in {primary, checkout}):
            raise ValueError(f"Refusing operation writes on protected branch '{branch}'; use --owned-checkout on a feature branch.")
    return checkout
