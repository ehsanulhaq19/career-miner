import asyncio
import json
import logging
import re
import uuid
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.career_client.crud import get_or_create_career_client
from app.modules.career_job.crud import (
    check_job_exist,
    create_career_job,
)
from app.modules.llm.service import LLMFactory
from app.modules.job_site.models import JobSite
from app.modules.scrap_client.crud import create_scrap_client_file_link
from app.modules.scrap_job.crud import (
    create_scrap_job_file_link,
    get_scrap_job_by_id,
    update_scrap_job_meta_data,
    update_scrap_job_status,
)
from app.modules.scrap_job.models import ScrapJob, ScrapJobStatus

# STOPPED (user) or TERMINATED (e.g. timeout): runner exits without marking COMPLETED.
_SCRAP_JOB_HALTED_STATUSES: frozenset[str] = frozenset(
    {ScrapJobStatus.STOPPED.value, ScrapJobStatus.TERMINATED.value}
)
from app.modules.scrap_job.schemas import ScrapJobResponse
from app.modules.scraper.prompts import (
    JOB_PARSER_SYSTEM_PROMPT,
    JOB_PARSER_USER_PROMPT_TEMPLATE,
)
from app.modules.scrap_job.service import create_log_and_broadcast
from app.modules.scraper.crud import create_scrapper
from app.modules.scraper.scrape_core import ScrapeCore
from app.modules.websocket.service import broadcast_scrap_job_status

logger = logging.getLogger(__name__)


class ScraperHtmlStorage:
    """Writes scraped HTML to configured storage and links Scrapper rows to jobs."""

    @staticmethod
    async def persist_for_scrap_job(
        db: AsyncSession,
        scrap_job_id: int,
        html: str,
        source_url: str,
    ) -> None:
        """
        Save HTML under SCRAP_HTML_OUTPUT_FOLDER/scrap_job_{id}/, create Scrapper,
        and link via ScrapJobFile.
        """
        settings = get_settings()
        base = Path(settings.SCRAP_HTML_OUTPUT_FOLDER).resolve()
        base.mkdir(parents=True, exist_ok=True)
        sub = base / f"scrap_job_{scrap_job_id}"
        sub.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.html"
        full_path = sub / filename
        full_path.write_text(html, encoding="utf-8")
        relative = str(full_path.relative_to(base))
        scrapper = await create_scrapper(db, relative, source_url)
        await create_scrap_job_file_link(db, scrap_job_id, scrapper.id)

    @staticmethod
    async def persist_for_scrap_client_job(
        db: AsyncSession,
        scrap_client_job_id: int,
        html: str,
        source_url: str,
    ) -> None:
        """
        Save HTML under SCRAP_HTML_OUTPUT_FOLDER/scrap_client_{id}/, create Scrapper,
        and link via ScrapClientFile.
        """
        settings = get_settings()
        base = Path(settings.SCRAP_HTML_OUTPUT_FOLDER).resolve()
        base.mkdir(parents=True, exist_ok=True)
        sub = base / f"scrap_client_{scrap_client_job_id}"
        sub.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.html"
        full_path = sub / filename
        full_path.write_text(html, encoding="utf-8")
        relative = str(full_path.relative_to(base))
        scrapper = await create_scrapper(db, relative, source_url)
        await create_scrap_client_file_link(db, scrap_client_job_id, scrapper.id)

def _extract_json_array(text: str) -> str | None:
    """Extract JSON array from LLM response, handling markdown code blocks."""
    text = text.strip()
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    depth = 0
    start = text.find("[")
    if start < 0:
        return None
    for i, c in enumerate(text[start:], start):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


JOB_LISTING_KEYWORDS = [
    "job",
    "listing",
    "vacancy",
    "position",
    "career",
    "opening",
    "opportunity",
    "posting",
    "role",
]


class ScraperService:
    """Handles fetching, parsing, and persisting scraped job listings from external sites."""

    def __init__(self) -> None:
        self._core = ScrapeCore()

    async def scrape_job_site(
        self,
        db: AsyncSession,
        job_site: JobSite,
        scrap_job: ScrapJob,
        categories: list[str] | None = None,
        max_pages_per_scrap: int | None = None,
        process_with_llm: bool = True,
        load_more_on_scroll: bool = False,
        max_scroll: int = 10,
        depth_levels: int = 0,
    ) -> None:
        """
        Execute scraping for a single job site and save found jobs.
        Accepts optional overrides for categories, max pages, LLM processing,
        scroll-based loading, and depth_levels for multi-level link following.
        When depth_levels is set, follows links up to that depth (0=parent only).
        Deduplicates jobs by title and link, keeping the latest parsed data.
        """
        refreshed = await get_scrap_job_by_id(db, scrap_job.id)
        if refreshed and refreshed.status in _SCRAP_JOB_HALTED_STATUSES:
            return
        updated = await update_scrap_job_status(
            db, scrap_job.id, ScrapJobStatus.IN_PROGRESS
        )
        if updated:
            await db.commit()
            await broadcast_scrap_job_status(
                ScrapJobResponse.model_validate(updated).model_dump(),
                ScrapJobStatus.IN_PROGRESS.value,
            )
        try:
            settings = get_settings()
            effective_categories = categories if categories is not None else (job_site.categories or [])
            effective_max_pages = max_pages_per_scrap if max_pages_per_scrap is not None else settings.MAX_PAGES_PER_SCRAP
            visited: set[str] = set()
            queued: set[str] = set()
            all_jobs_by_key: dict[tuple[str, str], dict] = {}
            base_domain = urlparse(job_site.url).netloc
            to_visit: deque[tuple[str, int]] = deque([(job_site.url, 0)])
            queued.add(self._core.normalize_url(job_site.url))
            saved_count = 0
            pages_scraped = 0
            total_jobs_scraped_from_html = 0

            await create_log_and_broadcast(
                db,
                scrap_job.id,
                "scrap_started",
                progress=0,
                status="in_progress",
                details=f"Starting scrape for {job_site.name}",
                meta_data={"job_site_id": job_site.id, "job_site_name": job_site.name},
            )

            client_kwargs: dict = {
                "timeout": 30,
                "follow_redirects": True,
                "headers": self._core.browser_headers(job_site.url),
            }
            if settings.SCRAP_HTTP_PROXY:
                client_kwargs["proxy"] = settings.SCRAP_HTTP_PROXY
            async with httpx.AsyncClient(**client_kwargs) as client:
                await self._core.warm_up_session(client, job_site.url)
                while to_visit and pages_scraped < effective_max_pages:
                    refreshed = await get_scrap_job_by_id(db, scrap_job.id)
                    if refreshed and refreshed.status in _SCRAP_JOB_HALTED_STATUSES:
                        logger.info(
                            "Scrap job %d halted (status=%s)", scrap_job.id, refreshed.status
                        )
                        break

                    url, current_depth = to_visit.popleft()
                    url_normalized = self._core.normalize_url(url)
                    if url_normalized in visited:
                        continue
                    visited.add(url_normalized)

                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "fetch_page",
                        progress=pages_scraped,
                        status="in_progress",
                        details=f"Fetching page {pages_scraped + 1}",
                        meta_data={"url": url, "page_index": pages_scraped},
                    )
                    try:
                        if load_more_on_scroll:
                            html, final_url = await self._core.fetch_page_with_scroll(
                                url, max_scroll=max_scroll
                            )
                        elif self._core.is_anti_bot_site(url):
                            html, final_url = await self._core.fetch_page_playwright(url)
                        else:
                            html, final_url = await self._core.fetch_page(client, url)
                    except Exception as e:
                        logger.warning("Failed to fetch %s: %s", url, e)
                        await create_log_and_broadcast(
                            db,
                            scrap_job.id,
                            "fetch_page",
                            progress=pages_scraped,
                            status="error",
                            details=str(e),
                            meta_data={"url": url, "page_index": pages_scraped},
                        )
                        continue

                    try:
                        await ScraperHtmlStorage.persist_for_scrap_job(
                            db, scrap_job.id, html, final_url
                        )
                    except Exception as persist_exc:
                        logger.warning(
                            "Failed to persist scrap HTML for job %s: %s",
                            scrap_job.id,
                            persist_exc,
                        )

                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "fetch_page",
                        progress=pages_scraped + 1,
                        status="completed",
                        details=f"Fetched page {url}",
                        meta_data={"url": final_url, "page_index": pages_scraped},
                    )

                    if pages_scraped == 0:
                        base_domain = urlparse(final_url).netloc

                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "extract_jobs_from_html",
                        progress=pages_scraped,
                        status="in_progress",
                        details=f"Extracting jobs from page {pages_scraped + 1}",
                        meta_data={"url": final_url},
                    )
                    jobs = await self._extract_jobs_from_html(html, final_url)
                    total_jobs_scraped_from_html += len(jobs)
                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "extract_jobs_from_html",
                        progress=pages_scraped,
                        status="completed",
                        details=f"Extracted {len(jobs)} jobs from page",
                        meta_data={
                            "url": final_url,
                            "jobs_count": len(jobs),
                            "jobs": jobs,
                        },
                    )
                    jobs_validated = 0
                    validated_jobs: list[dict] = []
                    for job_data in jobs:
                        if not job_data.get("title"):
                            continue
                        if not self._job_matches_categories(
                            job_data, effective_categories
                        ):
                            continue
                        exists = await check_job_exist(
                            db,
                            title=job_data["title"],
                            job_site_id=job_site.id,
                            links=job_data.get("links", []),
                            created_by=scrap_job.created_by,
                        )
                        if exists:
                            continue
                        links_list = job_data.get("links") or []
                        primary_link = links_list[0] if links_list else final_url
                        norm_link = self._core.normalize_url(primary_link) if primary_link else ""
                        dedupe_key = (job_data["title"], norm_link)
                        all_jobs_by_key[dedupe_key] = job_data
                        validated_jobs.append(job_data)
                        jobs_validated += 1

                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "jobs_validation",
                        progress=pages_scraped,
                        status="completed",
                        details=f"Validated {len(jobs)} jobs, {jobs_validated} new",
                        meta_data={
                            "total_on_page": len(jobs),
                            "new_jobs": jobs_validated,
                            "total_collected": len(all_jobs_by_key),
                            "jobs": validated_jobs,
                        },
                    )

                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "extract_crawlable_links",
                        progress=pages_scraped,
                        status="in_progress",
                        details=f"Extracting links from page {pages_scraped + 1}",
                        meta_data={"url": final_url},
                    )
                    crawlable_links = self._extract_crawlable_links(html, final_url, base_domain)
                    next_depth = current_depth + 1
                    can_follow_links = depth_levels is None or next_depth <= depth_levels
                    for link in crawlable_links:
                        normalized = self._core.normalize_url(link)
                        if normalized not in visited and normalized not in queued and can_follow_links:
                            to_visit.append((link, next_depth))
                            queued.add(normalized)

                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "extract_crawlable_links",
                        progress=pages_scraped,
                        status="completed",
                        details=f"Found {len(crawlable_links)} crawlable links",
                        meta_data={"links_count": len(crawlable_links), "queue_size": len(to_visit), "depth": current_depth},
                    )

                    pages_scraped += 1
                    delay = self._core.random_delay(settings)
                    if delay > 0:
                        await asyncio.sleep(delay)

                refreshed = await get_scrap_job_by_id(db, scrap_job.id)
                if refreshed and refreshed.status in _SCRAP_JOB_HALTED_STATUSES:
                    logger.info(
                        "Scrap job %d halted (status=%s)", scrap_job.id, refreshed.status
                    )
                    return

                all_jobs = list(all_jobs_by_key.values())
                total_jobs = len(all_jobs)
                if process_with_llm and total_jobs > 0:
                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "fetch_job_details_via_llm",
                        progress=0,
                        status="in_progress",
                        details=f"Parsing {total_jobs} jobs via LLM",
                        meta_data={"total_jobs": total_jobs},
                    )

                    chunk_size = 5
                    total_chunks = (total_jobs + chunk_size - 1) // chunk_size if total_jobs else 0
                    jobs_created_in_phase = 0

                    async for job_data, parsed_data in self._fetch_job_details_via_llm(
                        all_jobs, db, scrap_job.id
                    ):
                        refreshed = await get_scrap_job_by_id(db, scrap_job.id)
                        if refreshed and refreshed.status in _SCRAP_JOB_HALTED_STATUSES:
                            logger.info(
                                "Scrap job %d halted (status=%s)",
                                scrap_job.id,
                                refreshed.status,
                            )
                            return

                        links = job_data.get("links") or []
                        primary_url = parsed_data.get("job_link") or (links[0] if links else None)
                        career_client = await get_or_create_career_client(
                            db,
                            name=parsed_data.get("company_name"),
                            link=parsed_data.get("company_link"),
                            location=parsed_data.get("location"),
                            emails=self._parse_emails(parsed_data.get("company_emails")),
                            detail=job_data.get("description"),
                            size=parsed_data.get("company_size"),
                            created_by=scrap_job.created_by,
                        )

                        if not career_client:
                            continue
                        
                        career_job_data = {
                            "title": job_data["title"],
                            "description": job_data.get("description"),
                            "url": primary_url,
                            "job_site_id": job_site.id,
                            "scrap_job_id": scrap_job.id,
                            "parsed_data": parsed_data,
                            "meta_data": {},
                            "created_by": scrap_job.created_by,
                        }
                        if career_client:
                            career_job_data["career_client_id"] = career_client.id
                        
                        exists = await check_job_exist(
                            db,
                            title=job_data["title"],
                            job_site_id=job_site.id,
                            career_client_id=career_client.id,
                            created_by=scrap_job.created_by,
                        )
                        if exists:
                            continue

                        await create_career_job(db, career_job_data)
                        await db.commit()
                        saved_count += 1
                        jobs_created_in_phase += 1

                        await create_log_and_broadcast(
                            db,
                            scrap_job.id,
                            "jobs_creation",
                            progress=saved_count,
                            status="completed",
                            details=f"Created job: {job_data.get('title', '')[:50]}",
                            meta_data={
                                "job_title": job_data.get("title"),
                                "total_created": saved_count,
                            },
                        )

                        if jobs_created_in_phase % chunk_size == 0 or jobs_created_in_phase == total_jobs:
                            await create_log_and_broadcast(
                                db,
                                scrap_job.id,
                                "fetch_job_details_via_llm",
                                progress=min(
                                    (jobs_created_in_phase // chunk_size + 1) * 100 // max(total_chunks, 1),
                                    100,
                                ),
                                status="in_progress",
                                details=f"Processed {jobs_created_in_phase}/{total_jobs} jobs",
                                meta_data={
                                    "processed": jobs_created_in_phase,
                                    "total_jobs": total_jobs,
                                    "chunk_size": chunk_size,
                                },
                            )

                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "fetch_job_details_via_llm",
                        progress=100,
                        status="completed",
                        details=f"Parsed and processed {total_jobs} jobs",
                        meta_data={"total_jobs": total_jobs, "jobs_saved": saved_count},
                    )
                else:
                    await create_log_and_broadcast(
                        db,
                        scrap_job.id,
                        "scrap_completed",
                        progress=100,
                        status="completed",
                        details=f"Collected {total_jobs} jobs (LLM processing skipped)",
                        meta_data={"total_jobs": total_jobs, "jobs_saved": 0},
                    )
                completion_meta = {
                    "total_jobs_scraped_from_html": total_jobs_scraped_from_html,
                    "total_jobs_validated": len(all_jobs_by_key),
                    "total_jobs_created": saved_count,
                }
                await update_scrap_job_meta_data(db, scrap_job.id, completion_meta)

            logger.info(
                "Scraping completed for site %s — %d pages crawled, %d jobs saved",
                job_site.name,
                pages_scraped,
                saved_count,
            )
            refreshed = await get_scrap_job_by_id(db, scrap_job.id)
            if refreshed and refreshed.status not in _SCRAP_JOB_HALTED_STATUSES:
                updated = await update_scrap_job_status(
                    db, scrap_job.id, ScrapJobStatus.COMPLETED
                )
                if updated:
                    await db.commit()
                    await broadcast_scrap_job_status(
                        ScrapJobResponse.model_validate(updated).model_dump(),
                        ScrapJobStatus.COMPLETED.value,
                    )
        except Exception as exc:
            logger.exception("Scraping failed for site %s", job_site.name)
            try:
                await create_log_and_broadcast(
                    db,
                    scrap_job.id,
                    "scrap_failed",
                    progress=0,
                    status="error",
                    details=str(exc),
                    meta_data={"job_site_name": job_site.name},
                )
            except Exception:
                pass
            try:
                completion_meta = {
                    "total_jobs_scraped_from_html": total_jobs_scraped_from_html,
                    "total_jobs_validated": len(all_jobs_by_key),
                    "total_jobs_created": saved_count,
                }
                await update_scrap_job_meta_data(db, scrap_job.id, completion_meta)
                await db.commit()
            except Exception:
                pass
            refreshed = await get_scrap_job_by_id(db, scrap_job.id)
            if refreshed and refreshed.status not in _SCRAP_JOB_HALTED_STATUSES:
                updated = await update_scrap_job_status(
                    db, scrap_job.id, ScrapJobStatus.ERROR
                )
                if updated:
                    await db.commit()
                    await broadcast_scrap_job_status(
                        ScrapJobResponse.model_validate(updated).model_dump(),
                        ScrapJobStatus.ERROR.value,
                    )

    async def _extract_jobs_from_html(
        self, html: str, base_url: str
    ) -> list[dict]:
        """Extract job listings from HTML content using common patterns."""
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[dict] = []

        candidate_elements = self._find_job_elements(soup)
        for element in candidate_elements:
            job = self._parse_job_element(element, base_url)
            if job and job.get("title"):
                jobs.append(job)

        if not jobs:
            jobs = self._fallback_extraction(soup, base_url)

        return jobs

    async def _fetch_job_details_via_llm(
        self, jobs: list[dict], db: AsyncSession, scrap_job_id: int
    ):
        """
        Fetch key details for jobs via LLM in chunks.
        Yields (job_data, parsed_data) for each job as chunks are parsed.
        """
        if not jobs:
            return
        chunk_size = 5
        llm_client = LLMFactory.get_client(
            provider_name="grok",
            model_name="grok-4-1-fast-reasoning",
        )
        for i in range(0, len(jobs), chunk_size):
            refreshed = await get_scrap_job_by_id(db, scrap_job_id)
            if refreshed and refreshed.status in _SCRAP_JOB_HALTED_STATUSES:
                return

            chunk = jobs[i : i + chunk_size]
            jobs_json = json.dumps(
                [{"title": j["title"], "links": j.get("links", []), "description": j.get("description", "")} for j in chunk],
                indent=2,
            )
            prompt = JOB_PARSER_USER_PROMPT_TEMPLATE.format(jobs_json=jobs_json)
            parsed_items: list[dict] = []
            try:
                response = await llm_client.generate_content(
                    system_prompt=JOB_PARSER_SYSTEM_PROMPT,
                    prompt=prompt,
                )
                response_text = (response or "").strip()
                json_str = _extract_json_array(response_text) or response_text
                json_str = re.sub(r",\s*}", "}", json_str)
                json_str = re.sub(r",\s*]", "]", json_str)
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    parsed_items = parsed[: len(chunk)]
                    if len(parsed_items) < len(chunk):
                        parsed_items.extend([{}] * (len(chunk) - len(parsed_items)))
                elif isinstance(parsed, dict):
                    parsed_items = [parsed] + [{}] * (len(chunk) - 1)
                else:
                    parsed_items = [{}] * len(chunk)
            except (json.JSONDecodeError, ValueError):
                logger.warning("LLM returned invalid JSON for chunk %d", i // chunk_size)
                parsed_items = [{}] * len(chunk)
            for job_data, parsed_data in zip(chunk, parsed_items):
                yield job_data, parsed_data

    def _parse_emails(self, value: str | list | None) -> list[str]:
        """Parse company_emails from LLM response into a list of strings."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if v and str(v).strip()]
        if isinstance(value, str):
            parts = re.split(r"[,;\s]+", value)
            return [p.strip() for p in parts if p and "@" in p]
        return []

    def _job_matches_categories(
        self, job_data: dict, categories: list | None
    ) -> bool:
        """Return True if job title or description contains any category keyword."""
        if not categories:
            return True
        title = (job_data.get("title") or "").lower()
        description = (job_data.get("description") or "").lower()
        text = f"{title} {description}"
        for category in categories:
            if category and str(category).strip().lower() in text:
                return True
        return False

    def _find_job_elements(self, soup: BeautifulSoup) -> list[Tag]:
        """Locate HTML elements that likely represent individual job listings."""
        candidates: list[Tag] = []
        for keyword in JOB_LISTING_KEYWORDS:
            candidates.extend(
                soup.find_all(
                    ["div", "li", "article", "section", "tr"],
                    class_=lambda c: c and keyword in str(c).lower(),
                )
            )
            candidates.extend(
                soup.find_all(
                    ["div", "li", "article", "section", "tr"],
                    id=lambda i: i and keyword in str(i).lower(),
                )
            )
            candidates.extend(
                soup.find_all(
                    attrs={"data-type": lambda v: v and keyword in str(v).lower()}
                )
            )

        seen_ids: set[int] = set()
        unique: list[Tag] = []
        for el in candidates:
            eid = id(el)
            if eid not in seen_ids:
                seen_ids.add(eid)
                unique.append(el)
        return unique

    def _title_from_job_href(self, href: str) -> str:
        """
        Build a readable title from a job detail URL path when the anchor has no text
        (e.g. listing cards that only expose the title in h2 or aria-label).
        """
        path = (href or "").strip().split("?")[0].rstrip("/")
        if not path:
            return ""
        segment = path.split("/")[-1]
        if not segment:
            return ""
        segment = re.sub(r"-\d{5,}$", "", segment)
        segment = re.sub(r"[_-]+", " ", segment).strip()
        return segment[:500] if segment else ""

    def _parse_job_element(self, element: Tag, base_url: str) -> dict | None:
        """
        Extract structured job data from a single HTML element.

        Filters out jobs that lack both url and email, or have no description or
        description shorter than 100 characters. Returns data in format
        {title, links, description}.
        """
        title = None
        links: list[str] = []
        description = None
        company_emails: list[str] = []

        heading = None
        for name in ("h1", "h2", "h3", "h4"):
            h = element.find(name)
            if h is not None and h.get_text(strip=True):
                heading = h
                break
        if heading is None:
            for a in element.find_all("a", href=True):
                aria = (a.get("aria-label") or "").strip()
                tit_a = (a.get("title") or "").strip()
                txt = a.get_text(strip=True)
                if txt or aria or tit_a:
                    heading = a
                    break
        if heading is None:
            job_path_markers = ("/jobs/", "/job/", "stellen", "vacancy", "career", "position")
            for a in element.find_all("a", href=True):
                raw_h = str(a.get("href", "")).strip().lower()
                if raw_h.startswith("#"):
                    continue
                if any(m in raw_h for m in job_path_markers):
                    heading = a
                    break
        if heading is None:
            return None

        if heading.name in ("h1", "h2", "h3", "h4"):
            title = heading.get_text(strip=True)
        else:
            title = (
                heading.get_text(strip=True)
                or (heading.get("aria-label") or "").strip()
                or (heading.get("title") or "").strip()
            )
            if not title and heading.get("href"):
                title = self._title_from_job_href(str(heading["href"]))

        if heading.name == "a" and heading.get("href"):
            href = heading["href"]
            full_url = urljoin(base_url, href)
            if full_url.startswith(("http://", "https://")):
                links.append(full_url)
        elif heading.name in ("h1", "h2", "h3", "h4"):
            link = heading.find("a")
            if link and link.get("href"):
                full_url = urljoin(base_url, link["href"])
                if full_url.startswith(("http://", "https://")):
                    links.append(full_url)

        for tag in element.find_all("a", href=True):
            raw = str(tag.get("href", "")).strip()
            if not raw or raw.startswith("#") or raw.lower().startswith("javascript:"):
                continue
            low = raw.lower()
            if low.startswith("mailto:"):
                email = raw.replace("mailto:", "").split("?")[0].strip()
                if email and email not in company_emails:
                    company_emails.append(email)
            else:
                full_url = urljoin(base_url, raw)
                if full_url.startswith(("http://", "https://")) and full_url not in links:
                    links.append(full_url)

        if not title:
            return None

        paragraphs = element.find_all("p")
        if paragraphs:
            description = " ".join(p.get_text(strip=True) for p in paragraphs)

        if not description:
            raw_text = element.get_text(separator=" ", strip=True)
            if raw_text and raw_text != title:
                description = raw_text

        email_pattern = re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )
        if description and email_pattern.search(description):
            for m in email_pattern.finditer(description):
                e = m.group(0)
                if e not in company_emails:
                    company_emails.append(e)

        has_url_or_email = len(links) > 0 or len(company_emails) > 0
        if not has_url_or_email:
            return None

        if not description or len(description.strip()) < 100:
            return None

        return {
            "title": title[:500],
            "links": links,
            "description": description,
        }

    def _fallback_extraction(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[dict]:
        """
        Attempt a broad extraction when no structured job elements are found.

        Returns jobs in format {title, links, description}. Only includes jobs
        that have url and description with at least 100 characters.
        """
        jobs: list[dict] = []
        for link in soup.find_all("a", href=True):
            raw_href = str(link.get("href", "")).strip()
            low = raw_href.lower()
            if not raw_href or low.startswith("#") or low.startswith("javascript:"):
                continue
            if not any(kw in low for kw in JOB_LISTING_KEYWORDS):
                continue
            text = link.get_text(strip=True)
            aria = (link.get("aria-label") or "").strip()
            tit = (link.get("title") or "").strip()
            title = text or aria or tit
            if not title:
                title = self._title_from_job_href(raw_href)
            if not title or len(title) < 3:
                continue
            job_url = urljoin(base_url, link["href"])
            if not job_url.startswith(("http://", "https://")):
                continue
            description = None
            if len(text) >= 100:
                description = text
            elif len(aria) >= 100:
                description = aria
            else:
                parent = link.find_parent(["article", "li", "div", "section"])
                if parent is not None:
                    blob = parent.get_text(separator=" ", strip=True)
                    if blob and len(blob) >= 100:
                        description = blob
            if not description or len(description.strip()) < 100:
                continue
            jobs.append(
                {
                    "title": title[:500],
                    "links": [job_url],
                    "description": description,
                }
            )
        return jobs

    def _extract_crawlable_links(
        self, html: str, base_url: str, base_domain: str
    ) -> list[str]:
        """Extract same-domain links from HTML for crawling."""
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        seen: set[str] = set()

        skip_extensions = (
            ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
            ".css", ".js", ".woff", ".woff2", ".ico", ".mp4", ".mp3",
            ".zip", ".doc", ".docx", ".xls", ".xml", ".json",
        )
        skip_schemes = ("mailto:", "tel:", "javascript:", "#")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or any(href.lower().startswith(s) for s in skip_schemes):
                continue
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.netloc != base_domain:
                continue
            path_lower = parsed.path.lower()
            if any(path_lower.endswith(ext) for ext in skip_extensions):
                continue
            norm = self._core.normalize_url(full_url)
            if norm not in seen:
                seen.add(norm)
                links.append(full_url)
        return links
