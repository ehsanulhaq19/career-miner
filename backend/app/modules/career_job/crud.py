from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.models import CareerClient
from app.modules.career_job.models import CareerJob, CareerJobUser
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
    category: str | None = None,
    search: str | None = None,
    user_id: int | None = None,
    show_unseen_jobs: bool = False,
) -> tuple[list[CareerJob], int]:
    """Retrieve a paginated list of career jobs with optional filters."""
    query = select(CareerJob)
    count_query = select(func.count(CareerJob.id))

    if job_site_id is not None:
        query = query.where(CareerJob.job_site_id == job_site_id)
        count_query = count_query.where(CareerJob.job_site_id == job_site_id)

    if search is not None:
        query = query.where(CareerJob.title.ilike(f"%{search}%"))
        count_query = count_query.where(CareerJob.title.ilike(f"%{search}%"))

    if show_unseen_jobs and user_id is not None:
        subq = select(CareerJobUser.career_job_id).where(
            CareerJobUser.user_id == user_id
        )
        query = query.where(CareerJob.id.not_in(subq))
        count_query = count_query.where(CareerJob.id.not_in(subq))

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


async def check_job_exists_by_title_and_links(
    db: AsyncSession,
    title: str,
    job_site_id: int,
    links: list[str],
) -> bool:
    """
    Check if a CareerJob exists with same title and one of the links as url.

    Returns True if a matching job exists, False otherwise.
    """
    if not links:
        return False
    query = select(CareerJob).where(
        CareerJob.title == title,
        CareerJob.job_site_id == job_site_id,
        CareerJob.url.in_(links),
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
