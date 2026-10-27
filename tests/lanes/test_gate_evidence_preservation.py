"""Exact QA custody across real squash merges; no evidence synthesis."""

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.lanes.merge import _is_gate_scaffold, _merge_branch_into
from specify_cli.merge.config import MergeStrategy

pytestmark = pytest.mark.git_repo
PATH = "kitty-specs/example-01ABCDEF/issue-matrix.md"
SCAFFOLD = "# Issue Matrix\n\n| Issue | Verdict | Evidence ref |\n| --- | --- | --- |\n"
AUTHORED = "# Issue Matrix\n\nExisting authored evidence; no approval inferred.\n"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def commit(repo: Path, content: str) -> None:
    path = repo / PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    git(repo, "add", "--all")
    git(repo, "commit", "-qm", "Fixture evidence")


@pytest.mark.parametrize("source_authored", [False, True])
def test_squash_preserves_exact_authored_blob(tmp_path: Path, source_authored: bool) -> None:
    git(tmp_path, "init", "-qb", "main")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "commit", "--allow-empty", "-qm", "Base")
    git(tmp_path, "checkout", "-qb", "mission")
    commit(tmp_path, AUTHORED if source_authored else SCAFFOLD)
    (tmp_path / "code.py").write_text("value = 1\n")
    git(tmp_path, "add", "code.py")
    git(tmp_path, "commit", "-qm", "Implementation")
    git(tmp_path, "checkout", "main")
    commit(tmp_path, SCAFFOLD if source_authored else AUTHORED)
    assert _merge_branch_into(tmp_path, "mission", "main", strategy=MergeStrategy.SQUASH)
    assert (tmp_path / PATH).read_text() == AUTHORED
    assert (tmp_path / "code.py").read_text() == "value = 1\n"
    assert git(tmp_path, "status", "--porcelain") == ""
    assert len(git(tmp_path, "worktree", "list", "--porcelain").split("worktree ")) == 2


@pytest.mark.parametrize("source", ["authored", "deleted", "symlink"])
def test_ambiguous_evidence_refuses_before_branch_or_workspace_mutation(tmp_path: Path, source: str) -> None:
    git(tmp_path, "init", "-qb", "main")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "Fixture")
    commit(tmp_path, SCAFFOLD)
    git(tmp_path, "checkout", "-qb", "mission")
    path = tmp_path / PATH
    if source == "authored":
        path.write_text("Different authored evidence\n")
    else:
        path.unlink()
        if source == "symlink":
            path.symlink_to("../../outside")
    git(tmp_path, "add", "--all")
    git(tmp_path, "commit", "-qm", "Conflicting evidence")
    git(tmp_path, "checkout", "main")
    commit(tmp_path, AUTHORED)
    before = git(tmp_path, "rev-parse", "HEAD")
    worktrees = git(tmp_path, "worktree", "list", "--porcelain")
    with pytest.raises(RuntimeError, match="gate evidence"):
        _merge_branch_into(tmp_path, "mission", "main", strategy=MergeStrategy.SQUASH)
    assert git(tmp_path, "rev-parse", "HEAD") == before
    assert git(tmp_path, "worktree", "list", "--porcelain") == worktrees
    assert (tmp_path / PATH).read_text() == AUTHORED


@pytest.mark.parametrize("content", [b'{"criteria":[],"criteria":[]}', b"null", b"{}", b"not json"])
def test_unknown_or_duplicate_json_is_never_scaffold(content: bytes) -> None:
    assert not _is_gate_scaffold("kitty-specs/example/acceptance-matrix.json", content)


def test_new_requirements_are_not_discardable_scaffold() -> None:
    matrix = {
        "mission_slug": "example",
        "negative_invariants": [],
        "criteria": [
            {
                "criterion_id": "FR-NEW",
                "description": "Verify FR-NEW is satisfied",
                "notes": "TODO: replace with a real acceptance criterion",
                "pass_fail": "pending",
                "proof_type": "automated_test",
            }
        ],
    }
    assert not _is_gate_scaffold("kitty-specs/example/acceptance-matrix.json", json.dumps(matrix).encode())
