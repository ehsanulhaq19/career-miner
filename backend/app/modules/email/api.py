from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.exceptions import AppException, BadRequestException
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.email.schemas import SendEmailRequest, SendEmailResponse
from app.modules.email.service import EmailService

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
