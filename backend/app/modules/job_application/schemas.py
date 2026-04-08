from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LiveJobApplicationAction(str, Enum):
    """
    Allowed actions when creating a job application from live-pasted job details.
    """

    CREATE_JOB_APPLICATION = "create_job_application"
    CREATE_AND_SEND_JOB_APPLICATION = "create_and_send_job_application"


class LiveJobApplicationCreateRequest(BaseModel):
    """Schema for creating a job application from unstructured job text via LLM extraction."""

    job_details: str = Field(..., min_length=1)
    resume_id: int
    action: LiveJobApplicationAction


class JobApplicationCreateRequest(BaseModel):
    """Schema for creating a job application."""

    career_job_id: int
    resume_id: int


class BulkJobApplicationCreateRequest(BaseModel):
    """Schema for creating bulk job applications."""

    resume_id: int
    career_job_ids: list[int]


class BulkJobApplicationUpdateRequest(BaseModel):
    """Schema for bulk-updating job applications (is_active only)."""

    job_application_ids: list[int]
    is_active: bool


class BulkJobApplicationUpdateResponse(BaseModel):
    """Schema for bulk job application update result."""

    updated_count: int


class BulkJobApplicationEmailSendRequest(BaseModel):
    """Schema for bulk job application email send request."""

    job_application_ids: list[int]
    min_similarity_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="If set, only send for applications with similarity_score >= this value (0–100).",
    )


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
    email_send_count: int = 0


class EmailLogResponse(BaseModel):
    """Schema for email log response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    content: str | None
    file_attachment: str | None
    to_email: str
    from_email: str | None
    response: str | None
    status: str
    created_at: datetime


class BulkJobApplicationEmailSendLogResponse(BaseModel):
    """Schema for bulk job application email send log response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    bulk_job_application_email_send_id: int
    action: str
    progress: int
    status: str
    details: str | None
    meta_data: dict
    created_at: datetime


class BulkJobApplicationEmailSendLogListResponse(BaseModel):
    """Schema for list of bulk job application email send logs."""

    items: list[BulkJobApplicationEmailSendLogResponse]


class JobApplicationListResponse(BaseModel):
    """Schema for paginated list of job applications."""

    items: list[JobApplicationResponse]
    total: int
    page: int
    limit: int


class JobApplicationDateGroupResponse(BaseModel):
    """Schema for a date group in the job applications tabular UI."""

    date: str
    application_count: int


class JobApplicationDateGroupListResponse(BaseModel):
    """Schema for paginated list of job application date groups."""

    items: list[JobApplicationDateGroupResponse]
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
