from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.job_application.schemas import (
    JobApplicationCreateRequest,
    JobApplicationListResponse,
    JobApplicationResponse,
    JobApplicationUpdate,
)
from app.modules.job_application.service import (
    create_job_application_flow,
    get_job_application,
    get_job_application_file_path,
    list_job_applications,
    update_job_application,
)

router = APIRouter()


@router.post("/", response_model=JobApplicationResponse)
async def create_job_application_endpoint(
    request: JobApplicationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplicationResponse:
    """
    Create a job application by fetching job, client, resume data,
    passing to LLM for generation, and saving the result.
    """
    return await create_job_application_flow(
        db,
        career_job_id=request.career_job_id,
        resume_id=request.resume_id,
        user_id=current_user.id,
    )


@router.get("/", response_model=JobApplicationListResponse)
async def list_job_applications_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplicationListResponse:
    """
    List job applications for the current user in descending order.
    Optional is_active filter.
    """
    return await list_job_applications(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        is_active=is_active,
    )


@router.get("/{job_application_id}", response_model=JobApplicationResponse)
async def get_job_application_endpoint(
    job_application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplicationResponse:
    """Retrieve a single job application by ID."""
    return await get_job_application(db, job_application_id, current_user.id)


@router.put("/{job_application_id}", response_model=JobApplicationResponse)
async def update_job_application_endpoint(
    job_application_id: int,
    job_application_update: JobApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplicationResponse:
    """Update a job application."""
    data = job_application_update.model_dump(exclude_unset=True)
    updated = await update_job_application(
        db, job_application_id, current_user.id, data
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Job application not found")
    return updated


@router.get("/{job_application_id}/file")
async def get_job_application_file_endpoint(
    job_application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Return the output resume PDF file for preview or download."""
    file_path = await get_job_application_file_path(
        db, job_application_id, current_user.id
    )
    if file_path is None:
        raise HTTPException(status_code=404, detail="Resume file not found")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
    )
