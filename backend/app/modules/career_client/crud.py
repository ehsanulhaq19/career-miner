from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.models import CareerClient


async def get_career_clients(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[CareerClient], int]:
    """Retrieve a paginated list of career clients in descending order by id."""
    query = (
        select(CareerClient)
        .order_by(CareerClient.id.desc())
        .offset(skip)
        .limit(limit)
    )
    count_query = select(func.count(CareerClient.id))

    result = await db.execute(query)
    items = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_career_client_by_id(
    db: AsyncSession, career_client_id: int
) -> CareerClient | None:
    """Retrieve a single career client by its primary key."""
    result = await db.execute(
        select(CareerClient).where(CareerClient.id == career_client_id)
    )
    return result.scalars().first()


async def get_career_client_by_link(
    db: AsyncSession, link: str | None
) -> CareerClient | None:
    """Retrieve a career client by link when link is non-empty."""
    if not link or not str(link).strip():
        return None
    result = await db.execute(
        select(CareerClient).where(CareerClient.link == link.strip())
    )
    return result.scalars().first()


async def get_career_client_by_name(
    db: AsyncSession, name: str | None
) -> CareerClient | None:
    """Retrieve a career client by name when name is non-empty."""
    if not name or not str(name).strip():
        return None
    result = await db.execute(
        select(CareerClient).where(CareerClient.name == name.strip())
    )
    return result.scalars().first()


async def create_career_client(db: AsyncSession, data: dict) -> CareerClient:
    """Create a new career client record from the provided data dictionary."""
    career_client = CareerClient(**data)
    db.add(career_client)
    await db.flush()
    await db.refresh(career_client)
    return career_client


async def get_total_career_clients_count(db: AsyncSession) -> int:
    """Return the total count of all career clients."""
    result = await db.execute(select(func.count(CareerClient.id)))
    return result.scalar() or 0


async def get_or_create_career_client(
    db: AsyncSession,
    name: str | None,
    link: str | None,
    location: str | None,
    emails: list[str],
    detail: str | None,
    size: str | None,
) -> CareerClient | None:
    """
    Get existing career client by link or name, or create new one if not found.
    Returns None if both name and link are empty.
    """
    client = None
    if link and str(link).strip():
        client = await get_career_client_by_link(db, link)
    if client is None and name and str(name).strip():
        client = await get_career_client_by_name(db, name)
    if client is not None:
        return client
    has_name = name and str(name).strip()
    has_link = link and str(link).strip()
    if not has_name and not has_link:
        return None
    client_data = {
        "emails": emails or [],
        "name": name.strip() if name else None,
        "location": location.strip() if location else None,
        "detail": detail.strip() if detail else None,
        "link": link.strip() if link else None,
        "size": size.strip() if size else None,
    }
    return await create_career_client(db, client_data)
