"""Real, independently owned Git worktrees for coordination read trials."""

import subprocess
from pathlib import Path


def materialize_coordination(repo: Path, root: Path, branch: str) -> None:
    """Register an absent fixture root; never adopt or replace an existing husk."""
    assert not root.exists(), root

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)

    if not (repo / ".git").exists():
        git("init", "-qb", "main")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "Coordination fixture")
    git("config", "commit.gpgsign", "false")
    # Nested fixture workspaces are execution resources, not source Git links.
    exclude = Path(git("rev-parse", "--git-path", "info/exclude").stdout.strip())
    if not exclude.is_absolute():
        exclude = repo / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a", encoding="utf-8") as stream:
        stream.write("\n/.worktrees/\n")
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        check=False,
    )
    if head.returncode:
        git("commit", "--allow-empty", "-qm", "Fixture baseline")
    present = subprocess.run(
        ["git", "-C", str(repo), "show-ref", "--verify", f"refs/heads/{branch}"],
        capture_output=True,
        check=False,
    )
    if present.returncode:
        git("branch", branch)
    root.parent.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", str(root), branch)
