from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, func

from app.database import Base


class ClientSite(Base):
    """SQLAlchemy model representing a client site to be scraped for company data."""

    __tablename__ = "client_sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    scrap_duration = Column(Integer, nullable=False, default=60)
    last_scrapped = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


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
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
