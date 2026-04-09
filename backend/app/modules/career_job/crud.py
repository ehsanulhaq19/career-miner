from datetime import date

from sqlalchemy import Date, and_, cast, exists, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.models import CareerClient
from app.modules.career_job.models import CareerJob, CareerJobScrapJobLink, CareerJobUser
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


async def get_all_career_job_ids(
    db: AsyncSession, created_by: int | None = None
) -> list[int]:
    """Return list of career job ids, optionally scoped to a single owner."""
    q = select(CareerJob.id)
    if created_by is not None:
        q = q.where(CareerJob.created_by == created_by)
    result = await db.execute(q)
    return list(result.scalars().all())


async def mark_all_jobs_seen_for_user(
    db: AsyncSession, user_id: int, created_by: int | None = None
) -> int:
    """Mark all career jobs as seen for the user. Returns count of newly created records."""
    all_ids = await get_all_career_job_ids(db, created_by=created_by)
    if not all_ids:
        return 0
    seen_ids = await get_seen_career_job_ids_from_list(db, user_id, all_ids)
    to_create = [id_ for id_ in all_ids if id_ not in seen_ids]
    for career_job_id in to_create:
        await create_career_job_user(db, career_job_id, user_id)
    return len(to_create)


async def get_career_job_ids_by_filters(
    db: AsyncSession,
    job_site_id: int | None = None,
    career_client_id: int | None = None,
    category: str | None = None,
    search: str | None = None,
    user_id: int | None = None,
    show_unseen_jobs: bool = False,
    has_client_emails: bool = False,
    created_date_from: date | None = None,
    created_date_to: date | None = None,
    created_by: int | None = None,
) -> list[int]:
    """
    Return career job IDs matching the given filters.
    Used for mark-all-seen with filters.
    """
    query = select(CareerJob.id)
    count_query = select(func.count(CareerJob.id))
    query, _ = _apply_career_job_filters(
        query,
        count_query,
        job_site_id=job_site_id,
        career_client_id=career_client_id,
        category=category,
        search=search,
        user_id=user_id,
        show_unseen_jobs=show_unseen_jobs,
        has_client_emails=has_client_emails,
        created_date_from=created_date_from,
        created_date_to=created_date_to,
        created_by=created_by,
    )
    query = query.order_by(CareerJob.created_at.desc())
    result = await db.execute(query)
    return [r[0] for r in result.all()]


async def mark_jobs_seen_for_user_by_ids(
    db: AsyncSession, user_id: int, career_job_ids: list[int]
) -> int:
    """
    Mark the given career jobs as seen for the user.
    Returns count of newly created records.
    """
    if not career_job_ids:
        return 0
    seen_ids = await get_seen_career_job_ids_from_list(db, user_id, career_job_ids)
    to_create = [id_ for id_ in career_job_ids if id_ not in seen_ids]
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


def _apply_career_job_filters(
    query,
    count_query,
    job_site_id: int | None = None,
    career_client_id: int | None = None,
    category: str | None = None,
    search: str | None = None,
    user_id: int | None = None,
    show_unseen_jobs: bool = False,
    has_client_emails: bool = False,
    created_date_from: date | None = None,
    created_date_to: date | None = None,
    created_by: int | None = None,
):
    """Apply common filters to career job query and count query."""
    if created_by is not None:
        query = query.where(CareerJob.created_by == created_by)
        count_query = count_query.where(CareerJob.created_by == created_by)

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

    if created_date_from is not None:
        date_col = cast(CareerJob.created_at, Date)
        query = query.where(date_col >= created_date_from)
        count_query = count_query.where(date_col >= created_date_from)

    if created_date_to is not None:
        date_col = cast(CareerJob.created_at, Date)
        query = query.where(date_col <= created_date_to)
        count_query = count_query.where(date_col <= created_date_to)

    return query, count_query


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
    created_date_from: date | None = None,
    created_date_to: date | None = None,
    created_by: int | None = None,
) -> tuple[list[CareerJob], int]:
    """
    Retrieve a paginated list of career jobs with optional filters.
    Results are ordered by created_at descending.
    """
    query = select(CareerJob)
    count_query = select(func.count(CareerJob.id))
    query, count_query = _apply_career_job_filters(
        query,
        count_query,
        job_site_id=job_site_id,
        career_client_id=career_client_id,
        category=category,
        search=search,
        user_id=user_id,
        show_unseen_jobs=show_unseen_jobs,
        has_client_emails=has_client_emails,
        created_date_from=created_date_from,
        created_date_to=created_date_to,
        created_by=created_by,
    )
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


async def get_career_job_for_user_matching_job_details(
    db: AsyncSession,
    user_id: int,
    job_details: str,
) -> CareerJob | None:
    """
    Newest career job owned by ``user_id`` whose description (trimmed) equals
    ``job_details`` (trimmed), or whose ``meta_data['original_job_details']`` matches
    (set for live-applications from pasted text).
    """
    norm = (job_details or "").strip()
    if not norm:
        return None
    desc_match = func.trim(func.coalesce(CareerJob.description, "")) == norm
    # JSON column: avoid .contains() (compiles to invalid json ~~ on PG). Use JSONB @>.
    meta_jsonb = cast(CareerJob.meta_data, JSONB)
    meta_match = meta_jsonb.contains({"original_job_details": norm})
    result = await db.execute(
        select(CareerJob)
        .where(
            CareerJob.created_by == user_id,
            or_(desc_match, meta_match),
        )
        .order_by(CareerJob.id.desc())
        .limit(1)
    )
    return result.scalars().first()


async def create_career_job(db: AsyncSession, data: dict) -> CareerJob:
    """Create a new career job record from the provided data dictionary."""
    career_job = CareerJob(**data)
    db.add(career_job)
    await db.flush()
    await db.refresh(career_job)
    if career_job.scrap_job_id:
        db.add(
            CareerJobScrapJobLink(
                career_job_id=career_job.id,
                scrap_job_id=career_job.scrap_job_id,
            )
        )
        await db.flush()
    return career_job


async def get_career_job_ids_by_scrap_job_id(
    db: AsyncSession,
    scrap_job_id: int,
    created_by: int | None = None,
) -> list[int]:
    """Return career job ids created under the given scrap job."""
    q = select(CareerJob.id).where(CareerJob.scrap_job_id == scrap_job_id)
    if created_by is not None:
        q = q.where(CareerJob.created_by == created_by)
    result = await db.execute(q)
    return [row[0] for row in result.all()]


async def get_career_client_ids_for_career_jobs(
    db: AsyncSession,
    career_job_ids: list[int],
    created_by: int | None = None,
) -> list[int]:
    """Return distinct career client ids referenced by the given career jobs."""
    if not career_job_ids:
        return []
    q = (
        select(CareerJob.career_client_id)
        .join(CareerClient, CareerClient.id == CareerJob.career_client_id)
        .where(CareerJob.id.in_(career_job_ids))
        .where(CareerJob.career_client_id.isnot(None))
    )
    if created_by is not None:
        q = q.where(
            CareerJob.created_by == created_by,
            CareerClient.created_by == created_by,
        )
    result = await db.execute(q)
    return list(
        dict.fromkeys(
            row[0] for row in result.all() if row[0] is not None
        )
    )


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
    created_by: int | None = None,
) -> bool:
    """Return True if a matching career job already exists for the owner and site."""
    parts = [
        CareerJob.title == title,
        CareerJob.job_site_id == job_site_id,
    ]
    if created_by is not None:
        parts.append(CareerJob.created_by == created_by)
    if career_client_id is not None:
        parts.append(CareerJob.career_client_id == career_client_id)
    if links:
        parts.append(CareerJob.url.in_(links))
    stmt = select(exists().where(and_(*parts)))
    result = await db.execute(stmt)
    return bool(result.scalar())


async def get_total_career_jobs_count(db: AsyncSession) -> int:
    """Return the total count of all career jobs."""
    result = await db.execute(select(func.count(CareerJob.id)))
    return result.scalar() or 0


async def get_career_jobs_count_by_site(
    db: AsyncSession,
    job_site_id: int,
    created_by: int | None = None,
) -> int:
    """Return the count of career jobs for a specific job site."""
    q = select(func.count(CareerJob.id)).where(CareerJob.job_site_id == job_site_id)
    if created_by is not None:
        q = q.where(CareerJob.created_by == created_by)
    result = await db.execute(q)
    return result.scalar() or 0


async def get_career_job_dates_grouped(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    created_by: int | None = None,
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
    )
    if created_by is not None:
        subq = subq.where(CareerJob.created_by == created_by)
    subq = subq.group_by(date_col).order_by(date_col.desc())
    count_subq_base = (
        select(date_col)
        .select_from(CareerJob)
        .join(CareerClient, CareerJob.career_client_id == CareerClient.id)
        .where(client_has_emails)
    )
    if created_by is not None:
        count_subq_base = count_subq_base.where(CareerJob.created_by == created_by)
    count_subq = count_subq_base.distinct().subquery()
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
    created_by: int | None = None,
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
    if created_by is not None:
        base_query = base_query.where(CareerJob.created_by == created_by)
    count_query = (
        select(func.count(CareerJob.id))
        .select_from(CareerJob)
        .join(CareerClient, CareerJob.career_client_id == CareerClient.id)
        .where(date_col == target_date)
        .where(client_has_emails)
    )
    if created_by is not None:
        count_query = count_query.where(CareerJob.created_by == created_by)
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


async def get_dashboard_stats(db: AsyncSession, user_id: int) -> dict:
    """Return aggregate counts for the dashboard overview for one user."""
    from app.modules.email.crud import get_job_email_logs_count_for_user

    scrap_q = select(func.count(ScrapJob.id)).where(ScrapJob.created_by == user_id)
    scrap_count_result = await db.execute(scrap_q)
    total_jobs_executed = scrap_count_result.scalar() or 0

    career_q = select(func.count(CareerJob.id)).where(CareerJob.created_by == user_id)
    career_count_result = await db.execute(career_q)
    total_job_records = career_count_result.scalar() or 0

    site_q = select(func.count(JobSite.id)).where(JobSite.created_by == user_id)
    site_count_result = await db.execute(site_q)
    total_job_sites = site_count_result.scalar() or 0

    client_count_result = await db.execute(
        select(func.count(CareerClient.id)).where(
            CareerClient.is_active == True,
            CareerClient.created_by == user_id,
        )
    )
    total_clients = client_count_result.scalar() or 0

    total_job_email_logs = await get_job_email_logs_count_for_user(db, user_id)

    return {
        "total_jobs_executed": total_jobs_executed,
        "total_job_records": total_job_records,
        "total_job_sites": total_job_sites,
        "total_clients": total_clients,
        "total_job_email_logs": total_job_email_logs,
    }
