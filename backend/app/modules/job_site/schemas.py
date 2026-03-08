from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobSiteCreate(BaseModel):
    """Schema for creating a new job site."""

    name: str
    url: str
    is_active: bool = True
    scrap_duration: int = 60
    categories: list[str] = []


class JobSiteUpdate(BaseModel):
    """Schema for updating an existing job site."""

    name: str | None = None
    url: str | None = None
    is_active: bool | None = None
    scrap_duration: int | None = None
    categories: list[str] | None = None


class JobSiteResponse(BaseModel):
    """Schema for job site response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    scrap_duration: int
    last_scrapped: datetime | None
    is_active: bool
    categories: list[str]
    created_at: datetime
    updated_at: datetime


class JobSiteListResponse(BaseModel):
    """Schema for paginated list of job sites."""

    items: list[JobSiteResponse]
    total: int
