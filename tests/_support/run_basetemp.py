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
import uuid
from collections.abc import Iterable
from functools import partial
from pathlib import Path

import pytest
from _pytest.compat import get_user_id

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
    ``--basetemp``) — there is nothing to tell.
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


def run_basetemp_dir(pid: int | None = None) -> Path:
    """A fresh candidate, reserved exclusively by ``install_run_basetemp``.

    The PID is diagnostic only. A nonce prevents a later invocation from
    selecting and wiping a failed run's evidence after PID reuse.
    """
    return run_tmp_root() / f"run-{pid if pid is not None else os.getpid()}-{uuid.uuid4().hex[:12]}"


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
    if getattr(config, "workerinput", None) is not None:
        return
    if config.option.basetemp:
        return

    root = run_tmp_root()
    # pytest creates the given basetemp with a bare mkdir (no parents), so the
    # intermediate root must exist before the factory first resolves it.
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _validate_existing_root(root)
    # No sibling scan or age-based removal: another run may still hold an old
    # directory, or its evidence may be the only retained failure record.
    basetemp = run_basetemp_dir().absolute()
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
