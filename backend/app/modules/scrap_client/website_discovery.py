"""Service for discovering official company websites and contact information via multiple strategies."""

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.modules.scrap_client.email_extractor import extract_emails_from_text
from app.modules.scrap_client.url_utils import normalize_url

logger = logging.getLogger(__name__)

WebSearchLogCallback = Callable[
    [str, str | None, dict[str, Any] | None, str],
    Awaitable[None],
]

DISCOVER_TIMEOUT_SECONDS = 60
HTTP_CONNECT_TIMEOUT = 5.0
HTTP_READ_TIMEOUT = 12.0

SEARCH_URL = "https://html.duckduckgo.com/html/"

SKIP_DOMAINS = {
    "duckduckgo.com", "google.com", "google.co", "facebook.com",
    "twitter.com", "x.com", "linkedin.com", "youtube.com",
    "instagram.com", "wikipedia.org", "crunchbase.com", "bloomberg.com",
    "reuters.com", "forbes.com", "medium.com", "github.com",
    "amazon.com", "ebay.com", "yelp.com", "trustpilot.com",
    "indeed.com", "glassdoor.com", "monster.com", "ziprecruiter.com",
    "jobstreet.com", "naukri.com", "seek.com", "reed.co.uk",
    "totaljobs.com", "cv-library.co.uk", "adzuna.com", "simplyhired.com",
    "stepstone.de", "xing.com", "kununu.com", "karriere.at",
}

COMPANY_TLDS = [
    ".com", ".co", ".io", ".net", ".org",
    ".co.uk", ".com.au", ".pk", ".edu.pk", ".edu",
    ".de", ".ch", ".at", ".fr", ".nl",
]

COMPANY_SUFFIXES = [
    r"\s+inc\.?$", r"\s+corp\.?$", r"\s+corporation$", r"\s+llc\.?$",
    r"\s+ltd\.?$", r"\s+limited$", r"\s+co\.?$", r"\s+company$",
    r"\s+group$", r"\s+holdings$", r"\s+technologies$", r"\s+tech$",
    r"\s+solutions$", r"\s+services$", r"\s+systems$", r"\s+software$",
    r"\s+ag$", r"\s+gmbh$", r"\s+s\.?a\.?$", r"\s+b\.?v\.?$",
]

URL_REGEX = re.compile(r"https?://\S+")


@dataclass
class DiscoveryResult:
    """Structured result from company information discovery containing website, emails, and metadata."""

    website: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    source: str = "none"


def _browser_headers() -> dict:
    """Return browser-like headers for HTTP requests."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
    }


def is_official_website_url(url: str | None) -> bool:
    """
    Check if URL appears to be an official company website (not job portal, LinkedIn, etc.).
    Use for CareerClient.link field - only use if it's an official site.
    """
    if not url or not url.strip():
        return False
    normalized = normalize_url(url)
    if not normalized:
        return False
    parsed = urlparse(normalized)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return not _is_skip_domain(domain)


def _clean_company_name_for_slugs(name: str) -> str:
    """Remove regional suffixes and clean for slug generation."""
    if not name or not name.strip():
        return ""
    raw = name.strip()
    raw = re.sub(r"\s*-\s*(PK|Pakistan|USA|US|UK|UAE)\s*$", "", raw, flags=re.IGNORECASE)
    return raw.strip()


def _company_name_to_slugs(name: str) -> list[str]:
    """Generate domain slug candidates from company name."""
    if not name or not name.strip():
        return []
    raw = _clean_company_name_for_slugs(name)
    if not raw:
        return []
    cleaned = raw
    for pattern in COMPANY_SUFFIXES:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip() or raw.strip()
    normalized = re.sub(r"[^a-z0-9\s-]", "", cleaned.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return []
    words = normalized.split()
    slugs: list[str] = []
    if words:
        slugs.append(words[0])
    no_spaces = "".join(w for w in words)
    if no_spaces and no_spaces not in slugs:
        slugs.append(no_spaces)
    hyphenated = "-".join(words)
    if hyphenated and hyphenated not in slugs:
        slugs.append(hyphenated)
    if len(words) >= 2:
        abbrev = "".join(w[0] for w in words if w)
        if len(abbrev) >= 2 and abbrev not in slugs:
            slugs.append(abbrev)
    known_abbrevs: dict[str, str] = {
        "lahore university of management sciences": "lums",
        "pwc": "pwc",
    }
    norm_lower = normalized
    if norm_lower in known_abbrevs and known_abbrevs[norm_lower] not in slugs:
        slugs.append(known_abbrevs[norm_lower])
    return slugs


def _generate_domain_candidates(company_name: str) -> list[str]:
    """Generate domain candidates to try."""
    slugs = _company_name_to_slugs(company_name)
    candidates: list[str] = []
    seen: set[str] = set()
    for slug in slugs:
        if len(slug) < 2:
            continue
        for tld in COMPANY_TLDS:
            domain = f"{slug}{tld}"
            if domain not in seen:
                seen.add(domain)
                candidates.append(f"https://www.{domain}")
                candidates.append(f"https://{domain}")
    return candidates[:30]


def _extract_url_from_duckduckgo_redirect(href: str) -> str | None:
    """Extract actual URL from DuckDuckGo redirect link."""
    if not href:
        return None
    if "uddg=" in href:
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        uddg = qs.get("uddg", [])
        if uddg:
            return unquote(uddg[0])
    return None


def _domain_relevance_score(domain: str, company_name: str) -> float:
    """Score how likely a domain is the official company site (0-1)."""
    domain_lower = domain.lower()
    if domain_lower.startswith("www."):
        domain_lower = domain_lower[4:]
    base = domain_lower.split(".")[0] if "." in domain_lower else domain_lower
    name_parts = re.sub(r"[^a-z0-9\s]", "", company_name.lower()).split()
    if not name_parts:
        return 0.0
    score = 0.0
    name_no_spaces = "".join(name_parts)
    if base == name_no_spaces:
        score += 0.5
    if name_parts[0] in base or base in name_no_spaces:
        score += 0.3
    if base == name_parts[0]:
        score += 0.2
    if domain_lower.endswith(".com"):
        score += 0.1
    return min(score, 1.0)


def _is_skip_domain(domain: str) -> bool:
    """Check if domain should be skipped."""
    d = domain.lower()
    if d.startswith("www."):
        d = d[4:]
    return any(d == s or d.endswith("." + s) for s in SKIP_DOMAINS)


def _extract_urls_from_text(text: str, company_name: str) -> list[tuple[str, float]]:
    """Extract and score URLs from free-form text by company name relevance."""
    if not text:
        return []
    matches = URL_REGEX.findall(text)
    results: list[tuple[str, float]] = []
    seen_domains: set[str] = set()
    for url_str in matches:
        url_str = url_str.rstrip(".,;:!?'\")>]}")
        normalized = normalize_url(url_str)
        if not normalized:
            continue
        parsed = urlparse(normalized)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if _is_skip_domain(domain) or domain in seen_domains:
            continue
        seen_domains.add(domain)
        score = _domain_relevance_score(domain, company_name)
        results.append((normalized, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def _filter_emails_by_domain_relevance(emails: list[str], company_name: str | None = None) -> list[str]:
    """Filter out emails from skip domains and optionally prioritize company-relevant domains."""
    filtered: list[str] = []
    seen: set[str] = set()
    for email in emails:
        lower = email.strip().lower()
        if lower in seen:
            continue
        domain = lower.split("@")[-1] if "@" in lower else ""
        if _is_skip_domain(domain):
            continue
        seen.add(lower)
        filtered.append(lower)
    return filtered


async def _verify_domain_exists(client: httpx.AsyncClient, url: str) -> bool:
    """Verify a URL exists with a quick HEAD request."""
    try:
        resp = await client.head(url, follow_redirects=True)
        return resp.status_code < 400
    except Exception:
        try:
            resp = await client.get(url, follow_redirects=True)
            return resp.status_code < 400
        except Exception:
            return False


async def _strategy_career_client_link(
    client_link: str | None,
    log_cb: WebSearchLogCallback | None = None,
) -> str | None:
    """Strategy: Use CareerClient.link if it's an official website (not job portal)."""
    if not client_link or not client_link.strip():
        return None
    if not is_official_website_url(client_link):
        if log_cb:
            await log_cb(
                "web_search_link_skipped",
                f"CareerClient link is job portal/social: {client_link[:80]}",
                {"source": "career_client_link", "link": client_link},
                "in_progress",
            )
        return None
    normalized = normalize_url(client_link)
    if normalized:
        if log_cb:
            await log_cb(
                "web_search_link_used",
                f"Using CareerClient link as official website: {normalized}",
                {"source": "career_client_link", "website": normalized},
                "completed",
            )
        return normalized
    return None


async def _strategy_gemini_web_search(
    company_name: str,
    log_cb: WebSearchLogCallback | None = None,
) -> DiscoveryResult:
    """Strategy: Use Gemini with Google Search grounding to find company website and contact information."""
    if log_cb:
        await log_cb(
            "gemini_search_start",
            f"Gemini web search for '{company_name}'",
            {"engine": "gemini", "company_name": company_name},
            "in_progress",
        )

    try:
        from app.modules.llm.service import DEFAULT_WEB_SEARCH_MODEL, DEFAULT_WEB_SEARCH_PROVIDER, LLMFactory
        llm_client = LLMFactory.get_client(DEFAULT_WEB_SEARCH_PROVIDER, DEFAULT_WEB_SEARCH_MODEL)
    except Exception as e:
        logger.warning("Gemini LLM client unavailable: %s", e)
        if log_cb:
            await log_cb(
                "gemini_search_unavailable",
                f"Gemini not configured: {e}",
                {"engine": "gemini", "error": str(e)},
                "error",
            )
        return DiscoveryResult(source="gemini_unavailable")

    query = (
        f'What is the official website URL and contact email addresses for the company "{company_name}"? '
        f'Include the main company website and any contact emails such as info@, hr@, careers@, '
        f'recruitment@, or general business emails. Also include phone numbers if available.'
    )

    try:
        response_text = await llm_client.web_search(query)
    except Exception as e:
        logger.warning("Gemini web search failed for '%s': %s", company_name, e)
        if log_cb:
            await log_cb(
                "gemini_search_error",
                f"AI search request failed: {e}",
                {"engine": "gemini", "error": str(e), "error_type": type(e).__name__},
                "error",
            )
        return DiscoveryResult(source="gemini_error")

    if log_cb:
        await log_cb(
            "gemini_search_response_received",
            f"AI returned {len(response_text)} chars response",
            {"engine": "gemini", "response_length": len(response_text)},
            "in_progress",
        )

    raw_emails = extract_emails_from_text(response_text)
    emails = _filter_emails_by_domain_relevance(raw_emails, company_name)
    scored_urls = _extract_urls_from_text(response_text, company_name)

    json_blocks = re.findall(r"\{[^{}]*\}", response_text, re.DOTALL)
    for block in json_blocks:
        try:
            parsed = json.loads(block)
            if isinstance(parsed.get("website"), str) and parsed["website"].strip():
                website_from_json = normalize_url(parsed["website"].strip())
                if website_from_json:
                    p = urlparse(website_from_json)
                    d = p.netloc.lower().replace("www.", "")
                    if not _is_skip_domain(d):
                        scored_urls.insert(0, (website_from_json, 1.0))
            if isinstance(parsed.get("emails"), list):
                for e in parsed["emails"]:
                    e_str = str(e).strip().lower()
                    if e_str and "@" in e_str and e_str not in emails:
                        emails.append(e_str)
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    best_website = scored_urls[0][0] if scored_urls else None
    phone_pattern = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
    phones = [p.strip() for p in phone_pattern.findall(response_text)][:5]

    result = DiscoveryResult(
        website=best_website,
        emails=emails[:20],
        phones=phones,
        source="gemini_web_search",
    )

    if log_cb:
        await log_cb(
            "gemini_search_complete",
            f"AI found: website={result.website or 'none'}, {len(result.emails)} emails",
            {
                "engine": "gemini",
                "website": result.website,
                "emails": result.emails,
                "phones": result.phones,
            },
            "completed" if result.website or result.emails else "in_progress",
        )

    return result


async def _strategy_direct_guess(
    client: httpx.AsyncClient,
    company_name: str,
    log_cb: WebSearchLogCallback | None = None,
) -> str | None:
    """Strategy: Guess likely domains from company name and verify they exist."""
    if log_cb:
        await log_cb(
            "web_search_direct_guess_start",
            f"Direct domain guess for '{company_name}'",
            {"engine": "direct_guess", "company_name": company_name},
            "in_progress",
        )
    candidates = _generate_domain_candidates(company_name)
    for url in candidates:
        try:
            normalized = normalize_url(url)
            if not normalized:
                continue
            parsed = urlparse(normalized)
            domain = parsed.netloc.lower()
            if _is_skip_domain(domain):
                continue
            if await _verify_domain_exists(client, normalized):
                if log_cb:
                    await log_cb(
                        "web_search_direct_guess_success",
                        f"Verified domain: {normalized}",
                        {"engine": "direct_guess", "website": normalized},
                        "completed",
                    )
                return normalized
        except Exception:
            pass
    if log_cb:
        await log_cb(
            "web_search_direct_guess_no_results",
            "No valid domain from direct guess",
            {"engine": "direct_guess"},
            "error",
        )
    return None


async def _strategy_duckduckgo_search(
    client: httpx.AsyncClient,
    company_name: str,
    log_cb: WebSearchLogCallback | None = None,
) -> str | None:
    """Strategy: Search DuckDuckGo HTML endpoint with multiple query variations."""
    if log_cb:
        await log_cb(
            "web_search_duckduckgo_start",
            f"DuckDuckGo search for '{company_name}'",
            {"engine": "duckduckgo", "company_name": company_name},
            "in_progress",
        )
    queries = [
        f'"{company_name}" official website',
        f"{company_name} company website",
        f"{company_name} official site",
        f"{company_name} contact",
        f"{company_name} .com",
    ]
    all_results: list[tuple[str, float]] = []
    seen_domains: set[str] = set()

    for query in queries:
        try:
            encoded = quote_plus(query)
            url = f"{SEARCH_URL}?q={encoded}"
            if log_cb:
                await log_cb(
                    "web_search_duckduckgo_query",
                    f"Query: '{query}'",
                    {"engine": "duckduckgo", "query": query},
                    "in_progress",
                )
            response = await client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            links = soup.find_all("a", href=True)
            for a in links:
                href = a.get("href", "")
                if "uddg=" not in href and "duckduckgo.com/l/" not in href:
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
                if domain in seen_domains or _is_skip_domain(domain):
                    continue
                seen_domains.add(domain)
                score = _domain_relevance_score(domain, company_name)
                all_results.append((normalized, score))

            if all_results:
                break
            await asyncio.sleep(0.5)
        except Exception as e:
            if log_cb:
                await log_cb(
                    "web_search_duckduckgo_error",
                    str(e),
                    {"engine": "duckduckgo", "query": query, "error": str(e)},
                    "error",
                )
            continue

    if not all_results:
        if log_cb:
            await log_cb(
                "web_search_duckduckgo_no_results",
                "No results from DuckDuckGo",
                {"engine": "duckduckgo"},
                "error",
            )
        return None

    all_results.sort(key=lambda x: x[1], reverse=True)
    best_url = all_results[0][0]
    if log_cb:
        await log_cb(
            "web_search_duckduckgo_success",
            f"Found: {best_url}",
            {"engine": "duckduckgo", "website": best_url},
            "completed",
        )
    return best_url


async def _discover_impl(
    company_name: str,
    client_link: str | None = None,
    log_cb: WebSearchLogCallback | None = None,
) -> DiscoveryResult:
    """
    Internal orchestrator that tries discovery strategies in priority order:
    0. CareerClient.link (if it's an official website)
    1. Gemini web search with Google Search grounding (first attempt)
    2. DuckDuckGo HTML search (second attempt)
    3. Direct domain guess and email guessing (third attempt)
    """
    if not company_name or not company_name.strip():
        if log_cb:
            await log_cb("web_search_error", "No company name provided", None, "error")
        return DiscoveryResult(source="no_company_name")

    name = company_name.strip()
    if log_cb:
        await log_cb(
            "web_search_start",
            f"Website discovery for '{name}'",
            {"company_name": name},
            "in_progress",
        )

    result = await _strategy_career_client_link(client_link, log_cb=log_cb)
    if result:
        return DiscoveryResult(website=result, source="career_client_link")

    gemini_result = await _strategy_gemini_web_search(name, log_cb=log_cb)
    if gemini_result.website or gemini_result.emails:
        return gemini_result

    settings = get_settings()
    timeout = httpx.Timeout(HTTP_READ_TIMEOUT, connect=HTTP_CONNECT_TIMEOUT)
    client_kwargs: dict = {
        "timeout": timeout,
        "follow_redirects": True,
        "headers": _browser_headers(),
    }
    if settings.SCRAP_HTTP_PROXY:
        client_kwargs["proxy"] = settings.SCRAP_HTTP_PROXY

    async with httpx.AsyncClient(**client_kwargs) as client:
        website = await _strategy_duckduckgo_search(client, name, log_cb=log_cb)
        if website:
            return DiscoveryResult(website=website, source="duckduckgo")

        website = await _strategy_direct_guess(client, name, log_cb=log_cb)
        if website:
            return DiscoveryResult(website=website, source="direct_guess")

    if log_cb:
        await log_cb(
            "web_search_failed",
            f"No website found for '{name}'",
            {"company_name": name},
            "error",
        )
    return DiscoveryResult(source="not_found")


async def discover_company_info(
    company_name: str,
    client_link: str | None = None,
    log_cb: WebSearchLogCallback | None = None,
) -> DiscoveryResult:
    """
    Discover official company website and contact information.
    Tries strategies in order: CareerClient link, Gemini web search, DuckDuckGo, domain/email guessing.
    Returns a DiscoveryResult with website URL, emails, phone numbers, and source strategy.
    """
    try:
        return await asyncio.wait_for(
            _discover_impl(company_name, client_link=client_link, log_cb=log_cb),
            timeout=DISCOVER_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("Website discovery timed out for '%s'", company_name)
        if log_cb:
            await log_cb(
                "web_search_timeout",
                f"Timed out after {DISCOVER_TIMEOUT_SECONDS}s",
                {"company_name": company_name},
                "error",
            )
        return DiscoveryResult(source="timeout")
    except Exception as e:
        logger.exception("Website discovery failed for '%s': %s", company_name, e)
        if log_cb:
            try:
                await log_cb(
                    "web_search_error",
                    str(e),
                    {"company_name": company_name, "error": str(e), "error_type": type(e).__name__},
                    "error",
                )
            except Exception as log_err:
                logger.warning("Could not log discovery error: %s", log_err)
        return DiscoveryResult(source="error")


def get_domain_candidates_for_guessing(company_name: str) -> list[str]:
    """
    Get list of domain candidates for email guessing when website not found.
    Returns root domains (e.g. example.com) that can be verified.
    """
    from app.modules.scrap_client.url_utils import extract_root_domain

    candidates: list[str] = []
    seen: set[str] = set()
    for url in _generate_domain_candidates(company_name):
        root = extract_root_domain(url)
        if root and root not in seen and not _is_skip_domain(root):
            seen.add(root)
            candidates.append(root)
    return candidates[:15]


async def verify_domain_and_get_website(domain: str) -> str | None:
    """
    Verify a domain exists (website reachable) and return normalized URL.
    Used when guessing domains for email discovery without known website.
    """
    if not domain or _is_skip_domain(domain):
        return None
    for prefix in ("https://www.", "https://"):
        url = f"{prefix}{domain}"
        normalized = normalize_url(url)
        if normalized:
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(5.0),
                    follow_redirects=True,
                    headers=_browser_headers(),
                ) as client:
                    resp = await client.head(normalized)
                    if resp.status_code < 400:
                        return normalized
            except Exception:
                try:
                    async with httpx.AsyncClient(
                        timeout=httpx.Timeout(5.0),
                        follow_redirects=True,
                        headers=_browser_headers(),
                    ) as client:
                        resp = await client.get(normalized)
                        if resp.status_code < 400:
                            return normalized
                except Exception:
                    pass
    return None
