"""Recruiter email pattern generator using company domain."""

RECRUITER_PREFIXES = [
    "hr",
    "jobs",
    "careers",
    "recruiting",
    "talent",
    "people",
    "recruitment",
    "hiring",
    "career",
    "humanresources",
    "resumes",
    "apply",
    "opportunities",
]

# Extended prefixes for email guessing when no emails found on website
EXTENDED_EMAIL_PREFIXES = [
    "info",
    "contact",
    "admin",
    "hello",
    "support",
    "office",
    "enquiries",
    "inquiry",
    "general",
] + RECRUITER_PREFIXES


def generate_recruiter_email_patterns(domain: str) -> list[str]:
    """
    Generate potential recruiter email addresses using company domain.
    Returns list of email strings like hr@example.com, jobs@example.com.
    """
    if not domain or not domain.strip():
        return []
    domain = domain.lower().strip()
    if "@" in domain or " " in domain:
        return []
    results: list[str] = []
    for prefix in RECRUITER_PREFIXES:
        email = f"{prefix}@{domain}"
        results.append(email)
    return results


def generate_extended_email_patterns(domain: str) -> list[str]:
    """
    Generate extended email patterns for guessing (info@, contact@, etc.).
    Used when no emails found on website or when website is guessed.
    """
    if not domain or not domain.strip():
        return []
    domain = domain.lower().strip()
    if "@" in domain or " " in domain:
        return []
    seen: set[str] = set()
    results: list[str] = []
    for prefix in EXTENDED_EMAIL_PREFIXES:
        email = f"{prefix}@{domain}"
        if email not in seen:
            seen.add(email)
            results.append(email)
    return results
