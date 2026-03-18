from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import get_settings
from app.core.exceptions import BadRequestException


class EmailService:
    """Service for sending emails via Gmail SMTP."""

    def __init__(self) -> None:
        """Initialize email service with settings."""
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
        attachment: bytes | None = None,
        attachment_filename: str | None = None,
    ) -> None:
        """
        Send an email to the specified recipient with optional file attachment.

        Args:
            recipient: Recipient email address.
            subject: Email subject line.
            content: Email body content.
            attachment: Optional file content as bytes.
            attachment_filename: Optional filename for the attachment.
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

        if attachment is not None and attachment_filename:
            part = MIMEApplication(attachment, _subtype="octet-stream")
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=attachment_filename,
            )
            message.attach(part)

        use_tls = self._use_tls and self._port == 465
        start_tls = self._use_tls and self._port == 587

        await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            use_tls=use_tls,
            start_tls=start_tls,
        )
