"""Sanitization does not require the optional event-library adapter."""

import importlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.fast


def test_sanitizer_import_does_not_load_optional_adapter():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from specify_cli.events.sanitizer import sanitize_event_for_log; "
            "assert callable(sanitize_event_for_log); "
            "assert 'specify_cli.events.adapter' not in sys.modules; "
            "assert 'spec_kitty_events' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_original_public_event_objects_keep_identity():
    import specify_cli.events as public

    contract = {
        "Event": "adapter",
        "EventAdapter": "adapter",
        "HAS_LIBRARY": "adapter",
        "LamportClock": "adapter",
        "sanitize_event_for_log": "sanitizer",
    }
    assert public.__all__ == list(contract)
    assert set(contract) <= set(dir(public))
    for name, module in contract.items():
        assert getattr(public, name) is getattr(importlib.import_module(f"specify_cli.events.{module}"), name)
    with pytest.raises(AttributeError):
        _ = public.not_an_event_export
