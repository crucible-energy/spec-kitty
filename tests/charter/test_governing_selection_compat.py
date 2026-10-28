"""Preserve authored selections when the workspace governor renames its key.

Source3 keeps its public doctrine field and emitted format. The current governor
writes charter; silently accepting that input as an empty selection drops policy.
"""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from charter.schemas import GovernanceConfig

pytestmark = pytest.mark.fast

_SELECTION = {
    "selected_directives": ["DIR-014", "DIR-015"],
    "selected_paradigms": ["test-first"],
    "selected_tactics": ["testing/example"],
    "selected_procedures": ["review-closeout"],
    "selected_agent_profiles": ["reviewer"],
    "available_tools": ["git"],
    "template_set": "project",
    "authority_paths": ["docs/authority"],
    "governance_references": ["docs/policy.md"],
}


@pytest.mark.parametrize("key", ["doctrine", "charter"])
def test_governing_selection_preserves_all_authored_values(key: str) -> None:
    raw = {key: deepcopy(_SELECTION), "enforcement": {"review": "required"}}
    before = deepcopy(raw)
    config = GovernanceConfig.model_validate(raw)

    for field, expected in _SELECTION.items():
        assert getattr(config.doctrine, field) == expected
    assert config.enforcement == {"review": "required"}
    assert raw == before
    emitted = config.model_dump()
    assert "charter" not in emitted
    assert emitted["doctrine"]["selected_directives"] == ["DIR-014", "DIR-015"]
    assert GovernanceConfig.model_validate(emitted) == config


def test_equal_dual_selections_do_not_drop_policy() -> None:
    config = GovernanceConfig.model_validate(
        {"doctrine": deepcopy(_SELECTION), "charter": deepcopy(_SELECTION)}
    )
    assert config.doctrine.selected_directives == ["DIR-014", "DIR-015"]


@pytest.mark.parametrize("legacy", [{}, {"selected_directives": ["DIR-002"]}, None])
def test_conflicting_dual_selections_fail_closed(legacy: object) -> None:
    with pytest.raises(ValidationError, match="Conflicting governance selection"):
        GovernanceConfig.model_validate({"doctrine": legacy, "charter": _SELECTION})


@pytest.mark.parametrize("value", [None, [], "DIR-014", 14])
def test_malformed_governing_selection_is_not_silently_ignored(value: object) -> None:
    with pytest.raises(ValidationError):
        GovernanceConfig.model_validate({"charter": value})
