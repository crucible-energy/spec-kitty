"""Contained tracked canonical aliases are material references, not new authority."""

from pathlib import Path
import json

import pytest

from tests.integration.conftest import OwnedCheckouts, _git
from tests.integration.test_owned_analysis_implementation_cli import (
    _assert_owned_analysis_refused_without_claim,
    implement,
    prepared_owner as prepared_owner,
    primary_state,
    record,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection, pytest.mark.real_drain_posture]


@pytest.fixture
def canonical_alias_owner(prepared_owner: OwnedCheckouts) -> OwnedCheckouts:
    checkouts = prepared_owner
    root = checkouts.owned_root
    (root / "docs").mkdir()
    (root / "docs/release-contract.md").write_text("# Contract\nOne canonical documentation authority.\n")
    (root / "alternate-docs").mkdir()
    (root / "alternate-docs/release-contract.md").write_bytes((root / "docs/release-contract.md").read_bytes())
    (root / "zig").mkdir()
    (root / "zig/native.txt").write_text("Native build uses zig/docs as its canonical docs reference.\n")
    (root / "zig/docs").symlink_to("../docs", target_is_directory=True)
    (root / ".kittify/charter/charter.yaml").write_text(
        "mission_type_activations: [software-dev]\ngovernance:\n  charter:\n    authority_paths: [zig, docs, alternate-docs]\n"
    )
    _git(root, "add", "docs", "alternate-docs", "zig", ".kittify/charter/charter.yaml")
    _git(root, "commit", "-qm", "declare canonical docs and tracked native alias")
    assert _git(root, "ls-tree", "HEAD", "zig/docs") == "120000 blob a9594bfe4ab69aca32d7c51b17985ad9ee89e563\tzig/docs"
    return checkouts


@pytest.mark.parametrize("report_only", [False, True])
def test_contained_canonical_alias_records_and_qualifies(canonical_alias_owner: OwnedCheckouts, report_only: bool) -> None:
    checkouts = canonical_alias_owner
    before = primary_state(checkouts)
    recorded = record(checkouts, report_only=report_only)
    assert recorded.exit_code == 0, recorded.output
    inputs = json.loads(recorded.output)["input_artifacts"]
    assert inputs["material:zig/docs"]["path"] == "zig/docs"
    assert inputs["material:zig/docs"]["sha256"] != "directory"
    assert "material:docs/release-contract.md" in inputs
    assert not any(key.startswith("material:zig/docs/") for key in inputs)
    claimed = implement(checkouts)
    assert claimed.exit_code == 0, claimed.output
    assert (checkouts.owned_root / "zig/docs").readlink() == Path("../docs")
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("change", ["content", "add", "remove", "retarget", "equivalent_target", "external"])
def test_alias_target_changes_invalidate_owned_report(canonical_alias_owner: OwnedCheckouts, change: str) -> None:
    checkouts = canonical_alias_owner
    root = checkouts.owned_root
    assert record(checkouts, report_only=True).exit_code == 0
    if change == "content":
        (root / "docs/release-contract.md").write_text("Changed canonical contract.\n")
    elif change == "add":
        (root / "docs/new-rule.md").write_text("New canonical rule.\n")
    elif change == "remove":
        (root / "docs/release-contract.md").unlink()
    else:
        if change == "external":
            target = root.parent / "external-docs"
            target.mkdir()
            (target / "rule.md").write_text("Different authority.\n")
        (root / "zig/docs").unlink()
        link = {"retarget": "../alternate-docs", "equivalent_target": ".././docs", "external": "../../external-docs"}[change]
        (root / "zig/docs").symlink_to(link, target_is_directory=True)
    # Committing the material change proves freshness refusal, independently
    # of a dirty-input/dirty-checkout preflight refusal.
    _git(root, "add", "docs", "zig", "--all")
    _git(root, "commit", "-qm", "change alias material fixture")
    _assert_owned_analysis_refused_without_claim(checkouts)


@pytest.mark.parametrize("invalid", ["dangling", "cycle", "external", "undeclared", "untracked", "ancestor_escape", "absolute", "graph_cycle", "ancestor_link"])
def test_unsafe_alias_refuses_before_report_write(canonical_alias_owner: OwnedCheckouts, invalid: str) -> None:
    checkouts = canonical_alias_owner
    root = checkouts.owned_root
    alias = root / "zig/docs"
    if invalid == "untracked":
        _git(root, "rm", "--cached", "zig/docs")
        _git(root, "commit", "-qm", "untracked alias fixture")
    else:
        alias.unlink()
        if invalid == "dangling":
            target = "../missing-docs"
        elif invalid == "cycle":
            target = "docs"
        elif invalid == "undeclared":
            (root / "hidden-docs").mkdir()
            (root / "hidden-docs/secret.md").write_text("Not selected canonical authority.\n")
            target = "../hidden-docs"
        elif invalid == "ancestor_escape":
            (root.parent / "outside").mkdir()
            target = f"../../outside/../{root.name}/docs"
        elif invalid == "absolute":
            target = str(root / "docs")
        elif invalid == "graph_cycle":
            (root / "docs/native-backref").symlink_to("../zig", target_is_directory=True)
            target = "../docs"
        elif invalid == "ancestor_link":
            (root / "escape").symlink_to(root.parent, target_is_directory=True)
            target = "../escape/../docs"
        else:
            (root.parent / "external-docs").mkdir()
            target = "../../external-docs"
        alias.symlink_to(target, target_is_directory=True)
        _git(root, "add", "zig/docs", "docs")
        _git(root, "commit", "-qm", "unsafe alias fixture")
    before = primary_state(checkouts)
    owner_head = _git(root, "rev-parse", "HEAD")
    recorded = record(checkouts, report_only=True)
    assert recorded.exit_code == 1, recorded.output
    assert json.loads(recorded.output)["commit_status"] == "failed_before_write"
    assert not (checkouts.mission_dir / "analysis-report.md").exists()
    assert _git(root, "rev-parse", "HEAD") == owner_head
    assert primary_state(checkouts) == before


def test_dirty_alias_is_not_admitted_as_new_authority(canonical_alias_owner: OwnedCheckouts) -> None:
    checkouts = canonical_alias_owner
    alias = checkouts.owned_root / "zig/docs"
    alias.unlink()
    alias.symlink_to("../alternate-docs", target_is_directory=True)
    before = primary_state(checkouts)
    recorded = record(checkouts, report_only=True)
    assert recorded.exit_code == 1, recorded.output
    assert "differs from its committed target" in recorded.output
    assert not (checkouts.mission_dir / "analysis-report.md").exists()
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("phase", ["pre-commit", "post-commit"])
def test_alias_target_race_cannot_qualify_report(canonical_alias_owner: OwnedCheckouts, phase: str) -> None:
    from specify_cli.analysis_report import check_analysis_report_current
    from specify_cli.cli.commands._owned_checkout import resolve_owned_or_adopt
    from specify_cli.core.owned_mission import LIFECYCLE_OWNED_TOPOLOGIES

    checkouts = canonical_alias_owner
    hook = Path(_git(checkouts.owned_root, "rev-parse", "--git-common-dir")) / "hooks" / phase
    hook.write_text("#!/bin/sh\nprintf 'concurrent canonical change\\n' >> docs/release-contract.md\n")
    hook.chmod(0o755)
    before = primary_state(checkouts)
    recorded = record(checkouts, report_only=True)
    assert recorded.exit_code == 1, recorded.output
    payload = json.loads(recorded.output)
    assert payload["commit_status"] == "committed_unqualified"
    hook.unlink()
    owned = resolve_owned_or_adopt(
        checkouts.repository_root,
        checkouts.owned_root,
        checkouts.mission_slug,
        cwd=checkouts.owned_root,
        allowed_topologies=LIFECYCLE_OWNED_TOPOLOGIES,
    )
    assert owned is not None
    assert not check_analysis_report_current(checkouts.mission_dir, checkouts.owned_root, owned=owned).ok
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("linked", ["metadata", "metadata_ancestor"])
def test_b2_metadata_refuses_before_content_read(canonical_alias_owner: OwnedCheckouts, linked: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.analysis_inputs import MaterialInputError, collect_material_inputs

    checkouts = canonical_alias_owner
    root = checkouts.owned_root
    metadata = checkouts.mission_dir / "meta.json"
    external = root.parent / "external-metadata"
    external.mkdir()
    if linked == "metadata":
        target = external / "meta.json"
        target.write_bytes(metadata.read_bytes())
        metadata.unlink()
        metadata.symlink_to(target)
    else:
        target_dir = external / "mission"
        checkouts.mission_dir.rename(target_dir)
        checkouts.mission_dir.symlink_to(target_dir, target_is_directory=True)
    before = primary_state(checkouts)
    reads: list[Path] = []
    actual_read = Path.read_text

    def observed_read(path: Path, *args: object, **kwargs: object) -> str:
        if path.name == "meta.json":
            reads.append(path)
        return actual_read(path, *args, **kwargs)

    # Observation delegates to the real content reader; it does not replace
    # authority selection or manufacture a safe source path.
    monkeypatch.setattr(Path, "read_text", observed_read)
    with pytest.raises(MaterialInputError, match="symlink"):
        collect_material_inputs(checkouts.mission_dir, root)
    assert reads == [], f"Unsafe metadata content was read before refusal: {reads}"
    assert primary_state(checkouts) == before
