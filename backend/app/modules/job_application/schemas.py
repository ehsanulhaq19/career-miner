from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobApplicationCreateRequest(BaseModel):
    """Schema for creating a job application."""

    career_job_id: int
    resume_id: int


class BulkJobApplicationCreateRequest(BaseModel):
    """Schema for creating bulk job applications."""

    resume_id: int
    career_job_ids: list[int]


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


class BulkJobApplicationResponse(BaseModel):
    """Schema for bulk job application response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    user_id: int
    resume_id: int
    status: str
    meta_data: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("meta_data", mode="before")
    @classmethod
    def coerce_meta_data(cls, v: dict | None) -> dict:
        return v if v is not None else {}


class BulkJobApplicationLogResponse(BaseModel):
    """Schema for bulk job application log response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    bulk_job_application_id: int
    action: str
    progress: int
    status: str
    details: str | None
    meta_data: dict
    created_at: datetime


class BulkJobApplicationLogListResponse(BaseModel):
    """Schema for list of bulk job application logs."""

    items: list[BulkJobApplicationLogResponse]
