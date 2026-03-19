from datetime import date

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.models import CareerClient
from app.modules.career_job.models import CareerJob, CareerJobUser
from app.modules.job_application.models import JobApplication
from app.modules.job_site.models import JobSite
from app.modules.scrap_job.models import ScrapJob


async def get_career_job_user(
    db: AsyncSession, career_job_id: int, user_id: int
) -> CareerJobUser | None:
    """Retrieve a career job user record by career job id and user id."""
    result = await db.execute(
        select(CareerJobUser).where(
            CareerJobUser.career_job_id == career_job_id,
            CareerJobUser.user_id == user_id,
        )
    )
    return result.scalars().first()


async def create_career_job_user(
    db: AsyncSession, career_job_id: int, user_id: int
) -> CareerJobUser:
    """Create a new career job user record."""
    career_job_user = CareerJobUser(career_job_id=career_job_id, user_id=user_id)
    db.add(career_job_user)
    await db.flush()
    await db.refresh(career_job_user)
    return career_job_user


async def get_all_career_job_ids(db: AsyncSession) -> list[int]:
    """Return list of all career job ids."""
    result = await db.execute(select(CareerJob.id))
    return list(result.scalars().all())


async def mark_all_jobs_seen_for_user(
    db: AsyncSession, user_id: int
) -> int:
    """Mark all career jobs as seen for the user. Returns count of newly created records."""
    all_ids = await get_all_career_job_ids(db)
    if not all_ids:
        return 0
    seen_ids = await get_seen_career_job_ids_from_list(db, user_id, all_ids)
    to_create = [id_ for id_ in all_ids if id_ not in seen_ids]
    for career_job_id in to_create:
        await create_career_job_user(db, career_job_id, user_id)
    return len(to_create)


async def get_seen_career_job_ids_from_list(
    db: AsyncSession, user_id: int, career_job_ids: list[int]
) -> set[int]:
    """Return set of career job ids from the given list that the user has seen."""
    if not career_job_ids:
        return set()
    result = await db.execute(
        select(CareerJobUser.career_job_id).where(
            CareerJobUser.user_id == user_id,
            CareerJobUser.career_job_id.in_(career_job_ids),
        )
    )
    rows = result.scalars().all()
    return set(rows)


async def get_career_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    job_site_id: int | None = None,
    career_client_id: int | None = None,
    category: str | None = None,
    search: str | None = None,
    user_id: int | None = None,
    show_unseen_jobs: bool = False,
    has_client_emails: bool = False,
) -> tuple[list[CareerJob], int]:
    """
    Retrieve a paginated list of career jobs with optional filters.
    Results are ordered by created_at descending.
    """
    query = select(CareerJob)
    count_query = select(func.count(CareerJob.id))

    if job_site_id is not None:
        query = query.where(CareerJob.job_site_id == job_site_id)
        count_query = count_query.where(CareerJob.job_site_id == job_site_id)

    if career_client_id is not None:
        query = query.where(CareerJob.career_client_id == career_client_id)
        count_query = count_query.where(
            CareerJob.career_client_id == career_client_id
        )

    if search is not None:
        query = query.where(CareerJob.title.ilike(f"%{search}%"))
        count_query = count_query.where(CareerJob.title.ilike(f"%{search}%"))

    if show_unseen_jobs and user_id is not None:
        subq = select(CareerJobUser.career_job_id).where(
            CareerJobUser.user_id == user_id
        )
        query = query.where(CareerJob.id.not_in(subq))
        count_query = count_query.where(CareerJob.id.not_in(subq))

    if has_client_emails:
        query = query.join(CareerClient, CareerJob.career_client_id == CareerClient.id).where(
            func.coalesce(func.json_array_length(CareerClient.emails), 0) > 0
        )
        count_query = count_query.join(
            CareerClient, CareerJob.career_client_id == CareerClient.id
        ).where(func.coalesce(func.json_array_length(CareerClient.emails), 0) > 0)

    query = query.order_by(CareerJob.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    items = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_career_job_by_id(db: AsyncSession, career_job_id: int) -> CareerJob | None:
    """Retrieve a single career job by its primary key."""
    result = await db.execute(select(CareerJob).where(CareerJob.id == career_job_id))
    return result.scalars().first()


async def create_career_job(db: AsyncSession, data: dict) -> CareerJob:
    """Create a new career job record from the provided data dictionary."""
    career_job = CareerJob(**data)
    db.add(career_job)
    await db.flush()
    await db.refresh(career_job)
    return career_job


async def check_duplicate_job(
    db: AsyncSession,
    title: str,
    job_site_id: int,
    url: str | None = None,
    description: str | None = None,
) -> CareerJob | None:
    """Check if a career job with the same title and job_site_id already exists."""
    query = select(CareerJob).where(
        CareerJob.title == title,
        CareerJob.job_site_id == job_site_id,
    )

    if url is not None:
        query = query.where(CareerJob.url == url)

    if description is not None:
        query = query.where(CareerJob.description == description)

    result = await db.execute(query)
    return result.scalars().first()


async def check_job_exist(
    db: AsyncSession,
    title: str,
    job_site_id: int,
    career_client_id: int | None = None,
    links: list[str] | None = None,
) -> CareerJob | None:
    """Check if a career job with the same title, job_site_id and career_client_id already exists."""

    query = select(CareerJob).where(
        CareerJob.title == title,
        CareerJob.job_site_id == job_site_id,
        CareerJob.career_client_id == career_client_id if career_client_id is not None else None,
        CareerJob.url.in_(links) if links is not None else None,
    )
    result = await db.execute(query)
    return result.scalars().first() is not None


async def get_total_career_jobs_count(db: AsyncSession) -> int:
    """Return the total count of all career jobs."""
    result = await db.execute(select(func.count(CareerJob.id)))
    return result.scalar() or 0


async def get_career_jobs_count_by_site(db: AsyncSession, job_site_id: int) -> int:
    """Return the count of career jobs for a specific job site."""
    result = await db.execute(
        select(func.count(CareerJob.id)).where(CareerJob.job_site_id == job_site_id)
    )
    return result.scalar() or 0


async def get_career_job_dates_grouped(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[tuple[date, int]], int]:
    """
    Return distinct dates of career jobs with job count per date.
    Only includes jobs whose client has at least one email.
    Ordered by date descending. Used for tabular UI grouped by creation date.
    """
    date_col = cast(CareerJob.created_at, Date)
    client_has_emails = func.coalesce(
        func.json_array_length(CareerClient.emails), 0
    ) > 0
    subq = (
        select(date_col, func.count(CareerJob.id).label("job_count"))
        .select_from(CareerJob)
        .join(CareerClient, CareerJob.career_client_id == CareerClient.id)
        .where(client_has_emails)
        .group_by(date_col)
        .order_by(date_col.desc())
    )
    count_subq = (
        select(date_col)
        .select_from(CareerJob)
        .join(CareerClient, CareerJob.career_client_id == CareerClient.id)
        .where(client_has_emails)
        .distinct()
        .subquery()
    )
    count_result = await db.execute(select(func.count()).select_from(count_subq))
    total = count_result.scalar() or 0
    result = await db.execute(subq.offset(skip).limit(limit))
    rows = result.all()
    return [(r[0], r[1]) for r in rows], total


async def get_career_jobs_by_date(
    db: AsyncSession,
    target_date: date,
    skip: int = 0,
    limit: int = 50,
    user_id: int | None = None,
) -> tuple[list[tuple[CareerJob, int, int]], int]:
    """
    Return career jobs created on the given date with job application counts.
    Only includes jobs whose client has at least one email.
    Returns list of (CareerJob, active_count, inactive_count) and total.
    """
    date_col = cast(CareerJob.created_at, Date)
    client_has_emails = func.coalesce(
        func.json_array_length(CareerClient.emails), 0
    ) > 0
    base_query = (
        select(CareerJob)
        .join(CareerClient, CareerJob.career_client_id == CareerClient.id)
        .where(date_col == target_date)
        .where(client_has_emails)
    )
    count_query = (
        select(func.count(CareerJob.id))
        .select_from(CareerJob)
        .join(CareerClient, CareerJob.career_client_id == CareerClient.id)
        .where(date_col == target_date)
        .where(client_has_emails)
    )
    base_query = base_query.order_by(CareerJob.created_at.desc())
    result = await db.execute(base_query.offset(skip).limit(limit))
    jobs = list(result.scalars().all())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    job_app_counts: list[tuple[CareerJob, int, int]] = []
    for job in jobs:
        active_query = select(func.count(JobApplication.id)).where(
            JobApplication.career_job_id == job.id,
            JobApplication.is_active.is_(True),
        )
        inactive_query = select(func.count(JobApplication.id)).where(
            JobApplication.career_job_id == job.id,
            JobApplication.is_active.is_(False),
        )
        if user_id is not None:
            active_query = active_query.where(JobApplication.user_id == user_id)
            inactive_query = inactive_query.where(JobApplication.user_id == user_id)
        active_result = await db.execute(active_query)
        inactive_result = await db.execute(inactive_query)
        active_count = active_result.scalar() or 0
        inactive_count = inactive_result.scalar() or 0
        job_app_counts.append((job, active_count, inactive_count))

    return job_app_counts, total


async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Return aggregate counts for the dashboard overview."""
    scrap_count_result = await db.execute(select(func.count(ScrapJob.id)))
    total_jobs_executed = scrap_count_result.scalar() or 0

    career_count_result = await db.execute(select(func.count(CareerJob.id)))
    total_job_records = career_count_result.scalar() or 0

    site_count_result = await db.execute(select(func.count(JobSite.id)))
    total_job_sites = site_count_result.scalar() or 0

    client_count_result = await db.execute(select(func.count(CareerClient.id)))
    total_clients = client_count_result.scalar() or 0

    return {
        "total_jobs_executed": total_jobs_executed,
        "total_job_records": total_job_records,
        "total_job_sites": total_job_sites,
        "total_clients": total_clients,
    }
