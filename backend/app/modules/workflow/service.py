import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.database import async_session
from app.modules.career_job.crud import (
    get_career_client_ids_for_career_jobs,
    get_career_job_ids_by_scrap_job_id,
)
from app.modules.job_application.crud import (
    get_job_application_ids_for_user_by_career_jobs,
)
from app.modules.job_site.crud import get_job_site_by_id
from app.modules.scrap_job.crud import create_scrap_job
from app.modules.scrap_job.models import ScrapJobStatus
from app.modules.scraper.service import ScraperService
from app.modules.workflow import crud as workflow_crud
from app.modules.workflow.models import (
    LinkedTaskModelName,
    WorkflowExecutionStatus,
    WorkflowJobStatus,
)
from app.modules.workflow.schemas import (
    WorkflowCreateRequest,
    WorkflowDetailResponse,
    WorkflowExecutionDetailResponse,
    WorkflowExecutionListResponse,
    WorkflowExecutionResponse,
    WorkflowJobResponse,
    WorkflowListResponse,
    WorkflowLogResponse,
    WorkflowResponse,
    WorkflowTaskInput,
    WorkflowTaskResponse,
    WorkflowUpdateRequest,
)
from app.modules.websocket.service import broadcast_workflow_event

logger = logging.getLogger(__name__)


async def _wf_append_log(
    db: AsyncSession,
    workflow_job_id: int,
    action: str,
    detail: str | None,
    meta_data: dict | None,
    user_id: int,
) -> None:
    """Persist workflow log and notify subscribers."""
    log = await workflow_crud.create_workflow_log(
        db,
        {
            "workflow_job_id": workflow_job_id,
            "action": action,
            "detail": detail,
            "meta_data": meta_data or {},
        },
    )
    await db.flush()
    payload = WorkflowLogResponse.model_validate(log).model_dump()
    if hasattr(payload.get("created_at"), "isoformat"):
        payload["created_at"] = payload["created_at"].isoformat()
    await broadcast_workflow_event(
        user_id,
        {
            "event": "workflow_log",
            "workflow_job_id": workflow_job_id,
            "log": payload,
        },
    )


def _resolve_resource(delta: dict) -> tuple[str | None, int | None]:
    """Map context delta to primary resource type/id for the workflow job row."""
    if "scrap_job_id" in delta:
        return LinkedTaskModelName.SCRAP_JOB.value, delta["scrap_job_id"]
    if "scrap_client_job_id" in delta:
        return LinkedTaskModelName.SCRAP_CLIENT_JOB.value, delta["scrap_client_job_id"]
    if "bulk_job_application_id" in delta:
        return LinkedTaskModelName.BULK_JOB_APPLICATION.value, delta["bulk_job_application_id"]
    if "bulk_job_application_email_send_id" in delta:
        return (
            LinkedTaskModelName.BULK_JOB_APPLICATION_EMAIL_SEND.value,
            delta["bulk_job_application_email_send_id"],
        )
    return None, None


async def _dispatch_scrap_job(
    data: dict,
    user_id: int,
    execution_id: int,
) -> dict:
    """Create a scrap job and run the site scraper to completion."""
    _ = user_id
    async with async_session() as db:
        site = await get_job_site_by_id(db, data["job_site_id"])
        if site is None:
            raise NotFoundException(detail="Job site not found")
        ts = int(datetime.now(timezone.utc).timestamp())
        scrap_job = await create_scrap_job(
            db,
            {
                "name": data.get("name") or f"wf_exec_{execution_id}_{ts}",
                "job_site_id": site.id,
                "status": ScrapJobStatus.PENDING.value,
                "meta_data": {
                    **(data.get("meta_data") or {}),
                    "workflow_execution_id": execution_id,
                },
            },
        )
        await db.commit()
        sid = scrap_job.id
    from app.modules.scrap_job.crud import get_scrap_job_by_id

    async with async_session() as db:
        site = await get_job_site_by_id(db, data["job_site_id"])
        scrap_job_row = await get_scrap_job_by_id(db, sid)
        if site is None or scrap_job_row is None:
            raise NotFoundException(detail="Scrap job or site missing")
        scraper = ScraperService()
        await scraper.scrape_job_site(
            db,
            site,
            scrap_job_row,
            categories=data.get("categories"),
            max_pages_per_scrap=data.get("max_pages_per_scrap"),
            process_with_llm=data.get("process_with_llm", True),
            load_more_on_scroll=data.get("load_more_on_scroll", False),
            max_scroll=data.get("max_scroll", 10),
            depth_levels=data.get("depth_levels", 0),
        )
    async with async_session() as db:
        cj_ids = await get_career_job_ids_by_scrap_job_id(db, sid)
    cc_ids = []
    if cj_ids:
        async with async_session() as db:
            cc_ids = await get_career_client_ids_for_career_jobs(db, cj_ids)
    return {
        "scrap_job_id": sid,
        "career_job_ids": cj_ids,
        "career_client_ids": cc_ids,
    }


async def _dispatch_scrap_client_job(
    data: dict,
    user_id: int,
    execution_id: int,
    context: dict,
) -> dict:
    """Create a scrap client job and await the matching runner."""
    _ = user_id
    mode = data.get("mode") or "site"
    from app.modules.scrap_client.crud import create_scrap_client_job
    from app.modules.scrap_client.models import ScrapClientJobStatus
    from app.modules.scrap_client.services.url_utils import normalize_url
    from app.modules.scrap_client.service import (
        _run_client_email_scraper,
        _run_client_site_scraper,
        _run_client_url_scraper,
    )

    ts = int(datetime.now(timezone.utc).timestamp())
    meta = {**(data.get("meta_data") or {}), "workflow_execution_id": execution_id}

    if mode == "site":
        cs_id = data["client_site_id"]
        async with async_session() as db:
            sj = await create_scrap_client_job(
                db,
                {
                    "name": data.get("name") or f"wf_sc_site_{execution_id}_{ts}",
                    "client_site_id": cs_id,
                    "status": ScrapClientJobStatus.PENDING.value,
                    "meta_data": {**meta, "client_site_id": cs_id},
                },
            )
            await db.commit()
            sid = sj.id
        await _run_client_site_scraper(sid, cs_id, is_test_mode=False)
        return {"scrap_client_job_id": sid}

    if mode == "url":
        raw_url = data.get("url")
        if not raw_url:
            raise BadRequestException(detail="url required for scrap client url mode")
        nu = normalize_url(raw_url)
        if not nu:
            raise BadRequestException(detail="Invalid url")
        async with async_session() as db:
            sj = await create_scrap_client_job(
                db,
                {
                    "name": data.get("name") or f"wf_sc_url_{execution_id}_{ts}",
                    "source_url": nu,
                    "status": ScrapClientJobStatus.PENDING.value,
                    "meta_data": {**meta, "url": nu},
                },
            )
            await db.commit()
            sid = sj.id
        await _run_client_url_scraper(sid, nu)
        return {"scrap_client_job_id": sid}

    if mode == "email":
        client_ids = list(data.get("client_ids") or [])
        if data.get("use_previous_career_clients"):
            cj = context.get("career_job_ids") or []
            if cj:
                async with async_session() as db:
                    client_ids = await get_career_client_ids_for_career_jobs(db, cj)
        only_without = bool(data.get("only_clients_without_emails", False))
        url = data.get("url")
        async with async_session() as db:
            sj = await create_scrap_client_job(
                db,
                {
                    "name": data.get("name") or f"wf_sc_em_{execution_id}_{ts}",
                    "status": ScrapClientJobStatus.PENDING.value,
                    "meta_data": {
                        **meta,
                        "client_ids": client_ids or None,
                        "only_clients_without_emails": only_without,
                        "url": url,
                    },
                },
            )
            await db.commit()
            sid = sj.id
        await _run_client_email_scraper(
            sid,
            client_ids or None,
            only_without,
            url=url,
            is_test_mode=False,
        )
        return {"scrap_client_job_id": sid}

    raise BadRequestException(detail=f"Unknown scrap client mode: {mode}")


async def _dispatch_bulk_job_application(
    data: dict,
    user_id: int,
    execution_id: int,
    context: dict,
) -> dict:
    """Run bulk job application creation to completion."""
    _ = execution_id
    from app.modules.job_application.service import (
        run_bulk_job_application_background,
        start_bulk_job_application,
    )

    resume_id = data["resume_id"]
    career_job_ids = list(data.get("career_job_ids") or [])
    if data.get("use_previous_career_jobs"):
        career_job_ids = list(context.get("career_job_ids") or [])
    if not career_job_ids:
        raise BadRequestException(detail="No career_job_ids for bulk applications")
    async with async_session() as db:
        bulk = await start_bulk_job_application(
            db, resume_id, career_job_ids, user_id
        )
        bid = bulk.id
        await db.commit()
    await run_bulk_job_application_background(
        bid, resume_id, career_job_ids, user_id
    )
    async with async_session() as db:
        ja_ids = await get_job_application_ids_for_user_by_career_jobs(
            db, user_id, career_job_ids
        )
    return {
        "bulk_job_application_id": bid,
        "job_application_ids": ja_ids,
    }


async def _dispatch_bulk_email(
    data: dict,
    user_id: int,
    execution_id: int,
    context: dict,
) -> dict:
    """Run bulk job application email send to completion."""
    _ = execution_id
    from app.modules.job_application.service import (
        run_bulk_job_application_email_background,
        start_bulk_job_application_email_send,
    )

    ja_ids = list(data.get("job_application_ids") or [])
    if data.get("use_previous_job_applications"):
        ja_ids = list(context.get("job_application_ids") or [])
    if not ja_ids:
        raise BadRequestException(detail="No job_application_ids for bulk email")
    raw_min = data.get("min_similarity_score")
    min_similarity = None
    if raw_min is not None:
        try:
            min_similarity = float(raw_min)
        except (TypeError, ValueError) as e:
            raise BadRequestException(
                detail="min_similarity_score must be a number"
            ) from e
        if min_similarity < 0 or min_similarity > 100:
            raise BadRequestException(
                detail="min_similarity_score must be between 0 and 100"
            )
    async with async_session() as db:
        out = await start_bulk_job_application_email_send(
            db,
            ja_ids,
            user_id,
            min_similarity_score=min_similarity,
        )
        bulk_id = out["id"]
        filtered_ja_ids = out["job_application_ids"]
        await db.commit()
    await run_bulk_job_application_email_background(
        bulk_id, filtered_ja_ids, user_id
    )
    return {"bulk_job_application_email_send_id": bulk_id}


async def dispatch_workflow_task(
    model_name: str,
    data: dict,
    context: dict,
    user_id: int,
    execution_id: int,
) -> dict:
    """Run a single template task and return context fields to merge."""
    if model_name == LinkedTaskModelName.SCRAP_JOB.value:
        return await _dispatch_scrap_job(data, user_id, execution_id)
    if model_name == LinkedTaskModelName.SCRAP_CLIENT_JOB.value:
        return await _dispatch_scrap_client_job(data, user_id, execution_id, context)
    if model_name == LinkedTaskModelName.BULK_JOB_APPLICATION.value:
        return await _dispatch_bulk_job_application(data, user_id, execution_id, context)
    if model_name == LinkedTaskModelName.BULK_JOB_APPLICATION_EMAIL_SEND.value:
        return await _dispatch_bulk_email(data, user_id, execution_id, context)
    raise BadRequestException(detail=f"Unsupported linked_task_model: {model_name}")


async def execute_workflow_run(workflow_id: int) -> None:
    """Execute all active tasks for a workflow in priority order."""
    async with async_session() as db:
        wf = await workflow_crud.get_workflow_by_id(db, workflow_id)
        if wf is None or not wf.is_active:
            return
        user_id = wf.user_id
        ex = await workflow_crud.create_workflow_execution(
            db,
            {
                "workflow_id": wf.id,
                "user_id": user_id,
                "status": WorkflowExecutionStatus.IN_PROGRESS.value,
                "meta_data": {"context": {}},
            },
        )
        await workflow_crud.touch_workflow_last_execution(db, wf.id)
        await db.flush()
        ex_id = ex.id
        await db.commit()

    tasks = []
    async with async_session() as db:
        tasks = await workflow_crud.list_workflow_tasks(db, workflow_id)
    active = [t for t in tasks if t.is_active]
    active.sort(key=lambda x: (-x.priority, x.id))
    context: dict = {}

    for task in active:
        wj_id = None
        try:
            async with async_session() as db:
                wj = await workflow_crud.create_workflow_job(
                    db,
                    {
                        "workflow_execution_id": ex_id,
                        "workflow_task_id": task.id,
                        "status": WorkflowJobStatus.IN_PROGRESS.value,
                        "started_at": datetime.now(timezone.utc).replace(tzinfo=None),
                    },
                )
                await db.flush()
                wj_id = wj.id
                await db.commit()
            await broadcast_workflow_event(
                user_id,
                {
                    "event": "workflow_job_started",
                    "workflow_execution_id": ex_id,
                    "workflow_job_id": wj_id,
                    "workflow_task_id": task.id,
                },
            )
            delta = await dispatch_workflow_task(
                task.linked_task_model,
                dict(task.linked_task_model_data or {}),
                context,
                user_id,
                ex_id,
            )
            context.update(delta)
            rtype, rid = _resolve_resource(delta)
            async with async_session() as db:
                ex_row = await workflow_crud.get_workflow_execution_by_id(db, ex_id)
                if ex_row:
                    meta = dict(ex_row.meta_data or {})
                    meta["context"] = context
                    await workflow_crud.update_workflow_execution(
                        db, ex_id, {"meta_data": meta}
                    )
                if wj_id:
                    await workflow_crud.update_workflow_job(
                        db,
                        wj_id,
                        {
                            "status": WorkflowJobStatus.COMPLETED.value,
                            "completed_at": datetime.now(timezone.utc).replace(
                                tzinfo=None
                            ),
                            "created_resource_type": rtype,
                            "created_resource_id": rid,
                        },
                    )
                    await _wf_append_log(
                        db,
                        wj_id,
                        "task_completed",
                        f"model={task.linked_task_model}",
                        {"delta_keys": list(delta.keys())},
                        user_id,
                    )
                await db.commit()
            await broadcast_workflow_event(
                user_id,
                {
                    "event": "workflow_job_completed",
                    "workflow_execution_id": ex_id,
                    "workflow_job_id": wj_id,
                },
            )
        except Exception as e:
            logger.exception("Workflow task error workflow_id=%s task_id=%s", workflow_id, task.id)
            async with async_session() as db:
                if wj_id:
                    await workflow_crud.update_workflow_job(
                        db,
                        wj_id,
                        {
                            "status": WorkflowJobStatus.ERROR.value,
                            "error_detail": str(e),
                            "completed_at": datetime.now(timezone.utc).replace(
                                tzinfo=None
                            ),
                        },
                    )
                    await _wf_append_log(
                        db,
                        wj_id,
                        "task_error",
                        str(e),
                        {"error_type": type(e).__name__},
                        user_id,
                    )
                await db.commit()
            await broadcast_workflow_event(
                user_id,
                {
                    "event": "workflow_job_error",
                    "workflow_execution_id": ex_id,
                    "workflow_job_id": wj_id,
                    "error": str(e),
                },
            )

    async with async_session() as db:
        await workflow_crud.update_workflow_execution(
            db,
            ex_id,
            {
                "status": WorkflowExecutionStatus.COMPLETED.value,
                "completed_at": datetime.now(timezone.utc).replace(tzinfo=None),
            },
        )
        await db.commit()
    await broadcast_workflow_event(
        user_id,
        {"event": "workflow_execution_completed", "workflow_execution_id": ex_id},
    )


async def tick_due_workflows() -> None:
    """Start background runs for workflows that are due."""
    async with async_session() as db:
        due = await workflow_crud.list_due_workflows(db)
        await db.commit()
    print("----------due--------", due)
    for wf in due:
        asyncio.create_task(execute_workflow_run(wf.id))


async def create_workflow_svc(
    db: AsyncSession,
    body: WorkflowCreateRequest,
    user_id: int,
) -> WorkflowDetailResponse:
    """Create workflow and tasks."""
    wf = await workflow_crud.create_workflow(
        db,
        {
            "name": body.name,
            "next_execution_duration_minutes": body.next_execution_duration_minutes,
            "user_id": user_id,
            "meta_data": body.meta_data or {},
            "is_active": body.is_active,
        },
    )
    await db.flush()
    for t in body.tasks:
        await workflow_crud.create_workflow_task(
            db,
            {
                "workflow_id": wf.id,
                "linked_task_model": t.linked_task_model,
                "linked_task_model_data": t.linked_task_model_data or {},
                "priority": t.priority,
                "is_active": t.is_active,
            },
        )
    await db.commit()
    return await get_workflow_detail(db, wf.id, user_id)


async def update_workflow_svc(
    db: AsyncSession,
    workflow_id: int,
    body: WorkflowUpdateRequest,
    user_id: int,
) -> WorkflowDetailResponse:
    """Patch workflow fields."""
    wf = await workflow_crud.get_workflow_by_id(db, workflow_id)
    if wf is None or wf.user_id != user_id:
        raise NotFoundException(detail="Workflow not found")
    data = body.model_dump(exclude_unset=True)
    await workflow_crud.update_workflow(db, workflow_id, data)
    await db.commit()
    return await get_workflow_detail(db, workflow_id, user_id)


async def delete_workflow_task_svc(
    db: AsyncSession,
    workflow_id: int,
    task_id: int,
    user_id: int,
) -> None:
    """Remove a task from a workflow."""
    wf = await workflow_crud.get_workflow_by_id(db, workflow_id)
    if wf is None or wf.user_id != user_id:
        raise NotFoundException(detail="Workflow not found")
    ok = await workflow_crud.delete_workflow_task(db, task_id, workflow_id)
    if not ok:
        raise NotFoundException(detail="Workflow task not found")
    await db.commit()


async def add_workflow_task_svc(
    db: AsyncSession,
    workflow_id: int,
    body: WorkflowTaskInput,
    user_id: int,
) -> WorkflowTaskResponse:
    """Create a new task row on an existing workflow."""
    wf = await workflow_crud.get_workflow_by_id(db, workflow_id)
    if wf is None or wf.user_id != user_id:
        raise NotFoundException(detail="Workflow not found")
    row = await workflow_crud.create_workflow_task(
        db,
        {
            "workflow_id": workflow_id,
            "linked_task_model": body.linked_task_model,
            "linked_task_model_data": body.linked_task_model_data or {},
            "priority": body.priority,
            "is_active": body.is_active,
        },
    )
    await db.commit()
    return WorkflowTaskResponse.model_validate(row)


async def update_workflow_task_svc(
    db: AsyncSession,
    workflow_id: int,
    task_id: int,
    data: dict,
    user_id: int,
) -> WorkflowTaskResponse:
    """Patch a workflow task."""
    wf = await workflow_crud.get_workflow_by_id(db, workflow_id)
    if wf is None or wf.user_id != user_id:
        raise NotFoundException(detail="Workflow not found")
    task = await workflow_crud.get_workflow_task_by_id(db, task_id)
    if task is None or task.workflow_id != workflow_id:
        raise NotFoundException(detail="Workflow task not found")
    updated = await workflow_crud.update_workflow_task(db, task_id, data)
    await db.commit()
    return WorkflowTaskResponse.model_validate(updated)


async def list_workflows_svc(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> WorkflowListResponse:
    """List workflows for current user."""
    items, total = await workflow_crud.list_workflows_for_user(
        db, user_id, skip=skip, limit=limit
    )
    return WorkflowListResponse(
        items=[WorkflowResponse.model_validate(i) for i in items],
        total=total,
    )


async def get_workflow_detail(
    db: AsyncSession,
    workflow_id: int,
    user_id: int,
) -> WorkflowDetailResponse:
    """Return workflow with tasks and execution stats."""
    wf = await workflow_crud.get_workflow_by_id(db, workflow_id)
    if wf is None or wf.user_id != user_id:
        raise NotFoundException(detail="Workflow not found")
    tasks = await workflow_crud.list_workflow_tasks(db, workflow_id)
    total_jobs = await workflow_crud.count_workflow_jobs_for_workflow(db, workflow_id)
    last_ex = await workflow_crud.get_last_execution_for_workflow(db, workflow_id)
    base = WorkflowResponse.model_validate(wf)
    detail = WorkflowDetailResponse(
        **base.model_dump(),
        tasks=[WorkflowTaskResponse.model_validate(t) for t in tasks],
        total_jobs_executed=total_jobs,
        last_execution_started_at=last_ex.started_at if last_ex else None,
    )
    return detail


async def list_executions_svc(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> WorkflowExecutionListResponse:
    """Paginated execution history."""
    items, total = await workflow_crud.list_workflow_executions_for_user(
        db, user_id, skip=skip, limit=limit
    )
    return WorkflowExecutionListResponse(
        items=[WorkflowExecutionResponse.model_validate(i) for i in items],
        total=total,
    )


async def get_execution_detail_svc(
    db: AsyncSession,
    execution_id: int,
    user_id: int,
) -> WorkflowExecutionDetailResponse:
    """Execution with jobs and logs grouped."""
    ex = await workflow_crud.get_workflow_execution_by_id(db, execution_id)
    if ex is None or ex.user_id != user_id:
        raise NotFoundException(detail="Workflow execution not found")
    wf = await workflow_crud.get_workflow_by_id(db, ex.workflow_id)
    jobs = await workflow_crud.list_workflow_jobs_for_execution(db, execution_id)
    logs_map: dict[int, list] = {}
    for j in jobs:
        logs = await workflow_crud.list_workflow_logs_for_job(db, j.id)
        logs_map[j.id] = [WorkflowLogResponse.model_validate(x) for x in logs]
    base = WorkflowExecutionResponse.model_validate(ex)
    return WorkflowExecutionDetailResponse(
        **base.model_dump(),
        workflow_name=wf.name if wf else None,
        jobs=[WorkflowJobResponse.model_validate(j) for j in jobs],
        logs_by_job_id=logs_map,
    )


async def trigger_workflow_run_svc(
    db: AsyncSession,
    workflow_id: int,
    user_id: int,
) -> dict:
    """Fire workflow execution asynchronously."""
    wf = await workflow_crud.get_workflow_by_id(db, workflow_id)
    if wf is None or wf.user_id != user_id:
        raise NotFoundException(detail="Workflow not found")
    asyncio.create_task(execute_workflow_run(workflow_id))
    return {"status": "started", "workflow_id": workflow_id}
