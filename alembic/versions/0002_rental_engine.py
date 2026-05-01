"""rental engine: add users table, restructure rentals (user_id, start_time, end_time)

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New users table.
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Restructure rentals: drop customer_name, rename date columns,
    # make end_time nullable, add user_id FK.
    op.drop_column("rentals", "customer_name")
    op.alter_column(
        "rentals",
        "start_date",
        new_column_name="start_time",
        server_default=sa.func.now(),
    )
    op.alter_column("rentals", "end_date", new_column_name="end_time", nullable=True)
    op.add_column(
        "rentals",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("ix_rentals_user_id", "rentals", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_rentals_user_id", table_name="rentals")
    op.drop_column("rentals", "user_id")

    # Active rentals have NULL end_time; the old schema required NOT NULL.
    # Backfill before tightening the constraint, otherwise populated tables
    # blow up on the ALTER.
    op.execute("UPDATE rentals SET end_time = now() WHERE end_time IS NULL")
    op.alter_column("rentals", "end_time", new_column_name="end_date", nullable=False)
    op.alter_column(
        "rentals", "start_time", new_column_name="start_date", server_default=None
    )

    # Same pattern for customer_name: add nullable + backfill, then NOT NULL.
    # Adding a NOT NULL column with no default to a populated table fails
    # ("column ... contains null values").
    op.add_column(
        "rentals",
        sa.Column("customer_name", sa.String(length=200), nullable=True),
    )
    op.execute("UPDATE rentals SET customer_name = '' WHERE customer_name IS NULL")
    op.alter_column("rentals", "customer_name", nullable=False)

    op.drop_table("users")
