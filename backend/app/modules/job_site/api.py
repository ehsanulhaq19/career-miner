from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.job_site.schemas import (
    JobSiteCreate,
    JobSiteListResponse,
    JobSiteResponse,
    JobSiteUpdate,
)
from app.modules.job_site.service import (
    create_job_site,
    delete_job_site,
    get_job_site,
    list_job_sites,
    update_job_site,
)

router = APIRouter()


@router.get("/", response_model=JobSiteListResponse)
async def list_job_sites_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobSiteListResponse:
    """List all job sites with optional filtering and pagination."""
    return await list_job_sites(db, skip=skip, limit=limit, is_active=is_active)


@router.get("/{job_site_id}", response_model=JobSiteResponse)
async def get_job_site_endpoint(
    job_site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobSiteResponse:
    """Retrieve a single job site by ID."""
    return await get_job_site(db, job_site_id)


@router.post("/", response_model=JobSiteResponse, status_code=201)
async def create_job_site_endpoint(
    job_site_create: JobSiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobSiteResponse:
    """Create a new job site."""
    return await create_job_site(db, job_site_create)


@router.put("/{job_site_id}", response_model=JobSiteResponse)
async def update_job_site_endpoint(
    job_site_id: int,
    job_site_update: JobSiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobSiteResponse:
    """Update an existing job site."""
    return await update_job_site(db, job_site_id, job_site_update)


@router.delete("/{job_site_id}")
async def delete_job_site_endpoint(
    job_site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a job site by ID."""
    return await delete_job_site(db, job_site_id)
