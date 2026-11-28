"""Messages that cannot be handled are kept in dead_letters with their error, so nothing is lost silently.

An event source uses this in two places (D-018 to D-022):
- a message it cannot read goes straight to the sink;
- a handler that fails is tried again after each wait in RETRY_DELAYS; after the last try the message
  goes to the sink. An error that means the database cannot be reached is raised at once instead: during
  an outage every event would fail, so the source stops and the events wait in the source (D-020).
The source saves its read position only after the sink returns; if the sink fails, the source stops.
"""

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine

from core.db.tables import dead_letters
from core.events import Event, EventHandler, Position

# Waits between tries of a failing handler: 3 tries in all (D-019).
RETRY_DELAYS: tuple[float, ...] = (0.5, 1.0)

# Errors that mean the database cannot be reached; OSError covers a refused or timed-out connection.
OUTAGE_ERRORS: tuple[type[BaseException], ...] = (OperationalError, InterfaceError, OSError)

Sleep = Callable[[float], Awaitable[None]]


@runtime_checkable
class DeadLetterSink(Protocol):
    async def record(self, position: Position, payload: bytes | None, error: str) -> None:
        """Keep the message at position with its raw bytes (None when it had no value) and the error."""
        ...


class PostgresDeadLetterSink:
    def __init__(self, engine: AsyncEngine):
        self._engine = engine

    async def record(self, position: Position, payload: bytes | None, error: str) -> None:
        statement = (
            insert(dead_letters)
            .values(
                topic=position.topic,
                partition=position.partition,
                offset=position.offset,
                payload=payload,
                error=error,
            )
            # The same message delivered again keeps the first row (D-022).
            .on_conflict_do_nothing(
                index_elements=[dead_letters.c.topic, dead_letters.c.partition, dead_letters.c.offset]
            )
        )
        async with self._engine.begin() as conn:
            await conn.execute(statement)


def is_outage(error: BaseException) -> bool:
    return isinstance(error, OUTAGE_ERRORS)


async def run_with_retries(handler: EventHandler, event: Event, sleep: Sleep) -> Exception | None:
    """Run handler, trying again after each wait in RETRY_DELAYS.

    Returns None when a try succeeds, or the last error when every try failed. An outage error is
    raised at once, without more tries.
    """
    for delay in (*RETRY_DELAYS, None):
        try:
            await handler(event)
            return None
        except Exception as error:
            if is_outage(error):
                raise
            if delay is None:
                return error
            await sleep(delay)
    raise AssertionError("unreachable")


def handler_error_text(error: Exception) -> str:
    return f"handler failed after {len(RETRY_DELAYS) + 1} tries: {type(error).__name__}: {error}"
