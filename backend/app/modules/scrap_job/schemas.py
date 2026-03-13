from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScrapJobStartRequest(BaseModel):
    """Schema for starting a new scrap job."""

    job_site_id: int


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


class ScrapJobLogResponse(BaseModel):
    """Schema for scrap job log response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    scrap_job_id: int
    action: str
    progress: int
    status: str
    details: str | None
    meta_data: dict
    created_at: datetime


class ScrapJobLogListResponse(BaseModel):
    """Schema for list of scrap job logs."""

    items: list[ScrapJobLogResponse]
