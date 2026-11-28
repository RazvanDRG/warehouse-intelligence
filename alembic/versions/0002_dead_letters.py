"""dead_letters: messages that could not be handled, kept with their error so nothing is lost silently.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dead_letters",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("partition", sa.Integer(), nullable=False),
        sa.Column("offset", sa.BigInteger(), nullable=False),
        # Raw message bytes; NULL for a message with no value (a Kafka tombstone).
        sa.Column("payload", sa.LargeBinary(), nullable=True),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # A message delivered again is stored once (D-022).
        sa.UniqueConstraint("topic", "partition", "offset", name="uq_dead_letters_position"),
    )


def downgrade() -> None:
    op.drop_table("dead_letters")
