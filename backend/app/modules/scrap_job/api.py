from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.job_site.crud import get_job_site_by_id
from app.modules.scrap_job.crud import get_scrap_job_by_id
from app.modules.scrap_job.schemas import (
    ScrapJobListResponse,
    ScrapJobLogListResponse,
    ScrapJobResponse,
    ScrapJobStartRequest,
    TestScrapRequest,
)
from app.modules.scrap_job.service import (
    get_scrap_job,
    get_scrap_job_logs,
    get_scrapper_html_for_scrap_job,
    list_scrappers_for_scrap_job_service,
    list_scrap_jobs,
    start_scrap_job,
    start_test_scrap_job,
    stop_scrap_job,
    resume_scrap_job,
)
from app.modules.scraper.schemas import ScrapperHtmlPreviewResponse, ScrapperListResponse
from app.modules.scraper.service import ScraperService

router = APIRouter()


async def _run_scraper_background(
    job_site_id: int,
    scrap_job_id: int,
    load_more_on_scroll: bool = False,
    max_scroll: int = 10,
    depth_levels: int = 0,
) -> None:
    """
    Execute scraper in background with its own database session.
    """
    async with async_session() as db:
        try:
            job_site = await get_job_site_by_id(db, job_site_id)
            if job_site is None:
                return
            scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
            if scrap_job is None:
                return
            scraper = ScraperService()
            await scraper.scrape_job_site(
                db,
                job_site,
                scrap_job,
                load_more_on_scroll=load_more_on_scroll,
                max_scroll=max_scroll,
                depth_levels=depth_levels,
            )
            await db.commit()
        except Exception:
            await db.rollback()


async def _run_test_scraper_background(
    job_site_id: int,
    scrap_job_id: int,
    categories: list[str],
    max_pages_per_scrap: int,
    process_with_llm: bool,
    load_more_on_scroll: bool = False,
    max_scroll: int = 10,
    depth_levels: int = 0,
) -> None:
    """
    Execute test scraper in background with custom parameters.
    """
    async with async_session() as db:
        try:
            job_site = await get_job_site_by_id(db, job_site_id)
            if job_site is None:
                return
            scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
            if scrap_job is None:
                return
            scraper = ScraperService()
            await scraper.scrape_job_site(
                db,
                job_site,
                scrap_job,
                categories=categories,
                max_pages_per_scrap=max_pages_per_scrap,
                process_with_llm=process_with_llm,
                load_more_on_scroll=load_more_on_scroll,
                max_scroll=max_scroll,
                depth_levels=depth_levels,
            )
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
    result = await start_scrap_job(
        db,
        request.job_site_id,
        current_user.id,
        load_more_on_scroll=request.load_more_on_scroll,
        max_scroll=request.max_scroll,
        depth_levels=request.depth_levels,
    )
    background_tasks.add_task(
        _run_scraper_background,
        request.job_site_id,
        result.id,
        request.load_more_on_scroll,
        request.max_scroll,
        request.depth_levels,
    )
    return result


@router.post("/test", response_model=ScrapJobResponse, status_code=201)
async def test_scrap_job_endpoint(
    request: TestScrapRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobResponse:
    """Create and start a test scrap job with custom parameters."""
    result = await start_test_scrap_job(db, request, current_user.id)
    background_tasks.add_task(
        _run_test_scraper_background,
        request.job_site_id,
        result.id,
        request.categories,
        request.max_pages_per_scrap,
        request.process_with_llm,
        request.load_more_on_scroll,
        request.max_scroll,
        request.depth_levels,
    )
    return result


@router.post("/{scrap_job_id}/stop", response_model=ScrapJobResponse)
async def stop_scrap_job_endpoint(
    scrap_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobResponse:
    """Stop a scrap job that is currently in progress."""
    return await stop_scrap_job(db, scrap_job_id, current_user.id)


@router.post("/{scrap_job_id}/resume", response_model=ScrapJobResponse)
async def resume_scrap_job_endpoint(
    scrap_job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobResponse:
    """Resume a stopped scrap job."""
    result = await resume_scrap_job(db, scrap_job_id, current_user.id)
    scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
    if scrap_job:
        job_site = await get_job_site_by_id(db, scrap_job.job_site_id)
        if job_site:
            meta = scrap_job.meta_data or {}
            load_more_on_scroll = meta.get("load_more_on_scroll", False)
            max_scroll = meta.get("max_scroll", 10)
            depth_levels = meta.get("depth_levels", 0)
            background_tasks.add_task(
                _run_scraper_background,
                scrap_job.job_site_id,
                scrap_job_id,
                load_more_on_scroll,
                max_scroll,
                depth_levels,
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
    """List scrap jobs for the current user with optional filtering and pagination."""
    return await list_scrap_jobs(
        db,
        skip=skip,
        limit=limit,
        job_site_id=job_site_id,
        status=status,
        user_id=current_user.id,
    )


@router.get("/{scrap_job_id}", response_model=ScrapJobResponse)
async def get_scrap_job_endpoint(
    scrap_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobResponse:
    """Retrieve a single scrap job by ID."""
    return await get_scrap_job(db, scrap_job_id, user_id=current_user.id)


@router.get("/{scrap_job_id}/logs", response_model=ScrapJobLogListResponse)
async def get_scrap_job_logs_endpoint(
    scrap_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobLogListResponse:
    """Retrieve scrap job logs for a given scrap job."""
    return await get_scrap_job_logs(db, scrap_job_id, user_id=current_user.id)


@router.get("/{scrap_job_id}/scrappers", response_model=ScrapperListResponse)
async def list_scrap_job_scrappers_endpoint(
    scrap_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapperListResponse:
    """List stored HTML pages (scrappers) associated with a scrap job."""
    return await list_scrappers_for_scrap_job_service(
        db, scrap_job_id, user_id=current_user.id
    )


@router.get(
    "/{scrap_job_id}/scrappers/{scrapper_id}/html",
    response_model=ScrapperHtmlPreviewResponse,
)
async def get_scrap_job_scrapper_html_endpoint(
    scrap_job_id: int,
    scrapper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapperHtmlPreviewResponse:
    """Return raw HTML content for preview for one scrapper linked to the job."""
    return await get_scrapper_html_for_scrap_job(
        db, scrap_job_id, scrapper_id, user_id=current_user.id
    )
