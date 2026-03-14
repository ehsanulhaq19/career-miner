from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.crud import (
    bulk_update_career_clients_by_location as crud_bulk_update,
    get_career_client_by_id as crud_get_career_client_by_id,
    get_career_clients,
    get_distinct_career_client_locations as crud_get_locations,
    get_total_career_clients_count,
    update_career_client as crud_update_career_client,
)
from app.modules.career_client.schemas import (
    CareerClientBulkUpdate,
    CareerClientListResponse,
    CareerClientLocationsResponse,
    CareerClientResponse,
    CareerClientUpdate,
)


async def get_career_client_by_id(
    db: AsyncSession, career_client_id: int
) -> CareerClientResponse | None:
    """Return a single career client by id or None if not found."""
    client = await crud_get_career_client_by_id(db, career_client_id)
    if client is None:
        return None
    return CareerClientResponse.model_validate(client)


async def list_career_clients(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    has_email_information: bool | None = None,
) -> CareerClientListResponse:
    """Return a paginated list of active career clients in descending order."""
    items, total = await get_career_clients(
        db,
        skip=skip,
        limit=limit,
        has_email_information=has_email_information,
    )

    response_items = [CareerClientResponse.model_validate(item) for item in items]

    page = (skip // limit) + 1 if limit > 0 else 1
    return CareerClientListResponse(
        items=response_items,
        total=total,
        page=page,
        limit=limit,
    )


async def update_career_client(
    db: AsyncSession, career_client_id: int, update_data: CareerClientUpdate
) -> CareerClientResponse | None:
    """Update an existing career client and return the updated client or None."""
    data = update_data.model_dump(exclude_unset=True)
    if not data:
        client = await crud_get_career_client_by_id(db, career_client_id)
        return CareerClientResponse.model_validate(client) if client else None
    updated = await crud_update_career_client(db, career_client_id, data)
    return CareerClientResponse.model_validate(updated) if updated else None


async def bulk_update_career_clients(
    db: AsyncSession, location: str, update_data: CareerClientBulkUpdate
) -> int:
    """Bulk update career clients by location. Returns count of updated rows."""
    data = update_data.model_dump(exclude_unset=True)
    if not data:
        return 0
    return await crud_bulk_update(db, location, data)


async def get_career_client_locations(
    db: AsyncSession,
) -> CareerClientLocationsResponse:
    """Return all distinct locations from career clients."""
    locations = await crud_get_locations(db)
    return CareerClientLocationsResponse(locations=locations)
