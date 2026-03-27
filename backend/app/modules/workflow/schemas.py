from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkflowTaskInput(BaseModel):
    """Payload for creating or updating a workflow task."""

    linked_task_model: str
    linked_task_model_data: dict = Field(default_factory=dict)
    priority: int = 0
    is_active: bool = True


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a workflow with tasks."""

    name: str
    next_execution_duration_minutes: int = 60
    meta_data: dict = Field(default_factory=dict)
    is_active: bool = True
    tasks: list[WorkflowTaskInput] = Field(default_factory=list)


class WorkflowUpdateRequest(BaseModel):
    """Request body for partial workflow updates."""

    name: str | None = None
    next_execution_duration_minutes: int | None = None
    meta_data: dict | None = None
    is_active: bool | None = None


class WorkflowTaskUpdateRequest(BaseModel):
    """Request body for updating a single workflow task."""

    linked_task_model: str | None = None
    linked_task_model_data: dict | None = None
    priority: int | None = None
    is_active: bool | None = None


class WorkflowTaskResponse(BaseModel):
    """Serialized workflow task template."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    linked_task_model: str
    linked_task_model_data: dict = Field(default_factory=dict)
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("linked_task_model_data", mode="before")
    @classmethod
    def coerce_task_data(cls, v: dict | None) -> dict:
        return v if v is not None else {}


class WorkflowResponse(BaseModel):
    """Serialized workflow definition."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    next_execution_duration_minutes: int
    user_id: int
    meta_data: dict = Field(default_factory=dict)
    is_active: bool
    last_execution_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("meta_data", mode="before")
    @classmethod
    def coerce_meta(cls, v: dict | None) -> dict:
        return v if v is not None else {}


class WorkflowDetailResponse(WorkflowResponse):
    """Workflow with nested tasks and aggregate stats."""

    tasks: list[WorkflowTaskResponse] = Field(default_factory=list)
    total_jobs_executed: int = 0
    last_execution_started_at: datetime | None = None


class WorkflowListResponse(BaseModel):
    """Paginated workflow list."""

    items: list[WorkflowResponse]
    total: int


class WorkflowJobResponse(BaseModel):
    """One execution step instance."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_execution_id: int
    workflow_task_id: int
    status: str
    created_resource_type: str | None = None
    created_resource_id: int | None = None
    error_detail: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    meta_data: dict = Field(default_factory=dict)


class WorkflowLogResponse(BaseModel):
    """Audit log line for a workflow job."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_job_id: int
    action: str
    detail: str | None = None
    meta_data: dict = Field(default_factory=dict)
    created_at: datetime


class WorkflowExecutionResponse(BaseModel):
    """One run of a workflow."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    user_id: int
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    meta_data: dict = Field(default_factory=dict)
    created_at: datetime

    @field_validator("meta_data", mode="before")
    @classmethod
    def coerce_meta(cls, v: dict | None) -> dict:
        return v if v is not None else {}


class WorkflowExecutionDetailResponse(WorkflowExecutionResponse):
    """Execution with jobs and optional nested logs."""

    workflow_name: str | None = None
    jobs: list[WorkflowJobResponse] = Field(default_factory=list)
    logs_by_job_id: dict[int, list[WorkflowLogResponse]] = Field(default_factory=dict)


class WorkflowExecutionListResponse(BaseModel):
    """Paginated execution history."""

    items: list[WorkflowExecutionResponse]
    total: int
