"""Tables in WI's own Postgres. Schema changes go through an Alembic migration (alembic/versions)."""

from sqlalchemy import BigInteger, Column, DateTime, Integer, MetaData, Table, Text, func

metadata = MetaData()

# One row per event already handled; a second delivery of the same event_id is skipped.
processed_events = Table(
    "processed_events",
    metadata,
    Column("event_id", Text, primary_key=True),
    Column("topic", Text, nullable=False),
    Column("partition", Integer, nullable=False),
    # "offset" is an SQL keyword; SQLAlchemy quotes it in every statement.
    Column("offset", BigInteger, nullable=False),
    Column("processed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
