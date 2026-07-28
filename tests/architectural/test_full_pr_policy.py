"""Architectural guard for the repository's full-PR-only operating policy."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from ruamel.yaml import YAML


pytestmark = pytest.mark.architectural


_POLICY_SOURCES: dict[str, str] = {
    ".kittify/charter/charter.md": "Merge-ready full PRs only",
    "AGENTS.md": "merge-ready full PRs only",
    "docs/development/onboarding-run.md": "Open a full PR only",
    "src/doctrine/directives/built-in/046-readable-consistent-prs.directive.yaml": "AUTOMATICALLY PROVEN",
    "src/doctrine/procedures/built-in/mission-wrap-up-sequence.procedure.yaml": "Open a full pull request",
    "src/doctrine/missions/mission-steps/software-dev/implement/prompt.md": "Open a full PR",
}

# The guard must reject any *affirmative instruction* to open a draft PR, not
# just a fixed phrase, so an active source cannot regress to an equivalent
# wording ("create a draft PR", "submit a draft pull request", `gh pr create
# --draft`, ...) while staying green. Each instruction pattern targets an
# imperative "<verb> a draft <pr>" construction (or the `--draft` CLI flag).
# Requiring a leading verb + article + singular object keeps these from matching
# the canonical *prohibitions* that must stay in the sources: "never open draft
# pull requests" / "MUST NOT open draft pull requests" (plural, no article),
# "Draft pull requests are prohibited" (no leading verb), "(never draft)",
# "non-draft PR only", and the "Draft-pull-request ... handoff" anti-pattern
# whose body names the prohibited practice with a gerund ("using" is not a
# matched verb stem).
_DRAFT_PR_OBJECT = r"draft (?:pull[ -]request|pr)s?"
_DRAFT_PR_INSTRUCTION_VERBS = "open|create|submit|make|raise|file|start|prepare|use|push|send|publish"
_DRAFT_PR_INSTRUCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf"\b(?:{_DRAFT_PR_INSTRUCTION_VERBS})s?\s+(?:a|an|the)\s+{_DRAFT_PR_OBJECT}\b"),
)
_DRAFT_FLAG_PATTERN = re.compile(r"--draft\b")
# Negation is evaluated per ``--draft`` occurrence, scoped to the clause that
# contains it (bounded by the nearest sentence break on either side). A cue on
# either side of the flag within that clause ("never run `gh pr create --draft`",
# "the `--draft` flag is prohibited") makes that occurrence a prohibition. Scoping
# per occurrence keeps an unrelated prohibition elsewhere in the source from
# masking a later affirmative ``gh pr create --draft``.
_DRAFT_FLAG_NEGATION_CUE = re.compile(
    r"\b(?:never|not|no|don't|do not|does not|doesn't|must not|mustn't|cannot|can't|"
    r"avoid|without|prohibit(?:ed|s)?|forbid(?:den|s)?|reject|refuse)\b"
)
_CLAUSE_BREAK_CHARS = ".;\n!?"


def _draft_flag_occurrence_negated(lowered: str, flag_start: int, flag_end: int) -> bool:
    """True when the ``--draft`` at ``flag_start`` sits in a clause carrying a negation cue."""
    left = max(lowered.rfind(char, 0, flag_start) for char in _CLAUSE_BREAK_CHARS)
    rights = [pos for char in _CLAUSE_BREAK_CHARS if (pos := lowered.find(char, flag_end)) != -1]
    right = min(rights) if rights else len(lowered)
    clause = lowered[left + 1 : right]
    return _DRAFT_FLAG_NEGATION_CUE.search(clause) is not None


def _contains_draft_pr_instruction(text: str) -> bool:
    """Return True when the text instructs an agent to open a draft pull request."""
    lowered = text.lower()
    if any(pattern.search(lowered) for pattern in _DRAFT_PR_INSTRUCTION_PATTERNS):
        return True
    return any(
        not _draft_flag_occurrence_negated(lowered, match.start(), match.end())
        for match in _DRAFT_FLAG_PATTERN.finditer(lowered)
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
        assert not _contains_draft_pr_instruction(
            content
        ), f"{relative_path} instructs agents to open a draft pull request"


_EQUIVALENT_DRAFT_INSTRUCTIONS: tuple[str, ...] = (
    "Open a draft PR to solicit review.",
    "Create a draft PR for early feedback.",
    "Submit a draft pull request before finishing.",
    "Please make a draft PR now.",
    "File a draft pull request first.",
    "Use a draft PR while iterating.",
    "Run `gh pr create --draft` to share progress.",
)


@pytest.mark.parametrize("instruction", _EQUIVALENT_DRAFT_INSTRUCTIONS)
def test_guard_rejects_equivalent_draft_instructions(instruction: str) -> None:
    """Equivalent draft-PR instructions must trip the guard, not just fixed phrases."""
    assert _contains_draft_pr_instruction(
        instruction
    ), f"guard failed to reject equivalent draft-PR instruction: {instruction!r}"


_CANONICAL_PROHIBITIONS: tuple[str, ...] = (
    "Agents never open draft pull requests.",
    "Agents MUST NOT open draft pull requests.",
    "Draft pull requests are prohibited.",
    "The PR is full (never draft), opened only for the complete validated slice.",
    "Full, non-draft PR only.",
    "Never run gh pr create --draft.",
    "The `--draft` flag is prohibited; always open a full PR.",
    "Open a full PR from the mission branch (`gh pr create`; never `--draft`).",
    "Using a draft pull request, opening a PR merely because a change exists, is an anti-pattern.",
)


@pytest.mark.parametrize("prohibition", _CANONICAL_PROHIBITIONS)
def test_guard_allows_canonical_prohibitions(prohibition: str) -> None:
    """The canonical prohibitions that must stay in the sources are not false positives."""
    assert not _contains_draft_pr_instruction(
        prohibition
    ), f"guard falsely flagged a canonical prohibition: {prohibition!r}"


def test_guard_flags_affirmative_draft_flag_despite_earlier_prohibition() -> None:
    """A prohibition clause must not mask a separate affirmative ``--draft`` occurrence."""
    text = (
        "Open a full PR from the mission branch; never `--draft`.\n"
        "Run `gh pr create --draft` to share progress early.\n"
    )
    assert _contains_draft_pr_instruction(
        text
    ), "guard let an affirmative --draft slip because an unrelated prohibition negated the file"


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


def test_wrap_up_sequence_validates_the_final_aggregate_before_handoff() -> None:
    """Workflow evidence, acceptance, and aggregate proof must have a viable order."""
    root = _repo_root()
    yaml = YAML(typ="safe")
    procedure = yaml.load(
        (
            root
            / "src/doctrine/procedures/built-in/mission-wrap-up-sequence.procedure.yaml"
        ).read_text(encoding="utf-8")
    )
    titles = [step["title"] for step in procedure["steps"]]

    merge_index = titles.index("Merge the lanes locally")
    rebase_index = titles.index("Rebase onto the current upstream base")
    aggregate_index = titles.index(
        "Establish automated proof on the consolidated, rebased aggregate before landing"
    )
    pr_index = titles.index("Open a full pull request and complete remote automation")
    acceptance_index = titles.index("Record final acceptance before opening the full pull request")
    hosted_evidence_index = titles.index("Verify hosted workflow evidence before handoff")
    catalog = yaml.load((root / ".kittify/charter/charter.yaml").read_text(encoding="utf-8"))
    procedure = next(
        entry
        for entry in catalog["catalog"]["references"]
        if entry["id"] == "PROCEDURE:mission-wrap-up-sequence"
    )

    assert merge_index < rebase_index < aggregate_index < acceptance_index < pr_index < hosted_evidence_index
    assert procedure["summary"].index("lands the lanes locally") < procedure["summary"].index(
        "establishes aggregate automated proof"
    )
    charter_text = (root / ".kittify/charter/charter.md").read_text(encoding="utf-8")
    assert charter_text.index("local merge") < charter_text.index("establish aggregate automated proof")
