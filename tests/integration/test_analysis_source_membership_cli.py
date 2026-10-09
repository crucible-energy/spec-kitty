"""Declared native-shaped authority excludes derived outputs by Git policy."""

import json
from pathlib import Path

import pytest

from tests.integration.conftest import OwnedCheckouts, _git
from tests.integration.test_owned_analysis_implementation_cli import prepared_owner as prepared_owner, primary_state
from tests.integration.test_analysis_bootstrap_templates_cli import cold_environment as cold_environment, cli, recording

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection, pytest.mark.real_drain_posture]


@pytest.fixture
def source_owner(prepared_owner: OwnedCheckouts) -> OwnedCheckouts:
    root = prepared_owner.owned_root
    (root / "docs").mkdir()
    (root / "docs/contract.md").write_text("# Canonical contract\nFR-001 remains source authority.\n")
    (root / "zig").mkdir()
    (root / "zig/build.zig").write_text("// Committed build source.\n")
    (root / "zig/docs").symlink_to("../docs", target_is_directory=True)
    (root / ".gitignore").write_text("/zig/.zig-cache/\n/zig/zig-out/\n/zig/*.ignored\n")
    (root / ".kittify/charter/charter.yaml").write_text("mission_type_activations: [software-dev]\ngovernance:\n  charter:\n    authority_paths: [docs, zig]\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "declare native-shaped source authority and ignore policy")
    for directory in (".zig-cache", "zig-out"):
        (root / "zig" / directory).mkdir()
        for index in range(100):
            (root / "zig" / directory / f"artifact-{index}").write_bytes(b"derived compiler bytes\0")
    assert _git(root, "status", "--porcelain=v1") == ""
    return prepared_owner


@pytest.mark.parametrize("report_only", [False, True])
def test_ignored_outputs_do_not_block_owned_recording(source_owner: OwnedCheckouts, cold_environment: dict[str, str], report_only: bool) -> None:
    checkouts = source_owner
    root = checkouts.owned_root
    hook = Path(_git(root, "rev-parse", "--git-common-dir")) / "hooks/pre-commit"
    hook.write_text("#!/bin/sh\nprintf 'compatibility hook cache\\n' > zig/.zig-cache/hook-cache\nprintf 'emitted binary\\n' > zig/zig-out/hook-binary\n")
    hook.chmod(0o755)
    before = primary_state(checkouts)
    recorded = recording(checkouts, cold_environment, report_only=report_only)
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    payload = json.loads(recorded.stdout)
    assert payload["commit_status"] == "committed"
    inputs = payload["input_artifacts"]
    assert "material:zig/build.zig" in inputs and "material:docs/contract.md" in inputs
    assert "material:.gitignore" in inputs
    assert "material:zig/docs" in inputs and not any(key.startswith("material:zig/docs/") for key in inputs)
    assert not any(key.startswith(("material:zig/.zig-cache", "material:zig/zig-out")) for key in inputs)
    assert (root / "zig/zig-out/hook-binary").read_bytes() == b"emitted binary\n"
    hook.unlink()
    claimed = cli(
        root, cold_environment, "agent", "action", "implement", "WP01", "--mission", checkouts.mission_slug, "--owned-checkout", str(root), "--agent", "codex"
    )
    assert claimed.returncode == 0, claimed.stdout + claimed.stderr
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("change", ["tracked_ignored", "deleted_tracked_ignored", "untracked_source", "explicit_ignored", "ignore_policy"])
def test_real_source_dirt_still_refuses_before_write(source_owner: OwnedCheckouts, cold_environment: dict[str, str], change: str) -> None:
    checkouts = source_owner
    root = checkouts.owned_root
    if change in ("tracked_ignored", "deleted_tracked_ignored"):
        relative = "zig/.zig-cache/source.zig"
        path = root / relative
        path.write_text("Committed source despite its ignored location.\n")
        _git(root, "add", "-f", relative)
        _git(root, "commit", "-qm", "track source in ignored directory")
        if change == "deleted_tracked_ignored":
            path.unlink()
        else:
            path.write_text("Dirty tracked source.\n")
    elif change == "untracked_source":
        relative = "zig/new-source.zig"
        (root / relative).write_text("Uncommitted source.\n")
    elif change == "explicit_ignored":
        relative = "zig/reference.ignored"
        charter = root / ".kittify/charter/charter.yaml"
        charter.write_text(charter.read_text() + "    governance_references: [zig/reference.ignored]\n")
        _git(root, "add", str(charter))
        _git(root, "commit", "-qm", "select an ignored material reference")
        (root / relative).write_text("Explicitly selected uncommitted authority.\n")
    else:
        relative = ".gitignore"
        (root / relative).write_text((root / relative).read_text() + "# Uncommitted policy change.\n")
    head = _git(root, "rev-parse", "HEAD")
    before = primary_state(checkouts)
    recorded = recording(checkouts, cold_environment)
    assert recorded.returncode == 1, recorded.stdout + recorded.stderr
    payload = json.loads(recorded.stdout)
    assert payload["commit_status"] == "failed_before_write"
    assert payload["error_code"] == "DIRTY_ANALYSIS_INPUT"
    assert payload["dirty_paths"] == [relative]
    assert not (checkouts.mission_dir / "analysis-report.md").exists()
    assert _git(root, "rev-parse", "HEAD") == head
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("change", ["ignore_policy", "tracked_membership"])
def test_committed_policy_and_membership_changes_invalidate_admission(source_owner: OwnedCheckouts, cold_environment: dict[str, str], change: str) -> None:
    checkouts = source_owner
    root = checkouts.owned_root
    recorded = recording(checkouts, cold_environment)
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    if change == "ignore_policy":
        path = root / ".gitignore"
        path.write_text(path.read_text() + "# Committed source-membership policy change.\n")
        _git(root, "add", ".gitignore")
    else:
        relative = "zig/.zig-cache/new-tracked-source.zig"
        (root / relative).write_text("Now a tracked material source.\n")
        _git(root, "add", "-f", relative)
    _git(root, "commit", "-qm", "change committed membership authority")
    before = primary_state(checkouts)
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    head = _git(root, "rev-parse", "HEAD")
    claimed = cli(
        root, cold_environment, "agent", "action", "implement", "WP01", "--mission", checkouts.mission_slug, "--owned-checkout", str(root), "--agent", "codex"
    )
    assert claimed.returncode == 1, claimed.stdout + claimed.stderr
    assert "analysis_report_required" in claimed.stdout + claimed.stderr
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert _git(root, "rev-parse", "HEAD") == head
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("phase", ["pre-commit", "post-commit"])
def test_ignore_policy_commit_race_cannot_qualify_report(source_owner: OwnedCheckouts, cold_environment: dict[str, str], phase: str) -> None:
    checkouts = source_owner
    root = checkouts.owned_root
    hook = Path(_git(root, "rev-parse", "--git-common-dir")) / "hooks" / phase
    hook.write_text("#!/bin/sh\nprintf '# concurrent ignore policy change\\n' >> .gitignore\n")
    hook.chmod(0o755)
    before = primary_state(checkouts)
    recorded = recording(checkouts, cold_environment)
    assert recorded.returncode == 1, recorded.stdout + recorded.stderr
    assert json.loads(recorded.stdout)["commit_status"] == "committed_unqualified"
    hook.unlink()
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("report_only", [False, True])
def test_b3_explicit_ignored_directory_with_tracked_child_refuses_owned_recording(
    source_owner: OwnedCheckouts, cold_environment: dict[str, str], report_only: bool
) -> None:
    checkouts = source_owner
    root = checkouts.owned_root
    charter = root / ".kittify/charter/charter.yaml"
    charter.write_text(charter.read_text() + "    governance_references: [zig/.zig-cache]\n")
    tracked = root / "zig/.zig-cache/tracked-source.zig"
    tracked.write_text("Tracked ignored source in explicit directory authority.\n")
    _git(root, "add", str(charter))
    _git(root, "add", "-f", "zig/.zig-cache/tracked-source.zig")
    _git(root, "commit", "-qm", "select ignored directory containing tracked source")
    authority = root / "zig/.zig-cache/explicit-reference.md"
    authority.write_text("Uncommitted explicitly selected authority.\n")
    assert _git(root, "status", "--porcelain=v1") == ""
    head = _git(root, "rev-parse", "HEAD")
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    before = primary_state(checkouts)
    recorded = recording(checkouts, cold_environment, report_only=report_only)
    assert recorded.returncode == 1, recorded.stdout + recorded.stderr
    payload = json.loads(recorded.stdout)
    assert payload["commit_status"] == "failed_before_write"
    assert payload["error_code"] == "DIRTY_ANALYSIS_INPUT"
    assert "zig/.zig-cache/explicit-reference.md" in payload["dirty_paths"]
    assert not any(path.startswith("zig/zig-out/") for path in payload["dirty_paths"])
    assert not (checkouts.mission_dir / "analysis-report.md").exists()
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert _git(root, "rev-parse", "HEAD") == head
    assert primary_state(checkouts) == before
