from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScrapClientStartRequest(BaseModel):
    """Schema for starting a new scrap client job."""

    client_ids: list[int] | None = None
    only_clients_without_emails: bool = False


class TestScrapClientRequest(BaseModel):
    """Schema for executing a test scrap client job with custom parameters."""

    client_ids: list[int] = []
    only_clients_without_emails: bool = False
    url: str | None = None


class ScrapClientJobResponse(BaseModel):
    """Schema for scrap client job response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str
    meta_data: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @field_validator("meta_data", mode="before")
    @classmethod
    def coerce_meta_data(cls, v: dict | None) -> dict:
        return v if v is not None else {}


class ScrapClientJobListResponse(BaseModel):
    """Schema for paginated list of scrap client jobs."""

    items: list[ScrapClientJobResponse]
    total: int


class ScrapClientLogResponse(BaseModel):
    """Schema for scrap client job log response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    scrap_client_job_id: int
    action: str
    progress: int
    status: str
    details: str | None
    meta_data: dict = Field(default_factory=dict)
    created_at: datetime

    @field_validator("meta_data", mode="before")
    @classmethod
    def coerce_meta_data(cls, v: dict | None) -> dict:
        return v if v is not None else {}


class ScrapClientLogListResponse(BaseModel):
    """Schema for list of scrap client logs."""

    items: list[ScrapClientLogResponse]


class ScrapClientStatusResponse(BaseModel):
    """Schema for scrap client job status summary."""

    pending: int
    processing: int
    completed: int
    failed: int
