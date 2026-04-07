from datetime import datetime

from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class CareerClientUpdate(BaseModel):
    """Schema for updating an existing career client."""

    emails: list[str] | None = None
    phone_numbers: list[str] | None = None
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
    phone_numbers: list[str] = []
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

    @field_validator("phone_numbers", mode="before")
    @classmethod
    def default_phone_numbers(cls, v: Any) -> list:
        if v is None:
            return []
        return v


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
    application_detail: str | None = None

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
    created_at: datetime
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


class CareerClientImportItem(BaseModel):
    """Single client row accepted by the import API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    emails: list[str] = Field(default_factory=list)
    official_website: str | None = Field(
        default=None,
        validation_alias=AliasChoices("official_website", "offical_website"),
    )
    name: str | None = None
    location: str | None = None
    detail: str | None = None
    phone_numbers: list[str] = Field(default_factory=list)

    @field_validator("emails", "phone_numbers", mode="before")
    @classmethod
    def coerce_string_or_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return []
            parts = []
            for sep in ("\n", ";", ","):
                if sep in stripped:
                    parts = [p.strip() for p in stripped.split(sep) if p.strip()]
                    break
            if not parts:
                parts = [stripped]
            return [str(p) for p in parts]
        if isinstance(v, list):
            return [str(x).strip() for x in v if x is not None and str(x).strip()]
        return []


class CareerClientImportRequest(BaseModel):
    """Request body for bulk import of career clients."""

    source: str = Field(min_length=1, max_length=500)
    clients: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class CareerClientImportErrorItem(BaseModel):
    """Describes one failed import row."""

    index: int
    record: dict[str, Any]
    message: str


class CareerClientImportResponse(BaseModel):
    """Result of a career client import batch."""

    created_count: int
    updated_count: int
    errors: list[CareerClientImportErrorItem]
