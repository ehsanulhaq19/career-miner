from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.career_job.schemas import (
    CareerJobDetailResponse,
    CareerJobListResponse,
    DashboardStatsResponse,
    MarkJobSeenRequest,
)
from app.modules.career_job.service import (
    get_career_job,
    get_dashboard_stats,
    list_career_jobs,
    mark_all_jobs_seen,
    mark_job_seen,
)

router = APIRouter()
dashboard_router = APIRouter()


@router.get("/", response_model=CareerJobListResponse)
async def list_career_jobs_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    job_site_id: int | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None),
    show_unseen_jobs: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerJobListResponse:
    """List all career jobs with optional filtering and pagination."""
    return await list_career_jobs(
        db,
        skip=skip,
        limit=limit,
        job_site_id=job_site_id,
        category=category,
        search=search,
        user_id=current_user.id,
        show_unseen_jobs=show_unseen_jobs,
    )


@router.post("/job-seen")
async def mark_job_seen_endpoint(
    request: MarkJobSeenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark a career job as seen by the current user."""
    await mark_job_seen(db, request.career_job_id, current_user.id)
    return {"success": True}


@router.post("/mark-all-seen")
async def mark_all_jobs_seen_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark all career jobs as seen by the current user."""
    return await mark_all_jobs_seen(db, current_user.id)


@router.get("/{career_job_id}", response_model=CareerJobDetailResponse)
async def get_career_job_endpoint(
    career_job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerJobDetailResponse:
    """Retrieve a single career job by ID."""
    return await get_career_job(db, career_job_id, user_id=current_user.id)


@dashboard_router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardStatsResponse:
    """Return dashboard statistics including per-site summary cards."""
    return await get_dashboard_stats(db)
