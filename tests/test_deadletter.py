"""T-004: unreadable messages and handlers that keep failing go to dead_letters; a database outage stops."""

import asyncio

import pytest
from alembic import command
from core.deadletter import DeadLetterSink, PostgresDeadLetterSink
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from adapters.warehouse.kafka_source import KafkaEventSource
from core.db.tables import dead_letters, processed_events
from core.events import Position
from core.idempotency import idempotent
from tests.dbsupport import alembic_config, database_url_or_skip
from tests.test_events import EVENT_ID, FakeConsumer, FakeMessage, encode, envelope

TOPIC = "wms.pick.completed"
OTHER_ID = "5d2a7e40-9c1b-4f3e-8a6d-1e2f3a4b5c6d"


class FakeSink:
    """Stands in for the dead_letters table: records every call, or fails when asked to."""

    def __init__(self, log=None, fail=False):
        self.records = []
        self.log = log if log is not None else []
        self.fail = fail

    async def record(self, position, payload, error):
        if self.fail:
            self.log.append("dead letter failed")
            raise RuntimeError("dead_letters write failed")
        self.log.append("dead letter")
        self.records.append((position, payload, error))


class FakeSleep:
    """Records each wait instead of sleeping."""

    def __init__(self):
        self.waits = []

    async def __call__(self, seconds):
        self.waits.append(seconds)


class LoggingConsumer(FakeConsumer):
    def __init__(self, messages, log):
        super().__init__(messages)
        self.log = log

    async def commit(self, offsets):
        self.log.append("offset commit")
        await super().commit(offsets)


def run(consumer, handler, sink, sleep=None):
    source = KafkaEventSource(consumer, dead_letters=sink, sleep=sleep or FakeSleep())
    asyncio.run(source.consume(handler))


def recording_handler(seen):
    async def handler(event):
        seen.append(event.event_id)

    return handler


def test_postgres_sink_is_a_dead_letter_sink():
    assert isinstance(PostgresDeadLetterSink(None), DeadLetterSink)


# AC-2: unreadable messages are dead-lettered and the consumer moves on


@pytest.mark.parametrize(
    ("value", "error_part"),
    [
        (b'{"event_id": ', "JSON"),
        (encode({k: v for k, v in envelope().items() if k != "event_id"}), "event_id"),
        (encode(envelope(order_id=[1, 2])), "order_id"),
    ],
    ids=["broken-json", "missing-field", "wrong-type"],
)
def test_unreadable_message_is_dead_lettered_and_consumer_continues(value, error_part):
    consumer = FakeConsumer(
        [FakeMessage(value, partition=1, offset=4), FakeMessage(encode(envelope()), partition=1, offset=5)]
    )
    sink, seen = FakeSink(), []

    run(consumer, recording_handler(seen), sink)

    assert len(sink.records) == 1
    position, payload, error = sink.records[0]
    assert position == Position(TOPIC, 1, 4)
    assert payload == value
    assert error_part in error
    assert seen == [EVENT_ID]
    assert consumer.commits == [{(TOPIC, 1): 5}, {(TOPIC, 1): 6}]
    assert consumer.calls == ["start", "stop"]


def test_dead_letter_is_saved_before_the_offset_commit():
    log = []
    consumer = LoggingConsumer([FakeMessage(b"garbage")], log)

    run(consumer, recording_handler([]), FakeSink(log))

    assert log == ["dead letter", "offset commit"]


# AC-3: a tombstone (no value) is dead-lettered with payload NULL


def test_tombstone_is_dead_lettered_with_no_payload():
    consumer = FakeConsumer([FakeMessage(None, offset=0), FakeMessage(encode(envelope()), offset=1)])
    sink, seen = FakeSink(), []

    run(consumer, recording_handler(seen), sink)

    assert [(p, v) for p, v, _ in sink.records] == [(Position(TOPIC, 0, 0), None)]
    assert "no value" in sink.records[0][2]
    assert seen == [EVENT_ID]
    assert consumer.commits == [{(TOPIC, 0): 1}, {(TOPIC, 0): 2}]


# AC-4: a handler that fails once is retried and nothing is dead-lettered


def test_handler_retried_after_one_failure():
    consumer = FakeConsumer([FakeMessage(encode(envelope()), offset=3)])
    sink, sleep, calls = FakeSink(), FakeSleep(), []

    async def flaky(event):
        calls.append(event.event_id)
        if len(calls) == 1:
            raise RuntimeError("first try broke")

    run(consumer, flaky, sink, sleep)

    assert calls == [EVENT_ID, EVENT_ID]
    assert sleep.waits == [0.5]
    assert sink.records == []
    assert consumer.commits == [{(TOPIC, 0): 4}]


# AC-5: a handler that fails on all 3 tries is dead-lettered, then the consumer continues


def test_handler_failing_every_try_is_dead_lettered():
    value = encode(envelope())
    consumer = FakeConsumer([FakeMessage(value, offset=0), FakeMessage(encode(envelope(event_id=OTHER_ID)), offset=1)])
    sink, sleep, calls = FakeSink(), FakeSleep(), []

    async def handler(event):
        calls.append(event.event_id)
        if event.event_id == EVENT_ID:
            raise ValueError(f"try {calls.count(EVENT_ID)} broke")

    run(consumer, handler, sink, sleep)

    assert calls == [EVENT_ID, EVENT_ID, EVENT_ID, OTHER_ID]
    assert sleep.waits == [0.5, 1.0]
    assert len(sink.records) == 1
    position, payload, error = sink.records[0]
    assert (position, payload) == (Position(TOPIC, 0, 0), value)
    assert "try 3 broke" in error
    assert "ValueError" in error
    assert consumer.commits == [{(TOPIC, 0): 1}, {(TOPIC, 0): 2}]


# AC-6: a database outage, or a failed dead_letters write, stops the consumer


@pytest.mark.parametrize(
    "outage",
    [
        OperationalError("SELECT 1", {}, ConnectionRefusedError("refused")),
        ConnectionRefusedError("refused"),
    ],
    ids=["sqlalchemy-operational", "connection-refused"],
)
def test_database_outage_stops_without_dead_letter(outage):
    consumer = FakeConsumer([FakeMessage(encode(envelope())), FakeMessage(encode(envelope(event_id=OTHER_ID)))])
    sink, calls = FakeSink(), []

    async def handler(event):
        calls.append(event.event_id)
        raise outage

    with pytest.raises(type(outage)):
        run(consumer, handler, sink)

    assert calls == [EVENT_ID]
    assert sink.records == []
    assert consumer.commits == []
    assert consumer.calls == ["start", "stop"]


def test_failed_dead_letter_write_stops_without_commit():
    log = []
    consumer = LoggingConsumer([FakeMessage(b"garbage"), FakeMessage(encode(envelope()))], log)
    seen = []

    with pytest.raises(RuntimeError, match="dead_letters write failed"):
        run(consumer, recording_handler(seen), FakeSink(log, fail=True))

    assert log == ["dead letter failed"]
    assert seen == []
    assert consumer.commits == []


# The dead_letters table itself, on the local test database


@pytest.fixture
def db_url():
    url = database_url_or_skip()
    command.upgrade(alembic_config(url), "head")

    async def reset():
        engine = create_async_engine(url)
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE TABLE IF NOT EXISTS test_writes (event_id text NOT NULL)"))
                await conn.execute(text("DELETE FROM test_writes"))
                await conn.execute(processed_events.delete())
                await conn.execute(dead_letters.delete())
        finally:
            await engine.dispose()

    asyncio.run(reset())
    return url


def run_with_engine(url, body):
    async def main():
        engine = create_async_engine(url)
        try:
            return await body(engine)
        finally:
            await engine.dispose()

    return asyncio.run(main())


async def dead_letter_rows(engine):
    async with engine.connect() as conn:
        rows = await conn.execute(
            select(
                dead_letters.c.topic,
                dead_letters.c.partition,
                dead_letters.c.offset,
                dead_letters.c.payload,
                dead_letters.c.error,
                dead_letters.c.created_at,
            ).order_by(dead_letters.c.id)
        )
        return [tuple(r) for r in rows]


def test_postgres_sink_writes_one_row(db_url):
    async def body(engine):
        sink = PostgresDeadLetterSink(engine)
        await sink.record(Position("test.topic", 2, 7), b"\xff not utf-8", "broken")
        await sink.record(Position("test.topic", 2, 8), None, "no value")
        return await dead_letter_rows(engine)

    rows = run_with_engine(db_url, body)
    assert [r[:5] for r in rows] == [
        ("test.topic", 2, 7, b"\xff not utf-8", "broken"),
        ("test.topic", 2, 8, None, "no value"),
    ]
    assert all(r[5].tzinfo is not None for r in rows)


def test_postgres_sink_keeps_one_row_per_position(db_url):
    # D-022: the same message delivered again keeps the first row and raises nothing.
    async def body(engine):
        sink = PostgresDeadLetterSink(engine)
        await sink.record(Position("test.topic", 0, 1), b"first", "first error")
        await sink.record(Position("test.topic", 0, 1), b"again", "second error")
        return await dead_letter_rows(engine)

    rows = run_with_engine(db_url, body)
    assert [r[:5] for r in rows] == [("test.topic", 0, 1, b"first", "first error")]


def test_failing_handler_end_to_end(db_url):
    # AC-5 on the real tables: one dead_letters row, no processed_events row, the next event is saved.
    async def failing(event, conn):
        await conn.execute(text("INSERT INTO test_writes (event_id) VALUES (:id)"), {"id": event.event_id})
        if event.event_id == EVENT_ID:
            raise RuntimeError("handler broke")

    value = encode(envelope())
    consumer = FakeConsumer([FakeMessage(value, offset=0), FakeMessage(encode(envelope(event_id=OTHER_ID)), offset=1)])

    async def body(engine):
        source = KafkaEventSource(consumer, dead_letters=PostgresDeadLetterSink(engine), sleep=FakeSleep())
        await source.consume(idempotent(engine, failing))
        async with engine.connect() as conn:
            writes = (await conn.execute(text("SELECT event_id FROM test_writes"))).scalars().all()
            processed = (await conn.execute(select(processed_events.c.event_id))).scalars().all()
        return list(writes), list(processed), await dead_letter_rows(engine)

    writes, processed, rows = run_with_engine(db_url, body)
    assert writes == [OTHER_ID]
    assert processed == [OTHER_ID]
    assert [r[:4] for r in rows] == [(TOPIC, 0, 0, value)]
    assert "handler broke" in rows[0][4]
    assert consumer.commits == [{(TOPIC, 0): 1}, {(TOPIC, 0): 2}]
