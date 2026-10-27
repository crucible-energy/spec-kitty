"""Event log integration package.

Public API:
    sanitize_event_for_log: Strip PII fields from an event envelope dict.
    Event: CLI representation of an event (wraps library Event).
    LamportClock: CLI representation of Lamport clock.
    EventAdapter: Adapter for spec-kitty-events library integration.
    HAS_LIBRARY: Whether the optional spec-kitty-events library is installed.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .adapter import Event, EventAdapter, HAS_LIBRARY, LamportClock
    from .sanitizer import sanitize_event_for_log

_EXPORT_MODULES = {
    "Event": "adapter",
    "EventAdapter": "adapter",
    "HAS_LIBRARY": "adapter",
    "LamportClock": "adapter",
    "sanitize_event_for_log": "sanitizer",
}

__all__ = [
    "Event",
    "EventAdapter",
    "HAS_LIBRARY",
    "LamportClock",
    "sanitize_event_for_log",
]


def __getattr__(name: str) -> Any:
    module = _EXPORT_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f"{__name__}.{module}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
