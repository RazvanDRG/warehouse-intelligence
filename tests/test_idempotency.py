"""AC-2..AC-4, AC-6, AC-7: the duplicate check on processed_events, on the local test database."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime

import pytest
import yaml
from alembic import command
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from adapters.warehouse.kafka_source import KafkaEventSource
from core.db.tables import processed_events
from core.events import Event, Position
from core.idempotency import idempotent
from tests.dbsupport import ROOT, alembic_config, check_test_database_url, database_url_or_skip
from tests.test_events import FakeConsumer, FakeMessage, encode, envelope

EVENT_A = "0b6f9c1e-4a52-4c8e-9a51-2f6d1c3e7a10"
EVENT_B = "5d2a7e40-9c1b-4f3e-8a6d-1e2f3a4b5c6d"


def make_event(event_id: str = EVENT_A, offset: int = 0) -> Event:
    return Event(
        event_id=event_id,
        type="test.happened",
        occurred_at=datetime(2026, 11, 22, 9, 0, tzinfo=UTC),
        entity="1",
        payload={},
        position=Position(topic="test.topic", partition=0, offset=offset),
    )


@pytest.fixture
def db_url():
    url = database_url_or_skip()
    command.upgrade(alembic_config(url), "head")

    async def reset():
        engine = create_async_engine(url)
        try:
            async with engine.begin() as conn:
                # A test-only table standing in for whatever a real handler writes.
                await conn.execute(text("CREATE TABLE IF NOT EXISTS test_writes (event_id text NOT NULL)"))
                await conn.execute(text("DELETE FROM test_writes"))
                await conn.execute(processed_events.delete())
        finally:
            await engine.dispose()

    asyncio.run(reset())
    return url


async def write_handler(event: Event, conn: AsyncConnection) -> None:
    await conn.execute(text("INSERT INTO test_writes (event_id) VALUES (:id)"), {"id": event.event_id})


async def counts(conn: AsyncConnection) -> tuple[list[str], list[tuple]]:
    writes = (await conn.execute(text("SELECT event_id FROM test_writes ORDER BY event_id"))).scalars().all()
    rows = (
        await conn.execute(
            select(
                processed_events.c.event_id,
                processed_events.c.topic,
                processed_events.c.partition,
                processed_events.c.offset,
            ).order_by(processed_events.c.event_id)
        )
    ).all()
    return list(writes), [tuple(r) for r in rows]


def run_with_engine(url, body):
    async def main():
        engine = create_async_engine(url)
        try:
            return await body(engine)
        finally:
            await engine.dispose()

    return asyncio.run(main())


# AC-2: first delivery


def test_first_delivery_runs_handler_and_records_event(db_url):
    async def body(engine):
        await idempotent(engine, write_handler)(make_event(offset=5))
        async with engine.connect() as conn:
            return await counts(conn)

    writes, rows = run_with_engine(db_url, body)
    assert writes == [EVENT_A]
    assert rows == [(EVENT_A, "test.topic", 0, 5)]


def test_processed_at_is_filled_by_the_database(db_url):
    async def body(engine):
        await idempotent(engine, write_handler)(make_event())
        async with engine.connect() as conn:
            return (await conn.execute(select(processed_events.c.processed_at))).scalar_one()

    processed_at = run_with_engine(db_url, body)
    assert processed_at.tzinfo is not None


# AC-3: duplicates are skipped


def test_duplicate_is_skipped(db_url):
    calls = []

    async def handler(event, conn):
        calls.append(event.event_id)
        await write_handler(event, conn)

    async def body(engine):
        wrapped = idempotent(engine, handler)
        await wrapped(make_event(offset=0))
        # The same event delivered again, for example after a lost commit, at a later offset.
        await wrapped(make_event(offset=7))
        async with engine.connect() as conn:
            return await counts(conn)

    writes, rows = run_with_engine(db_url, body)
    assert calls == [EVENT_A]
    assert writes == [EVENT_A]
    assert rows == [(EVENT_A, "test.topic", 0, 0)]


# AC-4: a failing handler saves nothing


def test_handler_failure_rolls_back_both(db_url):
    async def failing(event, conn):
        await write_handler(event, conn)
        raise RuntimeError("handler broke")

    async def body(engine):
        with pytest.raises(RuntimeError, match="handler broke"):
            await idempotent(engine, failing)(make_event())
        async with engine.connect() as conn:
            after_failure = await counts(conn)
        # The next delivery is not treated as a duplicate.
        await idempotent(engine, write_handler)(make_event())
        async with engine.connect() as conn:
            return after_failure, await counts(conn)

    after_failure, after_retry = run_with_engine(db_url, body)
    assert after_failure == ([], [])
    assert after_retry == ([EVENT_A], [(EVENT_A, "test.topic", 0, 0)])


# AC-6: a replay through a new consumer group handles each event once


def test_replay_handles_each_event_once(db_url):
    def messages():
        return [
            FakeMessage(encode(envelope(event_id=EVENT_A)), topic="wms.pick.completed", partition=1, offset=3),
            FakeMessage(encode(envelope(event_id=EVENT_B)), topic="wms.order.audit", partition=0, offset=8),
        ]

    calls = []

    async def handler(event, conn):
        calls.append(event.event_id)
        await write_handler(event, conn)

    async def body(engine):
        first, replay = FakeConsumer(messages()), FakeConsumer(messages())
        await KafkaEventSource(first).consume(idempotent(engine, handler))
        # A new KAFKA_GROUP_ID starts from the earliest offset and delivers every kept message again.
        await KafkaEventSource(replay).consume(idempotent(engine, handler))
        async with engine.connect() as conn:
            return first, replay, await counts(conn)

    first, replay, (writes, rows) = run_with_engine(db_url, body)
    assert calls == [EVENT_A, EVENT_B]
    assert writes == sorted([EVENT_A, EVENT_B])
    assert rows == sorted([(EVENT_A, "wms.pick.completed", 1, 3), (EVENT_B, "wms.order.audit", 0, 8)])
    # Skipped duplicates are still committed, so the new group moves past them.
    assert replay.commits == first.commits == [{("wms.pick.completed", 1): 4}, {("wms.order.audit", 0): 9}]


# Needs no database


def test_event_without_position_is_refused():
    # The engine is never reached: the check comes first.
    with pytest.raises(ValueError, match="position"):
        asyncio.run(idempotent(None, write_handler)(replace(make_event(), position=None)))


# AC-7: only a local *_test database


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://wi:fake@db.example.supabase.co:5432/wi_test",
        "postgresql+asyncpg://wi:fake@10.0.0.5:5432/wi_test",
        "postgresql+asyncpg://wi:fake@localhost:5433/wi",
        "postgresql+asyncpg://wi:fake@localhost:5433/postgres",
    ],
)
def test_refuses_non_local_database(url):
    with pytest.raises(ValueError, match="TEST_DATABASE_URL"):
        check_test_database_url(url)


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "postgres"])
def test_accepts_local_test_database(host):
    url = f"postgresql+asyncpg://wi:fake@{host}:5432/wi_test"
    assert check_test_database_url(url) == url


# D-016, D-017: CI runs the database tests on its own Postgres; the name is documented without a value


def test_ci_runs_tests_against_a_postgres_service():
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    check = workflow["jobs"]["check"]
    assert check["services"]["postgres"]["image"] == "pgvector/pgvector:pg16"
    pytest_step = next(s for s in check["steps"] if s.get("run") == "pytest -q")
    url = pytest_step["env"]["TEST_DATABASE_URL"]
    assert check_test_database_url(url) == url


def test_env_example_lists_test_database_url():
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "# TEST_DATABASE_URL=" in lines
