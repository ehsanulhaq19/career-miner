from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.resume.models import Resume


async def get_resumes_by_user(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    name_filter: str | None = None,
) -> tuple[list[Resume], int]:
    """
    Retrieve a paginated list of resumes for a user in descending order by id.
    """
    base_query = (
        select(Resume)
        .where(Resume.uploaded_by_id == user_id)
        .order_by(Resume.id.desc())
    )
    if name_filter and name_filter.strip():
        pattern = f"%{name_filter.strip()}%"
        base_query = base_query.where(Resume.name.ilike(pattern))

    query = base_query.offset(skip).limit(limit)
    count_query = (
        select(func.count(Resume.id)).where(Resume.uploaded_by_id == user_id)
    )
    if name_filter and name_filter.strip():
        pattern = f"%{name_filter.strip()}%"
        count_query = count_query.where(Resume.name.ilike(pattern))

    result = await db.execute(query)
    items = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_resume_by_id(
    db: AsyncSession, resume_id: int, user_id: int
) -> Resume | None:
    """
    Retrieve a single resume by id for the given user.
    """
    result = await db.execute(
        select(Resume)
        .where(Resume.id == resume_id)
        .where(Resume.uploaded_by_id == user_id)
    )
    return result.scalars().first()


async def create_resume(db: AsyncSession, data: dict) -> Resume:
    """
    Create a new resume record from the provided data dictionary.
    """
    resume = Resume(**data)
    db.add(resume)
    await db.flush()
    await db.refresh(resume)
    return resume


async def update_resume(
    db: AsyncSession,
    resume_id: int,
    user_id: int,
    data: dict,
) -> Resume | None:
    """
    Update an existing resume with the provided data.
    """
    resume = await get_resume_by_id(db, resume_id, user_id)
    if resume is None:
        return None
    for key, value in data.items():
        if hasattr(resume, key):
            setattr(resume, key, value)
    await db.flush()
    await db.refresh(resume)
    return resume
