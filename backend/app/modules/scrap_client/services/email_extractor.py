"""Email extraction from HTML content."""

import re
from urllib.parse import unquote

PLACEHOLDER_EMAILS = {
    "example@example.com",
    "test@test.com",
    "email@example.com",
    "user@example.com",
    "info@example.com",
    "contact@example.com",
    "admin@example.com",
    "support@example.com",
    "noreply@example.com",
    "no-reply@example.com",
    "mail@example.com",
    "sentry@example.com",
    "placeholder@example.com",
    "your@email.com",
    "you@example.com",
}

EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)


def _normalize_email(raw: str) -> str:
    """Decode URL-encoded chars, strip whitespace, lowercase."""
    decoded = unquote(raw)
    return decoded.strip().lower()


def extract_emails_from_html(html: str) -> list[str]:
    """
    Extract email addresses from HTML using regex.
    Filters duplicates, placeholder emails, and normalizes (decodes %20 etc).
    """
    if not html:
        return []
    matches = EMAIL_PATTERN.findall(html)
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        email = _normalize_email(m)
        if not email or "@" not in email:
            continue
        normalized = email.replace(" ", "")
        if normalized in seen:
            continue
        if normalized in PLACEHOLDER_EMAILS:
            continue
        if "example.com" in normalized or "test.com" in normalized:
            continue
        if "..." in normalized or ".." in normalized:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def extract_emails_from_text(text: str) -> list[str]:
    """Extract email addresses from plain text."""
    if not text:
        return []
    return extract_emails_from_html(text)
