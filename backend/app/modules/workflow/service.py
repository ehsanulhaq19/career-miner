import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
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
from app.modules.client_site.crud import get_client_site_by_id
from app.modules.job_site.crud import get_job_site_by_id
from app.modules.scrap_job.crud import create_scrap_job, get_scrap_job_by_id
from app.modules.scrap_client.crud import get_scrap_client_job_by_id
from app.modules.job_application.crud import (
    get_bulk_job_application_by_id,
    get_bulk_job_application_email_send_by_id,
    get_bulk_job_application_email_send_logs,
    get_bulk_job_application_logs_by_id,
)
from app.modules.scrap_job.models import ScrapJob, ScrapJobStatus
from app.modules.scraper.service import ScraperService
from app.modules.workflow import crud as workflow_crud
from app.modules.workflow.models import (
    LinkedTaskModelName,
    WorkflowExecutionStatus,
    WorkflowJob,
    WorkflowJobStatus,
    WorkflowTask,
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


async def _workflow_job_row_status_for_linked_task(
    linked_model: str, delta: dict
) -> str:
    """
    Step row status after dispatch: COMPLETED unless the linked job record is terminated.
    """
    from app.modules.job_application.crud import (
        get_bulk_job_application_by_id,
        get_bulk_job_application_email_send_by_id,
    )
    from app.modules.job_application.models import (
        BulkJobApplicationEmailSendStatus,
        BulkJobApplicationStatus,
    )
    from app.modules.scrap_client.crud import get_scrap_client_job_by_id
    from app.modules.scrap_client.models import ScrapClientJobStatus
    from app.modules.scrap_job.crud import get_scrap_job_by_id
    from app.modules.scrap_job.models import ScrapJobStatus

    async with async_session() as db:
        if linked_model == LinkedTaskModelName.SCRAP_JOB.value:
            sid = delta.get("scrap_job_id")
            if sid is not None:
                row = await get_scrap_job_by_id(db, int(sid))
                if row and row.status == ScrapJobStatus.TERMINATED.value:
                    return WorkflowJobStatus.TERMINATED.value
        elif linked_model == LinkedTaskModelName.SCRAP_CLIENT_JOB.value:
            sid = delta.get("scrap_client_job_id")
            if sid is not None:
                row = await get_scrap_client_job_by_id(db, int(sid))
                if row and row.status == ScrapClientJobStatus.TERMINATED.value:
                    return WorkflowJobStatus.TERMINATED.value
        elif linked_model == LinkedTaskModelName.BULK_JOB_APPLICATION.value:
            bid = delta.get("bulk_job_application_id")
            if bid is not None:
                row = await get_bulk_job_application_by_id(db, int(bid))
                if row and row.status == BulkJobApplicationStatus.TERMINATED.value:
                    return WorkflowJobStatus.TERMINATED.value
        elif linked_model == LinkedTaskModelName.BULK_JOB_APPLICATION_EMAIL_SEND.value:
            eid = delta.get("bulk_job_application_email_send_id")
            if eid is not None:
                row = await get_bulk_job_application_email_send_by_id(db, int(eid))
                if row and row.status == BulkJobApplicationEmailSendStatus.TERMINATED.value:
                    return WorkflowJobStatus.TERMINATED.value
    return WorkflowJobStatus.COMPLETED.value


async def _dispatch_scrap_job(
    data: dict,
    user_id: int,
    execution_id: int,
) -> dict:
    """Create a scrap job and run the site scraper to completion."""
    from app.modules.scrap_job.crud import get_scrap_job_by_id

    async with async_session() as db:
        site = await get_job_site_by_id(db, data["job_site_id"])
        if site is None or site.created_by != user_id:
            raise NotFoundException(detail="Job site not found")

        reuse = await db.execute(
            select(ScrapJob)
            .where(
                ScrapJob.workflow_execution_id == execution_id,
                ScrapJob.job_site_id == site.id,
                ScrapJob.created_by == user_id,
            )
            .order_by(ScrapJob.id.desc())
            .limit(1)
        )
        existing = reuse.scalars().first()
        if existing is not None and existing.status == ScrapJobStatus.COMPLETED.value:
            sid = existing.id
            await db.commit()
            async with async_session() as db_cj:
                cj_ids = await get_career_job_ids_by_scrap_job_id(
                    db_cj, sid, created_by=user_id
                )
            cc_ids: list[int] = []
            if cj_ids:
                async with async_session() as db_cc:
                    cc_ids = await get_career_client_ids_for_career_jobs(
                        db_cc, cj_ids, created_by=user_id
                    )
            return {
                "scrap_job_id": sid,
                "career_job_ids": cj_ids,
                "career_client_ids": cc_ids,
            }

        if existing is not None and existing.status in (
            ScrapJobStatus.PENDING.value,
            ScrapJobStatus.IN_PROGRESS.value,
        ):
            sid = existing.id
        else:
            ts = int(datetime.now(timezone.utc).timestamp())
            scrap_job = await create_scrap_job(
                db,
                {
                    "name": data.get("name") or f"wf_exec_{execution_id}_{ts}",
                    "job_site_id": site.id,
                    "created_by": user_id,
                    "workflow_execution_id": execution_id,
                    "status": ScrapJobStatus.PENDING.value,
                    "meta_data": {
                        **(data.get("meta_data") or {}),
                        "workflow_execution_id": execution_id,
                    },
                },
            )
            sid = scrap_job.id
        await db.commit()

    async with async_session() as db:
        site = await get_job_site_by_id(db, data["job_site_id"])
        scrap_job_row = await get_scrap_job_by_id(db, sid)
        if (
            site is None
            or scrap_job_row is None
            or site.created_by != user_id
            or scrap_job_row.created_by != user_id
        ):
            raise NotFoundException(detail="Scrap job or site missing")
        if scrap_job_row.status != ScrapJobStatus.COMPLETED.value:
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
        cj_ids = await get_career_job_ids_by_scrap_job_id(db, sid, created_by=user_id)
    cc_ids = []
    if cj_ids:
        async with async_session() as db:
            cc_ids = await get_career_client_ids_for_career_jobs(
                db, cj_ids, created_by=user_id
            )
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
            cs = await get_client_site_by_id(db, cs_id)
            if cs is None or cs.created_by != user_id:
                raise NotFoundException(detail="Client site not found")
            sj = await create_scrap_client_job(
                db,
                {
                    "name": data.get("name") or f"wf_sc_site_{execution_id}_{ts}",
                    "client_site_id": cs_id,
                    "created_by": user_id,
                    "workflow_execution_id": execution_id,
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
                    "created_by": user_id,
                    "workflow_execution_id": execution_id,
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
                    client_ids = await get_career_client_ids_for_career_jobs(
                        db, cj, created_by=user_id
                    )
        only_without = bool(data.get("only_clients_without_emails", False))
        url = data.get("url")
        async with async_session() as db:
            sj = await create_scrap_client_job(
                db,
                {
                    "name": data.get("name") or f"wf_sc_em_{execution_id}_{ts}",
                    "created_by": user_id,
                    "workflow_execution_id": execution_id,
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
            workflow_execution_id=execution_id,
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


async def _finalize_workflow_execution_completed(ex_id: int, user_id: int) -> None:
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


def _resolve_resume_start(
    active: list[WorkflowTask],
    jobs: list[WorkflowJob],
) -> tuple[int | None, int | None, str | None]:
    """
    Returns (start_task_index, reuse_workflow_job_id, reason).
    reason ``already_complete`` means caller should finalize the execution only.
    """
    jobs_sorted = sorted(jobs, key=lambda j: j.id)
    nj = len(jobs_sorted)
    na = len(active)
    if na == 0:
        return None, None, "no_tasks"
    for i in range(na):
        if i >= nj:
            return i, None, None
        job = jobs_sorted[i]
        if job.workflow_task_id != active[i].id:
            return None, None, "job_task_mismatch"
        if job.status == WorkflowJobStatus.ERROR.value:
            return None, None, "has_error"
        if job.status in (
            WorkflowJobStatus.IN_PROGRESS.value,
            WorkflowJobStatus.PENDING.value,
        ):
            return i, job.id, None
    if nj >= na and all(
        jobs_sorted[k].workflow_task_id == active[k].id
        and jobs_sorted[k].status
        in (
            WorkflowJobStatus.COMPLETED.value,
            WorkflowJobStatus.TERMINATED.value,
        )
        for k in range(na)
    ):
        return None, None, "already_complete"
    if nj < na:
        return nj, None, None
    return None, None, "unknown"


async def _execute_workflow_tasks_loop(
    workflow_id: int,
    ex_id: int,
    user_id: int,
    active: list[WorkflowTask],
    start_at_index: int,
    resume_workflow_job_id: int | None,
    context: dict,
) -> None:
    """Run workflow tasks from start_at_index; optionally reuse an in-progress job row."""
    for task_index in range(start_at_index, len(active)):
        task = active[task_index]
        wj_id = None
        try:
            reuse_row = (
                task_index == start_at_index and resume_workflow_job_id is not None
            )
            if reuse_row:
                wj_id = resume_workflow_job_id
            else:
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
            wj_row_status = await _workflow_job_row_status_for_linked_task(
                task.linked_task_model, delta
            )
            log_action = (
                "task_terminated"
                if wj_row_status == WorkflowJobStatus.TERMINATED.value
                else "task_completed"
            )
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
                            "status": wj_row_status,
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
                        log_action,
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
                    "status": wj_row_status,
                },
            )
        except Exception as e:
            logger.exception(
                "Workflow task error workflow_id=%s task_id=%s",
                workflow_id,
                task.id,
            )
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

    await _finalize_workflow_execution_completed(ex_id, user_id)


async def continue_workflow_execution(execution_id: int) -> None:
    """Resume an in-progress execution from the first incomplete or in-progress step."""
    async with async_session() as db:
        ex = await workflow_crud.get_workflow_execution_by_id(db, execution_id)
        if ex is None:
            logger.warning("continue_workflow_execution: missing execution %s", execution_id)
            return
        if ex.status != WorkflowExecutionStatus.IN_PROGRESS.value:
            return
        user_id = ex.user_id
        workflow_id = ex.workflow_id
        context = dict((ex.meta_data or {}).get("context") or {})
        jobs = await workflow_crud.list_workflow_jobs_for_execution(db, execution_id)

    tasks: list[WorkflowTask] = []
    async with async_session() as db:
        tasks = await workflow_crud.list_workflow_tasks(db, workflow_id)
    active = [t for t in tasks if t.is_active]
    active.sort(key=lambda x: (-x.priority, x.id))
    start_idx, reuse_id, reason = _resolve_resume_start(active, jobs)

    if reason == "already_complete":
        await _finalize_workflow_execution_completed(execution_id, user_id)
        return
    if reason in ("has_error", "job_task_mismatch", "no_tasks", "unknown"):
        logger.warning(
            "continue_workflow_execution: cannot proceed execution_id=%s reason=%s",
            execution_id,
            reason,
        )
        return
    if start_idx is None:
        return

    await _execute_workflow_tasks_loop(
        workflow_id,
        execution_id,
        user_id,
        active,
        start_idx,
        reuse_id,
        context,
    )


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
    await _execute_workflow_tasks_loop(
        workflow_id, ex_id, user_id, active, 0, None, context
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


def _coerce_int_stat(value: object) -> int | None:
    """Parse a statistic value from JSON or numeric types."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_int_from_dict(meta: dict, *keys: str) -> int | None:
    """Return the first key that yields a coercible integer."""
    for key in keys:
        n = _coerce_int_stat(meta.get(key))
        if n is not None:
            return n
    return None


async def _stats_from_bulk_job_application_logs(
    db: AsyncSession,
    bulk_job_application_id: int,
) -> tuple[int | None, int | None, int | None]:
    """Read total, created, and validated counts from the bulk job application completion log."""
    logs = await get_bulk_job_application_logs_by_id(db, bulk_job_application_id)
    for log in reversed(logs):
        if log.action == "bulk_completed" and log.meta_data:
            m = log.meta_data or {}
            tf = _first_int_from_dict(m, "total")
            cr = _first_int_from_dict(m, "created_count")
            tv = cr
            return tf, tv, cr
    return None, None, None


async def _stats_from_bulk_email_logs(
    db: AsyncSession,
    bulk_id: int,
) -> tuple[int | None, int | None, int | None]:
    """Read total, success, and success counts from the bulk email completion log."""
    logs = await get_bulk_job_application_email_send_logs(db, bulk_id)
    for log in reversed(logs):
        if log.action == "bulk_email_completed" and log.meta_data:
            m = log.meta_data or {}
            tf = _first_int_from_dict(m, "total")
            sc = _first_int_from_dict(m, "success_count")
            return tf, sc, sc
    return None, None, None


async def _resolve_workflow_job_record_stats(
    db: AsyncSession,
    job: WorkflowJob,
) -> tuple[int | None, int | None, int | None]:
    """
    Derive total_records_fetched, records_validated, and created_records_count from
    workflow job meta_data or from the linked ScrapJob, ScrapClientJob, or bulk row and logs.
    """
    wj_meta = job.meta_data or {}
    tf = _first_int_from_dict(wj_meta, "total_records_fetched", "total_fetched")
    tv = _first_int_from_dict(wj_meta, "records_validated", "validated_count")
    cr = _first_int_from_dict(wj_meta, "created_records_count", "created_count")
    rtype = job.created_resource_type
    rid = job.created_resource_id
    if not rtype or rid is None:
        return tf, tv, cr
    if rtype == LinkedTaskModelName.SCRAP_JOB.value:
        row = await get_scrap_job_by_id(db, rid)
        if row is None:
            return tf, tv, cr
        m = row.meta_data or {}
        if tf is None:
            tf = _first_int_from_dict(
                m,
                "total_jobs_scraped_from_html",
                "total_jobs",
            )
        if tv is None:
            tv = _first_int_from_dict(m, "total_jobs_validated")
        if cr is None:
            cr = _first_int_from_dict(m, "total_jobs_created")
        return tf, tv, cr
    if rtype == LinkedTaskModelName.SCRAP_CLIENT_JOB.value:
        row = await get_scrap_client_job_by_id(db, rid)
        if row is None:
            return tf, tv, cr
        m = row.meta_data or {}
        if tf is None:
            tf = _first_int_from_dict(m, "total", "total_clients")
        if tv is None:
            tv = _first_int_from_dict(m, "completed", "clients_saved")
        if cr is None:
            cr = _first_int_from_dict(m, "clients_saved", "completed")
        if tf is None and tv is not None:
            tf = tv
        return tf, tv, cr
    if rtype == LinkedTaskModelName.BULK_JOB_APPLICATION.value:
        bulk = await get_bulk_job_application_by_id(db, rid)
        if bulk is None:
            return tf, tv, cr
        m = bulk.meta_data or {}
        if tf is None:
            tf = _first_int_from_dict(m, "total")
        if cr is None:
            cr = _first_int_from_dict(m, "created_count")
        if tv is None:
            tv = cr
        cj = m.get("career_job_ids")
        if tf is None and isinstance(cj, list):
            tf = len(cj)
        if tf is None or tv is None or cr is None:
            lt_tf, lt_tv, lt_cr = await _stats_from_bulk_job_application_logs(db, rid)
            tf = tf if tf is not None else lt_tf
            tv = tv if tv is not None else lt_tv
            cr = cr if cr is not None else lt_cr
        return tf, tv, cr
    if rtype == LinkedTaskModelName.BULK_JOB_APPLICATION_EMAIL_SEND.value:
        bulk = await get_bulk_job_application_email_send_by_id(db, rid)
        if bulk is None:
            return tf, tv, cr
        m = bulk.meta_data or {}
        if tf is None:
            tf = _first_int_from_dict(m, "total")
        if cr is None:
            cr = _first_int_from_dict(m, "success_count")
        if tv is None:
            tv = cr
        jids = m.get("job_application_ids")
        if tf is None and isinstance(jids, list):
            tf = len(jids)
        if tf is None or tv is None or cr is None:
            lt_tf, lt_tv, lt_cr = await _stats_from_bulk_email_logs(db, rid)
            tf = tf if tf is not None else lt_tf
            tv = tv if tv is not None else lt_tv
            cr = cr if cr is not None else lt_cr
        return tf, tv, cr
    return tf, tv, cr


async def get_execution_detail_svc(
    db: AsyncSession,
    execution_id: int,
    user_id: int,
) -> WorkflowExecutionDetailResponse:
    """Execution with jobs, logs, and per-step record statistics."""
    ex = await workflow_crud.get_workflow_execution_by_id(db, execution_id)
    if ex is None or ex.user_id != user_id:
        raise NotFoundException(detail="Workflow execution not found")
    wf = await workflow_crud.get_workflow_by_id(db, ex.workflow_id)
    jobs = await workflow_crud.list_workflow_jobs_for_execution(db, execution_id)
    logs_map: dict[int, list] = {}
    enriched_jobs: list[WorkflowJobResponse] = []
    for j in jobs:
        logs = await workflow_crud.list_workflow_logs_for_job(db, j.id)
        logs_map[j.id] = [WorkflowLogResponse.model_validate(x) for x in logs]
        tf, tv, cr = await _resolve_workflow_job_record_stats(db, j)
        base_job = WorkflowJobResponse.model_validate(j)
        enriched_jobs.append(
            base_job.model_copy(
                update={
                    "total_records_fetched": tf,
                    "records_validated": tv,
                    "created_records_count": cr,
                }
            )
        )
    base = WorkflowExecutionResponse.model_validate(ex)
    return WorkflowExecutionDetailResponse(
        **base.model_dump(),
        workflow_name=wf.name if wf else None,
        jobs=enriched_jobs,
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


async def resume_workflow_execution_svc(
    db: AsyncSession,
    execution_id: int,
    user_id: int,
) -> dict:
    """Re-enter an in-progress execution from its current step (background)."""
    ex = await workflow_crud.get_workflow_execution_by_id(db, execution_id)
    if ex is None or ex.user_id != user_id:
        raise NotFoundException(detail="Workflow execution not found")
    if ex.status != WorkflowExecutionStatus.IN_PROGRESS.value:
        raise BadRequestException(
            detail="Only in-progress executions can be resumed",
        )
    jobs = await workflow_crud.list_workflow_jobs_for_execution(db, execution_id)
    tasks = await workflow_crud.list_workflow_tasks(db, ex.workflow_id)
    active = [t for t in tasks if t.is_active]
    active.sort(key=lambda x: (-x.priority, x.id))
    _, _, reason = _resolve_resume_start(active, jobs)
    if reason == "has_error":
        raise BadRequestException(
            detail="Cannot resume: a workflow step is in error; start a new run instead",
        )
    if reason == "job_task_mismatch":
        raise BadRequestException(detail="Cannot resume: workflow state is inconsistent")
    if reason == "no_tasks":
        raise BadRequestException(detail="Workflow has no active tasks")
    if reason == "unknown":
        raise BadRequestException(detail="Cannot resume this execution")
    asyncio.create_task(continue_workflow_execution(execution_id))
    return {"status": "resumed", "execution_id": execution_id}
