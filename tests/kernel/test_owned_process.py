"""Only a runner-created process group may be signalled; every test joins its child."""

import os
import subprocess
import sys

import pytest


def test_owned_process_group_is_terminated_and_joined() -> None:
    from kernel.owned_process import signal_owned_process_tree

    if os.name != "posix":
        pytest.skip("POSIX process-group fixture")
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)"],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        signal_owned_process_tree(process, force=True)
        assert process.wait(timeout=2) != 0
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=2)


def test_process_budget_caps_the_actual_git_subprocess(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time
    from kernel.git import GitCommandError, run_git
    from kernel.owned_process import process_budget

    if os.name != "posix":
        pytest.skip("POSIX owned-process fixture")
    tool = tmp_path / "git"
    tool.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(20)\n")
    tool.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    before = time.monotonic()
    with process_budget(0.1), pytest.raises(GitCommandError) as failed:
        run_git(tmp_path, "version", timeout=10)
    assert failed.value.timed_out
    assert time.monotonic() - before < 2


def test_timeout_joins_owned_parent_even_when_a_descendant_keeps_capture_open() -> None:
    import time
    from kernel.owned_process import bounded_run

    if os.name != "posix":
        pytest.skip("POSIX owned-process fixture")
    script = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'])"
    before = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        bounded_run([sys.executable, "-c", script], capture_output=True, check=False, timeout=0.1)
    assert time.monotonic() - before < 2


def test_shared_signal_authority_refuses_reaped_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    from kernel.owned_process import signal_owned_process_tree

    calls = []
    monkeypatch.setattr(os, "killpg", lambda *args: calls.append(args))
    signal_owned_process_tree(SimpleNamespace(returncode=0, pid=123456), force=True, platform="posix")
    assert calls == []
