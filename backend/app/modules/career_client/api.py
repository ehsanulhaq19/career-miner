from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.career_client.schemas import (
    CareerClientListResponse,
    CareerClientResponse,
)
from app.modules.career_client.service import (
    get_career_client_by_id,
    list_career_clients,
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
    """List all career clients with pagination in descending order."""
    return await list_career_clients(
        db,
        skip=skip,
        limit=limit,
        has_email_information=has_email_information,
    )


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
