"""Add min_similarity_score to bulk_job_application_email_sends

Revision ID: t3u4v5w6x7y8
Revises: s1t2u3v4w5x6
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t3u4v5w6x7y8"
down_revision: Union[str, None] = "s1t2u3v4w5x6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bulk_job_application_email_sends",
        sa.Column("min_similarity_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bulk_job_application_email_sends", "min_similarity_score")
