"""Operation custody through real linked Git worktrees and public commands."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli import app
from tests.specify_cli.invocation.cli.test_dispatch import ArgvCliRunner

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
runner = ArgvCliRunner()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def workspaces(tmp_path: Path) -> tuple[Path, Path]:
    primary = tmp_path / "primary"
    primary.mkdir()
    _git(primary, "init", "-b", "main")
    _git(primary, "config", "user.email", "fixture@example.invalid")
    _git(primary, "config", "user.name", "Operation fixture")
    (primary / ".kittify").mkdir()
    (primary / ".kittify" / "config.yaml").write_text("{}\n")
    _git(primary, "add", ".kittify/config.yaml")
    _git(primary, "commit", "-m", "fixture seed")
    # Space tests the executable close contract's shell quoting.
    lane = tmp_path / "owned lane"
    _git(primary, "worktree", "add", "-b", "fixture/operations", str(lane))
    return primary.resolve(), lane.resolve()


def _open(lane: Path):  # type: ignore[no-untyped-def]
    context = MagicMock(mode="compact", text="fixture governance")
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=context):
        return runner.invoke(
            app,
            [
                "dispatch",
                "diagnose checkout custody",
                "--profile",
                "generic-agent",
                "--owned-checkout",
                str(lane),
                "--json",
            ],
        )


def test_owned_open_and_generated_close_keep_primary_untouched(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, lane = workspaces
    before_head = _git(primary, "rev-parse", "HEAD")
    monkeypatch.chdir(lane)
    opened = _open(lane)
    assert opened.exit_code == 0, opened.output
    payload = json.loads(opened.stdout)
    record = lane / "kitty-ops" / f"{payload['invocation_id']}.jsonl"
    assert record.is_file()
    assert not (primary / "kitty-ops").exists()
    close_args = shlex.split(payload["close_contract"]["command"])[1:]
    close_args[close_args.index("--outcome") + 1] = "done"
    assert close_args[close_args.index("--owned-checkout") + 1] == str(lane)
    # The generated instruction must work even after the caller changes cwd.
    unrelated = primary.parent / "outside-repository"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    closed = runner.invoke(app, [*close_args, "--json"])
    assert closed.exit_code == 0, closed.output
    events = [json.loads(line) for line in record.read_text().splitlines()]
    assert [event["event"] for event in events] == ["started", "completed"]
    assert _git(primary, "rev-parse", "HEAD") == before_head
    assert _git(primary, "status", "--porcelain") == ""
    assert _git(lane, "show", f"HEAD:kitty-ops/{record.name}")


@pytest.mark.parametrize("opt_out", ["hatch", "empty_config"])
def test_main_opt_out_cannot_bypass_branch_first(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    opt_out: str,
) -> None:
    primary, _ = workspaces
    if opt_out == "hatch":
        monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
    else:
        (primary / ".kittify" / "config.yaml").write_text("protection:\n  protected_branches: []\n")
    before = _git(primary, "status", "--porcelain")
    monkeypatch.chdir(primary)
    result = _open(primary)
    assert result.exit_code != 0
    assert "protected" in result.output.lower()
    assert not (primary / "kitty-ops").exists()
    assert _git(primary, "status", "--porcelain") == before


def test_branch_binding_refuses_generated_close_after_checkout_switch(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, lane = workspaces
    monkeypatch.chdir(lane)
    opened = _open(lane)
    assert opened.exit_code == 0, opened.output
    payload = json.loads(opened.stdout)
    record = lane / "kitty-ops" / f"{payload['invocation_id']}.jsonl"
    before = record.read_bytes()
    _git(lane, "checkout", "-b", "fixture/another-task")
    head = _git(lane, "rev-parse", "HEAD")
    args = shlex.split(payload["close_contract"]["command"])[1:]
    args[args.index("--outcome") + 1] = "done"
    monkeypatch.chdir(primary)
    closed = runner.invoke(app, [*args, "--json"])
    assert closed.exit_code != 0
    assert record.read_bytes() == before
    assert _git(lane, "rev-parse", "HEAD") == head


def test_branch_switch_during_open_refuses_before_creating_record(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, lane = workspaces
    monkeypatch.chdir(lane)
    context = MagicMock(mode="compact", text="fixture governance")

    def switch_branch(*args: object, **kwargs: object) -> MagicMock:
        _git(lane, "checkout", "-b", "fixture/switched-during-open")
        return context

    with patch("specify_cli.invocation.executor.build_charter_context", side_effect=switch_branch):
        result = runner.invoke(
            app,
            [
                "dispatch",
                "diagnose checkout custody",
                "--profile",
                "generic-agent",
                "--owned-checkout",
                str(lane),
                "--json",
            ],
        )
    assert result.exit_code != 0
    assert not (lane / "kitty-ops").exists()
    assert _git(primary, "status", "--porcelain") == ""


@pytest.mark.parametrize("explicit", [False, True])
def test_main_refused_before_any_record_write(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    explicit: bool,
) -> None:
    primary, _ = workspaces
    monkeypatch.chdir(primary)
    args = ["dispatch", "diagnose custody", "--profile", "generic-agent", "--json"]
    if explicit:
        args.extend(["--owned-checkout", str(primary)])
    result = runner.invoke(app, args)
    assert result.exit_code != 0
    assert "protected" in result.output.lower()
    assert _git(primary, "status", "--porcelain") == ""


def test_detached_owned_checkout_refused_before_write(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, lane = workspaces
    _git(lane, "checkout", "--detach")
    monkeypatch.chdir(primary)
    result = _open(lane)
    assert result.exit_code != 0
    assert "branch" in result.output.lower()
    assert not (lane / "kitty-ops").exists()


def test_foreign_checkout_refused_before_write(
    workspaces: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, _ = workspaces
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _git(foreign, "init", "-b", "fixture/foreign")
    monkeypatch.chdir(primary)
    result = _open(foreign)
    assert result.exit_code != 0
    assert not (foreign / "kitty-ops").exists()
    assert _git(primary, "status", "--porcelain") == ""


def test_nested_claim_refused_before_write(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, lane = workspaces
    nested = lane / "nested"
    nested.mkdir()
    monkeypatch.chdir(primary)
    result = _open(nested)
    assert result.exit_code != 0
    assert not (lane / "kitty-ops").exists()
    assert _git(primary, "status", "--porcelain") == ""


def test_uninitialized_main_refused_before_registry_creation(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, _ = workspaces
    shutil.rmtree(primary / ".kittify")
    monkeypatch.chdir(primary)
    result = runner.invoke(app, ["dispatch", "diagnose custody", "--profile", "generic-agent", "--json"])
    assert result.exit_code != 0
    assert "protected" in result.output.lower()
    assert not (primary / ".kittify").exists()
    assert not (primary / "kitty-ops").exists()


def test_dry_run_on_main_stays_read_only(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, _ = workspaces
    monkeypatch.chdir(primary)
    context = MagicMock(mode="compact", text="fixture governance")
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=context):
        result = runner.invoke(
            app,
            [
                "dispatch",
                "diagnose custody",
                "--profile",
                "generic-agent",
                "--owned-checkout",
                str(primary),
                "--dry-run",
                "--json",
            ],
        )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["status"] == "dry_run"
    assert "_owned_checkout" not in payload
    assert not (primary / "kitty-ops").exists()


def test_close_refused_on_protected_branch_before_append(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, lane = workspaces
    monkeypatch.chdir(lane)
    opened = _open(lane)
    assert opened.exit_code == 0, opened.output
    invocation_id = json.loads(opened.stdout)["invocation_id"]
    record = lane / "kitty-ops" / f"{invocation_id}.jsonl"
    before = record.read_bytes()
    _git(lane, "checkout", "-b", "release/protected")
    (lane / ".kittify" / "config.yaml").write_text(
        "protection:\n  protected_branches: [main, release/protected]\n",
    )
    monkeypatch.chdir(primary)
    result = runner.invoke(
        app,
        [
            "profile-invocation",
            "complete",
            "--invocation-id",
            invocation_id,
            "--outcome",
            "done",
            "--owned-checkout",
            str(lane),
            "--json",
        ],
    )
    assert result.exit_code != 0
    assert record.read_bytes() == before


def test_checkout_cannot_weaken_primary_protection(
    workspaces: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary, lane = workspaces
    (primary / ".kittify" / "config.yaml").write_text(
        "protection:\n  protected_branches: [main, fixture/operations]\n",
    )
    before = _git(primary, "status", "--porcelain")
    monkeypatch.chdir(lane)
    result = _open(lane)
    assert result.exit_code != 0
    assert "protected" in result.output.lower()
    assert not (lane / "kitty-ops").exists()
    assert _git(primary, "status", "--porcelain") == before
