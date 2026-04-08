from datetime import date

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.career_client.models import CareerClient
from app.modules.career_job.models import CareerJob
from app.modules.email.models import EmailLog
from app.modules.job_application.models import JobApplication, JobApplicationEmailLog


async def create_email_log(db: AsyncSession, data: dict) -> EmailLog:
    """
    Create a new email log record from the provided data dictionary.
    """
    email_log = EmailLog(**data)
    db.add(email_log)
    await db.flush()
    await db.refresh(email_log)
    return email_log


async def get_job_email_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    career_client_id: int | None = None,
    created_date_from: date | None = None,
    created_date_to: date | None = None,
    search: str | None = None,
    user_id: int | None = None,
) -> tuple[list[tuple], int]:
    """
    Retrieve paginated job email logs (email logs linked to job applications).
    Results ordered by email log created_at descending.
    """
    base = (
        select(EmailLog, JobApplication, CareerJob, CareerClient)
        .join(JobApplicationEmailLog, JobApplicationEmailLog.email_log_id == EmailLog.id)
        .join(JobApplication, JobApplication.id == JobApplicationEmailLog.job_application_id)
        .join(CareerJob, CareerJob.id == JobApplication.career_job_id)
        .outerjoin(CareerClient, CareerClient.id == CareerJob.career_client_id)
    )
    count_base = (
        select(func.count(EmailLog.id))
        .select_from(EmailLog)
        .join(JobApplicationEmailLog, JobApplicationEmailLog.email_log_id == EmailLog.id)
        .join(JobApplication, JobApplication.id == JobApplicationEmailLog.job_application_id)
        .join(CareerJob, CareerJob.id == JobApplication.career_job_id)
        .outerjoin(CareerClient, CareerClient.id == CareerJob.career_client_id)
    )

    if user_id is not None:
        owner = JobApplication.created_by == user_id
        base = base.where(owner)
        count_base = count_base.where(owner)

    if career_client_id is not None:
        base = base.where(CareerJob.career_client_id == career_client_id)
        count_base = count_base.where(CareerJob.career_client_id == career_client_id)

    if created_date_from is not None:
        date_col = cast(EmailLog.created_at, Date)
        base = base.where(date_col >= created_date_from)
        count_base = count_base.where(date_col >= created_date_from)

    if created_date_to is not None:
        date_col = cast(EmailLog.created_at, Date)
        base = base.where(date_col <= created_date_to)
        count_base = count_base.where(date_col <= created_date_to)

    if search and search.strip():
        term = f"%{search.strip()}%"
        search_cond = or_(
            EmailLog.to_email.ilike(term),
            CareerJob.title.ilike(term),
            CareerClient.name.ilike(term),
            CareerClient.official_website.ilike(term),
        )
        base = base.where(search_cond)
        count_base = count_base.where(search_cond)

    base = base.order_by(EmailLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(base)
    rows = result.all()

    count_result = await db.execute(count_base)
    total = count_result.scalar() or 0

    return [(r[0], r[1], r[2], r[3]) for r in rows], total


async def get_email_log_by_id(db: AsyncSession, email_log_id: int) -> EmailLog | None:
    """Retrieve a single email log by id."""
    result = await db.execute(select(EmailLog).where(EmailLog.id == email_log_id))
    return result.scalars().first()


async def get_job_email_log_detail(
    db: AsyncSession, email_log_id: int
) -> tuple[EmailLog, JobApplication, CareerJob, CareerClient] | None:
    """
    Retrieve full job email log detail with linked job application, career job, and client.
    Returns None if not a job-linked email log.
    """
    result = await db.execute(
        select(EmailLog, JobApplication, CareerJob, CareerClient)
        .join(JobApplicationEmailLog, JobApplicationEmailLog.email_log_id == EmailLog.id)
        .join(JobApplication, JobApplication.id == JobApplicationEmailLog.job_application_id)
        .join(CareerJob, CareerJob.id == JobApplication.career_job_id)
        .outerjoin(CareerClient, CareerClient.id == CareerJob.career_client_id)
        .where(EmailLog.id == email_log_id)
        .limit(1)
    )
    row = result.first()
    return row if row else None


async def get_job_email_logs_count(db: AsyncSession) -> int:
    """Return total count of email logs linked to job applications."""
    result = await db.execute(
        select(func.count(EmailLog.id))
        .select_from(EmailLog)
        .join(JobApplicationEmailLog, JobApplicationEmailLog.email_log_id == EmailLog.id)
    )
    return result.scalar() or 0


async def get_job_email_logs_count_for_user(db: AsyncSession, user_id: int) -> int:
    """Return count of email logs linked to the given user's job applications."""
    result = await db.execute(
        select(func.count(EmailLog.id))
        .select_from(EmailLog)
        .join(
            JobApplicationEmailLog,
            JobApplicationEmailLog.email_log_id == EmailLog.id,
        )
        .join(
            JobApplication,
            JobApplication.id == JobApplicationEmailLog.job_application_id,
        )
        .where(JobApplication.user_id == user_id)
    )
    return result.scalar() or 0
