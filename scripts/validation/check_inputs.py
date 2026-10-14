"""Bound local input adapters for the existing prose and result classifiers.

These adapters neither execute checks nor authenticate their producers. Native
candidate/execution tooling must supply and bind the actual roster and blobs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

from scripts.ci.gate_selection import router_from_local_document
from scripts.ci.prose_only import prose_only_pr_verdict
from scripts.ci.router_gate import classify

MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 32768
INVALID_INPUT = "Invalid local input"


def _object(value: object, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(INVALID_INPUT)
    return dict(value)


def _string(value: object, limit: int = 4096) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > limit or "\0" in value:
        raise ValueError(INVALID_INPUT)
    return value


def _hash(value: object, *, tree: bool = False) -> str:
    text = _string(value, 64)
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}" if tree else r"[0-9a-f]{64}", text) is None:
        raise ValueError(INVALID_INPUT)
    if set(text) == {"0"}:
        raise ValueError(INVALID_INPUT)
    return text


def _rows(value: object) -> list[Any]:
    if not isinstance(value, list) or len(value) > MAX_ROWS:
        raise ValueError(INVALID_INPUT)
    return value


def _names(value: object) -> list[str]:
    names = [_string(item) for item in _rows(value)]
    if len(set(names)) != len(names):
        raise ValueError(INVALID_INPUT)
    return names


def _header(request: dict[str, Any], kind: str) -> None:
    if type(request["schema_version"]) is not int or request["schema_version"] != 1 or request["kind"] != kind:
        raise ValueError(INVALID_INPUT)


def _binding(value: object) -> dict[str, str]:
    row = _object(value, {"candidate_tree", "specification_sha256", "invocation_id"})
    return {
        "candidate_tree": _hash(row["candidate_tree"], tree=True),
        "specification_sha256": _hash(row["specification_sha256"]),
        "invocation_id": _string(row["invocation_id"], 256),
    }


def evaluate_results(value: object) -> dict[str, object]:
    """Classify exactly one complete selected/unselected roster; refuse drift."""
    fields = {"schema_version", "kind", "binding", "selected", "unselected", "results"}
    if isinstance(value, dict) and "advisory" in value:
        fields.add("advisory")
    request = _object(value, fields)
    _header(request, "results")
    binding = _binding(request["binding"])
    selected, unselected = _names(request["selected"]), _names(request["unselected"])
    advisory = _names(request.get("advisory", []))
    if not selected or len(set(selected + unselected + advisory)) != len(selected + unselected + advisory):
        raise ValueError(INVALID_INPUT)
    expected = set(selected + unselected + advisory)
    conclusions: dict[str, str] = {}
    for value in _rows(request["results"]):
        row = _object(value, {"id", "conclusion", "binding"})
        name, conclusion = _string(row["id"]), _string(row["conclusion"], 128)
        if name not in expected or name in conclusions or _binding(row["binding"]) != binding:
            raise ValueError(INVALID_INPUT)
        if (name in selected and conclusion == "skipped") or (name in unselected and conclusion != "skipped"):
            raise ValueError(INVALID_INPUT)
        conclusions[name] = conclusion
    if set(conclusions) != expected:
        raise ValueError(INVALID_INPUT)
    decision = classify({name: conclusion for name, conclusion in conclusions.items() if name not in advisory or conclusion not in {"success", "failure"}})
    result: dict[str, object] = {"blocks": decision.blocks, "blocking": dict(decision.blocking), "validation_performed": False}
    if advisory:
        result["advisory_outcomes"] = {name: conclusions[name] for name in advisory}
    return result


def _path(value: object) -> str:
    path = _string(value)
    if path.startswith(("/", "\\")) or ".." in path.split("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError(INVALID_INPUT)
    return path


def _blob(value: object, digest: object) -> str | None:
    if value is None and digest is None:
        return None  # Added/deleted source is known absence, never proved prose.
    if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_BYTES:
        raise ValueError(INVALID_INPUT)
    if hashlib.sha256(value.encode("utf-8")).hexdigest() != _hash(digest):
        raise ValueError(INVALID_INPUT)
    return value


def _blobs(values: object, paths: list[str]) -> dict[str, tuple[str | None, str | None]]:
    result: dict[str, tuple[str | None, str | None]] = {}
    total = 0
    expected = set(paths)
    for value in _rows(values):
        row = _object(value, {"path", "base", "head", "base_sha256", "head_sha256"})
        path = _path(row["path"])
        if path not in expected or path in result:
            raise ValueError(INVALID_INPUT)
        base, head = _blob(row["base"], row["base_sha256"]), _blob(row["head"], row["head_sha256"])
        total += sum(len(text.encode("utf-8")) for text in (base, head) if text is not None)
        if total > MAX_BYTES:
            raise ValueError(INVALID_INPUT)
        result[path] = (base, head)
    if set(result) != expected:
        raise ValueError(INVALID_INPUT)
    return result


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(INVALID_INPUT)
        result[key] = value
    return result


def _json(raw: bytes) -> object:
    if len(raw) > MAX_BYTES:
        raise ValueError(INVALID_INPUT)
    return json.loads(raw, object_pairs_hook=_unique)


def evaluate_prose(value: object, authority: bytes) -> dict[str, object]:
    """Apply the existing prose predicate to bound staged/base blobs and routing."""
    request = _object(value, {"schema_version", "kind", "base_tree", "candidate_tree", "specification_sha256", "paths", "blobs"})
    _header(request, "prose")
    _hash(request["base_tree"], tree=True)
    _hash(request["candidate_tree"], tree=True)
    if hashlib.sha256(authority).hexdigest() != _hash(request["specification_sha256"]):
        raise ValueError(INVALID_INPUT)
    router = router_from_local_document(_json(authority))
    paths = [_path(path) for path in _names(request["paths"])]
    blobs = _blobs(request["blobs"], paths)
    doc_globs = tuple(router.filters.get("docs", ())) + tuple(router.filters.get("corpus", ()))
    verdict = prose_only_pr_verdict(paths, lambda path, side: blobs[path][0 if side == "base" else 1], doc_globs)
    return {"prose_only": verdict, "validation_performed": False}


def _read(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        stream = os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise
    with stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError(INVALID_INPUT)
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(INVALID_INPUT)
    return raw


def main(argv: list[str] | None = None) -> int:
    """Read bound JSON; emit metadata only and propagate classifier refusals."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("prose", "results"))
    parser.add_argument("input", type=Path)
    parser.add_argument("--authority", type=Path)
    args = parser.parse_args(argv)
    try:
        request = _json(_read(args.input))
        if args.kind == "prose":
            if args.authority is None:
                raise ValueError(INVALID_INPUT)
            result = evaluate_prose(request, _read(args.authority))
        else:
            if args.authority is not None:
                raise ValueError(INVALID_INPUT)
            result = evaluate_results(request)
    except (ValueError, OSError, UnicodeError, RecursionError):
        print("Local input refused", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 1 if result.get("blocks") else 0


if __name__ == "__main__":
    raise SystemExit(main())
