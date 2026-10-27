"""Original creator custody through actual private foreground producers.

Release queues a hint only; these tests do not supply accepted delivery or
permission to retire a real workspace. No mocked producer establishes a join.
"""

from __future__ import annotations

import copy
import gc
import json
import pickle
import sys
from pathlib import Path
from typing import Any

import pytest

from specify_cli.workspace_lifecycle.adapters import GitHubDelivery
from specify_cli.workspace_lifecycle.state import StateError
from tests.workspace_lifecycle.test_adapters import git, managed_owner


def new_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any, list[Any], Any]:
    from specify_cli.workspace_lifecycle.original_run import OriginalWorkspaceRun

    other_owner, store, events, repo = managed_owner(tmp_path, monkeypatch, runtime="actual")
    run = OriginalWorkspaceRun.create(
        store,
        repo_root=repo,
        path=tmp_path / "ordinary",
        branch="ordinary",
        repository="crucible-energy/example",
        repository_id=7,
        delivery=GitHubDelivery(timeout=1),
        on_complete=events.append,
        expected_base_commit=git(repo, "rev-parse", "HEAD"),
        accountable_owner="fixture:original-run",
    )
    return run, store, events, other_owner


def ordinary_record(store: Any) -> dict[str, Any]:
    records = [json.loads(path.read_bytes()) for path in store.root.glob("creator-*.json")]
    ordinary = [record for record in records if record.get("creator_kind") == "ordinary_git"]
    assert len(ordinary) == 1
    return ordinary[0]


def test_original_run_retains_exact_creator_across_real_commit_and_join(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run, store, events, _ = new_run(tmp_path, monkeypatch)
    before = ordinary_record(store)
    gc.collect()
    script = (
        "from pathlib import Path; import subprocess; Path('result.md').write_text('actual producer'); "
        "subprocess.run(['git','add','result.md'],check=True); "
        "subprocess.run(['git','commit','-m','result'],check=True)"
    )
    run.run_producer([sys.executable, "-c", script], timeout=5)
    joined = ordinary_record(store)
    assert joined["identity"]["head"] != before["identity"]["head"]
    assert joined["identity"]["lease_generation"] != before["identity"]["lease_generation"]
    assert joined["identity"]["workspace_generation"] == before["identity"]["workspace_generation"]
    gc.collect()
    run.complete(pr=9)
    assert ordinary_record(store)["status"] == "released"
    assert len(events) == 1
    assert (tmp_path / "ordinary" / "result.md").read_text() == "actual producer"
    with pytest.raises(StateError):
        run.complete(pr=9)
    assert len(events) == 1


def test_original_run_cannot_release_from_labels_or_another_creator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run, store, events, other = new_run(tmp_path, monkeypatch)
    before = ordinary_record(store)
    with pytest.raises(StateError):
        run.complete(pr=9)
    with pytest.raises(StateError):
        run.require_joined_for(other)
    assert ordinary_record(store) == before
    assert not events


@pytest.mark.parametrize("clone", [copy.copy, copy.deepcopy, pickle.dumps])
def test_original_run_cannot_copy_or_serialize_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clone: Any) -> None:
    run, store, events, _ = new_run(tmp_path, monkeypatch)
    before = ordinary_record(store)
    with pytest.raises(TypeError):
        clone(run)
    assert ordinary_record(store) == before
    assert not events


def test_original_run_failed_real_producer_cannot_retry_or_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run, store, events, _ = new_run(tmp_path, monkeypatch)
    with pytest.raises(StateError):
        run.run_producer([sys.executable, "-c", "raise SystemExit(2)"], timeout=5)
    before = ordinary_record(store)
    assert before["status"] == "producer_unknown"
    with pytest.raises(StateError):
        run.run_producer([sys.executable, "-c", "pass"], timeout=5)
    with pytest.raises(StateError):
        run.complete(pr=9)
    assert ordinary_record(store) == before
    assert not events


def test_original_run_constructor_is_not_a_recovery_or_adoption_api() -> None:
    from specify_cli.workspace_lifecycle.original_run import OriginalWorkspaceRun

    with pytest.raises(TypeError):
        OriginalWorkspaceRun()
