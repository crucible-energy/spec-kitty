"""Architectural parity test for the basetemp retention rationale."""

from __future__ import annotations

import re
import ast
from pathlib import Path
from typing import NamedTuple

import pytest

# This guard reads a repo documentation page, so a docs-only PR must select it.
pytestmark = [pytest.mark.architectural, pytest.mark.docs_scoped]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOC_PATH = _REPO_ROOT / "docs/development/testing/testing-parallel.md"
_SUPPORT_PATH = _REPO_ROOT / "tests/_support/run_basetemp.py"

_DOC_RETENTION_BULLET = re.compile(
    r"^- Retention requires owner/runtime release: (?P<body>.*?)^## ",
    re.MULTILINE | re.DOTALL,
)
_SUPPORT_RETENTION_BULLET = re.compile(
    r"^\* \*\*Retained until owner/runtime release\*\* — (?P<body>.*?)^\* \*\*",
    re.MULTILINE | re.DOTALL,
)

_RETENTION_CONTRACT_CLAUSES = (
    "ExitCode.OK",
    "does not release",
    "failures, errors, or an interruption",
    "retains",
    "owner/runtime release",
)


class _RetentionTexts(NamedTuple):
    doc_body: str
    support_body: str
    support_source: str


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_body(pattern: re.Pattern[str], text: str, source: Path) -> str:
    match = pattern.search(text)
    assert match is not None, f"expected the retention bullet to remain in {source}"
    return _normalize(match.group("body"))


def _missing_clauses(body: str) -> list[str]:
    return [clause for clause in _RETENTION_CONTRACT_CLAUSES if clause not in body]


def _retention_texts() -> _RetentionTexts:
    doc_source = _DOC_PATH.read_text(encoding="utf-8")
    support_source = _SUPPORT_PATH.read_text(encoding="utf-8")
    return _RetentionTexts(
        doc_body=_extract_body(_DOC_RETENTION_BULLET, doc_source, _DOC_PATH),
        support_body=_extract_body(_SUPPORT_RETENTION_BULLET, support_source, _SUPPORT_PATH),
        support_source=support_source,
    )


def test_retention_rationale_matches_support_contract() -> None:
    texts = _retention_texts()
    for source, body in (
        (_DOC_PATH, texts.doc_body),
        (_SUPPORT_PATH, texts.support_body),
    ):
        missing = _missing_clauses(body)
        assert missing == [], f"{source} retention rationale is missing: {missing}"


def test_startup_never_sweeps_unreleased_sibling_runs() -> None:
    doc_source = _normalize(_DOC_PATH.read_text(encoding="utf-8"))
    assert "never performs a sibling age sweep" in doc_source
    assert "`STALE_RUN_MAX_AGE_S` is observational only" in doc_source
    module = ast.parse(_SUPPORT_PATH.read_text(encoding="utf-8"))
    startup = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "install_run_basetemp")
    calls = {node.func.id for node in ast.walk(startup) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "remove_run_dirs" not in calls
    assert "stale_run_dirs" not in calls
    callback = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "_record_session_outcome")
    assert not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"rmtree", "unlink", "rmdir"} for node in ast.walk(callback)
    ), "test outcome cannot authorize deletion of a runtime-held leaf"


def test_retention_guard_detects_reap_drift() -> None:
    support_body = _retention_texts().support_body
    drifted_body = support_body.replace("does not release", "releases", 1)
    assert drifted_body != support_body, "mutation did not change the support rationale"
    assert _missing_clauses(drifted_body) == ["does not release"]
