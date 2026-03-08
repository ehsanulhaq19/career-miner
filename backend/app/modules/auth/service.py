from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.crud import create_user, get_user_by_email, get_user_by_id, update_user_password
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    PasswordUpdate,
    TokenResponse,
    UserCreate,
    UserResponse,
)


async def register_user(db: AsyncSession, user_create: UserCreate) -> UserResponse:
    """Register a new user after checking for email uniqueness."""
    existing = await get_user_by_email(db, user_create.email)
    if existing:
        raise ConflictException(detail="A user with this email already exists")

    user_data = {
        "first_name": user_create.first_name,
        "last_name": user_create.last_name,
        "email": user_create.email,
        "password": hash_password(user_create.password),
    }
    user = await create_user(db, user_data)
    return UserResponse.model_validate(user)


async def login_user(db: AsyncSession, user_login) -> TokenResponse:
    """Authenticate a user by email and password, returning a JWT token."""
    user = await get_user_by_email(db, user_login.email)
    if not user:
        raise UnauthorizedException(detail="Invalid email or password")

    if not verify_password(user_login.password, user.password):
        raise UnauthorizedException(detail="Invalid email or password")

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token)


async def update_password(db: AsyncSession, user_id: int, password_update: PasswordUpdate) -> dict:
    """Update the authenticated user's password after verifying the current one."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise UnauthorizedException(detail="User not found")

    if not verify_password(password_update.current_password, user.password):
        raise UnauthorizedException(detail="Current password is incorrect")

    hashed = hash_password(password_update.new_password)
    await update_user_password(db, user_id, hashed)
    return {"message": "Password updated successfully"}


async def forgot_password(db: AsyncSession, forgot_req: ForgotPasswordRequest) -> ForgotPasswordResponse:
    """Handle forgot password request with a generic response for security."""
    return ForgotPasswordResponse(
        message="If an account with that email exists, password reset instructions have been sent"
    )
