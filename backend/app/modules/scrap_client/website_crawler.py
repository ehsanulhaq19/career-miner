"""Website crawling service for high-value pages."""

import asyncio
import logging
import random
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.modules.scrap_client.url_utils import extract_root_domain, normalize_url

logger = logging.getLogger(__name__)

HIGH_VALUE_PATHS = [
    "/contact",
    "/contact-us",
    "/contact_us",
    "/about",
    "/about-us",
    "/team",
    "/careers",
    "/jobs",
    "/support",
    "/career",
    "/recruiting",
    "/talent",
    "/hr",
    "/people",
]


def _browser_headers(base_url: str) -> dict:
    """Return browser-like headers for HTTP requests."""
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": origin,
    }


class WebsiteCrawler:
    """Crawls high-value pages on a website with rate limiting and retries."""

    def __init__(
        self,
        max_pages: int = 20,
        request_timeout: float = 15,
        max_retries: int = 3,
        delay_min: float | None = None,
        delay_max: float | None = None,
    ):
        self.max_pages = max_pages
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        settings = get_settings()
        self.delay_min = delay_min or settings.CRAWL_DELAY_MIN_SECONDS
        self.delay_max = delay_max or settings.CRAWL_DELAY_MAX_SECONDS

    async def crawl(
        self,
        base_url: str,
        on_page_fetched: Callable[[str, str], None] | None = None,
    ) -> list[tuple[str, str]]:
        """
        Crawl high-value pages on the website.
        Returns list of (url, html_content) tuples.
        """
        root_domain = extract_root_domain(base_url)
        if not root_domain:
            return []
        parsed_base = urlparse(base_url)
        scheme = parsed_base.scheme or "https"
        netloc = parsed_base.netloc or ""
        base_origin = f"{scheme}://{netloc}"
        to_visit: list[str] = [base_url]
        for path in HIGH_VALUE_PATHS:
            candidate = urljoin(base_origin, path)
            normalized = normalize_url(candidate)
            if normalized and normalized not in to_visit:
                to_visit.append(normalized)
        visited: set[str] = set()
        results: list[tuple[str, str]] = []
        settings = get_settings()
        client_kwargs: dict = {
            "timeout": self.request_timeout,
            "follow_redirects": True,
            "headers": _browser_headers(base_url),
        }
        if settings.SCRAP_HTTP_PROXY:
            client_kwargs["proxy"] = settings.SCRAP_HTTP_PROXY
        async with httpx.AsyncClient(**client_kwargs) as client:
            for url in to_visit:
                if len(results) >= self.max_pages:
                    break
                url_norm = normalize_url(url, base_origin)
                if not url_norm:
                    continue
                parsed = urlparse(url_norm)
                if parsed.netloc.lower() != netloc.lower():
                    continue
                if url_norm in visited:
                    continue
                visited.add(url_norm)
                html = await self._fetch_with_retry(client, url_norm)
                if html:
                    results.append((url_norm, html))
                    if on_page_fetched:
                        on_page_fetched(url_norm, html)
                delay = random.uniform(self.delay_min, self.delay_max)
                await asyncio.sleep(delay)
        return results

    async def _fetch_with_retry(
        self, client: httpx.AsyncClient, url: str
    ) -> str | None:
        """Fetch URL with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except Exception:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    pass
        return None
