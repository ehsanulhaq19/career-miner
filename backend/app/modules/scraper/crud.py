from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scraper.models import Scrapper


async def create_scrapper(
    db: AsyncSession, file_path: str, source_url: str
) -> Scrapper:
    """Insert a scrapper row for a saved HTML file."""
    row = Scrapper(file_path=file_path, source_url=source_url)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def get_scrapper_by_id(db: AsyncSession, scrapper_id: int) -> Scrapper | None:
    """Load a scrapper by primary key."""
    result = await db.execute(select(Scrapper).where(Scrapper.id == scrapper_id))
    return result.scalars().first()
