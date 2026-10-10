"""Strict, bounded evidence for explicit owned single-branch recovery (#85).

This proves absence of committed post-base source work and archival preservation;
it deliberately does not implement or weaken whole-branch absorption.
"""

from __future__ import annotations

import os
import json
import re
import stat
from pathlib import Path
from typing import Annotated, Literal

import psutil
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from kernel.git import blob_at, run_git
from kernel.git.worktree_registry import parse_worktree_records
from kernel.content_digest import sha256_digest
from kernel.no_follow import fd_relative_dir_ops_supported
from mission_runtime import OwnedCheckout
from specify_cli.status import read_events_from_text
from specify_cli.lanes.models import LanesManifest
from specify_cli.lanes.branch_naming import parse_mission_slug_from_branch

__all__ = ["RecoveryError", "RecoveryEvidence", "digest", "load_proof", "read_closed_object", "read_regular", "verify_history"]

Sha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]


class RecoveryError(ValueError):
    """Evidence cannot establish safe explicit recovery."""


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class HistoricalRef(_ClosedModel):
    ref: str
    sha: Sha


class ArchivedStatus(_ClosedModel):
    ref: str
    path: str


class _PinnedProof(_ClosedModel):
    owner_head: Sha
    planning_commit_sha: Sha
    historical_base: Sha
    historical_refs: Annotated[list[HistoricalRef], Field(min_length=1, max_length=16)]
    archived_status: ArchivedStatus
    claim_refs: dict[str, Sha]


class RecoveryProof(_PinnedProof):
    """Original strict zero-source-work contract."""

    schema_version: Literal[1]


class _CustodyReference(_ClosedModel):
    path: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class CustodyRecoveryProof(_PinnedProof):
    schema_version: Literal[2]
    source_disposition: Literal["preserved_unapplied"]
    custody: _CustodyReference


RecoveryEvidence = RecoveryProof | CustodyRecoveryProof


def read_closed_object(content: bytes) -> dict[str, object]:
    """Reject duplicate keys at every depth before closed typed validation.

    The repository's metadata JSON reader permits duplicates, and its legacy
    detector checks only top-level metadata. Neither qualifies this proof seam.
    Validation failures are sanitized here before they can carry input values.
    """

    def pairs(rows: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in rows:
            if key in result:
                raise RecoveryError("Duplicate proof key")
            result[key] = value
        return result

    def nonfinite(_value: str) -> object:
        raise RecoveryError("Nonfinite proof number")

    try:
        data = json.loads(content, object_pairs_hook=pairs, parse_constant=nonfinite)
        if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
            raise RecoveryError("Invalid proof object")
        return data
    except (ValueError, ValidationError, UnicodeDecodeError, RecursionError):
        raise RecoveryError("Invalid closed recovery proof") from None


def load_proof(content: bytes) -> RecoveryEvidence:
    try:
        data = read_closed_object(content)
        if data["schema_version"] == 1:
            return RecoveryProof.model_validate(data)
        return CustodyRecoveryProof.model_validate(data)
    except (ValueError, ValidationError):
        raise RecoveryError("Invalid closed recovery proof") from None


def digest(data: bytes) -> str:
    """Return a content identity, never a substitute for ownership admission."""
    return sha256_digest(data)


def read_regular(path: Path, *, limit: int = 8_388_608, executable: bool | None = None) -> bytes:
    """Read bounded regular bytes through held, non-following directory descriptors.

    Platforms lacking descriptor-relative no-follow reads refuse. Caller-approved
    external proof files are supported; project evidence containment is separate.
    """
    path = path.absolute()
    if not fd_relative_dir_ops_supported() or ".." in path.parts:
        raise RecoveryError("Descriptor-safe evidence reads unavailable or path is ambiguous")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, "rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise RecoveryError("Evidence must be a bounded regular file")
            if executable is not None and bool(before.st_mode & stat.S_IXUSR) != executable:
                raise RecoveryError("Current source mode differs from the pinned tree")
            content = handle.read(limit + 1)
            after = os.fstat(handle.fileno())
            named = os.stat(path.name, dir_fd=directory, follow_symlinks=False)

            def identity(info: os.stat_result) -> tuple[int, ...]:
                return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

            if len(content) > limit or identity(before) != identity(after) or identity(after) != identity(named):
                raise RecoveryError("Evidence changed during read")
            return content
    finally:
        os.close(directory)


def _text(owned: OwnedCheckout, *args: str) -> str:
    return run_git(owned.owned_root, *args, timeout=15).stdout.decode("utf-8").strip()


def _blob(owned: OwnedCheckout, tip: str, path: str) -> bytes:
    content = blob_at(owned.owned_root, tip, path, timeout=15, max_bytes=8_388_608)
    if content is None:
        raise RecoveryError("Required historical immutable blob is absent")
    return content


def _mission_ref(ref: str, branch: str) -> bool:
    if ref.startswith("refs/heads/"):
        name = ref.removeprefix("refs/heads/")
    elif ref.startswith("refs/remotes/"):
        parts = ref.removeprefix("refs/remotes/").split("/", 1)
        name = parts[1] if len(parts) == 2 else ""
    elif ref.startswith("refs/spec-kitty/lane-tip/"):
        name = ref.removeprefix("refs/spec-kitty/lane-tip/")
    else:
        return False
    expected = parse_mission_slug_from_branch(branch)
    parsed = parse_mission_slug_from_branch(name)
    return expected is not None and expected.lane_id is None and parsed is not None and parsed.slug == expected.slug and parsed.mid8_token == expected.mid8_token


def _verify_processes(owned: OwnedCheckout, content: bytes) -> None:
    events = read_events_from_text(owned.mission_dir, content.decode("utf-8"))
    for event in events:
        pid = event.policy_metadata.get("shell_pid") if event.policy_metadata else None
        if pid is not None:
            if type(pid) is not int or pid <= 0:
                raise RecoveryError("Historical process identity is invalid")
            # A reused live PID is ambiguous too; do not classify it as inactive.
            if psutil.pid_exists(pid):
                raise RecoveryError(f"Historical process {pid} is active or ambiguous")


def _historical_refs(owned: OwnedCheckout, proof: RecoveryEvidence, branch: str) -> dict[str, str]:
    """Ref census is complete, so omissions never read as absent work."""
    if not branch:
        raise RecoveryError("Historical branch is required")
    supplied = {row.ref: row.sha for row in proof.historical_refs}
    if len(supplied) != len(proof.historical_refs) or any(not _mission_ref(ref, branch) for ref in supplied):
        raise RecoveryError("Historical refs are duplicated or outside this mission")
    actual: dict[str, str] = {}
    rows = _text(owned, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/remotes", "refs/spec-kitty/lane-tip")
    for row in rows.splitlines():
        ref, sha = row.split(" ", 1)
        if _mission_ref(ref, branch):
            actual[ref] = sha
    if actual != supplied:
        raise RecoveryError("Historical refs are missing, changed, or unknown")
    return actual


def _verify_workspaces(owned: OwnedCheckout, branch: str, tips: set[str]) -> None:
    # The caller owns the bounded read-only probe; kernel.git owns byte/path parsing.
    inventory = run_git(owned.owned_root, "worktree", "list", "--porcelain", "-z", timeout=15).stdout
    for record in parse_worktree_records(inventory, max_records=512):
        if record.branch and _mission_ref(record.branch, branch):
            raise RecoveryError("Historical branch still has a registered workspace")
        if not record.detached:
            continue
        if record.head is None:
            raise RecoveryError("Detached workspace HEAD is unknown")
        for tip in tips:
            relation = run_git(owned.owned_root, "merge-base", "--is-ancestor", tip, record.head, check=False, timeout=15)
            if relation.returncode == 0:
                raise RecoveryError("Detached historical workspace remains registered")
            if relation.returncode != 1:
                raise RecoveryError("Detached workspace ancestry is unknown")


def verify_history(owned: OwnedCheckout, proof: RecoveryEvidence, branch: str, scope: list[str]) -> dict[str, str]:
    """Verify complete refs, zero source commits, archives and inactive workspaces."""
    if not scope:
        raise RecoveryError("Production scope is required")
    actual = _historical_refs(owned, proof, branch)
    archive = proof.archived_status
    if archive.ref not in actual or not re.fullmatch(r"[A-Za-z0-9_./-]+", archive.path):
        raise RecoveryError("Archive selection is invalid")
    dossier = owned.mission_dir.relative_to(owned.owned_root).as_posix()
    historical_lanes = LanesManifest.from_dict(json.loads(_blob(owned, actual[archive.ref], dossier + "/lanes.json")))
    current_lanes = LanesManifest.from_dict(json.loads(read_regular(owned.mission_dir / "lanes.json")))
    if historical_lanes.mission_id != current_lanes.mission_id or {wp for lane in historical_lanes.lanes for wp in lane.wp_ids} != {
        wp for lane in current_lanes.lanes for wp in lane.wp_ids
    }:
        raise RecoveryError("Historical manifest identity or membership differs")
    scope = sorted(set(scope) | {path for lane in historical_lanes.lanes for path in lane.write_scope})
    if any(Path(path).is_absolute() or ".." in Path(path).parts or path.startswith(":") for path in scope):
        raise RecoveryError("Historical production scope is ambiguous")
    _text(owned, "rev-parse", "--verify", proof.historical_base + "^{commit}")
    source_custody: dict[str, str] = {}
    if isinstance(proof, CustodyRecoveryProof):
        from specify_cli.migration.owned_source_custody import verify_source_custody

        source_custody = verify_source_custody(owned, proof, actual, scope, current_lanes.mission_id)
    else:
        for ref, tip in actual.items():
            run_git(owned.owned_root, "merge-base", "--is-ancestor", proof.historical_base, tip, timeout=15)
            run_git(owned.owned_root, "diff", "--quiet", proof.historical_base, tip, "--", *scope, timeout=15)
            if _text(owned, "log", "--full-history", "--max-count=1", "--format=%H", proof.historical_base + ".." + tip, "--", *scope):
                raise RecoveryError(f"Historical ref {ref} contains post-base source commits")
    _verify_workspaces(owned, branch, set(actual.values()))
    relative = Path(archive.path)
    if relative.is_absolute() or ".." in relative.parts:
        raise RecoveryError("Archive must stay inside the owned mission")
    source = owned.mission_dir.relative_to(owned.owned_root).as_posix() + "/status.events.jsonl"
    content = _blob(owned, actual[archive.ref], source)
    if read_regular(owned.mission_dir / relative) != content:
        raise RecoveryError("Historical raw state archive is incomplete or changed")
    _verify_processes(owned, content)
    archived_lines = content.splitlines()
    for tip in actual.values():
        raw = _blob(owned, tip, source)
        remaining = iter(archived_lines)
        for line in raw.splitlines():
            if not any(candidate == line for candidate in remaining):
                raise RecoveryError("Archive omits ordered historical raw state")
        _verify_processes(owned, raw)
    claims = _text(owned, "for-each-ref", "--format=%(refname) %(objectname)", f"refs/spec-kitty/wp-base/{owned.mission_slug}/")
    current_claims = dict(row.split(" ", 1) for row in claims.splitlines())
    if current_claims != proof.claim_refs:
        raise RecoveryError("Current claim refs are missing, changed, or unknown")
    return {
        "archived_status_sha256": digest(content),
        "claim_refs_sha256": digest(claims.encode()),
        "historical_refs_sha256": digest(json.dumps(actual, sort_keys=True).encode()),
        **source_custody,
    }
