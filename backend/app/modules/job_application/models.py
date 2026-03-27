import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)

from app.database import Base


class BulkJobApplicationLogStatus(str, enum.Enum):
    """Enumeration of bulk job application log status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"


class BulkJobApplicationLog(Base):
    """SQLAlchemy model representing a bulk job application progress log entry."""

    __tablename__ = "bulk_job_application_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bulk_job_application_id = Column(
        Integer, ForeignKey("bulk_job_applications.id"), nullable=False
    )
    action = Column(String(255), nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    status = Column(
        String(50),
        default=BulkJobApplicationLogStatus.PENDING.value,
        nullable=False,
    )
    details = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class BulkJobApplicationStatus(str, enum.Enum):
    """Enumeration of possible bulk job application execution states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"
    STOPPED = "stopped"


class BulkJobApplication(Base):
    """SQLAlchemy model representing a bulk job application creation run."""

    __tablename__ = "bulk_job_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    status = Column(
        String(50),
        default=BulkJobApplicationStatus.PENDING.value,
        nullable=False,
    )
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class JobApplicationBulkJobApplicationLink(Base):
    """
    SQLAlchemy pivot preserving each association between a job application and a bulk run.
    """

    __tablename__ = "job_application_bulk_job_application_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_application_id = Column(
        Integer, ForeignKey("job_applications.id"), nullable=False
    )
    bulk_job_application_id = Column(
        Integer, ForeignKey("bulk_job_applications.id"), nullable=False
    )
    created_at = Column(DateTime, server_default=func.now())


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


class JobApplicationEmailLog(Base):
    """
    SQLAlchemy pivot model linking job applications to their related email logs.
    """

    __tablename__ = "job_application_email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_application_id = Column(
        Integer, ForeignKey("job_applications.id"), nullable=False
    )
    email_log_id = Column(Integer, ForeignKey("email_logs.id"), nullable=False)
    bulk_job_application_email_send_id = Column(
        Integer,
        ForeignKey("bulk_job_application_email_sends.id"),
        nullable=True,
    )
    created_at = Column(DateTime, server_default=func.now())


class BulkJobApplicationEmailSendStatus(str, enum.Enum):
    """Enumeration of bulk job application email send execution states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"


class BulkJobApplicationEmailSend(Base):
    """
    SQLAlchemy model representing a bulk job application email send run.
    """

    __tablename__ = "bulk_job_application_email_sends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        String(50),
        default=BulkJobApplicationEmailSendStatus.PENDING.value,
        nullable=False,
    )
    min_similarity_score = Column(Float, nullable=True)
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BulkJobApplicationEmailSendLog(Base):
    """
    SQLAlchemy model representing a bulk job application email send progress log.
    """

    __tablename__ = "bulk_job_application_email_send_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bulk_job_application_email_send_id = Column(
        Integer,
        ForeignKey("bulk_job_application_email_sends.id"),
        nullable=False,
    )
    action = Column(String(255), nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    details = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
