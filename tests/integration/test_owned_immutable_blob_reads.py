"""Immutable proof reads must never freeze mutable refs or leak across queries."""
from pathlib import Path

import pytest

from specify_cli.migration.owned_history_sources import _blob, immutable_blob_reads
from tests.integration.test_restore_owned_mission_history import commit, git

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def test_object_proof_survives_head_movement_without_caching_head(tmp_path: Path):
    git(tmp_path, "init", "-q")
    (tmp_path / "value.md").write_text("original")
    pin = commit(tmp_path)
    with immutable_blob_reads():
        first, metadata = _blob(tmp_path, pin, "value.md")
        assert _blob(tmp_path, "HEAD", "value.md")[0] == b"original"
        metadata["blob"] = "caller-local metadata change"
        (tmp_path / "value.md").write_text("changed")
        newer = commit(tmp_path)
        assert _blob(tmp_path, pin, "value.md")[0] == first == b"original"
        assert _blob(tmp_path, pin, "value.md")[1]["blob"] == git(tmp_path, "rev-parse", pin + ":value.md")
        assert _blob(tmp_path, newer, "value.md")[0] == b"changed"
        assert _blob(tmp_path, "HEAD", "value.md")[0] == b"changed"


def test_refusal_resets_cache_and_new_query_rechecks_objects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from specify_cli.migration import owned_history_sources

    git(tmp_path, "init", "-q")
    (tmp_path / "value.md").write_text("original")
    pin = commit(tmp_path)
    calls = []
    original = owned_history_sources.git_bytes

    def read(root, *args):
        calls.append(args)
        return original(root, *args)

    monkeypatch.setattr(owned_history_sources, "git_bytes", read)
    with pytest.raises(ValueError, match="synthetic refusal"), immutable_blob_reads():
        _blob(tmp_path, pin, "value.md")
        count = len(calls)
        _blob(tmp_path, pin, "value.md")
        assert len(calls) == count
        raise ValueError("synthetic refusal")
    _blob(tmp_path, pin, "value.md")
    assert len(calls) > count
    count = len(calls)
    with immutable_blob_reads():
        _blob(tmp_path, pin, "value.md")
    assert len(calls) > count


def test_object_cache_does_not_escape_query_when_an_object_disappears(tmp_path: Path):
    from specify_cli.migration.owned_history_sources import HistoryRestoreError, git_bytes

    git(tmp_path, "init", "-q")
    (tmp_path / "value.md").write_text("original")
    pin = commit(tmp_path)
    oid = git(tmp_path, "rev-parse", pin + ":value.md")
    loose = tmp_path / ".git" / "objects" / oid[:2] / oid[2:]
    assert loose.is_file()
    with immutable_blob_reads():
        assert git_bytes(tmp_path, "cat-file", "blob", oid) == b"original"
        loose.unlink()
        assert git_bytes(tmp_path, "cat-file", "blob", oid) == b"original"
    with pytest.raises(HistoryRestoreError):
        git_bytes(tmp_path, "cat-file", "blob", oid)
