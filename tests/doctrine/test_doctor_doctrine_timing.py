"""NFR-005 doctor wall-clock guard, owned by the mandatory serial timing pole."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from tests.doctrine.test_doctrine_health_glossary_pack import (
    _invoke_doctrine_json,
    bare_repo_root as bare_repo_root,
)

pytestmark = [pytest.mark.unit, pytest.mark.timing]


class TestDoctorDoctrinePerformance:
    def test_doctor_doctrine_json_completes_under_two_seconds(self, bare_repo_root: Path) -> None:
        start = time.perf_counter()
        exit_code, _payload = _invoke_doctrine_json(bare_repo_root)
        elapsed = time.perf_counter() - start

        assert exit_code == 0
        assert elapsed < 2.0, f"doctor doctrine --json took {elapsed:.2f}s (budget: 2.0s)"
