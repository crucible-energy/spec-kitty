"""Coordinator intent/recovery ordering with a contract-level creator double.

Actual creator retirement and automatic ingress are WP03 acceptance, not proven here.
"""

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from collections.abc import Iterator

import pytest

from specify_cli.workspace_lifecycle.coordinator import Coordinator, Recovered, Result
from specify_cli.workspace_lifecycle.policy import Evidence, Identity
from specify_cli.workspace_lifecycle.state import Operation, StateError, StateStore


class Creator:
    authority_id = "registered-git-fixture"

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

    def recover(self, intent: Operation) -> Recovered:
        assert self.held
        self.recovery_calls += 1
        return Recovered(intent, Result("unknown", "creator_outcome_unconfirmed"))


def setup(tmp_path: Path) -> tuple[Coordinator, Creator, Identity]:
    root = tmp_path / "ledger"
    root.mkdir(mode=0o700)
    ledger = StateStore.initialize(root)
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


def test_partial_inventory_never_discharges_prior_unknown_workspace(tmp_path: Path) -> None:
    c, a, i = setup(tmp_path)
    c.reconcile("event-1", i, a)
    observation = {
        "repository": i.repository,
        "repository_id": i.repository_id,
        "common_dir": i.common_dir,
        "path": "/another/work",
        "head": i.head,
        "branch": i.branch,
        "bare": False,
        "exists": True,
        "disposition": "retained",
        "reason": "ownership_unknown",
    }
    c.account([observation])
    c.account([])
    assert c.store.read().observations[0]["path"] == "/another/work"
    assert c.closeout(workflow_complete=True)["cleanup_complete"] is False


def test_recovery_receives_exact_retained_intent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from specify_cli.workspace_lifecycle.state import Operation

    c, a, i = setup(tmp_path)

    def interrupted(identity: Identity, event_id: str) -> Result:
        raise KeyboardInterrupt

    monkeypatch.setattr(a, "retire", interrupted)
    with pytest.raises(KeyboardInterrupt):
        c.reconcile("event-1", i, a)
    retained = c.store.read().operations[-1]

    def recover(*args: object) -> object:
        assert len(args) == 1 and isinstance(args[0], Operation)
        assert args[0] == retained
        assert args[0].release_id == "release" and args[0].delivery_id == "delivery"
        from specify_cli.workspace_lifecycle.coordinator import Recovered

        return Recovered(retained, Result("retired", "receipt_verified"))

    monkeypatch.setattr(a, "recover", recover)
    assert c.reconcile("event-1", i, a).status == "retired"


def test_owned_accounting_settles_exact_generation_at_closeout(tmp_path: Path) -> None:
    c, a, i = setup(tmp_path)
    c.account_owned(i, a)
    assert c.closeout(workflow_complete=True)["cleanup_complete"] is False
    c.reconcile("event-1", i, a)
    assert c.store.read().observations[0]["disposition"] == "retired"
    assert c.closeout(workflow_complete=True)["cleanup_complete"] is True


def test_replacement_generation_cannot_discharge_prior_accounting(tmp_path: Path) -> None:
    c, a, old = setup(tmp_path)
    c.account_owned(old, a)
    new = replace(old, workspace_generation="workspace-replacement")
    a.identity = new
    a.current = replace(a.current, identity=new)
    c.account_owned(new, a)
    c.reconcile("event-new", new, a)
    assert c.closeout(workflow_complete=True)["cleanup_complete"] is False
    assert len(c.store.read().observations) == 2


def test_uncertain_intent_must_recover_before_another_event_effect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    c, a, i = setup(tmp_path)

    def unknown(identity: Identity, event_id: str) -> Result:
        a.calls += 1
        return Result("unknown", "creator_outcome_unconfirmed")

    monkeypatch.setattr(a, "retire", unknown)
    assert c.reconcile("event-1", i, a).status == "unknown"
    with pytest.raises(StateError):
        c.reconcile("event-2", i, a)
    assert a.calls == 1


def test_retired_generation_is_terminal_across_different_events(tmp_path: Path) -> None:
    c, a, i = setup(tmp_path)
    first = c.reconcile("event-1", i, a)
    duplicate = c.reconcile("event-2", i, a)
    assert duplicate == first
    assert a.calls == 1
    assert len(c.store.read().operations) == 1


def test_retired_generation_cannot_be_readmitted(tmp_path: Path) -> None:
    c, a, i = setup(tmp_path)
    c.account_owned(i, a)
    c.reconcile("event-1", i, a)
    with pytest.raises(StateError):
        c.account_owned(i, a)
    assert c.closeout(workflow_complete=True)["cleanup_complete"] is True
