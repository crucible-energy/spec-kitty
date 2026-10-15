"""ATDD: read-only owned implementation admission through the canonical root CLI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import _get_app
from specify_cli.status import materialize
from tests.integration.test_owned_coordinated_authority import Authority, COORD, authority as authority
from tests.integration.test_restore_owned_mission_history import MID, SLUG, TARGET, commit, encode, git, tree

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
COMMAND = "preview-owned-implementation"


@dataclass
class Admission:
    authority: Authority
    slot: Path
    pin: str

    def invoke(self, *extra: str):
        return CliRunner().invoke(
            _get_app(),
            [
                "migrate",
                COMMAND,
                "--mission",
                SLUG,
                "--owned-checkout",
                str(self.authority.owned),
                "--wp-id",
                "WP03",
                "--code-checkout",
                str(self.slot),
                "--code-commit",
                self.pin,
                "--dependency-pin",
                f"WP01={self.pin}",
                "--dependency-pin",
                f"WP02={self.pin}",
                "--json",
                *extra,
            ],
        )

    def snapshot(self):
        return (
            self.authority.snapshot(),
            tree(self.slot),
            git(self.slot, "ls-files", "-v"),
            git(self.slot, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)"),
        )


@pytest.fixture
def admission(authority: Authority, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    """Real external coordination and existing code slot; dirty primary has no mission."""
    from specify_cli.migration import owned_coordination
    from specify_cli.coordination.owned_status import OwnedReviewRequest

    a = authority
    manifest = {
        "version": 1,
        "mission_slug": SLUG,
        "mission_id": MID,
        "mission_branch": COORD,
        "target_branch": TARGET,
        "computed_at": "2026-09-08T09:00:00+00:00",
        "computed_from": "dependency_graph+ownership",
        "lanes": [
            {"lane_id": "lane-a", "wp_ids": ["WP01"], "write_scope": ["WP01.txt"], "depends_on_lanes": []},
            {"lane_id": "lane-b", "wp_ids": ["WP02", "WP03"], "write_scope": ["WP02.txt", "WP03.txt"], "depends_on_lanes": ["lane-a"]},
        ],
    }
    fault = getattr(request, "param", None)
    if fault == "duplicate-wp":
        manifest["lanes"][0]["wp_ids"].append("WP03")
    elif fault == "wrong-mission":
        manifest["mission_id"] = "01M204R7Y759H4DV93ZP8V3TM1"
    elif fault == "invalid-lane":
        manifest["lanes"][0]["lane_id"] = "../escape"
    elif fault == "malformed":
        del manifest["lanes"][0]["wp_ids"]
    raw = json.dumps(manifest)
    (a.directory / "lanes.json").write_text(raw)
    a.target_pin = commit(a.owned)
    git(a.owned, "switch", "-q", "archive/coordination-pin")
    (a.directory / "lanes.json").write_text(raw)
    a.coord_pin = commit(a.owned)
    git(a.owned, "switch", "-q", TARGET)
    slot = a.primary.parent / "existing-code"
    git(a.owned, "worktree", "add", "-qb", COORD + "-lane-b", str(slot), a.target_pin)
    original = owned_coordination.git_operation
    monkeypatch.setattr(
        owned_coordination,
        "git_operation",
        lambda root, args, **kw: original(root, ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", *args], **kw),
    )
    assert a.placement("--apply").exit_code == 0
    pin = git(slot, "rev-parse", "HEAD")
    log = a.directory / "status.events.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    for wp in ("WP01", "WP02"):
        if wp == "WP01":
            historical = next(row for row in rows if row.get("wp_id") == wp and row.get("to_lane") == "approved")
            rows.append(
                {**historical, "event_id": "01M204R7Y759H4DV93ZP8V3298", "from_lane": "approved", "to_lane": "in_review", "at": "2026-09-09T00:00:00+00:00"}
            )
            approval = {**historical, "event_id": "01M204R7Y759H4DV93ZP8V3299", "at": "2026-09-09T00:00:01+00:00"}
            rows.append(approval)
        else:
            approval = {
                **next(row for row in reversed(rows) if row.get("wp_id") == wp and "to_lane" in row),
                "event_id": "01M204R7Y759H4DV93ZP8V3300",
                "from_lane": "in_review",
                "to_lane": "approved",
                "at": "2026-09-09T00:00:00+00:00",
            }
            rows.append(approval)
        request = OwnedReviewRequest(wp, "independent-current-reviewer", "approved", f"review://fixture/{wp}/{pin}", pin)
        approval.update(
            {
                "actor": request.reviewer,
                "review_ref": request.reference,
                "review_result": {"reviewer": request.reviewer, "verdict": "approved", "reference": request.reference},
                "evidence": {"review": {"reviewer": request.reviewer, "verdict": "approved", "reference": request.reference}},
                "policy_metadata": {"owned_review_request": request.key(MID), "reviewed_commit": pin, "fresh_review": True},
            }
        )
    log.write_text(encode(rows))
    materialize(a.directory)
    commit(a.owned)
    # Actual primary is intentionally missing this mission; it is never the status fallback.
    import shutil

    shutil.rmtree(a.primary / "kitty-specs")
    return Admission(a, slot, pin)


def checked(admission: Admission, result, code: str | None = None):
    assert result.exit_code == (1 if code else 0), result.output
    data = json.loads(result.stdout)
    assert data["allocated"] is False and data["runtime_advanced"] is False and data["write"] is False
    assert data["admitted"] is False
    assert data["proof_ready"] is (code is None)
    if code:
        assert data["code"] == code
    return data


def test_computed_proof_pins_real_git_facts_without_mutation(admission: Admission):
    a = admission.authority
    before = admission.snapshot()
    proof = checked(admission, admission.invoke())
    assert proof["admitted"] is False
    assert proof["proof_ready"] is True and proof["kind"] == "owned_implementation_preview"
    assert proof["wp_id"] == "WP03" and proof["lane_id"] == "lane-b"
    assert proof["roots"]["status_root"] == str(a.owned)
    assert proof["roots"]["code_root"] == str(admission.slot)
    assert proof["authority_commit"] == git(a.owned, "rev-parse", "HEAD")
    assert proof["slot"]["commit"] == admission.pin
    assert proof["slot"]["tree"] == git(a.owned, "rev-parse", admission.pin + "^{tree}")
    assert proof["common_ancestor"] == git(a.owned, "merge-base", a.target_pin, a.coord_pin)
    assert proof["planning_ancestor"] == a.coord_pin
    assert proof["counts"]["rows"] == len(git(a.owned, "show", f"{a.target_pin}:kitty-specs/{SLUG}/status.events.jsonl").splitlines())
    assert proof["counts"]["rows"] < len((a.directory / "status.events.jsonl").read_text().splitlines())
    assert set(proof["dependencies"]) == {"WP01", "WP02"}
    for wp, binding in proof["dependencies"].items():
        assert binding["commit"] == admission.pin and binding["approval_event_id"]
        assert binding["owned_blobs"][f"{wp}.txt"]["blob"] == git(a.owned, "rev-parse", f"{admission.pin}:{wp}.txt")
    assert proof["planning"]["meta.json"]["blob"] == git(a.owned, "rev-parse", f"{a.target_pin}:kitty-specs/{SLUG}/meta.json")
    assert proof["profile"] is None and proof["tool"] is None and proof["model"] is None
    assert admission.snapshot() == before


@pytest.mark.parametrize(
    "fault,code",
    [
        ("prose", "OWNED_DEPENDENCY_BINDING_MISSING"),
        ("stale", "OWNED_DEPENDENCY_BINDING_REFUSED"),
        ("wrong-wp", "OWNED_DEPENDENCY_BINDING_REFUSED"),
        ("self-review", "OWNED_DEPENDENCY_BINDING_REFUSED"),
        ("not-ready", "OWNED_DEPENDENCIES_NOT_READY"),
        ("not-planned", "OWNED_IMPLEMENTATION_LANE_REFUSED"),
    ],
)
def test_recorded_approval_is_required_and_exact(admission: Admission, fault: str, code: str):
    a = admission.authority
    log = a.directory / "status.events.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    event = next(row for row in reversed(rows) if row.get("wp_id") == "WP01" and row.get("to_lane") == "approved")
    if fault == "prose":
        event.pop("policy_metadata")
    elif fault == "stale":
        event["policy_metadata"]["reviewed_commit"] = a.coord_pin
    elif fault == "wrong-wp":
        event["policy_metadata"] = next(row["policy_metadata"] for row in rows if row.get("wp_id") == "WP02" and row.get("to_lane") == "approved")
    elif fault == "self-review":
        event["actor"] = event["review_result"]["reviewer"] = "historical-implementer"
        event["evidence"]["review"]["reviewer"] = "historical-implementer"
    elif fault == "not-ready":
        rows.remove(event)
    else:
        event = next(row for row in rows if row.get("wp_id") == "WP03" and row.get("to_lane") == "planned")
        rows.append({**event, "event_id": "01M204R7Y759H4DV93ZP8V3301", "from_lane": "planned", "to_lane": "claimed", "at": "2026-09-10T00:00:00+00:00"})
    log.write_text(encode(rows))
    materialize(a.directory)
    commit(a.owned)
    before = admission.snapshot()
    checked(admission, admission.invoke(), code)
    assert admission.snapshot() == before


@pytest.mark.parametrize("fault", ["dirty", "staged", "hidden", "symlink-file", "foreign", "wrong-head", "wrong-branch", "alias", "active", "runtime"])
def test_existing_slot_requires_exact_clean_inactive_owned_authority(admission: Admission, fault: str):
    extra = []
    slot = admission.slot
    if fault in ("dirty", "staged", "hidden"):
        if fault == "hidden":
            git(slot, "update-index", "--assume-unchanged", "WP02.txt")
        (slot / "WP02.txt").write_text("valuable local change")
        if fault == "staged":
            git(slot, "add", "WP02.txt")
    elif fault == "symlink-file":
        (slot / "WP02.txt").unlink()
        (slot / "WP02.txt").symlink_to(admission.authority.primary / "user.txt")
    elif fault == "foreign":
        extra = ["--code-checkout", str(admission.authority.sibling)]
    elif fault == "wrong-head":
        extra = ["--code-commit", admission.authority.coord_pin]
    elif fault == "wrong-branch":
        git(slot, "switch", "-qc", "unrelated-code")
    elif fault == "alias":
        alias = slot.parent / "slot-alias"
        alias.symlink_to(slot, target_is_directory=True)
        extra = ["--code-checkout", str(alias)]
    elif fault == "runtime":
        run = slot / ".kittify/runtime/runs/active"
        run.mkdir(parents=True)
        (run / "state.json").write_text('{"issued_step_id":"still-owned"}')
        (slot / ".kittify/runtime/feature-runs.json").write_text(json.dumps({MID: {"run_dir": str(run), "run_id": "active"}}))
    else:
        log = slot / "kitty-specs" / SLUG / "status.events.jsonl"
        rows = [json.loads(line) for line in log.read_text().splitlines()]
        rows[-1 if "to_lane" in rows[-1] else 0]["shell_pid"] = os.getpid()
        log.write_text(encode(rows))
        materialize(log.parent)
        admission.pin = commit(slot)
    before = admission.snapshot()
    result = admission.invoke(*extra)
    assert result.exit_code == 1, result.output
    data = json.loads(result.stdout)
    assert data["write"] is False and data["allocated"] is False and data["runtime_advanced"] is False
    assert admission.snapshot() == before


@pytest.mark.parametrize(
    "extra,code",
    [
        (["--wp-id", "WP99"], "OWNED_IMPLEMENTATION_WP_REFUSED"),
        (["--wp-id", "../WP03"], "OWNED_IMPLEMENTATION_INPUT_REFUSED"),
        (["--mission", "../escape"], "OWNED_IMPLEMENTATION_VALIDATION_REFUSED"),
        (["--code-commit", "HEAD"], "OWNED_IMPLEMENTATION_INPUT_REFUSED"),
        (["--dependency-pin", "WP01=HEAD"], "OWNED_IMPLEMENTATION_INPUT_REFUSED"),
        (["--dependency-pin", "WP99=" + "a" * 40], "OWNED_DEPENDENCY_PINS_REFUSED"),
    ],
)
def test_bad_explicit_inputs_fail_closed(admission: Admission, extra: list[str], code: str):
    before = admission.snapshot()
    checked(admission, admission.invoke(*extra), code)
    assert admission.snapshot() == before


def test_missing_dependency_proposal_never_silently_skips(admission: Admission):
    args = [
        "migrate",
        COMMAND,
        "--mission",
        SLUG,
        "--owned-checkout",
        str(admission.authority.owned),
        "--wp-id",
        "WP03",
        "--code-checkout",
        str(admission.slot),
        "--code-commit",
        admission.pin,
        "--json",
    ]
    before = admission.snapshot()
    checked(admission, CliRunner().invoke(_get_app(), args), "OWNED_DEPENDENCY_PINS_REFUSED")
    assert admission.snapshot() == before


@pytest.mark.parametrize("admission", ["duplicate-wp", "wrong-mission", "invalid-lane", "malformed"], indirect=True)
def test_declared_mapping_must_match_authority(admission: Admission):
    before = admission.snapshot()
    checked(admission, admission.invoke(), "OWNED_IMPLEMENTATION_MAPPING_REFUSED")
    assert admission.snapshot() == before


def test_final_freshness_check_observes_concurrent_branch_change(admission: Admission, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.coordination import owned_admission

    original = owned_admission.dependency_binding
    changed = False

    def bind(*args):
        nonlocal changed
        result = original(*args)
        if not changed:
            git(admission.slot, "switch", "-qc", "concurrent-code-owner")
            changed = True
        return result

    monkeypatch.setattr(owned_admission, "dependency_binding", bind)
    result = admission.invoke()
    assert changed and result.exit_code == 1, result.output
    data = json.loads(result.stdout)
    assert data["admitted"] is False and data["proof_ready"] is False
    assert data["code"] == "OWNED_IMPLEMENTATION_SLOT_REFUSED"
    assert git(admission.slot, "branch", "--show-current") == "concurrent-code-owner"


@pytest.mark.parametrize("fault", ["planning-drift", "blob-not-commit"])
def test_requested_code_pin_preserves_original_planning(admission: Admission, fault: str):
    if fault == "planning-drift":
        (admission.slot / "kitty-specs" / SLUG / "plan.md").write_text("different plan")
        admission.pin = commit(admission.slot)
        code = "OWNED_IMPLEMENTATION_PLANNING_REFUSED"
    else:
        admission.pin = git(admission.slot, "rev-parse", "HEAD:WP02.txt")
        code = "OWNED_IMPLEMENTATION_PIN_REFUSED"
    before = admission.snapshot()
    checked(admission, admission.invoke(), code)
    assert admission.snapshot() == before
