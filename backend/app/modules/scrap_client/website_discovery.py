"""Service for discovering official company websites via search."""

import logging
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.modules.scrap_client.url_utils import normalize_url

logger = logging.getLogger(__name__)

SEARCH_URL = "https://html.duckduckgo.com/html/"
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
]


def _browser_headers() -> dict:
    """Return browser-like headers for HTTP requests."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _extract_url_from_duckduckgo_redirect(href: str) -> str | None:
    """Extract actual URL from DuckDuckGo redirect link."""
    if not href or "uddg=" not in href:
        return None
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    uddg = qs.get("uddg", [])
    if uddg:
        return unquote(uddg[0])
    return None


async def discover_official_website(company_name: str) -> str | None:
    """
    Search for the official company website using DuckDuckGo.
    Returns the first valid domain found for the company.
    """
    if not company_name or not company_name.strip():
        return None
    query = f'"{company_name.strip()}" official website'
    encoded_query = quote_plus(query)
    url = f"{SEARCH_URL}?q={encoded_query}"
    settings = get_settings()
    client_kwargs: dict = {
        "timeout": 15,
        "follow_redirects": True,
        "headers": _browser_headers(),
    }
    if settings.SCRAP_HTTP_PROXY:
        client_kwargs["proxy"] = settings.SCRAP_HTTP_PROXY
    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            results = soup.select("a.result__url") or soup.select("a.result__a")
            if not results:
                results = [
                    a for a in soup.find_all("a", href=True)
                    if "uddg=" in a.get("href", "") or "duckduckgo.com/l/" in a.get("href", "")
                ]
            seen_domains: set[str] = set()
            for anchor in results[:10]:
                href = anchor.get("href")
                if not href:
                    continue
                actual_url = _extract_url_from_duckduckgo_redirect(href)
                if not actual_url:
                    continue
                normalized = normalize_url(actual_url)
                if not normalized:
                    continue
                parsed = urlparse(normalized)
                domain = parsed.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                if domain in seen_domains:
                    continue
                skip_domains = [
                    "duckduckgo.com",
                    "google.com",
                    "facebook.com",
                    "twitter.com",
                    "x.com",
                    "linkedin.com",
                    "youtube.com",
                    "instagram.com",
                    "wikipedia.org",
                    "crunchbase.com",
                ]
                if any(domain.endswith(d) or domain == d for d in skip_domains):
                    continue
                seen_domains.add(domain)
                return normalized
    except Exception:
        pass
    return None
