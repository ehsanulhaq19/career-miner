from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.career_job.schemas import (
    CareerJobDateGroupListResponse,
    CareerJobDetailResponse,
    CareerJobListResponse,
    CareerJobWithCountsListResponse,
    DashboardStatsResponse,
    MarkJobSeenRequest,
)
from app.modules.career_job.service import (
    get_career_job,
    get_career_job_dates_grouped,
    get_career_jobs_by_date,
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
    career_client_id: int | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None),
    show_unseen_jobs: bool = Query(False),
    has_client_emails: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerJobListResponse:
    """
    List career jobs with optional filtering and pagination.
    Use career_client_id to filter jobs by client. Results are in desc order.
    """
    return await list_career_jobs(
        db,
        skip=skip,
        limit=limit,
        job_site_id=job_site_id,
        career_client_id=career_client_id,
        category=category,
        search=search,
        user_id=current_user.id,
        show_unseen_jobs=show_unseen_jobs,
        has_client_emails=has_client_emails,
    )


@router.get("/grouped-by-date", response_model=CareerJobDateGroupListResponse)
async def get_career_job_dates_grouped_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerJobDateGroupListResponse:
    """
    Return distinct dates with job counts, sorted by date descending.
    Used for tabular UI - by default shows only date groups.
    """
    return await get_career_job_dates_grouped(db, skip=skip, limit=limit)


@router.get("/by-date", response_model=CareerJobWithCountsListResponse)
async def get_career_jobs_by_date_endpoint(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerJobWithCountsListResponse:
    """
    Return career jobs for a specific date with active/inactive application counts.
    """
    return await get_career_jobs_by_date(
        db,
        target_date=date,
        skip=skip,
        limit=limit,
        user_id=current_user.id,
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
