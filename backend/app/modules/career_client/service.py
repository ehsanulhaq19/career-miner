from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.crud import (
    get_career_clients,
    get_total_career_clients_count,
)
from app.modules.career_client.schemas import (
    CareerClientListResponse,
    CareerClientResponse,
)


async def list_career_clients(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
) -> CareerClientListResponse:
    """Return a paginated list of career clients in descending order."""
    items, total = await get_career_clients(db, skip=skip, limit=limit)

    response_items = [CareerClientResponse.model_validate(item) for item in items]

    page = (skip // limit) + 1 if limit > 0 else 1
    return CareerClientListResponse(
        items=response_items,
        total=total,
        page=page,
        limit=limit,
    )
