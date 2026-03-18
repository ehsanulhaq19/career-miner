from pydantic import BaseModel, EmailStr, Field


class SendEmailRequest(BaseModel):
    """Schema for sending an email request."""

    recipient: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, description="Email subject")
    content: str = Field(..., description="Email body content")


class SendEmailResponse(BaseModel):
    """Schema for send email response."""

    success: bool = Field(..., description="Whether the email was sent successfully")
    message: str = Field(..., description="Status message")
