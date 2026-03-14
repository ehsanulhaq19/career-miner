"""Scrap client job business logic and orchestration."""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.database import async_session
from app.modules.career_client.crud import (
    get_career_client_by_id,
    get_career_clients_without_emails,
    update_career_client,
)
from app.modules.scrap_client.crud import (
    create_scrap_client_job,
    create_scrap_client_job_log,
    get_active_scrap_client_jobs,
    get_scrap_client_job_by_id,
    get_scrap_client_job_logs_by_job_id,
    get_scrap_client_jobs,
    update_scrap_client_job_meta_data,
    update_scrap_client_job_status,
)
from app.modules.scrap_client.email_extractor import extract_emails_from_html
from app.modules.scrap_client.email_pattern_generator import (
    generate_recruiter_email_patterns,
)
from app.modules.scrap_client.email_validator import validate_emails_smtp
from app.modules.scrap_client.models import ScrapClientJobStatus
from app.modules.scrap_client.schemas import (
    ScrapClientJobListResponse,
    ScrapClientJobResponse,
    ScrapClientLogListResponse,
    ScrapClientLogResponse,
    ScrapClientStartRequest,
    ScrapClientStatusResponse,
    TestScrapClientRequest,
)
from app.modules.scrap_client.url_utils import extract_root_domain
from app.modules.scrap_client.website_crawler import WebsiteCrawler
from app.modules.scrap_client.website_discovery import discover_official_website
from app.modules.websocket.service import (
    broadcast_scrap_client_log,
    broadcast_scrap_client_status,
)

CONCURRENCY_LIMIT = 5


async def _create_log_and_broadcast(
    scrap_client_job_id: int,
    action: str,
    progress: int = 0,
    status: str = "in_progress",
    details: str | None = None,
    meta_data: dict | None = None,
) -> None:
    """Create scrap client log and broadcast via WebSocket."""
    async with async_session() as log_db:
        try:
            log = await create_scrap_client_job_log(
                log_db,
                scrap_client_job_id=scrap_client_job_id,
                action=action,
                progress=progress,
                status=status,
                details=details,
                meta_data=meta_data,
            )
            await log_db.commit()
            await broadcast_scrap_client_log(
                ScrapClientLogResponse.model_validate(log).model_dump()
            )
        except Exception:
            await log_db.rollback()
            raise


async def _process_single_client(
    client_id: int,
    client_name: str,
    website_override: str | None = None,
) -> tuple[bool, list[str], str | None]:
    """
    Process a single client: discover website or use override, crawl, extract/generate emails, validate.
    Returns (success, emails_found, official_website).
    """
    website = website_override
    if not website:
        website = await discover_official_website(client_name)
    if not website:
        return False, [], None
    root_domain = extract_root_domain(website)
    if not root_domain:
        return False, [], website
    crawler = WebsiteCrawler(max_pages=15)
    pages_data = await crawler.crawl(website)
    extracted_emails: set[str] = set()
    for _, html in pages_data:
        extracted = extract_emails_from_html(html)
        for e in extracted:
            if root_domain in e.split("@")[-1].lower():
                extracted_emails.add(e)
    candidates = list(extracted_emails)
    if not candidates:
        candidates = generate_recruiter_email_patterns(root_domain)
    validated = await validate_emails_smtp(candidates)
    if not validated and extracted_emails:
        patterns = generate_recruiter_email_patterns(root_domain)
        validated = await validate_emails_smtp(patterns)
    return True, validated, website


async def _run_client_email_scraper(
    scrap_client_job_id: int,
    client_ids: list[int] | None,
    only_clients_without_emails: bool,
    url: str | None = None,
    is_test_mode: bool = False,
) -> None:
    """Background worker that processes clients for email scraping."""

    async def is_stopped() -> bool:
        async with async_session() as s:
            j = await get_scrap_client_job_by_id(s, scrap_client_job_id)
            return j is not None and j.status == ScrapClientJobStatus.STOPPED.value

    async with async_session() as db:
        try:
            job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
            if job is None:
                return
            meta = job.meta_data or {}
            job_url = url or meta.get("url")
            if job_url:
                from app.modules.scrap_client.url_utils import normalize_url

                website_override = normalize_url(job_url)
            else:
                website_override = None
            if client_ids and only_clients_without_emails:
                clients = await get_career_clients_without_emails(
                    db, limit=1000, client_ids=client_ids
                )
            elif client_ids:
                clients = []
                for cid in client_ids:
                    c = await get_career_client_by_id(db, cid)
                    if c and c.name:
                        clients.append(c)
            elif only_clients_without_emails:
                clients = await get_career_clients_without_emails(
                    db, limit=1000
                )
            elif job_url:
                from types import SimpleNamespace

                clients = [SimpleNamespace(id=0, name="url_crawl")]
            else:
                await update_scrap_client_job_status(
                    db, scrap_client_job_id, ScrapClientJobStatus.ERROR
                )
                await db.commit()
                return

            total = len(clients)
            if total == 0:
                await update_scrap_client_job_status(
                    db, scrap_client_job_id, ScrapClientJobStatus.COMPLETED
                )
                await update_scrap_client_job_meta_data(
                    db, scrap_client_job_id, {"total": 0}
                )
                await db.commit()
                return

            await update_scrap_client_job_status(
                db, scrap_client_job_id, ScrapClientJobStatus.IN_PROGRESS
            )
            await update_scrap_client_job_meta_data(
                db,
                scrap_client_job_id,
                {
                    "total": total,
                    "pending": total,
                    "processing": 0,
                    "completed": 0,
                    "failed": 0,
                },
            )
            await db.commit()

            sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
            completed = 0
            failed = 0

            async def process_one(client):
                nonlocal completed, failed
                if await is_stopped():
                    return
                async with sem:
                    if await is_stopped():
                        return
                    success, emails, website = await _process_single_client(
                        client.id,
                        client.name or "",
                        website_override=website_override,
                    )
                    async with async_session() as session:
                        if await is_stopped():
                            return
                        if not is_test_mode and client.id > 0:
                            if success and emails:
                                await update_career_client(
                                    session,
                                    client.id,
                                    {
                                        "emails": emails,
                                        "official_website": website,
                                    },
                                )
                                completed += 1
                            else:
                                if website:
                                    await update_career_client(
                                        session,
                                        client.id,
                                        {"official_website": website},
                                    )
                                failed += 1
                            await session.commit()
                        else:
                            if success and emails:
                                completed += 1
                            else:
                                failed += 1
                    meta = {
                        "total": total,
                        "pending": total - completed - failed,
                        "processing": 0,
                        "completed": completed,
                        "failed": failed,
                    }
                    async with async_session() as mdb:
                        await update_scrap_client_job_meta_data(
                            mdb, scrap_client_job_id, meta
                        )
                        await mdb.commit()
                    progress = int(100 * (completed + failed) / total)
                    await _create_log_and_broadcast(
                        scrap_client_job_id,
                        f"processed_{client.name}",
                        progress=progress,
                        status="completed" if success else "error",
                        details=f"Client {client.name}: {len(emails)} emails",
                        meta_data={"client_id": client.id, "emails": emails},
                    )

            await asyncio.gather(*[process_one(c) for c in clients])

            async with async_session() as fdb:
                j = await get_scrap_client_job_by_id(fdb, scrap_client_job_id)
                if j and j.status != ScrapClientJobStatus.STOPPED.value:
                    await update_scrap_client_job_status(
                        fdb, scrap_client_job_id, ScrapClientJobStatus.COMPLETED
                    )
                await fdb.commit()
                updated = await get_scrap_client_job_by_id(fdb, scrap_client_job_id)
                if updated:
                    await broadcast_scrap_client_status(
                        ScrapClientJobResponse.model_validate(updated).model_dump(),
                        updated.status,
                    )
        except Exception:
            async with async_session() as edb:
                await update_scrap_client_job_status(
                    edb, scrap_client_job_id, ScrapClientJobStatus.ERROR
                )
                await edb.commit()


async def start_scrap_client_job(
    db: AsyncSession,
    request: ScrapClientStartRequest,
) -> ScrapClientJobResponse:
    """
    Create and start a new scrap client job.
    Fails if client_ids and only_clients_without_emails are both empty/False.
    """
    if not request.client_ids and not request.only_clients_without_emails:
        raise BadRequestException(
            detail="Provide client_ids or set only_clients_without_emails to True"
        )

    active = await get_active_scrap_client_jobs(db)
    if active:
        raise BadRequestException(
            detail="An active scrap client job already exists"
        )

    meta_data = {
        "client_ids": request.client_ids,
        "only_clients_without_emails": request.only_clients_without_emails,
    }
    scrap_job = await create_scrap_client_job(
        db,
        {
            "name": f"client_{int(datetime.now(timezone.utc).timestamp())}",
            "status": ScrapClientJobStatus.PENDING.value,
            "meta_data": meta_data,
        },
    )
    response = ScrapClientJobResponse.model_validate(scrap_job)
    await broadcast_scrap_client_status(
        response.model_dump(), ScrapClientJobStatus.PENDING.value
    )
    return response


async def start_test_scrap_client_job(
    db: AsyncSession,
    request: TestScrapClientRequest,
) -> ScrapClientJobResponse:
    """Create and start a test scrap client job. Does not save emails to database."""
    if not request.client_ids and not request.url:
        raise BadRequestException(
            detail="Provide at least one client_id or a url to crawl"
        )

    meta_data = {
        "client_ids": request.client_ids,
        "only_clients_without_emails": request.only_clients_without_emails,
        "url": request.url,
        "is_test_mode": True,
    }
    scrap_job = await create_scrap_client_job(
        db,
        {
            "name": f"test_client_{int(datetime.now(timezone.utc).timestamp())}",
            "status": ScrapClientJobStatus.PENDING.value,
            "meta_data": meta_data,
        },
    )
    response = ScrapClientJobResponse.model_validate(scrap_job)
    await broadcast_scrap_client_status(
        response.model_dump(), ScrapClientJobStatus.PENDING.value
    )
    return response


async def stop_scrap_client_job(
    db: AsyncSession, scrap_client_job_id: int
) -> ScrapClientJobResponse:
    """Stop a scrap client job that is pending or in progress."""
    scrap_job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
    if scrap_job is None:
        raise NotFoundException(detail="Scrap client job not found")
    if scrap_job.status not in (
        ScrapClientJobStatus.PENDING.value,
        ScrapClientJobStatus.IN_PROGRESS.value,
    ):
        raise BadRequestException(
            detail="Only jobs with status pending or in_progress can be stopped"
        )

    updated = await update_scrap_client_job_status(
        db, scrap_client_job_id, ScrapClientJobStatus.STOPPED
    )
    response = ScrapClientJobResponse.model_validate(updated)
    await broadcast_scrap_client_status(
        response.model_dump(), ScrapClientJobStatus.STOPPED.value
    )
    return response


async def resume_scrap_client_job(
    db: AsyncSession, scrap_client_job_id: int
) -> ScrapClientJobResponse:
    """Resume a stopped scrap client job."""
    scrap_job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
    if scrap_job is None:
        raise NotFoundException(detail="Scrap client job not found")
    if scrap_job.status != ScrapClientJobStatus.STOPPED.value:
        raise BadRequestException(
            detail="Only jobs with status stopped can be resumed"
        )

    updated = await update_scrap_client_job_status(
        db, scrap_client_job_id, ScrapClientJobStatus.IN_PROGRESS
    )
    response = ScrapClientJobResponse.model_validate(updated)
    await broadcast_scrap_client_status(
        response.model_dump(), ScrapClientJobStatus.IN_PROGRESS.value
    )
    return response


async def list_scrap_client_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
) -> ScrapClientJobListResponse:
    """Return a paginated list of scrap client jobs."""
    items, total = await get_scrap_client_jobs(
        db, skip=skip, limit=limit, status=status,
    )
    return ScrapClientJobListResponse(
        items=[ScrapClientJobResponse.model_validate(item) for item in items],
        total=total,
    )


async def get_scrap_client_job(
    db: AsyncSession, scrap_client_job_id: int
) -> ScrapClientJobResponse:
    """Return a single scrap client job or raise NotFoundException."""
    scrap_job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
    if scrap_job is None:
        raise NotFoundException(detail="Scrap client job not found")
    return ScrapClientJobResponse.model_validate(scrap_job)


async def get_scrap_client_job_logs(
    db: AsyncSession,
    scrap_client_job_id: int,
) -> ScrapClientLogListResponse:
    """Return all logs for a scrap client job."""
    scrap_job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
    if scrap_job is None:
        raise NotFoundException(detail="Scrap client job not found")
    logs = await get_scrap_client_job_logs_by_job_id(db, scrap_client_job_id)
    return ScrapClientLogListResponse(
        items=[ScrapClientLogResponse.model_validate(log) for log in logs]
    )


async def get_scrap_client_status(
    db: AsyncSession,
) -> ScrapClientStatusResponse:
    """Return status summary: pending, processing, completed, failed."""
    from app.modules.scrap_client.models import ScrapClientJob

    result = await db.execute(
        select(ScrapClientJob.status, func.count(ScrapClientJob.id))
        .group_by(ScrapClientJob.status)
    )
    rows = result.all()
    counts = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
    for status, cnt in rows:
        if status in ("pending",):
            counts["pending"] += cnt
        elif status in ("in_progress",):
            counts["processing"] += cnt
        elif status in ("completed",):
            counts["completed"] += cnt
        else:
            counts["failed"] += cnt
    return ScrapClientStatusResponse(**counts)
