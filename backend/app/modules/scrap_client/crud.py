from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scrap_client.models import (
    ScrapClientJob,
    ScrapClientLog,
    ScrapClientJobStatus,
)


async def get_scrap_client_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
) -> tuple[list[ScrapClientJob], int]:
    """Retrieve a paginated list of scrap client jobs with optional filters."""
    query = select(ScrapClientJob)
    count_query = select(func.count(ScrapClientJob.id))

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


async def get_active_scrap_client_jobs(db: AsyncSession) -> list[ScrapClientJob]:
    """Return scrap client jobs with status pending or in_progress."""
    result = await db.execute(
        select(ScrapClientJob).where(
            ScrapClientJob.status.in_(
                [
                    ScrapClientJobStatus.PENDING.value,
                    ScrapClientJobStatus.IN_PROGRESS.value,
                ]
            )
        )
    )
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
