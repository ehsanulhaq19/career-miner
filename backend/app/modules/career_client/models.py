from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func

from app.database import Base


class CareerClient(Base):
    """SQLAlchemy model representing a company/client extracted from job listings."""

    __tablename__ = "career_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    emails = Column(JSON, default=list)
    official_website = Column(Text, nullable=True)
    name = Column(String(500), nullable=True)
    location = Column(String(500), nullable=True)
    detail = Column(Text, nullable=True)
    link = Column(Text, nullable=True)
    size = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
