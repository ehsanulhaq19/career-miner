"""Low-level HTTP and browser fetch utilities shared by job-site and client scrapers."""

import asyncio
import logging
import random
from urllib.parse import urlparse

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

ANTI_BOT_DOMAIN_PATTERNS = (
    "indeed.",
    "glassdoor.",
    "monster.",
    "ziprecruiter.",
    "xing.",
)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


class ScrapeCore:
    """
    Provides browser-like fetching with httpx, Playwright fallback for anti-bot pages,
    and optional scroll-based loading. Used by job-site scraping and can be reused elsewhere.
    """

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for deduplication (strip fragment, trailing slash)."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            normalized += "?" + parsed.query
        return normalized

    @staticmethod
    def get_random_user_agent() -> str:
        """Return a random User-Agent from the pool to reduce fingerprinting."""
        return random.choice(USER_AGENTS)

    @staticmethod
    def is_anti_bot_site(url: str) -> bool:
        """Return True if the URL's domain is known to block simple HTTP clients."""
        parsed = urlparse(url)
        domain = (parsed.netloc or "").lower()
        return any(pattern in domain for pattern in ANTI_BOT_DOMAIN_PATTERNS)

    def browser_headers(
        self, referer: str | None, user_agent: str | None = None
    ) -> dict[str, str]:
        """Return browser-like headers to reduce bot detection."""
        headers = {
            "User-Agent": user_agent or self.get_random_user_agent(),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
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

    async def warm_up_session(self, client: httpx.AsyncClient, seed_url: str) -> None:
        """Visit homepage first to establish session cookies (helps with 403)."""
        parsed = urlparse(seed_url)
        homepage = f"{parsed.scheme}://{parsed.netloc}/"
        if homepage == seed_url:
            return
        try:
            headers = self.browser_headers(homepage)
            await client.get(homepage, headers=headers)
            await asyncio.sleep(random.uniform(1.0, 2.5))
        except Exception as e:
            logger.debug("Warm-up request to %s failed: %s", homepage, e)

    def random_delay(self, settings: Settings) -> float:
        """Return a random delay between requests to avoid detection."""
        return random.uniform(
            settings.CRAWL_DELAY_MIN_SECONDS,
            settings.CRAWL_DELAY_MAX_SECONDS,
        )

    async def fetch_page(
        self, client: httpx.AsyncClient, url: str
    ) -> tuple[str, str]:
        """
        Fetch a web page and return (HTML content, final URL after redirects).
        On 403, falls back to Playwright. On 429, retries with backoff.
        """
        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        max_retries = 3
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                headers = self.browser_headers(referer)
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                final_url = str(response.url)
                return response.text, final_url
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 403:
                    logger.info("403 on %s, falling back to Playwright", url)
                    return await self.fetch_page_playwright(url)
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    delay = (2**attempt) + random.uniform(1.0, 2.0)
                    logger.info(
                        "Rate limited (429) on %s, retrying in %.1fs",
                        url,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = (2**attempt) + random.uniform(0.5, 1.5)
                    await asyncio.sleep(delay)
                else:
                    raise

        if last_error:
            raise last_error
        raise RuntimeError("Unexpected fetch failure")

    async def fetch_page_playwright(self, url: str) -> tuple[str, str]:
        """
        Fetch a page using Playwright (real browser). Used for anti-bot sites
        and as fallback when httpx gets 403.
        """
        from playwright.async_api import async_playwright

        settings = get_settings()
        user_agent = self.get_random_user_agent()
        async with async_playwright() as p:
            launch_options: dict = {"headless": True}
            if settings.SCRAP_HTTP_PROXY:
                launch_options["proxy"] = {"server": settings.SCRAP_HTTP_PROXY}
            browser = await p.chromium.launch(**launch_options)
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="load", timeout=30000)
                await asyncio.sleep(random.uniform(1.5, 3.0))
                html = await page.content()
                final_url = page.url
                return html, final_url
            finally:
                await browser.close()

    async def fetch_page_with_scroll(
        self, url: str, max_scroll: int = 10, scroll_delay: float = 1.5
    ) -> tuple[str, str]:
        """
        Fetch a page using Playwright, simulate scroll to load lazy/infinite content,
        and return the final HTML and URL.
        """
        from playwright.async_api import async_playwright

        settings = get_settings()
        user_agent = self.get_random_user_agent()
        async with async_playwright() as p:
            launch_options: dict = {"headless": True}
            if settings.SCRAP_HTTP_PROXY:
                launch_options["proxy"] = {"server": settings.SCRAP_HTTP_PROXY}
            browser = await p.chromium.launch(**launch_options)
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                prev_height = 0
                scroll_count = 0
                while scroll_count < max_scroll:
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await asyncio.sleep(scroll_delay)
                    new_height = await page.evaluate(
                        "document.body.scrollHeight"
                    )
                    if new_height == prev_height:
                        break
                    prev_height = new_height
                    scroll_count += 1
                html = await page.content()
                final_url = page.url
                return html, final_url
            finally:
                await browser.close()
