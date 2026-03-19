from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeResponse(BaseModel):
    """
    Schema for resume response data.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    size: int
    extension: str
    content: str | None
    extra_detail: str | None
    uploaded_by_id: int
    is_active: bool
    created_at: datetime


class ResumeListResponse(BaseModel):
    """
    Schema for paginated list of resumes.
    """

    items: list[ResumeResponse]
    total: int
    page: int
    limit: int


class ResumeUpdate(BaseModel):
    """
    Schema for updating an existing resume.
    """

    is_active: bool | None = None
    extra_detail: str | None = None
