"""Add scrappers, scrap_job_files, scrap_client_files

Revision ID: u4v5w6x7y8z9
Revises: t3u4v5w6x7y8
Create Date: 2026-03-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "u4v5w6x7y8z9"
down_revision: Union[str, None] = "t3u4v5w6x7y8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scrappers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_path", sa.String(length=2048), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scrap_job_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scrap_job_id", sa.Integer(), nullable=False),
        sa.Column("scrapper_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scrap_job_id"],
            ["scrap_jobs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["scrapper_id"],
            ["scrappers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scrap_client_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scrap_client_job_id", sa.Integer(), nullable=False),
        sa.Column("scrapper_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scrap_client_job_id"],
            ["scrap_client_jobs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["scrapper_id"],
            ["scrappers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("scrap_client_files")
    op.drop_table("scrap_job_files")
    op.drop_table("scrappers")
