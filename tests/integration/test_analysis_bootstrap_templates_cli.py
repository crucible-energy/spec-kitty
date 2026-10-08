"""Cold root-CLI bootstrap must not turn bundled templates into foreign authority."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import errno
import shlex

import pytest

from tests.integration.conftest import OwnedCheckouts, _git, _init_repo
from tests.integration.test_owned_analysis_implementation_cli import (
    BODY,
    prepared_owner as prepared_owner,
    primary_state,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo, pytest.mark.real_worktree_detection, pytest.mark.real_drain_posture]
SDK = Path(__file__).resolve().parents[2]


@pytest.fixture
def cold_environment(tmp_path: Path, prepared_owner: OwnedCheckouts) -> dict[str, str]:
    home = tmp_path / "cold-home"
    home.mkdir()
    if sys.platform == "darwin" and home.is_relative_to("/private/var"):
        # Exercise the exact /var system-alias spelling used by native callers.
        home = Path("/") / home.relative_to("/private")
    # Never expose inherited credentials through pytest's failure-local repr.
    env = {key: os.environ[key] for key in ("PATH", "TMPDIR", "LANG", "SYSTEMROOT") if key in os.environ}
    env.update(
        HOME=str(home), XDG_CONFIG_HOME=str(home / "config"), SPEC_KITTY_HOME=str(home / ".spec-kitty"), PYTHONPATH=str(SDK / "src"), PYTHONDONTWRITEBYTECODE="1"
    )
    assert not Path(env["SPEC_KITTY_HOME"]).exists()
    return env


def cli(root: Path, env: dict[str, str], *args: str, body: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "specify_cli", *args], cwd=root, env=env, input=body, capture_output=True, text=True, timeout=120)


def recording(checkouts: OwnedCheckouts, env: dict[str, str], *, report_only: bool = True) -> subprocess.CompletedProcess[str]:
    args = [
        "agent",
        "mission",
        "record-analysis",
        "--mission",
        checkouts.mission_slug,
        "--owned-checkout",
        str(checkouts.owned_root),
        "--agent",
        "opencode",
        "--json",
    ]
    if report_only:
        args.append("--report-only")
    return cli(checkouts.owned_root, env, *args, body=BODY)


def selected_template(env: dict[str, str]) -> Path:
    return Path(env["SPEC_KITTY_HOME"]) / "missions/software-dev/templates/spec-template.md"


def mutate_template(env: dict[str, str], change: str) -> None:
    path = selected_template(env)
    if change == "altered":
        path.write_bytes(path.read_bytes() + b"\nExternal mutable directive.\n")
    elif change == "global_identical":
        destination = Path(env["SPEC_KITTY_HOME"]) / "templates" / path.name
        destination.parent.mkdir()
        destination.write_bytes(path.read_bytes())
        path.unlink()
    else:
        linked = path if change == "leaf_symlink" else path.parent if change == "ancestor_symlink" else Path(env["SPEC_KITTY_HOME"])
        moved = linked.with_name(linked.name + "-foreign")
        linked.rename(moved)
        linked.symlink_to(moved, target_is_directory=change != "leaf_symlink")


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO synchronizes after real CLI bootstrap")
@pytest.mark.parametrize("change", ["altered", "global_identical", "leaf_symlink", "ancestor_symlink", "home_symlink"])
def test_after_bootstrap_unsafe_selection_refuses_before_write(
    prepared_owner: OwnedCheckouts, cold_environment: dict[str, str], tmp_path: Path, change: str
) -> None:
    checkouts = prepared_owner
    fifo = tmp_path / "analysis-input"
    os.mkfifo(fifo)
    before = primary_state(checkouts)
    head = _git(checkouts.owned_root, "rev-parse", "HEAD")
    command = [
        sys.executable,
        "-m",
        "specify_cli",
        "agent",
        "mission",
        "record-analysis",
        "--mission",
        checkouts.mission_slug,
        "--owned-checkout",
        str(checkouts.owned_root),
        "--input-file",
        str(fifo),
        "--report-only",
        "--json",
    ]
    child = subprocess.Popen(command, cwd=checkouts.owned_root, env=cold_environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 120
        while True:
            try:
                writer = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
                break
            except OSError as exc:
                if exc.errno != errno.ENXIO or child.poll() is not None or time.monotonic() >= deadline:
                    stdout, stderr = child.communicate(timeout=15)
                    pytest.fail(f"CLI did not reach its post-bootstrap input read: {stdout}{stderr}")
                time.sleep(0.05)
        with os.fdopen(writer, "w") as stream:
            # The real command has opened its input after ordinary bootstrap and
            # placement resolution. No bootstrap or authority resolver is mocked.
            assert selected_template(cold_environment).is_file()
            mutate_template(cold_environment, change)
            stream.write(BODY)
        stdout, stderr = child.communicate(timeout=120)
        assert child.returncode == 1, stdout + stderr
        assert json.loads(stdout)["commit_status"] == "failed_before_write"
        assert not (checkouts.mission_dir / "analysis-report.md").exists()
        assert _git(checkouts.owned_root, "rev-parse", "HEAD") == head
        assert primary_state(checkouts) == before
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=15)


@pytest.mark.parametrize("change", ["altered", "retarget_home", "equal_byte_replacement", "leaf_symlink"])
def test_post_report_selection_changes_refuse_without_claim(prepared_owner: OwnedCheckouts, cold_environment: dict[str, str], tmp_path: Path, change: str) -> None:
    checkouts = prepared_owner
    result = recording(checkouts, cold_environment)
    assert result.returncode == 0, result.stdout + result.stderr
    if change == "retarget_home":
        cold_environment["SPEC_KITTY_HOME"] = str(tmp_path / "retargeted-runtime")
    elif change == "equal_byte_replacement":
        path = selected_template(cold_environment)
        replacement = path.with_name("replacement")
        replacement.write_bytes(path.read_bytes())
        replacement.replace(path)
    else:
        mutate_template(cold_environment, change)
    before = primary_state(checkouts)
    head = _git(checkouts.owned_root, "rev-parse", "HEAD")
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    result = cli(
        checkouts.owned_root,
        cold_environment,
        "agent",
        "action",
        "implement",
        "WP01",
        "--mission",
        checkouts.mission_slug,
        "--owned-checkout",
        str(checkouts.owned_root),
        "--agent",
        "codex",
    )
    assert result.returncode == 1, result.stdout + result.stderr
    # Real bootstrap can repair managed altered bytes before freshness. Replica
    # identity still invalidates the previously recorded selection in that case.
    assert "analysis_report_required" in result.stdout + result.stderr or "STARTUP_ASSET" in result.stdout + result.stderr
    assert _git(checkouts.owned_root, "rev-parse", "HEAD") == head
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("phase", ["pre-commit", "post-commit"])
def test_real_global_template_commit_race_remains_unqualified(prepared_owner: OwnedCheckouts, cold_environment: dict[str, str], phase: str) -> None:
    checkouts = prepared_owner
    hook = Path(_git(checkouts.owned_root, "rev-parse", "--git-common-dir")) / "hooks" / phase
    hook.write_text(f"#!/bin/sh\nprintf 'concurrent external directive\\n' >> {shlex.quote(str(selected_template(cold_environment)))}\n")
    hook.chmod(0o755)
    before = primary_state(checkouts)
    result = recording(checkouts, cold_environment)
    assert result.returncode == 1, result.stdout + result.stderr
    assert json.loads(result.stdout)["commit_status"] == "committed_unqualified"
    hook.unlink()
    events = (checkouts.mission_dir / "status.events.jsonl").read_bytes()
    result = cli(
        checkouts.owned_root,
        cold_environment,
        "agent",
        "action",
        "implement",
        "WP01",
        "--mission",
        checkouts.mission_slug,
        "--owned-checkout",
        str(checkouts.owned_root),
        "--agent",
        "codex",
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "unqualified_report_transaction" in result.stdout + result.stderr
    assert (checkouts.mission_dir / "status.events.jsonl").read_bytes() == events
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("report_only", [False, True])
def test_cold_owned_bootstrap_records_and_admits(prepared_owner: OwnedCheckouts, cold_environment: dict[str, str], report_only: bool) -> None:
    checkouts = prepared_owner
    before = primary_state(checkouts)
    result = recording(checkouts, cold_environment, report_only=report_only)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert selected_template(cold_environment).is_file()
    assert payload["commit_status"] == "committed"
    assert {"package:built-in", "package:mission-assets"} <= payload["input_artifacts"].keys()
    assert "material:.kittify/charter/charter.yaml" in payload["input_artifacts"]
    assert f"material:kitty-specs/{checkouts.mission_slug}/tasks/WP01-owned.md" in payload["input_artifacts"]
    assert not any(str(Path(cold_environment["HOME"])) in str(entry) for entry in payload["input_artifacts"].values())
    claimed = cli(
        checkouts.owned_root,
        cold_environment,
        "agent",
        "action",
        "implement",
        "WP01",
        "--mission",
        checkouts.mission_slug,
        "--owned-checkout",
        str(checkouts.owned_root),
        "--agent",
        "codex",
    )
    assert claimed.returncode == 0, claimed.stdout + claimed.stderr
    assert primary_state(checkouts) == before


@pytest.mark.parametrize("report_only", [False, True])
def test_cold_ordinary_bootstrap_records(prepared_owner: OwnedCheckouts, cold_environment: dict[str, str], tmp_path: Path, report_only: bool) -> None:
    ordinary = tmp_path / "ordinary"
    _init_repo(ordinary)
    _git(ordinary, "branch", "-m", prepared_owner.target_branch)
    shutil.copytree(prepared_owner.owned_root / ".kittify", ordinary / ".kittify", dirs_exist_ok=True)
    shutil.copytree(prepared_owner.owned_root / "kitty-specs", ordinary / "kitty-specs")
    _git(ordinary, "add", ".")
    _git(ordinary, "commit", "-qm", "ordinary planning fixture")
    args = ["agent", "mission", "record-analysis", "--mission", prepared_owner.mission_slug, "--json"]
    if report_only:
        args.append("--report-only")
    result = cli(ordinary, cold_environment, *args, body=BODY)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    if report_only:
        assert payload["commit_status"] == "committed"
    assert (ordinary / "kitty-specs" / prepared_owner.mission_slug / "analysis-report.md").is_file()
    assert selected_template(cold_environment).is_file()
