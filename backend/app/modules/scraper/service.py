import asyncio
import json
import logging
import random
import re
from collections import deque
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.modules.career_client.crud import get_or_create_career_client
from app.modules.career_job.crud import (
    check_job_exists_by_title_and_links,
    create_career_job,
)
from app.modules.llm.service import LLMFactory
from app.modules.job_site.models import JobSite
from app.modules.scrap_job.crud import get_scrap_job_by_id, update_scrap_job_status
from app.modules.scrap_job.models import ScrapJob, ScrapJobStatus
from app.modules.scrap_job.schemas import ScrapJobResponse
from app.modules.scraper.prompts import (
    JOB_PARSER_SYSTEM_PROMPT,
    JOB_PARSER_USER_PROMPT_TEMPLATE,
)
from app.modules.websocket.service import broadcast_scrap_job_status

logger = logging.getLogger(__name__)

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

    async def scrape_job_site(
        self,
        db: AsyncSession,
        job_site: JobSite,
        scrap_job: ScrapJob,
    ) -> None:
        """Execute scraping for a single job site and save found jobs."""
        refreshed = await get_scrap_job_by_id(db, scrap_job.id)
        if refreshed and refreshed.status == ScrapJobStatus.STOPPED.value:
            return
        updated = await update_scrap_job_status(
            db, scrap_job.id, ScrapJobStatus.IN_PROGRESS
        )
        if updated:
            await broadcast_scrap_job_status(
                ScrapJobResponse.model_validate(updated).model_dump(),
                ScrapJobStatus.IN_PROGRESS.value,
            )
        try:
            settings = get_settings()
            visited: set[str] = set()
            queued: set[str] = set()
            all_jobs: list[dict] = []
            base_domain = urlparse(job_site.url).netloc
            to_visit: deque[str] = deque([job_site.url])
            queued.add(self._normalize_url(job_site.url))
            saved_count = 0
            pages_scraped = 0

            client_kwargs: dict = {
                "timeout": 30,
                "follow_redirects": True,
                "headers": self._browser_headers(job_site.url),
            }
            if settings.SCRAP_HTTP_PROXY:
                client_kwargs["proxy"] = settings.SCRAP_HTTP_PROXY
            async with httpx.AsyncClient(**client_kwargs) as client:
                await self._warm_up_session(client, job_site.url)

                while to_visit and pages_scraped < settings.MAX_PAGES_PER_SCRAP:
                    refreshed = await get_scrap_job_by_id(db, scrap_job.id)
                    if refreshed and refreshed.status == ScrapJobStatus.STOPPED.value:
                        logger.info("Scrap job %d stopped by user", scrap_job.id)
                        break

                    url = to_visit.popleft()
                    url_normalized = self._normalize_url(url)
                    if url_normalized in visited:
                        continue
                    visited.add(url_normalized)

                    try:
                        html, final_url = await self._fetch_page(client, url)
                    except Exception as e:
                        logger.warning("Failed to fetch %s: %s", url, e)
                        continue

                    if pages_scraped == 0:
                        base_domain = urlparse(final_url).netloc

                    jobs = await self._extract_jobs_from_html(html, final_url)
                    for job_data in jobs:
                        if not job_data.get("title"):
                            continue
                        if not self._job_matches_categories(
                            job_data, job_site.categories
                        ):
                            continue
                        exists = await check_job_exists_by_title_and_links(
                            db,
                            title=job_data["title"],
                            job_site_id=job_site.id,
                            links=job_data.get("links", []),
                        )
                        if exists:
                            continue
                        all_jobs.append(job_data)

                    for link in self._extract_crawlable_links(html, final_url, base_domain):
                        normalized = self._normalize_url(link)
                        if normalized not in visited and normalized not in queued:
                            to_visit.append(link)
                            queued.add(normalized)

                    pages_scraped += 1
                    delay = self._random_delay(settings)
                    if delay > 0:
                        await asyncio.sleep(delay)

                parsed_jobs_array = await self._fetch_job_details_via_llm(all_jobs)
                for job_data, parsed_data in zip(all_jobs, parsed_jobs_array):
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
                    )
                    career_job_data = {
                        "title": job_data["title"],
                        "description": job_data.get("description"),
                        "url": primary_url,
                        "job_site_id": job_site.id,
                        "scrap_job_id": scrap_job.id,
                        "parsed_data": parsed_data,
                        "meta_data": {},
                    }
                    if career_client:
                        career_job_data["career_client_id"] = career_client.id
                    await create_career_job(db, career_job_data)
                    saved_count += 1

            logger.info(
                "Scraping completed for site %s — %d pages crawled, %d jobs saved",
                job_site.name,
                pages_scraped,
                saved_count,
            )
            refreshed = await get_scrap_job_by_id(db, scrap_job.id)
            if refreshed and refreshed.status != ScrapJobStatus.STOPPED.value:
                updated = await update_scrap_job_status(
                    db, scrap_job.id, ScrapJobStatus.COMPLETED
                )
                if updated:
                    await broadcast_scrap_job_status(
                        ScrapJobResponse.model_validate(updated).model_dump(),
                        ScrapJobStatus.COMPLETED.value,
                    )
        except Exception:
            logger.exception("Scraping failed for site %s", job_site.name)
            refreshed = await get_scrap_job_by_id(db, scrap_job.id)
            if refreshed and refreshed.status != ScrapJobStatus.STOPPED.value:
                updated = await update_scrap_job_status(
                    db, scrap_job.id, ScrapJobStatus.ERROR
                )
                if updated:
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
        self, jobs: list[dict]
    ) -> list[dict]:
        """
        Fetch key details for jobs via LLM in chunks of 10.

        Returns a list of parsed_data dicts in the same order as input jobs.
        """
        if not jobs:
            return []
        parsed_jobs_array: list[dict] = []
        chunk_size = 5
        llm_client = LLMFactory.get_client(
            provider_name="grok",
            model_name="grok-4-1-fast-reasoning",
        )
        for i in range(0, len(jobs), chunk_size):
            chunk = jobs[i : i + chunk_size]
            jobs_json = json.dumps(
                [{"title": j["title"], "links": j.get("links", []), "description": j.get("description", "")} for j in chunk],
                indent=2,
            )
            prompt = JOB_PARSER_USER_PROMPT_TEMPLATE.format(jobs_json=jobs_json)
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
                    items = parsed[: len(chunk)]
                    parsed_jobs_array.extend(items)
                    if len(items) < len(chunk):
                        parsed_jobs_array.extend([{}] * (len(chunk) - len(items)))
                elif isinstance(parsed, dict):
                    parsed_jobs_array.append(parsed)
                    parsed_jobs_array.extend([{}] * (len(chunk) - 1))
                else:
                    parsed_jobs_array.extend([{}] * len(chunk))
            except (json.JSONDecodeError, ValueError):
                logger.warning("LLM returned invalid JSON for chunk %d", i // chunk_size)
                parsed_jobs_array.extend([{}] * len(chunk))
        return parsed_jobs_array[: len(jobs)]

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

        heading = element.find(["h1", "h2", "h3", "h4", "a"])
        if heading:
            title = heading.get_text(strip=True)
            if heading.name == "a" and heading.get("href"):
                href = heading["href"]
                full_url = urljoin(base_url, href)
                if full_url.startswith(("http://", "https://")):
                    links.append(full_url)
            else:
                link = heading.find("a")
                if link and link.get("href"):
                    full_url = urljoin(base_url, link["href"])
                    if full_url.startswith(("http://", "https://")):
                        links.append(full_url)

        for tag in element.find_all("a", href=True):
            href = str(tag.get("href", "")).lower()
            if href.startswith("mailto:"):
                email = href.replace("mailto:", "").split("?")[0].strip()
                if email and email not in company_emails:
                    company_emails.append(email)
            elif href.startswith(("http://", "https://")):
                full_url = urljoin(base_url, tag["href"])
                if full_url not in links:
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
            text = link.get_text(strip=True)
            href = str(link["href"]).lower()
            if not text or len(text) < 5:
                continue
            if any(kw in href for kw in JOB_LISTING_KEYWORDS):
                job_url = urljoin(base_url, link["href"])
                if not job_url.startswith(("http://", "https://")):
                    continue
                description = text if len(text) >= 100 else None
                if not description:
                    continue
                jobs.append(
                    {
                        "title": text[:500],
                        "links": [job_url],
                        "description": description,
                    }
                )
        return jobs

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication (strip fragment, trailing slash)."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            normalized += "?" + parsed.query
        return normalized

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
            norm = self._normalize_url(full_url)
            if norm not in seen:
                seen.add(norm)
                links.append(full_url)
        return links

    def _browser_headers(self, referer: str | None) -> dict[str, str]:
        """Return browser-like headers to reduce bot detection."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none" if not referer else "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Cache-Control": "max-age=0",
            "DNT": "1",
            "Pragma": "no-cache",
            "Priority": "u=0, i",
        }
        if referer:
            parsed = urlparse(referer)
            base = f"{parsed.scheme}://{parsed.netloc}/"
            headers["Referer"] = base
            headers["Origin"] = base.rstrip("/")
        return headers

    async def _warm_up_session(self, client: httpx.AsyncClient, seed_url: str) -> None:
        """Visit homepage first to establish session cookies (helps with 403)."""
        parsed = urlparse(seed_url)
        homepage = f"{parsed.scheme}://{parsed.netloc}/"
        if homepage == seed_url:
            return
        try:
            await client.get(homepage)
        except Exception as e:
            logger.debug("Warm-up request to %s failed: %s", homepage, e)

    def _random_delay(self, settings: Settings) -> float:
        """Return a random delay between requests to avoid detection."""
        return random.uniform(
            settings.CRAWL_DELAY_MIN_SECONDS,
            settings.CRAWL_DELAY_MAX_SECONDS,
        )

    async def _fetch_page(
        self, client: httpx.AsyncClient, url: str
    ) -> tuple[str, str]:
        """Fetch a web page and return (HTML content, final URL after redirects)."""
        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        headers = self._browser_headers(referer)
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        final_url = str(response.url)
        return response.text, final_url
