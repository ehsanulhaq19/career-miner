from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Retrieve a user by their email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Retrieve a user by their primary key ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_user(db: AsyncSession, user_data: dict) -> User:
    """Create a new user record in the database."""
    user = User(**user_data)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user_password(db: AsyncSession, user_id: int, hashed_password: str) -> User:
    """Update a user's password hash by their ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.password = hashed_password
        await db.flush()
        await db.refresh(user)
    return user
