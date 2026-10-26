"""Upgrade compatibility must describe the checkout the command will inspect."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from tests.upgrade.preview_support.fixtures import prepare_case
from tests.upgrade.preview_support.process import run_process
from tests.upgrade.preview_support.snapshot import assert_unchanged, snapshot

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
CHECKOUT = Path(__file__).resolve().parents[2]


def _set_fixture_schema(project: Path, schema: int) -> None:
    path = project / ".kittify/metadata.yaml"
    metadata = yaml.safe_load(path.read_text())
    metadata["spec_kitty"]["schema_version"] = schema
    path.write_text(yaml.safe_dump(metadata, sort_keys=False))


@pytest.mark.parametrize(("primary_schema", "selected_schema", "expected_exit"), [(999, 3, 0), (3, 999, 5)])
def test_public_linked_preview_binds_selected_checkout(tmp_path: Path, primary_schema: int, selected_schema: int, expected_exit: int) -> None:
    case = prepare_case(tmp_path / "case", CHECKOUT)
    selected = tmp_path / "selected"
    for args in (
        ["git", "add", "-A"],
        ["git", "add", "-f", ".kittify"],
        ["git", "commit", "--allow-empty", "-qm", "prepare synthetic linked upgrade baseline"],
        ["git", "worktree", "add", "-b", "codex/selected-upgrade", str(selected)],
    ):
        setup = run_process(args, case.project, case.env)
        assert setup.returncode == 0, setup
    assert (selected / ".kittify/metadata.yaml").is_file()
    _set_fixture_schema(case.project, primary_schema)
    _set_fixture_schema(selected, selected_schema)
    (case.project / "busy-owner.md").write_text("Preserve staged primary-owner work.\n")
    staged = run_process(["git", "add", "busy-owner.md"], case.project, case.env)
    assert staged.returncode == 0, staged
    roots = {"primary": case.project, "selected": selected, "home": Path(case.env["HOME"]), "temp": Path(case.env["TMPDIR"])}
    before = snapshot(roots)

    result = run_process([case.identity.executable, "upgrade", "--dry-run", "--json", "--no-worktrees"], selected, case.env)
    after = snapshot(roots)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "stdout.log").write_text(result.stdout)
    (evidence / "stderr.log").write_text(result.stderr)
    (evidence / "receipt.json").write_text(json.dumps({"identity": asdict(case.identity), "process": asdict(result)}, indent=2) + "\n")

    payload = result.json()
    assert result.returncode == expected_exit, result
    assert payload["project"]["project_root"] == str(selected)
    assert payload["project"]["schema_version"] == selected_schema
    assert payload["decision"] == ("BLOCK_CLI_UPGRADE" if expected_exit else "ALLOW")
    assert_unchanged(before, after)
