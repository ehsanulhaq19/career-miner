from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func

from app.database import Base


class JobApplication(Base):
    """
    SQLAlchemy model representing a job application with generated content.
    """

    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_name = Column(String(100), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    applied_on = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)
    subject = Column(String(500), nullable=True)
    cover_letter = Column(Text, nullable=True)
    output_resume_path = Column(String(1000), nullable=True)
    career_job_id = Column(Integer, ForeignKey("career_jobs.id"), nullable=False)
    similarity_score = Column(Float, nullable=True)
    meta_data = Column(JSON, default=dict)
    is_email_send = Column(Boolean, default=False, nullable=False)
    to_emails = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
