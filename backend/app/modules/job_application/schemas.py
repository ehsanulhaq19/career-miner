from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobApplicationCreateRequest(BaseModel):
    """Schema for creating a job application."""

    career_job_id: int
    resume_id: int


class JobApplicationUpdate(BaseModel):
    """Schema for updating a job application."""

    is_active: bool | None = None


class JobApplicationResponse(BaseModel):
    """Schema for job application response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    application_name: str
    resume_id: int
    user_id: int
    applied_on: datetime
    is_active: bool
    subject: str | None
    cover_letter: str | None
    output_resume_path: str | None
    career_job_id: int
    similarity_score: float | None = None
    meta_data: dict = Field(default_factory=dict)
    is_email_send: bool
    to_emails: list[str] = Field(default_factory=list)
    created_at: datetime
    career_job_title: str | None = None
    career_client_id: int | None = None
    career_client_name: str | None = None
    job_site_name: str | None = None
    resume_name: str | None = None


class JobApplicationListResponse(BaseModel):
    """Schema for paginated list of job applications."""

    items: list[JobApplicationResponse]
    total: int
    page: int
    limit: int
