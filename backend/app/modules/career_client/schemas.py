from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    created_at: datetime


class CareerClientListResponse(BaseModel):
    """Schema for paginated list of career clients."""

    items: list[CareerClientResponse]
    total: int
    page: int
    limit: int
