from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.job_site.models import JobSite


async def get_job_sites(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
) -> tuple[list[JobSite], int]:
    """Retrieve a paginated list of job sites with optional active filter."""
    query = select(JobSite)
    count_query = select(func.count(JobSite.id))

    if is_active is not None:
        query = query.where(JobSite.is_active == is_active)
        count_query = count_query.where(JobSite.is_active == is_active)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    items = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_job_site_by_id(db: AsyncSession, job_site_id: int) -> JobSite | None:
    """Retrieve a single job site by its primary key."""
    result = await db.execute(select(JobSite).where(JobSite.id == job_site_id))
    return result.scalar_one_or_none()


async def create_job_site(db: AsyncSession, data: dict) -> JobSite:
    """Create a new job site record from the provided data dictionary."""
    job_site = JobSite(**data)
    db.add(job_site)
    await db.flush()
    await db.refresh(job_site)
    return job_site


async def update_job_site(db: AsyncSession, job_site_id: int, data: dict) -> JobSite | None:
    """Update an existing job site with only the non-None fields from data."""
    job_site = await get_job_site_by_id(db, job_site_id)
    if job_site is None:
        return None

    for key, value in data.items():
        if value is not None:
            setattr(job_site, key, value)

    await db.flush()
    await db.refresh(job_site)
    return job_site


async def delete_job_site(db: AsyncSession, job_site_id: int) -> bool:
    """Delete a job site by its primary key. Returns True if deleted."""
    job_site = await get_job_site_by_id(db, job_site_id)
    if job_site is None:
        return False

    await db.delete(job_site)
    await db.flush()
    return True


async def get_active_job_sites_for_scraping(db: AsyncSession) -> list[JobSite]:
    """Retrieve active job sites whose scrap_duration has elapsed since last_scrapped."""
    now = (datetime.now(timezone.utc)).replace(tzinfo=None)

    result = await db.execute(select(JobSite).where(JobSite.is_active == True))
    sites = list(result.scalars().all())

    eligible = []
    for site in sites:
        if site.last_scrapped is None:
            eligible.append(site)
        else:
            last = site.last_scrapped.replace(tzinfo=None) if site.last_scrapped.tzinfo else site.last_scrapped
            elapsed = now - last
            if elapsed >= timedelta(minutes=site.scrap_duration):
                eligible.append(site)

    return eligible


async def update_last_scrapped(
    db: AsyncSession,
    job_site_id: int,
    scrapped_at: datetime,
) -> None:
    """Update the last_scrapped timestamp for a given job site."""
    job_site = await get_job_site_by_id(db, job_site_id)
    if job_site is not None:
        job_site.last_scrapped = scrapped_at
        await db.flush()
