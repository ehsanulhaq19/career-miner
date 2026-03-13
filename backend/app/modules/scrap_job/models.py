import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, func

from app.database import Base


class ScrapJobLogStatus(str, enum.Enum):
    """Enumeration of scrap job log status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"


class ScrapJobLog(Base):
    """SQLAlchemy model representing a scrap job progress log entry."""

    __tablename__ = "scrap_job_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scrap_job_id = Column(Integer, ForeignKey("scrap_jobs.id"), nullable=False)
    action = Column(String(255), nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    status = Column(
        String(50),
        default=ScrapJobLogStatus.PENDING.value,
        nullable=False,
    )
    details = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ScrapJobStatus(str, enum.Enum):
    """Enumeration of possible scrap job execution states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"
    STOPPED = "stopped"


class ScrapJob(Base):
    """SQLAlchemy model representing a scraping job execution."""

    __tablename__ = "scrap_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    job_site_id = Column(Integer, ForeignKey("job_sites.id"), nullable=False)
    status = Column(
        String(50),
        default=ScrapJobStatus.PENDING.value,
        nullable=False,
    )
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
