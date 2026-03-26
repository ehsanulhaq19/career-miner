"""Create career client bulk email and pivot tables

Revision ID: p8q9r0s1t2u3
Revises: o6p7q8r9s0t1
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p8q9r0s1t2u3"
down_revision: Union[str, None] = "o6p7q8r9s0t1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bulk_career_client_email_sends",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "bulk_career_client_email_send_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bulk_career_client_email_send_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(
            ["bulk_career_client_email_send_id"],
            ["bulk_career_client_email_sends.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "career_client_email_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("career_client_id", sa.Integer(), nullable=False),
        sa.Column("email_log_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["career_client_id"], ["career_clients.id"], ),
        sa.ForeignKeyConstraint(["email_log_id"], ["email_logs.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("career_client_email_logs")
    op.drop_table("bulk_career_client_email_send_logs")
    op.drop_table("bulk_career_client_email_sends")
