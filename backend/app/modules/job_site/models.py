from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, func

from app.database import Base


class JobSite(Base):
    """SQLAlchemy model representing a job site to be scraped."""

    __tablename__ = "job_sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    scrap_duration = Column(Integer, nullable=False, default=60)
    last_scrapped = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    categories = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
