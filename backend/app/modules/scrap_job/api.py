from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.job_site.crud import get_job_site_by_id
from app.modules.scrap_job.schemas import (
    ScrapJobListResponse,
    ScrapJobResponse,
    ScrapJobStartRequest,
)
from app.modules.scrap_job.service import (
    get_scrap_job,
    list_scrap_jobs,
    start_scrap_job,
    stop_scrap_job,
    resume_scrap_job,
)
from app.modules.scraper.service import ScraperService

router = APIRouter()


async def _run_scraper_background(job_site_id: int, scrap_job_id: int) -> None:
    """Execute scraper in background with its own database session."""
    async with async_session() as db:
        try:
            job_site = await get_job_site_by_id(db, job_site_id)
            if job_site is None:
                return
            from app.modules.scrap_job.crud import get_scrap_job_by_id

            scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
            if scrap_job is None:
                return
            scraper = ScraperService()
            await scraper.scrape_job_site(db, job_site, scrap_job)
            await db.commit()
        except Exception:
            await db.rollback()


@router.post("/start", response_model=ScrapJobResponse, status_code=201)
async def start_scrap_job_endpoint(
    request: ScrapJobStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobResponse:
    """Create and start a new scrap job for the given job site."""
    result = await start_scrap_job(db, request.job_site_id)
    background_tasks.add_task(
        _run_scraper_background,
        request.job_site_id,
        result.id,
    )
    return result


@router.post("/{scrap_job_id}/stop", response_model=ScrapJobResponse)
async def stop_scrap_job_endpoint(
    scrap_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobResponse:
    """Stop a scrap job that is currently in progress."""
    return await stop_scrap_job(db, scrap_job_id)


@router.post("/{scrap_job_id}/resume", response_model=ScrapJobResponse)
async def resume_scrap_job_endpoint(
    scrap_job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobResponse:
    """Resume a stopped scrap job."""
    result = await resume_scrap_job(db, scrap_job_id)
    from app.modules.scrap_job.crud import get_scrap_job_by_id

    scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
    if scrap_job:
        job_site = await get_job_site_by_id(db, scrap_job.job_site_id)
        if job_site:
            background_tasks.add_task(
                _run_scraper_background,
                scrap_job.job_site_id,
                scrap_job_id,
            )
    return result


@router.get("/", response_model=ScrapJobListResponse)
async def list_scrap_jobs_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    job_site_id: int | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobListResponse:
    """List all scrap jobs with optional filtering and pagination."""
    return await list_scrap_jobs(
        db, skip=skip, limit=limit, job_site_id=job_site_id, status=status,
    )


@router.get("/{scrap_job_id}", response_model=ScrapJobResponse)
async def get_scrap_job_endpoint(
    scrap_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobResponse:
    """Retrieve a single scrap job by ID."""
    return await get_scrap_job(db, scrap_job_id)
