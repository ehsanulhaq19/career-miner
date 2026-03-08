"""Alter user password column to Text

Revision ID: a1b2c3d4e5f6
Revises: 1cdb270c8a7d
Create Date: 2026-03-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "1cdb270c8a7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "password",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "password",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
