from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.scrap_job.schemas import ScrapJobListResponse, ScrapJobResponse
from app.modules.scrap_job.service import get_scrap_job, list_scrap_jobs

router = APIRouter()


@router.get("/", response_model=ScrapJobListResponse)
async def list_scrap_jobs_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    job_site_id: int | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobListResponse:
    """List all scrap jobs with optional filtering and pagination."""
    return await list_scrap_jobs(
        db, skip=skip, limit=limit, job_site_id=job_site_id, status=status,
    )


@router.get("/{scrap_job_id}", response_model=ScrapJobResponse)
async def get_scrap_job_endpoint(
    scrap_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScrapJobResponse:
    """Retrieve a single scrap job by ID."""
    return await get_scrap_job(db, scrap_job_id)
