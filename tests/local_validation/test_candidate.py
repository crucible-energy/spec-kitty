"""Real staged-content and Git-state contracts for the native candidate module."""

from __future__ import annotations

import hashlib
import errno
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
    files: dict[str, tuple[str, str] | tuple[str, str, int]] = {}
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
        "git_files": {str(p.relative_to(common)): digest(p.read_bytes()) for p in common.rglob("*") if p.is_file()},
        "files": files,
    }


def capture(
    binary: Path, repo: Path, tmp_path: Path, environment: dict[str, str] | None = None, **changes: Any
) -> tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]:
    request = {"schema_version": 1, "repository": str(repo), "base": "HEAD", "destination": str(tmp_path / "owned evidence"), "git_executable": "/usr/bin/git"}
    request.update(changes)
    request_path = tmp_path / "capture-request.json"
    request_path.write_text(json.dumps(request))
    before = snapshot(repo)
    result = subprocess.run([str(binary), "capture", str(request_path)], env=environment, capture_output=True, timeout=40)
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
    changes: dict[str, Any] = {}
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


def test_candidate_all_deletions_keeps_valid_empty_tree(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    git(repository, "rm", "--cached", "app.py", "validator.py")
    result, _ = capture(candidate_binary, repository, tmp_path)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert manifest["paths"] == []
    assert git(Path(manifest["root"]), "ls-files", "-z").stdout == b""
    assert not (Path(manifest["root"]) / "app.py").exists()


def test_candidate_ignores_archive_attributes_and_keeps_dash_path(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    (repository / ".gitattributes").write_text("app.py export-ignore\nformat.txt export-subst\n")
    (repository / "format.txt").write_bytes(b"$Format:%H$\n")
    (repository / "-looks-like-an-option").write_bytes(b"data, not argv\n")
    git(repository, "add", "--all")
    result, _ = capture(candidate_binary, repository, tmp_path)
    assert result.returncode == 0, result.stderr
    root = Path(json.loads(result.stdout)["root"])
    assert (root / "app.py").read_bytes() == b"PASS\n"
    assert (root / "format.txt").read_bytes() == b"$Format:%H$\n"
    assert (root / "-looks-like-an-option").read_bytes() == b"data, not argv\n"


def test_candidate_honors_actual_index_environment_without_touching_either_index(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    custom_index = tmp_path / "custom index"
    shutil.copyfile(repository / ".git/index", custom_index)
    environment = os.environ.copy()
    environment["GIT_INDEX_FILE"] = str(custom_index)
    (repository / "app.py").write_text("FAIL\n")
    subprocess.run(["/usr/bin/git", "-C", str(repository), "add", "app.py"], env=environment, check=True, timeout=10)
    (repository / "app.py").write_text("PASS\n")
    before = custom_index.read_bytes()
    result, _ = capture(candidate_binary, repository, tmp_path, environment=environment)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert manifest["index_path"] == str(custom_index)
    assert manifest["index_sha256"] == digest(before)
    assert (Path(manifest["root"]) / "app.py").read_text() == "FAIL\n"
    assert custom_index.read_bytes() == before


def test_linked_fixture_keeps_common_dir_index_and_registry(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    # Disposable fixture repository, never an operational mission lane.
    linked = tmp_path / "fixture linked checkout"
    git(repository, "worktree", "add", "--detach", str(linked), "HEAD")
    (linked / "app.py").write_text("FAIL\n")
    git(linked, "add", "app.py")
    (linked / "app.py").write_text("PASS\n")
    original = snapshot(repository)
    result, _ = capture(candidate_binary, linked, tmp_path)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert manifest["common_directory"] == str(repository / ".git")
    assert manifest["git_directory"] != manifest["common_directory"]
    assert manifest["index_path"].startswith(str(repository / ".git/worktrees/"))
    assert (Path(manifest["root"]) / "app.py").read_text() == "FAIL\n"
    assert snapshot(repository) == original


def test_unmerged_index_is_refused_and_preserved(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    blob = git(repository, "rev-parse", "HEAD:app.py").stdout.strip()
    payload = b"0 " + b"0" * 40 + b"\tapp.py\0" + b"100644 " + blob + b" 1\tapp.py\0" + b"100644 " + blob + b" 2\tapp.py\0"
    subprocess.run(["/usr/bin/git", "-C", str(repository), "update-index", "-z", "--index-info"], input=payload, check=True, capture_output=True, timeout=10)
    result, _ = capture(candidate_binary, repository, tmp_path)
    assert result.returncode != 0 and result.stderr and not result.stdout


def test_split_index_capture_preserves_shared_index_bytes_and_metadata(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    git(repository, "update-index", "--split-index")
    (repository / "app.py").write_text("FAIL\n")
    git(repository, "add", "app.py")
    (repository / "app.py").write_text("PASS\n")
    shared = Path(os.fsdecode(git(repository, "rev-parse", "--shared-index-path").stdout[:-1]))
    if not shared.is_absolute():
        shared = repository / shared
    before = (shared.read_bytes(), shared.stat().st_mtime_ns)
    result, request = capture(candidate_binary, repository, tmp_path)
    assert result.returncode == 0, result.stderr
    assert (shared.read_bytes(), shared.stat().st_mtime_ns) == before
    assert (Path(json.loads(result.stdout)["root"]) / "app.py").read_text() == "FAIL\n"
    verified = subprocess.run([str(candidate_binary), "verify", str(Path(request["destination"]) / "candidate.json")], capture_output=True, timeout=30)
    assert verified.returncode == 0, verified.stderr
    assert (shared.read_bytes(), shared.stat().st_mtime_ns) == before


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("matching", None),
        ("index", "IndexDrift"),
        ("parent", "ParentDrift"),
        ("base", "BaseDrift"),
        ("content", "SnapshotDrift"),
        ("extra", "UnexpectedSnapshotInput"),
        ("directory", "UnexpectedSnapshotInput"),
        ("mode", "SnapshotModeDrift"),
    ],
)
def test_current_candidate_identity_pairs_success_with_real_drift(candidate_binary: Path, repository: Path, tmp_path: Path, fault: str, reason: str | None) -> None:
    git(repository, "branch", "frozen-base", "HEAD")
    result, request = capture(candidate_binary, repository, tmp_path, base="refs/heads/frozen-base")
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    if fault == "index":
        (repository / "app.py").write_text("FAIL\n")
        git(repository, "add", "app.py")
    elif fault == "parent":
        index = repository / ".git/index"
        original_index = index.read_bytes()
        git(repository, "commit", "--allow-empty", "-qm", "parent drift")
        index.write_bytes(original_index)
        assert digest(index.read_bytes()) == manifest["index_sha256"], "Parent control must not depend on index drift"
    elif fault == "base":
        tree = git(repository, "rev-parse", "HEAD^{tree}").stdout.strip().decode()
        other = git(repository, "commit-tree", tree, "-p", "HEAD", "-m", "base drift").stdout.strip().decode()
        git(repository, "update-ref", "refs/heads/frozen-base", other)
        assert git(repository, "rev-parse", "HEAD").stdout.strip().decode() == manifest["head"]
    elif fault == "content":
        (Path(manifest["root"]) / "app.py").write_text("FAIL\n")
    elif fault == "extra":
        (Path(manifest["root"]) / "injected.py").write_text("raise RuntimeError('extra input')\n")
    elif fault == "directory":
        (Path(manifest["root"]) / "injected_namespace").mkdir()
    elif fault == "mode":
        (Path(manifest["root"]) / "app.py").chmod(0o755)
    before = snapshot(repository)
    verify = subprocess.run([str(candidate_binary), "verify", str(Path(request["destination"]) / "candidate.json")], capture_output=True, timeout=30)
    assert snapshot(repository) == before
    if reason is None:
        assert verify.returncode == 0, verify.stderr
        assert json.loads(verify.stdout) == {"candidate_identity_current": True, "acceptance_performed": False}
    else:
        assert verify.returncode != 0 and verify.stdout == b""
        assert reason.encode() in verify.stderr


def test_manifest_tree_must_describe_the_actual_materialized_index(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    original_tree = git(repository, "rev-parse", "HEAD^{tree}").stdout.strip().decode()
    (repository / "app.py").write_text("FAIL\n")
    git(repository, "add", "app.py")
    result, request = capture(candidate_binary, repository, tmp_path)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert manifest["candidate_tree"] != original_tree
    manifest["candidate_tree"] = original_tree
    path = Path(request["destination"]) / "candidate.json"
    path.write_text(json.dumps(manifest))
    before = snapshot(repository)
    result = subprocess.run([str(candidate_binary), "verify", str(path)], capture_output=True, timeout=30)
    assert snapshot(repository) == before
    assert result.returncode != 0 and result.stdout == b"" and b"TreeIdentityMismatch" in result.stderr


def test_non_utf8_path_bytes_survive_native_materialization(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    name = b"raw-\xff\t\n.py"
    try:
        (repository / os.fsdecode(name)).write_bytes(b"raw staged bytes\n")
    except OSError as failure:
        if failure.errno != errno.EILSEQ:
            raise
        pytest.skip("Filesystem refuses non-UTF-8 filenames; native raw-byte qualification remains unproved here")
    git(repository, "add", "--all")
    result, _ = capture(candidate_binary, repository, tmp_path)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert any(entry["path_hex"] == name.hex() for entry in manifest["paths"])
    assert (Path(manifest["root"]) / os.fsdecode(name)).read_bytes() == b"raw staged bytes\n"


def test_sha256_git_objects_are_verified_as_sha256(candidate_binary: Path, tmp_path: Path) -> None:
    repo = tmp_path / "sha256 fixture"
    repo.mkdir()
    git(repo, "init", "--template=", "--object-format=sha256", "-q")
    git(repo, "config", "user.name", "Candidate Fixture")
    git(repo, "config", "user.email", "candidate@example.invalid")
    (repo / "app.py").write_bytes(b"base\n")
    git(repo, "add", "--all")
    git(repo, "commit", "-qm", "fixture base")
    (repo / "app.py").write_bytes(b"staged\n")
    git(repo, "add", "--all")
    result, request = capture(candidate_binary, repo, tmp_path)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert len(manifest["candidate_tree"]) == 64 and all(len(entry["oid"]) == 64 for entry in manifest["paths"])
    assert (Path(manifest["root"]) / "app.py").read_bytes() == b"staged\n"
    verified = subprocess.run([str(candidate_binary), "verify", str(Path(request["destination"]) / "candidate.json")], capture_output=True, timeout=30)
    assert verified.returncode == 0, verified.stderr


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("matching", None),
        ("tree-terminator", "MalformedTree"),
        ("tree-header", "MalformedTree"),
        ("tree-duplicate", "DuplicatePath"),
        ("tree-escape", "UnsafePath"),
        ("tree-mode", "UnsupportedMode"),
        ("tree-oid", "MalformedTree"),
        ("blob-header", "MalformedBlob"),
        ("blob-identity", "MalformedBlob"),
        ("blob-kind", "MalformedBlob"),
        ("blob-size", "MalformedBlob"),
        ("blob-content", "CorruptBlob"),
        ("blob-separator", "CorruptBlob"),
        ("blob-trailing", "MalformedBlob"),
        ("object-format", "UnsupportedObjectFormat"),
        ("identity-nul", "GitIdentityRefused"),
    ],
)
def test_actual_git_delegate_preserves_positive_and_refuses_corrupted_protocol(
    candidate_binary: Path, repository: Path, tmp_path: Path, fault: str, reason: str | None
) -> None:
    # The shim actually runs the same Git plumbing and corrupts only one named
    # response. Its matching control must work; a missing command is no proof.
    shim = tmp_path / "delegating-git"
    shim.write_text(
        f"#!{sys.executable}\n"
        "import subprocess,sys\n"
        f"fault={fault!r}\n"
        "args=sys.argv[1:]\n"
        "data=sys.stdin.buffer.read() if 'cat-file' in args else None\n"
        "result=subprocess.run(['/usr/bin/git',*args],input=data,capture_output=True,timeout=15)\n"
        "out=result.stdout\n"
        "if result.returncode == 0 and 'ls-tree' in args and fault.startswith('tree-'):\n"
        " row=out.split(b'\\0')[0]; head,path=row.split(b'\\t',1)\n"
        " if fault=='tree-terminator': out=out[:-1]\n"
        " elif fault=='tree-header': out=b'no-tab\\0'\n"
        " elif fault=='tree-duplicate': out=out+row+b'\\0'\n"
        " elif fault=='tree-escape': out=head+b'\\t../outside\\0'\n"
        " elif fault=='tree-mode': out=b'100600 '+head.split(b' ',1)[1]+b'\\t'+path+b'\\0'\n"
        " elif fault=='tree-oid': out=b'100644 blob invalid\\t'+path+b'\\0'\n"
        "if result.returncode == 0 and 'cat-file' in args and fault.startswith('blob-'):\n"
        " head,body=out.split(b'\\n',1); oid,kind,size=head.split(b' ')\n"
        " if fault=='blob-header': out=b'no-newline'\n"
        " elif fault=='blob-identity': out=b'0'*len(oid)+b' '+kind+b' '+size+b'\\n'+body\n"
        " elif fault=='blob-kind': out=oid+b' tree '+size+b'\\n'+body\n"
        " elif fault=='blob-size': out=oid+b' blob not-a-size\\n'+body\n"
        " elif fault=='blob-content': out=head+b'\\nX'+body[1:]\n"
        " elif fault=='blob-separator': out=head+b'\\n'+body[:int(size)]+b'X'+body[int(size)+1:]\n"
        " elif fault=='blob-trailing': out=out+b'extra'\n"
        "if result.returncode == 0 and '--show-object-format' in args and fault=='object-format': out=b'unknown-format\\n'\n"
        "if result.returncode == 0 and '--show-toplevel' in args and fault=='identity-nul': out=out[:-1]+b'\\0\\n'\n"
        "sys.stdout.buffer.write(out)\n"
        "sys.stderr.buffer.write(result.stderr)\n"
        "sys.exit(result.returncode)\n"
    )
    shim.chmod(0o700)
    result, _ = capture(candidate_binary, repository, tmp_path, git_executable=str(shim))
    if reason is None:
        assert result.returncode == 0, result.stderr
        assert (Path(json.loads(result.stdout)["root"]) / "app.py").read_text() == "PASS\n"
    else:
        assert result.returncode != 0 and result.stdout == b"" and reason.encode() in result.stderr


@pytest.mark.parametrize(
    "fault",
    [
        "missing-field",
        "unknown-field",
        "old-schema",
        "accepted-flag",
        "not-capture",
        "bad-parent",
        "relative-root",
        "hyphen-base",
        "git-context",
        "index-path",
        "entry-oid",
        "entry-mode",
        "duplicate-path",
        "odd-hex",
        "invalid-hex",
        "escape-hex",
        "missing-file",
        "git-pointer",
        "private-config",
        "private-link",
    ],
)
def test_incomplete_or_tampered_candidate_never_reports_current(candidate_binary: Path, repository: Path, tmp_path: Path, fault: str) -> None:
    result, request = capture(candidate_binary, repository, tmp_path)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    root = Path(manifest["root"])
    fields = {
        "unknown-field": ("invented_current", True),
        "old-schema": ("schema_version", 0),
        "accepted-flag": ("acceptance_performed", True),
        "not-capture": ("capture_only", False),
        "bad-parent": ("head", "not-an-object-id"),
        "relative-root": ("root", "relative"),
        "hyphen-base": ("base_reference", "--all"),
        "git-context": ("common_directory", manifest["common_directory"] + "/other"),
        "index-path": ("index_path", manifest["index_path"] + ".other"),
    }
    if fault in fields:
        key, value = fields[fault]
        manifest[key] = value
    elif fault == "missing-field":
        manifest.pop("base")
    elif fault == "entry-oid":
        manifest["paths"][0]["oid"] = "not-an-object-id"
    elif fault == "entry-mode":
        manifest["paths"][0]["mode"] = "100600"
    elif fault == "duplicate-path":
        manifest["paths"].append(manifest["paths"][0].copy())
    elif fault == "odd-hex":
        manifest["paths"][0]["path_hex"] = "a"
    elif fault == "invalid-hex":
        manifest["paths"][0]["path_hex"] = "zz"
    elif fault == "escape-hex":
        manifest["paths"][0]["path_hex"] = b"../outside".hex()
    elif fault == "missing-file":
        (root / "app.py").unlink()
    elif fault == "git-pointer":
        (root / ".git").write_text("gitdir: /outside\n")
    elif fault == "private-config":
        path = root.parent / "git/config"
        path.write_bytes(path.read_bytes() + b"\n[extra]\nvalue=true\n")
    elif fault == "private-link":
        (root.parent / "git/extra-link").symlink_to("config")
    path = Path(request["destination"]) / "candidate.json"
    path.write_text(json.dumps(manifest))
    before = snapshot(repository)
    refused = subprocess.run([str(candidate_binary), "verify", str(path)], capture_output=True, timeout=30)
    assert snapshot(repository) == before
    assert refused.returncode != 0 and refused.stdout == b"" and b"candidate refused:" in refused.stderr


@pytest.mark.parametrize("fault", ["unknown", "schema", "empty", "relative", "base-option", "newline-destination", "duplicate-json"])
def test_malformed_capture_request_refuses_without_live_effect(candidate_binary: Path, repository: Path, tmp_path: Path, fault: str) -> None:
    request: dict[str, Any] = {
        "schema_version": 1,
        "repository": str(repository),
        "base": "HEAD",
        "destination": str(tmp_path / "rejected"),
        "git_executable": "/usr/bin/git",
    }
    if fault == "unknown":
        request["invented_acceptance"] = True
    elif fault == "schema":
        request["schema_version"] = 0
    elif fault == "empty":
        request["repository"] = ""
    elif fault == "relative":
        request["repository"] = "."
    elif fault == "base-option":
        request["base"] = "--all"
    elif fault == "newline-destination":
        request["destination"] += "\nline"
    raw = json.dumps(request)
    if fault == "duplicate-json":
        raw = '{"base":"HEAD",' + raw[1:]
    path = tmp_path / "malformed-request.json"
    path.write_text(raw)
    before = snapshot(repository)
    result = subprocess.run([str(candidate_binary), "capture", str(path)], capture_output=True, timeout=30)
    assert snapshot(repository) == before
    assert result.returncode != 0 and result.stdout == b"" and b"candidate refused:" in result.stderr


@pytest.mark.parametrize(
    ("fault", "reason"), [("matching", None), ("link-target", "SnapshotDrift"), ("link-type", "SnapshotModeDrift"), ("file-type", "SnapshotModeDrift")]
)
def test_nested_and_link_identity_pairs_matching_with_actual_drift(
    candidate_binary: Path, repository: Path, tmp_path: Path, fault: str, reason: str | None
) -> None:
    (repository / "nested/deeper").mkdir(parents=True)
    (repository / "nested/deeper/value").write_bytes(b"staged value\n")
    (repository / "link").symlink_to("nested/deeper/value")
    git(repository, "add", "--all")
    result, request = capture(candidate_binary, repository, tmp_path)
    assert result.returncode == 0, result.stderr
    root = Path(json.loads(result.stdout)["root"])
    if fault == "link-target":
        (root / "link").unlink()
        (root / "link").symlink_to("other")
    elif fault == "link-type":
        (root / "link").unlink()
        (root / "link").write_text("nested/deeper/value")
    elif fault == "file-type":
        (root / "nested/deeper/value").unlink()
        (root / "nested/deeper/value").symlink_to("other")
    before = snapshot(repository)
    observed = subprocess.run([str(candidate_binary), "verify", str(Path(request["destination"]) / "candidate.json")], capture_output=True, timeout=30)
    assert snapshot(repository) == before
    if reason is None:
        assert observed.returncode == 0, observed.stderr
    else:
        assert observed.returncode != 0 and observed.stdout == b"" and reason.encode() in observed.stderr


def test_changed_actual_git_executable_invalidates_capture(candidate_binary: Path, repository: Path, tmp_path: Path) -> None:
    executable = tmp_path / "bound-tool/git"
    executable.parent.mkdir()
    # Relocating Apple's signed Git launcher is not a valid executable control.
    # Use a real, bound delegate which execs the installed Git in this process.
    executable.write_text(f"#!{sys.executable}\nimport os,sys\nos.execv('/usr/bin/git',['/usr/bin/git',*sys.argv[1:]])\n")
    executable.chmod(0o700)
    result, request = capture(candidate_binary, repository, tmp_path, git_executable=str(executable))
    assert result.returncode == 0, result.stderr
    executable.write_bytes(executable.read_bytes() + b"changed tool input\n")
    before = snapshot(repository)
    observed = subprocess.run([str(candidate_binary), "verify", str(Path(request["destination"]) / "candidate.json")], capture_output=True, timeout=30)
    assert snapshot(repository) == before
    assert observed.returncode != 0 and observed.stdout == b"" and b"ToolDrift" in observed.stderr
