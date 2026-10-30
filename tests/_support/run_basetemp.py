"""Per-run pytest temp root — retire the shared ``pytest-of-<user>`` numbered-dir
tree's unbounded growth and stale-lock debt.

**What this is NOT: a fix for #63's crash mechanism.** An earlier version of
this module claimed the ``OSError: could not create numbered dir with prefix
test_* ... after 10 tries`` crash in #63 (a different xdist worker each run) was
cross-run contention in :func:`_pytest.pathlib.make_numbered_dir` and its
cleanup wrapper (sibling scans, symlink locks, old-root pruning). A
controller-qa audit on this fix falsified that: every #63 crash names a
*worker* basetemp (``pytest-0/popen-gw<N>``) — an already-resolved
``_given_basetemp`` — and ``TempPathFactory.getbasetemp`` takes the
given-basetemp branch there (plain ``rm_rf`` + ``mkdir``), never the
numbered-dir path with its locks and pruning. Exactly one process ever writes
that directory, so there is no sibling to race. ``_pytest/pathlib.py``'s
numbered-dir ``mkdir`` also swallows *any* ``Exception``, so the "after 10
tries" message fires identically for ENOSPC / EDQUOT / inode exhaustion as it
would for a real collision — the message names no cause. CI reproduced the
crash on a head that already carried this fix, confirming it does not touch
the real driver: ``pytest.ini`` set no ``tmp_path_retention_policy``, so
pytest's ``all`` default keeps *every* test's ``tmp_path`` — pass or fail —
alive for the whole session, and across the ~40k tests of ``make test-full``
that is enough to exhaust the runner's temp filesystem. The fix for that is
``tmp_path_retention_policy = failed`` in ``pytest.ini``, not this module.

**What this is.** A genuinely private basetemp per invocation, under
``<temproot>/spk-t2/run-<pid>-<nonce>``:

* **Private per run** — each producer exclusively reserves its leaf and writes
  a private owner record before test execution. PID reuse cannot select an
  earlier run's evidence.
* **Retained until owner/runtime release** — even ``ExitCode.OK`` does not release
  a child or service holding the exact leaf. The exit callback retains an
  explicit owner/runtime release obligation and records the pytest outcome.
  It retains failures, errors, or an interruption too; neither a successful
  test outcome nor a negative process snapshot is deletion authority.
* **Other runs retained** — startup never retires another run's tree. Age,
  silence or an apparently dead PID is not release authority. Eligible cleanup
  remains an independently verified owner operation through the existing
  lifecycle workflow, not an inference made by this test launcher.

xdist needs no separate handling: the controller's factory resolves this
basetemp during worker setup and hands each worker ``<basetemp>/popen-gwN``
(``xdist.workermanage``), so workers nest exactly as they would under a CLI
``--basetemp``. An explicit ``--basetemp`` on the command line still wins
untouched — whoever passes one owns its lifecycle, including its persistence
(default retention does not apply to explicit basetemps).

Pass an explicit ``--basetemp`` to opt out of both the private root and the
outcome-gated reap.
"""

from __future__ import annotations

import atexit
import contextlib
import json
import hashlib
import os
import shutil
import stat
import tempfile
import socket
import threading
import struct
import uuid
from collections.abc import Iterable
from functools import partial
from pathlib import Path
from typing import Any, Protocol

import pytest
import psutil
from _pytest.compat import get_user_id
from kernel.yaml_io import _refuse_privileged_metadata
from specify_cli.core.process_liveness import capture_creation_time_baseline

#: Sibling of WP04's ``spec-kitty-test-homes`` under the resolved temproot —
#: A suite namespace, not blanket ownership of other producers' contents.
#: Each invocation owns only its exclusively reserved leaf.
# A distinct, shorter v2 namespace also keeps old launchers' unsafe age sweep
# away from new retained evidence, without lengthening Unix-socket paths.
RUN_TMP_ROOT_NAME = "spk-t2"

#: Observational inventory threshold only; never deletion/release authority.
STALE_RUN_MAX_AGE_S = 24 * 60 * 60

#: ``config`` attribute holding this run's :class:`_SessionOutcome`. Set only
#: on the controller config that :func:`install_run_basetemp` actually
#: installed a private basetemp against — absent for xdist workers and for an
#: explicit ``--basetemp`` (whoever passes one owns its own lifecycle), so
#: :func:`mark_session_outcome` is a safe no-op in both cases.
_OUTCOME_CONFIG_ATTR = "_spec_kitty_run_basetemp_outcome"

_ENCLOSURE_ENV = "SPEC_KITTY_TEST_ENCLOSURE"
_ENCLOSURE_ATTR = "_spec_kitty_run_enclosure"
_ADMITTED_BASETEMP_ATTR = "_spec_kitty_admitted_basetemp"
_WORKER_ENCLOSURE = "spec_kitty_run_enclosure"
_ACTIVE_ENCLOSURE: _RunEnclosure | _EnclosureView | None = None


def _birth(pid: int) -> str:
    value = capture_creation_time_baseline(pid)
    if not isinstance(value, str):
        raise OSError("Cannot verify test producer generation")
    return value


def _raw_temproot() -> Path:
    # gettempdir() may write while choosing its fallback. Admission precedes it.
    value = next((os.environ[k] for k in ("PYTEST_DEBUG_TEMPROOT", "TMPDIR", "TEMP", "TMP") if os.environ.get(k)), None)
    if value is None:
        value = tempfile.tempdir or ("/tmp" if os.name == "posix" else None)
    if not isinstance(value, str):
        raise OSError("Select a test temporary directory before admission")
    return Path(value).absolute()


def _markers(path: Path, boundary: Path | None = None) -> None:
    resolved = path.resolve()
    for parent in (resolved, *resolved.parents):
        if boundary is not None and not parent.is_relative_to(boundary):
            break
        for name in (".git", ".kittify"):
            marker = parent / name
            if not (marker.exists() or marker.is_symlink()):
                continue
            if boundary is None:
                raise OSError(f"Foreign configuration ancestor: {marker}")
            if not (marker.is_file() or marker.is_dir() or marker.is_symlink()):
                raise OSError("Unsupported test configuration marker type")
            if marker.is_symlink() and not marker.resolve().is_relative_to(boundary):
                raise OSError("Configuration marker escapes the test enclosure")
            if name == ".git" and marker.is_file():
                if marker.stat().st_size > 4096:
                    raise OSError("Oversized test Git marker")
                text = marker.read_text().strip()
                if text.startswith("gitdir:"):
                    target = (parent / text[7:].strip()).resolve()
                    if not target.is_relative_to(boundary):
                        raise OSError("Git directory escapes the test enclosure")


def _security_sid(value: bytes, offset: int) -> str:
    if offset < 0 or offset + 8 > len(value):
        raise OSError("Invalid security identifier")
    revision, count = value[offset : offset + 2]
    end = offset + 8 + count * 4
    if count > 15 or end > len(value):
        raise OSError("Invalid security identifier length")
    authority = int.from_bytes(value[offset + 2 : offset + 8], "big")
    parts = struct.unpack_from("<" + "I" * count, value, offset + 8)
    return "-".join(map(str, ("S", revision, authority, *parts)))


def _windows_security(path: Path) -> str:
    """Read and check native owner/DACL; never infer privacy from Windows mode bits."""
    import ctypes
    from ctypes import wintypes

    library = getattr(ctypes, "WinDLL", None)
    if library is None:
        raise OSError("Native Windows security inspection is unavailable")
    advapi = library("advapi32", use_last_error=True)
    kernel = library("kernel32", use_last_error=True)
    advapi.GetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.GetFileSecurityW.restype = wintypes.BOOL
    needed = wintypes.DWORD()
    advapi.GetFileSecurityW(str(path), 5, None, 0, ctypes.byref(needed))
    if not 20 <= needed.value <= 65536:
        raise OSError("Cannot inspect private test directory security")
    data = ctypes.create_string_buffer(needed.value)
    if not advapi.GetFileSecurityW(str(path), 5, data, len(data), ctypes.byref(needed)):
        raise OSError("Cannot read private test directory security")
    raw = data.raw[: needed.value]

    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.GetLengthSid.argtypes = [ctypes.c_void_p]
    advapi.GetLengthSid.restype = wintypes.DWORD
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise OSError("Cannot inspect current test token")
    try:
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not 8 <= size.value <= 65536:
            raise OSError("Invalid current test token")
        token_data = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token, 1, token_data, len(token_data), ctypes.byref(size)):
            raise OSError("Cannot read current test token")
        pointer = ctypes.cast(token_data, ctypes.POINTER(ctypes.c_void_p))[0]
        length = advapi.GetLengthSid(pointer)
        if not 8 <= length <= 68:
            raise OSError("Invalid current test identity")
        user = _security_sid(ctypes.string_at(pointer, length), 0)
    finally:
        if not kernel.CloseHandle(token):
            raise OSError("Test token close failed")
    allowed = {user, "S-1-5-18", "S-1-5-32-544"}
    _, _, control, owner, _, _, dacl = struct.unpack_from("<BBHIIII", raw)
    if not control & 4 or not dacl or _security_sid(raw, owner) not in allowed or dacl + 8 > len(raw):
        raise OSError("Test directory is not privately owned")
    _, _, size, count, _ = struct.unpack_from("<BBHHH", raw, dacl)
    end = dacl + size
    offset = dacl + 8
    if end > len(raw):
        raise OSError("Invalid test directory ACL")
    for _ in range(count):
        kind, flags, size = struct.unpack_from("<BBH", raw, offset)
        if size < 12 or offset + size > end or kind not in (0, 1):
            raise OSError("Unsupported test directory ACL")
        identity = _security_sid(raw[: offset + size], offset + 8)
        if kind == 0 and identity not in allowed and not (identity == "S-1-3-0" and flags & 8):
            raise OSError("Test directory grants access outside the current user")
        offset += size
    return hashlib.sha256(raw).hexdigest()  # noqa: TID251 - native permission preimage, not charter data.


def _private_identity(path: Path) -> list[int | str | None]:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise OSError("Test enclosure is not a physical directory")
    if os.name == "posix" and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
        raise OSError("Test enclosure must be private and owned by the current user")
    _refuse_privileged_metadata(path)
    return [info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, _windows_security(path) if os.name == "nt" else None]


def _connection_owned(process: psutil.Process, local_port: int, remote_port: int | None = None) -> bool:
    return any(
        row.laddr
        and row.laddr.ip == "127.0.0.1"
        and row.laddr.port == local_port
        and (row.status == psutil.CONN_LISTEN if remote_port is None else row.raddr and row.raddr.port == remote_port)
        for row in process.net_connections(kind="tcp")
    )


def _frame(connection: socket.socket) -> dict[str, Any]:
    data = b""
    while not data.endswith(b"\n") and len(data) < 16384:
        part = connection.recv(16384 - len(data))
        if not part:
            raise OSError("Incomplete test enclosure observation")
        data += part
    value = json.loads(data)
    if not data.endswith(b"\n") or not isinstance(value, dict):
        raise OSError("Invalid test enclosure observation")
    return value


class _RunEnclosure:
    """The live controller owns this context; projections never reconstruct it."""

    def __init__(self, root: Path, allowed: list[Path], tmp_parent: Path) -> None:
        self.root = root.resolve()
        self.allowed = [path.resolve() for path in allowed]
        self.tmp_parent = tmp_parent.resolve()
        if not 1 <= len(self.allowed) <= 3 or any(not path.is_relative_to(self.root) for path in self.allowed):
            raise OSError("Test scope escapes its physical enclosure")
        if not any(self.tmp_parent.is_relative_to(path) for path in self.allowed):
            raise OSError("Test temporary allocation escapes its fixed scope")
        self.pid = os.getpid()
        self.birth = _birth(self.pid)
        self.run_id = uuid.uuid4().hex
        self.identity: list[int | str | None] | None = None
        self.record = self.root / (".e-" + self.run_id + ".json")
        self.fd: int | None = None
        self.listener: socket.socket | None = None
        self.thread: threading.Thread | None = None
        self.stop = threading.Event()
        self.closed = False

    def open(self) -> None:
        self.identity = _private_identity(self.root)
        self.fd = os.open(self.record, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        os.chmod(self.record, 0o600)
        body = json.dumps(
            {
                "owner_pid": self.pid,
                "generation": self.birth,
                "run_id": self.run_id,
                "root": str(self.root),
                "purpose": "Source test-resource enclosure; not cleanup authority",
                "next_action": "retain until owning producer and runtime dependencies are released",
            }
        ).encode()
        with os.fdopen(os.dup(self.fd), "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        self.record_identity = os.fstat(self.fd)
        self.listener = socket.socket()
        self.listener.settimeout(0.2)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(16)
        self.thread = threading.Thread(target=self._serve, daemon=False)
        self.thread.start()

    def current(self) -> None:
        if self.closed or self.fd is None or _birth(self.pid) != self.birth or _private_identity(self.root) != self.identity:
            raise OSError("Test enclosure is stale or changed")
        actual = self.record.lstat()
        held = os.fstat(self.fd)
        fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")
        if any(getattr(actual, k) != getattr(held, k) or getattr(held, k) != getattr(self.record_identity, k) for k in fields):
            raise OSError("Test enclosure reservation changed")

    def check(self, path: Path) -> None:
        self.current()
        if not any(path.resolve().is_relative_to(prefix) for prefix in self.allowed):
            raise OSError("Test resource escapes the admitted enclosure")
        _markers(path, self.root)
        for parent in (path.resolve(), *path.resolve().parents):
            if not parent.is_relative_to(self.root):
                break
            if any((parent / name).exists() or (parent / name).is_symlink() for name in (".git", ".kittify")) and not any(
                parent.is_relative_to(prefix) for prefix in self.allowed
            ):
                raise OSError("Configuration marker is outside this run's fixed scope")

    def projection(self) -> dict[str, Any]:
        self.current()
        if self.listener is None:
            raise OSError("Test enclosure transport is not open")
        return {"schema": 1, "pid": self.pid, "birth": self.birth, "run_id": self.run_id, "port": self.listener.getsockname()[1]}

    def _serve(self) -> None:
        listener = self.listener
        if listener is None:
            raise OSError("Test enclosure transport is not open")
        while not self.stop.is_set():
            try:
                connection, peer = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                if self.stop.is_set():
                    return
                raise
            with connection:
                connection.settimeout(1)
                response: dict[str, Any] = {"ok": False}
                try:
                    request = _frame(connection)
                    if set(request) != {"pid", "birth", "run_id", "challenge", "path"} or request["run_id"] != self.run_id:
                        raise OSError("Invalid test enclosure request")
                    pid = request["pid"]
                    if type(pid) is not int or pid <= 0 or _birth(pid) != request["birth"]:
                        raise OSError("Invalid test requester generation")
                    process = psutil.Process(pid)
                    if pid != self.pid and self.pid not in [p.pid for p in process.parents()]:
                        raise OSError("Test requester is not a real descendant")
                    if not _connection_owned(process, peer[1], listener.getsockname()[1]):
                        raise OSError("Test requester does not own this connection")
                    self.check(Path(request["path"]))
                    response = {
                        "ok": True,
                        "challenge": request["challenge"],
                        "run_id": self.run_id,
                        "root": str(self.root),
                        "identity": self.identity,
                        "allowed": [str(path) for path in self.allowed],
                        "tmp_parent": str(self.tmp_parent),
                    }
                except (OSError, ValueError, TypeError, KeyError, psutil.Error):
                    pass
                with contextlib.suppress(OSError):
                    connection.sendall(json.dumps(response).encode() + b"\n")

    def close(self) -> None:
        global _ACTIVE_ENCLOSURE
        self.closed = True
        self.stop.set()
        if self.listener is not None:
            self.listener.close()
        if self.thread is not None:
            self.thread.join(timeout=2)
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        if self.thread is not None and self.thread.is_alive():
            raise OSError("Test enclosure thread closeout is unconfirmed")
        if _ACTIVE_ENCLOSURE is self:
            _ACTIVE_ENCLOSURE = None
        # Files and run evidence remain; closing transport grants no deletion.


class _EnclosureView:
    def __init__(self, projection: dict[str, Any]) -> None:
        if set(projection) != {"schema", "pid", "birth", "run_id", "port"} or type(projection["schema"]) is not int or projection["schema"] != 1:
            raise OSError("Invalid test enclosure projection")
        if type(projection["pid"]) is not int or projection["pid"] <= 0 or type(projection["port"]) is not int or not 0 < projection["port"] < 65536:
            raise OSError("Invalid test enclosure endpoint")
        if (
            not isinstance(projection["birth"], str)
            or not 1 <= len(projection["birth"]) <= 128
            or not isinstance(projection["run_id"], str)
            or len(projection["run_id"]) != 32
            or any(c not in "0123456789abcdef" for c in projection["run_id"])
        ):
            raise OSError("Invalid test enclosure generation")
        self.value = projection
        self.pid = os.getpid()
        self.root: Path | None = None

    def projection(self) -> dict[str, Any]:
        return self.value.copy()

    def check(self, path: Path) -> None:
        value = self.value
        owner = psutil.Process(value["pid"])
        if _birth(owner.pid) != value["birth"] or (owner.pid != os.getpid() and owner.pid not in [p.pid for p in psutil.Process().parents()]):
            raise OSError("No live enclosing test producer")
        if not _connection_owned(owner, value["port"]):
            raise OSError("Enclosing test producer does not own the endpoint")
        challenge = uuid.uuid4().hex
        with socket.create_connection(("127.0.0.1", value["port"]), timeout=2) as connection:
            connection.sendall(
                json.dumps(
                    {"pid": os.getpid(), "birth": _birth(os.getpid()), "run_id": value["run_id"], "challenge": challenge, "path": str(path.absolute())}
                ).encode()
                + b"\n"
            )
            response = _frame(connection)
            if not response.get("ok") or response.get("challenge") != challenge or response.get("run_id") != value["run_id"]:
                raise OSError("Test enclosure observation refused")
            if _birth(owner.pid) != value["birth"] or not _connection_owned(owner, value["port"]):
                raise OSError("Enclosing test producer changed during observation")
        root = Path(response["root"])
        allowed = response["allowed"]
        if not isinstance(allowed, list) or not 1 <= len(allowed) <= 3 or any(not isinstance(p, str) or not Path(p).is_absolute() for p in allowed):
            raise OSError("Invalid test enclosure scope observation")
        if (
            _private_identity(root) != response["identity"]
            or not path.resolve().is_relative_to(root)
            or not any(path.resolve().is_relative_to(Path(p)) for p in allowed)
        ):
            raise OSError("Test enclosure physical identity mismatch")
        _markers(path, root)
        self.root = root
        self.tmp_parent = Path(response["tmp_parent"])
        if not self.tmp_parent.is_relative_to(root) or not any(self.tmp_parent.is_relative_to(Path(p)) for p in allowed):
            raise OSError("Invalid test temporary allocation parent")


class _WorkerHandoff(Protocol):
    workerinput: dict[str, Any]


class _EnclosureHandoff:
    def __init__(self, context: _RunEnclosure | _EnclosureView) -> None:
        self.context = context

    @pytest.hookimpl(optionalhook=True)
    def pytest_configure_node(self, node: _WorkerHandoff) -> None:
        node.workerinput[_WORKER_ENCLOSURE] = self.context.projection()


def _inherited_enclosure(config: pytest.Config) -> _RunEnclosure | _EnclosureView | None:
    context = _ACTIVE_ENCLOSURE
    if context is not None and context.pid != os.getpid():
        context = None
    if context is None:
        worker = getattr(config, "workerinput", None)
        projection = worker.get(_WORKER_ENCLOSURE) if worker is not None else os.environ.get(_ENCLOSURE_ENV)
        if worker is not None and projection is None:
            raise OSError("Worker has no real controller enclosure handoff")
        if projection is not None:
            try:
                if isinstance(projection, str) and len(projection.encode()) > 16384:
                    raise OSError("Oversized test enclosure projection")
                context = _EnclosureView(json.loads(projection) if isinstance(projection, str) else projection)
            except (TypeError, ValueError, KeyError) as error:
                raise OSError("Invalid test enclosure routing projection") from error
    return context


def _declared_config_path() -> Path | None:
    value = os.environ.get("SPEC_KITTY_HOME")
    return Path(value).absolute() if value else None


def _create_enclosure(config: pytest.Config, candidate: Path, explicit: str | None, debug_root: str | None) -> tuple[_RunEnclosure, Path | None]:
    _markers(candidate)
    if explicit:
        _markers(Path(explicit))
    if not hasattr(config, "add_cleanup"):
        raise OSError("A real controller or live parent enclosure is required")
    if explicit:
        root = Path(explicit).absolute().parent
    elif debug_root:
        root = candidate / RUN_TMP_ROOT_NAME
    else:
        root = candidate / ("e-" + uuid.uuid4().hex[:8])
    _markers(root)
    config_path = _declared_config_path()
    if config_path is not None:
        _markers(config_path)
        if not config_path.resolve().is_relative_to(root.resolve()):
            raise OSError("Inherited Source home override is outside the test enclosure")
    home_tmp = root / ("n-" + uuid.uuid4().hex[:8])
    namespace = candidate / RUN_TMP_ROOT_NAME if debug_root else home_tmp / RUN_TMP_ROOT_NAME
    admitted = Path(explicit) if explicit else run_basetemp_dir(root=namespace)
    selected = None if explicit else admitted
    allowed = [admitted, home_tmp]
    if config_path is not None:
        allowed.append(config_path)
    context = _RunEnclosure(root, allowed, home_tmp)
    config.add_cleanup(context.close)  # Before descriptor/thread birth.
    # Register closeout before any owned directory, descriptor or thread birth.
    if not root.exists():
        root.mkdir(mode=0o700, parents=True)
        root.chmod(0o700)
    context.open()
    return context, selected


def _admit_run_resources(config: pytest.Config) -> None:
    """Admit before HOME/temp effects; never treat a projection as authority."""
    global _ACTIVE_ENCLOSURE
    known = getattr(config, _ENCLOSURE_ATTR, None)
    if known is not None:
        known.check(Path(getattr(config, _ADMITTED_BASETEMP_ATTR, None) or config.option.basetemp or _raw_temproot()))
        if (config_path := _declared_config_path()) is not None:
            known.check(config_path)
        return
    candidate = _raw_temproot()
    explicit = getattr(config.option, "basetemp", None)
    debug_root = os.environ.get("PYTEST_DEBUG_TEMPROOT")
    requested = Path(explicit) if explicit else candidate / RUN_TMP_ROOT_NAME if debug_root else candidate
    selected = None
    context = _inherited_enclosure(config)
    if context is None:
        context, selected = _create_enclosure(config, candidate, explicit, debug_root)
        if explicit:
            requested = Path(explicit)
        elif selected is not None:
            requested = selected
        else:
            raise OSError("Controller did not select its admitted temporary path")
    context.check(requested)
    if (config_path := _declared_config_path()) is not None:
        context.check(config_path)
    _ACTIVE_ENCLOSURE = context
    setattr(config, _ENCLOSURE_ATTR, context)
    if hasattr(config, "add_cleanup"):
        home_tmp = (
            context.tmp_parent
            if selected is not None or isinstance(context, _RunEnclosure) and not context.tmp_parent.exists()
            else context.tmp_parent / ("n-" + uuid.uuid4().hex[:8])
        )
        context.check(home_tmp)
        home_tmp.mkdir(mode=0o700)
        home_tmp.chmod(0o700)
        environment = pytest.MonkeyPatch()
        config.add_cleanup(environment.undo)
        environment.setenv("TMPDIR", str(home_tmp))
        environment.setenv(_ENCLOSURE_ENV, json.dumps(context.projection()))
        environment.setattr(tempfile, "tempdir", str(home_tmp))
        if not explicit:
            if selected is None:
                namespace = candidate / RUN_TMP_ROOT_NAME if debug_root else home_tmp / RUN_TMP_ROOT_NAME
                selected = run_basetemp_dir(root=namespace)
                context.check(selected)
            setattr(config, _ADMITTED_BASETEMP_ATTR, str(selected))

        config.pluginmanager.register(_EnclosureHandoff(context), "spec-kitty-test-enclosure")


def admit_run_resources(config: pytest.Config) -> None:
    """Refuse unsafe admission before Source-managed HOME or temporary effects."""
    try:
        _admit_run_resources(config)
    except (OSError, ValueError, psutil.Error) as error:
        raise pytest.UsageError(f"Test resource admission refused: {error}") from error


class _SessionOutcome:
    """Test outcome for the exit record; never a runtime release capability."""

    def __init__(self) -> None:
        self.succeeded = False
        self.owner_pid = os.getpid()
        self.manifest: Path | None = None
        self.manifest_bytes: bytes | None = None


def mark_session_outcome(config: pytest.Config, *, succeeded: bool) -> None:
    """Record this run's pytest outcome without granting runtime release.

    Call from ``pytest_sessionfinish`` with ``succeeded=exitstatus ==
    pytest.ExitCode.OK``. A no-op if :func:`install_run_basetemp` never
    installed a reaper against *config* (xdist worker, or an explicit
    ``--basetemp``) — there is no installed outcome record.
    """
    outcome = getattr(config, _OUTCOME_CONFIG_ATTR, None)
    if outcome is not None:
        outcome.succeeded = succeeded


def temproot() -> Path:
    """The temp root this scheme lives under, honoring pytest's own override.

    Same resolution order as the default branch of
    ``TempPathFactory.getbasetemp``: ``PYTEST_DEBUG_TEMPROOT`` wins, then the
    platform temp dir (which itself honors ``TMPDIR``).
    """
    return Path(os.environ.get("PYTEST_DEBUG_TEMPROOT") or tempfile.gettempdir())


def run_tmp_root() -> Path:
    """The directory holding every run's private basetemp."""
    return temproot() / RUN_TMP_ROOT_NAME


def run_basetemp_dir(pid: int | None = None, *, root: Path | None = None) -> Path:
    """A fresh candidate, reserved exclusively by ``install_run_basetemp``.

    The PID is diagnostic only. A nonce prevents a later invocation from
    selecting and wiping a failed run's evidence after PID reuse.
    """
    return (root if root is not None else run_tmp_root()) / f"run-{pid if pid is not None else os.getpid()}-{uuid.uuid4().hex[:12]}"


def stale_run_dirs(
    root: Path,
    *,
    now: float,
    max_age_s: float = STALE_RUN_MAX_AGE_S,
) -> list[Path]:
    """Entries of *root* untouched for longer than *max_age_s*.

    This is observational only. It is not a liveness check or permission to
    delete anything, and installation never calls it to retire other runs.
    """
    cutoff = now - max_age_s
    stale: list[Path] = []
    try:
        entries = list(root.iterdir())
    except OSError:
        return stale
    for entry in entries:
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            continue  # vanished between iterdir and stat — not ours to judge
        if mtime < cutoff:
            stale.append(entry)
    return stale


def remove_run_dirs(dirs: Iterable[Path]) -> list[Path]:
    """Best-effort removal of *dirs*; returns the ones THIS call removed.

    The caller must independently own/release every supplied resource; age
    inventory is insufficient. This is never a startup sibling sweep.
    ``ignore_errors`` throughout: cleanup must never be the thing that turns a
    green run red. Inputs that are already absent are skipped — they were not
    removed by this call and are not reported.
    """
    removed: list[Path] = []
    for path in dirs:
        try:
            if not (path.exists() or path.is_symlink()):
                continue
        except OSError:
            continue  # unstattable — vanished mid-iteration, not ours to judge
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
        else:
            with contextlib.suppress(OSError):
                path.unlink()
        if not path.exists():
            removed.append(path)
    return removed


def _validate_existing_root(root: Path) -> None:
    """Apply the same owner/mode/symlink hardening pytest's own
    ``TempPathFactory.getbasetemp`` applies to its ``pytest-of-<user>``
    rootdir (:mod:`_pytest.tmpdir`) — ``root.mkdir(..., exist_ok=True)``
    accepts a pre-existing directory unchanged, so a predictable, shared
    temproot means whatever is already there (wrong owner, world-writable,
    or a symlink) would otherwise be trusted as-is (#77).

    Raises :class:`OSError` on a symlinked or wrong-owner root, matching
    pytest's fail-closed behavior. A verified owner root is restored to mode 0700 in place, including
    owner access removed by a restrictive caller umask.
    """
    uid = get_user_id()
    if uid is None:
        return  # platform can't tell us an owner (Windows) — nothing to check
    stat_follow_symlinks = os.stat not in os.supports_follow_symlinks
    root_stat = root.stat(follow_symlinks=stat_follow_symlinks)
    if stat.S_ISLNK(root_stat.st_mode):
        raise OSError(f"The temporary directory {root} is a symbolic link. Fix this and try again.")
    if root_stat.st_uid != uid:
        raise OSError(f"The temporary directory {root} is not owned by the current user. Fix this and try again.")
    if stat.S_IMODE(root_stat.st_mode) != 0o700:
        chmod_follow_symlinks = os.chmod not in os.supports_follow_symlinks
        root.chmod(0o700, follow_symlinks=chmod_follow_symlinks)


def install_run_basetemp(config: pytest.Config, now: float) -> None:
    """Point *config* at this run's private basetemp unless the user already did.

    Must run from ``pytest_configure``: the builtin tmpdir plugin snapshots
    ``config.option.basetemp`` into its ``TempPathFactory`` there, and xdist
    derives every worker's ``popen-gwN`` from the controller's factory value at
    worker setup. Controller-gated (``workerinput is None``) like the session
    outcome recorder — an xdist worker receives its own nested basetemp over the wire and
    must not second-guess it.
    """
    admit_run_resources(config)
    if getattr(config, "workerinput", None) is not None:
        return
    if config.option.basetemp:
        return

    admitted = getattr(config, _ADMITTED_BASETEMP_ATTR, None)
    root = Path(admitted).parent if admitted else run_tmp_root()
    # pytest creates the given basetemp with a bare mkdir (no parents), so the
    # intermediate root must exist before the factory first resolves it.
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _validate_existing_root(root)
    # No sibling scan or age-based removal: another run may still hold an old
    # directory, or its evidence may be the only retained failure record.
    basetemp = Path(admitted) if admitted else run_basetemp_dir().absolute()
    basetemp.mkdir(mode=0o700)  # Exclusive: never reuse a retained path.
    basetemp.chmod(0o700)  # A restrictive caller umask must not remove owner access.
    outcome = _SessionOutcome()
    manifest = basetemp.with_name(basetemp.name + ".owner.json")
    manifest_bytes = (
        json.dumps(
            {
                "owner_pid": outcome.owner_pid,
                "run_id": basetemp.name,
                "helper_source": str(Path(__file__).resolve()),
                "helper_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),  # noqa: TID251 - exact non-charter launcher source integrity.
                "resource": str(basetemp),
                "purpose": "private pytest scratch and retained diagnostics",
                "next_action": "owning producer joins runtime dependencies; existing lifecycle owner qualifies exact release before retirement",
                "review_event": "producer termination followed by independent owner/runtime-release review",
                "automatic_closeout_obligation": "pending admitted temporary-resource runtime-release adapter; outcome is not release",
                "retention": "requires independently proven owner/runtime release; test success alone cannot authorize removal",
            },
            sort_keys=True,
        )
        + "\n"
    ).encode()
    # A durable obligation survives a failed or interrupted producer. Neither
    # this metadata nor a dead PID grants another producer deletion authority.
    with manifest.open("xb") as handle:
        handle.write(manifest_bytes)
        handle.flush()
        os.fsync(handle.fileno())
    manifest.chmod(0o600)
    outcome.manifest = manifest
    outcome.manifest_bytes = manifest_bytes
    config.option.basetemp = str(basetemp)
    setattr(config, _OUTCOME_CONFIG_ATTR, outcome)
    # Retain exact owner/outcome records; pytest success cannot prove a child
    # or external service has released the leaf. Record after later shutdown
    # callbacks, without inferring that their execution proves release.
    # pytest_sessionfinish records success/failure; absence remains unfinished.
    # Neither outcome authorizes unlinking retained runtime dependencies.
    # Registered during configure — i.e. BEFORE the sessionstart handlers and
    # any service shutdown callbacks registered later — so LIFO ordering runs
    # it last, after everything that might still hold a file open under
    # tmp_path.
    atexit.register(partial(_record_session_outcome, basetemp, outcome))


def _record_session_outcome(basetemp: Path, outcome: _SessionOutcome) -> None:
    """Retain the leaf until the owning lifecycle proves runtime release.

    The outcome is DATA, not permission to unlink. Failed writes or changed
    identity leave all existing evidence intact; no sibling probe or sweep runs.
    """
    if outcome.owner_pid != os.getpid() or outcome.manifest is None:
        return
    try:
        if outcome.manifest.is_symlink() or basetemp.is_symlink():
            return
        with outcome.manifest.open("rb") as handle:
            if handle.read(len(outcome.manifest_bytes or b"") + 1) != outcome.manifest_bytes:
                return
        terminal = basetemp.with_name(basetemp.name + ".terminal.json")
        record = {
            "owner_pid": outcome.owner_pid,
            "run_id": basetemp.name,
            "owner_record_sha256": hashlib.sha256(outcome.manifest_bytes or b"").hexdigest(),  # noqa: TID251 - exact non-charter owner-record byte integrity.
            "pytest_outcome": "passed" if outcome.succeeded else "unsuccessful_or_unfinished",
            "runtime_release": "unobserved",
            "cleanup": "retained_pending_owner_runtime_release",
        }
        with terminal.open("xb") as handle:
            terminal.chmod(0o600)
            handle.write((json.dumps(record, sort_keys=True) + "\n").encode())
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        return  # Preserve existing owner/evidence records on uncertain closeout.
