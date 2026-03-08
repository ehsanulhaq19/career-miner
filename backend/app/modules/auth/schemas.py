from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration requests."""

    first_name: str
    last_name: str
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    """Schema for user login requests."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user data returned in API responses."""

    id: int
    first_name: str
    last_name: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for authentication token responses."""

    access_token: str
    token_type: str = "bearer"


class PasswordUpdate(BaseModel):
    """Schema for password update requests."""

    current_password: str
    new_password: str = Field(min_length=6)


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password requests."""

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Schema for forgot password responses."""

    message: str
