from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.career_client.schemas import (
    CareerClientBulkUpdate,
    CareerClientListResponse,
    CareerClientLocationsResponse,
    CareerClientResponse,
    CareerClientUpdate,
)
from app.modules.career_client.service import (
    bulk_update_career_clients,
    get_career_client_by_id,
    get_career_client_locations,
    list_career_clients,
    update_career_client,
)

router = APIRouter()


@router.get("/", response_model=CareerClientListResponse)
async def list_career_clients_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    has_email_information: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientListResponse:
    """List active career clients with pagination in descending order."""
    return await list_career_clients(
        db,
        skip=skip,
        limit=limit,
        has_email_information=has_email_information,
    )


@router.get("/locations", response_model=CareerClientLocationsResponse)
async def get_career_client_locations_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientLocationsResponse:
    """Return all distinct locations from career clients."""
    return await get_career_client_locations(db)


@router.get("/{career_client_id}", response_model=CareerClientResponse)
async def get_career_client_endpoint(
    career_client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientResponse:
    """Return a single career client by id."""
    client = await get_career_client_by_id(db, career_client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Career client not found")
    return client


@router.put("/{career_client_id}", response_model=CareerClientResponse)
async def update_career_client_endpoint(
    career_client_id: int,
    career_client_update: CareerClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientResponse:
    """Update an existing career client."""
    updated = await update_career_client(
        db, career_client_id, career_client_update
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Career client not found")
    return updated


@router.put("/bulk-update/location")
async def bulk_update_career_clients_endpoint(
    bulk_update: CareerClientBulkUpdate,
    location: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Bulk update career clients by location."""
    count = await bulk_update_career_clients(db, location, bulk_update)
    return {"updated_count": count}
