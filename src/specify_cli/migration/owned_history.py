"""Scoped restoration into a Git-owned target checkout; no lifecycle advancement.

This is a historical intake surface, not coordination-branch placement. It writes
only a retained log, its derived snapshot and a pinned receipt into the explicit
target checkout. Existing root discovery and lifecycle placement stay separate.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specify_cli.context.mission_resolver import AmbiguousHandleError, MissionNotFoundError, resolve_mission
from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.status.locking import feature_status_lock, status_replacement_fence
from specify_cli.status.reducer import materialize_to_json

from .owned_history_sources import (
    HistoryRestoreError,
    git_bytes,
    json_object,
    load_source,
    merge_rows,
    project,
    sha256,
    validate_meta,
)
from .owned_history_io import BoundHistoryDirectory, FileImage

__all__ = ["restore_owned_mission_history"]

_MANIFEST = "history-restoration.json"
_OUTPUT_NAMES = ("status.events.jsonl", "status.json", _MANIFEST)
_GIT_REDIRECTS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE")


@dataclass(frozen=True)
class CheckoutOwnership:
    """Exact Git-registered checkout belonging to the invoking repository."""

    root: Path
    head: str


def _git_path(root: Path, argument: str) -> Path:
    value = Path(git_bytes(root, "rev-parse", argument).decode().strip())
    return (root / value).resolve() if not value.is_absolute() else value.resolve()


def _ownership(repository: Path, checkout: Path) -> CheckoutOwnership:
    if any(key in os.environ for key in _GIT_REDIRECTS):
        raise HistoryRestoreError("Git routing environment overrides are unsupported for owned recovery")
    root = checkout.absolute()
    if root != root.resolve() or _git_path(root, "--show-toplevel") != root:
        raise HistoryRestoreError("--owned-checkout must be the exact checkout root, without symlink aliases")
    if _git_path(repository, "--git-common-dir") != _git_path(root, "--git-common-dir"):
        raise HistoryRestoreError("Owned checkout belongs to a different repository")
    entries = git_bytes(repository, "worktree", "list", "--porcelain", "-z").decode().split("\0")
    registered = {Path(entry.removeprefix("worktree ")).resolve() for entry in entries if entry.startswith("worktree ")}
    if root not in registered:
        raise HistoryRestoreError("Owned checkout is not Git-registered")
    return CheckoutOwnership(root, git_bytes(root, "rev-parse", "HEAD").decode().strip())


def _safe_file(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or any(part in ("..", ".") for part in relative.parts):
        raise HistoryRestoreError("Unsafe relative dossier path")
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise HistoryRestoreError(f"Symlink dossier path refused: {relative}")
    if path.exists() and not path.is_file():
        raise HistoryRestoreError(f"Dossier artifact is not a regular file: {relative}")
    return path


def _target(repository: Path, checkout: Path, handle: str) -> tuple[CheckoutOwnership, Path, dict[str, Any]]:
    assert_safe_path_segment(handle)
    ownership = _ownership(repository, checkout)
    try:
        resolved = resolve_mission(handle, ownership.root)
    except (AmbiguousHandleError, MissionNotFoundError) as exc:
        raise HistoryRestoreError(str(exc)) from exc
    slug = assert_safe_path_segment(resolved.feature_dir.name)
    directory = ownership.root / "kitty-specs" / slug
    meta_path = _safe_file(ownership.root, Path("kitty-specs") / slug / "meta.json")
    meta = json_object(meta_path.read_bytes())
    validate_meta(meta, slug)
    branch = git_bytes(ownership.root, "symbolic-ref", "--short", "HEAD").decode().strip()
    if branch != meta["target_branch"] or ProtectionPolicy.resolve(ownership.root).is_protected(branch):
        raise HistoryRestoreError("Owned checkout must be on the dossier's unprotected target branch")
    for name in _OUTPUT_NAMES:
        _safe_file(ownership.root, Path("kitty-specs") / slug / name)
    return ownership, directory, meta


def _dirty_paths(root: Path) -> set[str]:
    # Index changes always refuse: even an identical staged output is user-owned.
    if git_bytes(root, "diff", "--cached", "--name-only", "-z"):
        raise HistoryRestoreError("Owned checkout has staged changes")
    paths = set(git_bytes(root, "diff", "--name-only", "-z").decode().rstrip("\0").split("\0"))
    paths.update(git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z").decode().rstrip("\0").split("\0"))
    return paths - {""}


def _baseline_pin(directory: Path, head: str, pins: list[str]) -> str:
    """Revalidate original inputs for exact reruns, even after output commit."""
    path = directory / _MANIFEST
    if not path.exists():
        return head
    previous = json_object(path.read_bytes())
    prior_sources = previous.get("sources", [])
    if not isinstance(prior_sources, list) or any(not isinstance(source, dict) or not isinstance(source.get("commit"), str) for source in prior_sources):
        raise HistoryRestoreError("Invalid recovery receipt sources")
    selected = [source["commit"] for source in prior_sources]
    hashes = previous.get("output_sha256", {})
    if not isinstance(hashes, dict):
        raise HistoryRestoreError("Invalid recovery receipt hashes")
    outputs_match = all(
        (directory / name).is_file() and sha256((directory / name).read_bytes()) == hashes.get(name) for name in ("status.events.jsonl", "status.json")
    )
    if selected == list(dict.fromkeys(pins)) and outputs_match:
        pin = previous.get("target_commit")
        if not isinstance(pin, str):
            raise HistoryRestoreError("Recovery receipt lacks its original target commit")
        return pin  # load_source revalidates this pin and rebuilds the receipt in full.
    return head


def _protect_outputs(ownership: CheckoutOwnership, outputs: dict[Path, bytes]) -> None:
    """Protect ignored/assume-unchanged artifacts as well as visible Git dirt."""
    for path, expected in outputs.items():
        if not path.exists() or path.read_bytes() == expected:
            continue
        relative = path.relative_to(ownership.root).as_posix()
        entry = git_bytes(ownership.root, "ls-tree", "-z", ownership.head, "--", relative)
        if not entry:
            raise HistoryRestoreError(f"Existing untracked/ignored output refused: {relative}")
        original = git_bytes(ownership.root, "show", f"{ownership.head}:{relative}")
        if path.read_bytes() != original:
            raise HistoryRestoreError(f"Divergent owned output refused: {relative}")


def _plan(ownership: CheckoutOwnership, directory: Path, meta: dict[str, Any], pins: list[str]) -> tuple[dict[Path, bytes], dict[str, Any]]:
    if not pins:
        raise HistoryRestoreError("At least one --source-commit is required")
    # The existing log MUST be committed source truth, not an arbitrary dirty input.
    groups, sources = [], []
    baseline = _baseline_pin(directory, ownership.head, pins)
    existing, target_source = load_source(ownership.root, directory, baseline, meta)
    groups.append(existing)
    for pin in dict.fromkeys(pins):
        rows, source = load_source(ownership.root, directory, pin, meta)
        groups.append(rows)
        sources.append(source)
    rows = merge_rows(groups)
    snapshot, log, counts = project(directory, rows, meta)
    snapshot_bytes = materialize_to_json(snapshot).encode("utf-8")
    receipt = {
        "schema_version": 1,
        "historical_only": True,
        "mission_id": meta["mission_id"],
        "mission_slug": meta["mission_slug"],
        "target_commit": baseline,
        "target_source": target_source,
        "sources": sources,
        "output_sha256": {"status.events.jsonl": sha256(log), "status.json": sha256(snapshot_bytes)},
        "counts": counts,
        "lanes": {wp: state["lane"] for wp, state in snapshot.work_packages.items()},
    }
    outputs = {directory / "status.events.jsonl": log, directory / "status.json": snapshot_bytes}
    outputs[directory / _MANIFEST] = (json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _protect_outputs(ownership, outputs)
    changed = any(not path.exists() or path.read_bytes() != raw for path, raw in outputs.items())
    dirty = _dirty_paths(ownership.root)
    # Immediate reruns accept only the exact verified generated outputs, and write nothing.
    if dirty and (changed or not dirty <= {str(path.relative_to(ownership.root)) for path in outputs}):
        raise HistoryRestoreError("Owned checkout is dirty; refusing to overwrite tracked or untracked work")
    report = {**receipt, "changed": changed, "owned_checkout": str(ownership.root)}
    return outputs, report


def _replace_batch(outputs: dict[Path, bytes], bound: BoundHistoryDirectory, originals: dict[str, FileImage], mission_slug: str) -> None:
    """Install under the canonical fence using a creator-owned directory transaction.

    The creator may conditionally roll back unchanged installed images on failure.
    A copied fork-child frame must propagate refusal without touching that ledger;
    the enclosing close detaches only its inherited descriptor copies.
    """
    staged = {path.name: bound.stage(raw, originals[path.name].mode) for path, raw in outputs.items()}
    expected = dict(originals)
    bound.verify(expected)  # A same-thread live append during staging must survive.
    attempted: dict[str, tuple[str, FileImage]] = {}
    installed_images: dict[str, FileImage] = {}
    with status_replacement_fence(bound.root, mission_slug) as fence:
        try:
            for name in sorted(staged, key=lambda name: name == "status.events.jsonl"):
                fence.check()
                bound.verify(expected)
                temporary, image = staged[name]
                attempted[name] = staged[name]
                bound.replace(temporary, name)
                installed = bound.read(name)
                if not installed.is_installed(image):
                    raise HistoryRestoreError(f"Installed history artifact changed concurrently: {name}")
                installed_images[name] = installed
                expected[name] = installed
                fence.check()
                bound.verify(expected)
            os.fsync(bound.fd)
        except BaseException:
            # A forked copy can reach this handler after a fence refusal or an
            # arbitrary child exception. Its matching images still belong to
            # the parent; only creator-owned rollback may modify them.
            if bound.owner_pid == os.getpid():
                bound.rollback(attempted, originals, installed_images)
            raise


def restore_owned_mission_history(repository: Path, checkout: Path, handle: str, pins: list[str], *, apply: bool = False) -> dict[str, Any]:
    """Restore verified pinned history; dry-run never creates locks or files."""
    ownership, directory, meta = _target(repository, checkout, handle)
    outputs, report = _plan(ownership, directory, meta, pins)
    if apply and report["changed"]:
        with feature_status_lock(ownership.root, meta["mission_slug"], timeout=10):
            bound = BoundHistoryDirectory(ownership.root, directory)
            try:
                originals = bound.capture(("meta.json", *_OUTPUT_NAMES))
                # Pin directory identities BEFORE the final locked plan, not at first staging.
                current, current_dir, current_meta = _target(repository, checkout, handle)
                if current != ownership or current_dir != directory or current_meta != meta:
                    raise HistoryRestoreError("Owned checkout changed during recovery planning")
                locked_outputs, locked_report = _plan(current, current_dir, current_meta, pins)
                if locked_outputs != outputs or locked_report != report:
                    raise HistoryRestoreError("History changed during recovery planning")
                bound.verify(originals)
                _replace_batch(outputs, bound, originals, meta["mission_slug"])
            finally:
                bound.close()
    return {**report, "dry_run": not apply, "applied": bool(apply and report["changed"])}
