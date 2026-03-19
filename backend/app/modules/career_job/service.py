from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.career_client.crud import get_career_client_by_id
from app.modules.career_job.crud import (
    create_career_job_user,
    get_career_job_by_id,
    get_career_jobs,
    get_career_jobs_count_by_site,
    get_career_job_user,
    get_dashboard_stats as crud_dashboard_stats,
    get_seen_career_job_ids_from_list,
    mark_all_jobs_seen_for_user,
)
from app.modules.career_job.schemas import (
    CareerJobDetailResponse,
    CareerJobListResponse,
    CareerJobResponse,
    DashboardStatsResponse,
    JobSiteCardResponse,
)
from app.modules.job_site.crud import get_job_site_by_id, get_job_sites


async def list_career_jobs(
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
) -> CareerJobListResponse:
    """
    Return a paginated list of career jobs with job site names.
    Results are ordered by created_at descending.
    """
    items, total = await get_career_jobs(
        db,
        skip=skip,
        limit=limit,
        job_site_id=job_site_id,
        career_client_id=career_client_id,
        category=category,
        search=search,
        user_id=user_id,
        show_unseen_jobs=show_unseen_jobs,
        has_client_emails=has_client_emails,
    )

    seen_job_ids: set[int] = set()
    if user_id is not None and items:
        career_job_ids = [item.id for item in items]
        seen_job_ids = await get_seen_career_job_ids_from_list(
            db, user_id, career_job_ids
        )

    response_items = []
    site_cache: dict[int, str] = {}
    client_cache: dict[int, str] = {}
    for item in items:
        job_site_name = site_cache.get(item.job_site_id)
        if job_site_name is None:
            site = await get_job_site_by_id(db, item.job_site_id)
            job_site_name = site.name if site else None
            site_cache[item.job_site_id] = job_site_name

        career_client_name = None
        if item.career_client_id:
            career_client_name = client_cache.get(item.career_client_id)
            if career_client_name is None:
                client = await get_career_client_by_id(db, item.career_client_id)
                career_client_name = client.name if client else None
                client_cache[item.career_client_id] = career_client_name

        job_data = CareerJobResponse.model_validate(item)
        job_data.job_site_name = job_site_name
        job_data.career_client_name = career_client_name
        job_data.job_seen = item.id in seen_job_ids
        response_items.append(job_data)

    page = (skip // limit) + 1 if limit > 0 else 1
    return CareerJobListResponse(
        items=response_items,
        total=total,
        page=page,
        limit=limit,
    )


async def get_career_job(
    db: AsyncSession, career_job_id: int, user_id: int | None = None
) -> CareerJobDetailResponse:
    """Return a single career job detail or raise NotFoundException."""
    career_job = await get_career_job_by_id(db, career_job_id)
    if career_job is None:
        raise NotFoundException(detail="Career job not found")

    site = await get_job_site_by_id(db, career_job.job_site_id)
    job_data = CareerJobDetailResponse.model_validate(career_job)
    job_data.job_site_name = site.name if site else None
    if career_job.career_client_id:
        client = await get_career_client_by_id(db, career_job.career_client_id)
        if client:
            job_data.career_client_name = client.name
            job_data.career_client_emails = list(client.emails or [])
            job_data.career_client_official_website = client.official_website
    if user_id is not None:
        seen_ids = await get_seen_career_job_ids_from_list(
            db, user_id, [career_job_id]
        )
        job_data.job_seen = career_job_id in seen_ids
    return job_data


async def mark_all_jobs_seen(db: AsyncSession, user_id: int) -> dict:
    """Mark all career jobs as seen by the user."""
    count = await mark_all_jobs_seen_for_user(db, user_id)
    return {"marked_count": count}


async def mark_job_seen(
    db: AsyncSession, career_job_id: int, user_id: int
) -> None:
    """Mark a career job as seen by the user. Creates record if not exists."""
    existing = await get_career_job_user(db, career_job_id, user_id)
    if existing is None:
        await create_career_job_user(db, career_job_id, user_id)


async def get_career_job_dates_grouped(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
):
    """Return date groups with job counts for tabular UI."""
    from app.modules.career_job.crud import get_career_job_dates_grouped as crud_dates
    from app.modules.career_job.schemas import (
        CareerJobDateGroupListResponse,
        CareerJobDateGroupResponse,
    )

    rows, total = await crud_dates(db, skip=skip, limit=limit)
    items = [
        CareerJobDateGroupResponse(
            date=d.isoformat() if d else "",
            job_count=count,
        )
        for d, count in rows
    ]
    page = (skip // limit) + 1 if limit > 0 else 1
    return CareerJobDateGroupListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


async def get_career_jobs_by_date(
    db: AsyncSession,
    target_date: str,
    skip: int = 0,
    limit: int = 50,
    user_id: int | None = None,
):
    """Return career jobs for a date with application counts."""
    from datetime import datetime

    from app.modules.career_job.crud import get_career_jobs_by_date as crud_by_date
    from app.modules.career_job.schemas import (
        CareerJobWithApplicationCountsResponse,
        CareerJobWithCountsListResponse,
    )

    try:
        parsed = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        from app.core.exceptions import BadRequestException

        raise BadRequestException(detail="Invalid date format. Use YYYY-MM-DD")

    rows, total = await crud_by_date(
        db, target_date=parsed, skip=skip, limit=limit, user_id=user_id
    )
    site_cache = {}
    client_cache = {}
    items = []
    for job, active_count, inactive_count in rows:
        job_site_name = site_cache.get(job.job_site_id)
        if job_site_name is None:
            site = await get_job_site_by_id(db, job.job_site_id)
            job_site_name = site.name if site else None
            site_cache[job.job_site_id] = job_site_name
        career_client_name = None
        career_client_emails: list[str] = []
        career_client_official_website: str | None = None
        if job.career_client_id:
            cached = client_cache.get(job.career_client_id)
            if cached is not None:
                career_client_name, career_client_emails, career_client_official_website = cached
            else:
                client = await get_career_client_by_id(db, job.career_client_id)
                career_client_name = client.name if client else None
                career_client_emails = list(client.emails or []) if client else []
                career_client_official_website = client.official_website if client else None
                client_cache[job.career_client_id] = (
                    career_client_name,
                    career_client_emails,
                    career_client_official_website,
                )
        item = CareerJobWithApplicationCountsResponse.model_validate(job)
        item.job_site_name = job_site_name
        item.career_client_name = career_client_name
        item.career_client_emails = career_client_emails
        item.career_client_official_website = career_client_official_website
        item.active_application_count = active_count
        item.inactive_application_count = inactive_count
        items.append(item)
    page = (skip // limit) + 1 if limit > 0 else 1
    return CareerJobWithCountsListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


async def get_dashboard_stats(db: AsyncSession) -> DashboardStatsResponse:
    """Build and return the dashboard statistics including per-site cards."""
    stats = await crud_dashboard_stats(db)

    sites, _ = await get_job_sites(db, skip=0, limit=1000)

    job_site_cards = []
    for site in sites:
        total_jobs = await get_career_jobs_count_by_site(db, site.id)
        job_site_cards.append(
            JobSiteCardResponse(
                id=site.id,
                name=site.name,
                url=site.url,
                total_jobs=total_jobs,
                last_scrapped=site.last_scrapped,
                is_active=site.is_active,
            )
        )

    return DashboardStatsResponse(
        total_jobs_executed=stats["total_jobs_executed"],
        total_job_records=stats["total_job_records"],
        total_job_sites=stats["total_job_sites"],
        total_clients=stats["total_clients"],
        job_site_cards=job_site_cards,
    )
