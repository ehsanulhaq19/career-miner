from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScrapJobStartRequest(BaseModel):
    """Schema for starting a new scrap job."""

    job_site_id: int
    load_more_on_scroll: bool = False
    max_scroll: int = Field(default=10, ge=1, le=100)


class TestScrapRequest(BaseModel):
    """Schema for executing a test scrap job with custom parameters."""

    job_site_id: int
    categories: list[str] = Field(default_factory=list)
    max_pages_per_scrap: int = Field(default=5, ge=1, le=100)
    process_with_llm: bool = True
    load_more_on_scroll: bool = False
    max_scroll: int = Field(default=10, ge=1, le=100)


class ScrapJobResponse(BaseModel):
    """Schema for scrap job response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    job_site_id: int
    status: str
    meta_data: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("meta_data", mode="before")
    @classmethod
    def coerce_meta_data(cls, v: dict | None) -> dict:
        return v if v is not None else {}


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
