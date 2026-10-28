"""Tests for ``charter.consistency_check`` (WP07, T033).

Covers:
- ``test_coherent_when_all_activated_ids_exist_in_doctrine``: All activated IDs
  are real doctrine IDs → report is coherent.
- ``test_unknown_reference_detected``: A planted fake ID → appears in
  ``unknown_references``; ``coherent`` is False.
- ``test_suggestion_contains_resolution_command``: Suggestion for unknown ID
  contains "charter deactivate".
- ``test_none_kind_skipped``: A kind with None activation (no config key) is
  skipped and produces no ``unknown_references`` entry for that kind.
- ``test_coherent_false_when_incoherent``: Any unknown ID → coherent is False.
- ``test_run_consistency_check_returns_report_object``: Return type and field
  types are correct.
- ``test_run_consistency_check_completes_within_2s``: NFR-003 performance guard.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from charter.consistency_check import ConsistencyReport, run_consistency_check
from charter.invocation_context import ProjectContext
from specify_cli.cli.commands.charter import charter_app

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# A real directive ID that exists in the built-in doctrine.
# Used in coherent tests to avoid false unknowns.
# ---------------------------------------------------------------------------
_REAL_DIRECTIVE_ID = "001-architectural-integrity-standard"


def _project_layer_fixture(root: Path) -> tuple[Path, Path]:
    """Independent retained-layout project with a compiled reference catalog."""
    kittify = root / ".kittify"
    layer = kittify / "doctrine"
    rule = layer / "directive" / "project-rule.directive.yaml"
    style = layer / "styleguide" / "project-style.styleguide.yaml"
    for path, body in [
        (rule, {"schema_version": "1.0", "id": "PROJECT_RULE", "title": "Project rule", "intent": "Keep project policy visible.", "enforcement": "required"}),
        (style, {"schema_version": "1.0", "id": "project-style", "title": "Project style", "scope": "code", "principles": ["Use explicit ownership."]}),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")
    (kittify / "config.yaml").write_text(
        "activated_directives: [project-rule]\nactivated_styleguides: [project-style]\n",
        encoding="utf-8",
    )
    charter = kittify / "charter" / "charter.yaml"
    charter.parent.mkdir()
    charter.write_text(
        json.dumps(
            {
                "catalog": {
                    "references": [
                        {"id": "DIRECTIVE:PROJECT_RULE", "kind": "directive"},
                        {"id": "STYLEGUIDE:project-style", "kind": "styleguide"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (layer / "graph.yaml").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "generated_at": "TEST",
                "generated_by": "independent fixture",
                "nodes": [{"urn": "directive:PROJECT_RULE", "kind": "directive"}, {"urn": "styleguide:project-style", "kind": "styleguide"}],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    return rule, charter


def _project_layer_report(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[int, dict[str, Any]]:
    unrelated = root.parent / "unrelated-cwd"
    unrelated.mkdir(exist_ok=True)
    monkeypatch.chdir(unrelated)
    result = CliRunner().invoke(charter_app, ["pack", "consistency-check", "--json", "--repo-root", str(root)])
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    assert result.exit_code in (0, 1), result.output
    return result.exit_code, json.loads(result.output)


def test_project_layer_cli_accepts_valid_artifacts_with_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _project_layer_fixture(tmp_path)
    code, report = _project_layer_report(tmp_path, monkeypatch)
    assert code == 0, report
    assert report["coherent"] is True
    assert report["unknown_references"] == []
    assert report["verification_errors"] == []


@pytest.mark.parametrize("body", [None, "[unterminated", "title: Missing identifier\n"])
def test_project_layer_cli_keeps_invalid_artifacts_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str | None) -> None:
    rule, _ = _project_layer_fixture(tmp_path)
    if body is None:
        rule.unlink()
    else:
        rule.write_text(body, encoding="utf-8")
    code, report = _project_layer_report(tmp_path, monkeypatch)
    assert code == 1
    assert report["coherent"] is False
    assert "directive/project-rule" in report["unknown_references"]


def test_project_layer_cli_keeps_catalog_divergence_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, charter = _project_layer_fixture(tmp_path)
    data = json.loads(charter.read_text(encoding="utf-8"))
    data["catalog"]["references"] = []
    charter.write_text(json.dumps(data), encoding="utf-8")
    code, report = _project_layer_report(tmp_path, monkeypatch)
    assert code == 1
    assert "directive/project-rule" in report["reference_id_divergences"]
    assert "styleguide/project-style" in report["reference_id_divergences"]


def test_project_layer_cli_preserves_active_tension_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rule, _ = _project_layer_fixture(tmp_path)
    graph = rule.parent.parent / "graph.yaml"
    data = json.loads(graph.read_text(encoding="utf-8"))
    data["edges"] = [{"source": "directive:PROJECT_RULE", "target": "styleguide:project-style", "relation": "in_tension_with"}]
    graph.write_text(json.dumps(data), encoding="utf-8")
    code, report = _project_layer_report(tmp_path, monkeypatch)
    assert code == 0, report  # Tensions stay advisory.
    findings = report["unreconciled_tensions"]
    assert len(findings) == 1
    assert findings[0]["type"] == "tension_unreconciled"
    assert findings[0]["pair"] == ["directive:PROJECT_RULE", "styleguide:project-style"]
    assert findings[0]["resolution_paths"] == ["deactivate one side", "activate a reconciler"]


def test_project_layer_cli_keeps_missing_graph_nodes_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rule, _ = _project_layer_fixture(tmp_path)
    (rule.parent.parent / "graph.yaml").unlink()
    code, report = _project_layer_report(tmp_path, monkeypatch)
    assert code == 1
    assert "directive/project-rule" in report["graph_kind_gaps"]
    assert "styleguide/project-style" in report["graph_kind_gaps"]


def test_project_layer_cli_preserves_project_precedence_over_org(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _project_layer_fixture(tmp_path)
    org = tmp_path / "org-pack"
    directive = org / "directives" / "project-rule.directive.yaml"
    directive.parent.mkdir(parents=True)
    directive.write_text(
        "schema_version: '1.0'\nid: ORG_RULE\ntitle: Org rule\nintent: Preserve organization policy.\nenforcement: required\n",
        encoding="utf-8",
    )
    config = tmp_path / ".kittify" / "config.yaml"
    with config.open("a", encoding="utf-8") as output:
        output.write(f"doctrine:\n  org:\n    packs:\n      - name: test-org\n        local_path: {org}\n")
    code, report = _project_layer_report(tmp_path, monkeypatch)
    assert code == 0, report
    assert report["coherent"] is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path, content: str) -> None:
    """Write a .kittify/config.yaml with the given content."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")


def _ctx_with_config(tmp_path: Path, config_yaml: str) -> ProjectContext:
    """Build a ProjectContext with the supplied config content."""
    _write_config(tmp_path, config_yaml)
    return ProjectContext.from_repo(tmp_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
def test_coherent_when_all_activated_ids_exist_in_doctrine(tmp_path: Path) -> None:
    """Activating a real doctrine directive ID → report is coherent."""
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {_REAL_DIRECTIVE_ID}\n",
    )
    report = run_consistency_check(ctx)

    assert report.coherent is True
    assert report.unknown_references == []


@pytest.mark.doctrine
def test_unknown_reference_detected(tmp_path: Path) -> None:
    """A planted fake directive ID → appears in unknown_references."""
    fake_id = "totally-fake-directive-zzz"
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {fake_id}\n",
    )
    report = run_consistency_check(ctx)

    assert any(fake_id in ref for ref in report.unknown_references), f"Expected '{fake_id}' in unknown_references but got: {report.unknown_references}"
    assert report.coherent is False


@pytest.mark.doctrine
def test_duplicate_activation_entry_detected(tmp_path: Path) -> None:
    """Duplicate YAML entries must not be hidden by frozenset conversion."""
    ctx = _ctx_with_config(
        tmp_path,
        (f"activated_directives:\n  - {_REAL_DIRECTIVE_ID}\n  - {_REAL_DIRECTIVE_ID}\n"),
    )
    report = run_consistency_check(ctx)

    assert report.coherent is False
    assert any("Duplicate entry" in v for v in report.kind_violations)


@pytest.mark.doctrine
def test_suggestion_contains_resolution_command(tmp_path: Path) -> None:
    """Suggestion for an unknown ID must contain 'charter deactivate'."""
    fake_id = "totally-fake-directive-zzz"
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {fake_id}\n",
    )
    report = run_consistency_check(ctx)

    assert any("charter deactivate" in s for s in report.suggestions), f"Expected a suggestion containing 'charter deactivate' but got: {report.suggestions}"


@pytest.mark.doctrine
def test_none_kind_skipped(tmp_path: Path) -> None:
    """When a kind has no config key (None state), it is skipped silently.

    No 'directive/' entries should appear in unknown_references when
    activated_directives is absent from config.yaml.
    """
    # Config with no activated_directives key at all.
    ctx = _ctx_with_config(tmp_path, "# no activation keys\n")
    report = run_consistency_check(ctx)

    assert not any(ref.startswith("directive/") for ref in report.unknown_references), (
        f"Expected no directive/ unknown_references but got: {report.unknown_references}"
    )


@pytest.mark.doctrine
def test_coherent_false_when_incoherent(tmp_path: Path) -> None:
    """Any planted unknown ID → coherent is False."""
    ctx = _ctx_with_config(
        tmp_path,
        "activated_directives:\n  - totally-fake-id-xyz\n",
    )
    report = run_consistency_check(ctx)

    assert report.coherent is False


@pytest.mark.doctrine
def test_run_consistency_check_returns_report_object(tmp_path: Path) -> None:
    """Return type is ConsistencyReport with correct field types."""
    ctx = _ctx_with_config(tmp_path, "# minimal valid project\n")
    report = run_consistency_check(ctx)

    assert isinstance(report, ConsistencyReport)
    assert isinstance(report.coherent, bool)
    assert isinstance(report.unknown_references, list)
    assert isinstance(report.missing_from_doctrine, list)
    assert isinstance(report.kind_violations, list)
    assert isinstance(report.suggestions, list)


@pytest.mark.doctrine
def test_no_activation_keys_skips_doctrine_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A minimal project has no IDs to validate, so it must not scan doctrine."""
    import charter.consistency_check as consistency_check

    ctx = _ctx_with_config(tmp_path, "# minimal valid project\n")

    def fail_scan(*_args: object, **_kwargs: object) -> dict[str, frozenset[str]]:
        raise AssertionError("doctrine scan should not run without activation keys")

    monkeypatch.setattr(consistency_check, "_collect_all_doctrine_ids", fail_scan)

    report = run_consistency_check(ctx)

    assert report.coherent is True
    assert report.unknown_references == []


@pytest.mark.doctrine
def test_run_consistency_check_completes_within_2s(tmp_path: Path) -> None:
    """NFR-003: consistency check against the built-in doctrine must finish < 2s."""
    ctx = _ctx_with_config(tmp_path, "# minimal valid project\n")

    start = time.perf_counter()
    run_consistency_check(ctx)
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, f"consistency check took {elapsed:.2f}s (limit: 2s)"
