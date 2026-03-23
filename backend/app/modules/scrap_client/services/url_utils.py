"""URL normalization and domain extraction utilities."""

from urllib.parse import urljoin, urlparse


def normalize_url(url: str, base: str | None = None) -> str:
    """
    Normalize a URL by resolving relative paths and standardizing scheme.
    """
    if not url or not url.strip():
        return ""
    url = url.strip()
    if base:
        url = urljoin(base, url)
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if not netloc:
        return ""
    path = parsed.path.rstrip("/") or "/"
    result = f"{scheme}://{netloc}{path}"
    if parsed.query:
        result += "?" + parsed.query
    return result


def extract_root_domain(url: str) -> str | None:
    """
    Extract the root domain from a URL for email pattern generation.
    Returns e.g. 'example.com' from 'https://www.example.com/contact'.
    """
    if not url or not url.strip():
        return None
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if not netloc:
        return None
    if netloc.startswith("www."):
        netloc = netloc[4:]
    parts = netloc.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return netloc
