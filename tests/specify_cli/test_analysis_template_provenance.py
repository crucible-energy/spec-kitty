"""Replica proof must survive content reads and package pinning as one collection."""

from pathlib import Path
from typing import BinaryIO
from collections.abc import Iterator
import os
import hashlib
import shutil

import pytest

from specify_cli import analysis_inputs
from specify_cli.runtime.bootstrap import ensure_runtime


@pytest.fixture
def bootstrapped_material(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, canonical_home: None) -> tuple[Path, Path, Path]:
    for key in ("SPEC_KITTY_PACKS_ROOT", "SPEC_KITTY_TEMPLATE_ROOT"):
        monkeypatch.delenv(key, raising=False)
    home = tmp_path / "runtime"
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    ensure_runtime()
    root = tmp_path / "project"
    charter = root / ".kittify/charter"
    charter.mkdir(parents=True)
    (root / ".kittify/config.yaml").write_text("mission_type_activations: [software-dev]\n")
    (charter / "charter.yaml").write_text("mission_type_activations: [software-dev]\n")
    mission = root / "kitty-specs/test"
    mission.mkdir(parents=True)
    (mission / "meta.json").write_text('{"mission_type": "software-dev"}')
    return root, mission, home / "missions/software-dev/templates/spec-template.md"


@pytest.mark.parametrize("change", ["content", "equal_bytes", "ancestor"])
def test_replica_change_between_proof_and_package_pin_refuses(bootstrapped_material: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    from kernel.paths import get_package_asset_root

    root, mission, replica = bootstrapped_material
    source = get_package_asset_root() / "software-dev/templates/spec-template.md"
    original = analysis_inputs._observe_template
    source_reads = 0
    changed = False

    def observed_hash(path: Path):
        nonlocal changed, source_reads
        observed = original(path)
        if path == source:
            source_reads += 1
        if path == source and source_reads == 2:
            changed = True
            if change == "content":
                replica.write_bytes(replica.read_bytes() + b"\nmutable\n")
            elif change == "equal_bytes":
                replacement = replica.with_name("replacement")
                replacement.write_bytes(replica.read_bytes())
                replacement.replace(replica)
            else:
                directory = replica.parent
                moved = directory.with_name("retargeted")
                directory.rename(moved)
                directory.symlink_to(moved, target_is_directory=True)
        return observed

    monkeypatch.setattr(analysis_inputs, "_observe_template", observed_hash)
    with pytest.raises(analysis_inputs.MaterialInputError):
        analysis_inputs.collect_material_inputs(mission, root)
    assert changed


@pytest.mark.parametrize("change", ["content", "same_bytes", "ancestor_aba"])
def test_template_change_during_real_digest_read_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    directory = tmp_path / "assets"
    directory.mkdir()
    path = directory / "template.md"
    path.write_bytes(b"exact bundled bytes\n")
    original = hashlib.file_digest

    def observed_read(stream: BinaryIO, digest: str) -> object:
        result = original(stream, digest)
        if change == "content":
            path.write_bytes(b"altered authority\n")
        elif change == "same_bytes":
            path.write_bytes(path.read_bytes())
        else:
            moved = directory.with_name("moved")
            directory.rename(moved)
            directory.symlink_to(moved, target_is_directory=True)
            directory.unlink()
            moved.rename(directory)
        return result

    monkeypatch.setattr(hashlib, "file_digest", observed_read)
    with pytest.raises(analysis_inputs.MaterialInputError, match="changed during content read"):
        analysis_inputs._observe_template(path)


@pytest.mark.parametrize("kind", ["missing", "directory", "symlink", "parent_symlink"])
def test_unverifiable_regular_asset_refuses_without_content_read(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "asset"
    if kind == "directory":
        path.mkdir()
    elif kind == "symlink":
        path.symlink_to(tmp_path / "missing")
    elif kind == "parent_symlink":
        path.symlink_to(tmp_path, target_is_directory=True)
        path /= "missing"
    with pytest.raises(analysis_inputs.MaterialInputError):
        analysis_inputs._observe_template(path)


@pytest.mark.parametrize("mission,name", [("custom", "spec-template.md"), ("software-dev", "foreign-template.md")])
def test_foreign_or_missing_package_counterpart_refuses(bootstrapped_material: tuple[Path, Path, Path], mission: str, name: str) -> None:
    _, _, replica = bootstrapped_material
    home = replica.parents[3]
    foreign = home / "missions" / mission / "templates" / name
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_bytes(replica.read_bytes())
    with pytest.raises(analysis_inputs.MaterialInputError, match="External mutable"):
        analysis_inputs._qualify_global_template(mission, name, foreign, {})


def test_content_pin_cannot_differ_from_observed_bundled_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A local package-pin fixture isolates this branch without changing actual
    # SDK/vendor bytes or mocking the real-CLI authority selection tests.
    root = tmp_path / "bundle"
    root.mkdir()
    source = root / "template.md"
    source.write_bytes(b"before\n")
    proof = analysis_inputs._observe_template(source)
    source.write_bytes(b"after\n")
    monkeypatch.delenv("SPEC_KITTY_PACKS_ROOT", raising=False)
    monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)
    monkeypatch.setattr(analysis_inputs, "built_in_root", lambda: root)
    monkeypatch.setattr(analysis_inputs, "get_package_asset_root", lambda: root)
    with pytest.raises(analysis_inputs.MaterialInputError, match="changed before package pinning"):
        analysis_inputs._package_inputs({source: proof})


def test_parent_validator_accepts_only_existing_system_alias_identity() -> None:
    from specify_cli.runtime.asset_preparation import asset_parent_states
    import sys

    if sys.platform != "darwin":
        pytest.skip("macOS system alias identity")
    assert os.readlink("/var") == "private/var"
    states = asset_parent_states(Path("/var/folders/template.md"))
    assert any(path == Path("/var") and state.kind == "symlink" and state.target == "private/var" for path, state in states)


def test_ancestor_retarget_before_descriptor_open_refuses_without_byte_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.runtime import asset_preparation

    directory = tmp_path / "assets"
    directory.mkdir()
    path = directory / "template.md"
    path.write_bytes(b"exact bytes\n")
    original = asset_preparation.asset_parent_states
    observations = 0
    reads = 0

    def observed_parents(selected: Path):
        nonlocal observations
        states = original(selected)
        observations += 1
        if observations == 3:
            moved = directory.with_name("foreign")
            directory.rename(moved)
            directory.symlink_to(moved, target_is_directory=True)
        return states

    original_digest = hashlib.file_digest

    def observed_digest(stream: BinaryIO, digest: str):
        nonlocal reads
        reads += 1
        return original_digest(stream, digest)

    monkeypatch.setattr(asset_preparation, "asset_parent_states", observed_parents)
    monkeypatch.setattr(hashlib, "file_digest", observed_digest)
    with pytest.raises(analysis_inputs.MaterialInputError):
        analysis_inputs._observe_template(path)
    assert observations == 3
    assert reads == 0


def test_unrelated_parent_membership_is_not_durable_template_material(bootstrapped_material: tuple[Path, Path, Path]) -> None:
    root, mission, replica = bootstrapped_material
    before = analysis_inputs.collect_material_inputs(mission, root)
    (replica.parent / "unselected-custom.md").write_text("Unselected customization.\n")
    assert analysis_inputs.collect_material_inputs(mission, root) == before


def test_unavailable_descriptor_guards_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "template.md"
    path.write_bytes(b"exact bytes\n")
    monkeypatch.setattr(os, "supports_dir_fd", set())
    with pytest.raises(analysis_inputs.MaterialInputError, match="unsupported on this platform"):
        analysis_inputs._observe_template(path)


@pytest.mark.parametrize("retarget", [False, True])
def test_b1_regular_file_ancestor_refuses_before_any_content_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, retarget: bool) -> None:
    ancestor = tmp_path / "AGENTS.md"
    ancestor.write_bytes(b"Not a template directory.\n")
    external = tmp_path / "external.md"
    external.write_bytes(b"External content must never be read.\n")
    original_lstat = Path.lstat
    original_read = Path.read_bytes
    original_digest = hashlib.file_digest
    path_reads: list[Path] = []
    descriptor_reads = 0
    changed = False

    def observed_lstat(path: Path) -> os.stat_result:
        nonlocal changed
        metadata = original_lstat(path)
        if path == ancestor and retarget and not changed:
            changed = True
            ancestor.unlink()
            ancestor.symlink_to(external)
        return metadata

    def observed_read(path: Path) -> bytes:
        path_reads.append(path)
        return original_read(path)

    def observed_digest(stream: BinaryIO, digest: str):
        nonlocal descriptor_reads
        descriptor_reads += 1
        return original_digest(stream, digest)

    monkeypatch.setattr(Path, "lstat", observed_lstat)
    monkeypatch.setattr(Path, "read_bytes", observed_read)
    monkeypatch.setattr(hashlib, "file_digest", observed_digest)
    with pytest.raises(analysis_inputs.MaterialInputError):
        analysis_inputs._observe_template(ancestor / "templates/spec-template.md")
    assert changed is retarget
    assert path_reads == []
    assert descriptor_reads == 0


def test_b2_full_collector_refuses_restored_source_omitted_during_traversal(
    bootstrapped_material: tuple[Path, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import kernel.paths as kernel_paths
    from charter.activation.mission_type_profiles import resolve_mission_type_context
    from charter.activation.resolver import DoctrineService

    root, mission, replica = bootstrapped_material
    package = tmp_path / "package-layout"
    built_in = package / "packs/built-in"
    shutil.copytree(analysis_inputs.built_in_root(), built_in)
    (package / "kernel").mkdir()
    anchor = package / "kernel/paths.py"
    shutil.copy2(kernel_paths.__file__, anchor)
    # Simulate a packaged layout at the canonical ancestor-walk input. All path,
    # Mission definition and template resolution bodies still execute normally;
    # no resolution result or material manifest is substituted.
    monkeypatch.setattr(kernel_paths, "__file__", str(anchor))
    assets = kernel_paths.get_package_asset_root()
    assert assets == built_in / "missions"
    assert analysis_inputs.built_in_root() == built_in
    context = resolve_mission_type_context(root, mission_type="software-dev")
    assert context.template_set is not None
    source = DoctrineService.resolve_package_default_asset_path(missions_root=assets, mission="software-dev", subdir="templates", name=context.template_set["spec"])
    assert source == assets / "software-dev/templates/spec-template.md"
    assert source.read_bytes() == replica.read_bytes()
    subtree = assets / "software-dev"
    parked = package / "parked-software-dev"
    original_rglob = Path.rglob
    original_observe = analysis_inputs._observe_template
    traversal_rows: list[Path] = []
    source_observations: list[analysis_inputs._TemplateObservation] = []
    traversed = False

    def observed_template(path: Path) -> analysis_inputs._TemplateObservation:
        observed = original_observe(path)
        if path == source:
            source_observations.append(observed)
        return observed

    def disappearing_subtree(path: Path, pattern: str) -> Iterator[Path]:
        nonlocal traversed
        if path != assets:
            yield from original_rglob(path, pattern)
            return
        traversed = True
        subtree.rename(parked)
        try:
            for member in original_rglob(path, pattern):
                traversal_rows.append(member)
                yield member
        finally:
            parked.rename(subtree)

    monkeypatch.setattr(analysis_inputs, "_observe_template", observed_template)
    monkeypatch.setattr(Path, "rglob", disappearing_subtree)
    try:
        with pytest.raises(analysis_inputs.MaterialInputError, match="Selected bundled template missing from mission-assets pin"):
            analysis_inputs.collect_material_inputs(mission, root)
    finally:
        assert traversed
        assert not any(path.is_relative_to(subtree) for path in traversal_rows)
        assert source.is_file() and not parked.exists()
        assert len(source_observations) >= 2
        assert all(observed == source_observations[0] for observed in source_observations)
