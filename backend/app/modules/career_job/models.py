from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func

from app.database import Base


class CareerJobUser(Base):
    """SQLAlchemy model representing a user's seen status for a career job."""

    __tablename__ = "career_job_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    career_job_id = Column(Integer, ForeignKey("career_jobs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("career_job_id", "user_id", name="uq_career_job_user"),)


class CareerJob(Base):
    """SQLAlchemy model representing a scraped career job listing."""

    __tablename__ = "career_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    job_site_id = Column(Integer, ForeignKey("job_sites.id"), nullable=False)
    scrap_job_id = Column(Integer, ForeignKey("scrap_jobs.id"), nullable=False)
    career_client_id = Column(Integer, ForeignKey("career_clients.id"), nullable=True)
    meta_data = Column(JSON, default=dict)
    parsed_data = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
