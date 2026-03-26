import os
from pathlib import Path

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import get_settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.database import async_session
from app.modules.email.crud import (
    create_email_log,
    get_job_email_log_detail,
    get_job_email_logs,
    get_job_email_logs_count,
)


class EmailService:
    """
    Service for sending emails via SMTP with logging to email_logs table.
    """

    def __init__(self) -> None:
        """
        Initialize email service with settings.
        """
        settings = get_settings()
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._username = settings.SMTP_USERNAME
        self._password = settings.SMTP_PASSWORD
        self._from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
        self._use_tls = settings.SMTP_USE_TLS

    async def send_email(
        self,
        recipient: str,
        subject: str,
        content: str,
        attachment_path: str | None = None,
        attachment: bytes | None = None,
        attachment_filename: str | None = None,
        raise_on_failure: bool = True,
    ) -> dict:
        """
        Send an email to the specified recipient with optional file attachment.
        Creates an entry in email_logs table with subject, content, file_attachment,
        to_email, from_email, response and status.
        When raise_on_failure is False, SMTP errors are recorded in the log and
        returned in the response dict instead of raising.
        """
        if not self._username or not self._password:
            raise BadRequestException(
                detail="Email service is not configured. Set SMTP_USERNAME and SMTP_PASSWORD."
            )
        message = MIMEMultipart()
        message["From"] = self._from_email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(content, "plain", "utf-8"))

        attachment_bytes = attachment
        attachment_name = attachment_filename
        if attachment_path and not attachment_bytes:
            full_path = Path(attachment_path)
            if not full_path.is_absolute():
                full_path = Path(os.getcwd()) / attachment_path
            if full_path.exists():
                with open(full_path, "rb") as f:
                    attachment_bytes = f.read()
                attachment_name = attachment_name or full_path.name

        if attachment_bytes is not None and attachment_name:
            part = MIMEApplication(attachment_bytes, _subtype="octet-stream")
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=attachment_name,
            )
            message.attach(part)

        use_tls = self._use_tls and self._port == 465
        start_tls = self._use_tls and self._port == 587

        status = "success"
        response = None
        email_log_id = None
        try:
            await aiosmtplib.send(
                message,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                use_tls=use_tls,
                start_tls=start_tls,
            )
        except Exception as exc:
            status = "error"
            response = str(exc)
            raise
        finally:
            log_data = {
                "subject": subject,
                "content": content,
                "file_attachment": attachment_path or (attachment_name if attachment_bytes else None),
                "to_email": recipient,
                "from_email": self._from_email,
                "response": response,
                "status": status,
            }
            async with async_session() as log_db:
                email_log = await create_email_log(log_db, log_data)
                await log_db.commit()
                email_log_id = email_log.id

        if send_error is not None and raise_on_failure:
            raise send_error
        return {"status": status, "response": response, "email_log_id": email_log_id}


async def list_job_email_logs(
    db,
    skip: int = 0,
    limit: int = 20,
    career_client_id: int | None = None,
    created_date_from: str | None = None,
    created_date_to: str | None = None,
    search: str | None = None,
):
    """
    Return paginated job email logs with optional filters.
    """
    from datetime import datetime

    from app.modules.email.schemas import (
        JobEmailLogItemResponse,
        JobEmailLogListResponse,
    )

    parsed_from = None
    parsed_to = None
    if created_date_from:
        try:
            parsed_from = datetime.strptime(created_date_from, "%Y-%m-%d").date()
        except ValueError:
            pass
    if created_date_to:
        try:
            parsed_to = datetime.strptime(created_date_to, "%Y-%m-%d").date()
        except ValueError:
            pass

    rows, total = await get_job_email_logs(
        db,
        skip=skip,
        limit=limit,
        career_client_id=career_client_id,
        created_date_from=parsed_from,
        created_date_to=parsed_to,
        search=search,
    )

    items = []
    for log, ja, cj, cc in rows:
        items.append(
            JobEmailLogItemResponse(
                id=log.id,
                subject=log.subject,
                content=log.content,
                file_attachment=log.file_attachment,
                to_email=log.to_email,
                from_email=log.from_email,
                response=log.response,
                status=log.status,
                created_at=log.created_at,
                job_application_id=ja.id,
                career_job_id=cj.id,
                career_job_title=cj.title,
                career_client_id=cc.id if cc else None,
                career_client_name=cc.name if cc else None,
            )
        )

    page = (skip // limit) + 1 if limit > 0 else 1
    return JobEmailLogListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


async def get_job_email_log_detail_by_id(db, email_log_id: int):
    """
    Return full job email log detail with linked job and client data.
    """
    from app.modules.email.schemas import JobEmailLogDetailResponse

    row = await get_job_email_log_detail(db, email_log_id)
    if row is None:
        raise NotFoundException(detail="Job email log not found")

    log, ja, cj, cc = row
    job_application = {
        "id": ja.id,
        "application_name": ja.application_name,
        "subject": ja.subject,
        "cover_letter": ja.cover_letter,
        "to_emails": ja.to_emails or [],
    }
    career_job = {
        "id": cj.id,
        "title": cj.title,
        "description": cj.description,
        "url": cj.url,
    }
    career_client = None
    if cc:
        career_client = {
            "id": cc.id,
            "name": cc.name,
            "official_website": cc.official_website,
            "emails": cc.emails or [],
        }

    return JobEmailLogDetailResponse(
        id=log.id,
        subject=log.subject,
        content=log.content,
        file_attachment=log.file_attachment,
        to_email=log.to_email,
        from_email=log.from_email,
        response=log.response,
        status=log.status,
        created_at=log.created_at,
        job_application=job_application,
        career_job=career_job,
        career_client=career_client,
    )
