"""Inspect pinned hosted commands before translating them to native gates.

This migration tool never runs checks or grants gate authority. Unsupported
actions, shell semantics, conditions, and execution bindings remain blockers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import stat
import sys
from pathlib import Path
from typing import TypedDict

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.tokens import AliasToken


# These depend on the selected shell's state/control rules. Bare names are
# refused; an explicitly qualified external executable has ordinary argv.
_SHELL_COMMANDS = frozenset(
    [
        ".",
        ":",
        "alias",
        "bg",
        "bind",
        "break",
        "builtin",
        "caller",
        "cd",
        "command",
        "compgen",
        "complete",
        "compopt",
        "coproc",
        "continue",
        "declare",
        "dirs",
        "disown",
        "echo",
        "enable",
        "eval",
        "exec",
        "exit",
        "export",
        "false",
        "fc",
        "fg",
        "getopts",
        "hash",
        "help",
        "history",
        "if",
        "then",
        "else",
        "elif",
        "fi",
        "for",
        "while",
        "until",
        "do",
        "done",
        "case",
        "esac",
        "in",
        "function",
        "select",
        "jobs",
        "kill",
        "let",
        "local",
        "logout",
        "mapfile",
        "popd",
        "printf",
        "pushd",
        "pwd",
        "read",
        "readarray",
        "readonly",
        "return",
        "set",
        "shift",
        "shopt",
        "source",
        "suspend",
        "test",
        "time",
        "times",
        "trap",
        "true",
        "type",
        "typeset",
        "ulimit",
        "umask",
        "unalias",
        "unset",
        "wait",
    ]
)


class Step(TypedDict):
    index: int
    sha256: str
    uses: object
    argv: list[list[str]] | None
    fields: dict[str, str]


class Job(TypedDict):
    condition: object
    needs: list[str]
    runner: object
    wall_ms: int | None
    fields: dict[str, str]
    steps: list[Step]


class Workflow(TypedDict):
    path: str
    sha256: str
    trigger: object
    fields: dict[str, str]
    jobs: dict[str, Job]


class Blocker(TypedDict):
    source: str
    reason: str


class Extraction(TypedDict):
    schema_version: int
    authority: bool
    validation_performed: bool
    runnable: bool
    workflows: list[Workflow]
    blockers: list[Blocker]


def _decode(node: Node, depth: int = 0) -> object:
    """Decode safe syntax directly, retaining string keys and rejecting duplicates."""
    if depth > 64:
        raise ValueError("Invalid workflow nesting budget")
    if isinstance(node, MappingNode):
        result: dict[str, object] = {}
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode) or key_node.tag not in {"tag:yaml.org,2002:str", "tag:yaml.org,2002:bool"}:
                raise ValueError("Invalid workflow key")
            key = key_node.value
            if key in result:
                raise ValueError("Invalid or duplicate workflow field")
            result[key] = _decode(value_node, depth + 1)
        return result
    if isinstance(node, SequenceNode):
        return [_decode(item, depth + 1) for item in node.value]
    if isinstance(node, ScalarNode):
        if node.tag in {"tag:yaml.org,2002:str", "tag:yaml.org,2002:timestamp"}:
            return node.value
        if node.tag == "tag:yaml.org,2002:null":
            return None
        if node.tag == "tag:yaml.org,2002:bool":
            return node.value.lower() == "true" if node.value.lower() in {"true", "false"} else node.value
        if node.tag in {"tag:yaml.org,2002:int", "tag:yaml.org,2002:float"}:
            value: object = yaml.safe_load(node.value)
            return value
    raise ValueError("Unsupported workflow YAML tag")


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError("Invalid workflow object")
    return dict(value)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _commands(value: object) -> list[list[str]] | None:
    if not isinstance(value, str) or not value.strip():
        return None
    commands: list[list[str]] = []
    for line in value.splitlines():
        if not line.strip():
            continue
        # Static argv only: no expansion, operators, globs, assignments, or
        # compound shell syntax. Original source is recoverable by its digest.
        if re.search(r"[$`;&|<>*?{}()\\\[\]~#!]", line):
            return None
        try:
            argv = shlex.split(line, comments=False)
        except ValueError:
            return None
        if not argv or argv[0] in _SHELL_COMMANDS or not re.fullmatch(r"[A-Za-z0-9_./-]+", argv[0]) or "=" in argv[0]:
            return None
        commands.append(argv)
    return commands or None


def _paths(directory: Path) -> list[Path]:
    return sorted(path for path in directory.iterdir() if path.suffix in {".yml", ".yaml"})


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Invalid workflow file or symlink")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Invalid workflow regular file")
        raw = stream.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("Invalid workflow byte budget")
    return raw


def _load(raw: bytes) -> dict[str, object]:
    try:
        if any(isinstance(token, AliasToken) for token in yaml.scan(raw)):
            raise ValueError("Unsupported workflow YAML alias")
        node = yaml.compose(raw, Loader=yaml.SafeLoader)
        if node is None:
            raise ValueError("Invalid empty workflow")
        return _mapping(_decode(node))
    except (yaml.YAMLError, UnicodeError, TypeError, RecursionError) as error:
        raise ValueError("Invalid workflow YAML") from error


def _block(blockers: list[Blocker], source: str, reason: str) -> None:
    blockers.append({"source": source, "reason": reason})


def _step(value: object, index: int, location: str, blockers: list[Blocker]) -> Step:
    step = _mapping(value)
    if "uses" in step:
        _block(blockers, location, "action")
    argv = _commands(step.get("run"))
    if "run" in step and argv is None:
        _block(blockers, location, "shell_semantics")
    for field in step:
        if field not in {"name", "id", "run", "uses"}:
            _block(blockers, location, f"step_field:{field}")
    return {"index": index, "sha256": _digest(step), "uses": step.get("uses"), "argv": argv, "fields": {key: _digest(val) for key, val in step.items()}}


def _job(value: object, name: str, jobs: dict[str, object], location: str, blockers: list[Blocker]) -> Job:
    job = _mapping(value)
    needs_value = job.get("needs", [])
    needs = [needs_value] if isinstance(needs_value, str) else needs_value
    if not isinstance(needs, list) or any(not isinstance(item, str) or item not in jobs or item == name for item in needs):
        raise ValueError("Invalid workflow dependency")
    minutes = job.get("timeout-minutes")
    if minutes is not None and (type(minutes) is not int or not 1 <= minutes <= 360):
        raise ValueError("Invalid workflow timeout")
    if minutes is None:
        _block(blockers, location, "missing_wall_budget")
    if "if" in job:
        _block(blockers, location, "job_condition")
    for field in job:
        if field not in {"name", "needs", "timeout-minutes", "if", "runs-on", "steps"}:
            _block(blockers, location, f"job_field:{field}")
    _block(blockers, location, "native_execution_binding")
    step_values = job.get("steps", [])
    if not isinstance(step_values, list) or len(step_values) > 1024:
        raise ValueError("Invalid workflow step budget")
    return {
        "condition": job.get("if"),
        "needs": needs,
        "runner": job.get("runs-on"),
        "wall_ms": minutes * 60000 if isinstance(minutes, int) else None,
        "fields": {key: _digest(val) for key, val in job.items()},
        "steps": [_step(item, index, f"{location}.steps.{index}", blockers) for index, item in enumerate(step_values)],
    }


def _check_dependencies(jobs: dict[str, Job]) -> None:
    pending = set(jobs)
    completed: set[str] = set()
    while pending:
        ready = {name for name in pending if set(jobs[name]["needs"]) <= completed}
        if not ready:
            raise ValueError("Invalid workflow dependency cycle")
        completed.update(ready)
        pending.difference_update(ready)


def extract_workflows(root: Path) -> Extraction:
    """Return a bounded, non-authoritative migration inventory; refuse ambiguity."""
    root = root.resolve(strict=True)
    directory = root / ".github" / "workflows"
    if (root / ".github").is_symlink() or directory.is_symlink():
        raise ValueError("Invalid workflow directory symlink")
    paths = _paths(directory)
    if not paths or len(paths) > 256:
        raise ValueError("Invalid workflow inventory size")
    workflows: list[Workflow] = []
    blockers: list[Blocker] = []
    pins: dict[Path, bytes] = {}

    for path in paths:
        raw = _read(path)
        pins[path] = raw
        document = _load(raw)
        jobs = _mapping(document.get("jobs"))
        if not jobs or len(jobs) > 256:
            raise ValueError("Invalid workflow job budget")
        source = path.relative_to(root).as_posix()
        _block(blockers, source, "trigger_and_publication_mapping")
        for field in document:
            if field not in {"name", "on", "jobs"}:
                _block(blockers, source, f"workflow_field:{field}")
        extracted_jobs = {name: _job(value, name, jobs, f"{source}#jobs.{name}", blockers) for name, value in jobs.items()}
        _check_dependencies(extracted_jobs)
        workflows.append(
            {
                "path": source,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "trigger": document.get("on"),
                "fields": {key: _digest(val) for key, val in document.items()},
                "jobs": extracted_jobs,
            }
        )
    if (root / ".github").is_symlink() or directory.is_symlink() or _paths(directory) != paths or any(_read(path) != raw for path, raw in pins.items()):
        raise ValueError("Changed workflow inventory during extraction")
    return {"schema_version": 1, "authority": False, "validation_performed": False, "runnable": False, "workflows": workflows, "blockers": blockers}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--require-runnable", action="store_true", help="Refuse an inventory with unresolved native mappings")
    args = parser.parse_args()
    try:
        result = extract_workflows(args.root)
    except (ValueError, OSError) as error:
        print(f"Workflow extraction refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if args.require_runnable and not result["runnable"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
