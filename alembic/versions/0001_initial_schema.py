"""initial schema: cars and rentals

Revision ID: 0001
Revises:
Create Date: 2026-04-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


carstatus_enum = sa.Enum(
    "AVAILABLE",
    "IN_USE",
    "MAINTENANCE",
    name="carstatus",
)


def upgrade() -> None:
    # Enum type is auto-created by op.create_table when it sees the column.
    op.create_table(
        "cars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            carstatus_enum,
            nullable=False,
            server_default="AVAILABLE",
        ),
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
    op.create_index("ix_cars_status", "cars", ["status"])

    op.create_table(
        "rentals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "car_id",
            sa.Integer(),
            sa.ForeignKey("cars.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
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
    op.create_index("ix_rentals_car_id", "rentals", ["car_id"])


def downgrade() -> None:
    op.drop_index("ix_rentals_car_id", table_name="rentals")
    op.drop_table("rentals")

    op.drop_index("ix_cars_status", table_name="cars")
    op.drop_table("cars")

    # Tables are gone; safe to drop the enum type now.
    carstatus_enum.drop(op.get_bind(), checkfirst=True)
