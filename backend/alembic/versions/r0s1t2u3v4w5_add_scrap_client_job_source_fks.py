"""Add client_site_id and source_url to scrap_client_jobs

Revision ID: r0s1t2u3v4w5
Revises: q9r0s1t2u3v4
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r0s1t2u3v4w5"
down_revision: Union[str, None] = "q9r0s1t2u3v4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scrap_client_jobs",
        sa.Column("client_site_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "scrap_client_jobs",
        sa.Column("source_url", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_scrap_client_jobs_client_site_id",
        "scrap_client_jobs",
        "client_sites",
        ["client_site_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_scrap_client_jobs_client_site_id",
        "scrap_client_jobs",
        type_="foreignkey",
    )
    op.drop_column("scrap_client_jobs", "source_url")
    op.drop_column("scrap_client_jobs", "client_site_id")
