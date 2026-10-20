"""Coordinator intent/recovery ordering with a contract-level creator double.

Actual creator retirement and automatic ingress are WP03 acceptance, not proven here.
"""

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from collections.abc import Iterator

import pytest

from specify_cli.workspace_lifecycle.coordinator import Coordinator, Result
from specify_cli.workspace_lifecycle.policy import Evidence, Identity
from specify_cli.workspace_lifecycle.state import StateError, StateStore


class Creator:
    def __init__(self, ledger: StateStore, ident: Identity) -> None:
        self.ledger = ledger
        self.identity = ident
        self.calls = 0
        self.held = False
        self.recovery_calls = 0
        self.current = Evidence(ident, False, True, False, False, False, True, "release", "delivery", ident.head, True)

    @contextmanager
    def hold(self, identity: Identity) -> Iterator[None]:
        assert identity == self.identity
        self.held = True
        try:
            yield
        finally:
            self.held = False

    def inspect(self, identity: Identity) -> Evidence:
        assert self.held
        return self.current

    def retire(self, identity: Identity, event_id: str) -> Result:
        import json

        assert self.held
        # Inspect durable bytes directly: re-entering the lock is deliberately avoided.
        state = json.loads((self.ledger.root / "state.json").read_text())
        assert state["operations"][-1]["status"] == "intent"
        self.calls += 1
        return Result("retired", "creator_confirmed")

    def recover(self, identity: Identity, event_id: str) -> Result:
        assert self.held
        self.recovery_calls += 1
        return Result("unknown", "creator_outcome_unconfirmed")


def setup(tmp_path: Path) -> tuple[Coordinator, Creator, Identity]:
    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    ledger = StateStore(root)
    ident = Identity(1, "crucible-energy/example", "/store/.git", "/work/feature", "a" * 40, "refs/heads/feature", "workspace-1", "lease-1")
    return Coordinator(ledger), Creator(ledger, ident), ident


def test_durable_intent_precedes_effect_and_exact_replay_is_idempotent(tmp_path: Path) -> None:
    c, a, i = setup(tmp_path)
    first = c.reconcile("event-1", i, a)
    assert first.status == "retired"
    assert c.reconcile("event-1", i, a) == first
    assert a.calls == 1
    assert c.store.read().operations[-1].status == "retired"


def test_replay_id_cannot_change_generation(tmp_path: Path) -> None:
    c, a, i = setup(tmp_path)
    c.reconcile("event-1", i, a)
    with pytest.raises(StateError):
        c.reconcile("event-1", replace(i, workspace_generation="replacement"), a)
    assert a.calls == 1


def test_refusal_is_durable_without_adapter_effect(tmp_path: Path) -> None:
    c, a, i = setup(tmp_path)
    a.current = replace(a.current, clean=False)
    assert c.reconcile("event-1", i, a).reason == "local_changes"
    assert a.calls == 0
    assert c.store.read().operations[-1].status == "retained"


def test_interruption_recovers_without_blind_retirement_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    c, a, i = setup(tmp_path)

    def interrupted(identity: Identity, event_id: str) -> Result:
        raise KeyboardInterrupt

    monkeypatch.setattr(a, "retire", interrupted)
    with pytest.raises(KeyboardInterrupt):
        c.reconcile("event-1", i, a)
    assert c.store.read().operations[-1].status == "intent"
    result = c.reconcile("event-1", i, a)
    assert result.status == "unknown"
    assert a.recovery_calls == 1
    assert a.calls == 0


def test_intent_sync_failure_prevents_creator_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.workspace_lifecycle.state as state

    c, a, i = setup(tmp_path)
    monkeypatch.setattr(state, "atomic_write", lambda *a, **kw: (_ for _ in ()).throw(OSError("durability unavailable")))
    with pytest.raises(StateError):
        c.reconcile("event-1", i, a)
    assert a.calls == 0
