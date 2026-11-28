"""Tables in WI's own Postgres. Schema changes go through an Alembic migration (alembic/versions)."""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Identity,
    Integer,
    LargeBinary,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    func,
)

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

# Messages that could not be handled (unreadable, or a handler that kept failing), with their error.
dead_letters = Table(
    "dead_letters",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("topic", Text, nullable=False),
    Column("partition", Integer, nullable=False),
    Column("offset", BigInteger, nullable=False),
    # Raw message bytes; NULL for a message with no value (a tombstone).
    Column("payload", LargeBinary, nullable=True),
    Column("error", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # A message delivered again is stored once (D-022).
    UniqueConstraint("topic", "partition", "offset", name="uq_dead_letters_position"),
)
