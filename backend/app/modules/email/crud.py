from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.email.models import EmailLog


async def create_email_log(db: AsyncSession, data: dict) -> EmailLog:
    """
    Create a new email log record from the provided data dictionary.
    """
    email_log = EmailLog(**data)
    db.add(email_log)
    await db.flush()
    await db.refresh(email_log)
    return email_log
