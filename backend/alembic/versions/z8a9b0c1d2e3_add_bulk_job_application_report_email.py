"""Add bulk job application report email tables

Revision ID: z8a9b0c1d2e3
Revises: y7z8a9b0c1d2
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z8a9b0c1d2e3"
down_revision: Union[str, None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bulk_job_application_report_emails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("send_to_email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("report_pdf_path", sa.String(length=1000), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("workflow_execution_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_execution_id"], ["workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "bulk_job_application_report_email_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bulk_job_application_report_email_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(
            ["bulk_job_application_report_email_id"],
            ["bulk_job_application_report_emails.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("bulk_job_application_report_email_logs")
    op.drop_table("bulk_job_application_report_emails")
