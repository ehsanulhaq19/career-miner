"""Add created_by (users FK) for user-scoped domain tables

Revision ID: y7z8a9b0c1d2
Revises: x8y9z403ad44
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "y7z8a9b0c1d2"
down_revision: Union[str, None] = "x8y9z403ad44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = (
    "career_clients",
    "client_sites",
    "career_jobs",
    "job_applications",
    "job_sites",
    "scrap_client_jobs",
    "scrap_jobs",
)


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("created_by", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            f"fk_{table}_created_by_users",
            table,
            "users",
            ["created_by"],
            ["id"],
        )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE job_applications SET created_by = user_id WHERE created_by IS NULL"
        )
    )
    uid = conn.execute(sa.text("SELECT id FROM users ORDER BY id ASC LIMIT 1")).scalar()
    if uid is not None:
        for table in (
            "career_clients",
            "client_sites",
            "career_jobs",
            "job_sites",
            "scrap_client_jobs",
            "scrap_jobs",
        ):
            conn.execute(
                sa.text(
                    f"UPDATE {table} SET created_by = :uid WHERE created_by IS NULL"
                ),
                {"uid": uid},
            )

    for table in _TABLES:
        op.alter_column(
            table,
            "created_by",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_constraint(
            f"fk_{table}_created_by_users",
            table,
            type_="foreignkey",
        )
        op.drop_column(table, "created_by")
