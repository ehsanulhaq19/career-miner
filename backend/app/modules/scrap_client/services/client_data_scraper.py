"""
Scrapes client/company data from a website URL and persists to CareerClient.
Uses website discovery when email is not found.
Supports Cloudflare-protected sites (e.g. GoodFirms) via Playwright fallback.
"""

import asyncio
import json
import logging
import random
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.career_client.crud import (
    get_or_create_career_client,
    update_career_client,
)
from app.modules.llm.service import LLMFactory
from app.modules.scrap_client.services.email_extractor import extract_emails_from_html
from app.modules.scrap_client.services.url_utils import extract_root_domain, normalize_url
from app.modules.scrap_client.services.website_crawler import WebsiteCrawler
from app.modules.scrap_client.services.website_discovery import (
    DiscoveryResult,
    discover_company_info,
)
from app.modules.scraper.service import ScraperHtmlStorage

logger = logging.getLogger(__name__)

# Sites that require Playwright (Cloudflare, JS rendering). Use for client scraping.
CLIENT_ANTI_BOT_DOMAIN_PATTERNS = ("goodfirms.", "clutch.co", "sortlist.")

# Strings that indicate a bot-block / JS-required page
BOT_BLOCK_INDICATORS = (
    "Enable JavaScript and cookies to continue",
    "Please enable JavaScript",
    "Checking your browser",
    "_cf_chl_opt",
    "cf-browser-verification",
)

CLIENT_LISTING_KEYWORDS = [
    "company",
    "employer",
    "organization",
    "business",
    "client",
    "corporate",
    "vendor",
    "listing",
    "card",
    "provider",
    "firm",
]

CLIENT_PARSER_SYSTEM_PROMPT = (
    "Act as a parser for company/client directory pages. "
    "Respond with ONLY a valid JSON array - no markdown, no code blocks, no extra text."
)

CLIENT_PARSER_USER_PROMPT_TEMPLATE = """Extract all companies/clients from the following HTML content. For each company provide:
{{
    "name": "",
    "website": "",
    "emails": [],
    "detail": "",
    "location": "",
    "size": "",
    "link": ""
}}

Return a JSON array of objects. Use empty string or empty array for missing fields.
link should be the primary URL for the company if available.
Output must be valid JSON with no markdown formatting.

HTML content (truncated if long):
{html_content}
"""


def _url_needs_playwright(url: str) -> bool:
    """Return True if domain is known to require Playwright (Cloudflare, etc.)."""
    try:
        netloc = (urlparse(url).netloc or "").lower()
        return any(p in netloc for p in CLIENT_ANTI_BOT_DOMAIN_PATTERNS)
    except Exception:
        return False


def _is_bot_block_page(html: str) -> bool:
    """Return True if HTML indicates a Cloudflare/bot-block page."""
    if not html or len(html) < 1000:
        return True
    lower = html.lower()
    return any(ind.lower() in lower for ind in BOT_BLOCK_INDICATORS)


async def _fetch_html_playwright(url: str) -> tuple[str, str]:
    """Fetch page using Playwright for JS-rendered / Cloudflare-protected sites."""
    from playwright.async_api import async_playwright

    settings = get_settings()
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ]
    user_agent = random.choice(user_agents)
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
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(random.uniform(2.0, 4.0))
            html = await page.content()
            final_url = page.url
            return html, final_url
        finally:
            await browser.close()


async def _fetch_html_for_client_scrape(url: str) -> tuple[str, str] | None:
    """
    Fetch HTML for client scraping. Uses Playwright for known anti-bot domains
    or when httpx returns a bot-block page (Cloudflare challenge, etc.).
    Returns (html, final_url) or None on failure.
    """
    settings = get_settings()
    client_kwargs: dict = {
        "timeout": 30,
        "follow_redirects": True,
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    }
    if settings.SCRAP_HTTP_PROXY:
        client_kwargs["proxy"] = settings.SCRAP_HTTP_PROXY

    use_playwright_first = _url_needs_playwright(url)
    if use_playwright_first:
        logger.info("Using Playwright for %s (anti-bot domain)", url)
        try:
            return await _fetch_html_playwright(url)
        except Exception as e:
            logger.warning("Playwright fetch failed for %s: %s", url, e)
            return None

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
            final_url = str(resp.url)
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None

    if _is_bot_block_page(html):
        logger.info("Bot-block detected, retrying with Playwright: %s", url)
        try:
            return await _fetch_html_playwright(url)
        except Exception as e:
            logger.warning("Playwright fallback failed for %s: %s", url, e)
            return None

    return html, final_url


def _extract_json_array(text: str) -> str | None:
    """Extract JSON array from LLM response."""
    text = (text or "").strip()
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    start = text.find("[")
    if start < 0:
        return None
    depth = 0
    for i, c in enumerate(text[start:], start):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_emails(value: str | list | None) -> list[str]:
    """Parse emails from LLM response into list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v and str(v).strip() and "@" in str(v)]
    if isinstance(value, str):
        parts = re.split(r"[,;\s]+", value)
        return [p.strip() for p in parts if p and "@" in p]
    return []


def _find_client_elements(soup: BeautifulSoup) -> list[Tag]:
    """Locate HTML elements that likely represent company/client listings."""
    candidates: list[Tag] = []
    for keyword in CLIENT_LISTING_KEYWORDS:
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
    seen_ids: set[int] = set()
    result: list[Tag] = []
    for el in candidates:
        eid = id(el)
        if eid not in seen_ids:
            seen_ids.add(eid)
            result.append(el)
    return result


def _parse_client_element(element: Tag, base_url: str) -> dict | None:
    """Extract structured client data from a single HTML element."""
    name = None
    links: list[str] = []
    description = None
    emails: list[str] = []

    heading = element.find(["h1", "h2", "h3", "h4", "a"])
    if heading:
        name = heading.get_text(strip=True)
        if heading.name == "a" and heading.get("href"):
            href = heading["href"]
            full_url = urljoin(base_url, href)
            if full_url.startswith(("http://", "https://")):
                links.append(full_url)
        else:
            link_el = heading.find("a")
            if link_el and link_el.get("href"):
                full_url = urljoin(base_url, link_el["href"])
                if full_url.startswith(("http://", "https://")):
                    links.append(full_url)

    for tag in element.find_all("a", href=True):
        href = str(tag.get("href", "")).lower()
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if email and email not in emails:
                emails.append(email)
        elif href.startswith(("http://", "https://")):
            full_url = urljoin(base_url, tag["href"])
            if full_url not in links:
                links.append(full_url)

    if not name:
        return None

    for p in element.find_all("p"):
        description = (description or "") + " " + p.get_text(strip=True)
    if not description:
        description = element.get_text(separator=" ", strip=True)

    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    if description and email_pattern.search(description):
        for m in email_pattern.finditer(description):
            e = m.group(0)
            if e not in emails:
                emails.append(e)

    return {
        "name": (name or "")[:500],
        "links": links,
        "description": (description or "").strip()[:2000],
        "emails": emails,
    }


def _extract_clients_from_directory_layout(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """
    Extract clients from directory-style pages (GoodFirms, Clutch, etc.) where
    each listing has an h2/h3/h4 with company name + external link.
    """
    clients: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for heading in soup.find_all(["h2", "h3", "h4"]):
        link_el = heading.find("a", href=True)
        if not link_el:
            continue
        href = str(link_el.get("href", ""))
        if not href.startswith(("http://", "https://")):
            continue
        full_url = urljoin(base_url, href)
        netloc = (urlparse(full_url).netloc or "").lower()
        if "goodfirms.co" in netloc or "goodfirms.com" in netloc:
            continue
        name = link_el.get_text(strip=True) or heading.get_text(strip=True)
        if not name or len(name) < 2:
            continue
        key = (name.lower(), full_url)
        if key in seen:
            continue
        seen.add(key)
        links = [full_url]
        description = ""
        card = heading.parent
        for _ in range(10):
            if not card:
                break
            for a in card.find_all("a", href=True):
                h = str(a.get("href", ""))
                if h.startswith(("http://", "https://")):
                    u = urljoin(base_url, h)
                    net = (urlparse(u).netloc or "").lower()
                    if u not in links and "goodfirms" not in net:
                        links.append(u)
            for p in card.find_all("p", recursive=True):
                t = p.get_text(strip=True)
                if t and len(t) > 30:
                    description = t[:2000]
                    break
            if description or len(links) >= 2:
                break
            card = getattr(card, "parent", None)
        clients.append({
            "name": name[:500],
            "links": links[:5],
            "description": description,
            "emails": [],
        })
    return clients


def _extract_clients_from_html(html: str, base_url: str) -> list[dict]:
    """Extract client/company listings from HTML using common patterns."""
    soup = BeautifulSoup(html, "html.parser")
    clients: list[dict] = []
    for element in _find_client_elements(soup):
        client = _parse_client_element(element, base_url)
        if client and client.get("name"):
            clients.append(client)
    if not clients:
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = str(link["href"]).lower()
            if len(text) >= 3 and any(kw in href for kw in CLIENT_LISTING_KEYWORDS):
                full_url = urljoin(base_url, link["href"])
                if full_url.startswith(("http://", "https://")):
                    clients.append({
                        "name": text[:500],
                        "links": [full_url],
                        "description": "",
                        "emails": [],
                    })
    if not clients:
        clients = _extract_clients_from_directory_layout(soup, base_url)
    return clients


async def _parse_clients_via_llm(html: str) -> list[dict]:
    """Use LLM to extract structured client data from HTML."""
    content = html[:15000] if len(html) > 15000 else html
    prompt = CLIENT_PARSER_USER_PROMPT_TEMPLATE.format(html_content=content)
    try:
        llm_client = LLMFactory.get_client(
            provider_name="grok",
            model_name="grok-4-1-fast-reasoning",
        )
        response = await llm_client.generate_content(
            system_prompt=CLIENT_PARSER_SYSTEM_PROMPT,
            prompt=prompt,
        )
        response_text = (response or "").strip()
        json_str = _extract_json_array(response_text) or response_text
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)
        parsed = json.loads(json_str)
        if isinstance(parsed, list):
            result = []
            for item in parsed:
                if not isinstance(item, dict) or not item.get("name"):
                    continue
                links = []
                for key in ("link", "website"):
                    val = item.get(key)
                    if val and isinstance(val, str) and val.startswith(("http://", "https://")):
                        links.append(val)
                result.append({
                    "name": str(item.get("name", ""))[:500],
                    "links": links[:5],
                    "description": str(item.get("detail", ""))[:2000],
                    "emails": _parse_emails(item.get("emails")),
                })
            return result
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return []


async def scrape_clients_from_url(
    db: AsyncSession,
    url: str,
    use_discovery_when_no_email: bool = True,
    max_pages: int = 5,
    scrap_client_job_id: int | None = None,
) -> int:
    """
    Scrape client/company data from a website URL and save to CareerClient.
    When email is not found and use_discovery_when_no_email is True, uses
    website_discovery to fetch company info by name.
    When scrap_client_job_id is set, associates touched clients with that job.
    Returns count of clients created/updated.
    """
    normalized_url = normalize_url(url)
    if not normalized_url:
        return 0

    all_clients: list[dict] = []
    fetch_result = await _fetch_html_for_client_scrape(normalized_url)
    if not fetch_result:
        return 0
    html, final_url = fetch_result

    if scrap_client_job_id is not None:
        try:
            await ScraperHtmlStorage.persist_for_scrap_client_job(
                db, scrap_client_job_id, html, final_url
            )
        except Exception as e:
            logger.warning(
                "Could not persist client scrap HTML for job %s: %s",
                scrap_client_job_id,
                e,
            )

    clients = _extract_clients_from_html(html, final_url)
    if not clients:
        clients = await _parse_clients_via_llm(html)
    all_clients.extend(clients)

    if not _url_needs_playwright(normalized_url):
        crawler = WebsiteCrawler(max_pages=max_pages)

        async def _on_crawl_page(page_url: str, page_html: str) -> None:
            if scrap_client_job_id is None:
                return
            try:
                await ScraperHtmlStorage.persist_for_scrap_client_job(
                    db, scrap_client_job_id, page_html, page_url
                )
            except Exception as e:
                logger.warning(
                    "Could not persist crawled client HTML for job %s: %s",
                    scrap_client_job_id,
                    e,
                )

        pages = await crawler.crawl(
            normalized_url,
            on_page_html=_on_crawl_page if scrap_client_job_id is not None else None,
        )
        for page_url, page_html in pages[:max_pages - 1]:
            page_clients = _extract_clients_from_html(page_html, page_url)
            for c in page_clients:
                if c.get("name") and not any(
                    x.get("name") == c.get("name") and x.get("links") == c.get("links")
                    for x in all_clients
                ):
                    all_clients.append(c)

    seen_keys: set[tuple[str, str]] = set()
    saved_count = 0
    for client_data in all_clients:
        name = (client_data.get("name") or "").strip()
        if not name or len(name) < 2:
            continue
        links = client_data.get("links") or []
        primary_link = links[0] if links else None
        norm_link = normalize_url(primary_link) if primary_link else ""
        dedupe_key = (name.lower(), norm_link)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        emails = list(client_data.get("emails") or [])
        description = (client_data.get("description") or "").strip()
        root_domain = extract_root_domain(primary_link) if primary_link else None
        if not emails and root_domain and description:
            extracted = extract_emails_from_html(description)
            for e in extracted:
                if root_domain in e.split("@")[-1].lower():
                    emails.append(e)

        career_client = await get_or_create_career_client(
            db,
            name=name,
            link=primary_link,
            location=None,
            emails=emails,
            detail=description or None,
            size=None,
        )
        if not career_client:
            continue

        if scrap_client_job_id is not None:
            await update_career_client(
                db,
                career_client.id,
                {"scrap_client_job_id": scrap_client_job_id},
            )

        if use_discovery_when_no_email and not emails and name:
            discovery: DiscoveryResult = await discover_company_info(
                name, client_link=primary_link
            )
            if discovery.emails or discovery.website:
                update_data = {}
                if discovery.emails:
                    update_data["emails"] = discovery.emails
                if discovery.website:
                    update_data["official_website"] = discovery.website
                if update_data:
                    await update_career_client(db, career_client.id, update_data)

        saved_count += 1
        await db.commit()

    return saved_count
