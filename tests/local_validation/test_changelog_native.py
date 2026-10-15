"""Actual same-executable changelog component against the unchanged Python oracle."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.local_validation.test_candidate import ROOT
from tests.local_validation.test_execution import executor_binary as executor_binary


def test_same_native_executable_checks_an_actual_clean_changelog(executor_binary: Path, tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [Unreleased]\n### Added\n- **A useful change** (#1). Works.\n")
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"repository_root": str(ROOT), "argv": ["--changelog", str(changelog)]}))
    result = subprocess.run([str(executor_binary), "changelog-style", str(request)], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout == b"0 error(s), 0 warning(s)\n"
