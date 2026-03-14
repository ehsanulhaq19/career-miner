from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.crud import (
    get_career_client_by_id as crud_get_career_client_by_id,
    get_career_clients,
    get_total_career_clients_count,
)
from app.modules.career_client.schemas import (
    CareerClientListResponse,
    CareerClientResponse,
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
    """Return a paginated list of career clients in descending order."""
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
