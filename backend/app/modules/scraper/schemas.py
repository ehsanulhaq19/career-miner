from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScrapperResponse(BaseModel):
    """Serialized scrapper record for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    source_url: str
    created_at: datetime


class ScrapperListResponse(BaseModel):
    """List of scrappers linked to a job."""

    items: list[ScrapperResponse]


class ScrapperHtmlPreviewResponse(BaseModel):
    """HTML body and source URL for in-app preview."""

    source_url: str
    html: str
