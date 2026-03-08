import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_job.crud import check_duplicate_job, create_career_job
from app.modules.job_site.models import JobSite
from app.modules.scrap_job.crud import update_scrap_job_status
from app.modules.scrap_job.models import ScrapJob

logger = logging.getLogger(__name__)

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
        await update_scrap_job_status(db, scrap_job.id, "in_progress")
        try:
            html = await self._fetch_page(job_site.url)
            jobs = await self._extract_jobs_from_html(html, job_site.url)
            saved_count = 0
            for job_data in jobs:
                if not job_data.get("title"):
                    continue
                existing = await check_duplicate_job(
                    db,
                    title=job_data["title"],
                    job_site_id=job_site.id,
                    url=job_data.get("url"),
                    description=job_data.get("description"),
                )
                if existing:
                    continue
                await create_career_job(
                    db,
                    {
                        "title": job_data["title"],
                        "description": job_data.get("description"),
                        "url": job_data.get("url"),
                        "job_site_id": job_site.id,
                        "scrap_job_id": scrap_job.id,
                        "contact_details": job_data.get("contact_details"),
                        "meta_data": job_data.get("meta_data", {}),
                    },
                )
                saved_count += 1
            logger.info(
                "Scraping completed for site %s — %d jobs saved",
                job_site.name,
                saved_count,
            )
            await update_scrap_job_status(db, scrap_job.id, "completed")
        except Exception:
            logger.exception("Scraping failed for site %s", job_site.name)
            await update_scrap_job_status(db, scrap_job.id, "error")

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
        """Extract structured job data from a single HTML element."""
        title = None
        url = None
        description = None
        contact_details = None

        heading = element.find(["h1", "h2", "h3", "h4", "a"])
        if heading:
            title = heading.get_text(strip=True)
            if heading.name == "a" and heading.get("href"):
                url = urljoin(base_url, heading["href"])
            else:
                link = heading.find("a")
                if link and link.get("href"):
                    url = urljoin(base_url, link["href"])

        if not title:
            return None

        paragraphs = element.find_all("p")
        if paragraphs:
            description = " ".join(p.get_text(strip=True) for p in paragraphs)

        if not description:
            raw_text = element.get_text(separator=" ", strip=True)
            if raw_text and raw_text != title:
                description = raw_text

        contact_keywords = ["email", "phone", "contact", "apply", "mailto:"]
        for tag in element.find_all(["a", "span", "p", "div"]):
            tag_text = tag.get_text(strip=True).lower()
            tag_href = str(tag.get("href", "")).lower()
            if any(kw in tag_text or kw in tag_href for kw in contact_keywords):
                contact_details = tag.get_text(strip=True)
                break

        meta_data: dict = {}
        for attr_name in ["data-company", "data-location", "data-salary", "data-date"]:
            value = element.get(attr_name)
            if value:
                meta_data[attr_name.replace("data-", "")] = value

        return {
            "title": title[:500],
            "description": description,
            "url": url,
            "contact_details": contact_details,
            "meta_data": meta_data,
        }

    def _fallback_extraction(
        self, soup: BeautifulSoup, base_url: str
    ) -> list[dict]:
        """Attempt a broad extraction when no structured job elements are found."""
        jobs: list[dict] = []
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = str(link["href"]).lower()
            if not text or len(text) < 5:
                continue
            if any(kw in href for kw in JOB_LISTING_KEYWORDS):
                jobs.append(
                    {
                        "title": text[:500],
                        "description": None,
                        "url": urljoin(base_url, link["href"]),
                        "contact_details": None,
                        "meta_data": {},
                    }
                )
        return jobs

    async def _fetch_page(self, url: str) -> str:
        """Fetch a web page and return its HTML content."""
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
            )
            response.raise_for_status()
            return response.text
