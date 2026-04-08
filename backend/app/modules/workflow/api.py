from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.workflow.schemas import (
    WorkflowCreateRequest,
    WorkflowDetailResponse,
    WorkflowExecutionDetailResponse,
    WorkflowExecutionListResponse,
    WorkflowListResponse,
    WorkflowTaskInput,
    WorkflowTaskResponse,
    WorkflowTaskUpdateRequest,
    WorkflowUpdateRequest,
)
from app.modules.workflow.service import (
    add_workflow_task_svc,
    create_workflow_svc,
    delete_workflow_task_svc,
    get_execution_detail_svc,
    get_workflow_detail,
    list_executions_svc,
    list_workflows_svc,
    resume_workflow_execution_svc,
    trigger_workflow_run_svc,
    update_workflow_svc,
    update_workflow_task_svc,
)

router = APIRouter()


@router.post("/", response_model=WorkflowDetailResponse, status_code=201)
async def create_workflow_endpoint(
    body: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowDetailResponse:
    """Create a workflow and its task templates."""
    return await create_workflow_svc(db, body, current_user.id)


@router.patch("/{workflow_id}", response_model=WorkflowDetailResponse)
async def update_workflow_endpoint(
    workflow_id: int,
    body: WorkflowUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowDetailResponse:
    """Update workflow name, schedule interval, active flag, or meta_data."""
    return await update_workflow_svc(db, workflow_id, body, current_user.id)


@router.post(
    "/{workflow_id}/tasks",
    response_model=WorkflowTaskResponse,
    status_code=201,
)
async def add_workflow_task_endpoint(
    workflow_id: int,
    body: WorkflowTaskInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowTaskResponse:
    """Append a new task template to an existing workflow."""
    return await add_workflow_task_svc(db, workflow_id, body, current_user.id)


@router.delete("/{workflow_id}/tasks/{task_id}", status_code=204)
async def delete_workflow_task_endpoint(
    workflow_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a workflow task."""
    await delete_workflow_task_svc(db, workflow_id, task_id, current_user.id)


@router.patch(
    "/{workflow_id}/tasks/{task_id}",
    response_model=WorkflowTaskResponse,
)
async def update_workflow_task_endpoint(
    workflow_id: int,
    task_id: int,
    body: WorkflowTaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowTaskResponse:
    """Update task model, payload JSON, priority, or active flag."""
    return await update_workflow_task_svc(
        db,
        workflow_id,
        task_id,
        body.model_dump(exclude_unset=True),
        current_user.id,
    )


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowListResponse:
    """List workflow definitions for the current user."""
    return await list_workflows_svc(db, current_user.id, skip=skip, limit=limit)


@router.get("/executions", response_model=WorkflowExecutionListResponse)
async def list_workflow_executions_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowExecutionListResponse:
    """List all workflow runs for the current user, newest first."""
    return await list_executions_svc(db, current_user.id, skip=skip, limit=limit)


@router.get(
    "/executions/{execution_id}",
    response_model=WorkflowExecutionDetailResponse,
)
async def get_workflow_execution_endpoint(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowExecutionDetailResponse:
    """Return one execution with jobs and logs."""
    return await get_execution_detail_svc(db, execution_id, current_user.id)


@router.post("/executions/{execution_id}/resume")
async def resume_workflow_execution_endpoint(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Continue an in-progress run from its current step (re-runs in-progress work)."""
    return await resume_workflow_execution_svc(
        db, execution_id, current_user.id
    )


@router.get("/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow_endpoint(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowDetailResponse:
    """Return workflow detail, tasks, and execution stats."""
    return await get_workflow_detail(db, workflow_id, current_user.id)


@router.post("/{workflow_id}/run", response_model=dict)
async def run_workflow_now_endpoint(
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger an immediate workflow run in the background."""
    return await trigger_workflow_run_svc(db, workflow_id, current_user.id)
