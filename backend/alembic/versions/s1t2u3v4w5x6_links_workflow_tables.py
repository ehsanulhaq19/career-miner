"""Career-scrap link pivots, job application email bulk ref, workflow tables

Revision ID: s1t2u3v4w5x6
Revises: r0s1t2u3v4w5
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s1t2u3v4w5x6"
down_revision: Union[str, None] = "r0s1t2u3v4w5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "career_client_scrap_client_job_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("career_client_id", sa.Integer(), nullable=False),
        sa.Column("scrap_client_job_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["career_client_id"], ["career_clients.id"]),
        sa.ForeignKeyConstraint(["scrap_client_job_id"], ["scrap_client_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "career_job_scrap_job_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("career_job_id", sa.Integer(), nullable=False),
        sa.Column("scrap_job_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["career_job_id"], ["career_jobs.id"]),
        sa.ForeignKeyConstraint(["scrap_job_id"], ["scrap_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "job_application_bulk_job_application_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_application_id", sa.Integer(), nullable=False),
        sa.Column("bulk_job_application_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["job_application_id"], ["job_applications.id"]),
        sa.ForeignKeyConstraint(["bulk_job_application_id"], ["bulk_job_applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "job_application_email_logs",
        sa.Column("bulk_job_application_email_send_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_jael_bulk_job_application_email_send",
        "job_application_email_logs",
        "bulk_job_application_email_sends",
        ["bulk_job_application_email_send_id"],
        ["id"],
    )
    op.create_table(
        "workflows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("next_execution_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_execution_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workflow_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("linked_task_model", sa.String(length=128), nullable=False),
        sa.Column("linked_task_model_data", sa.JSON(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workflow_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workflow_execution_id", sa.Integer(), nullable=False),
        sa.Column("workflow_task_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("created_resource_type", sa.String(length=128), nullable=True),
        sa.Column("created_resource_id", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["workflow_execution_id"], ["workflow_executions.id"]),
        sa.ForeignKeyConstraint(["workflow_task_id"], ["workflow_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workflow_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workflow_job_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["workflow_job_id"], ["workflow_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("workflow_logs")
    op.drop_table("workflow_jobs")
    op.drop_table("workflow_executions")
    op.drop_table("workflow_tasks")
    op.drop_table("workflows")
    op.drop_constraint("fk_jael_bulk_job_application_email_send", "job_application_email_logs", type_="foreignkey")
    op.drop_column("job_application_email_logs", "bulk_job_application_email_send_id")
    op.drop_table("job_application_bulk_job_application_links")
    op.drop_table("career_job_scrap_job_links")
    op.drop_table("career_client_scrap_client_job_links")
