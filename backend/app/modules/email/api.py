from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, BadRequestException
from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.email.schemas import (
    JobEmailLogDetailResponse,
    JobEmailLogListResponse,
    SendEmailRequest,
    SendEmailResponse,
)
from app.modules.email.crud import get_email_log_by_id
from app.modules.email.service import (
    EmailService,
    get_job_email_log_detail_by_id,
    list_job_email_logs,
)

router = APIRouter()


def _validate_email_request(recipient: str, subject: str, content: str) -> None:
    """Validate email request fields and raise BadRequestException if invalid."""
    try:
        SendEmailRequest(recipient=recipient, subject=subject, content=content)
    except Exception:
        raise BadRequestException(detail="Invalid email address or missing required fields")


@router.post("/send", response_model=SendEmailResponse)
async def send_email_endpoint(
    recipient: str = Form(..., description="Recipient email address"),
    subject: str = Form(..., min_length=1, description="Email subject"),
    content: str = Form(..., description="Email body content"),
    attachment: UploadFile | None = File(None, description="Optional file attachment"),
    current_user: User = Depends(get_current_user),
) -> SendEmailResponse:
    """
    Send an email to the specified recipient with optional file attachment.
    """
    _validate_email_request(recipient, subject, content)
    try:
        attachment_bytes: bytes | None = None
        attachment_filename: str | None = None

        if attachment and attachment.filename:
            attachment_bytes = await attachment.read()
            attachment_filename = attachment.filename

        service = EmailService()
        await service.send_email(
            recipient=recipient,
            subject=subject,
            content=content,
            attachment=attachment_bytes,
            attachment_filename=attachment_filename,
        )
        return SendEmailResponse(success=True, message="Email sent successfully")
    except AppException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/job-logs", response_model=JobEmailLogListResponse)
async def list_job_email_logs_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    career_client_id: int | None = Query(None),
    created_date_from: str | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    created_date_to: str | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    search: str | None = Query(None, description="Search in to_email, job title, client name, client website"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobEmailLogListResponse:
    """
    List email logs linked to job applications with pagination and filters.
    Results ordered by created_at descending.
    """
    return await list_job_email_logs(
        db,
        skip=skip,
        limit=limit,
        career_client_id=career_client_id,
        created_date_from=created_date_from,
        created_date_to=created_date_to,
        search=search,
    )


@router.get("/job-logs/{email_log_id}/attachment")
async def get_job_email_log_attachment_endpoint(
    email_log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Serve file attachment for a job email log if available.
    """
    log = await get_email_log_by_id(db, email_log_id)
    if not log or not log.file_attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    full_path = Path(log.file_attachment)
    if not full_path.is_absolute():
        full_path = Path.cwd() / log.file_attachment
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found")
    media_type = "application/octet-stream"
    if full_path.suffix.lower() == ".pdf":
        media_type = "application/pdf"
    return FileResponse(
        path=str(full_path),
        media_type=media_type,
        filename=full_path.name,
    )


@router.get("/job-logs/{email_log_id}", response_model=JobEmailLogDetailResponse)
async def get_job_email_log_detail_endpoint(
    email_log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobEmailLogDetailResponse:
    """
    Retrieve full job email log detail including linked job and client data.
    """
    return await get_job_email_log_detail_by_id(db, email_log_id)
