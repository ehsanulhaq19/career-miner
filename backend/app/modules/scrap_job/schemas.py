from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScrapJobResponse(BaseModel):
    """Schema for scrap job response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    job_site_id: int
    status: str
    created_at: datetime
    updated_at: datetime


class ScrapJobListResponse(BaseModel):
    """Schema for paginated list of scrap jobs."""

    items: list[ScrapJobResponse]
    total: int
