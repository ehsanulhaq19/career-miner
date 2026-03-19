from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    parsed_data: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    job_site_name: str | None = None
    career_client_name: str | None = None
    job_seen: bool = False


class CareerJobListResponse(BaseModel):
    """Schema for paginated list of career jobs."""

    items: list[CareerJobResponse]
    total: int
    page: int
    limit: int


class CareerJobDetailResponse(CareerJobResponse):
    """Schema for detailed career job response (extends CareerJobResponse)."""

    career_client_emails: list[str] = Field(default_factory=list)
    career_client_official_website: str | None = None


class MarkJobSeenRequest(BaseModel):
    """Schema for marking a job as seen."""

    career_job_id: int


class CareerJobDateGroupResponse(BaseModel):
    """Schema for a date group in the jobs tabular UI."""

    date: str
    job_count: int


class CareerJobWithApplicationCountsResponse(BaseModel):
    """Schema for career job with application counts in tabular UI."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    url: str | None
    job_site_id: int
    scrap_job_id: int
    career_client_id: int | None
    meta_data: dict = Field(default_factory=dict)
    parsed_data: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    job_site_name: str | None = None
    career_client_name: str | None = None
    career_client_emails: list[str] = Field(default_factory=list)
    career_client_official_website: str | None = None
    active_application_count: int = 0
    inactive_application_count: int = 0


class CareerJobDateGroupListResponse(BaseModel):
    """Schema for paginated list of date groups."""

    items: list[CareerJobDateGroupResponse]
    total: int
    page: int
    limit: int


class CareerJobWithCountsListResponse(BaseModel):
    """Schema for paginated list of career jobs with application counts."""

    items: list[CareerJobWithApplicationCountsResponse]
    total: int
    page: int
    limit: int


class DashboardStatsResponse(BaseModel):
    """Schema for dashboard statistics overview."""

    total_jobs_executed: int
    total_job_records: int
    total_job_sites: int
    total_clients: int
    job_site_cards: list[JobSiteCardResponse]
