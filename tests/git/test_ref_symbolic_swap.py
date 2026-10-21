"""Real Git commit-ID CAS must not follow a late symbolic-ref swap to primary."""

from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import tempfile
from typing import Any

import pytest

from specify_cli.git import ref_advance
from kernel.owned_process import bounded_run, process_budget
from tests._support.git_cli import git_out

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]


def _prepare_repo(tmp_path: Path) -> tuple[str, str]:
    git_out(tmp_path, "init", "-q", "-b", "main")
    git_out(tmp_path, "config", "user.name", "Symbolic swap fixture")
    git_out(tmp_path, "config", "user.email", "fixture@example.invalid")
    git_out(tmp_path, "config", "commit.gpgsign", "false")
    git_out(tmp_path, "commit", "-qm", "base", "--allow-empty")
    before = git_out(tmp_path, "rev-parse", "main")
    git_out(tmp_path, "branch", "feature/result", before)
    git_out(tmp_path, "checkout", "-q", "--detach", before)
    git_out(tmp_path, "commit", "-qm", "candidate", "--allow-empty")
    candidate = git_out(tmp_path, "rev-parse", "HEAD")
    return before, candidate


@pytest.mark.parametrize("operation", ["advance", "delete"])
def test_late_symbolic_swap_refuses_without_advancing_or_deleting_primary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str) -> None:
    before, candidate = _prepare_repo(tmp_path)
    original = ref_advance._run_git
    swapped = False

    def swap_before_real_write(repo: Path, args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal swapped
        if args[0] == "update-ref" and "refs/heads/feature/result" in args and not swapped:
            swapped = True
            git_out(repo, "symbolic-ref", "refs/heads/feature/result", "refs/heads/main")
        return original(repo, args, **kwargs)

    monkeypatch.setattr(ref_advance, "_run_git", swap_before_real_write)
    refused = False
    try:
        if operation == "advance":
            ref_advance.advance_branch_ref(tmp_path, "feature/result", candidate, expected_old_sha=before)
        else:
            ref_advance.delete_branch_ref(tmp_path, "feature/result", before)
    except (ref_advance.RefAdvanceError, ref_advance.RefDeleteError):
        refused = True
    assert swapped, "The race must occur at the actual canonical write boundary."
    assert git_out(tmp_path, "rev-parse", "main") == before
    assert refused, "Foreign symbolic state must be refused, not silently replaced."
    assert git_out(tmp_path, "symbolic-ref", "refs/heads/feature/result") == "refs/heads/main"


@pytest.mark.skipif(os.name != "posix", reason="Executable native reference hook fixture")
def test_prepared_git_lock_excludes_a_symbolic_swap_and_preserves_normal_advance(tmp_path: Path) -> None:
    before, candidate = _prepare_repo(tmp_path)
    marker = tmp_path / "native-lock.json"
    hook = tmp_path / ".git" / "hooks" / "reference-transaction"
    hook.write_text(
        f"#!{sys.executable}\n"
        "import json, subprocess, sys\n"
        "from pathlib import Path\n"
        "if sys.argv[1] == 'prepared':\n"
        "    result = subprocess.run(['git', 'symbolic-ref', 'refs/heads/feature/result', 'refs/heads/main'], capture_output=True, timeout=2)\n"
        f"    Path({str(marker)!r}).write_text(json.dumps({{'swap_exit': result.returncode}}))\n"
    )
    hook.chmod(0o700)
    ref_advance.advance_branch_ref(tmp_path, "feature/result", candidate, expected_old_sha=before)
    assert json.loads(marker.read_text())["swap_exit"] != 0
    assert git_out(tmp_path, "rev-parse", "main") == before
    assert git_out(tmp_path, "rev-parse", "feature/result") == candidate


def test_direct_cas_preserves_reflog_message_beginning_with_option_prefix(tmp_path: Path) -> None:
    before, candidate = _prepare_repo(tmp_path)
    result = ref_advance._update_branch_ref_cas(tmp_path, "refs/heads/feature/result", candidate, before, message="--retain-this-message")
    assert result.returncode == 0, result.stderr
    assert git_out(tmp_path, "reflog", "show", "-1", "--format=%gs", "feature/result") == "--retain-this-message"


@pytest.mark.parametrize("operation", ["write", "delete"])
def test_bookkeeping_namespace_cannot_follow_an_alias_into_primary(tmp_path: Path, operation: str) -> None:
    before, candidate = _prepare_repo(tmp_path)
    ref = "refs/spec-kitty/test-receipt"
    git_out(tmp_path, "symbolic-ref", ref, "refs/heads/main")
    result = ref_advance.write_bookkeeping_ref(tmp_path, ref, candidate) if operation == "write" else ref_advance.delete_bookkeeping_ref(tmp_path, ref)
    assert git_out(tmp_path, "rev-parse", "main") == before
    assert not result
    assert git_out(tmp_path, "symbolic-ref", ref) == "refs/heads/main"


@pytest.mark.parametrize("ref,value,old", [("refs/heads/feature/result", "HEAD", "0" * 40), ("refs/heads/feature/result\nupdate injected", "0" * 40, "0" * 40)])
def test_malformed_protocol_input_refuses_without_moving_refs(tmp_path: Path, ref: str, value: str, old: str) -> None:
    _prepare_repo(tmp_path)
    before = git_out(tmp_path, "for-each-ref", "--format=%(refname) %(objectname)")
    result = ref_advance._run_git(tmp_path, ["update-ref", ref, value, old])
    assert result.returncode != 0
    assert "Direct-ref CAS refused" in result.stderr
    assert git_out(tmp_path, "for-each-ref", "--format=%(refname) %(objectname)") == before


@pytest.mark.skipif(os.name != "posix", reason="Owned POSIX controller group fixture")
@pytest.mark.parametrize("expiry", ["clock", "inherited-budget"])
def test_expired_controller_terminates_git_and_live_hook_descendants(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, expiry: str) -> None:
    before, candidate = _prepare_repo(tmp_path)
    marker = tmp_path / "hook-processes.json"
    hook = tmp_path / ".git" / "hooks" / "reference-transaction"
    hook.write_text(
        f"#!{sys.executable}\n"
        "import json, os, subprocess, sys, time\n"
        "from pathlib import Path\n"
        "if sys.argv[1] == 'prepared':\n"
        "    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'])\n"
        f"    Path({str(marker)!r}).write_text(json.dumps([os.getpid(), child.pid]))\n"
        "    time.sleep(20)\n"
    )
    hook.chmod(0o700)
    if expiry == "clock":
        # Controlled expiry after a real descendant, not a fake writer.
        with tempfile.TemporaryDirectory(dir=tmp_path, prefix="owned-capture-") as directory:
            capture = Path(directory)
            controller = (
                "from pathlib import Path; from specify_cli.git import ref_advance as owner; "
                f"owner.time.monotonic=lambda: 100.0 if Path({str(marker)!r}).exists() else 0.0; "
                f"owner._transact_direct_ref('refs/heads/feature/result', {candidate!r}, {before!r}, owned_controller=True, capture_dir=Path({str(capture)!r}))"
            )
            result = bounded_run([sys.executable, "-c", controller], cwd=tmp_path, timeout=5, text=True)
        assert not capture.exists(), "The joining parent owns capture cleanup even after controller termination."
        assert result.returncode == -signal.SIGKILL, result.stderr
        assert "terminating the owned controller group" in result.stderr
    else:
        captures: list[Path] = []
        original = tempfile.TemporaryDirectory

        def observe_capture(*args: Any, **kwargs: Any) -> Any:
            owned = original(*args, **kwargs)
            if kwargs.get("prefix") == "kitty-ref-cas-":
                captures.append(Path(owned.name))
            return owned

        monkeypatch.setattr(ref_advance.tempfile, "TemporaryDirectory", observe_capture)
        with process_budget(2), pytest.raises(ref_advance.RefAdvanceError):
            ref_advance.advance_branch_ref(tmp_path, "feature/result", candidate, expected_old_sha=before)
        assert captures and all(not path.exists() for path in captures)
    for pid in json.loads(marker.read_text()):
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, timeout=2, check=False).stdout.strip()
        assert not state or state.startswith("Z"), f"Owned hook descendant {pid} is still active: {state}"
    assert git_out(tmp_path, "rev-parse", "main") == before
    assert git_out(tmp_path, "rev-parse", "feature/result") == before
    assert not (tmp_path / ".git" / "refs" / "heads" / "feature" / "result.lock").exists()
    # Clear only our injected hook fault, then prove ordinary fresh operation
    # works without deleting native locks or weakening any guard.
    hook.unlink()
    ref_advance.advance_branch_ref(tmp_path, "feature/result", candidate, expected_old_sha=before)
    assert git_out(tmp_path, "rev-parse", "feature/result") == candidate
    assert git_out(tmp_path, "rev-parse", "main") == before


def test_capture_cleanup_cannot_reclassify_a_confirmed_ref_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    before, candidate = _prepare_repo(tmp_path)
    original = tempfile.TemporaryDirectory.cleanup

    def cleanup_then_raise(directory: Any) -> None:
        original(directory)
        raise OSError("injected capture cleanup failure")

    monkeypatch.setattr(tempfile.TemporaryDirectory, "cleanup", cleanup_then_raise)
    ref_advance.advance_branch_ref(tmp_path, "feature/result", candidate, expected_old_sha=before)
    assert git_out(tmp_path, "rev-parse", "feature/result") == candidate
    assert git_out(tmp_path, "rev-parse", "main") == before
    assert "capture cleanup" in caplog.text


@pytest.mark.parametrize("invalid", ["missing-capture", "nonfinite", "expired", "missing-old"])
def test_invalid_controller_admission_never_starts_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: str) -> None:
    before, candidate = _prepare_repo(tmp_path)
    refs = git_out(tmp_path, "for-each-ref", "--format=%(refname) %(objectname)")

    def no_child(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Invalid controller admission must not start a child")

    monkeypatch.setattr(ref_advance.subprocess, "Popen", no_child)
    kwargs: dict[str, Any] = {}
    old: str | None = before
    if invalid == "missing-capture":
        kwargs["owned_controller"] = True
    elif invalid == "nonfinite":
        kwargs["deadline"] = float("inf")
    elif invalid == "expired":
        kwargs["deadline"] = 0.0
    else:
        old = None
    with pytest.raises((ValueError, subprocess.TimeoutExpired)):
        ref_advance._transact_direct_ref("refs/heads/feature/result", candidate, old, **kwargs)
    monkeypatch.undo()
    assert git_out(tmp_path, "for-each-ref", "--format=%(refname) %(objectname)") == refs


def test_expired_outer_budget_refuses_before_capture_or_child(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    before, candidate = _prepare_repo(tmp_path)

    def no_capture(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("No cleanup margin: refuse before creating capture state")

    monkeypatch.setattr(ref_advance.tempfile, "TemporaryDirectory", no_capture)
    with process_budget(0.1), pytest.raises(subprocess.TimeoutExpired):
        ref_advance._run_git(tmp_path, ["update-ref", "refs/heads/feature/result", candidate, before])
    assert git_out(tmp_path, "rev-parse", "feature/result") == before
