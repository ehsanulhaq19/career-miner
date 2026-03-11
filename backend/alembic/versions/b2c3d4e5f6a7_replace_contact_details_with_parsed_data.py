"""Replace contact_details with parsed_data

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("career_jobs", "contact_details")
    op.add_column(
        "career_jobs",
        sa.Column("parsed_data", sa.JSON(), nullable=True, server_default=sa.text("'{}'::json")),
    )


def downgrade() -> None:
    op.drop_column("career_jobs", "parsed_data")
    op.add_column(
        "career_jobs",
        sa.Column("contact_details", sa.Text(), nullable=True),
    )
