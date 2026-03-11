"""Create career clients table and add career_client_id to career_jobs

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-03-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "career_clients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("emails", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("name", sa.String(length=500), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("size", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "career_jobs",
        sa.Column("career_client_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_career_jobs_career_client_id",
        "career_jobs",
        "career_clients",
        ["career_client_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_career_jobs_career_client_id",
        "career_jobs",
        type_="foreignkey",
    )
    op.drop_column("career_jobs", "career_client_id")
    op.drop_table("career_clients")
