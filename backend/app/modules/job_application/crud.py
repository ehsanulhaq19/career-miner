from datetime import date

from sqlalchemy import Date, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.job_application.models import (
    BulkJobApplication,
    BulkJobApplicationLog,
    BulkJobApplicationEmailSend,
    BulkJobApplicationEmailSendLog,
    BulkJobApplicationEmailSendStatus,
    BulkJobApplicationStatus,
    JobApplication,
    JobApplicationBulkJobApplicationLink,
    JobApplicationEmailLog,
)


async def record_job_application_bulk_job_application_link(
    db: AsyncSession,
    job_application_id: int,
    bulk_job_application_id: int,
) -> JobApplicationBulkJobApplicationLink:
    """
    Append a pivot row linking a job application to a bulk job application run.
    """
    row = JobApplicationBulkJobApplicationLink(
        job_application_id=job_application_id,
        bulk_job_application_id=bulk_job_application_id,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


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
        .where(JobApplication.created_by == user_id)
        .order_by(JobApplication.created_at.desc())
    )
    if is_active is not None:
        base_query = base_query.where(JobApplication.is_active.is_(is_active))

    query = base_query.offset(skip).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())

    count_query = select(func.count(JobApplication.id)).where(
        JobApplication.user_id == user_id,
        JobApplication.created_by == user_id,
    )
    if is_active is not None:
        count_query = count_query.where(JobApplication.is_active.is_(is_active))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_job_application_dates_grouped(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[tuple[date, int]], int]:
    """
    Return distinct created_at dates with application count per date for the user.
    Ordered by date descending.
    """
    date_col = cast(JobApplication.created_at, Date)
    grouped = (
        select(date_col, func.count(JobApplication.id).label("application_count"))
        .where(JobApplication.user_id == user_id)
        .where(JobApplication.created_by == user_id)
        .group_by(date_col)
        .order_by(date_col.desc())
    )
    count_subq = (
        select(date_col)
        .where(JobApplication.user_id == user_id)
        .where(JobApplication.created_by == user_id)
        .distinct()
        .subquery()
    )
    count_result = await db.execute(select(func.count()).select_from(count_subq))
    total = count_result.scalar() or 0
    result = await db.execute(grouped.offset(skip).limit(limit))
    rows = result.all()
    return [(r[0], r[1]) for r in rows], total


async def get_job_applications_by_created_date(
    db: AsyncSession,
    user_id: int,
    target_date: date,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[JobApplication], int]:
    """
    Return job applications for the user created on the given calendar date.
    Results ordered by created_at descending.
    """
    date_col = cast(JobApplication.created_at, Date)
    base_query = (
        select(JobApplication)
        .where(JobApplication.user_id == user_id)
        .where(JobApplication.created_by == user_id)
        .where(date_col == target_date)
        .order_by(JobApplication.created_at.desc())
    )
    count_query = (
        select(func.count(JobApplication.id))
        .where(JobApplication.user_id == user_id)
        .where(JobApplication.created_by == user_id)
        .where(date_col == target_date)
    )
    query = base_query.offset(skip).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())
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
        .where(JobApplication.created_by == user_id)
    )
    return result.scalars().first()


async def get_job_application_ids_for_user_by_career_jobs(
    db: AsyncSession,
    user_id: int,
    career_job_ids: list[int],
) -> list[int]:
    """
    Return job application ids for the user tied to the given career jobs.
    """
    if not career_job_ids:
        return []
    result = await db.execute(
        select(JobApplication.id)
        .where(JobApplication.user_id == user_id)
        .where(JobApplication.created_by == user_id)
        .where(JobApplication.career_job_id.in_(career_job_ids))
        .order_by(JobApplication.id.desc())
    )
    return [row[0] for row in result.all()]


async def get_active_job_applications_count_by_similarity(
    db: AsyncSession, user_id: int
) -> dict:
    """
    Return count of active job applications grouped by similarity score ranges.
    Ranges: 100%, 90-99%, 80-89%, 70-79%, 60-69%, 50-59%, below 50%.
    """
    score_100 = select(func.count(JobApplication.id)).where(
        JobApplication.user_id == user_id,
        JobApplication.created_by == user_id,
        JobApplication.is_active.is_(True),
        JobApplication.similarity_score == 100,
    )
    above_90 = select(func.count(JobApplication.id)).where(
        JobApplication.user_id == user_id,
        JobApplication.created_by == user_id,
        JobApplication.is_active.is_(True),
        JobApplication.similarity_score >= 90,
        JobApplication.similarity_score < 100,
    )
    above_80 = select(func.count(JobApplication.id)).where(
        JobApplication.user_id == user_id,
        JobApplication.created_by == user_id,
        JobApplication.is_active.is_(True),
        JobApplication.similarity_score >= 80,
        JobApplication.similarity_score < 90,
    )
    above_70 = select(func.count(JobApplication.id)).where(
        JobApplication.user_id == user_id,
        JobApplication.created_by == user_id,
        JobApplication.is_active.is_(True),
        JobApplication.similarity_score >= 70,
        JobApplication.similarity_score < 80,
    )
    above_60 = select(func.count(JobApplication.id)).where(
        JobApplication.user_id == user_id,
        JobApplication.created_by == user_id,
        JobApplication.is_active.is_(True),
        JobApplication.similarity_score >= 60,
        JobApplication.similarity_score < 70,
    )
    above_50 = select(func.count(JobApplication.id)).where(
        JobApplication.user_id == user_id,
        JobApplication.created_by == user_id,
        JobApplication.is_active.is_(True),
        JobApplication.similarity_score >= 50,
        JobApplication.similarity_score < 60,
    )
    below_50 = select(func.count(JobApplication.id)).where(
        JobApplication.user_id == user_id,
        JobApplication.created_by == user_id,
        JobApplication.is_active.is_(True),
        (JobApplication.similarity_score < 50)
        | (JobApplication.similarity_score.is_(None)),
    )

    r100 = await db.execute(score_100)
    r90 = await db.execute(above_90)
    r80 = await db.execute(above_80)
    r70 = await db.execute(above_70)
    r60 = await db.execute(above_60)
    r50 = await db.execute(above_50)
    rb50 = await db.execute(below_50)

    return {
        "score_100": r100.scalar() or 0,
        "above_90": r90.scalar() or 0,
        "above_80": r80.scalar() or 0,
        "above_70": r70.scalar() or 0,
        "above_60": r60.scalar() or 0,
        "above_50": r50.scalar() or 0,
        "below_50": rb50.scalar() or 0,
    }


async def get_job_applications_by_date_and_similarity(
    db: AsyncSession,
    user_id: int,
    target_date: date,
    min_similarity_score: float,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[JobApplication], int]:
    """
    Retrieve job applications created on the given date with similarity_score
    greater than or equal to min_similarity_score.
    """
    date_col = cast(JobApplication.created_at, Date)
    base_query = (
        select(JobApplication)
        .where(JobApplication.user_id == user_id)
        .where(JobApplication.created_by == user_id)
        .where(date_col == target_date)
        .where(JobApplication.similarity_score >= min_similarity_score)
        .order_by(JobApplication.created_at.desc())
    )
    result = await db.execute(base_query.offset(skip).limit(limit))
    items = list(result.scalars().all())

    count_query = (
        select(func.count(JobApplication.id))
        .where(JobApplication.user_id == user_id)
        .where(JobApplication.created_by == user_id)
        .where(date_col == target_date)
        .where(JobApplication.similarity_score >= min_similarity_score)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


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


async def bulk_update_job_applications_is_active(
    db: AsyncSession,
    user_id: int,
    job_application_ids: list[int],
    is_active: bool,
) -> int:
    """Set is_active for all job applications owned by the user with given ids."""
    if not job_application_ids:
        return 0
    result = await db.execute(
        update(JobApplication)
        .where(
            JobApplication.user_id == user_id,
            JobApplication.created_by == user_id,
            JobApplication.id.in_(job_application_ids),
        )
        .values(is_active=is_active)
    )
    await db.flush()
    return int(result.rowcount or 0)


async def create_job_application_email_log(
    db: AsyncSession,
    job_application_id: int,
    email_log_id: int,
    bulk_job_application_email_send_id: int | None = None,
) -> JobApplicationEmailLog:
    """
    Create a pivot record linking a job application to an email log.
    """
    record = JobApplicationEmailLog(
        job_application_id=job_application_id,
        email_log_id=email_log_id,
        bulk_job_application_email_send_id=bulk_job_application_email_send_id,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def get_email_send_count_for_job_application(
    db: AsyncSession,
    job_application_id: int,
) -> int:
    """
    Return the number of email logs linked to the given job application.
    """
    result = await db.execute(
        select(func.count(JobApplicationEmailLog.id)).where(
            JobApplicationEmailLog.job_application_id == job_application_id
        )
    )
    return result.scalar() or 0


async def get_email_logs_for_job_application(
    db: AsyncSession,
    job_application_id: int,
) -> list:
    """
    Return all email logs linked to the given job application.
    """
    from app.modules.email.models import EmailLog

    result = await db.execute(
        select(EmailLog)
        .join(
            JobApplicationEmailLog,
            JobApplicationEmailLog.email_log_id == EmailLog.id,
        )
        .where(
            JobApplicationEmailLog.job_application_id == job_application_id
        )
        .order_by(EmailLog.created_at.desc())
    )
    return list(result.scalars().all())


async def filter_job_application_ids_by_min_similarity(
    db: AsyncSession,
    job_application_ids: list[int],
    user_id: int,
    min_similarity_score: float,
) -> list[int]:
    """
    Keep IDs in the same order as ``job_application_ids`` that belong to the user
    and have similarity_score >= min_similarity_score (NULL scores excluded).
    dedupe first would change behavior — caller passes list as intended.
    """
    if not job_application_ids:
        return []
    result = await db.execute(
        select(JobApplication.id).where(
            JobApplication.id.in_(job_application_ids),
            JobApplication.user_id == user_id,
            JobApplication.created_by == user_id,
            JobApplication.similarity_score.isnot(None),
            JobApplication.similarity_score >= min_similarity_score,
        )
    )
    allowed = {row[0] for row in result.all()}
    return [jid for jid in job_application_ids if jid in allowed]


async def create_bulk_job_application_email_send(
    db: AsyncSession,
    data: dict,
) -> BulkJobApplicationEmailSend:
    """
    Create a new bulk job application email send record.
    """
    record = BulkJobApplicationEmailSend(**data)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def get_bulk_job_application_email_send_by_id(
    db: AsyncSession,
    bulk_id: int,
) -> BulkJobApplicationEmailSend | None:
    """
    Retrieve a bulk job application email send by id.
    """
    result = await db.execute(
        select(BulkJobApplicationEmailSend).where(
            BulkJobApplicationEmailSend.id == bulk_id
        )
    )
    return result.scalars().first()


async def create_bulk_job_application_email_send_log(
    db: AsyncSession,
    bulk_job_application_email_send_id: int,
    action: str,
    progress: int = 0,
    status: str = "pending",
    details: str | None = None,
    meta_data: dict | None = None,
) -> BulkJobApplicationEmailSendLog:
    """
    Create a new bulk job application email send log entry.
    """
    log = BulkJobApplicationEmailSendLog(
        bulk_job_application_email_send_id=bulk_job_application_email_send_id,
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


async def get_bulk_job_application_email_send_logs(
    db: AsyncSession,
    bulk_job_application_email_send_id: int,
) -> list[BulkJobApplicationEmailSendLog]:
    """
    Retrieve all logs for a bulk job application email send.
    """
    result = await db.execute(
        select(BulkJobApplicationEmailSendLog)
        .where(
            BulkJobApplicationEmailSendLog.bulk_job_application_email_send_id
            == bulk_job_application_email_send_id
        )
        .order_by(BulkJobApplicationEmailSendLog.created_at.asc())
    )
    return list(result.scalars().all())


async def update_bulk_job_application_email_send_status(
    db: AsyncSession,
    bulk_id: int,
    status: str | BulkJobApplicationEmailSendStatus,
) -> BulkJobApplicationEmailSend | None:
    """
    Update the status of a bulk job application email send.
    """
    record = await get_bulk_job_application_email_send_by_id(db, bulk_id)
    if record is None:
        return None
    status_value = (
        status.value
        if isinstance(status, BulkJobApplicationEmailSendStatus)
        else status
    )
    record.status = status_value
    await db.flush()
    await db.refresh(record)
    return record
