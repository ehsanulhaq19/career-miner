"""Discover company profile fields via DuckDuckGo search, page fetches, and Grok structured extraction."""

import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.modules.scrap_client.services.url_utils import extract_root_domain, normalize_url
from app.modules.scrap_client.services.website_discovery import (
    WebSearchLogCallback,
    _domain_relevance_score,
    _duckduckgo_html_headers,
    _extract_url_from_duckduckgo_redirect,
    _is_skip_domain,
)

logger = logging.getLogger(__name__)

MIN_DETAIL_CHARS = 80
MIN_DETAIL_CHARS_RELAXED = 45
SEARCH_URL = "https://html.duckduckgo.com/html/"
HTTP_CONNECT_TIMEOUT = 5.0
HTTP_READ_TIMEOUT = 12.0
DDG_QUERY_MAX_ATTEMPTS = 3
MAX_STORED_DETAIL_LEN = 16000
MAX_STORED_LOCATION_LEN = 500
MAX_STORED_HEADCOUNT = 9_999_999
MAX_FETCH_URLS = 6
MAX_CHARS_PER_PAGE = 12_000
MAX_TOTAL_GROK_CONTEXT = 48_000
GROK_DETAIL_PROVIDER = "grok"
GROK_DETAIL_MODEL = "grok-4-1-fast-reasoning"
FETCH_CONCURRENCY = 3

COMPANY_PROFILE_GROK_SYSTEM = """You are a precise research assistant. You receive plain text extracted from web pages \
obtained through public search. Your job is to produce a structured company profile using only information that is \
supported by that text (you may combine facts stated across sources). Do not invent facts. If the text is ambiguous \
or insufficient, use empty strings or null for size. For size, return only an integer employee headcount estimate or null; \
never return prose or category labels in the size field. Respond with ONLY valid JSON, no markdown."""


@dataclass
class CompanyProfileResult:
    """Structured company profile fields from discovery pipelines."""

    detail: str | None = None
    location: str | None = None
    size: str | None = None
    source: str = "none"


def clip_detail_for_storage(text: str | None) -> str | None:
    """Trim company detail text to a length safe for typical database text columns."""
    if not text or not str(text).strip():
        return None
    s = str(text).strip()
    if len(s) <= MAX_STORED_DETAIL_LEN:
        return s
    return s[: MAX_STORED_DETAIL_LEN - 1] + "\u2026"


def clip_location_for_storage(text: str | None) -> str | None:
    """Trim location to match career_clients.location String length expectations."""
    if not text or not str(text).strip():
        return None
    s = str(text).strip()
    if len(s) <= MAX_STORED_LOCATION_LEN:
        return s
    return s[: MAX_STORED_LOCATION_LEN - 1] + "\u2026"


def parse_size_headcount_for_storage(size_raw: str | int | None) -> int | None:
    """
    Derive a single non-negative headcount integer for career_clients.size.
    Does not preserve prose categories; extracts numbers from model output only.
    """
    if size_raw is None:
        return None
    if isinstance(size_raw, bool):
        return None
    if isinstance(size_raw, int):
        v = int(size_raw)
        if v < 0:
            return None
        return min(v, MAX_STORED_HEADCOUNT)
    s = str(size_raw).strip()
    if not s:
        return None
    m = re.match(r"^\s*(\d{1,3}(?:,\d{3})*|\d+)\s*$", s)
    if m:
        try:
            v = int(m.group(1).replace(",", ""))
            return min(max(v, 0), MAX_STORED_HEADCOUNT)
        except ValueError:
            pass
    best: int | None = None
    for part in re.finditer(r"\d{1,3}(?:,\d{3})+|\d{4,}", s):
        try:
            v = int(part.group(0).replace(",", ""))
            if best is None or v > best:
                best = v
        except ValueError:
            continue
    if best is not None:
        return min(best, MAX_STORED_HEADCOUNT)
    for part in re.finditer(r"\b(\d{2,3})\b", s):
        try:
            v = int(part.group(1))
            if v >= 10 and (best is None or v > best):
                best = v
        except ValueError:
            continue
    if best is None:
        return None
    return min(best, MAX_STORED_HEADCOUNT)


def _build_profile_ddg_queries(
    company_name: str,
    official_website: str | None,
) -> list[str]:
    """
    Build DuckDuckGo query strings. When no website is known, queries rely on the
    company name only (plus generic context terms). When a website exists, add
    disambiguating queries that include the hostname or domain.
    """
    name = str(company_name).strip()
    if not name:
        return []
    queries: list[str] = []
    normalized = (
        normalize_url(official_website.strip())
        if official_website and str(official_website).strip()
        else ""
    )
    if normalized:
        parsed = urlparse(normalized)
        host = (parsed.netloc or "").lower()
        dom = extract_root_domain(normalized)
        if dom:
            queries.append(f"{name} {dom}")
        if host:
            queries.append(f'"{name}" {host} company')
    queries.extend(
        [
            f"{name} company what they do",
            f'"{name}" about company business',
            f"{name} company overview",
            f"{name} wikipedia",
            f"{name} headquarters industry",
        ]
    )
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            out.append(q)
    return out


def _browser_headers_for_page_fetch(target_url: str) -> dict:
    """Browser-like headers for fetching third-party pages (aligned with website crawler pattern)."""
    parsed = urlparse(target_url)
    netloc = parsed.netloc or ""
    scheme = parsed.scheme or "https"
    origin = f"{scheme}://{netloc}" if netloc else "https://duckduckgo.com"
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": origin,
    }


def _merge_snippets_from_soup(soup: BeautifulSoup) -> str:
    """Extract visible snippet text from DuckDuckGo HTML result markup."""
    parts: list[str] = []
    selectors = (
        ".result__snippet",
        ".web-result__description",
        ".result-snippet",
    )
    for sel in selectors:
        for el in soup.select(sel):
            text = el.get_text(separator=" ", strip=True)
            if text and len(text) > 15:
                parts.append(text)
    if not parts:
        for a in soup.find_all("a", class_=re.compile(r"result__a", re.I)):
            nxt = a.find_next_sibling()
            if nxt:
                text = nxt.get_text(separator=" ", strip=True)
                if text and len(text) > 15:
                    parts.append(text)
    if not parts:
        return ""
    seen: set[str] = set()
    unique: list[str] = []
    for p in parts:
        key = p[:120]
        if key not in seen:
            seen.add(key)
            unique.append(p)
    merged = " ".join(unique[:6])
    return merged.strip()[:8000]


def _urls_from_ddg_soup(
    soup: BeautifulSoup,
    company_name: str,
    limit: int,
) -> list[str]:
    """Collect scored outbound URLs from a DuckDuckGo HTML results page."""
    scored: list[tuple[str, float]] = []
    seen_domains: set[str] = set()
    for a in soup.find_all("a", href=True):
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
        scored.append((normalized, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [u for u, _ in scored[:limit]]


async def _duckduckgo_get_html(
    client: httpx.AsyncClient,
    company_name: str,
    query: str,
    log_cb: WebSearchLogCallback | None,
) -> BeautifulSoup | None:
    """Fetch one DuckDuckGo HTML results page and return parsed soup, or None."""
    url = f"{SEARCH_URL}?q={quote_plus(query)}"
    settings = get_settings()
    response: httpx.Response | None = None
    for attempt in range(DDG_QUERY_MAX_ATTEMPTS):
        await asyncio.sleep(
            random.uniform(
                settings.CRAWL_DELAY_MIN_SECONDS,
                settings.CRAWL_DELAY_MAX_SECONDS,
            )
        )
        try:
            response = await client.get(url, headers=_duckduckgo_html_headers())
            if response.status_code == 403:
                if attempt < DDG_QUERY_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(
                        (2**attempt) * random.uniform(0.8, 1.2)
                    )
                    continue
            response.raise_for_status()
            break
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403 and attempt < DDG_QUERY_MAX_ATTEMPTS - 1:
                await asyncio.sleep(
                    (2**attempt) * random.uniform(0.8, 1.2)
                )
                continue
            logger.warning("DuckDuckGo request failed for '%s': %s", company_name, e)
            if log_cb:
                await log_cb(
                    "company_details_ddg_error",
                    str(e),
                    {
                        "engine": "duckduckgo",
                        "query": query,
                        "error": str(e),
                    },
                    "error",
                )
            return None
        except Exception as e:
            logger.warning("DuckDuckGo request failed for '%s': %s", company_name, e)
            if log_cb:
                await log_cb(
                    "company_details_ddg_error",
                    str(e),
                    {"engine": "duckduckgo", "query": query, "error": str(e)},
                    "error",
                )
            return None
    if response is None:
        return None
    try:
        return BeautifulSoup(response.text, "lxml")
    except Exception as e:
        logger.warning("DuckDuckGo parse failed for '%s': %s", company_name, e)
        return None


async def _discover_urls_via_duckduckgo(
    client: httpx.AsyncClient,
    company_name: str,
    queries: list[str],
    log_cb: WebSearchLogCallback | None,
) -> list[str]:
    """Run DuckDuckGo HTML searches until result URLs are found."""
    if not queries:
        return []
    if log_cb:
        await log_cb(
            "company_details_ddg_urls_start",
            f"DuckDuckGo URL discovery for '{company_name}'",
            {"engine": "duckduckgo", "company_name": company_name},
            "in_progress",
        )
    for query in queries:
        if log_cb:
            await log_cb(
                "company_details_ddg_query",
                f"Query: '{query}'",
                {"engine": "duckduckgo", "query": query},
                "in_progress",
            )
        soup = await _duckduckgo_get_html(client, company_name, query, log_cb)
        if soup is None:
            continue
        urls = _urls_from_ddg_soup(soup, company_name, MAX_FETCH_URLS)
        if urls:
            if log_cb:
                await log_cb(
                    "company_details_ddg_urls_found",
                    f"Found {len(urls)} candidate URLs",
                    {"engine": "duckduckgo", "query": query, "urls": urls},
                    "completed",
                )
            return urls
    if log_cb:
        await log_cb(
            "company_details_ddg_no_urls",
            "No result URLs from DuckDuckGo",
            {"engine": "duckduckgo"},
            "in_progress",
        )
    return []


async def _fetch_snippets_duckduckgo(
    client: httpx.AsyncClient,
    company_name: str,
    log_cb: WebSearchLogCallback | None,
    queries: list[str],
    min_chars: int,
) -> str | None:
    """Run DuckDuckGo HTML searches and combine result snippets into one text blob."""
    if not queries:
        return None
    if log_cb:
        await log_cb(
            "company_details_ddg_snippets_start",
            f"DuckDuckGo snippets for '{company_name}' ({len(queries)} queries)",
            {"engine": "duckduckgo", "company_name": company_name},
            "in_progress",
        )
    for query in queries:
        soup = await _duckduckgo_get_html(client, company_name, query, log_cb)
        if soup is None:
            continue
        try:
            merged = _merge_snippets_from_soup(soup)
            if merged and len(merged) >= min_chars:
                if log_cb:
                    await log_cb(
                        "company_details_ddg_success",
                        f"Collected {len(merged)} chars from DuckDuckGo snippets",
                        {"engine": "duckduckgo", "query": query, "min_chars": min_chars},
                        "completed",
                    )
                return merged
        except Exception as e:
            logger.warning("DuckDuckGo snippet parse failed for '%s': %s", company_name, e)
    if log_cb:
        await log_cb(
            "company_details_ddg_insufficient",
            "DuckDuckGo snippets missing or below threshold",
            {"engine": "duckduckgo", "min_chars": min_chars},
            "in_progress",
        )
    return None


async def _fetch_page_text(
    client: httpx.AsyncClient,
    page_url: str,
) -> tuple[str, str | None]:
    """Fetch a URL and return (url, plain text) or (url, None) on failure."""
    try:
        r = await client.get(page_url, headers=_browser_headers_for_page_fetch(page_url))
        r.raise_for_status()
        ctype = (r.headers.get("content-type") or "").lower()
        if "text/html" not in ctype and "text/plain" not in ctype:
            return page_url, None
        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [ln for ln in (ln.strip() for ln in text.splitlines()) if ln]
        blob = "\n".join(lines)
        if len(blob) > MAX_CHARS_PER_PAGE:
            blob = blob[: MAX_CHARS_PER_PAGE - 1] + "\u2026"
        if len(blob) < 80:
            return page_url, None
        return page_url, blob
    except Exception:
        return page_url, None


async def _gather_page_texts(
    client: httpx.AsyncClient,
    urls: list[str],
) -> list[tuple[str, str]]:
    """Fetch multiple URLs with bounded concurrency."""
    sem = asyncio.Semaphore(FETCH_CONCURRENCY)
    results: list[tuple[str, str]] = []

    async def one(u: str) -> None:
        async with sem:
            url_key, text = await _fetch_page_text(client, u)
            if text:
                results.append((url_key, text))

    await asyncio.gather(*[one(u) for u in urls])
    return results


def _parse_profile_json_from_text(text: str) -> CompanyProfileResult | None:
    """Parse JSON object with detail, location, size from model output."""
    if not text or not text.strip():
        return None
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if fence:
        raw = fence.group(1).strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    detail = data.get("detail")
    loc = data.get("location")
    size = data.get("size")
    if isinstance(size, bool):
        s_str = ""
    elif isinstance(size, int):
        s_str = str(size)
    elif isinstance(size, float):
        s_str = str(int(round(size)))
    elif size is not None:
        s_str = str(size).strip()
    else:
        s_str = ""
    d_str = str(detail).strip() if detail is not None else ""
    l_str = str(loc).strip() if loc is not None else ""
    if not d_str and not l_str and not s_str:
        return None
    return CompanyProfileResult(
        detail=d_str or None,
        location=l_str or None,
        size=s_str or None,
        source="grok",
    )


def _extract_profile_from_llm_response(response_text: str) -> CompanyProfileResult | None:
    """Parse profile from Grok response using shallow JSON blocks then greedy JSON."""
    if not response_text or not response_text.strip():
        return None
    best_detail = ""
    best_loc = ""
    best_size = ""
    json_blocks = re.findall(r"\{[^{}]*\}", response_text, re.DOTALL)
    for block in json_blocks:
        try:
            parsed = json.loads(block)
            if not isinstance(parsed, dict):
                continue
            d = parsed.get("detail")
            if isinstance(d, str) and len(d.strip()) > len(best_detail):
                best_detail = d.strip()
            loc = parsed.get("location")
            if isinstance(loc, str) and len(loc.strip()) > len(best_loc):
                best_loc = loc.strip()
            sz = parsed.get("size")
            if isinstance(sz, bool):
                sz_text = ""
            elif isinstance(sz, int):
                sz_text = str(sz)
            elif isinstance(sz, float):
                sz_text = str(int(round(sz)))
            elif isinstance(sz, str):
                sz_text = sz.strip()
            else:
                sz_text = ""
            if sz_text and len(sz_text) > len(best_size):
                best_size = sz_text
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
    greedy = _parse_profile_json_from_text(response_text)
    if greedy:
        if len((greedy.detail or "")) > len(best_detail):
            best_detail = (greedy.detail or "").strip()
        if len((greedy.location or "")) > len(best_loc):
            best_loc = (greedy.location or "").strip()
        if len((greedy.size or "")) > len(best_size):
            best_size = (greedy.size or "").strip()
    if not best_detail and not best_loc and not best_size:
        return None
    return CompanyProfileResult(
        detail=best_detail or None,
        location=best_loc or None,
        size=best_size or None,
        source="grok",
    )


async def _grok_synthesize_profile(
    company_name: str,
    official_website: str | None,
    sources: list[tuple[str, str]],
    log_cb: WebSearchLogCallback | None,
) -> CompanyProfileResult:
    """Use Grok generate_content to derive structured fields from fetched web text."""
    if not sources:
        return CompanyProfileResult(source="grok_no_input")
    if log_cb:
        await log_cb(
            "company_profile_grok_start",
            f"Grok synthesis for '{company_name}' ({len(sources)} sources)",
            {"engine": "grok", "company_name": company_name},
            "in_progress",
        )
    try:
        from app.modules.llm.service import LLMFactory

        llm = LLMFactory.get_client(GROK_DETAIL_PROVIDER, GROK_DETAIL_MODEL)
    except Exception as e:
        logger.warning("Grok client unavailable for company profile: %s", e)
        if log_cb:
            await log_cb(
                "company_profile_grok_unavailable",
                str(e),
                {"engine": "grok", "error": str(e)},
                "error",
            )
        return CompanyProfileResult(source="grok_unavailable")
    parts: list[str] = []
    for url, text in sources:
        parts.append(f"--- SOURCE: {url} ---\n{text}")
    bundle = "\n\n".join(parts)
    if len(bundle) > MAX_TOTAL_GROK_CONTEXT:
        bundle = bundle[: MAX_TOTAL_GROK_CONTEXT - 1] + "\u2026"
    hint = ""
    if official_website and str(official_website).strip():
        hint = f'The organization\'s known website may be "{official_website.strip()}". Prefer facts consistent with this entity.\n\n'
    user_prompt = (
        f'Company name: "{company_name}"\n\n'
        f"{hint}"
        "Below is plain text extracted from web pages (from a public web search). "
        "Use only this material to fill the JSON fields.\n\n"
        f"{bundle}\n\n"
        "Return ONLY valid JSON with keys detail (string, 2-5 sentences), "
        "location (string, headquarters city and country or empty), "
        "size (integer approximate employee headcount or null). "
        'Shape: {"detail":"...","location":"...","size":5000}'
    )
    try:
        raw = await llm.generate_content(COMPANY_PROFILE_GROK_SYSTEM, user_prompt)
    except Exception as e:
        logger.warning("Grok generate_content failed for company profile '%s': %s", company_name, e)
        if log_cb:
            await log_cb(
                "company_profile_grok_error",
                str(e),
                {"engine": "grok", "error": str(e), "error_type": type(e).__name__},
                "error",
            )
        return CompanyProfileResult(source="grok_error")
    if log_cb:
        await log_cb(
            "company_profile_grok_response",
            f"Grok returned {len(raw or '')} chars",
            {"engine": "grok", "response_length": len(raw or "")},
            "in_progress",
        )
    parsed = _extract_profile_from_llm_response(raw or "")
    if not parsed:
        if log_cb:
            await log_cb(
                "company_profile_grok_parse_fail",
                "Could not parse JSON from Grok response",
                {"engine": "grok"},
                "error",
            )
        return CompanyProfileResult(source="grok_parse_failed")
    if log_cb:
        await log_cb(
            "company_profile_grok_complete",
            (
                f"detail={'yes' if parsed.detail else 'no'}, "
                f"location={parsed.location or 'none'}, size={parsed.size or 'none'}"
            ),
            {
                "engine": "grok",
                "has_detail": bool(parsed.detail),
                "has_location": bool(parsed.location),
                "has_size": bool(parsed.size),
            },
            "completed",
        )
    return parsed


def _dedupe_urls_keep_order(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


async def discover_company_profile(
    company_name: str,
    official_website: str | None = None,
    log_cb: WebSearchLogCallback | None = None,
) -> CompanyProfileResult:
    """
    Resolve company description and optional location and size.
    Uses DuckDuckGo HTML search to find pages, fetches plain text from result URLs,
    then Grok (generate_content) to produce structured fields. Falls back to
    DuckDuckGo snippets and optional relaxed snippet pass when URLs or Grok fail.
    """
    if not company_name or not str(company_name).strip():
        return CompanyProfileResult(source="no_company_name")

    name = str(company_name).strip()
    settings = get_settings()
    timeout = httpx.Timeout(HTTP_READ_TIMEOUT, connect=HTTP_CONNECT_TIMEOUT)
    ddg_client_kwargs: dict = {
        "timeout": timeout,
        "follow_redirects": True,
        "headers": _duckduckgo_html_headers(),
    }
    fetch_client_kwargs: dict = {
        "timeout": timeout,
        "follow_redirects": True,
    }
    if settings.SCRAP_HTTP_PROXY:
        ddg_client_kwargs["proxy"] = settings.SCRAP_HTTP_PROXY
        fetch_client_kwargs["proxy"] = settings.SCRAP_HTTP_PROXY

    primary_queries = _build_profile_ddg_queries(name, official_website)
    seed_urls: list[str] = []
    nu = (
        normalize_url(official_website.strip())
        if official_website and str(official_website).strip()
        else ""
    )
    if nu:
        seed_urls.append(nu)

    async with httpx.AsyncClient(**ddg_client_kwargs) as ddg_client:
        discovered = await _discover_urls_via_duckduckgo(
            ddg_client, name, primary_queries, log_cb
        )
    urls = _dedupe_urls_keep_order(seed_urls + discovered)

    sources: list[tuple[str, str]] = []
    async with httpx.AsyncClient(**fetch_client_kwargs) as fetch_client:
        sources = await _gather_page_texts(fetch_client, urls)

    if not sources:
        async with httpx.AsyncClient(**ddg_client_kwargs) as ddg_client:
            snippet = await _fetch_snippets_duckduckgo(
                ddg_client, name, log_cb, primary_queries, MIN_DETAIL_CHARS
            )
            if snippet:
                sources = [("duckduckgo_snippets", snippet)]

    if sources:
        grok_res = await _grok_synthesize_profile(name, official_website, sources, log_cb)
        if grok_res.detail or grok_res.location or grok_res.size:
            return grok_res
        if (
            len(sources) == 1
            and sources[0][0] == "duckduckgo_snippets"
            and sources[0][1]
        ):
            return CompanyProfileResult(detail=sources[0][1], source="duckduckgo")

    async with httpx.AsyncClient(**ddg_client_kwargs) as ddg_client:
        ddg_relaxed = await _fetch_snippets_duckduckgo(
            ddg_client,
            name,
            log_cb,
            _build_profile_ddg_queries(name, None),
            MIN_DETAIL_CHARS_RELAXED,
        )
        if ddg_relaxed:
            return CompanyProfileResult(detail=ddg_relaxed, source="duckduckgo_relaxed")

    return CompanyProfileResult(source="not_found")
