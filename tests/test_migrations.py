"""AC-1: the Alembic migrations go up, down and up again on the local test database."""

import asyncio

from alembic import command
from sqlalchemy import BigInteger, Integer, Text, inspect
from sqlalchemy.ext.asyncio import create_async_engine

from tests.dbsupport import alembic_config, database_url_or_skip


async def table_columns(url: str) -> dict[str, dict]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:

            def read(sync_conn):
                inspector = inspect(sync_conn)
                if not inspector.has_table("processed_events"):
                    return {}
                pk = inspector.get_pk_constraint("processed_events")["constrained_columns"]
                return {
                    c["name"]: {**c, "primary_key": c["name"] in pk} for c in inspector.get_columns("processed_events")
                }

            return await conn.run_sync(read)
    finally:
        await engine.dispose()


def test_upgrade_downgrade_upgrade():
    url = database_url_or_skip()
    config = alembic_config(url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")
    assert asyncio.run(table_columns(url)) == {}, "downgrade left processed_events behind"

    command.upgrade(config, "head")
    columns = asyncio.run(table_columns(url))
    assert list(columns) == ["event_id", "topic", "partition", "offset", "processed_at"]
    assert [name for name, c in columns.items() if c["primary_key"]] == ["event_id"]
    assert isinstance(columns["event_id"]["type"], Text)
    assert isinstance(columns["topic"]["type"], Text)
    assert isinstance(columns["partition"]["type"], Integer)
    assert isinstance(columns["offset"]["type"], BigInteger)
    assert all(not c["nullable"] for c in columns.values())
    assert columns["processed_at"]["default"] is not None
    assert columns["processed_at"]["type"].timezone is True
