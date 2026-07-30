"""Shared drain for an append that races an atomic Op-record swap.

Both Op-record repairs (``m_3_3_0_op_record_schema_v2`` and
``m_3_2_7_redact_op_requests``) install their result with ``os.replace``.
Current writers share ``invocation_record_lock``, but a writer from before that
lock existed can hold the record open across the swap, and its append then
lands on the inode the swap unlinked. Keeping the replaced inode open past the
swap keeps those bytes readable, so the repair can carry them onto the
installed file instead of losing them with the old inode.

This wait is a compatibility net, not a protocol: the shared record lock is the
protocol. A writer outside that lock can be descheduled for an unbounded time,
so no bounded wait can close the window. What this module does guarantee is
that the window is not closed by a pause shorter than an ordinary scheduling
delay, and that a writer which never stops appending cannot stall an upgrade.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import TextIO

#: Whether this platform can drain the inode a swap replaced, which decides
#: whether the swap may happen while the compare handle is still open.
#:
#: POSIX only. Windows has no unlinked-but-open file: an open handle blocks both
#: the rename and the delete, so ``os.replace`` over a destination this process
#: still holds open fails with a sharing violation (the CRT opens without
#: ``FILE_SHARE_DELETE``), and holding the handle would turn every repair into a
#: reported failure that leaves the record unrepaired. The same rule means there
#: is nothing to drain there: a stale writer holding the record open makes the
#: swap fail loudly instead of silently landing its append on a dead inode, and
#: that failure is already reported and retried on the next upgrade run.
DRAIN_SUPPORTED = os.name != "nt"

#: Pause between reads of the replaced inode.
_SETTLE_SECONDS = 0.02
#: How long the replaced inode must stay *continuously* quiet before its last
#: handle is released. Deliberately wall-clock rather than a read count: a
#: writer that opened the record and was then descheduled needs more than one
#: scheduler quantum to reach its write, so reading faster or pausing for less
#: must not shorten the window a stale writer gets.
_QUIET_SECONDS = 0.1
#: Ceiling on the whole drain, so a writer that keeps appending is reported
#: rather than allowed to hold the upgrade open indefinitely.
_BUDGET_SECONDS = 2.0

#: Receives the complete lines that landed on the replaced inode. Returns an
#: error message to fail the repair, or ``None`` once the lines are carried.
LateAppendHandler = Callable[[list[str]], str | None]


def drain_late_appends(source: TextIO, path: Path, handle: LateAppendHandler) -> str | None:
    """Carry appends from the replaced inode at *source* onto *path*.

    ``source`` must be a handle on the file the swap unlinked, opened before
    the swap so it outlives it. Reads it until it has stayed quiet for
    :data:`_QUIET_SECONDS`, passing each batch of complete lines to *handle*.

    A trailing fragment left by a writer that stopped mid-line is dropped with
    the replaced inode's bytes: a half-written record is not a record any
    reader accepts (the canonical readers skip it), and carrying it forward
    would corrupt the installed file instead.

    Returns ``None`` once the appends settle, the error message from *handle*
    when carrying a line fails, or an error when the appends never settle.
    """
    pending = ""
    quiet_since: float | None = None
    deadline = time.monotonic() + _BUDGET_SECONDS
    while time.monotonic() < deadline:
        chunk = source.read()
        if not chunk:
            now = time.monotonic()
            if quiet_since is None:
                quiet_since = now
            elif now - quiet_since >= _QUIET_SECONDS:
                return None
            time.sleep(_SETTLE_SECONDS)
            continue
        quiet_since = None
        complete, separator, pending = (pending + chunk).rpartition("\n")
        if not separator:
            time.sleep(_SETTLE_SECONDS)
            continue
        error = handle(complete.splitlines())
        if error is not None:
            return error
    return f"Could not settle appends to {path}; a writer kept appending after the replacement was installed"
