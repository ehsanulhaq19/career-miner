"""
Assign ownership of core domain rows to a user identified by email.

Sets ``created_by`` (and ``user_id`` for job applications) on every row in:

- career_clients, client_sites, career_jobs, job_applications,
  job_sites, scrap_client_jobs, scrap_jobs

Run from the backend directory::

    python -m app.modules.auth.commands.link_user_domain

Or non-interactive::

    python -m app.modules.auth.commands.link_user_domain --email user@example.com --yes
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import func, select, update

from app.database import async_session
from app.modules.auth.models import User
from app.modules.career_client.models import CareerClient, ClientSite
from app.modules.career_job.models import CareerJob
from app.modules.job_application.models import JobApplication
from app.modules.job_site.models import JobSite
from app.modules.scrap_client.models import ScrapClientJob
from app.modules.scrap_job.models import ScrapJob


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Link all domain table rows to the user with the given email.",
    )
    p.add_argument(
        "--email",
        "-e",
        default=None,
        help="User email (if omitted, you will be prompted)",
    )
    p.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    return p.parse_args(argv)


async def _get_user_by_email_ci(db, email: str) -> User | None:
    normalized = email.strip().lower()
    if not normalized:
        return None
    result = await db.execute(
        select(User).where(func.lower(User.email) == normalized)
    )
    return result.scalars().first()


async def link_user_domain_data(email: str, *, assume_yes: bool) -> int:
    """
    Update all listed models so ``created_by`` (and job_applications.user_id)
    point to the user with ``email``. Returns process exit code (0 ok, 1 error).
    """
    async with async_session() as db:
        user = await _get_user_by_email_ci(db, email)
        if user is None:
            print(f"No user found with email matching {email.strip()!r}.", file=sys.stderr)
            return 1

        uid = user.id
        tables_desc = (
            "career_clients, client_sites, career_jobs, job_applications, "
            "job_sites, scrap_client_jobs, scrap_jobs"
        )

        if not assume_yes:
            print(
                f"This will set ownership on ALL rows in:\n  {tables_desc}\n"
                f"to user id={uid} ({user.email}).\n"
                f"Type 'yes' to continue."
            )
            if input().strip().lower() != "yes":
                print("Aborted.")
                return 1

        job_app_result = await db.execute(
            update(JobApplication).values(user_id=uid, created_by=uid)
        )
        updates_meta: list[tuple[str, int | None]] = [
            ("job_applications", job_app_result.rowcount),
        ]
        for model in (
            CareerClient,
            ClientSite,
            CareerJob,
            JobSite,
            ScrapClientJob,
            ScrapJob,
        ):
            res = await db.execute(update(model).values(created_by=uid))
            updates_meta.append((model.__tablename__, res.rowcount))

        await db.commit()

    print(f"Linked all rows to user id={uid} ({user.email}). Row counts (may be -1 for some drivers):")
    for name, count in updates_meta:
        print(f"  {name}: {count}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    email = args.email
    if not email:
        email = input("User email: ").strip()
    if not email:
        print("Email is required.", file=sys.stderr)
        return 1
    return asyncio.run(link_user_domain_data(email, assume_yes=args.yes))


if __name__ == "__main__":
    raise SystemExit(main())
