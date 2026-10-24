"""Creator-side authorities. Events and local ancestry never certify delivery."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import stat
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import cast

from kernel.atomic import atomic_write
from kernel.git import run_git
from kernel.git.listing import status_entries
from kernel.git.worktree_registry import parse_worktree_records
from kernel.git_topology import inspect_git_common_dir
from kernel.locks import machine_file_lock
from kernel.no_follow import NoFollowPathError
from kernel.owned_process import bounded_run, budget_active, process_budget, signal_owned_process_tree
from specify_cli.core.git_ops import resolve_primary_branch
from specify_cli.git.destructive_guard import guarded_worktree_remove
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.git.ref_advance import RefDeleteError, delete_branch_ref
from specify_cli.workspace_lifecycle.coordinator import Recovered, Result
from specify_cli.workspace_lifecycle.discovery import discover_workspaces
from specify_cli.workspace_lifecycle.events import Completion
from specify_cli.workspace_lifecycle.policy import Evidence, Identity
from specify_cli.workspace_lifecycle.state import Operation, StateError, StateStore


class GitHubDelivery:
    """Fresh authenticated same-repository PR delivery to its default branch.

    A source SHA from a merged PR explicitly binds squash/rebase delivery without
    pretending the original commit must be an ancestor of the merge commit.
    This authority establishes delivery only, never owner release or fencing.
    """

    def __init__(self, *, timeout: float = 10.0) -> None:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Delivery authority requires a finite positive timeout")
        self.timeout = timeout

    @staticmethod
    def _get(path: str, deadline: float) -> dict[str, object]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise StateError("Delivery authority unavailable")
        env = {k: v for k, v in os.environ.items() if k != "GH_DEBUG"}
        env["GH_PROMPT_DISABLED"] = "1"
        try:
            executor = bounded_run if budget_active() else subprocess.run
            result = executor(
                ["gh", "api", "--hostname", "github.com", "--method", "GET", path],
                capture_output=True,
                check=False,
                timeout=remaining,
                env=env,
            )
            if result.returncode != 0 or len(result.stdout) > 4 * 1024 * 1024:
                raise StateError("Delivery authority unavailable")
            data: object = json.loads(result.stdout)
            if not isinstance(data, dict):
                raise StateError("Delivery authority unavailable")
            return cast(dict[str, object], data)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise StateError("Delivery authority unavailable") from exc

    @staticmethod
    def _same_repository(value: object, expected: Identity) -> bool:
        return (
            isinstance(value, dict)
            and type(value.get("id")) is int
            and value.get("id") == expected.repository_id
            and isinstance(value.get("full_name"), str)
            and value["full_name"].lower() == expected.repository
        )

    def verify(self, expected: Identity, pr: int) -> str | None:
        """Return an exact accepted-PR identity or no delivery; fail on unavailable authority."""
        if type(pr) is not int or pr <= 0:
            raise ValueError("Positive PR number required")
        deadline = time.monotonic() + self.timeout
        repository = self._get(f"repos/{expected.repository}", deadline)
        if not self._same_repository(repository, expected):
            return None
        default_branch = repository.get("default_branch")
        if not isinstance(default_branch, str) or not default_branch:
            raise StateError("Delivery authority unavailable")
        pull = self._get(f"repos/{expected.repository}/pulls/{pr}", deadline)
        head, base = pull.get("head"), pull.get("base")
        merged_at, merge_sha = pull.get("merged_at"), pull.get("merge_commit_sha")
        if (
            type(pull.get("number")) is not int
            or pull.get("number") != pr
            or pull.get("merged") is not True
            or pull.get("state") != "closed"
            or not isinstance(merged_at, str)
            or not merged_at
            or not isinstance(merge_sha, str)
            or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", merge_sha)
            or not isinstance(head, dict)
            or head.get("sha") != expected.head
            or head.get("ref") != expected.branch.removeprefix("refs/heads/")
            or not self._same_repository(head.get("repo"), expected)
            or not isinstance(base, dict)
            or base.get("ref") != default_branch
            or expected.branch == "refs/heads/" + default_branch
            or not self._same_repository(base.get("repo"), expected)
        ):
            return None
        return f"github:{expected.repository_id}:pr:{pr}:merge:{merge_sha}"


@dataclass(frozen=True)
class _OwnerState:
    identity: Identity
    repo_root: str
    device: int
    inode: int
    release_hash: str
    status: str = "active"
    producer_succeeded: bool = False
    release_cap: str | None = None
    release_id: str | None = None
    delivery_id: str | None = None
    pr: int | None = None
    branch_disposition: str = "local_retained;remote_retained"
    retirement_event_id: str | None = None
    retirement_intent_sha256: str | None = None
    schema_version: int = 1


def _creator_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate creator history key")
        result[key] = value
    return result


def _owner_decode(raw: bytes) -> _OwnerState:
    try:
        value = json.loads(raw, object_pairs_hook=_creator_pairs)
        if not isinstance(value, dict) or set(value) != {f.name for f in fields(_OwnerState)}:
            raise ValueError("Unexpected creator fields")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise ValueError("Unsupported creator schema")
        if value["branch_disposition"] not in ("local_retained;remote_retained", "local_retired;remote_retained"):
            raise ValueError("Invalid branch result")
        ident = value.pop("identity")
        if not isinstance(ident, dict) or set(ident) != {f.name for f in fields(Identity)}:
            raise ValueError("Invalid creator identity")
        if any(not isinstance(v, str) for k, v in ident.items() if k != "repository_id"):
            raise ValueError("Invalid creator identity values")
        identity = Identity(**ident)
        if any(type(value[k]) is not int or value[k] < 0 for k in ("device", "inode")):
            raise ValueError("Invalid filesystem identity")
        if any(not isinstance(value[k], str) or not value[k] for k in ("repo_root", "release_hash", "status", "branch_disposition")):
            raise ValueError("Invalid creator value")
        if not Path(value["repo_root"]).is_absolute() or ".." in Path(value["repo_root"]).parts:
            raise ValueError("Invalid creator root")
        if not re.fullmatch(r"[0-9a-f]{64}", value["release_hash"]) or value["status"] not in ("creating", "active", "producer_unknown", "released", "retired"):
            raise ValueError("Invalid creator state")
        if type(value["producer_succeeded"]) is not bool:
            raise ValueError("Invalid producer result")
        if any(
            value[k] is not None and (not isinstance(value[k], str) or not value[k])
            for k in ("release_cap", "release_id", "delivery_id", "retirement_event_id", "retirement_intent_sha256")
        ):
            raise ValueError("Invalid creator proof")
        if value["pr"] is not None and (type(value["pr"]) is not int or value["pr"] <= 0):
            raise ValueError("Invalid creator PR")
        state = _OwnerState(identity=identity, **value)
        _require_owner_proofs(state)
        return state
    except (ValueError, TypeError, KeyError) as exc:
        raise StateError("Creator history unavailable or invalid") from exc


def _require_owner_proofs(state: _OwnerState) -> None:
    if state.status == "retired" and (
        not state.retirement_event_id
        or not state.delivery_id
        or not state.retirement_intent_sha256
        or not re.fullmatch(r"[0-9a-f]{64}", state.retirement_intent_sha256)
    ):
        raise ValueError("Missing retirement receipt binding")
    if state.status in ("creating", "active", "producer_unknown") and any(
        getattr(state, key) is not None for key in ("release_cap", "release_id", "delivery_id", "pr", "retirement_event_id", "retirement_intent_sha256")
    ):
        raise ValueError("Inconsistent unreleased creator history")
    if state.status in ("released", "retired") and not _released(state):
        raise ValueError("Invalid owner release")


def _cap_hash(capability: str) -> str:
    return hashlib.sha256(capability.encode()).hexdigest()  # noqa: TID251 -- owner release capability integrity, not charter hashing.


def _released(state: _OwnerState) -> bool:
    return bool(
        state.producer_succeeded
        and state.release_cap
        and secrets.compare_digest(_cap_hash(state.release_cap), state.release_hash)
        and state.release_id
        and state.pr
    )


def _git_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0"})
    return env


def _nested_state(root: Path) -> tuple[bool, bool]:
    """Return nested repository / complete bounded traversal, without following links."""
    pending, seen = [root], 0
    while pending:
        path = pending.pop()
        with os.scandir(path) as entries:
            for entry in entries:
                seen += 1
                if seen > 10000:
                    return False, False
                if path == root and entry.name == ".git":
                    continue
                if entry.name == ".git" or (
                    entry.is_dir(follow_symlinks=False) and (Path(entry.path) / "HEAD").exists() and (Path(entry.path) / "objects").is_dir()
                ):
                    return True, True
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
    return False, True


class ManagedGitCreator:
    """Creator-owned linked checkout with serialized, explicitly released leases.

    The synchronous producer context is a cooperative ownership contract, not a
    sandbox for arbitrary processes. It fences participating lease holders;
    leaving a caller block alone does not certify a joined producer. Only the
    owned runner records joined success. Existing workspaces cannot be adopted.
    Worker restoration does not recover the in-memory release capability.
    """

    def __init__(
        self,
        store: StateStore,
        token: str,
        *,
        delivery: GitHubDelivery,
        on_complete: Callable[[Completion], None],
        capability: str | None = None,
        operation_timeout: float = 30.0,
    ) -> None:
        if not re.fullmatch(r"[0-9a-f]{32}", token):
            raise ValueError("Invalid creator token")
        if not math.isfinite(operation_timeout) or operation_timeout <= 0:
            raise ValueError("Finite positive creator operation timeout required")
        self.operation_timeout = operation_timeout
        self.store, self.token, self.delivery, self.on_complete = store, token, delivery, on_complete
        self._capability = capability
        self._pid = os.getpid()
        self._unconfirmed_producer = False
        self._held: tuple[int, int] | None = None
        self._last_delivery: str | None = None
        info = store.root.lstat()
        self._root_identity = (info.st_dev, info.st_ino)
        self.authority_id = "registered-git:" + token

    @property
    def _path(self) -> Path:
        return self.store.root / f"creator-{self.token}.json"

    def _check_root(self) -> None:
        root = self.store.root
        if any(p.is_symlink() for p in (root, *root.parents)):
            raise StateError("Creator root changed")
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != self._root_identity or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise StateError("Creator root changed")

    def _read(self) -> _OwnerState:
        self._check_root()
        state = _owner_decode(self.store.read_private(self._path.name, limit=65536))
        if state.identity.workspace_generation != self.token:
            raise StateError("Creator generation does not match registration")
        return state

    def _write(self, state: _OwnerState) -> None:
        self._check_root()
        raw = json.dumps(asdict(state), sort_keys=True, separators=(",", ":")).encode()
        _owner_decode(raw)
        if self._path.exists() or self._path.is_symlink():
            if state.status == "creating":
                raise StateError("Creator registration already exists")
            self._read()
        atomic_write(self._path, raw, durable=True, expected_parent=self._root_identity)

    @contextmanager
    def _fence(self) -> Iterator[None]:
        self._check_root()
        with machine_file_lock(self.store.root / f"creator-{self.token}.lock", blocking=True, timeout_s=self.store.timeout, private=True):
            self._check_root()
            yield

    @classmethod
    @process_budget(30.0)
    def create(
        cls,
        store: StateStore,
        *,
        repo_root: Path,
        path: Path,
        branch: str,
        repository: str,
        repository_id: int,
        delivery: GitHubDelivery,
        on_complete: Callable[[Completion], None],
    ) -> ManagedGitCreator:
        store.read()
        repo_root, path = repo_root.absolute(), path.absolute()
        if path.exists() or any(p.is_symlink() for p in (path, *path.parents)) or ".." in path.parts:
            raise StateError("Creator requires a new non-symlinked workspace")
        if ProtectionPolicy.resolve(repo_root).is_protected_target(branch, primary_branch=resolve_primary_branch(repo_root, bias=False), allow_bypass=False):
            raise StateError("Protected branch cannot be creator-owned")
        env = _git_env()
        common = inspect_git_common_dir(repo_root, env=env, timeout=5)
        observed = discover_workspaces({repository: repository_id}, [repo_root], max_depth=0)["workspaces"]
        if not any(row["path"] == str(repo_root) and row["common_dir"] == str(common) for row in observed):
            raise StateError("Verified repository origin required")
        run_git(repo_root, "check-ref-format", "--branch", branch, env=env, timeout=5)
        head = run_git(repo_root, "rev-parse", "HEAD", env=env, timeout=5).stdout.decode().strip()
        token, capability = secrets.token_hex(16), secrets.token_hex(32)
        owner = cls(store, token, delivery=delivery, on_complete=on_complete, capability=capability)
        with owner._fence():
            ident = Identity(repository_id, repository, str(common), str(path), head, "refs/heads/" + branch, token, secrets.token_hex(16))
            pending = _OwnerState(ident, str(repo_root), 0, 0, _cap_hash(capability), status="creating")
            # Custody precedes effects. A crash keeps an explicit creation-unknown
            # record; matching path/branch alone never adopts an ambiguous orphan.
            owner._write(pending)
            run_git(repo_root, "worktree", "add", "-b", branch, str(path), head, env=env, timeout=5)
            info = path.lstat()
            owner._write(replace(pending, device=info.st_dev, inode=info.st_ino, status="active"))
        return owner

    @property
    def identity(self) -> Identity:
        return self._read().identity

    @property
    def branch_disposition(self) -> str:
        return self._read().branch_disposition

    def _fresh(self, state: _OwnerState) -> Identity:
        path, expected = Path(state.identity.path), state.identity
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise StateError("Workspace identity changed")
        info = path.lstat()
        if (info.st_dev, info.st_ino) != (state.device, state.inode):
            raise StateError("Workspace identity changed")
        env = _git_env()
        if str(inspect_git_common_dir(path, env=env, timeout=5)) != expected.common_dir:
            raise StateError("Workspace store changed")
        raw = run_git(Path(state.repo_root), "worktree", "list", "--porcelain", "-z", env=env, timeout=5).stdout
        matches = [row for row in parse_worktree_records(raw) if str(row.path) == expected.path]
        if len(matches) != 1 or matches[0].branch != expected.branch or matches[0].head is None:
            raise StateError("Workspace registry identity changed")
        return replace(expected, head=matches[0].head)

    @contextmanager
    def producer(self) -> Iterator[Path]:
        if os.getpid() != self._pid or not self._capability or self._unconfirmed_producer:
            raise StateError("Creator producer authority unavailable")
        with self._fence(), process_budget(self.operation_timeout):
            state = self._read()
            if state.status != "active":
                raise StateError("Creator generation released")
            ident = replace(self._fresh(state), lease_generation=secrets.token_hex(16))
            state = replace(state, identity=ident, producer_succeeded=False)
            self._write(state)
            yield Path(ident.path)
            current = self._read()
            self._write(replace(current, identity=self._fresh(current)))

    def run_producer(self, argv: list[str], *, timeout: float) -> None:
        """Own, bound and join one foreground producer while admission is fenced.

        This POSIX runner supports cooperative foreground jobs, not detached or
        scheduled producers. A failed/timed-out/remaining group durably fences
        the generation as producer_unknown; cleanup cannot infer its release.
        Child output is not retained or surfaced by the lifecycle channel.
        """
        if os.name != "posix" or not math.isfinite(timeout) or timeout <= 0 or timeout > self.operation_timeout:
            raise StateError("Bounded POSIX producer ownership required")
        if not argv or len(argv) > 256 or any(not isinstance(arg, str) or "\0" in arg for arg in argv):
            raise ValueError("Explicit producer argument vector required")
        with self.producer() as path:
            state = self._read()
            self._unconfirmed_producer = True
            process = subprocess.Popen(
                argv,
                cwd=path,
                env={**_git_env(), "SPEC_KITTY_LIFECYCLE_RESULT": str(self.store.root / f"producer-{self.token}-result.json")},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            successful = False
            try:
                successful = process.wait(timeout=timeout) == 0
                # A foreground parent returning while its own group still runs
                # is not joined producer completion. No snapshot grants release.
                try:
                    os.killpg(process.pid, 0)
                    successful = False
                except ProcessLookupError:
                    pass
                if not successful:
                    raise StateError("Owned producer did not complete successfully")
            except subprocess.TimeoutExpired as exc:
                raise StateError("Owned producer timed out") from exc
            finally:
                if not successful:
                    try:
                        self._write(replace(state, status="producer_unknown", producer_succeeded=False))
                    finally:
                        self._stop_producer(process)
                if process.returncode is None:
                    self._stop_producer(process)
            self._write(replace(state, identity=self._fresh(state), producer_succeeded=True))
            self._unconfirmed_producer = False

    @staticmethod
    def _stop_producer(process: subprocess.Popen[bytes]) -> None:
        # wait()/poll() end PID/PGID custody. Never signal a numeric group after
        # reaping its leader: a later process may have reused that identifier.
        if process.returncode is not None:
            return
        with suppress(ProcessLookupError):
            signal_owned_process_tree(process, force=False)
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            with suppress(ProcessLookupError):
                signal_owned_process_tree(process, force=True)
            process.wait(timeout=0.5)
        # Once wait reaps the leader, signalling authority ends. A remaining
        # or escaped producer is unconfirmed; durable producer_unknown retains it.

    def complete(self, *, pr: int | None = None) -> None:
        if os.getpid() != self._pid or not self._capability or self._unconfirmed_producer:
            raise StateError("Creating owner release capability or producer confirmation unavailable")
        if pr is not None and (type(pr) is not int or pr <= 0):
            raise ValueError("Positive PR number required")
        with self._fence(), process_budget(self.operation_timeout):
            state = self._read()
            if state.status != "active":
                raise StateError("Creator generation released")
            if not state.producer_succeeded:
                raise StateError("Joined successful producer required")
            if pr is None:
                try:
                    result = json.loads(self.store.read_private(f"producer-{self.token}-result.json", limit=4096), object_pairs_hook=_creator_pairs)
                    if not isinstance(result, dict) or set(result) != {"pr"} or type(result["pr"]) is not int or result["pr"] <= 0:
                        raise ValueError("Invalid producer PR")
                    pr = result["pr"]
                except (ValueError, OSError, StateError, NoFollowPathError) as exc:
                    raise StateError("Joined producer PR result unavailable or invalid") from exc
            ident = self._fresh(state)
            if ident != state.identity or not secrets.compare_digest(_cap_hash(self._capability), state.release_hash):
                raise StateError("Creator release identity changed")
            # Release is independent of accepted delivery. The foreground CLI
            # may exit now; worker/startup evidence can establish delivery later.
            state = replace(state, status="released", release_cap=self._capability, release_id=secrets.token_hex(16), pr=pr)
            self._write(state)
        # Enqueue a hint after releasing admission. The durable release remains
        # available to startup recovery if enqueue fails or this process exits.
        self.on_complete(Completion(secrets.token_hex(16), ident, self.authority_id))

    @contextmanager
    def hold(self, identity: Identity) -> Iterator[None]:
        with self._fence(), process_budget(self.operation_timeout):
            if self._read().identity != identity:
                raise StateError("Creator hold identity changed")
            self._held = (os.getpid(), threading.get_ident())
            self._last_delivery = None
            try:
                yield
            finally:
                self._held = None
                self._last_delivery = None

    def _require_hold(self) -> None:
        if self._held != (os.getpid(), threading.get_ident()):
            raise StateError("Creator hold required")

    def inspect(self, identity: Identity) -> Evidence:
        self._require_hold()
        state = self._read()
        if identity.workspace_generation != state.identity.workspace_generation:
            raise StateError("Creator generation changed")
        fresh = self._fresh(state)
        path = Path(fresh.path)
        entries = status_entries(path, untracked="all", ignored=True, optional_locks=False, env=_git_env(), timeout=5)
        nested, complete = _nested_state(path)
        receipt = self.delivery.verify(fresh, state.pr) if state.pr and _released(state) else None
        if receipt is not None and receipt != state.delivery_id:
            self._write(replace(state, delivery_id=receipt))
        self._last_delivery = receipt
        return Evidence(
            fresh,
            path == Path(state.repo_root) or (path / ".git").is_dir(),
            not entries,
            any(row.is_ignored for row in entries),
            nested,
            state.status == "active",
            state.status == "released",
            state.release_id if _released(state) else None,
            receipt,
            fresh.head if receipt else None,
            complete,
        )

    def retire(self, intent: Operation) -> Result:
        self._require_hold()
        identity, event_id = intent.identity, intent.event_id
        state = self._read()
        if not event_id:
            raise StateError("Retirement event identity required")
        if state.status != "released" or identity != self._fresh(state) or not _released(state):
            return Result("retained", "creator_release_changed")
        if (
            not self._last_delivery
            or self._last_delivery != state.delivery_id
            or intent.creator_id != self.authority_id
            or intent.release_id != state.release_id
            or intent.delivery_id != state.delivery_id
            or intent.status != "intent"
        ):
            return Result("retained", "authorizing_intent_changed")
        guarded_worktree_remove(Path(identity.path), retain=False, is_residue=lambda _: False, env=_git_env(), preserve_ignored=True)
        disposition = "local_retained;remote_retained"
        try:
            branch = identity.branch.removeprefix("refs/heads/")
            if not ProtectionPolicy.resolve(Path(state.repo_root)).is_protected_target(
                branch, primary_branch=resolve_primary_branch(Path(state.repo_root), bias=False), allow_bypass=False
            ):
                delete_branch_ref(Path(state.repo_root), branch, identity.head, env=_git_env())
                disposition = "local_retired;remote_retained"
        except (RefDeleteError, OSError):
            pass
        self._write(
            replace(
                state, status="retired", branch_disposition=disposition, retirement_event_id=event_id, retirement_intent_sha256=intent.authorization_fingerprint()
            )
        )
        return Result("retired", "creator_confirmed;" + disposition)

    def recover(self, intent: Operation) -> Recovered:
        self._require_hold()
        state = self._read()
        result = Result("unknown", "creator_effect_unconfirmed")
        if (
            state.status != "retired"
            or state.identity != intent.identity
            or state.retirement_event_id != intent.event_id
            or intent.creator_id != self.authority_id
            or state.release_id != intent.release_id
            or state.delivery_id != intent.delivery_id
            or state.retirement_intent_sha256 != intent.authorization_fingerprint()
        ):
            return Recovered(intent, result)
        path = Path(intent.identity.path)
        if any(p.is_symlink() for p in (path, *path.parents)):
            return Recovered(intent, result)
        try:
            path.lstat()
            return Recovered(intent, result)
        except FileNotFoundError:
            pass
        raw = run_git(Path(state.repo_root), "worktree", "list", "--porcelain", "-z", env=_git_env(), timeout=5).stdout
        if not any(str(row.path) == intent.identity.path for row in parse_worktree_records(raw)):
            result = Result("retired", "creator_receipt_confirmed;" + state.branch_disposition)
        return Recovered(intent, result)
