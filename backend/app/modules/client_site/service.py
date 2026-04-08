from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.client_site.crud import (
    create_client_site as crud_create,
    delete_client_site as crud_delete,
    get_client_site_by_id,
    get_client_sites,
    update_client_site as crud_update,
)
from app.modules.client_site.schemas import (
    ClientSiteCreate,
    ClientSiteListResponse,
    ClientSiteResponse,
    ClientSiteUpdate,
)


async def list_client_sites(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
    user_id: int | None = None,
) -> ClientSiteListResponse:
    """Return a paginated list of client sites."""
    items, total = await get_client_sites(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        created_by=user_id,
    )
    return ClientSiteListResponse(
        items=[ClientSiteResponse.model_validate(item) for item in items],
        total=total,
    )


async def get_client_site(
    db: AsyncSession, client_site_id: int, user_id: int | None = None
) -> ClientSiteResponse:
    """Return a single client site or raise NotFoundException."""
    client_site = await get_client_site_by_id(db, client_site_id)
    if client_site is None:
        raise NotFoundException(detail="Client site not found")
    if user_id is not None and client_site.created_by != user_id:
        raise NotFoundException(detail="Client site not found")
    return ClientSiteResponse.model_validate(client_site)


async def create_client_site(
    db: AsyncSession, client_site_create: ClientSiteCreate, user_id: int
) -> ClientSiteResponse:
    """Create a new client site and return the response."""
    data = client_site_create.model_dump()
    data["created_by"] = user_id
    client_site = await crud_create(db, data)
    return ClientSiteResponse.model_validate(client_site)


async def update_client_site(
    db: AsyncSession,
    client_site_id: int,
    client_site_update: ClientSiteUpdate,
    user_id: int,
) -> ClientSiteResponse:
    """Update a client site or raise NotFoundException if it does not exist."""
    existing = await get_client_site_by_id(db, client_site_id)
    if existing is None or existing.created_by != user_id:
        raise NotFoundException(detail="Client site not found")
    client_site = await crud_update(
        db, client_site_id, client_site_update.model_dump(exclude_unset=True)
    )
    if client_site is None:
        raise NotFoundException(detail="Client site not found")
    return ClientSiteResponse.model_validate(client_site)


async def delete_client_site(
    db: AsyncSession, client_site_id: int, user_id: int
) -> dict:
    """Delete a client site by ID."""
    existing = await get_client_site_by_id(db, client_site_id)
    if existing is None or existing.created_by != user_id:
        raise NotFoundException(detail="Client site not found")
    deleted = await crud_delete(db, client_site_id)
    if not deleted:
        raise NotFoundException(detail="Client site not found")
    return {"message": "Client site deleted successfully"}
