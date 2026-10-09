"""Git source membership cannot conceal tracked or explicitly selected authority."""

from pathlib import Path

import pytest

from specify_cli import analysis_inputs
from tests.integration.conftest import _git, _init_repo


@pytest.fixture
def material_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    _init_repo(root)
    monkeypatch.chdir(root)
    for key in ("SPEC_KITTY_PACKS_ROOT", "SPEC_KITTY_TEMPLATE_ROOT", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(key, raising=False)
    (root / ".kittify/charter").mkdir()
    (root / ".kittify/charter/charter.yaml").write_text("governance:\n  charter:\n    authority_paths: [zig]\n")
    (root / "zig").mkdir()
    (root / "zig/build.zig").write_text("Tracked source.\n")
    (root / ".gitignore").write_text("/zig/derived/\n/zig/*.ignored\n")
    mission = root / "kitty-specs/test"
    mission.mkdir(parents=True)
    (mission / "meta.json").write_text("{}")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "source and repository policy")
    (root / "zig/derived").mkdir()
    (root / "zig/derived/cache").write_bytes(b"derived\0")
    return root, mission


def collect(repo: tuple[Path, Path]) -> dict[str, dict[str, str | None]]:
    root, mission = repo
    return analysis_inputs.collect_material_inputs(mission, root)


def test_derived_contents_and_membership_are_not_material(material_repo: tuple[Path, Path]) -> None:
    root, _ = material_repo
    before = collect(material_repo)
    (root / "zig/derived/cache").write_bytes(b"different output")
    (root / "zig/derived/another output\n").write_text("More ignored output.\n")
    assert collect(material_repo) == before
    for path in (root / "zig/derived").iterdir():
        path.unlink()
    assert collect(material_repo) == before
    assert not any(key.startswith("material:zig/derived") for key in before)


@pytest.mark.parametrize("declaration", ["authority_paths", "governance_references", "source_path", "local_path", "ignored_directory"])
def test_explicit_ignored_authority_remains_material(material_repo: tuple[Path, Path], declaration: str) -> None:
    root, _ = material_repo
    path = root / "zig/reference.ignored"
    path.write_text("Explicit authority.\n")
    charter = root / ".kittify/charter/charter.yaml"
    if declaration in ("authority_paths", "governance_references", "ignored_directory"):
        selected = "zig/derived" if declaration == "ignored_directory" else "zig/reference.ignored"
        if declaration == "authority_paths":
            charter.write_text("governance:\n  charter:\n    authority_paths: [zig, zig/reference.ignored]\n")
        else:
            charter.write_text(charter.read_text() + f"    governance_references: [{selected}]\n")
    elif declaration == "source_path":
        charter.write_text(charter.read_text() + "catalog:\n- source_path: zig/reference.ignored\n")
    else:
        path = charter.parent / "reference.ignored"
        path.write_text("Explicit ignored local reference.\n")
        (root / ".gitignore").write_text((root / ".gitignore").read_text() + "/.kittify/charter/*.ignored\n")
        charter.write_text(charter.read_text() + "catalog:\n- local_path: reference.ignored\n")
    before = collect(material_repo)
    if declaration == "ignored_directory":
        path = root / "zig/derived/cache"
    key = f"material:{path.relative_to(root).as_posix()}"
    assert key in before
    path.write_text("Changed explicitly selected authority.\n")
    assert collect(material_repo)[key] != before[key]


def test_tracked_ignored_source_and_staged_deletion_remain_material(material_repo: tuple[Path, Path]) -> None:
    root, _ = material_repo
    path = root / "zig/derived/source.zig"
    path.write_text("Tracked ignored source.\n")
    _git(root, "add", "-f", "zig/derived/source.zig")
    _git(root, "commit", "-qm", "track ignored source")
    before = collect(material_repo)
    assert "material:zig/derived/source.zig" in before
    assert "material:zig/derived/cache" not in before
    path.write_text("Dirty tracked source.\n")
    assert collect(material_repo) != before
    _git(root, "rm", "--cached", "zig/derived/source.zig")
    removed = collect(material_repo)
    assert "material:zig/derived/source.zig" in removed
    assert removed["git:source-membership"] != before["git:source-membership"]
    path.unlink()
    missing = collect(material_repo)
    assert missing["material:zig/derived/source.zig"]["sha256"] is None


def test_nonignored_untracked_additions_and_nested_policy_are_material(material_repo: tuple[Path, Path]) -> None:
    root, _ = material_repo
    before = collect(material_repo)
    (root / "zig/new-source.zig").write_text("Nonignored new source.\n")
    after = collect(material_repo)
    assert "material:zig/new-source.zig" in after and after != before
    assert after["material:zig/.gitignore"]["sha256"] is None
    (root / "zig/.gitignore").write_text("# Nested policy even without effective exclusion.\n")
    assert collect(material_repo) != after


@pytest.mark.parametrize("policy", ["local_exclude", "global_exclude"])
def test_mutable_external_excludes_do_not_hide_source(material_repo: tuple[Path, Path], tmp_path: Path, policy: str) -> None:
    root, _ = material_repo
    source = root / "zig/uncommitted-source.zig"
    source.write_text("Must remain material even when status hides it.\n")
    if policy == "local_exclude":
        path = Path(_git(root, "rev-parse", "--git-path", "info/exclude"))
        if not path.is_absolute():
            path = root / path
    else:
        path = tmp_path / "personal-excludes"
        _git(root, "config", "core.excludesFile", str(path))
    path.write_text("/zig/uncommitted-source.zig\n")
    assert _git(root, "status", "--porcelain=v1") == ""
    before = collect(material_repo)
    assert "material:zig/uncommitted-source.zig" in before
    path.write_text("/zig/\n")
    assert collect(material_repo) == before
    assert "material:zig/derived/cache" not in before


@pytest.mark.parametrize("failure", ["truncated", "invalid_path", "warning", "failed"])
def test_ambiguous_git_classification_refuses(material_repo: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    from kernel.git import GitCommandError, GitResult
    from kernel.git import listing

    original = listing.run_git
    classified = False

    def observed_git(cwd: Path, *args: str, **kwargs):
        nonlocal classified
        if "--ignored" not in args:
            return original(cwd, *args, **kwargs)
        classified = True
        if failure == "failed":
            raise GitCommandError(argv=args, cwd=cwd, returncode=128, stderr="Classification failed")
        outputs = {"truncated": (b"zig/derived", b""), "invalid_path": (b"../escape\0", b""), "warning": (b"", b"Cannot read ignore policy")}
        stdout, stderr = outputs[failure]
        return GitResult(0, stdout, stderr)

    monkeypatch.setattr(listing, "run_git", observed_git)
    with pytest.raises(analysis_inputs.MaterialInputError, match="classification failed"):
        collect(material_repo)
    assert classified


@pytest.mark.parametrize("explicit", [False, True])
def test_ignored_unsafe_link_cannot_select_external_authority(
    material_repo: tuple[Path, Path], tmp_path: Path, explicit: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = material_repo
    external = tmp_path / "external"
    external.mkdir()
    target = external / "secret.md"
    target.write_text("Do not read this authority.\n")
    link = root / "zig/link.ignored"
    link.symlink_to(external, target_is_directory=True)
    if explicit:
        charter = root / ".kittify/charter/charter.yaml"
        charter.write_text(charter.read_text() + "    governance_references: [zig/link.ignored/secret.md]\n")
    original = Path.read_bytes
    reads: list[Path] = []

    def observed_read(path: Path) -> bytes:
        if path == target or path.is_relative_to(link):
            reads.append(path)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", observed_read)
    with pytest.raises(analysis_inputs.MaterialInputError):
        collect(material_repo)
    assert reads == []


@pytest.mark.parametrize("variation", ["tracked", "deleted", "staged_removal"])
def test_b3_explicit_ignored_directory_retains_authority_with_tracked_child(material_repo: tuple[Path, Path], variation: str) -> None:
    from kernel.git.listing import repository_ignored_paths

    root, _ = material_repo
    directory = root / "zig/derived"
    tracked = directory / "tracked-source.zig"
    tracked.write_text("Tracked child of explicit ignored authority.\n")
    charter = root / ".kittify/charter/charter.yaml"
    charter.write_text(charter.read_text() + "    governance_references: [zig/derived]\n")
    _git(root, "add", str(charter))
    _git(root, "add", "-f", "zig/derived/tracked-source.zig")
    _git(root, "commit", "-qm", "declare ignored directory with tracked child")
    authority = directory / "explicit-reference.md"
    authority.write_text("Uncommitted explicitly selected authority.\n")
    if variation == "deleted":
        tracked.unlink()
    elif variation == "staged_removal":
        _git(root, "rm", "--cached", "zig/derived/tracked-source.zig")
    listing = {str(path) for path in repository_ignored_paths(root)}
    if variation != "staged_removal":
        assert "zig/derived" not in listing
        assert "zig/derived/explicit-reference.md" in listing
    before = collect(material_repo)
    authority.write_text("Changed authority bytes.\n")
    after = collect(material_repo)
    assert after != before, "Explicit ignored authority bytes were omitted from the snapshot"
    key = "material:zig/derived/explicit-reference.md"
    assert key in before and before[key] != after[key]
    if variation == "deleted":
        assert before["material:zig/derived/tracked-source.zig"]["sha256"] is None
    added = directory / "new-authority.md"
    added.write_text("Additional explicitly selected authority.\n")
    expanded = collect(material_repo)
    assert "material:zig/derived/new-authority.md" in expanded and expanded != after
    authority.unlink()
    assert key not in collect(material_repo)


@pytest.mark.parametrize("external_policy", ["local", "global"])
def test_b3_selection_policy_is_index_independent_and_ignores_external_parent_exclude(
    material_repo: tuple[Path, Path], tmp_path: Path, external_policy: str
) -> None:
    from kernel.git import run_git
    from kernel.git.listing import repository_ignored_paths

    root, _ = material_repo
    tracked = root / "zig/derived/tracked-source.zig"
    tracked.write_text("Tracked child.\n")
    _git(root, "add", "-f", "zig/derived/tracked-source.zig")
    _git(root, "commit", "-qm", "track ignored source for policy probe")
    if external_policy == "local":
        exclude = Path(_git(root, "rev-parse", "--git-path", "info/exclude"))
        if not exclude.is_absolute():
            exclude = root / exclude
    else:
        exclude = tmp_path / "personal-excludes"
        _git(root, "config", "core.excludesFile", str(exclude))
    exclude.write_text("/zig/\n")
    result = run_git(root, "check-ignore", "--verbose", "--no-index", "--", "zig/derived", check=False)
    assert result.returncode == 0
    # Effective check-ignore sees the mutable external parent rule, so it cannot
    # supply the repository-only selection-policy verdict.
    assert b"/zig/\tzig/derived" in result.stdout, result.stdout
    actual_index = root / ".git/index"
    before = actual_index.read_bytes()
    policy = {str(path) for path in repository_ignored_paths(root, index_independent=True)}
    assert "zig/derived" in policy and "zig" not in policy
    assert actual_index.read_bytes() == before
    charter = root / ".kittify/charter/charter.yaml"
    charter.write_text(charter.read_text() + "    governance_references: [zig/derived]\n")
    (root / "zig/derived/explicit-reference.md").write_text("Explicit ignored authority.\n")
    (root / "zig/sibling.ignored").write_text("Implicit ignored sibling.\n")
    inputs = collect(material_repo)
    assert "material:zig/derived/explicit-reference.md" in inputs
    assert "material:zig/sibling.ignored" not in inputs


def test_policy_change_during_collection_refuses(material_repo: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    root, _ = material_repo
    original = Path.iterdir
    changed = False

    def observed_children(path: Path):
        nonlocal changed
        if path == root / "zig" and not changed:
            changed = True
            (root / ".gitignore").write_text("# Prior cache exclusion removed concurrently.\n")
        return original(path)

    monkeypatch.setattr(Path, "iterdir", observed_children)
    with pytest.raises(analysis_inputs.MaterialInputError, match="membership changed"):
        collect(material_repo)
    assert changed


def test_pruned_derived_tree_is_not_traversed(material_repo: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _ = material_repo
    external = tmp_path / "external"
    external.mkdir()
    (external / "secret.md").write_text("Not source authority.\n")
    (root / "zig/derived/external").symlink_to(external, target_is_directory=True)
    original = Path.iterdir
    visits: list[Path] = []

    def observed_directory(path: Path):
        if path == root / "zig/derived" or path == external:
            visits.append(path)
        return original(path)

    monkeypatch.setattr(Path, "iterdir", observed_directory)
    inputs = collect(material_repo)
    assert visits == []
    assert not any(key.startswith("material:zig/derived") for key in inputs)


def test_root_ignore_symlink_refuses_before_classification_or_content_read(
    material_repo: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kernel.git import listing

    root, _ = material_repo
    external = tmp_path / "external-policy"
    external.write_text("/zig/\n")
    (root / ".gitignore").unlink()
    (root / ".gitignore").symlink_to(external)
    original = listing.repository_ignored_paths
    classifications = 0
    original_read = Path.read_text
    reads: list[Path] = []

    def observed_classification(*args, **kwargs):
        nonlocal classifications
        classifications += 1
        return original(*args, **kwargs)

    def observed_read(path: Path, *args, **kwargs):
        if path in (root / ".gitignore", external):
            reads.append(path)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(listing, "repository_ignored_paths", observed_classification)
    monkeypatch.setattr(Path, "read_text", observed_read)
    with pytest.raises(analysis_inputs.MaterialInputError):
        collect(material_repo)
    assert classifications == 0
    assert reads == []
