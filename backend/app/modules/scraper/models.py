from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base


class Scrapper(Base):
    """Stored artifact for raw HTML saved during a scrape, with filesystem path and source URL."""

    __tablename__ = "scrappers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String(2048), nullable=False)
    source_url = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
