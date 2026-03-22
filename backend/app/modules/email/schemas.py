from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SendEmailRequest(BaseModel):
    """Schema for sending an email request."""

    recipient: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, description="Email subject")
    content: str = Field(..., description="Email body content")


class SendEmailResponse(BaseModel):
    """Schema for send email response."""

    success: bool = Field(..., description="Whether the email was sent successfully")
    message: str = Field(..., description="Status message")


class JobEmailLogItemResponse(BaseModel):
    """Schema for job email log list item."""

    id: int
    subject: str
    content: str | None
    file_attachment: str | None
    to_email: str
    from_email: str | None
    response: str | None
    status: str
    created_at: datetime
    job_application_id: int
    career_job_id: int
    career_job_title: str
    career_client_id: int | None
    career_client_name: str | None


class JobEmailLogListResponse(BaseModel):
    """Schema for paginated job email logs list."""

    items: list[JobEmailLogItemResponse]
    total: int
    page: int
    limit: int


class JobEmailLogDetailResponse(BaseModel):
    """Schema for job email log detail with linked job and client data."""

    id: int
    subject: str
    content: str | None
    file_attachment: str | None
    to_email: str
    from_email: str | None
    response: str | None
    status: str
    created_at: datetime
    job_application: dict
    career_job: dict
    career_client: dict | None
