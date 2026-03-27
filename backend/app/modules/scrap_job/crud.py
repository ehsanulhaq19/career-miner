from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scrap_job.models import ScrapJob, ScrapJobFile, ScrapJobLog, ScrapJobStatus
from app.modules.scraper.models import Scrapper


async def get_scrap_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    job_site_id: int | None = None,
    status: str | None = None,
) -> tuple[list[ScrapJob], int]:
    """Retrieve a paginated list of scrap jobs with optional filters."""
    query = select(ScrapJob)
    count_query = select(func.count(ScrapJob.id))

    if job_site_id is not None:
        query = query.where(ScrapJob.job_site_id == job_site_id)
        count_query = count_query.where(ScrapJob.job_site_id == job_site_id)

    if status is not None:
        query = query.where(ScrapJob.status == status)
        count_query = count_query.where(ScrapJob.status == status)

    query = query.order_by(ScrapJob.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    items = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_scrap_job_by_id(db: AsyncSession, scrap_job_id: int) -> ScrapJob | None:
    """Retrieve a single scrap job by its primary key."""
    result = await db.execute(select(ScrapJob).where(ScrapJob.id == scrap_job_id))
    return result.scalars().first()


async def create_scrap_job(db: AsyncSession, data: dict) -> ScrapJob:
    """Create a new scrap job record from the provided data dictionary."""
    scrap_job = ScrapJob(**data)
    db.add(scrap_job)
    await db.flush()
    await db.refresh(scrap_job)
    return scrap_job


async def update_scrap_job_status(
    db: AsyncSession,
    scrap_job_id: int,
    status: str | ScrapJobStatus,
) -> ScrapJob | None:
    """Update the status of an existing scrap job."""
    scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
    if scrap_job is None:
        return None

    status_value = status.value if isinstance(status, ScrapJobStatus) else status
    scrap_job.status = status_value
    await db.flush()
    await db.refresh(scrap_job)
    return scrap_job


async def update_scrap_job_meta_data(
    db: AsyncSession,
    scrap_job_id: int,
    meta_data: dict,
) -> ScrapJob | None:
    """Update or merge meta_data for an existing scrap job."""
    scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
    if scrap_job is None:
        return None

    existing = scrap_job.meta_data or {}
    merged = {**existing, **meta_data}
    scrap_job.meta_data = merged
    await db.flush()
    await db.refresh(scrap_job)
    return scrap_job


async def get_active_scrap_jobs_for_site(
    db: AsyncSession,
    job_site_id: int,
) -> list[ScrapJob]:
    """Return scrap jobs with status pending or in_progress for a given site."""
    result = await db.execute(
        select(ScrapJob).where(
            ScrapJob.job_site_id == job_site_id,
            ScrapJob.status.in_(
                [ScrapJobStatus.PENDING.value, ScrapJobStatus.IN_PROGRESS.value]
            ),
        )
    )
    return list(result.scalars().all())


async def create_scrap_job_log(
    db: AsyncSession,
    scrap_job_id: int,
    action: str,
    progress: int = 0,
    status: str = "pending",
    details: str | None = None,
    meta_data: dict | None = None,
) -> ScrapJobLog:
    """Create a new scrap job log entry."""
    log = ScrapJobLog(
        scrap_job_id=scrap_job_id,
        action=action,
        progress=progress,
        status=status,
        details=details,
        meta_data=meta_data or {},
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_scrap_job_logs_by_scrap_job_id(
    db: AsyncSession,
    scrap_job_id: int,
) -> list[ScrapJobLog]:
    """Retrieve all log entries for a scrap job ordered by creation time."""
    result = await db.execute(
        select(ScrapJobLog)
        .where(ScrapJobLog.scrap_job_id == scrap_job_id)
        .order_by(ScrapJobLog.created_at.asc())
    )
    return list(result.scalars().all())


async def get_timed_out_scrap_jobs(db: AsyncSession, max_minutes: int) -> list[ScrapJob]:
    """Return scrap jobs that are pending or in_progress and exceeded the time limit."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=max_minutes)).replace(tzinfo=None)
    result = await db.execute(
        select(ScrapJob).where(
            ScrapJob.status.in_(
                [ScrapJobStatus.PENDING.value, ScrapJobStatus.IN_PROGRESS.value]
            ),
            ScrapJob.created_at <= cutoff,
        )
    )
    return list(result.scalars().all())


async def create_scrap_job_file_link(
    db: AsyncSession, scrap_job_id: int, scrapper_id: int
) -> ScrapJobFile:
    """Link a scrap job to a scrapper record."""
    row = ScrapJobFile(scrap_job_id=scrap_job_id, scrapper_id=scrapper_id)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def list_scrappers_for_scrap_job(
    db: AsyncSession, scrap_job_id: int
) -> list[Scrapper]:
    """Return scrappers linked to a scrap job."""
    q = (
        select(Scrapper)
        .join(ScrapJobFile, ScrapJobFile.scrapper_id == Scrapper.id)
        .where(ScrapJobFile.scrap_job_id == scrap_job_id)
        .order_by(Scrapper.id.asc())
    )
    result = await db.execute(q)
    return list(result.scalars().unique().all())


async def scrap_job_owns_scrapper(
    db: AsyncSession, scrap_job_id: int, scrapper_id: int
) -> bool:
    """Return True if the scrapper is linked to the scrap job."""
    result = await db.execute(
        select(ScrapJobFile.id).where(
            ScrapJobFile.scrap_job_id == scrap_job_id,
            ScrapJobFile.scrapper_id == scrapper_id,
        )
    )
    return result.scalar_one_or_none() is not None
