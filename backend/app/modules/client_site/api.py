from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.client_site.schemas import (
    ClientSiteCreate,
    ClientSiteListResponse,
    ClientSiteResponse,
    ClientSiteUpdate,
)
from app.modules.client_site.service import (
    create_client_site,
    delete_client_site,
    get_client_site,
    list_client_sites,
    update_client_site,
)

router = APIRouter()


@router.get("/", response_model=ClientSiteListResponse)
async def list_client_sites_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientSiteListResponse:
    """List all client sites with optional filtering and pagination."""
    return await list_client_sites(
        db, skip=skip, limit=limit, is_active=is_active, user_id=current_user.id
    )


@router.get("/{client_site_id}", response_model=ClientSiteResponse)
async def get_client_site_endpoint(
    client_site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientSiteResponse:
    """Retrieve a single client site by ID."""
    return await get_client_site(db, client_site_id, user_id=current_user.id)


@router.post("/", response_model=ClientSiteResponse, status_code=201)
async def create_client_site_endpoint(
    client_site_create: ClientSiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientSiteResponse:
    """Create a new client site."""
    return await create_client_site(db, client_site_create, user_id=current_user.id)


@router.put("/{client_site_id}", response_model=ClientSiteResponse)
async def update_client_site_endpoint(
    client_site_id: int,
    client_site_update: ClientSiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientSiteResponse:
    """Update an existing client site."""
    return await update_client_site(db, client_site_id, client_site_update)


@router.delete("/{client_site_id}")
async def delete_client_site_endpoint(
    client_site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a client site by ID."""
    return await delete_client_site(db, client_site_id, user_id=current_user.id)
