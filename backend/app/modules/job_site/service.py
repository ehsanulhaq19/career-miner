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
) -> JobSiteListResponse:
    """Return a paginated list of job sites."""
    items, total = await get_job_sites(db, skip=skip, limit=limit, is_active=is_active)
    return JobSiteListResponse(
        items=[JobSiteResponse.model_validate(item) for item in items],
        total=total,
    )


async def get_job_site(db: AsyncSession, job_site_id: int) -> JobSiteResponse:
    """Return a single job site or raise NotFoundException."""
    job_site = await get_job_site_by_id(db, job_site_id)
    if job_site is None:
        raise NotFoundException(detail="Job site not found")
    return JobSiteResponse.model_validate(job_site)


async def create_job_site(db: AsyncSession, job_site_create: JobSiteCreate) -> JobSiteResponse:
    """Create a new job site and return the response."""
    job_site = await crud_create(db, job_site_create.model_dump())
    return JobSiteResponse.model_validate(job_site)


async def update_job_site(
    db: AsyncSession,
    job_site_id: int,
    job_site_update: JobSiteUpdate,
) -> JobSiteResponse:
    """Update a job site or raise NotFoundException if it does not exist."""
    job_site = await crud_update(db, job_site_id, job_site_update.model_dump(exclude_unset=True))
    if job_site is None:
        raise NotFoundException(detail="Job site not found")
    return JobSiteResponse.model_validate(job_site)


async def delete_job_site(db: AsyncSession, job_site_id: int) -> dict:
    """Delete a job site or raise NotFoundException if it does not exist."""
    deleted = await crud_delete(db, job_site_id)
    if not deleted:
        raise NotFoundException(detail="Job site not found")
    return {"message": "Job site deleted successfully"}
