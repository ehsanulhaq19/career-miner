import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.database import async_session
from app.modules.job_site.crud import get_active_job_sites_for_scraping, update_last_scrapped
from app.modules.scrap_job.crud import (
    create_scrap_job,
    get_active_scrap_jobs_for_site,
    get_timed_out_scrap_jobs,
    update_scrap_job_status,
)
from app.modules.scraper.service import ScraperService

logger = logging.getLogger(__name__)
settings = get_settings()
scheduler = AsyncIOScheduler()


async def scraping_cron_job() -> None:
    """Main cron job that runs every minute to process scraping tasks."""
    async with async_session() as db:
        try:
            await _terminate_timed_out_jobs(db)
            await _process_eligible_sites(db)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Scraping cron job encountered an error")


async def _terminate_timed_out_jobs(db) -> None:
    """Find and terminate scrap jobs that exceeded the maximum execution time."""
    timed_out_jobs = await get_timed_out_scrap_jobs(
        db, settings.MAX_SCRAP_EXECUTION_TIME_MINUTES
    )
    for job in timed_out_jobs:
        logger.warning("Terminating timed-out scrap job %d", job.id)
        await update_scrap_job_status(db, job.id, "terminated")
        await update_last_scrapped(db, job.job_site_id, datetime.now(timezone.utc))


async def _process_eligible_sites(db) -> None:
    """Scrape all eligible job sites that have no active scrap jobs."""
    job_sites = await get_active_job_sites_for_scraping(db)
    scraper = ScraperService()
    for job_site in job_sites:
        active_jobs = await get_active_scrap_jobs_for_site(db, job_site.id)
        if active_jobs:
            logger.info(
                "Skipping site %s — active scrap job already exists",
                job_site.name,
            )
            continue

        scrap_job = await create_scrap_job(
            db,
            {
                "name": f"job_{int(datetime.now(timezone.utc).timestamp())}",
                "job_site_id": job_site.id,
                "status": "pending",
            },
        )
        logger.info(
            "Created scrap job %d for site %s",
            scrap_job.id,
            job_site.name,
        )
        await scraper.scrape_job_site(db, job_site, scrap_job)
        await update_last_scrapped(db, job_site.id, datetime.now(timezone.utc))


def start_scheduler() -> None:
    """Start the APScheduler with the scraping cron job running every minute."""
    if not scheduler.running:
        scheduler.add_job(
            scraping_cron_job,
            "interval",
            minutes=1,
            id="scraping_cron",
            replace_existing=True,
        )
        scheduler.start()


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
