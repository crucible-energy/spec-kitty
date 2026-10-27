"""Preserve the pre-repair public export contract without unrelated startup work."""

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


def test_next_only_app_keeps_pin_and_schema_refusal(monkeypatch, tmp_path):
    import specify_cli
    from typer.testing import CliRunner

    seen = []
    monkeypatch.setattr(sys, "argv", ["spec-kitty", "next"])
    monkeypatch.setattr(specify_cli, "locate_project_root", lambda: tmp_path)
    monkeypatch.setattr("specify_cli.runtime.bootstrap.check_version_pin", lambda root: seen.append(("pin", root)))

    def refuse(root, invoked_subcommand):
        seen.append(("schema", root, invoked_subcommand))
        raise SystemExit(42)

    monkeypatch.setattr("specify_cli.migration.gate.check_schema_version", refuse)
    result = CliRunner().invoke(specify_cli._build_app(), ["next", "--agent", "test", "--mission", "private-gate", "--json"])
    assert result.exit_code == 42, result.output
    assert seen == [("pin", tmp_path), ("schema", tmp_path, "next")]


def test_next_app_does_not_initialize_unrelated_project_installer():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.argv=['spec-kitty', 'next']; import specify_cli; specify_cli._build_app(); assert 'specify_cli.cli.commands.init' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_catalog_read_does_not_initialize_compiler_or_interview():
    result = subprocess.run(
        [sys.executable, "-c", "import sys; import charter.catalog; assert 'charter.compiler' not in sys.modules; assert 'charter.interview' not in sys.modules"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_every_preexisting_public_export_keeps_its_original_identity():
    import charter

    contract = json.loads((Path(__file__).parents[1] / "fixtures/charter-public-exports.json").read_text())
    assert charter.__all__ == list(contract)
    assert set(contract) <= set(dir(charter))
    for name, module in contract.items():
        assert getattr(charter, name) is getattr(importlib.import_module(f"charter.{module}"), name)
    with pytest.raises(AttributeError):
        _ = charter.not_a_charter_export


def test_sync_function_identity_survives_submodule_import_order():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib; import charter; module = importlib.import_module('charter.sync'); assert charter.sync is module.sync; assert callable(charter.sync)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
