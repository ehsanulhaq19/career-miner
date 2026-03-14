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
