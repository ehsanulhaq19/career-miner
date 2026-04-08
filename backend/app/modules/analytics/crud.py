from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.models import CareerClient
from app.modules.career_job.models import CareerJob
from app.modules.email.models import EmailLog
from app.modules.job_application.models import JobApplication, JobApplicationEmailLog
from app.modules.scrap_client.models import ScrapClientJob
from app.modules.scrap_job.models import ScrapJob
from app.modules.workflow.models import WorkflowExecution, WorkflowExecutionStatus


SCRAP_JOB_FINISHED_STATUSES: tuple[str, ...] = (
    "completed",
    "error",
    "stopped",
    "terminated",
)


async def fetch_scrap_web_rows_for_range(
    db: AsyncSession, date_from: date, date_to: date, user_id: int
) -> list[tuple[object, dict | None]]:
    """
    Return (updated_at, meta_data) pairs for scrap jobs that finished in the date range.
    """
    result = await db.execute(
        select(ScrapJob.updated_at, ScrapJob.meta_data).where(
            ScrapJob.created_by == user_id,
            ScrapJob.status.in_(SCRAP_JOB_FINISHED_STATUSES),
            cast(ScrapJob.updated_at, Date) >= date_from,
            cast(ScrapJob.updated_at, Date) <= date_to,
        )
    )
    return [(row[0], row[1]) for row in result.all()]


async def fetch_scrap_client_rows_for_range(
    db: AsyncSession, date_from: date, date_to: date, user_id: int
) -> list[tuple[object, dict | None]]:
    """
    Return (updated_at, meta_data) pairs for scrap client jobs that finished in the range.
    """
    result = await db.execute(
        select(ScrapClientJob.updated_at, ScrapClientJob.meta_data).where(
            ScrapClientJob.created_by == user_id,
            ScrapClientJob.status.in_(SCRAP_JOB_FINISHED_STATUSES),
            cast(ScrapClientJob.updated_at, Date) >= date_from,
            cast(ScrapClientJob.updated_at, Date) <= date_to,
        )
    )
    return [(row[0], row[1]) for row in result.all()]


async def count_career_jobs_created_in_range(
    db: AsyncSession, date_from: date, date_to: date, user_id: int
) -> int:
    """Count career jobs whose created_at date falls in the inclusive range."""
    result = await db.execute(
        select(func.count(CareerJob.id)).where(
            CareerJob.created_by == user_id,
            cast(CareerJob.created_at, Date) >= date_from,
            cast(CareerJob.created_at, Date) <= date_to,
        )
    )
    return int(result.scalar() or 0)


async def career_jobs_created_by_day(
    db: AsyncSession, date_from: date, date_to: date, user_id: int
) -> dict[date, int]:
    """Return map of calendar day to number of career jobs created."""
    result = await db.execute(
        select(cast(CareerJob.created_at, Date), func.count(CareerJob.id)).where(
            CareerJob.created_by == user_id,
            cast(CareerJob.created_at, Date) >= date_from,
            cast(CareerJob.created_at, Date) <= date_to,
        ).group_by(cast(CareerJob.created_at, Date))
    )
    return {row[0]: int(row[1]) for row in result.all() if row[0] is not None}


async def count_career_clients_created_in_range(
    db: AsyncSession, date_from: date, date_to: date, user_id: int
) -> int:
    """Count active career clients created in the date range."""
    result = await db.execute(
        select(func.count(CareerClient.id)).where(
            CareerClient.created_by == user_id,
            CareerClient.is_active.is_(True),
            cast(CareerClient.created_at, Date) >= date_from,
            cast(CareerClient.created_at, Date) <= date_to,
        )
    )
    return int(result.scalar() or 0)


async def career_clients_created_by_day(
    db: AsyncSession, date_from: date, date_to: date, user_id: int
) -> dict[date, int]:
    """Return map of day to active career clients created."""
    result = await db.execute(
        select(cast(CareerClient.created_at, Date), func.count(CareerClient.id)).where(
            CareerClient.created_by == user_id,
            CareerClient.is_active.is_(True),
            cast(CareerClient.created_at, Date) >= date_from,
            cast(CareerClient.created_at, Date) <= date_to,
        ).group_by(cast(CareerClient.created_at, Date))
    )
    return {row[0]: int(row[1]) for row in result.all() if row[0] is not None}


async def count_job_applications_created_in_range(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> int:
    """Count job applications for the user created in the range."""
    result = await db.execute(
        select(func.count(JobApplication.id)).where(
            JobApplication.user_id == user_id,
            JobApplication.created_by == user_id,
            cast(JobApplication.created_at, Date) >= date_from,
            cast(JobApplication.created_at, Date) <= date_to,
        )
    )
    return int(result.scalar() or 0)


async def job_applications_created_by_day(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> dict[date, int]:
    """Return map of day to job applications created for the user."""
    result = await db.execute(
        select(
            cast(JobApplication.created_at, Date),
            func.count(JobApplication.id),
        ).where(
            JobApplication.user_id == user_id,
            JobApplication.created_by == user_id,
            cast(JobApplication.created_at, Date) >= date_from,
            cast(JobApplication.created_at, Date) <= date_to,
        ).group_by(cast(JobApplication.created_at, Date))
    )
    return {row[0]: int(row[1]) for row in result.all() if row[0] is not None}


async def count_job_application_emails_by_status_in_range(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> dict[str, int]:
    """Count email logs linked to the user's job applications, grouped by log status."""
    result = await db.execute(
        select(EmailLog.status, func.count(EmailLog.id))
        .select_from(EmailLog)
        .join(
            JobApplicationEmailLog,
            JobApplicationEmailLog.email_log_id == EmailLog.id,
        )
        .join(
            JobApplication,
            JobApplication.id == JobApplicationEmailLog.job_application_id,
        )
        .where(
            JobApplication.user_id == user_id,
            JobApplication.created_by == user_id,
            cast(EmailLog.created_at, Date) >= date_from,
            cast(EmailLog.created_at, Date) <= date_to,
        )
        .group_by(EmailLog.status)
    )
    return {str(row[0]): int(row[1]) for row in result.all() if row[0] is not None}


async def job_application_emails_by_day_and_status(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> dict[date, dict[str, int]]:
    """
    Nested map day -> {status: count} for job-application-related email logs.
    """
    result = await db.execute(
        select(
            cast(EmailLog.created_at, Date),
            EmailLog.status,
            func.count(EmailLog.id),
        )
        .select_from(EmailLog)
        .join(
            JobApplicationEmailLog,
            JobApplicationEmailLog.email_log_id == EmailLog.id,
        )
        .join(
            JobApplication,
            JobApplication.id == JobApplicationEmailLog.job_application_id,
        )
        .where(
            JobApplication.user_id == user_id,
            JobApplication.created_by == user_id,
            cast(EmailLog.created_at, Date) >= date_from,
            cast(EmailLog.created_at, Date) <= date_to,
        )
        .group_by(cast(EmailLog.created_at, Date), EmailLog.status)
    )
    out: dict[date, dict[str, int]] = defaultdict(dict)
    for row in result.all():
        d, status, cnt = row[0], row[1], row[2]
        if d is not None and status is not None:
            out[d][str(status)] = int(cnt)
    return dict(out)


async def count_completed_workflow_executions_in_range(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> int:
    """Count workflow executions completed by the user whose completion day is in range."""
    result = await db.execute(
        select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.user_id == user_id,
            WorkflowExecution.status == WorkflowExecutionStatus.COMPLETED.value,
            WorkflowExecution.completed_at.isnot(None),
            cast(WorkflowExecution.completed_at, Date) >= date_from,
            cast(WorkflowExecution.completed_at, Date) <= date_to,
        )
    )
    return int(result.scalar() or 0)


async def completed_workflow_executions_by_day(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> dict[date, int]:
    """Map completion day to count of completed workflow runs for the user."""
    result = await db.execute(
        select(
            cast(WorkflowExecution.completed_at, Date),
            func.count(WorkflowExecution.id),
        ).where(
            WorkflowExecution.user_id == user_id,
            WorkflowExecution.status == WorkflowExecutionStatus.COMPLETED.value,
            WorkflowExecution.completed_at.isnot(None),
            cast(WorkflowExecution.completed_at, Date) >= date_from,
            cast(WorkflowExecution.completed_at, Date) <= date_to,
        ).group_by(cast(WorkflowExecution.completed_at, Date))
    )
    return {row[0]: int(row[1]) for row in result.all() if row[0] is not None}


def iter_dates_inclusive(date_from: date, date_to: date) -> Iterable[date]:
    """Yield each calendar day from date_from through date_to inclusive."""
    current = date_from
    while current <= date_to:
        yield current
        current += timedelta(days=1)


def _as_calendar_day(value: object) -> date | None:
    """Normalize SQLAlchemy/datetime values to a calendar date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def aggregate_scrap_web_from_rows(
    rows: list[tuple[object, dict | None]],
) -> tuple[int, int, dict[date, tuple[int, int]]]:
    """
    From scrap job rows, return total runs, total scraped records (from meta),
    and per-day (runs, scraped sum).
    """
    total_runs = 0
    total_scraped = 0
    by_day: dict[date, list[int]] = defaultdict(lambda: [0, 0])
    for updated_at, meta in rows:
        day = _as_calendar_day(updated_at)
        if day is None:
            continue
        scraped = _scraped_count_from_scrap_job_meta(meta)
        total_runs += 1
        total_scraped += scraped
        by_day[day][0] += 1
        by_day[day][1] += scraped
    flat = {d: (pair[0], pair[1]) for d, pair in by_day.items()}
    return total_runs, total_scraped, flat


def aggregate_scrap_client_from_rows(
    rows: list[tuple[object, dict | None]],
) -> tuple[int, int, dict[date, tuple[int, int]]]:
    """Same as aggregate_scrap_web_from_rows for scrap client jobs."""
    total_runs = 0
    total_scraped = 0
    by_day: dict[date, list[int]] = defaultdict(lambda: [0, 0])
    for updated_at, meta in rows:
        day = _as_calendar_day(updated_at)
        if day is None:
            continue
        scraped = _scraped_count_from_scrap_client_meta(meta)
        total_runs += 1
        total_scraped += scraped
        by_day[day][0] += 1
        by_day[day][1] += scraped
    flat = {d: (pair[0], pair[1]) for d, pair in by_day.items()}
    return total_runs, total_scraped, flat


def _scraped_count_from_scrap_job_meta(meta: dict | None) -> int:
    """Best-effort numeric scraped total from scrap job completion meta_data."""
    if not meta:
        return 0
    for key in (
        "total_jobs_created",
        "total_jobs_scraped_from_html",
        "total_jobs_validated",
    ):
        raw = meta.get(key)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
    return 0


def _scraped_count_from_scrap_client_meta(meta: dict | None) -> int:
    """Best-effort scraped / saved count from scrap client job meta_data."""
    if not meta:
        return 0
    for key in ("clients_saved", "total_clients", "total", "completed"):
        raw = meta.get(key)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
    return 0


def split_email_status_totals(status_map: dict[str, int]) -> tuple[int, int]:
    """Split grouped email log counts into success and error totals."""
    success = int(status_map.get("success", 0))
    error = int(status_map.get("error", 0))
    return success, error

