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
