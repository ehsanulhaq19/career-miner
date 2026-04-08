from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.job_site.crud import (
    create_job_site as crud_create,
    delete_job_site as crud_delete,
    get_job_site_by_id,
    get_job_sites,
    update_job_site as crud_update,
)
from app.modules.job_site.schemas import (
    JobSiteCreate,
    JobSiteListResponse,
    JobSiteResponse,
    JobSiteUpdate,
)


async def list_job_sites(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
    user_id: int | None = None,
) -> JobSiteListResponse:
    """Return a paginated list of job sites."""
    items, total = await get_job_sites(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        created_by=user_id,
    )
    return JobSiteListResponse(
        items=[JobSiteResponse.model_validate(item) for item in items],
        total=total,
    )


async def get_job_site(
    db: AsyncSession, job_site_id: int, user_id: int | None = None
) -> JobSiteResponse:
    """Return a single job site or raise NotFoundException."""
    job_site = await get_job_site_by_id(db, job_site_id)
    if job_site is None:
        raise NotFoundException(detail="Job site not found")
    if user_id is not None and job_site.created_by != user_id:
        raise NotFoundException(detail="Job site not found")
    return JobSiteResponse.model_validate(job_site)


async def create_job_site(
    db: AsyncSession, job_site_create: JobSiteCreate, user_id: int
) -> JobSiteResponse:
    """Create a new job site and return the response."""
    data = job_site_create.model_dump()
    data["created_by"] = user_id
    job_site = await crud_create(db, data)
    return JobSiteResponse.model_validate(job_site)


async def update_job_site(
    db: AsyncSession,
    job_site_id: int,
    job_site_update: JobSiteUpdate,
    user_id: int,
) -> JobSiteResponse:
    """Update a job site or raise NotFoundException if it does not exist."""
    existing = await get_job_site_by_id(db, job_site_id)
    if existing is None or existing.created_by != user_id:
        raise NotFoundException(detail="Job site not found")
    job_site = await crud_update(
        db, job_site_id, job_site_update.model_dump(exclude_unset=True)
    )
    if job_site is None:
        raise NotFoundException(detail="Job site not found")
    return JobSiteResponse.model_validate(job_site)


async def delete_job_site(db: AsyncSession, job_site_id: int, user_id: int) -> dict:
    """Delete a job site or raise NotFoundException if it does not exist."""
    existing = await get_job_site_by_id(db, job_site_id)
    if existing is None or existing.created_by != user_id:
        raise NotFoundException(detail="Job site not found")
    deleted = await crud_delete(db, job_site_id)
    if not deleted:
        raise NotFoundException(detail="Job site not found")
    return {"message": "Job site deleted successfully"}
