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
import unicodedata
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


def _logical_lines(value: str) -> list[str] | None:
    """Remove unquoted LF continuations and full-line comments only."""
    lines: list[str] = []
    pending = ""
    for line in value.split("\n"):
        if not pending and line.lstrip(" \t").startswith("#"):
            continue
        if line.endswith("\\"):
            prefix = pending + line[:-1]
            if "\\" in prefix:
                return None
            try:
                shlex.split(prefix, comments=False, posix=True)
            except ValueError:
                return None
            pending = prefix
        else:
            lines.append(pending + line)
            pending = ""
    return None if pending else lines


def _commands(value: object) -> list[list[str]] | None:
    if not isinstance(value, str) or not value.strip(" \t\n"):
        return None
    # Bash command boundaries and blanks are not Unicode splitlines/strip
    # boundaries. Refuse other control/separator categories, even inside
    # quotes, rather than inventing commands or silently changing payloads.
    if any(character not in " \t\n" and unicodedata.category(character)[0] in {"C", "Z"} for character in value):
        return None
    lines = _logical_lines(value)
    if lines is None:
        return None
    commands: list[list[str]] = []
    for line in lines:
        if not line.strip(" \t"):
            continue
        # Static argv only: no expansion, operators, globs, assignments, or
        # compound shell syntax. Original source is recoverable by its digest.
        if re.search(r"[$`;&|<>*?{}()\\\[\]~#!]", line):
            return None
        try:
            lexer = shlex.shlex(line, posix=True)
            lexer.whitespace = " \t"
            lexer.whitespace_split = True
            lexer.commenters = ""
            argv = list(lexer)
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


def _local_command(kind: str, instance: str) -> list[str]:
    """Map the pinned router's known IO boundaries, never execute its shell."""
    prefix = ["uv", "run", "--frozen", "python", "-m"]
    if kind in {"start", "stop"}:
        return prefix + ["scripts.ci.memory_sampler", kind, "--out", f"out/validation/memory-{instance}.json"]
    if kind == "prose":
        return prefix + ["scripts.validation.check_inputs", "prose", "out/validation/prose-input.json", "--authority", "tools/validation/gates.json"]
    if kind == "results":
        return prefix + ["scripts.validation.check_inputs", "results", "out/validation/results-input.json"]
    if kind == "commit-range":
        return ["git", "log", "--format=%s", "--end-of-options", "@commit_range"]
    if kind == "markdown":
        return ["npx", "--yes", "markdownlint-cli2", "**/*.md"]
    raise ValueError("Unsupported native command binding")


def _router_step(name: str, index: int, step: dict[str, object], shard: str, instance: str) -> tuple[list[list[str]], str]:
    run = step.get("run")
    if not isinstance(run, str):
        return [], "success"
    if "scripts.ci.memory_sampler" in run:
        return [_local_command("stop" if " stop " in run else "start", instance)], "always" if " stop " in run else "success"
    if name in {"prose-scan", "router-gate"}:
        if name == "prose-scan" and "pip install" in run:
            return [], "success"  # Exact dependency provisioning remains an explicit prerequisite.
        return [_local_command("prose" if name == "prose-scan" else "results", instance)], "success"
    if name == "commit-msg":
        return [_local_command("commit-range", instance)], "advisory"
    if name == "markdownlint":
        return [_local_command("markdown", instance)], "advisory"
    if name == "architectural-heavy":
        prefix = ["uv", "run", "--frozen", "python", "-m", "scripts.ci.collect_universe_prestep"]
        if "consumers --battery-part" in run:
            return [prefix + ["consumers", "--battery-part", shard]], "decision"
        if " key --with-commit" in run:
            return [prefix + ["key", "--with-commit"]], "optional-cache"
        run = run.replace("${{ matrix.shard }}", shard).replace("${{ matrix.label }}", instance)
    commands = _commands(run)
    if commands is None:
        raise ValueError(f"Unsupported native mapping: {name}.steps.{index}")
    condition = "universe-always" if "collect_universe_prestep check" in run else "universe" if step.get("if") else "success"
    return commands, condition


def _router_check(name: str, job: dict[str, object], source: dict[str, str]) -> dict[str, object]:
    argv: list[list[str]] = []
    conditions: list[str] = []
    instances: list[str] = []
    legs = [("1/2", "1-of-2"), ("2/2", "2-of-2")] if name == "architectural-heavy" else [("fast", "default")]
    steps = job["steps"]
    if not isinstance(steps, list):
        raise ValueError("Invalid router steps")
    for shard, instance in legs:
        for index, value in enumerate(steps):
            step = _mapping(value)
            commands, condition = _router_step(name, index, step, shard, instance)
            argv.extend(commands)
            conditions.extend([condition] * len(commands))
            instances.extend([instance] * len(commands))
    required_inputs = ["candidate", "base", "dependencies"]
    if name in {"architectural-fast", "architectural-heavy"}:
        required_inputs.append("memory_output")
    if name == "architectural-heavy":
        required_inputs.extend(["universe_decision", "universe_reuse"])
    if name in {"prose-scan", "router-gate", "commit-msg"}:
        required_inputs.append({"prose-scan": "prose", "router-gate": "results", "commit-msg": "commit_range"}[name])
    minutes = job.get("timeout-minutes")
    if type(minutes) is not int or minutes <= 0 or not argv:
        raise ValueError("Missing native command or finite budget")
    needs = job.get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    if not isinstance(needs, list) or any(not isinstance(item, str) for item in needs):
        raise ValueError("Invalid router dependencies")
    dependencies = [str(item) for item in needs]
    return {
        "argv": argv,
        "unmatched_source": True,
        "stderr_policy": ["allow"] * len(argv),
        "modes": ["commit", "full"],
        "platforms": ["linux"] if name in {"architectural-fast", "architectural-heavy"} else ["macos", "linux", "windows"],
        "dependencies": [] if name == "router-gate" else [name for name in dependencies if name != "changes"],
        "environment": {"PYTHONPATH": "."},
        "budgets": {
            "wall_ms": minutes * 60000 * len(legs),
            "cleanup_ms": 5000,
            "stdout_bytes": 16777216,
            "stderr_bytes": 16777216,
            "sampled_processes": 64,
            "sampled_resident_bytes": 8589934592,
        },
        "recipe": {
            "source": source,
            "python_version": "3.12",
            "advisory": name in {"commit-msg", "markdownlint"},
            "required_inputs": required_inputs,
            "conditions": conditions,
            "instances": instances,
            "applicability": "routing-and-not-prose" if name == "architectural-heavy" else "routing-or-prose" if name == "tests-docs" else "routing",
            "packages": {"PyYAML": "6.0.2"} if name == "prose-scan" else {},
            "observed_dependencies": dependencies,
            "instance_environment": {instance: {"SK_GATE_REUSE_REPORT": f"out/validation/universe-{instance}.jsonl"} for _, instance in legs}
            if name == "architectural-heavy"
            else {},
        },
    }


def _pack_check(name: str, job: dict[str, object], source: dict[str, str]) -> dict[str, object]:
    """Translate only the exact pinned Packs epoch; do not run its commands."""
    steps = job.get("steps")
    if not isinstance(steps, list):
        raise ValueError("Invalid Packs steps")
    argv: list[list[str]] = []
    policies: list[str] = []
    for value in steps:
        step = _mapping(value)
        run = step.get("run")
        if not isinstance(run, str) or step.get("if") == "failure()":
            continue  # Original source retains pure remediation notices.
        if name == "packs-gate":
            commands = [_local_command("results", "default")[:-1] + ["out/validation/packs-results-input.json"]]
        elif name == "built-in-plugin-validate":
            if run.startswith("npm install"):
                continue  # Exact Claude executable is a bound prerequisite, never a global install.
            commands = [["uv", "sync", "--frozen", "--all-extras"], ["uv", "run", "--frozen", "spec-kitty", "plugin", "build", "--target", "claude-code"]]
        elif run.strip() == "find . -depth -type d -name '__pycache__' -exec rm -rf {} +":
            commands = [["find", ".", "-depth", "-type", "d", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"]]
        else:
            static = _commands(run)
            if static is None:
                raise ValueError(f"Unsupported native Packs mapping: {name}")
            commands = static
        argv.extend(commands)
        policies.extend(["allow"] * len(commands))
    if name == "built-in-plugin-validate":
        policies[-1] = "reject-warning-prefix"
    minutes = job.get("timeout-minutes")
    if type(minutes) is not int or minutes <= 0 or not argv:
        raise ValueError("Missing Packs commands or finite budget")
    needs = job.get("needs", [])
    if not isinstance(needs, list) or any(not isinstance(item, str) for item in needs):
        raise ValueError("Invalid Packs dependencies")
    inputs = ["candidate", "base", "dependencies"]
    if name == "built-in-plugin-validate":
        inputs.append("claude_cli_2_1_270")
    if name == "packs-gate":
        inputs.append("results")
    return {
        "argv": argv,
        "unmatched_source": name in {"built-in-pack-manifest", "built-in-corpus-suite", "packs-gate"},
        "stderr_policy": policies,
        "modes": ["commit", "full"],
        "platforms": ["linux"],
        "dependencies": [],
        "environment": {"PYTHONPATH": "."},
        "budgets": {
            "wall_ms": minutes * 60000,
            "cleanup_ms": 5000,
            "stdout_bytes": 16777216,
            "stderr_bytes": 16777216,
            "sampled_processes": 64,
            "sampled_resident_bytes": 8589934592,
        },
        "recipe": {
            "source": source,
            "python_version": "3.12",
            "advisory": job.get("continue-on-error", False),
            "required_inputs": inputs,
            "conditions": ["success"] * len(argv),
            "instances": ["default"] * len(argv),
            "applicability": "routing",
            "packages": {},
            "observed_dependencies": needs if name == "packs-gate" else [],
            "instance_environment": {},
        },
    }


def _argument_commands(run: str) -> tuple[list[list[str]], list[dict[str, object]]] | None:
    """Normalize only complete quoted variable words, without shell evaluation."""
    if "`" in run or "@environment." in run or any(character not in " \t\n" and unicodedata.category(character)[0] in {"C", "Z"} for character in run):
        return None
    references: list[tuple[str, str, str]] = []

    def replace(match: re.Match[str]) -> str:
        references.append((match[2] or match[3], match[1], match[4]))
        return f'"@environment.{len(references) - 1}"'

    pattern = r'(?<!\S)"([^"$\\\n]*)\$(?:\{([A-Z][A-Z0-9_]*)\}|([A-Z][A-Z0-9_]*)(?![A-Za-z0-9_]))([^"$\\\n]*)"(?=\s|$)'
    commands = _commands(re.sub(pattern, replace, run))
    if commands is None:
        return None
    bindings: list[dict[str, object]] = []
    for command, argv in enumerate(commands):
        for argument, value in enumerate(argv):
            if value.startswith("@environment."):
                if argument == 0:
                    return None
                reference = int(value.removeprefix("@environment."))
                variable, prefix, suffix = references[reference]
                bindings.append({"command": command, "argument": argument, "variable": variable, "prefix": prefix, "suffix": suffix})
    if len(bindings) != len(references):
        return None
    return commands, bindings


def _step_program(run: str) -> tuple[list[list[str]], list[dict[str, object]], str] | None:
    lines = _logical_lines(run)
    if lines is None:
        return None
    lines = [line.strip(" \t") for line in lines if line.strip(" \t")]
    failure = "fail-fast"
    if lines and lines[0] == "set -u":
        if len(lines) < 4 or lines[1] != "status=0" or lines[-1] != "exit $status" or any(not line.endswith(" || status=1") for line in lines[2:-1]):
            return None
        lines = [line.removesuffix(" || status=1") for line in lines[2:-1]]
        failure = "collect-failures"
    elif lines and lines[0] == "set -euo pipefail":
        lines = lines[1:]
    result = _argument_commands("\n".join(lines))
    return (*result, failure) if result is not None else None


def _workflow_program(job: dict[str, object]) -> dict[str, object]:
    """Extract the shared supported command class; retain every other boundary."""
    argv: list[list[str]] = []
    controls: list[dict[str, object]] = []
    bindings: list[dict[str, object]] = []
    unsupported: list[int] = []
    steps = job.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("Invalid workflow steps")
    for index, value in enumerate(steps):
        step = _mapping(value)
        if "run" not in step:
            continue
        shell = step.get("shell")
        bash = shell == "bash" or (shell is None and str(job.get("runs-on", "")).startswith(("ubuntu-", "macos-")))
        result = _step_program(str(step["run"])) if bash else None
        if result is None:
            unsupported.append(index)
            continue
        commands, arguments, failure = result
        start = len(argv)
        controls.append({"step": index, "start": start, "count": len(commands), "failure": failure})
        for argument in arguments:
            argument["command"] = int(str(argument["command"])) + start
        bindings.extend(arguments)
        argv.extend(commands)
    if unsupported or not argv:
        return {
            "status": "unsupported",
            "steps": unsupported,
            "reason": "unsupported-shell-or-command-control" if unsupported else "no-external-argv",
            "context_required": True,
        }
    return {"status": "normalized", "argv": argv, "controls": controls, "argument_bindings": bindings, "context_required": True}


def _static_workflow_check(workflow: str, name: str, job: dict[str, object], source: dict[str, str]) -> dict[str, object]:
    """Declare a complete literal recipe, retaining its unbound source context."""
    program = _workflow_program(job)
    if program["status"] != "normalized":
        raise ValueError("Unsupported static workflow recipe")
    argv = program["argv"]
    if not isinstance(argv, list):
        raise ValueError("Invalid normalized workflow argv")
    steps = job.get("steps")
    if not isinstance(steps, list):
        raise ValueError("Invalid static workflow steps")
    if not argv or job.get("strategy") or job.get("runs-on") != "ubuntu-24.04":
        raise ValueError("Unsupported static workflow binding")
    minutes = job.get("timeout-minutes")
    if type(minutes) is not int or not 1 <= minutes <= 360:
        raise ValueError("Missing static workflow budget")
    versions = {
        str(_mapping(step.get("with", {}))["python-version"]) for value in steps for step in [_mapping(value)] if "python-version" in _mapping(step.get("with", {}))
    }
    if len(versions) > 1:
        raise ValueError("Unresolved static workflow interpreter")
    modes = ["commit", "full"] if workflow in {"ci-quality", "contracts"} else ["full"]
    if workflow == "ci-quality":
        modes.append("release")
        if name == "build-wheel":
            modes.append("package")
    return {
        "argv": argv,
        "unmatched_source": workflow == "ci-quality",
        "stderr_policy": ["allow"] * len(argv),
        "modes": modes,
        "platforms": ["linux"],
        "dependencies": [],
        "environment": {},
        "budgets": {
            "wall_ms": minutes * 60000,
            "cleanup_ms": 5000,
            "stdout_bytes": 16777216,
            "stderr_bytes": 16777216,
            "sampled_processes": 64,
            "sampled_resident_bytes": 8589934592,
        },
        "recipe": {
            "source": source,
            "python_version": next(iter(versions), "unbound"),
            "advisory": job.get("continue-on-error", False),
            "required_inputs": ["candidate", "base", "dependencies", "workflow_context"],
            "conditions": ["source-context"] * len(argv),
            "instances": ["default"] * len(argv),
            "applicability": "workflow",
            "packages": {},
            "observed_dependencies": [],
            "instance_environment": {},
            "workflow_job": name,
        },
    }


def _contract_dependencies(workflow: str, definition: dict[str, object], checks: dict[str, object], supported: set[str]) -> None:
    if workflow != "contracts":
        return
    jobs = _mapping(definition["jobs"])
    for name in supported:
        needs = _mapping(jobs[name]).get("needs", [])
        names = [needs] if isinstance(needs, str) else needs
        if not isinstance(names, list) or any(item not in supported for item in names):
            raise ValueError("Unsupported normalized workflow dependency")
        check = _mapping(checks[f"contracts.{name}"])
        check["dependencies"] = [f"contracts.{item}" for item in names]
        checks[f"contracts.{name}"] = check


def _workflow_contracts(root: Path, inventory: Extraction, authority: dict[str, object]) -> list[dict[str, object]]:
    """Preserve all authored semantics; normalize only reviewed literal recipes."""
    checks = _mapping(authority["checks"])
    routing = _mapping(authority["routing"])
    filters = _mapping(routing["filters"])
    gates = _mapping(routing["job_gates"])
    data = routing["non_source_groups"]
    if not isinstance(data, list):
        raise ValueError("Invalid workflow routing")
    compatible = {
        "ci-quality": {"lint", "build-wheel", "uv-lock-check"},
        "contracts": {"verify-pins"},
        "ci-nightly": {"universe-equivalence"},
        "ci-shard-recapture": {"strict-shard-timings-check"},
    }
    migration = authority.get("migration")
    if not isinstance(migration, list):
        raise ValueError("Invalid pinned workflow roster")
    expected = {str(row["path"]): str(row["sha256"]) for value in migration for row in [_mapping(value)]}
    if expected != {row["path"]: row["sha256"] for row in inventory["workflows"]}:
        raise ValueError("Pinned workflow roster changed; source mapping review required")
    contracts: list[dict[str, object]] = []
    for row in inventory["workflows"]:
        path = root / row["path"]
        raw = _read(path)
        if hashlib.sha256(raw).hexdigest() != expected[row["path"]]:
            raise ValueError("Pinned workflow changed; source mapping review required")
        definition = _load(raw)
        workflow = path.stem
        source = {"path": row["path"], "sha256": row["sha256"], "role": "migration-baseline"}
        jobs: dict[str, object] = {}
        for name, value in _mapping(definition["jobs"]).items():
            job = _mapping(value)
            program = _workflow_program(job)
            identifier: str | None = name if workflow in {"ci-router", "packs"} and name != "changes" else None
            if name in compatible.get(workflow, set()) or (workflow == "contracts" and program["status"] == "normalized"):
                if workflow == "contracts":
                    compatible[workflow].add(name)
                identifier = f"{workflow}.{name}"
                checks[identifier] = _static_workflow_check(workflow, name, job, source)
                paths = _mapping(_mapping(definition["on"]).get("pull_request", {})).get("paths", [])
                group = f"workflow_{workflow.replace('-', '_')}"
                if workflow == "contracts":
                    # Corpus retains sole contracts routing ownership. Exact
                    # source triggers still require genuine workflow context.
                    gates[identifier] = ["corpus"]
                    if "corpus" not in data:
                        data.append("corpus")
                elif workflow != "ci-quality":
                    filters[group] = paths
                    if group not in data:
                        data.append(group)
                    # An explicit full-only declaration has no changed-path trigger.
                    gates[identifier] = [group]
                else:
                    gates[identifier] = []
            minutes = job.get("timeout-minutes", 360)
            if type(minutes) is not int or not 1 <= minutes <= 360:
                raise ValueError("Unsupported workflow wall budget")
            jobs[name] = {
                "check_id": identifier,
                "wall_ms": minutes * 60000,
                "budget_scope": "per-job-instance",
                "budget_origin": "source" if "timeout-minutes" in job else "github-default-360-minutes",
                "binding_required": True,
                "program": program,
            }
        _contract_dependencies(workflow, definition, checks, compatible.get(workflow, set()))
        contracts.append({"id": workflow, "source": source, "definition": definition, "jobs": jobs})
        if _read(path) != raw:
            raise ValueError("Workflow changed during declaration construction")
    routing.update(filters=filters, job_gates=gates, non_source_groups=sorted(data))
    authority.update(checks=checks, routing=routing)
    return contracts


def executable_router_specification(root: Path) -> dict[str, object]:
    """Construct pinned source contracts and compatible complete command recipes.

    The result declares commands and unbound prerequisites. It neither provisions
    an environment nor establishes execution/platform/publication qualification.
    """
    root = root.resolve(strict=True)
    path = root / "tools/validation/gates.json"
    raw = _read(path)
    authority = _mapping(json.loads(raw))
    source = _mapping(authority["source"])
    router_path = root / str(source["path"])
    router_raw = _read(router_path)
    if hashlib.sha256(router_raw).hexdigest() != source["sha256"]:
        raise ValueError("Pinned router changed; source mapping review required")
    # Every dynamic normalization below is scoped to this reviewed exact source.
    if source["sha256"] != "aee8b9e6bda7dcf046d3b90a6a41cdc519d60ceb30e6f5d2dd329bcaa3f31ea1":
        raise ValueError("Unsupported router source mapping")
    jobs = _mapping(_load(router_raw)["jobs"])
    inventory = extract_workflows(root)
    normalized_source = {key: str(source[key]) for key in ("path", "sha256", "role")}
    packs_path = root / ".github/workflows/packs.yml"
    packs_raw = _read(packs_path)
    packs_sha = hashlib.sha256(packs_raw).hexdigest()
    if packs_sha != "6ee5cc4f580cc1e69bd58f1aa5b8d1d67c1e030c78f87e85b40d56290bf18d7e":
        raise ValueError("Unsupported Packs source mapping")
    packs = _mapping(_load(packs_raw)["jobs"])
    from scripts.ci.gate_selection import load_router

    router_model = load_router(router_path)
    packs_model = load_router(packs_path)
    filters = {name: list(patterns) for name, patterns in router_model.filters.items()}
    gates = {name: sorted(groups) for name, groups in router_model.job_gates.items()}
    data_groups = []
    for name, patterns in packs_model.filters.items():
        group = "packs_" + name
        filters[group] = list(patterns)
        data_groups.append(group)
    for name, groups in packs_model.job_gates.items():
        gates[name] = sorted("corpus" if group == "corpus" else "packs_" + group for group in groups)
    authority["routing"] = {"filters": filters, "job_gates": gates, "non_source_groups": sorted(data_groups), "unknown_surface_policy": "refuse-path-sensitive"}
    authority["schema_version"] = 6
    authority["checks"] = {name: _router_check(name, _mapping(value), normalized_source) for name, value in jobs.items() if name != "changes"}
    checks = _mapping(authority["checks"])
    packs_source = {"path": ".github/workflows/packs.yml", "sha256": packs_sha, "role": "migration-baseline"}
    checks.update({name: _pack_check(name, _mapping(job), packs_source) for name, job in packs.items() if name != "changes"})
    authority["checks"] = checks
    authority["workflow_contracts"] = _workflow_contracts(root, inventory, authority)
    if _read(path) != raw or _read(router_path) != router_raw or _read(packs_path) != packs_raw:
        raise ValueError("Changed native specification inputs")
    return authority


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--require-runnable", action="store_true", help="Refuse an inventory with unresolved native mappings")
    parser.add_argument("--router-specification", action="store_true", help="Emit pinned native router recipes; execution remains unqualified")
    args = parser.parse_args()
    try:
        if args.router_specification:
            if args.require_runnable:
                raise ValueError("Recipe declaration is not execution qualification")
            print(json.dumps(executable_router_specification(args.root), indent=2, sort_keys=True))
            return 0
        result = extract_workflows(args.root)
    except (ValueError, OSError) as error:
        print(f"Workflow extraction refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if args.require_runnable and not result["runnable"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
