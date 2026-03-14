from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.models import CareerClient


def _apply_has_email_filter(query, has_email_information: bool | None):
    """Apply email filter to query when has_email_information is True."""
    if has_email_information is not True:
        return query
    return query.where(func.json_array_length(CareerClient.emails) > 0)


async def get_career_clients(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    has_email_information: bool | None = None,
) -> tuple[list[CareerClient], int]:
    """Retrieve a paginated list of active career clients in descending order by id."""
    base_query = (
        select(CareerClient)
        .where(CareerClient.is_active.is_(True))
        .order_by(CareerClient.id.desc())
    )
    base_query = _apply_has_email_filter(base_query, has_email_information)
    query = base_query.offset(skip).limit(limit)

    count_query = select(func.count(CareerClient.id)).where(
        CareerClient.is_active.is_(True)
    )
    if has_email_information is True:
        count_query = count_query.where(
            func.json_array_length(CareerClient.emails) > 0
        )

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


async def update_career_client(
    db: AsyncSession,
    career_client_id: int,
    data: dict,
) -> CareerClient | None:
    """Update an existing career client with the provided data."""
    client = await get_career_client_by_id(db, career_client_id)
    if client is None:
        return None
    for key, value in data.items():
        if hasattr(client, key):
            setattr(client, key, value)
    await db.flush()
    await db.refresh(client)
    return client


async def get_career_clients_without_emails(
    db: AsyncSession,
    limit: int = 1000,
    client_ids: list[int] | None = None,
) -> list[CareerClient]:
    """Retrieve career clients that have no emails, optionally filtered by ids."""
    query = select(CareerClient).where(
        func.coalesce(func.json_array_length(CareerClient.emails), 0) == 0
    )
    if client_ids:
        query = query.where(CareerClient.id.in_(client_ids))
    query = query.where(CareerClient.name.isnot(None)).where(
        CareerClient.name != ""
    ).order_by(CareerClient.id.asc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_total_career_clients_count(db: AsyncSession) -> int:
    """Return the total count of all career clients."""
    result = await db.execute(select(func.count(CareerClient.id)))
    return result.scalar() or 0


async def bulk_update_career_clients_by_location(
    db: AsyncSession, location: str, data: dict
) -> int:
    """Update all career clients with the given location. Returns count of updated rows."""
    from sqlalchemy import update

    stmt = (
        update(CareerClient)
        .where(CareerClient.location == location)
        .values(**data)
    )
    result = await db.execute(stmt)
    return result.rowcount or 0


async def get_distinct_career_client_locations(
    db: AsyncSession,
) -> list[str]:
    """Retrieve all distinct non-null, non-empty location values from career clients."""
    result = await db.execute(
        select(CareerClient.location)
        .where(CareerClient.location.isnot(None))
        .where(CareerClient.location != "")
        .distinct()
        .order_by(CareerClient.location)
    )
    return [row[0] for row in result.all() if row[0]]


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
