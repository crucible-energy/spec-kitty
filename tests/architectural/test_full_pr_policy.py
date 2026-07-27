"""Architectural guard for the repository's full-PR-only operating policy."""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML


pytestmark = pytest.mark.architectural


_POLICY_SOURCES: dict[str, str] = {
    ".kittify/charter/charter.md": "Merge-ready full PRs only",
    "src/doctrine/directives/built-in/046-readable-consistent-prs.directive.yaml": "AUTOMATICALLY PROVEN",
    "src/doctrine/procedures/built-in/mission-wrap-up-sequence.procedure.yaml": "Open a full pull request",
    "src/doctrine/missions/mission-steps/software-dev/implement/prompt.md": "Open a full PR",
}
_DRAFT_OPENING_INSTRUCTIONS: tuple[str, ...] = (
    "open a draft pr",
    "open a draft pull request",
    "use a draft pr",
)


def _repo_root() -> Path:
    """Resolve the repository root from this checked-in architectural test."""
    return Path(__file__).resolve().parents[2]


def test_active_pr_policy_requires_full_prs_with_automated_proof() -> None:
    """Canonical policy sources must require a full PR and executable evidence."""
    root = _repo_root()
    for relative_path, expected_text in _POLICY_SOURCES.items():
        content = (root / relative_path).read_text(encoding="utf-8")
        assert expected_text in content, f"{relative_path} lost its full-PR policy"
        lowered = content.lower()
        for instruction in _DRAFT_OPENING_INSTRUCTIONS:
            assert instruction not in lowered, f"{relative_path} instructs agents to {instruction}"


def test_charter_selects_full_pr_policy_directive() -> None:
    """The runtime charter must surface the permanent full-PR rule on every action."""
    root = _repo_root()
    yaml = YAML(typ="safe")
    charter = yaml.load((root / ".kittify/charter/charter.yaml").read_text(encoding="utf-8"))

    selected = charter["governance"]["doctrine"]["selected_directives"]
    assert "DIR-015" in selected

    directives = charter["directives"]["directives"]
    full_pr_directive = next(directive for directive in directives if directive["id"] == "DIR-015")
    description = full_pr_directive["description"].lower()
    assert "must not open draft pull requests" in description
    assert "full pull request" in description
    assert "automated proof" in description
