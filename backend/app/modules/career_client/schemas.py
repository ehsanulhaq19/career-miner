from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
