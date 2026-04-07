from datetime import date

from pydantic import BaseModel, Field


class AnalyticsDailyRow(BaseModel):
    """Per-day buckets for dashboard charts."""

    day: date
    scrap_web_jobs_run: int = 0
    scrap_web_scraped_records: int = 0
    scrap_client_jobs_run: int = 0
    scrap_client_scraped_records: int = 0
    jobs_created: int = 0
    clients_created: int = 0
    job_applications_created: int = 0
    job_application_emails_success: int = 0
    job_application_emails_error: int = 0
    workflows_completed: int = 0


class AnalyticsSummaryResponse(BaseModel):
    """Aggregated analytics totals and optional daily series for a date range."""

    date_from: date
    date_to: date
    scrap_web_jobs_run: int = 0
    scrap_web_scraped_records: int = 0
    scrap_client_jobs_run: int = 0
    scrap_client_scraped_records: int = 0
    jobs_created: int = 0
    clients_created: int = 0
    job_applications_created: int = 0
    job_application_emails_success: int = 0
    job_application_emails_error: int = 0
    workflows_completed: int = 0
    daily: list[AnalyticsDailyRow] = Field(default_factory=list)
