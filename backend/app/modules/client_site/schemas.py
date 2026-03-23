from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClientSiteCreate(BaseModel):
    """Schema for creating a new client site."""

    name: str
    url: str
    is_active: bool = True
    scrap_duration: int = 60


class ClientSiteUpdate(BaseModel):
    """Schema for updating an existing client site."""

    name: str | None = None
    url: str | None = None
    is_active: bool | None = None
    scrap_duration: int | None = None


class ClientSiteResponse(BaseModel):
    """Schema for client site response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    scrap_duration: int
    last_scrapped: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClientSiteListResponse(BaseModel):
    """Schema for paginated list of client sites."""

    items: list[ClientSiteResponse]
    total: int
