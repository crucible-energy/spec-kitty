"""Real root CLI consumer isolation survives another package asset writer."""

from pathlib import Path
import json

import pytest

from specify_cli.runtime.merge import merge_package_assets
from tests.integration.conftest import OwnedCheckouts
from tests.integration.test_owned_analysis_implementation_cli import prepared_owner as prepared_owner, primary_state
from tests.integration.test_analysis_bootstrap_templates_cli import (
    cold_environment as cold_environment,
    cli,
    recording,
    selected_template,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection, pytest.mark.real_drain_posture]


def snapshot(root: Path) -> dict[str, tuple[bytes | None, int, int, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes() if path.is_file() else None, path.lstat().st_mode, path.lstat().st_ino, path.lstat().st_mtime_ns)
        for path in root.rglob("*")
    }


def test_consumer_record_implement_survives_shared_runtime_replacement(prepared_owner: OwnedCheckouts, cold_environment: dict[str, str], tmp_path: Path) -> None:
    env = dict(cold_environment, SPEC_KITTY_HOME=str(tmp_path / "qualified-runtime"), SPEC_KITTY_ASSET_SCOPE="consumer")
    shared = Path(env["HOME"])
    for name in (".kittify/missions/custom/sentinel.md", ".claude/commands/custom.md", ".agents/skills/custom/SKILL.md", ".config/opencode/commands/custom.md"):
        path = shared / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"user-owned sentinel\n")
    shared_before = snapshot(shared)
    primary_before = primary_state(prepared_owner)
    recorded = recording(prepared_owner, env)
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert json.loads(recorded.stdout)["commit_status"] == "committed"
    assert snapshot(shared) == shared_before, "consumer startup must have zero shared-user asset effects"
    private = Path(env["SPEC_KITTY_HOME"])
    assert (private / "agent-assets/.claude/commands/spec-kitty.analyze.md").is_file()
    assert (private / "agent-assets/.agents/skills/spk-doctrine-profile-load/SKILL.md").is_file()
    template_before = selected_template(env).stat()
    assets_before = snapshot(private / "agent-assets")
    # The retained legacy public writer has the same rmtree/copytree behavior
    # as the observed installed 3.2.7 bootstrap. Keep the test self-contained.
    staged = tmp_path / "other-package"
    target = staged / "missions/software-dev/templates/spec-template.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"another package's selected template\n")
    merge_package_assets(staged, shared / ".kittify")
    shared_after_foreign_write = snapshot(shared)
    claimed = cli(
        prepared_owner.owned_root,
        env,
        "agent",
        "action",
        "implement",
        "WP01",
        "--mission",
        prepared_owner.mission_slug,
        "--owned-checkout",
        str(prepared_owner.owned_root),
        "--agent",
        "codex",
    )
    assert claimed.returncode == 0, claimed.stdout + claimed.stderr
    assert selected_template(env).stat() == template_before
    assert snapshot(private / "agent-assets") == assets_before
    assert snapshot(shared) == shared_after_foreign_write
    assert primary_state(prepared_owner) == primary_before


@pytest.mark.parametrize("scope,home", [("unknown", "absolute"), ("consumer", "missing"), ("consumer", "relative"), ("consumer", "empty")])
def test_invalid_consumer_configuration_refuses_before_effects(
    prepared_owner: OwnedCheckouts, cold_environment: dict[str, str], tmp_path: Path, scope: str, home: str
) -> None:
    env = dict(cold_environment, SPEC_KITTY_ASSET_SCOPE=scope)
    destination = tmp_path / "invalid-home"
    if home == "missing":
        env.pop("SPEC_KITTY_HOME")
    else:
        env["SPEC_KITTY_HOME"] = str(destination) if home == "absolute" else "relative-runtime" if home == "relative" else ""
    shared = Path(env["HOME"])
    before = snapshot(shared)
    primary_before = primary_state(prepared_owner)
    result = cli(prepared_owner.owned_root, env, "agent", "profile", "list", "--json")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "SPEC_KITTY" in result.stdout + result.stderr
    assert snapshot(shared) == before
    assert not destination.exists()
    assert not (prepared_owner.owned_root / "relative-runtime").exists()
    assert primary_state(prepared_owner) == primary_before
