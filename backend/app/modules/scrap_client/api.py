"""Scrap client API endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.scrap_client.schemas import (
    ScrapClientJobListResponse,
    ScrapClientLogListResponse,
    ScrapClientJobResponse,
    ScrapClientStartRequest,
    ScrapClientStatusResponse,
    TestScrapClientRequest,
)
from app.modules.scrap_client.service import (
    _run_client_email_scraper,
    get_scrap_client_job,
    get_scrap_client_job_logs,
    get_scrap_client_status,
    list_scrap_client_jobs,
    resume_scrap_client_job,
    start_scrap_client_job,
    start_test_scrap_client_job,
    stop_scrap_client_job,
)

router = APIRouter()


async def _run_scraper_background(
    scrap_client_job_id: int,
    client_ids: list[int] | None,
    only_clients_without_emails: bool,
    url: str | None = None,
    is_test_mode: bool = False,
) -> None:
    """Execute client email scraper in background."""
    await _run_client_email_scraper(
        scrap_client_job_id,
        client_ids,
        only_clients_without_emails,
        url=url,
        is_test_mode=is_test_mode,
    )


@router.post("/start", response_model=ScrapClientJobResponse, status_code=201)
async def start_scrap_client_job_endpoint(
    request: ScrapClientStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """Create and start a new scrap client job for email fetching."""
    result = await start_scrap_client_job(db, request)
    background_tasks.add_task(
        _run_scraper_background,
        result.id,
        request.client_ids,
        request.only_clients_without_emails,
    )
    return result


@router.post("/test", response_model=ScrapClientJobResponse, status_code=201)
async def test_scrap_client_job_endpoint(
    request: TestScrapClientRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """Create and start a test scrap client job. Does not save to database."""
    result = await start_test_scrap_client_job(db, request)
    background_tasks.add_task(
        _run_scraper_background,
        result.id,
        request.client_ids or None,
        request.only_clients_without_emails,
        url=request.url,
        is_test_mode=True,
    )
    return result


@router.get("/status", response_model=ScrapClientStatusResponse)
async def get_scrap_client_status_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientStatusResponse:
    """Return scraping progress: pending, processing, completed, failed counts."""
    return await get_scrap_client_status(db)


@router.post("/{scrap_client_job_id}/stop", response_model=ScrapClientJobResponse)
async def stop_scrap_client_job_endpoint(
    scrap_client_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """Stop a scrap client job that is currently in progress."""
    return await stop_scrap_client_job(db, scrap_client_job_id)


@router.post("/{scrap_client_job_id}/resume", response_model=ScrapClientJobResponse)
async def resume_scrap_client_job_endpoint(
    scrap_client_job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """Resume a stopped scrap client job."""
    result = await resume_scrap_client_job(db, scrap_client_job_id)
    from app.modules.scrap_client.crud import get_scrap_client_job_by_id

    job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
    if job and job.meta_data:
        meta = job.meta_data or {}
        client_ids = meta.get("client_ids")
        only_without = meta.get("only_clients_without_emails", False)
        url = meta.get("url")
        is_test_mode = meta.get("is_test_mode", False)
        background_tasks.add_task(
            _run_scraper_background,
            scrap_client_job_id,
            client_ids,
            only_without,
            url=url,
            is_test_mode=is_test_mode,
        )
    return result


@router.get("/", response_model=ScrapClientJobListResponse)
async def list_scrap_client_jobs_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobListResponse:
    """List all scrap client jobs with optional filtering and pagination."""
    return await list_scrap_client_jobs(
        db, skip=skip, limit=limit, status=status,
    )


@router.get("/{scrap_client_job_id}", response_model=ScrapClientJobResponse)
async def get_scrap_client_job_endpoint(
    scrap_client_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """Retrieve a single scrap client job by ID."""
    return await get_scrap_client_job(db, scrap_client_job_id)


@router.get("/{scrap_client_job_id}/logs", response_model=ScrapClientLogListResponse)
async def get_scrap_client_job_logs_endpoint(
    scrap_client_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientLogListResponse:
    """Retrieve scrap client job logs for a given job."""
    return await get_scrap_client_job_logs(db, scrap_client_job_id)
