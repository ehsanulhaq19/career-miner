import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, func

from app.database import Base


class WorkflowJobStatus(str, enum.Enum):
    """Enumeration of workflow step job execution states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"
    STOPPED = "stopped"


class WorkflowExecutionStatus(str, enum.Enum):
    """Enumeration of workflow run states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class LinkedTaskModelName(str, enum.Enum):
    """Known persisted job model names for workflow tasks."""

    SCRAP_JOB = "ScrapJob"
    SCRAP_CLIENT_JOB = "ScrapClientJob"
    BULK_JOB_APPLICATION = "BulkJobApplication"
    BULK_JOB_APPLICATION_EMAIL_SEND = "BulkJobApplicationEmailSend"


class Workflow(Base):
    """SQLAlchemy model representing an automated multi-step workflow definition."""

    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    next_execution_duration_minutes = Column(Integer, nullable=False, default=60)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    meta_data = Column(JSON, default=dict, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_execution_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WorkflowTask(Base):
    """
    SQLAlchemy model for a single step template: which job model to instantiate and with what data.
    """

    __tablename__ = "workflow_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    linked_task_model = Column(String(128), nullable=False)
    linked_task_model_data = Column(JSON, default=dict, nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WorkflowExecution(Base):
    """SQLAlchemy model for one scheduled or manual run of a workflow."""

    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        String(50),
        default=WorkflowExecutionStatus.PENDING.value,
        nullable=False,
    )
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class WorkflowJob(Base):
    """
    SQLAlchemy model for one task execution within a workflow run.
    """

    __tablename__ = "workflow_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_execution_id = Column(
        Integer, ForeignKey("workflow_executions.id"), nullable=False
    )
    workflow_task_id = Column(Integer, ForeignKey("workflow_tasks.id"), nullable=False)
    status = Column(
        String(50),
        default=WorkflowJobStatus.PENDING.value,
        nullable=False,
    )
    created_resource_type = Column(String(128), nullable=True)
    created_resource_id = Column(Integer, nullable=True)
    error_detail = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    meta_data = Column(JSON, default=dict, nullable=True)


class WorkflowLog(Base):
    """SQLAlchemy model for workflow step audit log lines."""

    __tablename__ = "workflow_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_job_id = Column(Integer, ForeignKey("workflow_jobs.id"), nullable=False)
    action = Column(String(255), nullable=False)
    detail = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
