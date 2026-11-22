"""Normalized events and the interface any event feed implements.

The core reads events only through EventSource, so it never knows where they come from.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Position:
    """Where the source delivered an event from: a topic, one of its partitions, and the offset within it."""

    topic: str
    partition: int
    offset: int


@dataclass(frozen=True)
class Event:
    event_id: str
    type: str
    occurred_at: datetime
    # The id of the thing the event is about, as text.
    entity: str
    payload: dict[str, Any]
    # Extra fields the source carries (for example a trace id), kept for observability.
    metadata: dict[str, Any] = field(default_factory=dict)
    # Set by the event source; the duplicate check (core/idempotency.py) records it.
    position: Position | None = None


EventHandler = Callable[[Event], Awaitable[None]]


@runtime_checkable
class EventSource(Protocol):
    async def consume(self, handler: EventHandler) -> None:
        """Deliver every event to handler, one at a time.

        An event counts as done only after handler returns; if handler raises, the source stops
        and the event is delivered again on the next run (at-least-once).
        """
        ...
