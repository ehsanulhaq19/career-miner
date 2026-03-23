from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.models import ClientSite


async def get_client_sites(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
) -> tuple[list[ClientSite], int]:
    """Retrieve a paginated list of client sites with optional active filter."""
    query = select(ClientSite)
    count_query = select(func.count(ClientSite.id))

    if is_active is not None:
        query = query.where(ClientSite.is_active == is_active)
        count_query = count_query.where(ClientSite.is_active == is_active)

    query = query.order_by(ClientSite.id.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    items = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_client_site_by_id(
    db: AsyncSession, client_site_id: int
) -> ClientSite | None:
    """Retrieve a single client site by its primary key."""
    result = await db.execute(
        select(ClientSite).where(ClientSite.id == client_site_id)
    )
    return result.scalars().first()


async def create_client_site(db: AsyncSession, data: dict) -> ClientSite:
    """Create a new client site record from the provided data dictionary."""
    client_site = ClientSite(**data)
    db.add(client_site)
    await db.flush()
    await db.refresh(client_site)
    return client_site


async def update_client_site(
    db: AsyncSession, client_site_id: int, data: dict
) -> ClientSite | None:
    """Update an existing client site with only the non-None fields from data."""
    client_site = await get_client_site_by_id(db, client_site_id)
    if client_site is None:
        return None

    for key, value in data.items():
        if value is not None:
            setattr(client_site, key, value)

    await db.flush()
    await db.refresh(client_site)
    return client_site


async def delete_client_site(
    db: AsyncSession, client_site_id: int
) -> bool:
    """Delete a client site by its primary key. Returns True if deleted."""
    client_site = await get_client_site_by_id(db, client_site_id)
    if client_site is None:
        return False

    await db.delete(client_site)
    await db.flush()
    return True
