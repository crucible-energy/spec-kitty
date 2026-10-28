"""Tests for the per-run pytest temp root (#63).

Pure-logic limbs are ``fast``; the subprocess probes prove actual pytest
invocations land under the private root and retain their outcome at exit.
They carry ``integration``, matching their real cost.
"""

from __future__ import annotations

import atexit
import contextlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import psutil

from tests._support import run_basetemp as run_basetemp_module
from tests._support.run_basetemp import (
    RUN_TMP_ROOT_NAME,
    STALE_RUN_MAX_AGE_S,
    _validate_existing_root,
    install_run_basetemp,
    mark_session_outcome,
    remove_run_dirs,
    run_basetemp_dir,
    run_tmp_root,
    stale_run_dirs,
    temproot,
)
from tests.utils import REPO_ROOT

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_PROBE_ENV = "SPEC_KITTY_RUN_BASETEMP_PROBE"


def _fake_config(basetemp: str | None = None, *, worker: bool = False) -> SimpleNamespace:
    """Just what :func:`install_run_basetemp` touches: the option and workerinput."""
    config = SimpleNamespace(option=SimpleNamespace(basetemp=basetemp))
    if worker:
        config.workerinput = {"workerid": "gw3"}
    return config


# ---------------------------------------------------------------------------
# Naming / resolution
# ---------------------------------------------------------------------------


def test_run_basetemp_dir_is_unique_per_controller_process() -> None:
    assert run_basetemp_dir(pid=100) != run_basetemp_dir(pid=200)
    # Recycled PIDs must not select and erase a retained earlier run.
    same_pid_first = run_basetemp_dir(pid=100)
    same_pid_second = run_basetemp_dir(pid=100)
    assert same_pid_first != same_pid_second
    assert run_basetemp_dir(pid=100).parent == run_tmp_root()


def test_temproot_honors_pytest_debug_temproot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYTEST_DEBUG_TEMPROOT", raising=False)
    default = temproot()
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", "/opt/alt-root")
    assert temproot() == Path("/opt/alt-root")
    assert run_tmp_root() == Path("/opt/alt-root") / RUN_TMP_ROOT_NAME
    monkeypatch.delenv("PYTEST_DEBUG_TEMPROOT", raising=False)
    assert temproot() == default


# ---------------------------------------------------------------------------
# Stale sweep
# ---------------------------------------------------------------------------


def _make_dir(root: Path, name: str, *, mtime: float) -> Path:
    path = root / name
    path.mkdir()
    os.utime(path, (mtime, mtime))
    return path


def test_stale_run_dirs_selects_only_entries_past_the_age_bound(tmp_path: Path) -> None:
    now = 2_000_000.0
    _make_dir(tmp_path, "run-1", mtime=now - STALE_RUN_MAX_AGE_S - 10)
    live = _make_dir(tmp_path, "run-2", mtime=now - STALE_RUN_MAX_AGE_S + 10)
    edge = _make_dir(tmp_path, "run-3", mtime=now - STALE_RUN_MAX_AGE_S)

    assert [path.name for path in stale_run_dirs(tmp_path, now=now)] == ["run-1"]
    assert live.is_dir() and edge.is_dir()


def test_stale_run_dirs_returns_empty_for_missing_root(tmp_path: Path) -> None:
    assert stale_run_dirs(tmp_path / "absent", now=10**9) == []


def test_remove_run_dirs_handles_dirs_files_and_repeats(tmp_path: Path) -> None:
    victim_dir = tmp_path / "run-9"
    (victim_dir / "nested").mkdir(parents=True)
    (victim_dir / "nested" / "f.txt").write_text("x")
    victim_file = tmp_path / "stray"
    victim_file.write_text("y")

    removed = remove_run_dirs([victim_dir, victim_file, victim_dir])
    assert removed == [victim_dir, victim_file]
    assert not victim_dir.exists() and not victim_file.exists()
    assert remove_run_dirs([victim_dir, victim_file]) == []


# ---------------------------------------------------------------------------
# Pre-existing-root validation (#77: pytest-parity owner/mode/symlink checks)
# ---------------------------------------------------------------------------


def test_validate_existing_root_repairs_world_readable_mode(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir(mode=0o755)
    os.chmod(root, 0o755)  # mkdir's mode is umask-filtered; force the bits we're testing

    _validate_existing_root(root)

    assert stat.S_IMODE(root.stat().st_mode) & 0o077 == 0


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_private_creator_preserves_owner_access_under_restrictive_umask(tmp_path: Path) -> None:
    script = """
import os,stat,sys
from pathlib import Path
from types import SimpleNamespace
from tests._support.run_basetemp import install_run_basetemp
os.environ["PYTEST_DEBUG_TEMPROOT"] = sys.argv[1]
os.umask(0o777)
config = SimpleNamespace(option=SimpleNamespace(basetemp=None))
install_run_basetemp(config, now=1)
path = Path(config.option.basetemp)
assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
assert stat.S_IMODE(path.stat().st_mode) == 0o700
manifest = path.with_name(path.name + ".owner.json")
assert stat.S_IMODE(manifest.stat().st_mode) == 0o600
assert manifest.read_bytes()
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_validate_existing_root_rejects_a_symlinked_root(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real_dir)

    with pytest.raises(OSError, match="symbolic link"):
        _validate_existing_root(link)


def test_validate_existing_root_rejects_a_root_owned_by_another_uid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(run_basetemp_module, "get_user_id", lambda: root.stat().st_uid + 1)

    with pytest.raises(OSError, match="not owned by the current user"):
        _validate_existing_root(root)


def test_validate_existing_root_is_a_noop_when_uid_is_undeterminable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows' ``get_user_id`` returns ``None`` — matches pytest's own
    rootdir check, which skips owner/mode enforcement in that case too."""
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real_dir)
    monkeypatch.setattr(run_basetemp_module, "get_user_id", lambda: None)

    _validate_existing_root(link)  # must not raise despite the symlink


def test_install_run_basetemp_rejects_a_preexisting_symlinked_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temp_root = tmp_path / "temproot"
    temp_root.mkdir()
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(temp_root))
    real_dir = tmp_path / "real-root"
    real_dir.mkdir()
    (temp_root / RUN_TMP_ROOT_NAME).symlink_to(real_dir)

    with pytest.raises(OSError, match="symbolic link"):
        install_run_basetemp(_fake_config(), now=10**9)


# ---------------------------------------------------------------------------
# install_run_basetemp
# ---------------------------------------------------------------------------


def test_install_points_config_at_a_fresh_private_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    config = _fake_config()

    install_run_basetemp(config, now=10**9)

    chosen = Path(config.option.basetemp)
    assert chosen.parent == tmp_path / RUN_TMP_ROOT_NAME
    assert chosen.name.startswith("run-")
    assert chosen.parent.is_dir(), "root pre-created: pytest mkdirs the basetemp without parents"
    assert chosen.is_dir(), "the creator exclusively reserves its own empty leaf"


def test_install_refuses_an_existing_candidate_without_erasing_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    root = tmp_path / RUN_TMP_ROOT_NAME
    root.mkdir(mode=0o700)
    retained = root / "run-recycled"
    retained.mkdir()
    evidence = retained / "retained.json"
    evidence.write_text('{"preserve":true}\n')
    monkeypatch.setattr(run_basetemp_module, "run_basetemp_dir", lambda: retained)
    handlers: list = []
    monkeypatch.setattr(atexit, "register", handlers.append)
    config = _fake_config()
    with pytest.raises(FileExistsError):
        install_run_basetemp(config, now=10**9)
    assert evidence.read_text() == '{"preserve":true}\n'
    assert config.option.basetemp is None
    assert handlers == []


def test_install_retains_aged_unknown_and_concurrent_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    now = 5_000_000.0
    root = tmp_path / RUN_TMP_ROOT_NAME
    root.mkdir()
    crashed = _make_dir(root, "run-111", mtime=now - STALE_RUN_MAX_AGE_S - 60)
    concurrent = _make_dir(root, "run-222", mtime=now - 30)

    install_run_basetemp(config := _fake_config(), now=now)

    assert crashed.is_dir(), "age is not owner release or evidence-retention authority"
    assert concurrent.is_dir()
    assert Path(config.option.basetemp) not in (crashed, concurrent)


def test_install_never_selects_another_aged_live_run_for_removal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    now = 5_000_000.0
    root = tmp_path / RUN_TMP_ROOT_NAME
    root.mkdir(mode=0o700)
    held = _make_dir(root, "run-live-held", mtime=now - STALE_RUN_MAX_AGE_S - 60)
    evidence = held / "retained.json"
    evidence.write_text('{"retain":true}\n')
    os.utime(held, (now - STALE_RUN_MAX_AGE_S - 60,) * 2)
    selected: list[Path] = []
    handlers: list = []
    # Observe the old unsafe selection without actually deleting evidence.
    monkeypatch.setattr(run_basetemp_module, "remove_run_dirs", lambda paths: selected.extend(paths) or [])
    monkeypatch.setattr(atexit, "register", handlers.append)
    child = subprocess.Popen(
        [sys.executable, "-c", "import os,sys; print(os.getcwd(),flush=True); sys.stdin.buffer.read()"],
        cwd=held,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert child.stdout is not None
        assert Path(child.stdout.readline().decode().strip()).resolve() == held.resolve()
        assert child.poll() is None
        config = _fake_config()
        install_run_basetemp(config, now=now)
        assert selected == [], "another producer's aged live/unknown path is not ours to remove"
        mark_session_outcome(config, succeeded=True)
        Path(config.option.basetemp).mkdir(parents=True, exist_ok=True)
        handlers[0]()
        assert held.is_dir() and evidence.read_text() == '{"retain":true}\n'
        assert child.poll() is None
    finally:
        child.communicate(timeout=10)
    assert child.returncode == 0


def test_live_enclosure_witness_and_explicit_descriptor_closeout(tmp_path: Path) -> None:
    root = tmp_path / "private-controller"
    root.mkdir(mode=0o700)
    data, temporary = root / "data", root / "temporary"
    context = run_basetemp_module._RunEnclosure(root, [data, temporary], temporary)
    with contextlib.ExitStack() as cleanup:
        cleanup.callback(context.close)
        context.open()
        view = run_basetemp_module._EnclosureView(context.projection())
        view.check(data / "child")
        descriptor = context.fd
        assert descriptor is not None
        assert os.fstat(descriptor).st_ino == context.record.stat().st_ino
    assert context.closed
    assert context.listener.fileno() == -1
    assert not context.thread.is_alive()
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(descriptor)
    assert context.record.is_file(), "closed transport grants no cleanup authority"


@pytest.mark.parametrize("change", ["closed", "record", "root", "generation", "nonce", "endpoint", "scope"])
def test_changed_or_forged_live_enclosure_refuses(tmp_path: Path, change: str) -> None:
    root = tmp_path / "controller"
    root.mkdir(mode=0o700)
    data, temporary = root / "data", root / "temporary"
    context = run_basetemp_module._RunEnclosure(root, [data, temporary], temporary)
    with contextlib.ExitStack() as cleanup:
        cleanup.callback(context.close)
        context.open()
        projection = context.projection()
        candidate = data / "not-created"
        if change == "closed":
            context.close()
        elif change == "record":
            contents = context.record.read_bytes()
            context.record.unlink()
            context.record.write_bytes(contents)
        elif change == "root":
            root.rename(tmp_path / "retained-original")
            root.mkdir(mode=0o700)
        elif change == "generation":
            projection["birth"] = "1970-01-01T00:00:00+00:00"
        elif change == "nonce":
            projection["run_id"] = "0" * 32
        elif change == "endpoint":
            projection["port"] = 1
        else:
            candidate = tmp_path / "foreign-sibling"
        view = run_basetemp_module._EnclosureView(projection)
        with pytest.raises((OSError, psutil.Error)):
            view.check(candidate)
        assert not candidate.exists()


def test_controller_cannot_mint_scope_outside_its_physical_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir(mode=0o700)
    with pytest.raises(OSError, match="physical enclosure"):
        run_basetemp_module._RunEnclosure(root, [tmp_path / "outside"], root / "tmp")
    assert list(root.iterdir()) == []


def test_enclosed_symlink_cannot_redirect_to_foreign_sibling(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir(mode=0o700)
    data, temporary = root / "data", root / "tmp"
    data.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (data / "redirect").symlink_to(outside, target_is_directory=True)
    context = run_basetemp_module._RunEnclosure(root, [data, temporary], temporary)
    with contextlib.ExitStack() as cleanup:
        cleanup.callback(context.close)
        context.open()
        with pytest.raises(OSError, match="escapes"):
            context.check(data / "redirect" / "not-created")
    assert list(outside.iterdir()) == []


def test_real_admission_refuses_foreign_source_home_override_before_effects(tmp_path: Path) -> None:
    selected = tmp_path / "selected"
    selected.mkdir(mode=0o700)
    foreign = tmp_path / "foreign"
    foreign.mkdir(mode=0o700)
    sentinel = foreign / "config.yaml"
    sentinel.write_bytes(b"synthetic: preserved\n")
    sentinel.chmod(0o600)
    before = sentinel.stat()
    environment = dict(os.environ)
    environment.pop("SPEC_KITTY_TEST_ENCLOSURE", None)
    environment["PYTEST_DEBUG_TEMPROOT"] = str(selected)
    environment["SPEC_KITTY_HOME"] = str(foreign)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/kernel/test_yaml_io.py::test_canonical_yaml_width_is_4096",
            "--basetemp",
            str(selected / "pytest"),
            "-p",
            "no:cacheprovider",
            "-q",
        ],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "outside the test enclosure" in result.stdout + result.stderr
    assert list(selected.iterdir()) == []
    assert list(foreign.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"synthetic: preserved\n"
    after = sentinel.stat()
    assert all(
        getattr(before, name) == getattr(after, name)
        for name in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_uid",
            "st_gid",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
            "st_nlink",
        )
    )


@pytest.mark.parametrize("explicit", [False, True])
def test_admission_refuses_foreign_configuration_before_effects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool) -> None:
    foreign = tmp_path / "foreign"
    foreign.mkdir(mode=0o700)
    marker = foreign / ".kittify"
    marker.mkdir()
    sentinel = marker / "config.yaml"
    sentinel.write_bytes(b"synthetic: preserved\n")
    sentinel.chmod(0o600)
    before = sentinel.stat()
    candidate = foreign / "scratch"
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(candidate))
    monkeypatch.delenv("SPEC_KITTY_TEST_ENCLOSURE", raising=False)
    monkeypatch.setattr(run_basetemp_module, "_ACTIVE_ENCLOSURE", None, raising=False)
    monkeypatch.setattr(atexit, "register", lambda callback: None)
    config = _fake_config(str(candidate / "explicit") if explicit else None)
    with pytest.raises((OSError, pytest.UsageError)):
        install_run_basetemp(config, now=1)
    assert not candidate.exists()
    assert sentinel.read_bytes() == b"synthetic: preserved\n"
    after = sentinel.stat()
    assert all(
        getattr(before, name) == getattr(after, name)
        for name in (
            "st_dev",
            "st_ino",
            "st_uid",
            "st_gid",
            "st_mode",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
            "st_nlink",
        )
    )


@pytest.mark.parametrize("projection", ["not-json", '{"owner_pid": 0}'])
def test_projection_alone_cannot_mint_an_enclosure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, projection: str) -> None:
    candidate = tmp_path / "unadmitted"
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(candidate))
    monkeypatch.setenv("SPEC_KITTY_TEST_ENCLOSURE", projection)
    monkeypatch.setattr(run_basetemp_module, "_ACTIVE_ENCLOSURE", None, raising=False)
    monkeypatch.setattr(atexit, "register", lambda callback: None)
    with pytest.raises((OSError, pytest.UsageError)):
        install_run_basetemp(_fake_config(), now=1)
    assert not candidate.exists()


def test_fresh_worker_without_real_handoff_refuses_before_effects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = tmp_path / "worker"
    config = _fake_config(str(candidate), worker=True)
    monkeypatch.delenv("SPEC_KITTY_TEST_ENCLOSURE", raising=False)
    monkeypatch.setattr(run_basetemp_module, "_ACTIVE_ENCLOSURE", None, raising=False)
    with pytest.raises((OSError, pytest.UsageError)):
        install_run_basetemp(config, now=1)
    assert config.option.basetemp == str(candidate)
    assert not candidate.exists()


def test_foreign_temp_is_refused_before_platform_temp_write_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    foreign = tmp_path / "foreign-temp"
    foreign.mkdir(mode=0o700)
    (foreign / ".kittify").mkdir()
    candidate = foreign / "scratch"
    monkeypatch.delenv("PYTEST_DEBUG_TEMPROOT", raising=False)
    monkeypatch.setenv("TMPDIR", str(candidate))
    monkeypatch.delenv("SPEC_KITTY_TEST_ENCLOSURE", raising=False)
    monkeypatch.setattr(run_basetemp_module, "_ACTIVE_ENCLOSURE", None, raising=False)

    def forbidden_probe() -> str:
        raise AssertionError("platform temporary-directory probing preceded admission")

    monkeypatch.setattr(run_basetemp_module.tempfile, "gettempdir", forbidden_probe)
    with pytest.raises((OSError, pytest.UsageError)):
        install_run_basetemp(_fake_config(), now=1)
    assert not candidate.exists()


def test_install_respects_an_explicit_basetemp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    explicit = str(tmp_path / "user-owned")
    registered: list[object] = []
    monkeypatch.setattr(atexit, "register", registered.append)

    config = _fake_config(basetemp=explicit)
    install_run_basetemp(config, now=10**9)

    assert config.option.basetemp == explicit
    assert registered == [], "whoever passes --basetemp owns its lifecycle"


def test_install_never_touches_an_xdist_worker_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    registered: list[object] = []
    monkeypatch.setattr(atexit, "register", registered.append)

    config = _fake_config(worker=True)
    install_run_basetemp(config, now=10**9)

    assert config.option.basetemp is None
    assert registered == []
    assert not (tmp_path / RUN_TMP_ROOT_NAME).exists()


def test_install_records_outcome_without_inventing_runtime_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    handlers: list = []

    def _capture(function) -> None:
        handlers.append(function)

    monkeypatch.setattr(atexit, "register", _capture)
    config = _fake_config()
    install_run_basetemp(config, now=10**9)
    assert len(handlers) == 1  # exactly one outcome recorder, never two

    # Simulate a successful session — pytest_sessionfinish marks this BEFORE
    # atexit callbacks run; success still cannot establish runtime release.
    mark_session_outcome(config, succeeded=True)

    # Simulate interpreter exit with residue left under the run dir.
    residue = Path(config.option.basetemp) / "popen-gw0"
    residue.mkdir(parents=True)
    (residue / "leftover").write_text("x")
    handlers[0]()
    held = Path(config.option.basetemp)
    assert held.is_dir()
    assert (residue / "leftover").read_text() == "x"
    terminal = json.loads(held.with_name(held.name + ".terminal.json").read_text())
    assert terminal["pytest_outcome"] == "passed"
    assert terminal["runtime_release"] == "unobserved"
    assert terminal["cleanup"] == "retained_pending_owner_runtime_release"


def test_install_retains_the_run_dir_when_the_session_did_not_succeed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#76: a failed/errored/interrupted session keeps its tmp tree — the
    reap is gated on a recorded success, never unconditional."""
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    handlers: list = []
    monkeypatch.setattr(atexit, "register", handlers.append)

    config = _fake_config()
    install_run_basetemp(config, now=10**9)

    basetemp = Path(config.option.basetemp)
    basetemp.mkdir(parents=True, exist_ok=True)
    forensic_evidence = basetemp / "leftover.txt"
    forensic_evidence.write_text("post-mortem state")

    # No mark_session_outcome(succeeded=True) call — the default is "not
    # succeeded", matching a run that crashed before sessionfinish too.
    handlers[0]()

    assert basetemp.is_dir()
    assert forensic_evidence.read_text() == "post-mortem state"
    assert basetemp.with_name(basetemp.name + ".owner.json").is_file()


@pytest.mark.parametrize("change", ["owner", "manifest"])
def test_success_does_not_reap_from_another_process_or_changed_owner_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    handlers: list = []
    monkeypatch.setattr(atexit, "register", handlers.append)
    config = _fake_config()
    install_run_basetemp(config, now=10**9)
    path = Path(config.option.basetemp)
    manifest = path.with_name(path.name + ".owner.json")
    mark_session_outcome(config, succeeded=True)
    if change == "owner":
        pid = os.getpid()
        monkeypatch.setattr(run_basetemp_module.os, "getpid", lambda: pid + 1)
    else:
        manifest.write_bytes(b"changed ownership\n")
    handlers[0]()
    assert path.is_dir()
    assert manifest.is_file()


def test_mark_session_outcome_is_a_noop_without_an_installed_reaper() -> None:
    """A config install_run_basetemp never ran against (xdist worker, or an
    explicit --basetemp) has nothing for mark_session_outcome to update."""
    config = _fake_config()
    mark_session_outcome(config, succeeded=True)  # must not raise


# ---------------------------------------------------------------------------
# End-to-end wiring: a real nested pytest run
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_inner_tmp_path_lands_under_the_private_run_root(tmp_path: Path) -> None:
    """Runs only as the inner probe spawned by the integration test below."""
    if not os.environ.get(_PROBE_ENV):
        pytest.skip("inner probe of test_subprocess_run_uses_the_private_root")
    expected_root = Path(os.environ["PYTEST_DEBUG_TEMPROOT"]) / RUN_TMP_ROOT_NAME
    assert tmp_path.is_relative_to(expected_root)


@pytest.mark.integration
@pytest.mark.parametrize("workers", ["0", "1"])
def test_subprocess_success_retains_private_root_until_runtime_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workers: str,
) -> None:
    """The whole mechanism, observed from outside a real pytest invocation."""
    if os.environ.get(_PROBE_ENV):
        pytest.skip("the inner probe must not recurse")
    scratch = tmp_path / "temproot"
    scratch.mkdir()
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(scratch))
    monkeypatch.setenv(_PROBE_ENV, "1")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(Path(__file__).resolve()),
            "-n",
            workers,
            "-k",
            "inner",
            "-p",
            "no:cacheprovider",
            "--tb=short",
            "-q",
        ],
        cwd=REPO_ROOT,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output

    private_root = scratch / RUN_TMP_ROOT_NAME
    assert private_root.is_dir(), f"the run never created its private root:\n{output}"
    runs = [entry for entry in private_root.iterdir() if entry.is_dir()]
    assert len(runs) == 1, output
    terminal = json.loads(runs[0].with_name(runs[0].name + ".terminal.json").read_text())
    assert terminal["pytest_outcome"] == "passed"
    assert terminal["runtime_release"] == "unobserved"


_PROBE_FAIL_ENV = "SPEC_KITTY_RUN_BASETEMP_PROBE_FAIL"


@pytest.mark.fast
def test_probe_failure_leaves_a_marker_under_tmp_path(tmp_path: Path) -> None:
    """Runs only as the inner probe spawned by
    ``test_subprocess_failed_run_retains_the_private_root``; deliberately
    fails after writing a marker so the outer test can check it survives."""
    if not os.environ.get(_PROBE_FAIL_ENV):
        pytest.skip("inner probe of test_subprocess_failed_run_retains_the_private_root")
    (tmp_path / "marker.txt").write_text("post-mortem evidence")
    pytest.fail("intentional failure to exercise outcome-gated retention (#76)")


@pytest.mark.integration
def test_subprocess_failed_run_retains_the_private_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#76 end-to-end: a session with a failing test keeps its private root.

    Exercises the real ``pytest_sessionfinish`` wiring in ``tests/conftest.py``
    (:func:`mark_session_outcome` called there), not just the isolated
    unit-level calls in the ``install_run_basetemp`` tests above.
    """
    if os.environ.get(_PROBE_ENV) or os.environ.get(_PROBE_FAIL_ENV):
        pytest.skip("the inner probe must not recurse")
    scratch = tmp_path / "temproot"
    scratch.mkdir()
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(scratch))
    monkeypatch.setenv(_PROBE_FAIL_ENV, "1")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(Path(__file__).resolve()),
            "-k",
            "probe_failure_leaves_a_marker",
            "-p",
            "no:cacheprovider",
            "--tb=short",
            "-q",
        ],
        cwd=REPO_ROOT,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"the inner probe was supposed to fail:\n{output}"

    private_root = scratch / RUN_TMP_ROOT_NAME
    run_dirs = [entry for entry in private_root.iterdir() if entry.is_dir()]
    assert len(run_dirs) == 1, f"expected exactly the retained run dir:\n{output}"
    manifest = run_dirs[0].with_name(run_dirs[0].name + ".owner.json")
    assert manifest.is_file(), "retained evidence needs its durable owner-closeout obligation"
    markers = list(run_dirs[0].rglob("marker.txt"))
    assert markers, f"forensic marker did not survive the failed session:\n{output}"
    assert markers[0].read_text() == "post-mortem evidence"


def test_success_retains_exact_leaf_while_another_process_holds_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_DEBUG_TEMPROOT", str(tmp_path))
    handlers: list = []
    monkeypatch.setattr(atexit, "register", handlers.append)
    config = _fake_config()
    install_run_basetemp(config, now=1)
    held = Path(config.option.basetemp)
    evidence = held / "evidence.json"
    evidence.write_text('{"preserve":true}\n')
    child = subprocess.Popen(
        [sys.executable, "-c", "import os,sys; print(os.getcwd(),flush=True); sys.stdin.buffer.read()"],
        cwd=held,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert child.stdout is not None
        assert Path(child.stdout.readline().decode().strip()).resolve() == held.resolve()
        mark_session_outcome(config, succeeded=True)
        handlers[0]()
        assert held.is_dir(), "test success alone does not release another runtime's custody"
        assert evidence.read_text() == '{"preserve":true}\n'
        assert child.poll() is None
    finally:
        child.communicate(timeout=10)
    assert child.returncode == 0
