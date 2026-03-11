from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.career_client.schemas import CareerClientListResponse
from app.modules.career_client.service import list_career_clients

router = APIRouter()


@router.get("/", response_model=CareerClientListResponse)
async def list_career_clients_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientListResponse:
    """List all career clients with pagination in descending order."""
    return await list_career_clients(db, skip=skip, limit=limit)
