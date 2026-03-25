"""Scrap client job business logic and orchestration."""

import asyncio
import logging
import traceback
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
from app.modules.scrap_client.models import ScrapClientJobStatus
from app.modules.scrap_client.schemas import (
    ScrapClientJobListResponse,
    ScrapClientJobResponse,
    ScrapClientLogListResponse,
    ScrapClientLogResponse,
    ScrapClientStartRequest,
    ScrapClientStatusResponse,
    TestScrapClientRequest,
    TestScrapClientSiteRequest,
)
from app.modules.scrap_client.services.email_extractor import extract_emails_from_html
from app.modules.scrap_client.services.email_pattern_generator import (
    generate_extended_email_patterns,
    generate_recruiter_email_patterns,
)
from app.modules.scrap_client.services.email_validator import (
    validate_scraped_emails_for_storage,
)
from app.modules.scrap_client.services.url_utils import extract_root_domain
from app.modules.scrap_client.services.website_crawler import WebsiteCrawler
from app.modules.scrap_client.services.website_discovery import (
    DiscoveryResult,
    discover_company_info,
    get_domain_candidates_for_guessing,
    verify_domain_and_get_website,
)
from app.modules.websocket.service import (
    broadcast_scrap_client_log,
    broadcast_scrap_client_status,
)

CONCURRENCY_LIMIT = 5
logger = logging.getLogger(__name__)


async def _create_log_and_broadcast(
    scrap_client_job_id: int,
    action: str,
    progress: int = 0,
    status: str = "in_progress",
    details: str | None = None,
    meta_data: dict | None = None,
) -> None:
    """Create scrap client log and broadcast via WebSocket. Log is persisted even if broadcast fails."""
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
        except Exception:
            await log_db.rollback()
            raise
        try:
            await broadcast_scrap_client_log(
                ScrapClientLogResponse.model_validate(log).model_dump()
            )
        except Exception as e:
            logger.warning("Broadcast scrap client log failed (log persisted): %s", e)


async def _process_single_client(
    client_id: int,
    client_name: str,
    website_override: str | None = None,
    client_link: str | None = None,
    scrap_client_job_id: int | None = None,
) -> tuple[bool, list[str], str | None]:
    """
    Process a single client: discover website and contact info, crawl, extract/generate emails, validate.
    Uses multi-strategy discovery with Grok AI as primary, followed by direct guess and DuckDuckGo.
    All persisted emails pass validate_scraped_emails_for_storage (format, disposable, MX, SMTP).
    Returns (success, validated_emails, official_website).
    """

    async def log_step(
        action: str,
        details: str | None = None,
        meta_data: dict | None = None,
        status: str = "in_progress",
    ) -> None:
        """Broadcast a log step for this client processing."""
        if scrap_client_job_id is not None:
            await _create_log_and_broadcast(
                scrap_client_job_id,
                action,
                progress=0,
                status=status,
                details=details,
                meta_data=meta_data,
            )

    await log_step(
        "client_processing_start",
        f"Starting processing for '{client_name}'",
        {"client_id": client_id, "client_name": client_name},
    )

    all_emails: set[str] = set()
    website: str | None = website_override
    discovery_source = "override"

    if website:
        await log_step(
            "using_website_override",
            f"Using provided URL: {website}",
            {"website": website},
        )
    else:
        await log_step(
            "discovery_start",
            f"Discovering website and contact info for '{client_name}'",
            {"client_name": client_name, "client_link": client_link},
        )
        discovery: DiscoveryResult = await discover_company_info(
            client_name, client_link=client_link, log_cb=log_step
        )
        website = discovery.website
        all_emails.update(discovery.emails)
        discovery_source = discovery.source

        await log_step(
            "discovery_complete",
            f"Discovery done via {discovery.source}: website={website or 'none'}, "
            f"{len(discovery.emails)} emails from AI",
            {
                "website": website,
                "emails": discovery.emails,
                "phones": discovery.phones,
                "source": discovery.source,
            },
        )

    root_domain: str | None = extract_root_domain(website) if website else None

    if website and root_domain:
        await log_step(
            "crawl_start",
            f"Crawling website for emails: {website}",
            {"website": website, "root_domain": root_domain},
        )
        try:
            crawler = WebsiteCrawler(max_pages=15)
            pages_data = await crawler.crawl(website)
            crawled_count = len(pages_data)

            await log_step(
                "crawl_complete",
                f"Crawled {crawled_count} pages from {website}",
                {"website": website, "pages_crawled": crawled_count},
            )

            crawled_emails_count = 0
            for _, html in pages_data:
                extracted = extract_emails_from_html(html)
                for e in extracted:
                    if root_domain in e.split("@")[-1].lower():
                        all_emails.add(e)
                        crawled_emails_count += 1

            if crawled_emails_count > 0:
                await log_step(
                    "crawl_emails_found",
                    f"Extracted {crawled_emails_count} domain-matching emails from crawled pages",
                    {"crawled_emails": crawled_emails_count, "total_emails": len(all_emails)},
                )
        except Exception as e:
            logger.warning("Crawling failed for %s: %s", website, e)
            await log_step(
                "crawl_error",
                f"Crawling failed: {e}",
                {"website": website, "error": str(e)},
                status="error",
            )

    if not all_emails and root_domain:
        recruiter_patterns = generate_recruiter_email_patterns(root_domain)
        extended_patterns = generate_extended_email_patterns(root_domain)
        combined = list(dict.fromkeys(recruiter_patterns + extended_patterns))
        all_emails.update(combined)

        await log_step(
            "email_patterns_generated",
            f"Generated {len(combined)} email patterns for {root_domain}",
            {"domain": root_domain, "pattern_count": len(combined)},
        )

    if all_emails:
        candidate_list = list(all_emails)
        await log_step(
            "email_validation_start",
            f"Validating {len(candidate_list)} email candidates (format, disposable, MX, SMTP)",
            {"candidate_count": len(candidate_list)},
        )

        validated = await validate_scraped_emails_for_storage(candidate_list)

        await log_step(
            "email_validation_complete",
            f"Validated {len(validated)} of {len(candidate_list)} emails",
            {"validated": validated, "total_candidates": len(candidate_list)},
        )

        if validated:
            await log_step(
                "client_processing_complete",
                f"Success: '{client_name}' - {len(validated)} valid emails via {discovery_source}",
                {"emails": validated, "website": website, "source": discovery_source},
                status="completed",
            )
            return True, validated, website

    if not website:
        await log_step(
            "domain_guess_fallback_start",
            f"No website found, trying domain guessing for '{client_name}'",
            {"client_name": client_name},
        )
        domain_candidates = get_domain_candidates_for_guessing(client_name)
        first_verified_website: str | None = None

        for domain in domain_candidates:
            verified_website = await verify_domain_and_get_website(domain)
            if verified_website:
                if first_verified_website is None:
                    first_verified_website = verified_website
                root = extract_root_domain(verified_website)
                if root:
                    extended = generate_extended_email_patterns(root)
                    validated = await validate_scraped_emails_for_storage(extended)
                    if validated:
                        await log_step(
                            "domain_guess_success",
                            f"Found {len(validated)} emails via domain guess: {domain}",
                            {"domain": domain, "emails": validated, "website": verified_website},
                            status="completed",
                        )
                        return True, validated, verified_website

        website = website or first_verified_website
        await log_step(
            "domain_guess_complete",
            f"Domain guessing finished, no valid emails found",
            {"website": website},
            status="error",
        )

    await log_step(
        "client_processing_failed",
        f"No valid emails found for '{client_name}'",
        {"website": website, "source": discovery_source},
        status="error",
    )
    return False, [], website


async def _run_client_site_scraper(
    scrap_client_job_id: int,
    client_site_id: int,
    is_test_mode: bool = False,
) -> None:
    """
    Background worker that scrapes client data from a client site URL.
    Saves extracted clients to CareerClient, using website discovery when email not found.
    """
    async def is_stopped() -> bool:
        """Check if the job has been stopped by the user."""
        async with async_session() as s:
            j = await get_scrap_client_job_by_id(s, scrap_client_job_id)
            return j is not None and j.status == ScrapClientJobStatus.STOPPED.value

    from app.modules.client_site.crud import get_client_site_by_id
    from app.modules.scrap_client.services.client_data_scraper import scrape_clients_from_url

    async with async_session() as db:
        try:
            await _create_log_and_broadcast(
                scrap_client_job_id,
                "job_started",
                progress=0,
                status="in_progress",
                details="Background client site scraper started",
                meta_data={"client_site_id": client_site_id},
            )
            client_site = await get_client_site_by_id(db, client_site_id)
            if client_site is None:
                await update_scrap_client_job_status(
                    db, scrap_client_job_id, ScrapClientJobStatus.ERROR
                )
                await db.commit()
                await _create_log_and_broadcast(
                    scrap_client_job_id,
                    "job_error",
                    status="error",
                    details="Client site not found",
                )
                return
            await _create_log_and_broadcast(
                scrap_client_job_id,
                "scrap_client_site_start",
                progress=0,
                status="in_progress",
                details=f"Scraping clients from {client_site.name}",
                meta_data={"client_site_id": client_site_id, "url": client_site.url},
            )
            if await is_stopped():
                return
            saved_count = await scrape_clients_from_url(
                db,
                client_site.url,
                use_discovery_when_no_email=True,
                max_pages=5,
            )
            if await is_stopped():
                return
            await update_scrap_client_job_status(
                db, scrap_client_job_id, ScrapClientJobStatus.COMPLETED
            )
            await update_scrap_client_job_meta_data(
                db, scrap_client_job_id, {"total": saved_count, "clients_saved": saved_count}
            )
            await db.commit()
            updated = await get_scrap_client_job_by_id(db, scrap_client_job_id)
            if updated:
                await broadcast_scrap_client_status(
                    ScrapClientJobResponse.model_validate(updated).model_dump(),
                    ScrapClientJobStatus.COMPLETED.value,
                )
            await _create_log_and_broadcast(
                scrap_client_job_id,
                "job_completed",
                progress=100,
                status="completed",
                details=f"Scraped {saved_count} clients from {client_site.name}",
                meta_data={
                    "clients_saved": saved_count,
                    "total_clients": saved_count,
                },
            )
        except Exception as e:
            logger.exception("Client site scrap failed: %s", e)
            try:
                await _create_log_and_broadcast(
                    scrap_client_job_id,
                    "job_error",
                    status="error",
                    details=str(e),
                    meta_data={
                        "clients_saved": 0,
                        "total_clients": 0,
                        "error_type": type(e).__name__,
                    },
                )
            except Exception:
                pass
            async with async_session() as edb:
                await update_scrap_client_job_status(
                    edb, scrap_client_job_id, ScrapClientJobStatus.ERROR
                )
                await edb.commit()


async def _run_client_email_scraper(
    scrap_client_job_id: int,
    client_ids: list[int] | None,
    only_clients_without_emails: bool,
    url: str | None = None,
    is_test_mode: bool = False,
) -> None:
    """
    Background worker that processes clients for email scraping.
    Persisted emails are validated only through validate_scraped_emails_for_storage
    in _process_single_client (format, disposable domains, MX, SMTP).
    """
    try:
        await _create_log_and_broadcast(
            scrap_client_job_id,
            "job_started",
            progress=0,
            status="in_progress",
            details="Background scraper task started",
            meta_data={
                "client_ids": client_ids,
                "only_without_emails": only_clients_without_emails,
                "is_test_mode": is_test_mode,
            },
        )
    except Exception as e:
        logger.warning("Could not create job_started log: %s", e)

    async def is_stopped() -> bool:
        """Check if the job has been stopped by the user."""
        async with async_session() as s:
            j = await get_scrap_client_job_by_id(s, scrap_client_job_id)
            return j is not None and j.status == ScrapClientJobStatus.STOPPED.value

    async with async_session() as db:
        try:
            job = await get_scrap_client_job_by_id(db, scrap_client_job_id)
            if job is None:
                logger.warning("Job %s not found, exiting", scrap_client_job_id)
                return

            meta = job.meta_data or {}
            job_url = url or meta.get("url")
            if job_url:
                from app.modules.scrap_client.services.url_utils import normalize_url
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
                clients = await get_career_clients_without_emails(db, limit=1000)
            elif job_url:
                from types import SimpleNamespace
                clients = [SimpleNamespace(id=0, name="url_crawl")]
            else:
                await update_scrap_client_job_status(
                    db, scrap_client_job_id, ScrapClientJobStatus.ERROR
                )
                await db.commit()
                await _create_log_and_broadcast(
                    scrap_client_job_id,
                    "job_error",
                    status="error",
                    details="No clients or URL provided",
                )
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
                await _create_log_and_broadcast(
                    scrap_client_job_id,
                    "job_completed",
                    progress=100,
                    status="completed",
                    details="No clients to process",
                    meta_data={"total": 0},
                )
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

            await _create_log_and_broadcast(
                scrap_client_job_id,
                "job_processing",
                progress=0,
                status="in_progress",
                details=f"Processing {total} clients",
                meta_data={"total": total},
            )

            sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
            completed = 0
            failed = 0

            async def process_one(client, index: int) -> None:
                """Process a single client within the semaphore-bounded concurrency pool."""
                nonlocal completed, failed
                if await is_stopped():
                    return
                async with sem:
                    if await is_stopped():
                        return

                    await _create_log_and_broadcast(
                        scrap_client_job_id,
                        f"client_queue_{client.name}",
                        progress=int(100 * (completed + failed) / total),
                        status="in_progress",
                        details=f"Processing client {index + 1}/{total}: {client.name}",
                        meta_data={"client_id": client.id, "index": index},
                    )

                    success, emails, website = await _process_single_client(
                        client.id,
                        client.name or "",
                        website_override=website_override,
                        client_link=getattr(client, "link", None),
                        scrap_client_job_id=scrap_client_job_id,
                    )

                    async with async_session() as session:
                        if await is_stopped():
                            return
                        if not is_test_mode and client.id > 0:
                            fresh = await get_career_client_by_id(
                                session, client.id
                            )
                            if fresh is None:
                                failed += 1
                            else:
                                base_meta: dict = {}
                                if isinstance(fresh.meta_data, dict):
                                    base_meta = dict(fresh.meta_data)
                                if success and emails:
                                    base_meta["email_found_error"] = False
                                    await update_career_client(
                                        session,
                                        client.id,
                                        {
                                            "emails": emails,
                                            "official_website": website,
                                            "meta_data": base_meta,
                                        },
                                    )
                                    completed += 1
                                else:
                                    base_meta["email_found_error"] = True
                                    payload: dict = {
                                        "meta_data": base_meta,
                                    }
                                    if website:
                                        payload["official_website"] = website
                                    await update_career_client(
                                        session, client.id, payload
                                    )
                                    failed += 1
                            await session.commit()
                        else:
                            if success and emails:
                                completed += 1
                            else:
                                failed += 1

                    job_meta = {
                        "total": total,
                        "pending": total - completed - failed,
                        "processing": 0,
                        "completed": completed,
                        "failed": failed,
                    }
                    async with async_session() as mdb:
                        await update_scrap_client_job_meta_data(
                            mdb, scrap_client_job_id, job_meta
                        )
                        await mdb.commit()

                    progress = int(100 * (completed + failed) / total)
                    await _create_log_and_broadcast(
                        scrap_client_job_id,
                        f"processed_{client.name}",
                        progress=progress,
                        status="completed" if success else "error",
                        details=f"Client '{client.name}': {len(emails)} emails found",
                        meta_data={
                            "client_id": client.id,
                            "emails": emails,
                            "website": website,
                            "success": success,
                        },
                    )

            for i, c in enumerate(clients):
                logger.info(
                    "Job %s: processing client %d/%d (id=%s, name=%s)",
                    scrap_client_job_id, i + 1, total,
                    c.id, getattr(c, "name", "unknown"),
                )
                await process_one(c, i)

            logger.info("Job %s: all clients processed, finalizing", scrap_client_job_id)

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

            await _create_log_and_broadcast(
                scrap_client_job_id,
                "job_completed",
                progress=100,
                status="completed",
                details=f"Job finished: {completed} succeeded, {failed} failed out of {total}",
                meta_data={"completed": completed, "failed": failed, "total": total},
            )

        except Exception as e:
            logger.exception("Scrap client job %s failed: %s", scrap_client_job_id, e)
            try:
                await _create_log_and_broadcast(
                    scrap_client_job_id,
                    "job_error",
                    progress=0,
                    status="error",
                    details=str(e),
                    meta_data={"error_type": type(e).__name__, "traceback": traceback.format_exc()},
                )
            except Exception as log_err:
                logger.warning("Could not create job_error log: %s", log_err)
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
    Create and start a new scrap client job for email fetching.
    Requires client_ids or only_clients_without_emails.
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


async def _run_client_url_scraper(
    scrap_client_job_id: int,
    url: str,
) -> None:
    """
    Background worker that scrapes client data from an arbitrary URL.
    Saves extracted clients to CareerClient, using website discovery when email not found.
    """
    async def is_stopped() -> bool:
        async with async_session() as s:
            j = await get_scrap_client_job_by_id(s, scrap_client_job_id)
            return j is not None and j.status == ScrapClientJobStatus.STOPPED.value

    from app.modules.scrap_client.services.client_data_scraper import scrape_clients_from_url
    from app.modules.scrap_client.services.url_utils import normalize_url

    normalized_url = normalize_url(url)
    if not normalized_url:
        async with async_session() as edb:
            await update_scrap_client_job_status(
                edb, scrap_client_job_id, ScrapClientJobStatus.ERROR
            )
            await edb.commit()
        await _create_log_and_broadcast(
            scrap_client_job_id,
            "job_error",
            status="error",
            details="Invalid URL provided",
            meta_data={"clients_saved": 0, "total_clients": 0, "url": url},
        )
        return

    async with async_session() as db:
        try:
            await _create_log_and_broadcast(
                scrap_client_job_id,
                "job_started",
                progress=0,
                status="in_progress",
                details="Background URL scraper started",
                meta_data={"url": normalized_url},
            )
            await _create_log_and_broadcast(
                scrap_client_job_id,
                "scrap_client_url_start",
                progress=0,
                status="in_progress",
                details=f"Scraping clients from {normalized_url}",
                meta_data={"url": normalized_url},
            )
            if await is_stopped():
                return
            saved_count = await scrape_clients_from_url(
                db,
                normalized_url,
                use_discovery_when_no_email=True,
                max_pages=5,
            )
            if await is_stopped():
                return
            await update_scrap_client_job_status(
                db, scrap_client_job_id, ScrapClientJobStatus.COMPLETED
            )
            await update_scrap_client_job_meta_data(
                db, scrap_client_job_id,
                {"total": saved_count, "clients_saved": saved_count, "url": normalized_url},
            )
            await db.commit()
            updated = await get_scrap_client_job_by_id(db, scrap_client_job_id)
            if updated:
                await broadcast_scrap_client_status(
                    ScrapClientJobResponse.model_validate(updated).model_dump(),
                    ScrapClientJobStatus.COMPLETED.value,
                )
            await _create_log_and_broadcast(
                scrap_client_job_id,
                "job_completed",
                progress=100,
                status="completed",
                details=f"Scraped {saved_count} clients from {normalized_url}",
                meta_data={
                    "clients_saved": saved_count,
                    "total_clients": saved_count,
                    "url": normalized_url,
                },
            )
        except Exception as e:
            logger.exception("Client URL scrap failed: %s", e)
            try:
                await _create_log_and_broadcast(
                    scrap_client_job_id,
                    "job_error",
                    status="error",
                    details=str(e),
                    meta_data={
                        "clients_saved": 0,
                        "total_clients": 0,
                        "url": normalized_url,
                        "error_type": type(e).__name__,
                    },
                )
            except Exception:
                pass
            async with async_session() as edb:
                await update_scrap_client_job_status(
                    edb, scrap_client_job_id, ScrapClientJobStatus.ERROR
                )
                await edb.commit()


async def start_scrap_client_from_site(
    db: AsyncSession,
    client_site_id: int,
) -> ScrapClientJobResponse:
    """
    Create and start a scrap client job that scrapes client data from a client site URL.
    Extracts companies from the site and saves to CareerClient, using discovery when email not found.
    """
    active = await get_active_scrap_client_jobs(db)
    if active:
        raise BadRequestException(
            detail="An active scrap client job already exists"
        )

    from app.modules.client_site.crud import get_client_site_by_id

    client_site = await get_client_site_by_id(db, client_site_id)
    if client_site is None:
        raise NotFoundException(detail="Client site not found")

    meta_data = {"client_site_id": client_site_id}
    scrap_job = await create_scrap_client_job(
        db,
        {
            "name": f"client_site_{client_site.name}_{int(datetime.now(timezone.utc).timestamp())}",
            "status": ScrapClientJobStatus.PENDING.value,
            "meta_data": meta_data,
        },
    )
    response = ScrapClientJobResponse.model_validate(scrap_job)
    await broadcast_scrap_client_status(
        response.model_dump(), ScrapClientJobStatus.PENDING.value
    )
    return response


async def start_scrap_client_from_url(
    db: AsyncSession,
    url: str,
) -> ScrapClientJobResponse:
    """
    Create and start a scrap client job that scrapes client data from an arbitrary URL.
    Extracts companies from the page and saves to CareerClient.
    """
    from app.modules.scrap_client.services.url_utils import normalize_url

    active = await get_active_scrap_client_jobs(db)
    if active:
        raise BadRequestException(
            detail="An active scrap client job already exists"
        )

    normalized_url = normalize_url(url)
    if not normalized_url:
        raise BadRequestException(detail="Invalid URL provided")

    meta_data = {"url": normalized_url}
    scrap_job = await create_scrap_client_job(
        db,
        {
            "name": f"client_url_{int(datetime.now(timezone.utc).timestamp())}",
            "status": ScrapClientJobStatus.PENDING.value,
            "meta_data": meta_data,
        },
    )
    response = ScrapClientJobResponse.model_validate(scrap_job)
    await broadcast_scrap_client_status(
        response.model_dump(), ScrapClientJobStatus.PENDING.value
    )
    return response


async def start_test_scrap_client_from_site(
    db: AsyncSession,
    request: TestScrapClientSiteRequest,
) -> ScrapClientJobResponse:
    """Create and start a test scrap client job from a client site. Does not skip saving."""
    from app.modules.client_site.crud import get_client_site_by_id

    client_site = await get_client_site_by_id(db, request.client_site_id)
    if client_site is None:
        raise NotFoundException(detail="Client site not found")

    meta_data = {
        "client_site_id": request.client_site_id,
        "is_test_mode": True,
    }
    scrap_job = await create_scrap_client_job(
        db,
        {
            "name": f"test_client_site_{client_site.name}_{int(datetime.now(timezone.utc).timestamp())}",
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
