"""Add meta_data column to scrap_jobs table

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scrap_jobs",
        sa.Column("meta_data", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scrap_jobs", "meta_data")
