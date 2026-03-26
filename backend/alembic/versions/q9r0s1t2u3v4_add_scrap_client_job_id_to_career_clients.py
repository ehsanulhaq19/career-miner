"""Add scrap_client_job_id foreign key to career_clients

Revision ID: q9r0s1t2u3v4
Revises: p8q9r0s1t2u3
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q9r0s1t2u3v4"
down_revision: Union[str, None] = "p8q9r0s1t2u3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "career_clients",
        sa.Column("scrap_client_job_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_career_clients_scrap_client_job_id",
        "career_clients",
        "scrap_client_jobs",
        ["scrap_client_job_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_career_clients_scrap_client_job_id",
        "career_clients",
        type_="foreignkey",
    )
    op.drop_column("career_clients", "scrap_client_job_id")
