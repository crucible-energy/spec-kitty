"""Read-only context rendering against tracked retained-consumer policy.

A fresh synthetic repository tracks both the legacy project directive and
charter YAML without a local exclude mask. This preserves the original LM-1
non-vacuity guard while separating the Python consumer contract from migrations
of this repository's own current-release governance runtime. Rendering once and
then again must leave every tracked byte unchanged and exercise bootstrap then
compact mode.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from charter.context import build_charter_context

# Real subprocess git clones/checkouts against a throwaway temp repo: not a
# pure-logic test, and structurally incompatible with mutmut's forked sandbox.
pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]

_MISSION_TYPE = "software-dev"


def _run_git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def _create_doctrine_tracked_repo(dest: Path) -> Path:
    """Independent retained-layout consumer, without the maintainer's policy.

    The maintainer uses the current governance runtime; this test protects
    the retained Python consumer. Its tracked policy cannot depend on that
    separate runtime's migrations or inherit a local exclude mask.
    """
    dest.mkdir()
    kittify = dest / ".kittify"
    charter = kittify / "charter"
    charter.mkdir(parents=True)
    (kittify / "config.yaml").write_text("activated_directives: [039-lynn-cole-engineering-culture]\n", encoding="utf-8")
    (charter / "charter.md").write_text("# Consumer charter\nPreserve tracked policy on every read.\n", encoding="utf-8")
    (charter / "charter.yaml").write_text(json.dumps({"catalog": {"references": []}}), encoding="utf-8")
    directive = kittify / "doctrine" / "directive" / "tracked-policy.directive.yaml"
    directive.parent.mkdir(parents=True)
    directive.write_text(
        "schema_version: '1.0'\nid: TRACKED_POLICY\ntitle: Tracked policy\nintent: Preserve source policy.\nenforcement: required\n",
        encoding="utf-8",
    )
    _run_git(["init", "--quiet"], cwd=dest)
    _run_git(["config", "user.name", "Synthetic consumer"], cwd=dest)
    _run_git(["config", "user.email", "consumer@example.invalid"], cwd=dest)
    _run_git(["add", ".kittify"], cwd=dest)
    _run_git(["commit", "--quiet", "-m", "Synthetic tracked consumer policy"], cwd=dest)
    return dest


def _assert_doctrine_is_git_tracked(repo: Path) -> None:
    """Fail loudly if the fixture is vacuous instead of proving nothing.

    Reviewer guidance for this WP is explicit: a green cleanliness assertion
    against a fixture that doesn't actually track doctrine is a false pass.
    """
    tracked_doctrine = _run_git(["ls-files", ".kittify/doctrine"], cwd=repo).stdout.strip().splitlines()
    assert tracked_doctrine, (
        "Fixture is vacuous: .kittify/doctrine/** is not git-tracked in the "
        "cloned repo. LM-1 requires a doctrine-tracked fixture for this guard "
        "to mean anything."
    )
    tracked_charter_yaml = _run_git(["ls-files", ".kittify/charter/charter.yaml"], cwd=repo).stdout.strip()
    assert tracked_charter_yaml, "Fixture is vacuous: .kittify/charter/charter.yaml is not git-tracked."

    exclude_path = repo / ".git" / "info" / "exclude"
    exclude_text = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    assert ".kittify/doctrine" not in exclude_text, (
        "Fixture leaked the LM-1 local exclude mask into the clone; the "
        "cleanliness assertion below would be vacuous."
    )


def _tracked_status_lines(repo: Path) -> list[str]:
    """``git status --porcelain`` lines for tracked content only.

    Untracked (``??``) entries are excluded on purpose: G1/G3 explicitly
    permit the gitignored runtime file ``.kittify/charter/context-state.json``
    to appear untracked after a render. Only modified/added/deleted entries
    against already-tracked content indicate a real regression.
    """
    status = _run_git(["status", "--porcelain"], cwd=repo).stdout.splitlines()
    return [line for line in status if line and not line.startswith("??")]


@pytest.fixture
def doctrine_tracked_repo(tmp_path: Path) -> Path:
    """An independently authored, doctrine-tracked consumer, initially clean."""
    repo = _create_doctrine_tracked_repo(tmp_path / "doctrine-tracked-repo")
    _assert_doctrine_is_git_tracked(repo)
    assert _tracked_status_lines(repo) == [], "fixture must start from a clean tracked tree"
    return repo


class TestRenderPathNoOpStability:
    """build_charter_context must not write any git-tracked artifact."""

    def test_fixture_doctrine_is_git_tracked_not_masked(self, doctrine_tracked_repo: Path) -> None:
        """Explicit LM-1 guard: this fixture is doctrine-tracked, not masked.

        Belt-and-braces companion to the fixture's own internal assertion —
        pins the precondition as a first-class, independently readable test
        so a reviewer (or future refactor) sees it fail on its own if the
        fixture ever regresses back to the masked checkout.
        """
        _assert_doctrine_is_git_tracked(doctrine_tracked_repo)

    def test_g1_single_render_produces_no_tracked_diff(self, doctrine_tracked_repo: Path) -> None:
        """G1: clean tree, fresh DRG -> render leaves 0 tracked-file diffs."""
        result = build_charter_context(
            doctrine_tracked_repo,
            action="implement",
            mission_type=_MISSION_TYPE,
        )

        assert result.mode == "bootstrap"
        assert _tracked_status_lines(doctrine_tracked_repo) == []

    def test_g3_second_render_also_produces_no_tracked_diff(self, doctrine_tracked_repo: Path) -> None:
        """G3: any governed op run twice -> the 2nd run is also 0 tracked-file diffs."""
        first = build_charter_context(
            doctrine_tracked_repo,
            action="implement",
            mission_type=_MISSION_TYPE,
        )
        assert _tracked_status_lines(doctrine_tracked_repo) == [], "1st render already left tracked churn"

        second = build_charter_context(
            doctrine_tracked_repo,
            action="implement",
            mission_type=_MISSION_TYPE,
        )

        # Second load transitions bootstrap -> compact (state-driven depth);
        # confirms the render actually re-executed the real path rather than
        # short-circuiting before it could write anything.
        assert first.first_load is True
        assert second.first_load is False
        assert _tracked_status_lines(doctrine_tracked_repo) == []
