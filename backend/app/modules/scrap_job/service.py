from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.job_site.crud import get_job_site_by_id
from app.modules.scrap_job.crud import (
    create_scrap_job,
    create_scrap_job_log,
    get_active_scrap_jobs_for_site,
    get_scrap_job_by_id,
    get_scrap_job_logs_by_scrap_job_id,
    get_scrap_jobs,
    update_scrap_job_meta_data,
    update_scrap_job_status,
)
from app.modules.scrap_job.models import ScrapJobStatus
from app.modules.scrap_job.schemas import (
    ScrapJobListResponse,
    ScrapJobLogListResponse,
    ScrapJobLogResponse,
    ScrapJobResponse,
    TestScrapRequest,
)
from app.modules.websocket.service import broadcast_scrap_job_status


async def start_scrap_job(
    db: AsyncSession,
    job_site_id: int,
    load_more_on_scroll: bool = False,
    max_scroll: int = 10,
) -> ScrapJobResponse:
    """
    Create and start a new scrap job for the given job site.
    Fails if the site already has an active (pending or in_progress) job.
    Returns the created job; scraping runs in background.
    """
    job_site = await get_job_site_by_id(db, job_site_id)
    if job_site is None:
        raise NotFoundException(detail="Job site not found")

    active_jobs = await get_active_scrap_jobs_for_site(db, job_site_id)
    if active_jobs:
        raise BadRequestException(
            detail="An active scrap job already exists for this job site"
        )

    meta_data = {
        "load_more_on_scroll": load_more_on_scroll,
        "max_scroll": max_scroll,
    }
    scrap_job = await create_scrap_job(
        db,
        {
            "name": f"job_{int(datetime.now(timezone.utc).timestamp())}",
            "job_site_id": job_site_id,
            "status": ScrapJobStatus.PENDING.value,
            "meta_data": meta_data,
        },
    )
    response = ScrapJobResponse.model_validate(scrap_job)
    await broadcast_scrap_job_status(response.model_dump(), ScrapJobStatus.PENDING.value)
    return response


async def stop_scrap_job(db: AsyncSession, scrap_job_id: int) -> ScrapJobResponse:
    """
    Stop a scrap job that is pending or in progress.
    """
    scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
    if scrap_job is None:
        raise NotFoundException(detail="Scrap job not found")
    if scrap_job.status not in (
        ScrapJobStatus.PENDING.value,
        ScrapJobStatus.IN_PROGRESS.value,
    ):
        raise BadRequestException(
            detail="Only jobs with status 'pending' or 'in_progress' can be stopped"
        )

    updated = await update_scrap_job_status(db, scrap_job_id, ScrapJobStatus.STOPPED)
    response = ScrapJobResponse.model_validate(updated)
    await broadcast_scrap_job_status(response.model_dump(), ScrapJobStatus.STOPPED.value)
    return response


async def resume_scrap_job(db: AsyncSession, scrap_job_id: int) -> ScrapJobResponse:
    """
    Resume a stopped scrap job by setting its status to in_progress.
    Only jobs with status stopped can be resumed.
    """
    scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
    if scrap_job is None:
        raise NotFoundException(detail="Scrap job not found")
    if scrap_job.status != ScrapJobStatus.STOPPED.value:
        raise BadRequestException(
            detail="Only jobs with status 'stopped' can be resumed"
        )

    updated = await update_scrap_job_status(
        db, scrap_job_id, ScrapJobStatus.IN_PROGRESS
    )
    response = ScrapJobResponse.model_validate(updated)
    await broadcast_scrap_job_status(
        response.model_dump(), ScrapJobStatus.IN_PROGRESS.value
    )
    return response


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


async def create_log_and_broadcast(
    db: AsyncSession,
    scrap_job_id: int,
    action: str,
    progress: int = 0,
    status: str = "in_progress",
    details: str | None = None,
    meta_data: dict | None = None,
):
    """
    Create a scrap job log entry and broadcast it via WebSocket.
    Uses a separate session to commit immediately so logs are visible at runtime.
    """
    from app.database import async_session
    from app.modules.websocket.service import broadcast_scrap_job_log

    async with async_session() as log_db:
        try:
            log = await create_scrap_job_log(
                log_db,
                scrap_job_id=scrap_job_id,
                action=action,
                progress=progress,
                status=status,
                details=details,
                meta_data=meta_data,
            )
            await log_db.commit()
            await broadcast_scrap_job_log(ScrapJobLogResponse.model_validate(log).model_dump())
            return log
        except Exception:
            await log_db.rollback()
            raise


async def start_test_scrap_job(
    db: AsyncSession,
    request: TestScrapRequest,
) -> ScrapJobResponse:
    """
    Create and start a test scrap job with custom parameters.
    Bypasses active job check; runs scraper with provided categories,
    max pages, process_with_llm, and scroll options.
    """
    job_site = await get_job_site_by_id(db, request.job_site_id)
    if job_site is None:
        raise NotFoundException(detail="Job site not found")

    meta_data = {
        "load_more_on_scroll": request.load_more_on_scroll,
        "max_scroll": request.max_scroll,
    }
    scrap_job = await create_scrap_job(
        db,
        {
            "name": f"test_{int(datetime.now(timezone.utc).timestamp())}",
            "job_site_id": request.job_site_id,
            "status": ScrapJobStatus.PENDING.value,
            "meta_data": meta_data,
        },
    )
    response = ScrapJobResponse.model_validate(scrap_job)
    await broadcast_scrap_job_status(response.model_dump(), ScrapJobStatus.PENDING.value)
    return response


async def get_scrap_job_logs(
    db: AsyncSession,
    scrap_job_id: int,
) -> ScrapJobLogListResponse:
    """Return all logs for a scrap job."""
    scrap_job = await get_scrap_job_by_id(db, scrap_job_id)
    if scrap_job is None:
        raise NotFoundException(detail="Scrap job not found")
    logs = await get_scrap_job_logs_by_scrap_job_id(db, scrap_job_id)
    return ScrapJobLogListResponse(
        items=[ScrapJobLogResponse.model_validate(log) for log in logs]
    )
