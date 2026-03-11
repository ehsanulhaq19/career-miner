from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import verify_token
from app.database import get_db
from app.modules.auth.crud import get_user_by_id
from app.modules.auth.models import User

http_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the Bearer token, then return the authenticated user."""
    token = credentials.credentials
    try:
        payload = verify_token(token)
        user_id: int | None = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException(detail="Invalid authentication token")
    except JWTError:
        raise UnauthorizedException(detail="Invalid authentication token")

    user = await get_user_by_id(db, int(user_id))
    if user is None:
        raise UnauthorizedException(detail="User not found")
    if not user.is_active:
        raise UnauthorizedException(detail="User account is inactive")
    return user
