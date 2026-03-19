"""Create job_applications table

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-03-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i0j1k2l3m4n5"
down_revision: Union[str, None] = "h9i0j1k2l3m4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_name", sa.String(length=100), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("applied_on", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column("output_resume_path", sa.String(length=1000), nullable=True),
        sa.Column("career_job_id", sa.Integer(), nullable=False),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("is_email_send", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("to_emails", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["career_job_id"], ["career_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("job_applications")
