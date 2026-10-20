"""Organization accounting includes non-lane workspaces without release authority."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.workspace_lifecycle.discovery import discover_workspaces, parse_repository_pages


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def seed(root: Path, remote: str) -> None:
    root.mkdir(parents=True)
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "fixture")
    git(root, "config", "core.hooksPath", "/dev/null")
    git(root, "commit", "--allow-empty", "-m", "seed")
    git(root, "remote", "add", "origin", remote)


def repositories() -> dict[str, int]:
    return parse_repository_pages([[{"id": 1, "full_name": "crucible-energy/example"}], [{"id": 2, "full_name": "crucible-energy/missing"}]], "crucible-energy")


def test_accounts_for_external_worktree_and_independent_clone(tmp_path: Path) -> None:
    root = tmp_path / "roots"
    seed(root / "primary", "git@github.com:crucible-energy/example.git")
    seed(root / "independent", "https://github.com/Crucible-Energy/Example.git")
    lane = tmp_path / "outside roots with spaces"
    git(root / "primary", "worktree", "add", "-b", "non-lane", str(lane))
    before = git(root / "primary", "rev-parse", "HEAD")
    result = discover_workspaces(repositories(), [root], max_depth=3, max_directories=100)
    assert len(result["workspaces"]) == 3
    assert len({w["common_dir"] for w in result["workspaces"]}) == 2
    assert all(w["disposition"] == "retained" and w["reason"] == "ownership_unknown" for w in result["workspaces"])
    assert {w["path"] for w in result["workspaces"]} == {str((root / "primary").resolve()), str((root / "independent").resolve()), str(lane.resolve())}
    assert result["unmatched_repositories"] == ["crucible-energy/missing"]
    assert git(root / "primary", "rev-parse", "HEAD") == before
    assert lane.exists()


def test_foreign_name_and_credentialed_origin_do_not_establish_identity(tmp_path: Path) -> None:
    seed(tmp_path / "example", "https://github.com/other/example.git")
    seed(tmp_path / "credentialed", "https://not-a-real-secret@github.com/crucible-energy/example.git")
    result = discover_workspaces(repositories(), [tmp_path], max_depth=3, max_directories=100)
    assert result["workspaces"] == []
    serialized = json.dumps(result)
    assert "not-a-real-secret" not in serialized
    assert any(g["reason"] == "origin_identity_unverified" for g in result["coverage_gaps"])


def test_scan_limits_and_missing_roots_are_visible(tmp_path: Path) -> None:
    (tmp_path / "one" / "two").mkdir(parents=True)
    result = discover_workspaces(repositories(), [tmp_path, tmp_path / "absent"], max_depth=0, max_directories=1)
    assert result["local_scan_complete"] is False
    assert result["coverage_gaps"]


def test_symlink_roots_are_not_followed(tmp_path: Path) -> None:
    seed(tmp_path / "real", "git@github.com:crucible-energy/example.git")
    link = tmp_path / "linked"
    link.symlink_to(tmp_path / "real", target_is_directory=True)
    result = discover_workspaces(repositories(), [link], max_depth=3, max_directories=100)
    assert not result["local_scan_complete"]
    assert not result["workspaces"]


@pytest.mark.parametrize(
    "pages",
    [
        None,
        [{"id": 1}],
        [[{"id": 1, "full_name": "other/example"}]],
        [[{"id": True, "full_name": "crucible-energy/example"}]],
        [[{"id": 1, "full_name": "crucible-energy/example"}, {"id": 2, "full_name": "crucible-energy/example"}]],
    ],
)
def test_invalid_inventory_refuses(pages: object) -> None:
    with pytest.raises(ValueError, match="Invalid|Expected|Repository|Conflicting"):
        parse_repository_pages(pages, "crucible-energy")


def test_ambient_git_repository_and_config_overrides_cannot_redirect_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seed(tmp_path / "one", "git@github.com:crucible-energy/example.git")
    seed(tmp_path / "two", "git@github.com:crucible-energy/missing.git")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "one" / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "one"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "remote.origin.url")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "git@github.com:other/redirected.git")
    report = discover_workspaces(repositories(), [tmp_path], max_depth=2, max_directories=10)
    assert {w["repository"] for w in report["workspaces"]} == {"crucible-energy/example", "crucible-energy/missing"}
    assert len({w["common_dir"] for w in report["workspaces"]}) == 2


def test_directory_entry_budget_is_enforced_during_enumeration(tmp_path: Path) -> None:
    for n in range(8):
        (tmp_path / f"folder-{n}").mkdir()
    report = discover_workspaces(repositories(), [tmp_path], max_depth=5, max_directories=100, max_entries=3)
    assert report["entries_scanned"] == 3
    assert not report["local_scan_complete"]
    assert any(g["reason"] == "entry_budget_exhausted" for g in report["coverage_gaps"])


def test_skipped_child_and_ancestor_symlinks_are_coverage_gaps(tmp_path: Path) -> None:
    seed(tmp_path / "outside" / "repository", "git@github.com:crucible-energy/example.git")
    root = tmp_path / "root"
    root.mkdir()
    (root / "linked").symlink_to(tmp_path / "outside", target_is_directory=True)
    report = discover_workspaces(repositories(), [root], max_depth=3, max_directories=100)
    assert not report["local_scan_complete"]
    assert any(g["reason"] == "symlink_entry_not_followed" for g in report["coverage_gaps"])
    assert not report["workspaces"]
    through_ancestor = discover_workspaces(repositories(), [root / "linked" / "repository"], max_depth=3, max_directories=100)
    assert not through_ancestor["local_scan_complete"]
    assert not through_ancestor["workspaces"]


def test_standalone_bare_store_reports_unsupported_coverage(tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    bare.mkdir()
    git(bare, "init", "--bare")
    report = discover_workspaces(repositories(), [tmp_path], max_depth=3, max_directories=100)
    assert not report["local_scan_complete"]
    assert any(g["reason"] == "standalone_bare_store_unsupported" for g in report["coverage_gaps"])
    assert (bare / "HEAD").exists()


def test_separate_common_directories_preserve_trailing_path_whitespace(tmp_path: Path) -> None:
    roots = tmp_path / "roots"
    roots.mkdir()
    for n, suffix in enumerate(("", " ")):
        checkout = roots / f"checkout-{n}"
        checkout.mkdir()
        git(checkout, "init", "-b", "main", f"--separate-git-dir={tmp_path / ('store' + suffix)}")
        git(checkout, "config", "user.email", "fixture@example.invalid")
        git(checkout, "config", "user.name", "fixture")
        git(checkout, "config", "core.hooksPath", "/dev/null")
        git(checkout, "commit", "--allow-empty", "-m", "seed")
        git(checkout, "remote", "add", "origin", "git@github.com:crucible-energy/example.git")
    report = discover_workspaces(repositories(), [roots], max_depth=2, max_directories=100)
    assert len(report["workspaces"]) == 2
    assert {w["common_dir"] for w in report["workspaces"]} == {str(tmp_path / "store"), str(tmp_path / "store ")}
