"""Scrap client API endpoints."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.scrap_client.schemas import (
    ScrapClientDetailsStartRequest,
    ScrapClientJobListResponse,
    ScrapClientLogListResponse,
    ScrapClientJobResponse,
    ScrapClientStartRequest,
    ScrapClientSiteStartRequest,
    ScrapClientUrlStartRequest,
    ScrapClientStatusResponse,
    TestScrapClientRequest,
    TestScrapClientSiteRequest,
)
from app.modules.scrap_client.service import (
    _run_client_details_scraper,
    _run_client_email_scraper,
    _run_client_site_scraper,
    _run_client_url_scraper,
    get_scrap_client_job,
    get_scrap_client_job_logs,
    get_scrap_client_status,
    get_scrapper_html_for_scrap_client_job,
    list_scrappers_for_scrap_client_job_service,
    list_scrap_client_jobs,
    resume_scrap_client_job,
    start_scrap_client_from_site,
    start_scrap_client_from_url,
    start_scrap_client_details_job,
    start_scrap_client_job,
    start_test_scrap_client_from_site,
    start_test_scrap_client_job,
    stop_scrap_client_job,
)
from app.modules.scraper.schemas import ScrapperHtmlPreviewResponse, ScrapperListResponse

router = APIRouter()
logger = logging.getLogger(__name__)


async def _run_email_scraper_background(
    scrap_client_job_id: int,
    client_ids: list[int] | None,
    only_clients_without_emails: bool,
    url: str | None = None,
    is_test_mode: bool = False,
) -> None:
    """Execute client email scraper in background."""
    try:
        await _run_client_email_scraper(
            scrap_client_job_id,
            client_ids,
            only_clients_without_emails,
            url=url,
            is_test_mode=is_test_mode,
        )
    except Exception as e:
        logger.exception("Background scraper failed: job_id=%s, error=%s", scrap_client_job_id, e)
        raise


async def _run_client_details_background(scrap_client_job_id: int) -> None:
    """Execute client company-details enrichment in background."""
    try:
        await _run_client_details_scraper(scrap_client_job_id)
    except Exception as e:
        logger.exception(
            "Background client details scraper failed: job_id=%s, error=%s",
            scrap_client_job_id,
            e,
        )
        raise


async def _run_site_scraper_background(
    scrap_client_job_id: int,
    client_site_id: int,
    is_test_mode: bool = False,
) -> None:
    """Execute client site data scraper in background."""
    try:
        await _run_client_site_scraper(
            scrap_client_job_id,
            client_site_id,
            is_test_mode=is_test_mode,
        )
    except Exception as e:
        logger.exception("Background site scraper failed: job_id=%s, error=%s", scrap_client_job_id, e)
        raise


async def _run_url_scraper_background(
    scrap_client_job_id: int,
    url: str,
) -> None:
    """Execute client URL data scraper in background."""
    try:
        await _run_client_url_scraper(scrap_client_job_id, url)
    except Exception as e:
        logger.exception("Background URL scraper failed: job_id=%s, error=%s", scrap_client_job_id, e)
        raise


@router.post("/start-from-site", response_model=ScrapClientJobResponse, status_code=201)
async def start_scrap_client_from_site_endpoint(
    request: ScrapClientSiteStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """
    Create a scrap client job with client_site_id stored on the job row (like job_site_id on scrap jobs),
    then run the site scraper in the background using the returned job id.
    """
    result = await start_scrap_client_from_site(
        db, request.client_site_id, current_user.id
    )
    background_tasks.add_task(
        _run_site_scraper_background,
        result.id,
        request.client_site_id,
    )
    return result


@router.post("/start-from-url", response_model=ScrapClientJobResponse, status_code=201)
async def start_scrap_client_from_url_endpoint(
    request: ScrapClientUrlStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """
    Create a scrap client job with source_url stored on the job row, then run the URL scraper
    in the background using the returned job id.
    """
    result = await start_scrap_client_from_url(
        db, request.url, current_user.id
    )
    background_tasks.add_task(
        _run_url_scraper_background,
        result.id,
        request.url,
    )
    return result


@router.post("/test-from-site", response_model=ScrapClientJobResponse, status_code=201)
async def test_scrap_client_from_site_endpoint(
    request: TestScrapClientSiteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """
    Create a test scrap client job with client_site_id on the job row, then run the site scraper
    in the background with test mode enabled.
    """
    result = await start_test_scrap_client_from_site(
        db, request, current_user.id
    )
    background_tasks.add_task(
        _run_site_scraper_background,
        result.id,
        request.client_site_id,
        is_test_mode=True,
    )
    return result


@router.post("/start", response_model=ScrapClientJobResponse, status_code=201)
async def start_scrap_client_job_endpoint(
    request: ScrapClientStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """
    Create a scrap client job; when client_ids are provided, assigns scrap_client_job_id on those
    career clients immediately, then runs the email scraper in the background.
    """
    result = await start_scrap_client_job(db, request, current_user.id)
    background_tasks.add_task(
        _run_email_scraper_background,
        result.id,
        list(request.client_ids),
        False,
    )
    return result


@router.post("/start-details", response_model=ScrapClientJobResponse, status_code=201)
async def start_scrap_client_details_endpoint(
    request: ScrapClientDetailsStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """
    Create a scrap client job that enriches career client profile fields from the web.
    Assigns scrap_client_job_id on the selected clients, then runs the details worker in the background.
    """
    result = await start_scrap_client_details_job(
        db, request, current_user.id
    )
    background_tasks.add_task(_run_client_details_background, result.id)
    return result


@router.post("/test", response_model=ScrapClientJobResponse, status_code=201)
async def test_scrap_client_job_endpoint(
    request: TestScrapClientRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """
    Create a test scrap client job with source_url on the job row when a URL is provided.
    When client_ids are present, assigns scrap_client_job_id on those career clients at initiation.
    Does not persist scraped emails; background worker still links clients to this job id.
    """
    result = await start_test_scrap_client_job(db, request, current_user.id)
    background_tasks.add_task(
        _run_email_scraper_background,
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
    return await get_scrap_client_status(db, current_user.id)


@router.post("/{scrap_client_job_id}/stop", response_model=ScrapClientJobResponse)
async def stop_scrap_client_job_endpoint(
    scrap_client_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """Stop a scrap client job that is currently in progress."""
    logger.info("Stopping scrap client job: id=%s", scrap_client_job_id)
    return await stop_scrap_client_job(db, scrap_client_job_id, current_user.id)


@router.post("/{scrap_client_job_id}/resume", response_model=ScrapClientJobResponse)
async def resume_scrap_client_job_endpoint(
    scrap_client_job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """Resume a stopped scrap client job."""
    logger.info("Resuming scrap client job: id=%s", scrap_client_job_id)
    result = await resume_scrap_client_job(
        db, scrap_client_job_id, current_user.id
    )
    from app.modules.scrap_client.crud import get_scrap_client_job_by_id

    job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
    if job:
        meta = job.meta_data or {}
        if meta.get("job_kind") == "client_details":
            background_tasks.add_task(
                _run_client_details_background,
                scrap_client_job_id,
            )
        else:
            client_site_id = job.client_site_id
            if client_site_id is None:
                client_site_id = meta.get("client_site_id")
            url = job.source_url or meta.get("url")
            client_ids = meta.get("client_ids")
            if client_site_id is not None:
                background_tasks.add_task(
                    _run_site_scraper_background,
                    scrap_client_job_id,
                    client_site_id,
                    is_test_mode=meta.get("is_test_mode", False),
                )
            elif url and (client_ids is None or len(client_ids or []) == 0) and not meta.get("is_test_mode"):
                background_tasks.add_task(
                    _run_url_scraper_background,
                    scrap_client_job_id,
                    url,
                )
            else:
                only_without = meta.get("only_clients_without_emails", False)
                is_test_mode = meta.get("is_test_mode", False)
                background_tasks.add_task(
                    _run_email_scraper_background,
                    scrap_client_job_id,
                    client_ids,
                    only_without,
                    url=url,
                    is_test_mode=is_test_mode,
                )
    return result


@router.get("", response_model=ScrapClientJobListResponse)
async def list_scrap_client_jobs_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobListResponse:
    """List all scrap client jobs with optional filtering and pagination."""
    return await list_scrap_client_jobs(
        db,
        skip=skip,
        limit=limit,
        status=status,
        user_id=current_user.id,
    )


@router.get("/{scrap_client_job_id}", response_model=ScrapClientJobResponse)
async def get_scrap_client_job_endpoint(
    scrap_client_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientJobResponse:
    """Retrieve a single scrap client job by ID."""
    return await get_scrap_client_job(db, scrap_client_job_id, current_user.id)


@router.get("/{scrap_client_job_id}/logs", response_model=ScrapClientLogListResponse)
async def get_scrap_client_job_logs_endpoint(
    scrap_client_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapClientLogListResponse:
    """Retrieve scrap client job logs for a given job."""
    return await get_scrap_client_job_logs(
        db, scrap_client_job_id, user_id=current_user.id
    )


@router.get("/{scrap_client_job_id}/scrappers", response_model=ScrapperListResponse)
async def list_scrap_client_job_scrappers_endpoint(
    scrap_client_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapperListResponse:
    """List stored HTML pages (scrappers) associated with a scrap client job."""
    return await list_scrappers_for_scrap_client_job_service(
        db, scrap_client_job_id, user_id=current_user.id
    )


@router.get(
    "/{scrap_client_job_id}/scrappers/{scrapper_id}/html",
    response_model=ScrapperHtmlPreviewResponse,
)
async def get_scrap_client_job_scrapper_html_endpoint(
    scrap_client_job_id: int,
    scrapper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapperHtmlPreviewResponse:
    """Return raw HTML content for preview for one scrapper linked to the job."""
    return await get_scrapper_html_for_scrap_client_job(
        db, scrap_client_job_id, scrapper_id, user_id=current_user.id
    )
