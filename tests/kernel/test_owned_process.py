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


def test_invalid_capture_modes_refuse_before_starting_child() -> None:
    from kernel.owned_process import bounded_run, process_budget

    with pytest.raises(ValueError, match="Encoding"):
        bounded_run(["unused"], timeout=1, encoding="utf-8")
    with pytest.raises(OSError, match="unsupported"):
        bounded_run(["unused"], timeout=1, capture_output=False)
    with pytest.raises(ValueError, match="Finite"):
        bounded_run(["unused"])
    with pytest.raises(ValueError, match="Finite"), process_budget(float("inf")):
        pass


def test_bounded_capture_preserves_nonzero_command_failure() -> None:
    from kernel.owned_process import bounded_run

    with pytest.raises(subprocess.CalledProcessError) as failure:
        bounded_run([sys.executable, "-c", "raise SystemExit(7)"], timeout=2, check=True)
    assert failure.value.returncode == 7


def test_windows_tree_adapter_uses_exact_owned_pid_and_retains_direct_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    from kernel.owned_process import signal_owned_process_tree

    calls = []
    child = SimpleNamespace(returncode=None, pid=12345, poll=lambda: None, kill=lambda: calls.append("kill"), terminate=lambda: calls.append("terminate"))

    def unavailable(command):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1)

    signal_owned_process_tree(child, force=True, platform="nt", windows_tree_kill=unavailable)
    assert calls == [["taskkill", "/PID", "12345", "/T", "/F"], "kill"]


def test_deadline_observation_preserves_nested_budget_and_restores_owner() -> None:
    from kernel.owned_process import process_budget, process_deadline

    assert process_deadline() is None
    with process_budget(5):
        outer = process_deadline()
        assert outer is not None
        with process_budget(10):
            assert process_deadline() == outer
        with process_budget(1):
            inner = process_deadline()
            assert inner is not None and inner < outer
        assert process_deadline() == outer
    assert process_deadline() is None


@pytest.mark.parametrize("payload,text", [(None, True), ("", True), ("joined λ\n", True), (b"\x00\xff\n", False)])
def test_bounded_stdin_preserves_exact_input_under_budget(payload, text) -> None:
    from kernel.owned_process import bounded_run, process_budget

    with process_budget(2):
        result = bounded_run(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
            input=payload,
            text=text,
            encoding="utf-8" if text else None,
            check=True,
        )
    assert result.stdout == (payload if payload is not None else "")


def test_bounded_stdin_timeout_joins_child_that_does_not_read(tmp_path) -> None:
    import time
    from kernel.owned_process import bounded_run, process_budget

    marker = tmp_path / "owned-child.json"
    script = "import os,pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(20)"
    before = time.monotonic()
    with process_budget(0.5), pytest.raises(subprocess.TimeoutExpired):
        bounded_run([sys.executable, "-c", script, str(marker)], input=b"x" * (2 * 1024 * 1024), timeout=10)
    assert time.monotonic() - before < 2
    assert marker.exists()
    with pytest.raises(ChildProcessError):
        os.waitpid(int(marker.read_text()), os.WNOHANG)


@pytest.mark.parametrize("payload,text", [(b"bytes", True), ("text", False)])
def test_bounded_stdin_type_mismatch_refuses_before_child(payload, text, monkeypatch) -> None:
    from kernel.owned_process import bounded_run

    def unexpected_child(*args, **kwargs):
        pytest.fail("Mismatched stdin must refuse before process creation")

    monkeypatch.setattr(subprocess, "Popen", unexpected_child)
    with pytest.raises(TypeError, match="input"):
        bounded_run(["unused"], input=payload, text=text, timeout=1)
