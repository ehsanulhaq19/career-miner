from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
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
    category: str | None = None,
    search: str | None = None,
    user_id: int | None = None,
    show_unseen_jobs: bool = False,
) -> CareerJobListResponse:
    """Return a paginated list of career jobs with job site names."""
    items, total = await get_career_jobs(
        db,
        skip=skip,
        limit=limit,
        job_site_id=job_site_id,
        category=category,
        search=search,
        user_id=user_id,
        show_unseen_jobs=show_unseen_jobs,
    )

    seen_job_ids: set[int] = set()
    if user_id is not None and items:
        career_job_ids = [item.id for item in items]
        seen_job_ids = await get_seen_career_job_ids_from_list(
            db, user_id, career_job_ids
        )

    response_items = []
    site_cache: dict[int, str] = {}
    for item in items:
        job_site_name = site_cache.get(item.job_site_id)
        if job_site_name is None:
            site = await get_job_site_by_id(db, item.job_site_id)
            job_site_name = site.name if site else None
            site_cache[item.job_site_id] = job_site_name

        job_data = CareerJobResponse.model_validate(item)
        job_data.job_site_name = job_site_name
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
