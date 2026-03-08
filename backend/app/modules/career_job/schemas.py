from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobSiteCardResponse(BaseModel):
    """Schema for a job site summary card on the dashboard."""

    id: int
    name: str
    url: str
    total_jobs: int
    last_scrapped: datetime | None
    is_active: bool


class CareerJobResponse(BaseModel):
    """Schema for career job response data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    url: str | None
    job_site_id: int
    scrap_job_id: int
    meta_data: dict
    contact_details: str | None
    created_at: datetime
    updated_at: datetime
    job_site_name: str | None = None


class CareerJobListResponse(BaseModel):
    """Schema for paginated list of career jobs."""

    items: list[CareerJobResponse]
    total: int
    page: int
    limit: int


class CareerJobDetailResponse(CareerJobResponse):
    """Schema for detailed career job response (extends CareerJobResponse)."""

    pass


class DashboardStatsResponse(BaseModel):
    """Schema for dashboard statistics overview."""

    total_jobs_executed: int
    total_job_records: int
    total_job_sites: int
    job_site_cards: list[JobSiteCardResponse]
