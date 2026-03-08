import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()


def _normalize_password_for_bcrypt(password: str) -> bytes:
    """Reduce password to 72 bytes or less for bcrypt compatibility."""
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        return hashlib.sha256(encoded).hexdigest().encode("utf-8")
    return encoded


def create_access_token(data: dict) -> str:
    """Create a JWT access token with an expiration claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token, raising JWTError on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    normalized = _normalize_password_for_bcrypt(password)
    return bcrypt.hashpw(normalized, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    normalized = _normalize_password_for_bcrypt(plain)
    return bcrypt.checkpw(normalized, hashed.encode("utf-8"))
