"""Add workflow_execution_id FK to scrap, bulk tables

Revision ID: a9b0c1d2e3f4
Revises: y7z8a9b0c1d2
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, None] = "y7z8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scrap_jobs",
        sa.Column("workflow_execution_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_scrap_jobs_workflow_execution_id",
        "scrap_jobs",
        "workflow_executions",
        ["workflow_execution_id"],
        ["id"],
    )
    op.add_column(
        "scrap_client_jobs",
        sa.Column("workflow_execution_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_scrap_client_jobs_workflow_execution_id",
        "scrap_client_jobs",
        "workflow_executions",
        ["workflow_execution_id"],
        ["id"],
    )
    op.add_column(
        "bulk_job_applications",
        sa.Column("workflow_execution_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_bulk_job_applications_workflow_execution_id",
        "bulk_job_applications",
        "workflow_executions",
        ["workflow_execution_id"],
        ["id"],
    )
    op.add_column(
        "bulk_job_application_email_sends",
        sa.Column("workflow_execution_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_bulk_job_application_email_sends_workflow_execution_id",
        "bulk_job_application_email_sends",
        "workflow_executions",
        ["workflow_execution_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_bulk_job_application_email_sends_workflow_execution_id",
        "bulk_job_application_email_sends",
        type_="foreignkey",
    )
    op.drop_column("bulk_job_application_email_sends", "workflow_execution_id")
    op.drop_constraint(
        "fk_bulk_job_applications_workflow_execution_id",
        "bulk_job_applications",
        type_="foreignkey",
    )
    op.drop_column("bulk_job_applications", "workflow_execution_id")
    op.drop_constraint(
        "fk_scrap_client_jobs_workflow_execution_id",
        "scrap_client_jobs",
        type_="foreignkey",
    )
    op.drop_column("scrap_client_jobs", "workflow_execution_id")
    op.drop_constraint(
        "fk_scrap_jobs_workflow_execution_id",
        "scrap_jobs",
        type_="foreignkey",
    )
    op.drop_column("scrap_jobs", "workflow_execution_id")
