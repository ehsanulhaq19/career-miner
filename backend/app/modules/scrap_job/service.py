from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.scrap_job.crud import get_scrap_job_by_id, get_scrap_jobs
from app.modules.scrap_job.schemas import ScrapJobListResponse, ScrapJobResponse


async def list_scrap_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    job_site_id: int | None = None,
    status: str | None = None,
) -> ScrapJobListResponse:
    """Return a paginated list of scrap jobs."""
    items, total = await get_scrap_jobs(
        db, skip=skip, limit=limit, job_site_id=job_site_id, status=status,
    )
    return ScrapJobListResponse(
        items=[ScrapJobResponse.model_validate(item) for item in items],
        total=total,
    )


async def get_scrap_job(db: AsyncSession, scrap_job_id: int) -> ScrapJobResponse:
    """Return a single scrap job or raise NotFoundException."""
    scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
    if scrap_job is None:
        raise NotFoundException(detail="Scrap job not found")
    return ScrapJobResponse.model_validate(scrap_job)
