from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.job_application.models import (
    BulkJobApplication,
    BulkJobApplicationLog,
    BulkJobApplicationStatus,
    JobApplication,
)


async def create_job_application(db: AsyncSession, data: dict) -> JobApplication:
    """Create a new job application record from the provided data dictionary."""
    job_application = JobApplication(**data)
    db.add(job_application)
    await db.flush()
    await db.refresh(job_application)
    return job_application


async def get_job_applications(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    is_active: bool | None = None,
) -> tuple[list[JobApplication], int]:
    """
    Retrieve a paginated list of job applications for the user.
    Results are ordered by created_at descending.
    """
    base_query = (
        select(JobApplication)
        .where(JobApplication.user_id == user_id)
        .order_by(JobApplication.created_at.desc())
    )
    if is_active is not None:
        base_query = base_query.where(JobApplication.is_active.is_(is_active))

    query = base_query.offset(skip).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())

    count_query = select(func.count(JobApplication.id)).where(
        JobApplication.user_id == user_id
    )
    if is_active is not None:
        count_query = count_query.where(JobApplication.is_active.is_(is_active))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_job_application_by_id(
    db: AsyncSession, job_application_id: int, user_id: int
) -> JobApplication | None:
    """Retrieve a single job application by id for the given user."""
    result = await db.execute(
        select(JobApplication)
        .where(JobApplication.id == job_application_id)
        .where(JobApplication.user_id == user_id)
    )
    return result.scalars().first()


async def get_bulk_job_application_by_id(
    db: AsyncSession, bulk_job_application_id: int
) -> BulkJobApplication | None:
    """Retrieve a single bulk job application by its primary key."""
    result = await db.execute(
        select(BulkJobApplication).where(BulkJobApplication.id == bulk_job_application_id)
    )
    return result.scalars().first()


async def create_bulk_job_application(
    db: AsyncSession, data: dict
) -> BulkJobApplication:
    """Create a new bulk job application record from the provided data dictionary."""
    bulk_job_application = BulkJobApplication(**data)
    db.add(bulk_job_application)
    await db.flush()
    await db.refresh(bulk_job_application)
    return bulk_job_application


async def create_bulk_job_application_log(
    db: AsyncSession,
    bulk_job_application_id: int,
    action: str,
    progress: int = 0,
    status: str = "pending",
    details: str | None = None,
    meta_data: dict | None = None,
) -> BulkJobApplicationLog:
    """Create a new bulk job application log entry."""
    log = BulkJobApplicationLog(
        bulk_job_application_id=bulk_job_application_id,
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


async def get_bulk_job_application_logs_by_id(
    db: AsyncSession,
    bulk_job_application_id: int,
) -> list[BulkJobApplicationLog]:
    """Retrieve all log entries for a bulk job application ordered by creation time."""
    result = await db.execute(
        select(BulkJobApplicationLog)
        .where(BulkJobApplicationLog.bulk_job_application_id == bulk_job_application_id)
        .order_by(BulkJobApplicationLog.created_at.asc())
    )
    return list(result.scalars().all())


async def update_bulk_job_application_status(
    db: AsyncSession,
    bulk_job_application_id: int,
    status: str | BulkJobApplicationStatus,
) -> BulkJobApplication | None:
    """Update the status of an existing bulk job application."""
    bulk_job_application = await get_bulk_job_application_by_id(
        db, bulk_job_application_id
    )
    if bulk_job_application is None:
        return None
    status_value = (
        status.value if isinstance(status, BulkJobApplicationStatus) else status
    )
    bulk_job_application.status = status_value
    await db.flush()
    await db.refresh(bulk_job_application)
    return bulk_job_application


async def update_job_application(
    db: AsyncSession,
    job_application_id: int,
    user_id: int,
    data: dict,
) -> JobApplication | None:
    """Update an existing job application with the provided data."""
    job_application = await get_job_application_by_id(
        db, job_application_id, user_id
    )
    if job_application is None:
        return None
    for key, value in data.items():
        if hasattr(job_application, key):
            setattr(job_application, key, value)
    await db.flush()
    await db.refresh(job_application)
    return job_application
