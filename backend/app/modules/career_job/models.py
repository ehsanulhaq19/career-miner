from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, func

from app.database import Base


class CareerJob(Base):
    """SQLAlchemy model representing a scraped career job listing."""

    __tablename__ = "career_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    job_site_id = Column(Integer, ForeignKey("job_sites.id"), nullable=False)
    scrap_job_id = Column(Integer, ForeignKey("scrap_jobs.id"), nullable=False)
    meta_data = Column(JSON, default=dict)
    parsed_data = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
