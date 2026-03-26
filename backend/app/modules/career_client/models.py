import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)

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
    meta_data = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class CareerClientEmailLog(Base):
    """
    SQLAlchemy pivot model linking career clients to related email logs.
    """

    __tablename__ = "career_client_email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    career_client_id = Column(
        Integer, ForeignKey("career_clients.id"), nullable=False
    )
    email_log_id = Column(Integer, ForeignKey("email_logs.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class BulkCareerClientEmailSendStatus(str, enum.Enum):
    """
    Enumeration of bulk career client email send execution states.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"


class BulkCareerClientEmailSend(Base):
    """
    SQLAlchemy model representing a bulk career client outreach email send run.
    """

    __tablename__ = "bulk_career_client_email_sends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        String(50),
        default=BulkCareerClientEmailSendStatus.PENDING.value,
        nullable=False,
    )
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BulkCareerClientEmailSendLog(Base):
    """
    SQLAlchemy model representing a bulk career client email send progress log.
    """

    __tablename__ = "bulk_career_client_email_send_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bulk_career_client_email_send_id = Column(
        Integer,
        ForeignKey("bulk_career_client_email_sends.id"),
        nullable=False,
    )
    action = Column(String(255), nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    details = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
