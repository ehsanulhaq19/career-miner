"""Email validation using DNS MX records and SMTP verification."""

import asyncio
import logging
import smtplib
import socket

import dns.resolver

logger = logging.getLogger(__name__)

SMTP_TIMEOUT = 10
REJECT_CODES = (550, 551, 552, 553, 554)


def _extract_domain(email: str) -> str | None:
    """Extract domain part from email address."""
    if not email or "@" not in email:
        return None
    _, domain = email.rsplit("@", 1)
    return domain.strip().lower() if domain else None


def _get_mx_host(domain: str) -> str | None:
    """Get the primary MX host for the domain."""
    try:
        answers = dns.resolver.resolve(domain, "MX")
        sorted_mx = sorted(answers, key=lambda r: r.preference)
        return str(sorted_mx[0].exchange).rstrip(".")
    except Exception:
        return None


def _verify_email_smtp_sync(email: str) -> bool:
    """
    Verify email via SMTP RCPT TO. Returns True only if server accepts the address.
    Rejects on 550/551/552/553/554 (mailbox does not exist) or connection errors.
    """
    domain = _extract_domain(email)
    if not domain:
        return False
    mx_host = _get_mx_host(domain)
    if not mx_host:
        return False
    try:
        with smtplib.SMTP(timeout=SMTP_TIMEOUT) as smtp:
            smtp.connect(mx_host, 25)
            smtp.ehlo(socket.gethostname() or "localhost")
            smtp.mail("verify@careerminer.local")
            code, _ = smtp.rcpt(email)
            if code in REJECT_CODES:
                return False
            if code == 250:
                return True
            return False
    except (smtplib.SMTPException, socket.error, OSError, TimeoutError):
        return False


async def validate_email_smtp(email: str) -> bool:
    """Async wrapper for SMTP verification to avoid blocking the event loop."""
    return await asyncio.to_thread(_verify_email_smtp_sync, email)


def validate_email_mx(email: str) -> bool:
    """
    Validate email by checking if the domain has MX records.
    Returns True if domain has mail servers configured.
    """
    domain = _extract_domain(email)
    if not domain:
        return False
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return len(list(answers)) > 0
    except Exception:
        return False


async def validate_emails_smtp(emails: list[str]) -> list[str]:
    """
    Validate multiple emails via SMTP RCPT TO.
    Returns only emails that the mail server accepts as valid recipients.
    """
    valid: list[str] = []
    for email in emails:
        if await validate_email_smtp(email):
            valid.append(email)
    return valid
