"""Make career_jobs.job_site_id and career_jobs.scrap_job_id nullable

Revision ID: x8y9z403ad44
Revises: w5x6y7z8a9b0
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x8y9z403ad44"
down_revision: Union[str, None] = "w5x6y7z8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "career_jobs",
        "job_site_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "career_jobs",
        "scrap_job_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "career_jobs",
        "job_site_id",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "career_jobs",
        "scrap_job_id",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )
