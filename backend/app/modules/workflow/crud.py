from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.workflow.models import (
    Workflow,
    WorkflowExecution,
    WorkflowJob,
    WorkflowLog,
    WorkflowTask,
)


async def create_workflow(db: AsyncSession, data: dict) -> Workflow:
    """Persist a new workflow definition."""
    row = Workflow(**data)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def update_workflow(
    db: AsyncSession, workflow_id: int, data: dict
) -> Workflow | None:
    """Merge fields onto an existing workflow."""
    wf = await get_workflow_by_id(db, workflow_id)
    if wf is None:
        return None
    for key, value in data.items():
        if value is not None and hasattr(wf, key):
            setattr(wf, key, value)
    await db.flush()
    await db.refresh(wf)
    return wf


async def get_workflow_by_id(db: AsyncSession, workflow_id: int) -> Workflow | None:
    """Return a workflow by primary key."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    return result.scalars().first()


async def list_workflows_for_user(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[Workflow], int]:
    """Return paginated workflows owned by the user."""
    q = (
        select(Workflow)
        .where(Workflow.user_id == user_id)
        .order_by(Workflow.id.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(q)
    items = list(result.scalars().all())
    cq = select(func.count(Workflow.id)).where(Workflow.user_id == user_id)
    total = (await db.execute(cq)).scalar() or 0
    return items, total


async def delete_workflow_task(
    db: AsyncSession, task_id: int, workflow_id: int
) -> bool:
    """Delete a task if it belongs to the workflow."""
    task = await get_workflow_task_by_id(db, task_id)
    if task is None or task.workflow_id != workflow_id:
        return False
    await db.delete(task)
    await db.flush()
    return True


async def create_workflow_task(db: AsyncSession, data: dict) -> WorkflowTask:
    """Create a workflow task row."""
    row = WorkflowTask(**data)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def get_workflow_task_by_id(db: AsyncSession, task_id: int) -> WorkflowTask | None:
    """Return a workflow task by id."""
    result = await db.execute(
        select(WorkflowTask).where(WorkflowTask.id == task_id)
    )
    return result.scalars().first()


async def update_workflow_task(
    db: AsyncSession, task_id: int, data: dict
) -> WorkflowTask | None:
    """Update an existing workflow task."""
    task = await get_workflow_task_by_id(db, task_id)
    if task is None:
        return None
    for key, value in data.items():
        if hasattr(task, key):
            setattr(task, key, value)
    await db.flush()
    await db.refresh(task)
    return task


async def list_workflow_tasks(
    db: AsyncSession, workflow_id: int
) -> list[WorkflowTask]:
    """Return tasks for a workflow ordered by priority descending."""
    result = await db.execute(
        select(WorkflowTask)
        .where(WorkflowTask.workflow_id == workflow_id)
        .order_by(WorkflowTask.priority.desc(), WorkflowTask.id.asc())
    )
    return list(result.scalars().all())


async def create_workflow_execution(db: AsyncSession, data: dict) -> WorkflowExecution:
    """Create a workflow run record."""
    row = WorkflowExecution(**data)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def update_workflow_execution(
    db: AsyncSession, execution_id: int, data: dict
) -> WorkflowExecution | None:
    """Update workflow execution fields."""
    ex = await get_workflow_execution_by_id(db, execution_id)
    if ex is None:
        return None
    for key, value in data.items():
        if hasattr(ex, key):
            setattr(ex, key, value)
    await db.flush()
    await db.refresh(ex)
    return ex


async def get_workflow_execution_by_id(
    db: AsyncSession, execution_id: int
) -> WorkflowExecution | None:
    """Return one workflow execution."""
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
    )
    return result.scalars().first()


async def list_workflow_executions_for_user(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[WorkflowExecution], int]:
    """List executions for a user newest first."""
    q = (
        select(WorkflowExecution)
        .where(WorkflowExecution.user_id == user_id)
        .order_by(WorkflowExecution.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(q)
    items = list(result.scalars().all())
    cq = select(func.count(WorkflowExecution.id)).where(
        WorkflowExecution.user_id == user_id
    )
    total = (await db.execute(cq)).scalar() or 0
    return items, total


async def list_workflow_executions_for_workflow(
    db: AsyncSession,
    workflow_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[WorkflowExecution]:
    """Return recent executions for one workflow definition."""
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.workflow_id == workflow_id)
        .order_by(WorkflowExecution.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_workflow_job(db: AsyncSession, data: dict) -> WorkflowJob:
    """Create a per-step workflow job row."""
    row = WorkflowJob(**data)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def update_workflow_job(
    db: AsyncSession, workflow_job_id: int, data: dict
) -> WorkflowJob | None:
    """Update a workflow job."""
    j = await get_workflow_job_by_id(db, workflow_job_id)
    if j is None:
        return None
    for key, value in data.items():
        if hasattr(j, key):
            setattr(j, key, value)
    await db.flush()
    await db.refresh(j)
    return j


async def get_workflow_job_by_id(
    db: AsyncSession, workflow_job_id: int
) -> WorkflowJob | None:
    """Return workflow job by id."""
    result = await db.execute(
        select(WorkflowJob).where(WorkflowJob.id == workflow_job_id)
    )
    return result.scalars().first()


async def list_workflow_jobs_for_execution(
    db: AsyncSession, workflow_execution_id: int
) -> list[WorkflowJob]:
    """Return jobs for an execution ordered by id."""
    result = await db.execute(
        select(WorkflowJob)
        .where(WorkflowJob.workflow_execution_id == workflow_execution_id)
        .order_by(WorkflowJob.id.asc())
    )
    return list(result.scalars().all())


async def create_workflow_log(db: AsyncSession, data: dict) -> WorkflowLog:
    """Append a workflow log line."""
    row = WorkflowLog(**data)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def list_workflow_logs_for_job(
    db: AsyncSession, workflow_job_id: int
) -> list[WorkflowLog]:
    """Return logs for a workflow job."""
    result = await db.execute(
        select(WorkflowLog)
        .where(WorkflowLog.workflow_job_id == workflow_job_id)
        .order_by(WorkflowLog.created_at.asc())
    )
    return list(result.scalars().all())


async def list_due_workflows(
    db: AsyncSession,
) -> list[Workflow]:
    """Return active workflows whose interval has elapsed since last run."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(Workflow).where(Workflow.is_active.is_(True))
    )
    due: list[Workflow] = []
    for wf in result.scalars().all():
        if wf.last_execution_at is None:
            due.append(wf)
            continue
        delta_min = (now - wf.last_execution_at).total_seconds() / 60.0
        if delta_min >= float(wf.next_execution_duration_minutes or 0):
            due.append(wf)
    return due


async def touch_workflow_last_execution(
    db: AsyncSession, workflow_id: int
) -> None:
    """Stamp last_execution_at to now for scheduling."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.execute(
        update(Workflow)
        .where(Workflow.id == workflow_id)
        .values(last_execution_at=now)
    )
    await db.flush()


async def count_workflow_jobs_for_workflow(
    db: AsyncSession, workflow_id: int
) -> int:
    """Count all workflow job rows for any execution of this definition."""
    r = await db.execute(
        select(WorkflowExecution.id).where(
            WorkflowExecution.workflow_id == workflow_id
        )
    )
    eids = [row[0] for row in r.all()]
    if not eids:
        return 0
    result = await db.execute(
        select(func.count(WorkflowJob.id)).where(
            WorkflowJob.workflow_execution_id.in_(eids)
        )
    )
    return result.scalar() or 0


async def get_last_execution_for_workflow(
    db: AsyncSession, workflow_id: int
) -> WorkflowExecution | None:
    """Return most recent execution row for stats."""
    result = await db.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.workflow_id == workflow_id)
        .order_by(WorkflowExecution.started_at.desc())
        .limit(1)
    )
    return result.scalars().first()
