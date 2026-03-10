import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


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
