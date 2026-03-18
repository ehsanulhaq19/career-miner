from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.resume.schemas import (
    ResumeListResponse,
    ResumeResponse,
    ResumeUpdate,
)
from app.modules.resume.service import (
    get_resume_by_id as service_get_resume_by_id,
    get_resume_file_path as service_get_resume_file_path,
    list_resumes as service_list_resumes,
    update_resume as service_update_resume,
    upload_resume as service_upload_resume,
)

router = APIRouter()


@router.post("/", response_model=ResumeResponse)
async def upload_resume_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeResponse:
    """
    Upload a PDF resume file and persist metadata with extracted content.
    """
    return await service_upload_resume(db, file, current_user.id)


@router.get("/", response_model=ResumeListResponse)
async def list_resumes_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeListResponse:
    """
    List resumes for the current user with pagination in descending order.
    """
    return await service_list_resumes(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        name_filter=name,
    )


@router.get("/{resume_id}/file")
async def get_resume_file_endpoint(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """
    Return the resume PDF file for preview or download.
    """
    file_path = await service_get_resume_file_path(
        db, resume_id, current_user.id
    )
    if file_path is None:
        raise HTTPException(status_code=404, detail="Resume file not found")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
    )


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume_endpoint(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeResponse:
    """
    Return a single resume by id for the current user.
    """
    resume = await service_get_resume_by_id(db, resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume_endpoint(
    resume_id: int,
    resume_update: ResumeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResumeResponse:
    """
    Update an existing resume.
    """
    updated = await service_update_resume(
        db, resume_id, current_user.id, resume_update
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return updated
