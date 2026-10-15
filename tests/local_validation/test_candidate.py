"""Real staged-content and Git-state contracts for the native candidate module."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/zig/validation_candidate.zig"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()  # noqa: TID251 — raw candidate bytes


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith("GIT_"):
            environment.pop(key)
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.run(
        ["/usr/bin/git", "--no-optional-locks", "-C", str(repo), *args],
        env=environment,
        check=check,
        capture_output=True,
        timeout=20,
    )


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "live repository"
    repo.mkdir()
    git(repo, "init", "--template=", "-q")
    git(repo, "config", "user.name", "Candidate Fixture")
    git(repo, "config", "user.email", "candidate@example.invalid")
    (repo / "app.py").write_text("PASS\n")
    (repo / "validator.py").write_text("from pathlib import Path\nimport sys\nsys.exit(0 if Path('app.py').read_text().strip() == 'PASS' else 7)\n")
    git(repo, "add", "app.py", "validator.py")
    git(repo, "commit", "-qm", "fixture base")
    (repo / "untracked private work").write_bytes(b"retain untracked bytes\n")
    return repo


@pytest.fixture(scope="session")
def candidate_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    assert SOURCE.is_file(), "Native candidate boundary is absent; this setup failure is not identity proof"
    binding_name = os.environ.get("SPEC_KITTY_NATIVE_CANDIDATE_BINDING")
    if binding_name:
        binding = json.loads(Path(binding_name).read_text())
        image = Path(binding["image"])
        assert digest(SOURCE.read_bytes()) == binding["source_sha256"]
        assert digest(image.read_bytes()) == binding["image_sha256"]
        return image
    image = tmp_path_factory.mktemp("native-candidate") / "candidate"
    subprocess.run(
        [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(SOURCE), "-femit-bin=" + str(image)],
        check=True,
        capture_output=True,
        timeout=90,
    )
    return image


def snapshot(repo: Path) -> dict[str, Any]:
    index = Path(os.fsdecode(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "index").stdout[:-1]))
    common = Path(os.fsdecode(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout[:-1]))
    files = {}
    for path in repo.rglob("*"):
        if ".git" in path.relative_to(repo).parts:
            continue
        if path.is_symlink():
            files[os.fsencode(path.relative_to(repo)).hex()] = ("symlink", os.fsencode(path.readlink()).hex())
        elif path.is_file():
            files[os.fsencode(path.relative_to(repo)).hex()] = ("file", digest(path.read_bytes()), path.stat().st_mode)
    hooks = common / "hooks"
    return {
        "index": digest(index.read_bytes()),
        "head": git(repo, "rev-parse", "HEAD").stdout,
        "refs": git(repo, "show-ref").stdout,
        "registry": git(repo, "worktree", "list", "--porcelain", "-z").stdout,
        "hooks": {str(p.relative_to(hooks)): digest(p.read_bytes()) for p in hooks.rglob("*") if p.is_file()},
        "files": files,
    }


def capture(binary: Path, repo: Path, tmp_path: Path, **changes: Any) -> tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]:
    request = {"schema_version": 1, "repository": str(repo), "base": "HEAD", "destination": str(tmp_path / "owned evidence"), "git_executable": "/usr/bin/git"}
    request.update(changes)
    request_path = tmp_path / "capture-request.json"
    request_path.write_text(json.dumps(request))
    before = snapshot(repo)
    result = subprocess.run([str(binary), "capture", str(request_path)], capture_output=True, timeout=40)
    assert snapshot(repo) == before, "Capture changed live staged, unstaged, untracked, ref, hook, or worktree state"
    return result, request


@pytest.mark.parametrize(("staged", "unstaged", "expected"), [("FAIL\n", "PASS\n", 7), ("PASS\n", "FAIL\n", 0)])
def test_partial_staging_uses_actual_staged_content(
    repository: Path, tmp_path: Path, request: pytest.FixtureRequest, staged: str, unstaged: str, expected: int
) -> None:
    (repository / "app.py").write_text(staged)
    git(repository, "add", "app.py")
    (repository / "app.py").write_text(unstaged)
    before = snapshot(repository)
    # Explicit historical migration oracle: today's direct live-source command.
    # It must fail these staged-content assertions in BOTH directions. It is
    # never a product fallback, and missing-command exits are not credited.
    if os.environ.get("SPEC_KITTY_CANDIDATE_MIGRATION_ORACLE") == "direct-live-check":
        root = repository
    else:
        binary = request.getfixturevalue("candidate_binary")
        result, _ = capture(binary, repository, tmp_path)
        assert result.returncode == 0, result.stderr
        manifest = json.loads(result.stdout)
        root = Path(manifest["root"])
        assert (root / "app.py").read_text() == staged
        assert git(root, "rev-parse", "HEAD").stdout == before["head"]
        assert git(root, "diff", "--exit-code").returncode == 0
        assert manifest["acceptance_performed"] is False
    actual = subprocess.run([sys.executable, "-I", "-S", "validator.py"], cwd=root, capture_output=True, timeout=10)
    assert snapshot(repository) == before
    assert actual.returncode == expected, {"expected_staged_exit": expected, "actual_exit": actual.returncode}


def test_capture_preserves_raw_paths_modes_renames_deletions_and_private_git(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    git(repository, "mv", "app.py", "renamed\napp.py")
    git(repository, "rm", "validator.py")
    path = repository / "odd\tünicode.sh"
    path.write_bytes(b"#!/bin/sh\nexit 0\n")
    path.chmod(0o755)
    os.symlink("renamed\napp.py", repository / "safe-link")
    git(repository, "add", "--all")
    (repository / "not staged").write_text("leave this alone")
    result, request = capture(candidate_binary, repository, tmp_path)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    root = Path(manifest["root"])
    assert not (root / "app.py").exists() and not (root / "validator.py").exists()
    assert not (root / "not staged").exists()
    assert (root / "renamed\napp.py").read_bytes() == b"PASS\n"
    assert os.access(root / path.name, os.X_OK)
    assert (root / "safe-link").readlink() == Path("renamed\napp.py")
    rows = {bytes.fromhex(row["path_hex"]): row for row in manifest["paths"]}
    assert rows[os.fsencode(path.name)]["mode"] == "100755"
    assert git(root, "write-tree").stdout.strip().decode() == manifest["candidate_tree"]
    destination = Path(request["destination"])
    assert destination.stat().st_mode & 0o077 == 0
    assert (destination / "candidate.json").stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("fault", ["gitlink", "escape", "reserved", "existing-destination", "inside-live"])
def test_capture_refuses_unsupported_or_unsafe_inputs_without_live_mutation(candidate_binary: Path, repository: Path, tmp_path: Path, fault: str) -> None:
    changes = {}
    if fault == "gitlink":
        head = git(repository, "rev-parse", "HEAD").stdout.strip().decode()
        git(repository, "update-index", "--add", "--cacheinfo", "160000," + head + ",submodule")
    elif fault == "escape":
        os.symlink("../../outside", repository / "escape")
        git(repository, "add", "escape")
    elif fault == "reserved":
        changes["base"] = "--all"
    elif fault == "existing-destination":
        destination = tmp_path / "owned evidence"
        destination.mkdir()
        (destination / "user-work").write_text("keep")
    else:
        changes["destination"] = str(repository / "evidence")
    result, _ = capture(candidate_binary, repository, tmp_path, **changes)
    assert result.returncode != 0 and result.stderr and result.stdout == b""
    if fault == "existing-destination":
        assert (tmp_path / "owned evidence/user-work").read_text() == "keep"
