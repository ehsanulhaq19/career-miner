from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scrap_client.models import (
    ScrapClientFile,
    ScrapClientJob,
    ScrapClientJobStatus,
    ScrapClientLog,
)
from app.modules.scraper.models import Scrapper


async def get_scrap_client_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    created_by: int | None = None,
) -> tuple[list[ScrapClientJob], int]:
    """Retrieve a paginated list of scrap client jobs with optional filters."""
    query = select(ScrapClientJob)
    count_query = select(func.count(ScrapClientJob.id))

    if created_by is not None:
        query = query.where(ScrapClientJob.created_by == created_by)
        count_query = count_query.where(ScrapClientJob.created_by == created_by)

    if status is not None:
        query = query.where(ScrapClientJob.status == status)
        count_query = count_query.where(ScrapClientJob.status == status)

    query = query.order_by(ScrapClientJob.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    items = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_scrap_client_job_by_id(
    db: AsyncSession, scrap_client_job_id: int
) -> ScrapClientJob | None:
    """Retrieve a single scrap client job by its primary key."""
    result = await db.execute(
        select(ScrapClientJob).where(ScrapClientJob.id == scrap_client_job_id)
    )
    return result.scalars().first()


async def create_scrap_client_job(db: AsyncSession, data: dict) -> ScrapClientJob:
    """Create a new scrap client job record from the provided data dictionary."""
    scrap_job = ScrapClientJob(**data)
    db.add(scrap_job)
    await db.flush()
    await db.refresh(scrap_job)
    return scrap_job


async def update_scrap_client_job_status(
    db: AsyncSession,
    scrap_client_job_id: int,
    status: str | ScrapClientJobStatus,
) -> ScrapClientJob | None:
    """Update the status of an existing scrap client job."""
    scrap_job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
    if scrap_job is None:
        return None

    status_value = (
        status.value if isinstance(status, ScrapClientJobStatus) else status
    )
    scrap_job.status = status_value
    await db.flush()
    await db.refresh(scrap_job)
    return scrap_job


async def update_scrap_client_job_meta_data(
    db: AsyncSession,
    scrap_client_job_id: int,
    meta_data: dict,
) -> ScrapClientJob | None:
    """Update or merge meta_data for an existing scrap client job."""
    scrap_job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
    if scrap_job is None:
        return None

    existing = scrap_job.meta_data or {}
    merged = {**existing, **meta_data}
    scrap_job.meta_data = merged
    await db.flush()
    await db.refresh(scrap_job)
    return scrap_job


async def get_active_scrap_client_jobs(
    db: AsyncSession, created_by: int | None = None
) -> list[ScrapClientJob]:
    """Return scrap client jobs with status pending or in_progress."""
    q = select(ScrapClientJob).where(
        ScrapClientJob.status.in_(
            [
                ScrapClientJobStatus.PENDING.value,
                ScrapClientJobStatus.IN_PROGRESS.value,
            ]
        )
    )
    if created_by is not None:
        q = q.where(ScrapClientJob.created_by == created_by)
    result = await db.execute(q)
    return list(result.scalars().all())


async def create_scrap_client_job_log(
    db: AsyncSession,
    scrap_client_job_id: int,
    action: str,
    progress: int = 0,
    status: str = "pending",
    details: str | None = None,
    meta_data: dict | None = None,
) -> ScrapClientLog:
    """Create a new scrap client job log entry."""
    log = ScrapClientLog(
        scrap_client_job_id=scrap_client_job_id,
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


async def get_scrap_client_job_logs_by_job_id(
    db: AsyncSession,
    scrap_client_job_id: int,
) -> list[ScrapClientLog]:
    """Retrieve all log entries for a scrap client job ordered by creation time."""
    result = await db.execute(
        select(ScrapClientLog)
        .where(ScrapClientLog.scrap_client_job_id == scrap_client_job_id)
        .order_by(ScrapClientLog.created_at.asc())
    )
    return list(result.scalars().all())


async def create_scrap_client_file_link(
    db: AsyncSession, scrap_client_job_id: int, scrapper_id: int
) -> ScrapClientFile:
    """Link a scrap client job to a scrapper record."""
    row = ScrapClientFile(
        scrap_client_job_id=scrap_client_job_id, scrapper_id=scrapper_id
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def list_scrappers_for_scrap_client_job(
    db: AsyncSession, scrap_client_job_id: int
) -> list[Scrapper]:
    """Return scrappers linked to a scrap client job."""
    q = (
        select(Scrapper)
        .join(
            ScrapClientFile,
            ScrapClientFile.scrapper_id == Scrapper.id,
        )
        .where(ScrapClientFile.scrap_client_job_id == scrap_client_job_id)
        .order_by(Scrapper.id.asc())
    )
    result = await db.execute(q)
    return list(result.scalars().unique().all())


async def scrap_client_job_owns_scrapper(
    db: AsyncSession, scrap_client_job_id: int, scrapper_id: int
) -> bool:
    """Return True if the scrapper is linked to the scrap client job."""
    result = await db.execute(
        select(ScrapClientFile.id).where(
            ScrapClientFile.scrap_client_job_id == scrap_client_job_id,
            ScrapClientFile.scrapper_id == scrapper_id,
        )
    )
    return result.scalar_one_or_none() is not None
