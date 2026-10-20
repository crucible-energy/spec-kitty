"""Generation-bound decisions consume creator evidence, never discovery guesses."""

from dataclasses import replace

import pytest

from specify_cli.workspace_lifecycle.policy import Evidence, Identity, decide


def identity() -> Identity:
    return Identity(1, "crucible-energy/example", "/store/.git", "/work/feature", "a" * 40, "refs/heads/feature", "workspace-1", "lease-1")


def evidence() -> Evidence:
    return Evidence(identity(), False, True, False, False, False, True, "release-1", "delivery-1", "a" * 40, True)


def test_exact_supported_released_and_delivered_workspace_is_eligible() -> None:
    assert decide(identity(), evidence()) is None


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"primary": True}, "primary_checkout"),
        ({"clean": False}, "local_changes"),
        ({"valuable_ignored": True}, "valuable_ignored_state"),
        ({"nested": True}, "nested_repository"),
        ({"runtime_held": True}, "runtime_dependency"),
        ({"producer_fenced": False}, "producer_fence_unproven"),
        ({"release_id": None}, "owner_release_missing"),
        ({"delivery_id": None}, "delivery_missing"),
        ({"delivery_head": "b" * 40}, "delivery_mismatch"),
        ({"supported": False}, "creator_operation_unsupported"),
    ],
)
def test_preservation_refusal(change: dict[str, object], reason: str) -> None:
    assert decide(identity(), replace(evidence(), **change)) == reason


def test_reused_path_or_lease_cannot_reuse_prior_evidence() -> None:
    for change in ({"workspace_generation": "workspace-2"}, {"lease_generation": "lease-2"}, {"head": "b" * 40}, {"branch": "refs/heads/other"}):
        assert decide(identity(), replace(evidence(), identity=replace(identity(), **change))) == "identity_changed"


def test_invalid_identity_is_not_admitted() -> None:
    with pytest.raises(ValueError):
        replace(identity(), workspace_generation="")
