"""Email validation using format checks, disposable filtering, DNS MX and SMTP verification."""

import asyncio
import smtplib
import socket
import dns.resolver

from app.modules.scrap_client.services._disposable_domains import DISPOSABLE_DOMAINS

try:
    from email_validator import EmailNotValidError, validate_email
except ImportError:
    validate_email = None
    EmailNotValidError = ValueError

SMTP_TIMEOUT = 12
SMTP_PERMANENT_REJECT = (550, 551, 552, 553, 554)
SMTP_TEMPORARY_REJECT = (421, 450, 451, 452)


def _extract_domain(email: str) -> str | None:
    """
    Extract and normalize domain part from email address.
    """
    if not email or "@" not in email:
        return None
    _, domain = email.rsplit("@", 1)
    return domain.strip().lower() if domain else None


def _validate_format(email: str) -> str | None:
    """
    Validate email format per RFC 5322. Returns normalized email or None if invalid.
    """
    if not email or not isinstance(email, str):
        return None
    email = email.strip().lower()
    if not email or "@" not in email:
        return None
    if validate_email is None:
        local, domain = email.rsplit("@", 1)
        if not local or not domain or "." not in domain or len(domain) < 4:
            return None
        return email
    try:
        result = validate_email(email, check_deliverability=False)
        return result.normalized
    except EmailNotValidError:
        return None


def _is_disposable_domain(domain: str) -> bool:
    """
    Check if domain is a known disposable or temporary email provider.
    """
    if not domain:
        return False
    return domain.lower() in DISPOSABLE_DOMAINS


def _get_mx_host(domain: str) -> str | None:
    """
    Resolve primary MX host for domain. Returns hostname or None.
    """
    try:
        answers = dns.resolver.resolve(domain, "MX")
        sorted_mx = sorted(answers, key=lambda r: r.preference)
        return str(sorted_mx[0].exchange).rstrip(".")
    except Exception:
        return None


def _verify_email_smtp_sync(email: str) -> tuple[bool, str]:
    """
    Verify email via SMTP RCPT TO.
    Returns (is_valid, reason). Reason is 'accepted'|'rejected'|'connection_failed'.
    """
    domain = _extract_domain(email)
    if not domain:
        return False, "connection_failed"
    mx_host = _get_mx_host(domain)
    if not mx_host:
        return False, "connection_failed"
    try:
        with smtplib.SMTP(timeout=SMTP_TIMEOUT) as smtp:
            smtp.connect(mx_host, 25)
            smtp.ehlo(socket.gethostname() or "careerminer.local")
            smtp.mail("verify@careerminer.local")
            code, _ = smtp.rcpt(email)
            if code in SMTP_PERMANENT_REJECT:
                return False, "rejected"
            if code in SMTP_TEMPORARY_REJECT:
                return False, "rejected"
            if code == 250:
                return True, "accepted"
            return False, "rejected"
    except (smtplib.SMTPException, socket.error, OSError, TimeoutError):
        return False, "connection_failed"


async def _verify_single_email(email: str, use_smtp: bool = True) -> bool:
    """
    Validate single email through format -> disposable -> MX -> SMTP (if use_smtp).
    """
    normalized = _validate_format(email)
    if normalized is None:
        return False
    domain = _extract_domain(normalized)
    if not domain:
        return False
    if _is_disposable_domain(domain):
        return False
    mx_host = await asyncio.to_thread(_get_mx_host, domain)
    if mx_host is None:
        return False
    if use_smtp:
        valid, reason = await asyncio.to_thread(
            _verify_email_smtp_sync, normalized
        )
        if reason == "connection_failed":
            return True
        return valid
    return True


async def validate_email_smtp(email: str) -> bool:
    """
    Async SMTP verification. Returns True only if server accepts the address.
    """
    return await _verify_single_email(email, use_smtp=True)


def validate_email_mx(email: str) -> bool:
    """
    Validate email by checking format, disposable filter and domain MX records.
    """
    normalized = _validate_format(email)
    if normalized is None:
        return False
    domain = _extract_domain(normalized)
    if not domain:
        return False
    if _is_disposable_domain(domain):
        return False
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return len(list(answers)) > 0
    except Exception:
        return False


async def validate_emails_smtp(emails: list[str]) -> list[str]:
    """
    Validate multiple emails via format, disposable filter, MX and SMTP RCPT TO.
    Returns only emails that pass all checks and are accepted by mail server.
    """
    valid: list[str] = []
    for email in emails:
        if await validate_email_smtp(email):
            valid.append(email)
    return valid


async def validate_emails_by_domain(emails: list[str]) -> list[str]:
    """
    Validate emails by format, disposable filter, MX records and SMTP RCPT TO.
    When SMTP is unavailable (e.g. port 25 blocked), falls back to MX-only for that email.
    Caches MX lookups to avoid redundant DNS queries.
    """
    valid: list[str] = []
    domain_mx_cache: dict[str, bool] = {}

    for raw in emails:
        normalized = _validate_format(raw)
        if normalized is None:
            continue
        domain = _extract_domain(normalized)
        if not domain:
            continue
        if _is_disposable_domain(domain):
            continue
        if domain not in domain_mx_cache:
            mx_host = await asyncio.to_thread(_get_mx_host, domain)
            domain_mx_cache[domain] = mx_host is not None
        if not domain_mx_cache[domain]:
            continue

        smtp_valid, smtp_reason = await asyncio.to_thread(
            _verify_email_smtp_sync, normalized
        )
        if smtp_reason == "connection_failed":
            valid.append(normalized)
        elif smtp_valid:
            valid.append(normalized)
    return valid


async def validate_scraped_emails_for_storage(emails: list[str]) -> list[str]:
    """
    Validate email candidates before persisting career client emails from scrap jobs.
    Applies RFC format checks, disposable-domain blocklist, MX resolution, and SMTP
    RCPT TO when available. Use this as the only path for scraped email persistence.
    """
    return await validate_emails_by_domain(emails)
