"""Finite native foreground sampler; existing Python state consumer is authority.

The public operation is deliberately narrower than the Python CLI. It neither
starts a detached process nor adopts the original Linux check recipe.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts.ci import memory_sampler as oracle
from tests.local_validation.test_candidate import ROOT, digest
from tests.local_validation.test_receipt import NATIVE_SOURCES, retain_native_build_metadata


@pytest.fixture(scope="session")
def sampler_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    supplied = os.environ.get("SPEC_KITTY_NATIVE_EXECUTION_BINDING")
    if supplied:
        binding = json.loads(Path(supplied).read_bytes())
        for name, expected in binding["sources"].items():
            assert digest((ROOT / name).read_bytes()) == expected
        image = Path(binding["image"])
        assert digest(image.read_bytes()) == binding["image_sha256"]
        return image
    image = tmp_path_factory.mktemp("native-memory-sampler") / "executor"
    argv = [shutil.which("zig") or "zig", "build-exe", "-j1", "-OReleaseSafe", "-lc", str(ROOT / "tools/zig/validation_execution.zig"), "-femit-bin=" + str(image)]
    compiled = subprocess.run(argv, check=True, capture_output=True, timeout=120)
    retain_native_build_metadata(image, NATIVE_SOURCES, argv, compiled)
    return image


def invoke(image: Path, operation: str, path: Path, directory: Path) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run([str(image), operation, str(path)], capture_output=True, timeout=15)
    (directory / "invocation.stdout.log").write_bytes(result.stdout)
    (directory / "invocation.stderr.log").write_bytes(result.stderr)
    return result


def request(directory: Path, **changes: Any) -> tuple[Path, dict[str, Any]]:
    proc = directory / "proc"
    proc.mkdir()
    (proc / "meminfo").write_bytes(b"MemTotal: 16384 kB\nMemAvailable: 8192 kB\n")
    value = {
        "schema_version": 1,
        "destination": str(directory / "new-state"),
        "proc_root": str(proc.resolve()),
        "interval_ms": 0,
        "max_samples": 3,
        "wall_ms": 5000,
        **changes,
    }
    path = directory / "request.json"
    path.write_text(json.dumps(value, sort_keys=True))
    return path, value


def test_existing_native_entry_and_bound_image_are_usable(sampler_binary: Path, tmp_path: Path) -> None:
    path = tmp_path / "help.json"
    path.write_text(json.dumps({"repository_root": str(ROOT), "argv": ["--help"]}))
    result = invoke(sampler_binary, "changelog-style", path, tmp_path)
    assert result.returncode == 0 and b"usage:" in result.stdout and result.stderr == b""


def test_native_memory_sample_produces_state_for_existing_python_consumer(sampler_binary: Path, tmp_path: Path) -> None:
    path, value = request(tmp_path)
    result = invoke(sampler_binary, "memory-sample", path, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == b""
    output = Path(value["destination"]) / "state.json"
    raw = output.read_text()
    state = oracle.from_json(raw)
    assert state is not None
    assert set(json.loads(raw)) == {"baseline_bytes", "elapsed_seconds", "peak_bytes", "pid", "samples", "source"}
    assert state.baseline_bytes == state.peak_bytes == 8192 * 1024
    assert state.samples == value["max_samples"] == 3 and state.source == "meminfo"
    assert state.pid > 0 and 0 <= state.elapsed_seconds <= value["wall_ms"] / 1000
    assert oracle.render_report(state, None, warn_bytes=10 * oracle.GIB, error_bytes=12 * oracle.GIB)[0].startswith(
        "peak_rss_bytes=8388608 source=meminfo baseline_bytes=8388608 delta_bytes=0 samples=3 elapsed_s="
    )
    assert Path(value["destination"]).stat().st_mode & 0o777 == 0o700 and output.stat().st_mode & 0o777 == 0o600
    assert not list(Path(value["destination"]).glob("*.tmp")) and not list(Path(value["destination"]).glob("*.pid"))
