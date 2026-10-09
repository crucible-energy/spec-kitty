"""Typed, NUL-safe registered workspace inventory by intent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from kernel.git.runner import decode_path

__all__ = ["WorktreeRecord", "parse_worktree_records"]


@dataclass(frozen=True, slots=True)
class WorktreeRecord:
    path: Path
    head: str | None
    branch: str | None
    detached: bool
    bare: bool


def parse_worktree_records(raw: bytes, *, max_records: int = 512) -> tuple[WorktreeRecord, ...]:
    """Parse porcelain -z without treating whitespace in a path as syntax."""
    stanzas = [stanza for stanza in raw.split(b"\0\0") if stanza]
    if len(stanzas) > max_records:
        raise ValueError("Workspace inventory exceeds its bounded scope")
    records: list[WorktreeRecord] = []
    for stanza in stanzas:
        # Porcelain wire labels are bytes; paths and typed values decode at their boundary.
        fields: dict[bytes, bytes] = {}
        for row in stanza.split(b"\0"):
            if not row:
                continue
            key, _, value = row.partition(b" ")
            if not key.isascii():
                raise ValueError("Workspace inventory contains a non-ASCII field")
            if key in fields:
                raise ValueError("Workspace inventory contains duplicate fields")
            fields[key] = value
        if not fields.get(b"worktree"):
            raise ValueError("Workspace inventory has no path")
        bare = b"bare" in fields
        head = fields.get(b"HEAD", b"").decode("ascii") or None
        branch = fields.get(b"branch", b"").decode("utf-8") or None
        detached = b"detached" in fields
        if (not bare and (head is None or not re.fullmatch(r"[0-9a-f]{40}", head))) or (branch is not None and detached):
            raise ValueError("Workspace inventory has ambiguous HEAD or branch")
        records.append(WorktreeRecord(Path(decode_path(fields[b"worktree"])), head, branch, detached, bare))
    return tuple(records)
