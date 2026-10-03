"""Operator contract for pinned coordinated-history recovery (fork issue #60)."""

from __future__ import annotations

import json
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app
from specify_cli.status.models import StatusSnapshot
from specify_cli.status.reducer import materialize_to_json, reduce
from specify_cli.status.store import read_event_stream_from_text

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
SLUG = "subsequent-progress-intake-01M204R7"
MID = "01M204R7Y759H4DV93ZP8V3TM0"
TARGET = "feat/subsequent-progress-intake"
COMMAND = "restore-owned-mission-history"
MANIFEST = "history-restoration.json"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def commit(root: Path) -> str:
    git(root, "add", ".")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "fixture")
    return git(root, "rev-parse", "HEAD")


def tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts}


def encode(rows: list[dict]) -> str:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)


def history() -> list[dict]:
    rows = []
    paths = {
        "WP01": ["planned", "claimed", "in_progress", "for_review", "in_review", "approved"],
        "WP02": ["planned", "claimed", "in_progress", "for_review", "in_review"],
        "WP03": ["planned"],
    }
    for wp, lanes in paths.items():
        previous = "genesis"
        for lane in lanes:
            index = len(rows) + 1
            row = {
                "event_id": f"01M204R7Y759H4DV93ZP8V3{index:03d}",
                "mission_slug": SLUG,
                "mission_id": MID,
                "wp_id": wp,
                "from_lane": previous,
                "to_lane": lane,
                "at": f"2026-09-08T20:00:{index:02d}+00:00",
                "actor": "codex",
                "force": False,
                "execution_mode": "worktree",
                "reason": "retained history",
                "review_ref": None,
                "evidence": None,
                "policy_metadata": None,
            }
            if lane == "in_review":
                row["actor"] = {"role": "reviewer", "profile": None, "tool": "codex", "model": None}
            if lane == "approved":
                review = {"reviewer": "Samuel Goff", "verdict": "approved", "reference": "retained arbiter disposition"}
                row["review_result"] = review
                row["evidence"] = {"review": review}
            rows.append(row)
            previous = lane
    rows.append(
        {
            "event_id": "01M204R7Y759H4DV93ZP8V3999",
            "kind": "annotation",
            "wp_id": "WP01",
            "at": "2026-09-08T20:01:00+00:00",
            "actor": "codex",
            "delta": {"role": "reviewer", "model": "__resolved_model_absent__", "subtasks": {"T001": "done"}},
        }
    )
    return rows


@dataclass
class Checkouts:
    primary: Path
    owned: Path
    sibling: Path
    directory: Path
    target: str
    source: str

    def invoke(self, *extra: str, checkout: Path | None = None, sources: list[str] | None = None):
        args = [COMMAND, "--mission", SLUG, "--owned-checkout", str(checkout or self.owned), "--json"]
        for source in sources if sources is not None else [self.target, self.source]:
            args += ["--source-commit", source]
        return CliRunner().invoke(app, [*args, *extra])

    def amend_source(self, change) -> str:
        git(self.owned, "switch", "-q", "archive/history")
        change(self.directory)
        result = commit(self.owned)
        git(self.owned, "switch", "-q", TARGET)
        return result


@pytest.fixture
def checkouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Checkouts:
    primary = tmp_path / "primary"
    primary.mkdir()
    git(primary, "init", "-q", "-b", "main")
    (primary / ".kittify").mkdir()
    (primary / ".kittify/config.yaml").write_text("{}\n")
    (primary / "user.txt").write_text("initial\n")
    commit(primary)
    owned, sibling = tmp_path / "external-owned", tmp_path / "external-sibling"
    git(primary, "worktree", "add", "-qb", TARGET, str(owned))
    git(primary, "worktree", "add", "-qb", "feat/sibling", str(sibling))
    directory = owned / "kitty-specs" / SLUG
    directory.mkdir(parents=True)
    meta = {
        "mission_id": MID,
        "mission_slug": SLUG,
        "slug": SLUG,
        "mission_number": None,
        "mission_type": "software-dev",
        "topology": "coord",
        "coordination_branch": f"kitty/mission-{SLUG}",
        "target_branch": TARGET,
        "created_at": "2026-09-08T09:00:00+00:00",
        "friendly_name": "Historical intake",
    }
    (directory / "meta.json").write_text(json.dumps(meta))
    lifecycle = {
        "event_id": "01M204R7Y759H4DV93ZP8V3000",
        "event_type": "MissionCreated",
        "aggregate_id": MID,
        "aggregate_type": "Mission",
        "schema_version": "5.0.0",
        "timestamp": "2026-09-08T09:00:00+00:00",
        "payload": {"mission_id": MID, "mission_slug": SLUG},
    }
    (directory / "status.events.jsonl").write_text(encode([lifecycle]))
    (directory / "status.json").write_text(materialize_to_json(reduce([])))
    (directory / "lanes.json").write_text('{"version": 1, "planning_commit_sha": null}\n')
    target = commit(owned)
    git(owned, "switch", "-qc", "archive/history")
    rows = history()
    text = encode([lifecycle, *rows])
    (directory / "status.events.jsonl").write_text(text)
    stream = read_event_stream_from_text(directory, text)
    snapshot = reduce(stream.transitions, stream.annotations)
    snapshot.mission_type = "software-dev"
    old = snapshot.to_dict()
    for wp in old["work_packages"].values():
        wp.pop("review_result", None)  # Historical projection predates this field.
    (directory / "status.json").write_text(materialize_to_json(StatusSnapshot.from_dict(old)))
    source = commit(owned)
    git(owned, "switch", "-q", TARGET)
    (primary / "user.txt").write_text("protected dirty user work\n")
    monkeypatch.chdir(primary)
    return Checkouts(primary, owned, sibling, directory, target, source)


def test_default_preview_restores_real_history_without_effects(checkouts: Checkouts):
    before = [tree(root) for root in (checkouts.primary, checkouts.owned, checkouts.sibling)]
    result = checkouts.invoke()
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["dry_run"] is True
    assert data["lanes"] == {"WP01": "approved", "WP02": "in_review", "WP03": "planned"}
    assert data["counts"] == {"rows": 14, "transitions": 12, "annotations": 1, "non_lane": 1}
    assert data["historical_only"] is True
    assert data["sources"][1]["projection_additions"] == {"WP01": ["review_result"]}
    assert all(source["blobs"]["status.events.jsonl"]["sha256"] for source in data["sources"])
    assert before == [tree(root) for root in (checkouts.primary, checkouts.owned, checkouts.sibling)]
    assert not (checkouts.primary / ".git/spec-kitty-locks").exists()


def test_apply_preserves_records_and_is_idempotent(checkouts: Checkouts):
    primary, sibling = tree(checkouts.primary), tree(checkouts.sibling)
    lanes = (checkouts.directory / "lanes.json").read_bytes()
    result = checkouts.invoke("--apply")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["applied"] is True
    rows = [json.loads(line) for line in (checkouts.directory / "status.events.jsonl").read_text().splitlines()]
    for row in history():
        assert row in rows
    receipt = json.loads((checkouts.directory / MANIFEST).read_text())
    assert receipt["historical_only"] is True
    assert receipt["target_commit"] == checkouts.target
    assert receipt["sources"][1]["commit"] == checkouts.source
    assert (checkouts.directory / "lanes.json").read_bytes() == lanes
    after = tree(checkouts.owned)
    again = checkouts.invoke("--apply")
    assert again.exit_code == 0, again.output
    assert json.loads(again.stdout)["changed"] is False
    assert tree(checkouts.owned) == after
    commit(checkouts.owned)
    committed = checkouts.invoke("--apply")
    assert committed.exit_code == 0, committed.output
    assert json.loads(committed.stdout)["changed"] is False
    assert tree(checkouts.primary) == primary
    assert tree(checkouts.sibling) == sibling


@pytest.mark.parametrize(
    "fault",
    [
        "conflict",
        "invalid-json",
        "unknown-kind",
        "wrong-identity",
        "wrong-row-identity",
        "snapshot-lane",
        "snapshot-count",
        "snapshot-review",
        "invalid-actor",
        "duplicate-key",
    ],
)
def test_bad_pinned_source_refuses_before_effects(checkouts: Checkouts, fault: str):
    def change(directory: Path):
        path = directory / "status.events.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if fault == "conflict":
            rows.append({**rows[1], "reason": "divergent duplicate"})
        elif fault == "unknown-kind":
            rows[-1]["kind"] = "invented"
        elif fault == "wrong-row-identity":
            rows[1]["mission_id"] = "01M204R7Y759H4DV93ZP8V3TM1"
        elif fault == "invalid-actor":
            rows[1]["actor"] = {"role": "reviewer"}
        path.write_text(encode(rows))
        if fault == "invalid-json":
            path.write_text(path.read_text() + "{broken\n")
        if fault == "duplicate-key":
            path.write_text(path.read_text().replace('"to_lane": "planned"', '"to_lane": "planned", "to_lane": "approved"', 1))
        if fault == "wrong-identity":
            meta_path = directory / "meta.json"
            meta = json.loads(meta_path.read_text())
            meta["mission_id"] = "01M204R7Y759H4DV93ZP8V3TM1"
            meta_path.write_text(json.dumps(meta))
        if fault.startswith("snapshot-"):
            snapshot_path = directory / "status.json"
            snapshot = json.loads(snapshot_path.read_text())
            if fault == "snapshot-lane":
                snapshot["work_packages"]["WP02"]["lane"] = "approved"
            elif fault == "snapshot-count":
                snapshot["event_count"] += 1
            else:
                snapshot["work_packages"]["WP01"]["review_result"] = {"verdict": "rejected"}
            snapshot_path.write_text(json.dumps(snapshot))

    source = checkouts.amend_source(change)
    before = [tree(root) for root in (checkouts.primary, checkouts.owned, checkouts.sibling)]
    result = checkouts.invoke("--apply", sources=[source])
    assert result.exit_code != 0
    assert "error" in json.loads(result.stdout)
    assert before == [tree(root) for root in (checkouts.primary, checkouts.owned, checkouts.sibling)]


@pytest.mark.parametrize(
    "fault", ["nested-root", "wrong-repository", "wrong-branch", "dirty-tracked", "dirty-untracked", "symlink", "mutable-pin", "abbreviated-pin", "traversal"]
)
def test_invalid_checkout_or_selector_refuses(checkouts: Checkouts, fault: str, tmp_path: Path):
    checkout = checkouts.owned
    sources = [checkouts.source]
    if fault == "nested-root":
        checkout = checkouts.directory
    elif fault == "wrong-repository":
        checkout = tmp_path / "foreign"
        checkout.mkdir()
        git(checkout, "init", "-q")
    elif fault == "wrong-branch":
        git(checkout, "switch", "-qc", "feat/wrong")
    elif fault == "dirty-tracked":
        (checkout / "user.txt").write_text("unrelated change")
    elif fault == "dirty-untracked":
        (checkout / "unexpected.txt").write_text("valuable user work")
    elif fault == "symlink":
        meta = checkouts.directory / "meta.json"
        meta.unlink()
        meta.symlink_to(checkouts.sibling / "user.txt")
    elif fault == "mutable-pin":
        sources = ["archive/history"]
    elif fault == "abbreviated-pin":
        sources = [checkouts.source[:8]]
    before = tree(checkout)
    if fault == "traversal":
        result = CliRunner().invoke(
            app, [COMMAND, "--mission", "../escape", "--owned-checkout", str(checkout), "--source-commit", checkouts.source, "--apply", "--json"]
        )
    else:
        result = checkouts.invoke("--apply", checkout=checkout, sources=sources)
    assert result.exit_code != 0
    assert before == tree(checkout)


def test_equal_duplicate_rows_deduplicate(checkouts: Checkouts):
    def change(directory: Path):
        path = directory / "status.events.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        path.write_text(encode([*rows, rows[1]]))

    source = checkouts.amend_source(change)
    result = checkouts.invoke(sources=[source, source])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["counts"]["transitions"] == 12


@pytest.mark.parametrize("fault", ["staged", "detached", "unregistered", "ignored-output", "hidden-output", "single-branch"])
def test_additional_ownership_boundaries(checkouts: Checkouts, fault: str, tmp_path: Path):
    root = checkouts.owned
    if fault == "staged":
        (root / "user.txt").write_text("staged user work")
        git(root, "add", "user.txt")
    elif fault == "detached":
        git(root, "checkout", "--detach", "-q")
    elif fault == "unregistered":
        root = tmp_path / "unregistered-pointer"
        root.mkdir()
        (root / ".git").write_bytes((checkouts.owned / ".git").read_bytes())
    elif fault == "ignored-output":
        (root / ".gitignore").write_text(f"kitty-specs/{SLUG}/{MANIFEST}\n")
        commit(root)
        (checkouts.directory / MANIFEST).write_text('{"owner": "valuable ignored work"}')
    elif fault == "hidden-output":
        relative = f"kitty-specs/{SLUG}/status.json"
        git(root, "update-index", "--assume-unchanged", relative)
        (root / relative).write_text('{"owner": "hidden user work"}')
    else:
        path = checkouts.directory / "meta.json"
        meta = json.loads(path.read_text())
        meta["topology"] = "single_branch"
        path.write_text(json.dumps(meta))
        commit(root)
    before = tree(root)
    result = checkouts.invoke("--apply", checkout=root)
    assert result.exit_code == 1, result.output
    assert "error" in json.loads(result.stdout)
    assert tree(root) == before


def test_missing_mission_is_structured_refusal(checkouts: Checkouts):
    result = CliRunner().invoke(app, [COMMAND, "--mission", "missing", "--owned-checkout", str(checkouts.owned), "--source-commit", checkouts.source, "--json"])
    assert result.exit_code == 1
    assert "error" in json.loads(result.stdout)


def test_conflicting_valid_branch_chains_refuse(checkouts: Checkouts):
    def change(directory: Path):
        path = directory / "status.events.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[2]["from_lane"] = "for_review"
        path.write_text(encode(rows))

    source = checkouts.amend_source(change)
    result = checkouts.invoke("--apply", sources=[source])
    assert result.exit_code == 1
    assert "lane chain" in json.loads(result.stdout)["error"]


def test_install_failure_rolls_back_complete_owned_batch(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.migration import owned_history

    original_replace = owned_history.os.replace
    calls = 0

    def fail_once(source, destination):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("injected event-log replacement failure")
        original_replace(source, destination)

    monkeypatch.setattr(owned_history.os, "replace", fail_once)
    before = tree(checkouts.owned)
    result = checkouts.invoke("--apply")
    assert result.exit_code == 1, result.output
    assert "replacement failure" in json.loads(result.stdout)["error"]
    assert tree(checkouts.owned) == before


def test_revalidation_under_shared_status_lock_refuses_race(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.migration import owned_history

    @contextmanager
    def concurrent_change(*args, **kwargs):
        (checkouts.owned / "user.txt").write_text("concurrent owned edit")
        yield

    before = tree(checkouts.directory)
    monkeypatch.setattr(owned_history, "feature_status_lock", concurrent_change)
    result = checkouts.invoke("--apply")
    assert result.exit_code == 1, result.output
    assert tree(checkouts.directory) == before


@pytest.mark.parametrize("field", ["review_result", "evidence", "actor", "extension"])
def test_duplicate_conflict_compares_entire_record(checkouts: Checkouts, field: str):
    def change(directory: Path):
        path = directory / "status.events.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows.append({**rows[6], field: {"different": True}})
        path.write_text(encode(rows))

    source = checkouts.amend_source(change)
    result = checkouts.invoke(sources=[source])
    assert result.exit_code == 1
    assert "Conflicting duplicate" in json.loads(result.stdout)["error"]


def test_review_projection_survives_later_transition_and_new_verdict_replaces():
    rows = history()
    approved = next(row for row in rows if row.get("to_lane") == "approved")
    done = {**approved, "event_id": "01M204R7Y759H4DV93ZP8V3997", "at": "2026-09-08T20:03:00+00:00", "from_lane": "approved", "to_lane": "done"}
    done.pop("review_result")
    stream = read_event_stream_from_text(Path("/unused"), encode([approved, done]))
    assert reduce(stream.transitions).work_packages["WP01"]["review_result"] == approved["review_result"]
    later = {
        **approved,
        "event_id": "01M204R7Y759H4DV93ZP8V3998",
        "at": "2026-09-08T20:04:00+00:00",
        "from_lane": "done",
        "to_lane": "in_progress",
        "force": True,
        "review_result": {"reviewer": "second reviewer", "verdict": "changes_requested", "reference": "later actual review"},
    }
    stream = read_event_stream_from_text(Path("/unused"), encode([approved, done, later]))
    assert reduce(stream.transitions).work_packages["WP01"]["review_result"] == later["review_result"]


@pytest.mark.parametrize(
    "fault",
    [
        "bad-timestamp",
        "naive-timestamp",
        "missing-time",
        "bad-payload",
        "empty-id",
        "nonfinite",
        "non-object",
        "bad-topology",
        "missing-meta-field",
        "wrong-slug",
        "retrospective",
        "mixed-discriminator",
        "invalid-wp",
        "invalid-mode",
        "source-symlink",
        "missing-artifact",
        "bad-utf8",
    ],
)
def test_strict_historical_input_boundaries(checkouts: Checkouts, fault: str):
    def change(directory: Path):
        path = directory / "status.events.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if fault in ("bad-topology", "missing-meta-field", "wrong-slug"):
            meta_path = directory / "meta.json"
            meta = json.loads(meta_path.read_text())
            if fault == "bad-topology":
                meta["topology"] = "invented"
            elif fault == "missing-meta-field":
                meta.pop("mission_type")
            else:
                meta["mission_slug"] = "foreign-dossier"
            meta_path.write_text(json.dumps(meta))
            return
        if fault == "bad-timestamp":
            rows[1]["at"] = "not-a-date"
        elif fault == "naive-timestamp":
            rows[1]["at"] = "2026-09-08T20:00:01"
        elif fault == "missing-time":
            rows[1].pop("at")
        elif fault == "bad-payload":
            rows[0]["payload"] = []
        elif fault == "empty-id":
            rows[1]["event_id"] = ""
        elif fault == "retrospective":
            rows[-1]["event_name"] = "retrospective.completed"
        elif fault == "mixed-discriminator":
            rows[1]["event_type"] = "WPStatusChanged"
        elif fault == "invalid-wp":
            rows[1]["wp_id"] = "../escaped"
        elif fault == "invalid-mode":
            rows[1]["execution_mode"] = "invented"
        path.write_text(encode(rows))
        _damage_source_artifact(directory, fault)

    source = checkouts.amend_source(change)
    before = tree(checkouts.owned)
    result = checkouts.invoke("--apply", sources=[source])
    assert result.exit_code == 1, result.output
    assert "error" in json.loads(result.stdout)
    assert tree(checkouts.owned) == before


def _damage_source_artifact(directory: Path, fault: str) -> None:
    path = directory / "status.events.jsonl"
    if fault == "nonfinite":
        path.write_text(path.read_text() + '{"extension": NaN}\n')
    elif fault == "non-object":
        path.write_text(path.read_text() + "[]\n")
    elif fault == "source-symlink":
        path.unlink()
        path.symlink_to("status.json")
    elif fault == "missing-artifact":
        (directory / "status.json").unlink()
    elif fault == "bad-utf8":
        path.write_bytes(b"\xff\xfe")


def test_git_routing_override_cannot_redirect_shared_lock(checkouts: Checkouts, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GIT_DIR", str(checkouts.primary / ".git"))
    before = tree(checkouts.owned)
    result = checkouts.invoke("--apply")
    assert result.exit_code == 1
    assert "routing environment" in json.loads(result.stdout)["error"]
    assert tree(checkouts.owned) == before
