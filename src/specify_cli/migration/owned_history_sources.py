"""Immutable source validation and lossless union for owned history restoration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from mission_runtime.context import MissionTopology, routes_through_coordination
from specify_cli.status.models import StatusSnapshot, ULID_PATTERN
from specify_cli.status.reducer import materialize_to_json, reduce
from specify_cli.status.store import StoreError, read_event_stream_from_text

__all__ = ["HistoryRestoreError", "git_bytes", "json_object", "load_source", "merge_rows", "project", "sha256", "validate_meta"]

EVENTS = "status.events.jsonl"
SNAPSHOT = "status.json"
META = "meta.json"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_IDENTITY_KEYS = ("mission_id", "mission_slug", "mission_type", "topology", "target_branch", "coordination_branch")


class HistoryRestoreError(ValueError):
    """A recovery cannot preserve verified identity or historical values."""


def git_bytes(root: Path, *args: str) -> bytes:
    """Read Git without optional index writes, environment redirects or replacements."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    try:
        result = subprocess.run(["git", "--no-optional-locks", "-C", str(root), *args], capture_output=True, timeout=30, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HistoryRestoreError(f"Git read failed: {exc}") from exc
    if result.returncode:
        raise HistoryRestoreError(f"Git {' '.join(args)} refused: {result.stderr.decode('utf-8', errors='replace').strip()}")
    return result.stdout


def sha256(raw: bytes) -> str:
    """Content identity, not an authentication claim."""
    return hashlib.sha256(raw).hexdigest()  # noqa: TID251 - immutable Git blob/output integrity, not charter hashing


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HistoryRestoreError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> Any:
    raise HistoryRestoreError(f"Non-finite JSON number: {value}")


def json_object(raw: bytes | str) -> dict[str, Any]:
    """Decode strict UTF-8 JSON objects without duplicate-key loss."""
    try:
        value = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HistoryRestoreError(f"Invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise HistoryRestoreError("Expected a JSON object")
    return value


def validate_meta(meta: dict[str, Any], slug: str, expected: dict[str, Any] | None = None) -> None:
    """Require an existing coordinated dossier; never mint or change its identity."""
    if not isinstance(meta.get("mission_id"), str) or not ULID_PATTERN.fullmatch(meta["mission_id"]):
        raise HistoryRestoreError("Dossier requires a valid existing mission_id")
    try:
        topology = MissionTopology(meta.get("topology"))
    except ValueError as exc:
        raise HistoryRestoreError("Dossier requires a supported topology") from exc
    if meta.get("mission_slug") != slug or not routes_through_coordination(topology):
        raise HistoryRestoreError("Dossier must match the selected slug and coordinated topology")
    for key in ("mission_type", "target_branch", "coordination_branch"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise HistoryRestoreError(f"Dossier requires {key}")
    if expected is not None and any(meta.get(key) != expected.get(key) for key in _IDENTITY_KEYS):
        raise HistoryRestoreError("Pinned dossier identity/topology/branch does not match the owned dossier")


def _row_identity(row: dict[str, Any], meta: dict[str, Any]) -> None:
    for mapping in (row, row.get("payload", {})):
        if not isinstance(mapping, dict):
            raise HistoryRestoreError("Event payload must be an object")
        for key in ("mission_id", "mission_slug"):
            if key in mapping and mapping[key] != meta[key]:
                raise HistoryRestoreError(f"Event {key} does not match the pinned dossier")
    if row.get("aggregate_type") == "Mission" and row.get("aggregate_id") not in (meta["mission_id"], meta["mission_slug"]):
        raise HistoryRestoreError("Mission aggregate identity does not match the dossier")


def _timestamp(row: dict[str, Any]) -> str:
    when = row.get("at") or row.get("timestamp")
    if not isinstance(when, str):
        raise HistoryRestoreError("Event requires a timestamp")
    try:
        parsed = datetime.fromisoformat(when.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HistoryRestoreError("Invalid event timestamp") from exc
    if parsed.tzinfo is None:
        raise HistoryRestoreError("Event timestamp requires a timezone")
    return when


def _rows(raw: bytes, meta: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise HistoryRestoreError("Status log must be UTF-8") from exc
    rows = []
    for line in lines:
        if not line.strip():
            continue
        row = json_object(line)
        if not isinstance(row.get("event_id"), str) or not ULID_PATTERN.fullmatch(row["event_id"]):
            raise HistoryRestoreError("Every retained record requires its original valid event_id")
        _row_identity(row, meta)
        _timestamp(row)
        _row_shape(row)
        rows.append(row)
    return rows


def _row_shape(row: dict[str, Any]) -> None:
    if "event_type" in row:
        if any(key in row for key in ("from_lane", "to_lane", "kind")):
            raise HistoryRestoreError("Mixed lifecycle/transition discriminator is unsupported")
        if not isinstance(row["event_type"], str) or not isinstance(row.get("payload"), dict):
            raise HistoryRestoreError("Lifecycle envelope requires event_type and payload")
    event_name, event_type = row.get("event_name"), row.get("type")
    if (isinstance(event_name, str) and event_name.startswith("retrospective.")) or (isinstance(event_type, str) and event_type.startswith("Retrospective")):
        raise HistoryRestoreError("Retrospective history requires its separate projection contract")
    if "wp_id" in row and (not isinstance(row["wp_id"], str) or not re.fullmatch(r"WP[0-9]{2,}", row["wp_id"])):
        raise HistoryRestoreError("Invalid historical wp_id")
    if "to_lane" in row and (not isinstance(row.get("force"), bool) or row.get("execution_mode") not in ("worktree", "direct_repo")):
        raise HistoryRestoreError("Invalid transition force or execution_mode")


def _verify_chain(rows: list[dict[str, Any]]) -> None:
    lanes: dict[str, str] = {}
    for row in rows:
        if "to_lane" not in row:
            continue
        wp_id = row["wp_id"]
        if row["from_lane"] != lanes.get(wp_id, "genesis"):
            raise HistoryRestoreError(f"Conflicting historical lane chain for {wp_id}: {row['event_id']}")
        lanes[wp_id] = row["to_lane"]


def merge_rows(groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Deduplicate only wholly equivalent rows, including all extension fields."""
    records: dict[str, dict[str, Any]] = {}
    canonical: dict[str, str] = {}
    for rows in groups:
        for row in rows:
            key = row["event_id"]
            encoded = json.dumps(row, sort_keys=True, ensure_ascii=False)
            if key in canonical and canonical[key] != encoded:
                raise HistoryRestoreError(f"Conflicting duplicate event_id: {key}")
            records[key], canonical[key] = row, encoded
    return sorted(records.values(), key=lambda row: (_timestamp(row), row["event_id"]))


def project(directory: Path, rows: list[dict[str, Any]], meta: dict[str, Any]) -> tuple[StatusSnapshot, bytes, dict[str, int]]:
    """Use the supported annotation-aware decoder/reducer, without file writes."""
    text = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    try:
        stream = read_event_stream_from_text(directory, text)
        _verify_chain(rows)
        snapshot = reduce(stream.transitions, stream.annotations)
    except (KeyError, ValueError, TypeError, StoreError) as exc:
        raise HistoryRestoreError(f"Invalid historical status log: {exc}") from exc
    snapshot.mission_number = str(meta["mission_number"]) if meta.get("mission_number") is not None else None
    snapshot.mission_type = meta["mission_type"]
    return (
        snapshot,
        text.encode("utf-8"),
        {
            "rows": len(rows),
            "transitions": len(stream.transitions),
            "annotations": len(stream.annotations),
            "non_lane": len(rows) - len(stream.transitions) - len(stream.annotations),
        },
    )


def _verify_snapshot(old: dict[str, Any], current: dict[str, Any]) -> dict[str, list[str]]:
    """Exact old projection parity, allowing only absent derived review_result slots."""
    additions: dict[str, list[str]] = {}
    comparable = json.loads(json.dumps(current))
    old_wps = old.get("work_packages")
    if not isinstance(old_wps, dict):
        raise HistoryRestoreError("Historical snapshot requires work_packages")
    for wp_id, state in comparable["work_packages"].items():
        previous = old_wps.get(wp_id, {})
        if not isinstance(previous, dict):
            raise HistoryRestoreError("Historical WP snapshot must be an object")
        if "review_result" in state and "review_result" not in previous:
            state.pop("review_result")
            additions[wp_id] = ["review_result"]
    # Older writers serialized an unset display number as an empty string.
    if old.get("mission_number") == "" and comparable.get("mission_number") is None:
        comparable["mission_number"] = ""
    if comparable != old:
        raise HistoryRestoreError("Historical snapshot does not match supported replay (lanes/counts/runtime/review values)")
    return additions


def _blob(root: Path, commit: str, path: str) -> tuple[bytes, dict[str, str]]:
    entry = git_bytes(root, "ls-tree", "-z", commit, "--", path).decode("utf-8")
    if not entry:
        raise HistoryRestoreError(f"Pinned dossier artifact missing: {commit}:{path}")
    header, name = entry.rstrip("\0").split("\t", 1)
    mode, kind, oid = header.split()
    if name != path or mode not in ("100644", "100755") or kind != "blob":
        raise HistoryRestoreError(f"Pinned artifact is not a regular file: {path}")
    raw = git_bytes(root, "cat-file", "blob", oid)
    return raw, {"blob": oid, "sha256": sha256(raw)}


def load_source(root: Path, directory: Path, commit: str, meta: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Pin a commit and its three regular dossier blobs, then verify its old snapshot."""
    if not _SHA.fullmatch(commit) or git_bytes(root, "cat-file", "-t", commit).strip() != b"commit":
        raise HistoryRestoreError("--source-commit requires a full lowercase immutable commit SHA")
    blobs: dict[str, dict[str, str]] = {}
    contents: dict[str, bytes] = {}
    for name in (META, EVENTS, SNAPSHOT):
        contents[name], blobs[name] = _blob(root, commit, f"kitty-specs/{meta['mission_slug']}/{name}")
    source_meta = json_object(contents[META])
    validate_meta(source_meta, meta["mission_slug"], meta)
    rows = merge_rows([_rows(contents[EVENTS], source_meta)])
    snapshot, _, counts = project(directory, rows, source_meta)
    additions = _verify_snapshot(json_object(contents[SNAPSHOT]), json.loads(materialize_to_json(snapshot)))
    return rows, {"commit": commit, "blobs": blobs, "counts": counts, "projection_additions": additions}
