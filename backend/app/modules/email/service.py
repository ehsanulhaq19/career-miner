import os
from pathlib import Path

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import get_settings
from app.core.exceptions import BadRequestException
from app.database import async_session
from app.modules.email.crud import create_email_log


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
    ) -> dict:
        """
        Send an email to the specified recipient with optional file attachment.
        Creates an entry in email_logs table with subject, content, file_attachment,
        to_email, from_email, response and status.
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

        return {"status": status, "response": response, "email_log_id": email_log_id}
