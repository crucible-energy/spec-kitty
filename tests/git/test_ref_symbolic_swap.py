"""Real Git commit-ID CAS must not follow a late symbolic-ref swap to primary."""

from pathlib import Path
import subprocess
from typing import Any

import pytest

from specify_cli.git import ref_advance
from tests._support.git_cli import git_out

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]


@pytest.mark.parametrize("operation", ["advance", "delete"])
def test_late_symbolic_swap_refuses_without_advancing_or_deleting_primary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str) -> None:
    git_out(tmp_path, "init", "-q", "-b", "main")
    git_out(tmp_path, "config", "user.name", "Symbolic swap fixture")
    git_out(tmp_path, "config", "user.email", "fixture@example.invalid")
    git_out(tmp_path, "config", "commit.gpgsign", "false")
    git_out(tmp_path, "commit", "-qm", "base", "--allow-empty")
    before = git_out(tmp_path, "rev-parse", "main")
    git_out(tmp_path, "branch", "feature/result", before)
    git_out(tmp_path, "checkout", "-q", "--detach", before)
    git_out(tmp_path, "commit", "-qm", "candidate", "--allow-empty")
    candidate = git_out(tmp_path, "rev-parse", "HEAD")
    original = ref_advance._run_git
    swapped = False

    def swap_before_real_write(repo: Path, args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal swapped
        if args[0] == "update-ref" and "refs/heads/feature/result" in args and not swapped:
            swapped = True
            git_out(repo, "symbolic-ref", "refs/heads/feature/result", "refs/heads/main")
        return original(repo, args, **kwargs)

    monkeypatch.setattr(ref_advance, "_run_git", swap_before_real_write)
    refused = False
    try:
        if operation == "advance":
            ref_advance.advance_branch_ref(tmp_path, "feature/result", candidate, expected_old_sha=before)
        else:
            ref_advance.delete_branch_ref(tmp_path, "feature/result", before)
    except (ref_advance.RefAdvanceError, ref_advance.RefDeleteError):
        refused = True
    assert swapped, "The race must occur at the actual canonical write boundary."
    assert git_out(tmp_path, "rev-parse", "main") == before
    assert refused, "Foreign symbolic state must be refused, not silently replaced."
    assert git_out(tmp_path, "symbolic-ref", "refs/heads/feature/result") == "refs/heads/main"
