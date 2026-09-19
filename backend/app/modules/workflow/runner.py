"""Helpers to run long workflow steps without blocking the API event loop."""

import asyncio
import logging
import threading
import time
from collections.abc import Awaitable, Callable, Coroutine
from datetime import datetime, timezone

from app.core.exceptions import BadRequestException, NotFoundException
from app.database import async_session, dispose_thread_local_db, init_thread_local_db

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2.0

_workflow_locks_guard = threading.Lock()
_workflow_locks: dict[int, threading.Lock] = {}


def _workflow_lock_for(workflow_id: int) -> threading.Lock:
    """Serialize runs for the same workflow; different workflows may run concurrently."""
    with _workflow_locks_guard:
        lock = _workflow_locks.get(workflow_id)
        if lock is None:
            lock = threading.Lock()
            _workflow_locks[workflow_id] = lock
        return lock


def _workflow_task_timeout_seconds() -> float:
    from app.config import get_settings

    return get_settings().WORKFLOW_TASK_TIMEOUT_MINUTES * 60


def _workflow_timeout_meta() -> dict:
    return {
        "workflow_timeout_forced": True,
        "workflow_timeout_forced_at": datetime.now(timezone.utc).isoformat(),
    }


def spawn_background_task(coro: Awaitable[None], *, label: str) -> None:
    """Schedule a coroutine on the current loop; log failures without crashing."""

    async def _wrapper() -> None:
        try:
            await coro
        except Exception:
            logger.exception("Background workflow task failed (%s)", label)

    asyncio.create_task(_wrapper())


def _workflow_thread_entry(
    coro: Coroutine[object, object, object],
    *,
    workflow_id: int,
) -> None:
    """Run a workflow coroutine on a dedicated thread with its own event loop and DB pool."""
    lock = _workflow_lock_for(workflow_id)
    acquired = lock.acquire(blocking=False)
    if not acquired:
        logger.warning(
            "Workflow %s already running; waiting for prior run to finish",
            workflow_id,
        )
        lock.acquire()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        init_thread_local_db()
        try:
            loop.run_until_complete(coro)
        except Exception:
            logger.exception("Workflow worker thread failed (workflow_id=%s)", workflow_id)
        finally:
            try:
                loop.run_until_complete(dispose_thread_local_db())
            except Exception:
                logger.exception("Failed to dispose workflow thread DB engine")
            loop.close()
    finally:
        lock.release()


def start_workflow_in_background(
    coro: Coroutine[object, object, object],
    *,
    label: str,
    workflow_id: int,
) -> None:
    """
    Execute a workflow coroutine off the API event loop.

    Heavy steps (scraping, bulk PDF/LLM) run on this worker thread so uvicorn
    can keep serving HTTP while workflows progress.
    """
    thread = threading.Thread(
        target=_workflow_thread_entry,
        args=(coro,),
        kwargs={"workflow_id": workflow_id},
        daemon=True,
        name=f"workflow-{label}",
    )
    thread.start()


async def wait_for_status(
    fetch_status: Callable[[], Awaitable[str | None]],
    terminal_statuses: frozenset[str],
    *,
    label: str,
    poll_interval: float = POLL_INTERVAL_SECONDS,
    timeout_seconds: float | None = None,
    force_complete: Callable[[], Awaitable[str]] | None = None,
) -> str:
    """Poll until a job reaches a terminal status, yielding between checks."""
    started = time.monotonic()
    while True:
        status = await fetch_status()
        if status is None:
            raise NotFoundException(detail=f"{label} not found")
        if status in terminal_statuses:
            return status
        if (
            timeout_seconds is not None
            and force_complete is not None
            and time.monotonic() - started >= timeout_seconds
        ):
            logger.warning(
                "%s exceeded %.0fs workflow timeout; forcing completion",
                label,
                timeout_seconds,
            )
            return await force_complete()
        await asyncio.sleep(poll_interval)


async def fetch_scrap_job_status(scrap_job_id: int) -> str | None:
    from app.modules.scrap_job.crud import get_scrap_job_by_id

    async with async_session() as db:
        row = await get_scrap_job_by_id(db, scrap_job_id)
        return row.status if row else None


async def fetch_scrap_client_job_status(scrap_client_job_id: int) -> str | None:
    from app.modules.scrap_client.crud import get_scrap_client_job_by_id

    async with async_session() as db:
        row = await get_scrap_client_job_by_id(db, scrap_client_job_id)
        return row.status if row else None


async def fetch_bulk_job_application_status(bulk_id: int) -> str | None:
    from app.modules.job_application.crud import get_bulk_job_application_by_id

    async with async_session() as db:
        row = await get_bulk_job_application_by_id(db, bulk_id)
        return row.status if row else None


async def fetch_bulk_email_send_status(bulk_id: int) -> str | None:
    from app.modules.job_application.crud import get_bulk_job_application_email_send_by_id

    async with async_session() as db:
        row = await get_bulk_job_application_email_send_by_id(db, bulk_id)
        return row.status if row else None


async def fetch_bulk_report_email_status(report_id: int) -> str | None:
    from app.modules.job_application.crud import get_bulk_job_application_report_email_by_id

    async with async_session() as db:
        row = await get_bulk_job_application_report_email_by_id(db, report_id)
        return row.status if row else None


SCRAP_JOB_TERMINAL = frozenset(
    {"completed", "error", "terminated", "stopped"}
)
SCRAP_CLIENT_JOB_TERMINAL = frozenset(
    {"completed", "error", "terminated", "stopped"}
)
BULK_JOB_APPLICATION_TERMINAL = frozenset(
    {"completed", "error", "terminated", "stopped"}
)
BULK_EMAIL_TERMINAL = frozenset({"completed", "error", "terminated"})
BULK_REPORT_EMAIL_TERMINAL = frozenset({"completed", "error", "terminated"})


def ensure_success_status(status: str, *, label: str) -> None:
    """Raise when a background job finished in a failed terminal state."""
    if status == "error":
        raise BadRequestException(detail=f"{label} failed")
    if status in ("terminated", "stopped"):
        raise BadRequestException(detail=f"{label} was {status}")


async def _force_complete_scrap_job(scrap_job_id: int) -> str:
    from app.modules.scrap_job.crud import (
        get_scrap_job_by_id,
        update_scrap_job_meta_data,
        update_scrap_job_status,
    )
    from app.modules.scrap_job.models import ScrapJobStatus

    async with async_session() as db:
        row = await get_scrap_job_by_id(db, scrap_job_id)
        if row is None:
            raise NotFoundException(detail=f"Scrap job {scrap_job_id} not found")
        if row.status in SCRAP_JOB_TERMINAL:
            return row.status
        await update_scrap_job_status(db, scrap_job_id, ScrapJobStatus.COMPLETED)
        await update_scrap_job_meta_data(db, scrap_job_id, _workflow_timeout_meta())
        await db.commit()
    return "completed"


async def _force_complete_scrap_client_job(scrap_client_job_id: int) -> str:
    from app.modules.scrap_client.crud import (
        get_scrap_client_job_by_id,
        update_scrap_client_job_meta_data,
        update_scrap_client_job_status,
    )
    from app.modules.scrap_client.models import ScrapClientJobStatus

    async with async_session() as db:
        row = await get_scrap_client_job_by_id(db, scrap_client_job_id)
        if row is None:
            raise NotFoundException(
                detail=f"Scrap client job {scrap_client_job_id} not found"
            )
        if row.status in SCRAP_CLIENT_JOB_TERMINAL:
            return row.status
        await update_scrap_client_job_status(
            db, scrap_client_job_id, ScrapClientJobStatus.COMPLETED
        )
        await update_scrap_client_job_meta_data(
            db, scrap_client_job_id, _workflow_timeout_meta()
        )
        await db.commit()
    return "completed"


async def _force_complete_bulk_job_application(bulk_id: int) -> str:
    from app.modules.job_application.crud import (
        get_bulk_job_application_by_id,
        update_bulk_job_application_status,
    )
    from app.modules.job_application.models import BulkJobApplicationStatus

    async with async_session() as db:
        row = await get_bulk_job_application_by_id(db, bulk_id)
        if row is None:
            raise NotFoundException(detail=f"Bulk job application {bulk_id} not found")
        if row.status in BULK_JOB_APPLICATION_TERMINAL:
            return row.status
        await update_bulk_job_application_status(
            db, bulk_id, BulkJobApplicationStatus.COMPLETED
        )
        meta = dict(row.meta_data or {})
        meta.update(_workflow_timeout_meta())
        row.meta_data = meta
        await db.flush()
        await db.commit()
    return "completed"


async def _force_complete_bulk_email_send(bulk_id: int) -> str:
    from app.modules.job_application.crud import (
        get_bulk_job_application_email_send_by_id,
        update_bulk_job_application_email_send_status,
    )
    from app.modules.job_application.models import BulkJobApplicationEmailSendStatus

    async with async_session() as db:
        row = await get_bulk_job_application_email_send_by_id(db, bulk_id)
        if row is None:
            raise NotFoundException(detail=f"Bulk email send {bulk_id} not found")
        if row.status in BULK_EMAIL_TERMINAL:
            return row.status
        await update_bulk_job_application_email_send_status(
            db, bulk_id, BulkJobApplicationEmailSendStatus.COMPLETED
        )
        meta = dict(row.meta_data or {})
        meta.update(_workflow_timeout_meta())
        row.meta_data = meta
        await db.flush()
        await db.commit()
    return "completed"


async def _force_complete_bulk_report_email(report_id: int) -> str:
    from app.modules.job_application.crud import (
        get_bulk_job_application_report_email_by_id,
        update_bulk_job_application_report_email_status,
    )
    from app.modules.job_application.models import BulkJobApplicationReportEmailStatus

    async with async_session() as db:
        row = await get_bulk_job_application_report_email_by_id(db, report_id)
        if row is None:
            raise NotFoundException(detail=f"Bulk report email {report_id} not found")
        if row.status in BULK_REPORT_EMAIL_TERMINAL:
            return row.status
        await update_bulk_job_application_report_email_status(
            db, report_id, BulkJobApplicationReportEmailStatus.COMPLETED
        )
        meta = dict(row.meta_data or {})
        meta.update(_workflow_timeout_meta())
        row.meta_data = meta
        await db.flush()
        await db.commit()
    return "completed"


async def wait_for_scrap_job(scrap_job_id: int) -> str:
    status = await wait_for_status(
        lambda: fetch_scrap_job_status(scrap_job_id),
        SCRAP_JOB_TERMINAL,
        label=f"Scrap job {scrap_job_id}",
        timeout_seconds=_workflow_task_timeout_seconds(),
        force_complete=lambda: _force_complete_scrap_job(scrap_job_id),
    )
    ensure_success_status(status, label=f"Scrap job {scrap_job_id}")
    return status


async def wait_for_scrap_client_job(scrap_client_job_id: int) -> str:
    status = await wait_for_status(
        lambda: fetch_scrap_client_job_status(scrap_client_job_id),
        SCRAP_CLIENT_JOB_TERMINAL,
        label=f"Scrap client job {scrap_client_job_id}",
        timeout_seconds=_workflow_task_timeout_seconds(),
        force_complete=lambda: _force_complete_scrap_client_job(scrap_client_job_id),
    )
    ensure_success_status(status, label=f"Scrap client job {scrap_client_job_id}")
    return status


async def wait_for_bulk_job_application(bulk_id: int) -> str:
    status = await wait_for_status(
        lambda: fetch_bulk_job_application_status(bulk_id),
        BULK_JOB_APPLICATION_TERMINAL,
        label=f"Bulk job application {bulk_id}",
        timeout_seconds=_workflow_task_timeout_seconds(),
        force_complete=lambda: _force_complete_bulk_job_application(bulk_id),
    )
    ensure_success_status(status, label=f"Bulk job application {bulk_id}")
    return status


async def wait_for_bulk_email_send(bulk_id: int) -> str:
    status = await wait_for_status(
        lambda: fetch_bulk_email_send_status(bulk_id),
        BULK_EMAIL_TERMINAL,
        label=f"Bulk email send {bulk_id}",
        timeout_seconds=_workflow_task_timeout_seconds(),
        force_complete=lambda: _force_complete_bulk_email_send(bulk_id),
    )
    ensure_success_status(status, label=f"Bulk email send {bulk_id}")
    return status


async def wait_for_bulk_report_email(report_id: int) -> str:
    status = await wait_for_status(
        lambda: fetch_bulk_report_email_status(report_id),
        BULK_REPORT_EMAIL_TERMINAL,
        label=f"Bulk report email {report_id}",
        timeout_seconds=_workflow_task_timeout_seconds(),
        force_complete=lambda: _force_complete_bulk_report_email(report_id),
    )
    ensure_success_status(status, label=f"Bulk report email {report_id}")
    return status
