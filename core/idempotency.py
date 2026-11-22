"""Handle each event once, even when the source delivers it again (D-015).

Delivery is at-least-once: a commit lost to a rebalance, or a new consumer group that starts from the
earliest kept message, delivers events that were already handled. The wrapper records each event_id in
processed_events in the same transaction as the handler's writes, so both are saved or neither is.
The source commits its offset only after the wrapper returns, that is after the transaction commits.
"""

from collections.abc import Awaitable, Callable

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from core.db.tables import processed_events
from core.events import Event, EventHandler

# A handler that writes through the connection it is given, inside the wrapper's transaction.
TransactionalHandler = Callable[[Event, AsyncConnection], Awaitable[None]]


def idempotent(engine: AsyncEngine, handler: TransactionalHandler) -> EventHandler:
    async def handle(event: Event) -> None:
        if event.position is None:
            raise ValueError(f"event {event.event_id} has no position; the event source must set it")
        async with engine.begin() as conn:
            statement = (
                insert(processed_events)
                .values(
                    event_id=event.event_id,
                    topic=event.position.topic,
                    partition=event.position.partition,
                    offset=event.position.offset,
                )
                .on_conflict_do_nothing(index_elements=[processed_events.c.event_id])
                .returning(processed_events.c.event_id)
            )
            if (await conn.execute(statement)).first() is None:
                # Already handled: skip it; the empty transaction commits and the source moves on.
                return
            await handler(event, conn)

    return handle
