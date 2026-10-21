"""Real Git commit-ID CAS must not follow a late symbolic-ref swap to primary."""

from pathlib import Path
import json
import os
import signal
import subprocess
import sys
from typing import Any

import pytest

from specify_cli.git import ref_advance
from kernel.owned_process import bounded_run
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
def test_expired_controller_terminates_git_and_live_hook_descendants(tmp_path: Path) -> None:
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
    # A controlled clock expiry after the real hook has spawned a descendant
    # exercises the inner deadline without a 20-second test or a fake writer.
    controller = (
        "from pathlib import Path; from specify_cli.git import ref_advance as owner; "
        f"owner.time.monotonic=lambda: 100.0 if Path({str(marker)!r}).exists() else 0.0; "
        f"owner._transact_direct_ref('refs/heads/feature/result', {candidate!r}, {before!r}, owned_controller=True)"
    )
    result = bounded_run([sys.executable, "-c", controller], cwd=tmp_path, timeout=5, text=True)
    assert result.returncode == -signal.SIGKILL, result.stderr
    assert "terminating the owned controller group" in result.stderr
    for pid in json.loads(marker.read_text()):
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, timeout=2, check=False).stdout.strip()
        assert not state or state.startswith("Z"), f"Owned hook descendant {pid} is still active: {state}"
    assert git_out(tmp_path, "rev-parse", "main") == before
    assert git_out(tmp_path, "rev-parse", "feature/result") == before
