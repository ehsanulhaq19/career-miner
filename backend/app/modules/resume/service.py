import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import BadRequestException
from app.modules.resume.crud import (
    create_resume as crud_create_resume,
    get_resume_by_id as crud_get_resume_by_id,
    get_resumes_by_user as crud_get_resumes_by_user,
    update_resume as crud_update_resume,
)
from app.modules.resume.schemas import (
    ResumeListResponse,
    ResumeResponse,
    ResumeUpdate,
)

settings = get_settings()


def _get_upload_folder() -> Path:
    """
    Return the configured resume upload folder path.
    """
    folder = settings.RESUME_UPLOAD_FOLDER
    path = Path(folder)
    if not path.is_absolute():
        path = Path(os.getcwd()) / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extract_pdf_content(file_path: Path) -> str:
    """
    Extract text content from a PDF file.
    """
    reader = PdfReader(str(file_path))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


async def upload_resume(
    db: AsyncSession,
    file: UploadFile,
    user_id: int,
    extra_detail: str | None = None,
) -> ResumeResponse:
    """
    Upload a PDF file, save it to local folder, extract content and persist resume record.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise BadRequestException(detail="Only PDF files are allowed")

    content_type = file.content_type or ""
    if "pdf" not in content_type.lower():
        raise BadRequestException(detail="Only PDF files are allowed")

    file_content = await file.read()
    file_size = len(file_content)

    upload_folder = _get_upload_folder()
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = upload_folder / unique_name

    with open(file_path, "wb") as f:
        f.write(file_content)

    try:
        extracted_content = _extract_pdf_content(file_path)
    except Exception:
        extracted_content = ""

    extension = Path(file.filename or "file.pdf").suffix.lstrip(".") or "pdf"
    resume_data = {
        "name": file.filename or "unnamed.pdf",
        "size": file_size,
        "extension": extension,
        "file_path": unique_name,
        "content": extracted_content,
        "extra_detail": extra_detail,
        "uploaded_by_id": user_id,
        "is_active": True,
    }
    resume = await crud_create_resume(db, resume_data)
    return ResumeResponse.model_validate(resume)


async def list_resumes(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    name_filter: str | None = None,
    is_active: bool | None = None,
) -> ResumeListResponse:
    """
    Return a paginated list of resumes for the user in descending order.
    """
    items, total = await crud_get_resumes_by_user(
        db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        name_filter=name_filter,
        is_active=is_active,
    )
    response_items = [ResumeResponse.model_validate(item) for item in items]
    page = (skip // limit) + 1 if limit > 0 else 1
    return ResumeListResponse(
        items=response_items,
        total=total,
        page=page,
        limit=limit,
    )


async def get_resume_by_id(
    db: AsyncSession, resume_id: int, user_id: int
) -> ResumeResponse | None:
    """
    Return a single resume by id for the given user.
    """
    resume = await crud_get_resume_by_id(db, resume_id, user_id)
    if resume is None:
        return None
    return ResumeResponse.model_validate(resume)


async def get_resume_file_path(
    db: AsyncSession, resume_id: int, user_id: int
) -> Path | None:
    """
    Return the filesystem path to the resume PDF file, or None if not found.
    """
    resume = await crud_get_resume_by_id(db, resume_id, user_id)
    if resume is None or not resume.file_path:
        return None
    upload_folder = _get_upload_folder()
    file_path = upload_folder / resume.file_path
    if not file_path.exists():
        return None
    return file_path


async def update_resume(
    db: AsyncSession,
    resume_id: int,
    user_id: int,
    update_data: ResumeUpdate,
) -> ResumeResponse | None:
    """
    Update an existing resume and return the updated resume or None.
    """
    data = update_data.model_dump(exclude_unset=True)
    if "name" in data and (not data["name"] or not str(data["name"]).strip()):
        del data["name"]
    if not data:
        resume = await crud_get_resume_by_id(db, resume_id, user_id)
        return ResumeResponse.model_validate(resume) if resume else None
    updated = await crud_update_resume(db, resume_id, user_id, data)
    return ResumeResponse.model_validate(updated) if updated else None
