from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class Resume(Base):
    """
    SQLAlchemy model representing an uploaded resume file.
    """

    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    size = Column(Integer, nullable=False)
    extension = Column(String(20), nullable=False)
    file_path = Column(String(1000), nullable=True)
    content = Column(Text, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
