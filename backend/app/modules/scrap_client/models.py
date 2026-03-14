import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, func

from app.database import Base


class ScrapClientLogStatus(str, enum.Enum):
    """Enumeration of scrap client log status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"


class ScrapClientLog(Base):
    """SQLAlchemy model representing a scrap client progress log entry."""

    __tablename__ = "scrap_client_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scrap_client_job_id = Column(
        Integer, ForeignKey("scrap_client_jobs.id"), nullable=False
    )
    action = Column(String(255), nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    status = Column(
        String(50),
        default=ScrapClientLogStatus.PENDING.value,
        nullable=False,
    )
    details = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ScrapClientJobStatus(str, enum.Enum):
    """Enumeration of possible scrap client job execution states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"
    STOPPED = "stopped"


class ScrapClientJob(Base):
    """SQLAlchemy model representing a client email scraping job execution."""

    __tablename__ = "scrap_client_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    status = Column(
        String(50),
        default=ScrapClientJobStatus.PENDING.value,
        nullable=False,
    )
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
