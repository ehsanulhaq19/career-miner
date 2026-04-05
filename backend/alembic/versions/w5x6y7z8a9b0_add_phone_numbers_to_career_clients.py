"""Add phone_numbers JSON column to career_clients

Revision ID: w5x6y7z8a9b0
Revises: u4v5w6x7y8z9
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w5x6y7z8a9b0"
down_revision: Union[str, None] = "u4v5w6x7y8z9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "career_clients",
        sa.Column(
            "phone_numbers",
            sa.JSON(),
            nullable=True,
            server_default=sa.text("'[]'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("career_clients", "phone_numbers")
