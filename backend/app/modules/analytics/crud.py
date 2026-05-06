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


def _normalize_hour_bucket(value: datetime | None) -> datetime | None:
    """Normalize a timestamp to a naive UTC hour start for consistent dict keys."""
    if value is None:
        return None
    dt = value.replace(tzinfo=None) if value.tzinfo else value
    return dt.replace(minute=0, second=0, microsecond=0)


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


async def career_jobs_created_by_hour(
    db: AsyncSession, date_from: date, date_to: date, user_id: int
) -> dict[datetime, int]:
    """Return map of hour start (UTC) to number of career jobs created."""
    hour_bucket = func.date_trunc("hour", CareerJob.created_at).label("hour_bucket")
    result = await db.execute(
        select(hour_bucket, func.count(CareerJob.id)).where(
            CareerJob.created_by == user_id,
            cast(CareerJob.created_at, Date) >= date_from,
            cast(CareerJob.created_at, Date) <= date_to,
        ).group_by(hour_bucket)
    )
    out: dict[datetime, int] = {}
    for row in result.all():
        h = _normalize_hour_bucket(row[0])
        if h is not None:
            out[h] = int(row[1])
    return out


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


async def career_clients_created_by_hour(
    db: AsyncSession, date_from: date, date_to: date, user_id: int
) -> dict[datetime, int]:
    """Return map of hour start to active career clients created."""
    hour_bucket = func.date_trunc("hour", CareerClient.created_at).label("hour_bucket")
    result = await db.execute(
        select(hour_bucket, func.count(CareerClient.id)).where(
            CareerClient.created_by == user_id,
            CareerClient.is_active.is_(True),
            cast(CareerClient.created_at, Date) >= date_from,
            cast(CareerClient.created_at, Date) <= date_to,
        ).group_by(hour_bucket)
    )
    out: dict[datetime, int] = {}
    for row in result.all():
        h = _normalize_hour_bucket(row[0])
        if h is not None:
            out[h] = int(row[1])
    return out


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


async def job_applications_created_by_hour(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> dict[datetime, int]:
    """Return map of hour start to job applications created for the user."""
    hour_bucket = func.date_trunc("hour", JobApplication.created_at).label("hour_bucket")
    result = await db.execute(
        select(hour_bucket, func.count(JobApplication.id)).where(
            JobApplication.user_id == user_id,
            JobApplication.created_by == user_id,
            cast(JobApplication.created_at, Date) >= date_from,
            cast(JobApplication.created_at, Date) <= date_to,
        ).group_by(hour_bucket)
    )
    out: dict[datetime, int] = {}
    for row in result.all():
        h = _normalize_hour_bucket(row[0])
        if h is not None:
            out[h] = int(row[1])
    return out


def _job_application_email_log_ids_subquery(user_id: int):
    """
    Subquery of email_logs.id values tied to the user's job applications.
    """
    return (
        select(JobApplicationEmailLog.email_log_id)
        .join(
            JobApplication,
            JobApplication.id == JobApplicationEmailLog.job_application_id,
        )
        .where(
            JobApplication.user_id == user_id,
            JobApplication.created_by == user_id,
        )
    )


async def count_email_logs_by_status_for_user_job_applications(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> dict[str, int]:
    """Count rows in email_logs for the user's job-application sends, by status."""
    ja_emails = _job_application_email_log_ids_subquery(user_id)
    result = await db.execute(
        select(EmailLog.status, func.count(EmailLog.id)).where(
            EmailLog.id.in_(ja_emails),
            cast(EmailLog.created_at, Date) >= date_from,
            cast(EmailLog.created_at, Date) <= date_to,
        ).group_by(EmailLog.status)
    )
    return {str(row[0]): int(row[1]) for row in result.all() if row[0] is not None}


async def email_logs_by_hour_and_status_for_user_job_applications(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> dict[datetime, dict[str, int]]:
    """
    Nested map hour_start -> {status: count} for email_logs tied to job applications.
    """
    ja_emails = _job_application_email_log_ids_subquery(user_id)
    hour_bucket = func.date_trunc("hour", EmailLog.created_at).label("hour_bucket")
    result = await db.execute(
        select(hour_bucket, EmailLog.status, func.count(EmailLog.id)).where(
            EmailLog.id.in_(ja_emails),
            cast(EmailLog.created_at, Date) >= date_from,
            cast(EmailLog.created_at, Date) <= date_to,
        ).group_by(hour_bucket, EmailLog.status)
    )
    out: dict[datetime, dict[str, int]] = defaultdict(dict)
    for row in result.all():
        h = _normalize_hour_bucket(row[0])
        status, cnt = row[1], row[2]
        if h is not None and status is not None:
            out[h][str(status)] = int(cnt)
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


async def completed_workflow_executions_by_hour(
    db: AsyncSession, user_id: int, date_from: date, date_to: date
) -> dict[datetime, int]:
    """Map completion hour to count of completed workflow runs for the user."""
    hour_bucket = func.date_trunc(
        "hour", WorkflowExecution.completed_at
    ).label("hour_bucket")
    result = await db.execute(
        select(hour_bucket, func.count(WorkflowExecution.id)).where(
            WorkflowExecution.user_id == user_id,
            WorkflowExecution.status == WorkflowExecutionStatus.COMPLETED.value,
            WorkflowExecution.completed_at.isnot(None),
            cast(WorkflowExecution.completed_at, Date) >= date_from,
            cast(WorkflowExecution.completed_at, Date) <= date_to,
        ).group_by(hour_bucket)
    )
    out: dict[datetime, int] = {}
    for row in result.all():
        h = _normalize_hour_bucket(row[0])
        if h is not None:
            out[h] = int(row[1])
    return out


def iter_hours_inclusive(date_from: date, date_to: date) -> Iterable[datetime]:
    """Yield each hour from date_from 00:00 through date_to 23:00 inclusive (naive UTC)."""
    start = datetime.combine(date_from, datetime.min.time())
    end_exclusive = datetime.combine(date_to, datetime.min.time()) + timedelta(days=1)
    cur = start
    while cur < end_exclusive:
        yield cur
        cur += timedelta(hours=1)


def _as_hour_start(value: object) -> datetime | None:
    """Normalize values to the start of the hour bucket (naive UTC)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return _normalize_hour_bucket(value)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return None


def aggregate_scrap_web_from_rows(
    rows: list[tuple[object, dict | None]],
) -> tuple[int, int, dict[datetime, tuple[int, int]]]:
    """
    From scrap job rows, return total runs, total scraped records (from meta),
    and per-hour (runs, scraped sum).
    """
    total_runs = 0
    total_scraped = 0
    by_hour: dict[datetime, list[int]] = defaultdict(lambda: [0, 0])
    for updated_at, meta in rows:
        hour_start = _as_hour_start(updated_at)
        if hour_start is None:
            continue
        scraped = _scraped_count_from_scrap_job_meta(meta)
        total_runs += 1
        total_scraped += scraped
        by_hour[hour_start][0] += 1
        by_hour[hour_start][1] += scraped
    flat = {h: (pair[0], pair[1]) for h, pair in by_hour.items()}
    return total_runs, total_scraped, flat


def aggregate_scrap_client_from_rows(
    rows: list[tuple[object, dict | None]],
) -> tuple[int, int, dict[datetime, tuple[int, int]]]:
    """Same as aggregate_scrap_web_from_rows for scrap client jobs."""
    total_runs = 0
    total_scraped = 0
    by_hour: dict[datetime, list[int]] = defaultdict(lambda: [0, 0])
    for updated_at, meta in rows:
        hour_start = _as_hour_start(updated_at)
        if hour_start is None:
            continue
        scraped = _scraped_count_from_scrap_client_meta(meta)
        total_runs += 1
        total_scraped += scraped
        by_hour[hour_start][0] += 1
        by_hour[hour_start][1] += scraped
    flat = {h: (pair[0], pair[1]) for h, pair in by_hour.items()}
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

