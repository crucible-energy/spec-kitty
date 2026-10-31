"""Tests for resolve_cli_package_name."""

from __future__ import annotations

from typing import Any

import pytest

from specify_cli.distribution.package_name import (

    DEFAULT_CLI_PACKAGE_NAME,
    clear_cli_package_name_cache,
    resolve_cli_package_name,
)

pytestmark = pytest.mark.fast



class _FakeEntryPoint:
    def __init__(self, name: str, payload: Any) -> None:
        self.name = name
        self._payload = payload

    def load(self) -> Any:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    clear_cli_package_name_cache()
    yield
    clear_cli_package_name_cache()


def test_default_when_no_entry_points_or_distributions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {},
    )
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME


def test_string_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [_FakeEntryPoint("main", "acme-spec-kitty-cli")],
    )
    assert resolve_cli_package_name() == "acme-spec-kitty-cli"


def test_callable_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [_FakeEntryPoint("main", lambda: "from-callable")],
    )
    assert resolve_cli_package_name() == "from-callable"


def test_object_with_package_name(monkeypatch: pytest.MonkeyPatch) -> None:
    class Holder:
        package_name = "holder-pkg"

    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [_FakeEntryPoint("main", Holder())],
    )
    assert resolve_cli_package_name() == "holder-pkg"


def test_packages_distributions_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {"specify_cli": ["fork-cli"]},
    )
    assert resolve_cli_package_name() == "fork-cli"


def test_entry_point_load_failure_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [_FakeEntryPoint("broken", RuntimeError("boom"))],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {},
    )
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME


def test_memoizes_result(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def counting_entry_points(*, group: str) -> list[_FakeEntryPoint]:
        calls["n"] += 1
        return []

    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        counting_entry_points,
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {},
    )
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME
    assert calls["n"] == 1


def test_never_uses_env_for_package_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_CLI_PACKAGE", "should-not-win")
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.entry_points",
        lambda group: [],
    )
    monkeypatch.setattr(
        "specify_cli.distribution.package_name.packages_distributions",
        lambda: {},
    )
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME


class _RegisteredStockEntryPoint(_FakeEntryPoint):
    value = "specify_cli.distribution.package_name:DEFAULT_CLI_PACKAGE_NAME"

    def __init__(self, distribution_name: Any) -> None:
        super().__init__("stock", DEFAULT_CLI_PACKAGE_NAME)
        from types import SimpleNamespace

        self.dist = SimpleNamespace(metadata={"Name": distribution_name})


@pytest.mark.parametrize("distribution_name", ["spec-kitty-cli", "acme-private-cli"])
def test_registered_stock_fallback_uses_actual_supplier_without_global_scan(monkeypatch: pytest.MonkeyPatch, distribution_name: str) -> None:
    registered = _RegisteredStockEntryPoint(distribution_name)
    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", lambda group: [registered])
    scanned: list[bool] = []

    def scan() -> dict[str, list[str]]:
        scanned.append(True)
        return {"specify_cli": [distribution_name]}

    monkeypatch.setattr("specify_cli.distribution.package_name.packages_distributions", scan)
    assert resolve_cli_package_name() == distribution_name
    assert not scanned


@pytest.mark.parametrize("custom_name", ["alpha", "zz-custom"])
def test_custom_provider_keeps_priority_over_registered_stock(monkeypatch: pytest.MonkeyPatch, custom_name: str) -> None:
    stock = _RegisteredStockEntryPoint("spec-kitty-cli")
    custom = _FakeEntryPoint(custom_name, "custom-vendor-cli")
    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", lambda group: [stock, custom])
    assert resolve_cli_package_name() == "custom-vendor-cli"


@pytest.mark.parametrize("invalid_name", [None, "", "   ", 42])
def test_invalid_registered_supplier_uses_existing_ownership_fallback(monkeypatch: pytest.MonkeyPatch, invalid_name: Any) -> None:
    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", lambda group: [_RegisteredStockEntryPoint(invalid_name)])
    monkeypatch.setattr("specify_cli.distribution.package_name.packages_distributions", lambda: {"specify_cli": ["actual-owner-cli"]})
    assert resolve_cli_package_name() == "actual-owner-cli"


def test_broken_custom_provider_does_not_silently_choose_stock(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = [_RegisteredStockEntryPoint("spec-kitty-cli"), _FakeEntryPoint("custom", RuntimeError("broken custom"))]
    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", lambda group: entries)
    monkeypatch.setattr("specify_cli.distribution.package_name.packages_distributions", lambda: {"specify_cli": ["installed-owner-cli"]})
    assert resolve_cli_package_name() == "installed-owner-cli"


def test_custom_alphabetical_selection_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = [_FakeEntryPoint("zulu", "later-cli"), _RegisteredStockEntryPoint("stock-cli"), _FakeEntryPoint("alpha", "first-cli")]
    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", lambda group: entries)
    assert resolve_cli_package_name() == "first-cli"


def test_unbound_stock_registration_does_not_guess_supplier(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = _RegisteredStockEntryPoint("unused")
    entry.dist = None
    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", lambda group: [entry])
    monkeypatch.setattr("specify_cli.distribution.package_name.packages_distributions", lambda: {"specify_cli": ["bound-owner-cli"]})
    assert resolve_cli_package_name() == "bound-owner-cli"


@pytest.mark.parametrize("payload", ["", "   ", object(), lambda: " ", lambda: 42])
def test_invalid_custom_payload_retains_ownership_fallback(monkeypatch: pytest.MonkeyPatch, payload: Any) -> None:
    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", lambda group: [_FakeEntryPoint("custom", payload)])
    monkeypatch.setattr("specify_cli.distribution.package_name.packages_distributions", lambda: {"specify_cli": [None, " ", "fallback-owner"]})
    assert resolve_cli_package_name() == "fallback-owner"


def test_type_provider_and_name_attribute_remain_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    class Provider:
        name = "typed-owner"

    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", lambda group: [_FakeEntryPoint("custom", Provider)])
    assert resolve_cli_package_name() == "typed-owner"


def test_broken_provider_construction_retains_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenProvider:
        def __init__(self) -> None:
            raise ValueError("invalid provider")

    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", lambda group: [_FakeEntryPoint("custom", BrokenProvider)])
    monkeypatch.setattr("specify_cli.distribution.package_name.packages_distributions", lambda: {"specify_cli": ["fallback-owner"]})
    assert resolve_cli_package_name() == "fallback-owner"


def test_unavailable_registration_and_ownership_metadata_preserves_stock_default(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise OSError("metadata unavailable")

    monkeypatch.setattr("specify_cli.distribution.package_name.entry_points", unavailable)
    monkeypatch.setattr("specify_cli.distribution.package_name.packages_distributions", unavailable)
    assert resolve_cli_package_name() == DEFAULT_CLI_PACKAGE_NAME
