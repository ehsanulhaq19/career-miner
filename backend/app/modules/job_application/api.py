from datetime import date as Date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.job_application.schemas import (
    BulkJobApplicationCreateRequest,
    BulkJobApplicationEmailSendRequest,
    BulkJobApplicationUpdateRequest,
    BulkJobApplicationUpdateResponse,
    JobApplicationCreateRequest,
    JobApplicationDateGroupListResponse,
    JobApplicationListResponse,
    JobApplicationResponse,
    JobApplicationUpdate,
    LiveJobApplicationCreateRequest,
    LiveJobDuplicateCheckRequest,
    LiveJobDuplicateCheckResponse,
)
from app.modules.job_application.schemas import EmailLogResponse
from app.modules.job_application.service import (
    check_live_job_duplicate,
    create_job_application_flow,
    create_live_job_application_flow,
    get_bulk_job_application_logs,
    get_bulk_job_application_email_send_logs,
    get_job_application,
    get_job_application_dates_grouped,
    get_job_application_email_logs,
    get_job_application_file_path,
    list_job_applications,
    list_job_applications_by_created_date,
    list_job_applications_for_bulk_email,
    run_bulk_job_application_background,
    run_bulk_job_application_email_background,
    send_job_application_email,
    start_bulk_job_application,
    start_bulk_job_application_email_send,
    bulk_update_job_applications,
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


@router.post("/live/check", response_model=LiveJobDuplicateCheckResponse)
async def check_live_job_application_duplicate_endpoint(
    request: LiveJobDuplicateCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LiveJobDuplicateCheckResponse:
    """
    Return whether a career job already exists for this user with the same
    job text (stored description or original pasted text from a prior live run).
    """
    return await check_live_job_duplicate(
        db,
        request.job_details,
        current_user.id,
    )


@router.post("/live", response_model=JobApplicationResponse)
async def create_live_job_application_endpoint(
    request: LiveJobApplicationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplicationResponse:
    """
    Create client and job from pasted job text via Grok extraction, then create a job
    application (and optionally send emails) tagged as a live application.
    """
    return await create_live_job_application_flow(
        db,
        job_details=request.job_details,
        resume_id=request.resume_id,
        user_id=current_user.id,
        action=request.action,
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


@router.get("/grouped-by-date", response_model=JobApplicationDateGroupListResponse)
async def get_job_application_dates_grouped_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplicationDateGroupListResponse:
    """
    Return distinct creation dates with application counts for the current user,
    sorted by date descending. Used for bulk edit UI grouped by date.
    """
    return await get_job_application_dates_grouped(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get("/by-date", response_model=JobApplicationListResponse)
async def list_job_applications_by_created_date_endpoint(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplicationListResponse:
    """
    List job applications created on the given calendar date for the current user.
    """
    try:
        target_date = Date.fromisoformat(date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format, expected YYYY-MM-DD",
        )
    return await list_job_applications_by_created_date(
        db,
        user_id=current_user.id,
        target_date=target_date,
        skip=skip,
        limit=limit,
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


@router.post("/bulk", response_model=dict, status_code=201)
async def create_bulk_job_applications_endpoint(
    request: BulkJobApplicationCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create job applications in bulk.
    Accepts resume_id and career_job_ids.
    Runs in background and sends socket updates for each job application created.
    """
    if not request.career_job_ids:
        raise HTTPException(
            status_code=400, detail="At least one career job must be selected"
        )
    result = await start_bulk_job_application(
        db,
        resume_id=request.resume_id,
        career_job_ids=request.career_job_ids,
        user_id=current_user.id,
    )
    background_tasks.add_task(
        run_bulk_job_application_background,
        result.id,
        request.resume_id,
        request.career_job_ids,
        current_user.id,
    )
    return {"id": result.id, "status": result.status}


@router.patch("/bulk", response_model=BulkJobApplicationUpdateResponse)
async def bulk_update_job_applications_endpoint(
    request: BulkJobApplicationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkJobApplicationUpdateResponse:
    """
    Bulk-update is_active for the specified job applications owned by the current user.
    """
    if not request.job_application_ids:
        raise HTTPException(
            status_code=400, detail="At least one job application must be selected"
        )
    updated_count = await bulk_update_job_applications(
        db,
        current_user.id,
        request.job_application_ids,
        request.is_active,
    )
    return BulkJobApplicationUpdateResponse(updated_count=updated_count)


@router.get("/bulk/{bulk_job_application_id}/logs")
async def get_bulk_job_application_logs_endpoint(
    bulk_job_application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve logs for a bulk job application run."""
    return await get_bulk_job_application_logs(
        db, bulk_job_application_id, current_user.id
    )


@router.get("/bulk-email/fetch", response_model=JobApplicationListResponse)
async def list_job_applications_for_bulk_email_endpoint(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    min_similarity_score: float = Query(0, ge=0, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplicationListResponse:
    """
    List job applications created on the given date with similarity_score
    >= min_similarity_score. Used for bulk email send UI.
    """
    items, total = await list_job_applications_for_bulk_email(
        db,
        user_id=current_user.id,
        target_date=date,
        min_similarity_score=min_similarity_score,
        skip=skip,
        limit=limit,
    )
    page = (skip // limit) + 1 if limit > 0 else 1
    return JobApplicationListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/bulk-email/send", status_code=201)
async def bulk_send_job_application_emails_endpoint(
    request: BulkJobApplicationEmailSendRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Send emails for multiple job applications in bulk.
    Runs in background and sends socket updates for each step.
    """
    if not request.job_application_ids:
        raise HTTPException(
            status_code=400, detail="At least one job application must be selected"
        )
    result = await start_bulk_job_application_email_send(
        db,
        job_application_ids=request.job_application_ids,
        user_id=current_user.id,
        min_similarity_score=request.min_similarity_score,
    )
    background_tasks.add_task(
        run_bulk_job_application_email_background,
        result["id"],
        result["job_application_ids"],
        current_user.id,
    )
    return {"id": result["id"], "status": result["status"]}


@router.get("/bulk-email/{bulk_id}/logs")
async def get_bulk_job_application_email_send_logs_endpoint(
    bulk_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve logs for a bulk job application email send run.
    """
    return await get_bulk_job_application_email_send_logs(
        db, bulk_id, current_user.id
    )


@router.post("/{job_application_id}/send-email", response_model=JobApplicationResponse)
async def send_job_application_email_endpoint(
    job_application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplicationResponse:
    """
    Send emails for the job application to each configured to_email address.
    """
    return await send_job_application_email(
        db, job_application_id, current_user.id
    )


@router.get("/{job_application_id}/email-logs")
async def get_job_application_email_logs_endpoint(
    job_application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailLogResponse]:
    """
    Retrieve all email logs for the given job application.
    """
    return await get_job_application_email_logs(
        db, job_application_id, current_user.id
    )


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
