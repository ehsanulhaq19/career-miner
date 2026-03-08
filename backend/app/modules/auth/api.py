from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    PasswordUpdate,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.modules.auth.service import (
    forgot_password as forgot_password_service,
    login_user as login_user_service,
    register_user as register_user_service,
    update_password as update_password_service,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user_create: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    return await register_user_service(db, user_create)


@router.post("/login", response_model=TokenResponse)
async def login(user_login: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate and receive an access token."""
    return await login_user_service(db, user_login)


@router.put("/update-password")
async def update_password(
    password_update: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's password."""
    return await update_password_service(db, current_user.id, password_update)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    forgot_req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset instructions."""
    return await forgot_password_service(db, forgot_req)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve the authenticated user's profile."""
    return UserResponse.model_validate(current_user)
