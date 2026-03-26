from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class CareerClientUpdate(BaseModel):
    """Schema for updating an existing career client."""

    emails: list[str] | None = None
    name: str | None = None
    official_website: str | None = None
    location: str | None = None
    link: str | None = None
    detail: str | None = None
    is_active: bool | None = None


class CareerClientBulkUpdate(BaseModel):
    """Schema for bulk updating career clients by location."""

    is_active: bool | None = None


class CareerClientResponse(BaseModel):
    """Schema for career client response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    emails: list[str] = []
    official_website: str | None = None
    name: str | None
    location: str | None
    detail: str | None
    link: str | None
    size: str | None
    meta_data: dict | None = None
    scrap_client_job_id: int | None = None
    is_active: bool
    created_at: datetime


class CareerClientListResponse(BaseModel):
    """Schema for paginated list of career clients."""

    items: list[CareerClientResponse]
    total: int
    page: int
    limit: int


class CareerClientLocationsResponse(BaseModel):
    """Schema for list of distinct career client locations."""

    locations: list[str]


class CareerClientScanCriteria(BaseModel):
    """Schema for career client scan criteria to deactivate non-compliant clients."""

    min_description: int | None = None
    matching_words: str | None = None

    @field_validator("min_description")
    @classmethod
    def min_description_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("min_description must be non-negative")
        return v


class CareerClientScanResponse(BaseModel):
    """Schema for career client scan result."""

    deactivated_count: int


class ValidateEmailsRequest(BaseModel):
    """Schema for validating client emails request."""

    client_ids: list[int] | None = None
    all_clients: bool = False

    @model_validator(mode="after")
    def validate_params(self):
        if self.all_clients:
            return self
        if not self.client_ids or len(self.client_ids) == 0:
            raise ValueError("Either client_ids or all_clients=true required")
        return self


class ClientInvalidEmailsItem(BaseModel):
    """Schema for a client with its invalid emails."""

    client_id: int
    client_name: str
    invalid_emails: list[str]


class RemoveInvalidEmailsItem(BaseModel):
    """Schema for single client invalid emails removal."""

    client_id: int
    invalid_emails: list[str]


class RemoveInvalidEmailsRequest(BaseModel):
    """Schema for removing invalid emails from clients."""

    clients: list[RemoveInvalidEmailsItem]


class ValidateEmailsStartedResponse(BaseModel):
    """Response when email validation is started in the background."""

    status: str = "started"


class CareerClientBulkEmailRecipient(BaseModel):
    """Single recipient for bulk career client outreach email."""

    client_id: int
    client_email: str


class CareerClientBulkEmailSendRequest(BaseModel):
    """Request body for bulk career client outreach emails."""

    resume_id: int
    recipients: list[CareerClientBulkEmailRecipient]

    @field_validator("recipients")
    @classmethod
    def recipients_non_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one recipient is required")
        return v


class CareerClientEmailRowResponse(BaseModel):
    """One career client email address with historical send count."""

    client_id: int
    client_name: str | None
    official_website: str | None
    location: str | None
    client_email: str
    email_count: int


class CareerClientEmailRowsListResponse(BaseModel):
    """Paginated list of career client email rows."""

    items: list[CareerClientEmailRowResponse]
    total: int
    page: int
    limit: int


class BulkCareerClientEmailSendLogResponse(BaseModel):
    """Schema for bulk career client email send log response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    bulk_career_client_email_send_id: int
    action: str
    progress: int
    status: str
    details: str | None
    meta_data: dict
    created_at: datetime


class BulkCareerClientEmailSendLogListResponse(BaseModel):
    """Schema for list of bulk career client email send logs."""

    items: list[BulkCareerClientEmailSendLogResponse]
