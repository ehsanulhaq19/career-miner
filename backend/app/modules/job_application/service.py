import json
import os
import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.career_client.crud import get_career_client_by_id
from app.modules.career_job.crud import get_career_job_by_id
from app.database import async_session
from app.modules.job_application.crud import (
    create_bulk_job_application,
    create_bulk_job_application_log,
    create_job_application,
    get_bulk_job_application_by_id,
    get_bulk_job_application_logs_by_id,
    get_job_application_by_id,
    get_job_applications,
    update_bulk_job_application_status,
    update_job_application as crud_update_job_application,
)
from app.modules.job_application.prompts import (
    JOB_APPLICATION_SYSTEM_PROMPT,
    JOB_APPLICATION_USER_PROMPT_TEMPLATE,
)
from app.modules.job_application.models import BulkJobApplicationStatus
from app.modules.job_application.schemas import (
    BulkJobApplicationLogListResponse,
    BulkJobApplicationLogResponse,
    BulkJobApplicationResponse,
    JobApplicationListResponse,
    JobApplicationResponse,
)
from app.modules.job_site.crud import get_job_site_by_id
from app.modules.llm.service import LLMFactory
from app.modules.resume.crud import get_resume_by_id
from app.modules.websocket.service import broadcast_bulk_job_application_log


def _extract_json_object(text: str) -> str | None:
    """Extract JSON object from LLM response, handling markdown code blocks."""
    text = text.strip()
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    depth = 0
    start = text.find("{")
    if start < 0:
        return None
    for i, c in enumerate(text[start:], start):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _generate_application_name() -> str:
    """Generate a unique application name using timestamp."""
    from time import time

    return str(int(time() * 1000))


def _render_resume_html(resume_content: dict) -> str:
    """Render resume content into HTML using the template."""
    from jinja2 import Environment, FileSystemLoader

    templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("resumes/resume.html")
    return template.render(resume=resume_content)


def _html_to_pdf(html_content: str, output_path: Path) -> None:
    """Convert HTML content to PDF and save to output_path."""
    from xhtml2pdf import pisa

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w+b") as dest:
        pisa.CreatePDF(html_content, dest=dest, encoding="utf-8")


def _get_job_application_resume_base_dir() -> Path:
    """Return the base directory for job application output resumes."""
    settings = get_settings()
    base = Path(settings.JOB_APPLICATION_OUTPUT_FOLDER)
    if not base.is_absolute():
        base = Path(os.getcwd()) / base
    base.mkdir(parents=True, exist_ok=True)
    return base


async def _create_job_application_pdf(
    resume_content: dict, application_name: str
) -> str:
    """
    Generate PDF from resume content and save to temp directory.
    Returns relative path for storage in output_resume_path.
    """
    base_dir = _get_job_application_resume_base_dir()
    filename = f"{application_name}.pdf"
    output_path = base_dir / filename
    html_content = _render_resume_html(resume_content)
    _html_to_pdf(html_content, output_path)
    return str(output_path.relative_to(Path(os.getcwd())))


async def create_job_application_flow(
    db: AsyncSession,
    career_job_id: int,
    resume_id: int,
    user_id: int,
) -> JobApplicationResponse:
    """
    Create a job application by fetching job, client, resume data,
    passing to LLM, generating PDF resume, and persisting.
    """
    career_job = await get_career_job_by_id(db, career_job_id)
    if career_job is None:
        raise NotFoundException(detail="Career job not found")

    resume = await get_resume_by_id(db, resume_id, user_id)
    if resume is None:
        raise NotFoundException(detail="Resume not found")

    career_client = None
    if career_job.career_client_id:
        career_client = await get_career_client_by_id(db, career_job.career_client_id)

    job_application_data = json.dumps(
        career_job.parsed_data or {}, indent=2, default=str
    )
    client_data = {}
    client_emails = []
    if career_client:
        client_data = {
            "detail": career_client.detail or "",
            "location": career_client.location or "",
            "official_website": career_client.official_website or "",
        }
        client_emails = career_client.emails or []

    client_data_str = json.dumps(client_data, indent=2)
    client_emails_str = json.dumps(client_emails, indent=2)
    resume_content_raw = resume.content or ""
    resume_extra_detail = getattr(resume, "extra_detail", None) or ""

    prompt = JOB_APPLICATION_USER_PROMPT_TEMPLATE.format(
        task="create job application related data",
        job_application_data=job_application_data,
        client_data=client_data_str,
        client_emails=client_emails_str,
        resume_content=resume_content_raw,
        resume_extra_detail=resume_extra_detail,
    )

    llm_client = LLMFactory.get_client(
        provider_name="grok",
        model_name="grok-4-1-fast-reasoning",
    )
    response = await llm_client.generate_content(
        system_prompt=JOB_APPLICATION_SYSTEM_PROMPT,
        prompt=prompt,
    )
    response_text = (response or "").strip()
    json_str = _extract_json_object(response_text) or response_text
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        raise BadRequestException(
            detail="Failed to parse LLM response as valid JSON"
        )

    similarity_score = parsed.get("similarity_score")
    if similarity_score is not None:
        try:
            similarity_score = float(similarity_score)
            similarity_score = max(0, min(100, similarity_score))
        except (TypeError, ValueError):
            similarity_score = None
    else:
        similarity_score = None

    subject = parsed.get("subject") or ""
    cover_letter = parsed.get("cover_letter") or ""
    to_emails = parsed.get("to_emails")
    if not isinstance(to_emails, list):
        to_emails = []

    resume_content = parsed.get("resume_content")
    if not isinstance(resume_content, dict):
        resume_content = {}

    application_name = _generate_application_name()
    output_resume_path = None
    try:
        output_resume_path = await _create_job_application_pdf(
            resume_content, application_name
        )
    except Exception:
        pass

    job_application_data = {
        "application_name": application_name,
        "resume_id": resume_id,
        "user_id": user_id,
        "subject": subject,
        "cover_letter": cover_letter,
        "output_resume_path": output_resume_path,
        "career_job_id": career_job_id,
        "similarity_score": similarity_score,
        "meta_data": {"resume_content": resume_content},
        "is_email_send": False,
        "to_emails": to_emails,
    }
    job_application = await create_job_application(db, job_application_data)

    return await _enrich_job_application_response(db, job_application)


async def _enrich_job_application_response(
    db: AsyncSession, job_application
) -> JobApplicationResponse:
    """Enrich job application with related entity names."""
    career_job = await get_career_job_by_id(db, job_application.career_job_id)
    job_site = None
    career_client = None
    if career_job:
        job_site = await get_job_site_by_id(db, career_job.job_site_id)
        if career_job.career_client_id:
            career_client = await get_career_client_by_id(
                db, career_job.career_client_id
            )

    from app.modules.resume.crud import get_resume_by_id

    resume = await get_resume_by_id(db, job_application.resume_id, job_application.user_id)

    response = JobApplicationResponse.model_validate(job_application)
    response.career_job_title = career_job.title if career_job else None
    response.career_client_id = (
        career_job.career_client_id if career_job and career_job.career_client_id else None
    )
    response.career_client_name = career_client.name if career_client else None
    response.job_site_name = job_site.name if job_site else None
    response.resume_name = resume.name if resume else None
    return response


async def list_job_applications(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    is_active: bool | None = None,
) -> JobApplicationListResponse:
    """Return a paginated list of job applications for the user."""
    items, total = await get_job_applications(
        db, user_id, skip=skip, limit=limit, is_active=is_active
    )
    response_items = []
    for item in items:
        enriched = await _enrich_job_application_response(db, item)
        response_items.append(enriched)
    page = (skip // limit) + 1 if limit > 0 else 1
    return JobApplicationListResponse(
        items=response_items,
        total=total,
        page=page,
        limit=limit,
    )


async def get_job_application(
    db: AsyncSession, job_application_id: int, user_id: int
) -> JobApplicationResponse:
    """Return a single job application or raise NotFoundException."""
    job_application = await get_job_application_by_id(
        db, job_application_id, user_id
    )
    if job_application is None:
        raise NotFoundException(detail="Job application not found")
    return await _enrich_job_application_response(db, job_application)


async def update_job_application(
    db: AsyncSession,
    job_application_id: int,
    user_id: int,
    update_data: dict,
) -> JobApplicationResponse | None:
    """Update an existing job application and return the updated record."""
    updated = await crud_update_job_application(
        db, job_application_id, user_id, update_data
    )
    if updated is None:
        return None
    return await _enrich_job_application_response(db, updated)


async def _create_bulk_log_and_broadcast(
    db: AsyncSession,
    bulk_job_application_id: int,
    user_id: int,
    action: str,
    progress: int = 0,
    status: str = "in_progress",
    details: str | None = None,
    meta_data: dict | None = None,
):
    """
    Create a bulk job application log entry and broadcast it via WebSocket.
    Uses a separate session to commit immediately so logs are visible at runtime.
    """
    async with async_session() as log_db:
        try:
            log = await create_bulk_job_application_log(
                log_db,
                bulk_job_application_id=bulk_job_application_id,
                action=action,
                progress=progress,
                status=status,
                details=details,
                meta_data=meta_data,
            )
            await log_db.commit()
            await broadcast_bulk_job_application_log(
                BulkJobApplicationLogResponse.model_validate(log).model_dump(),
                user_id,
            )
            return log
        except Exception:
            await log_db.rollback()
            raise


async def start_bulk_job_application(
    db: AsyncSession,
    resume_id: int,
    career_job_ids: list[int],
    user_id: int,
) -> BulkJobApplicationResponse:
    """
    Create a bulk job application record and return it.
    Actual processing runs in background.
    """
    from datetime import datetime, timezone

    resume = await get_resume_by_id(db, resume_id, user_id)
    if resume is None:
        raise NotFoundException(detail="Resume not found")

    name = f"bulk_{int(datetime.now(timezone.utc).timestamp())}"
    meta_data = {
        "resume_id": resume_id,
        "career_job_ids": career_job_ids,
        "total": len(career_job_ids),
    }
    bulk_job_application = await create_bulk_job_application(
        db,
        {
            "name": name,
            "user_id": user_id,
            "resume_id": resume_id,
            "status": BulkJobApplicationStatus.PENDING.value,
            "meta_data": meta_data,
        },
    )
    return BulkJobApplicationResponse.model_validate(bulk_job_application)


async def run_bulk_job_application_background(
    bulk_job_application_id: int,
    resume_id: int,
    career_job_ids: list[int],
    user_id: int,
) -> None:
    """
    Execute bulk job application creation in background.
    Creates job applications one by one, logs each step, broadcasts via WebSocket.
    """
    async with async_session() as db:
        try:
            bulk_job_application = await get_bulk_job_application_by_id(
                db, bulk_job_application_id
            )
            if bulk_job_application is None:
                return
            if bulk_job_application.status == BulkJobApplicationStatus.STOPPED.value:
                return

            await update_bulk_job_application_status(
                db, bulk_job_application_id, BulkJobApplicationStatus.IN_PROGRESS
            )
            await db.commit()

            await _create_bulk_log_and_broadcast(
                db,
                bulk_job_application_id,
                user_id,
                "bulk_started",
                progress=0,
                status="in_progress",
                details=f"Starting bulk creation for {len(career_job_ids)} jobs",
                meta_data={"total": len(career_job_ids)},
            )

            created_count = 0
            failed_count = 0
            total = len(career_job_ids)

            for idx, career_job_id in enumerate(career_job_ids):
                bulk_job_application = await get_bulk_job_application_by_id(
                    db, bulk_job_application_id
                )
                if bulk_job_application and bulk_job_application.status == BulkJobApplicationStatus.STOPPED.value:
                    break

                progress = int((idx / total) * 100) if total > 0 else 0
                await _create_bulk_log_and_broadcast(
                    db,
                    bulk_job_application_id,
                    user_id,
                    "job_application_started",
                    progress=progress,
                    status="in_progress",
                    details=f"Creating job application {idx + 1}/{total}",
                    meta_data={"career_job_id": career_job_id, "index": idx + 1, "total": total},
                )

                try:
                    async with async_session() as app_db:
                        await create_job_application_flow(
                            app_db,
                            career_job_id=career_job_id,
                            resume_id=resume_id,
                            user_id=user_id,
                        )
                        await app_db.commit()
                    created_count += 1
                    await _create_bulk_log_and_broadcast(
                        db,
                        bulk_job_application_id,
                        user_id,
                        "job_application_created",
                        progress=int(((idx + 1) / total) * 100) if total > 0 else 100,
                        status="completed",
                        details=f"Created job application for job {career_job_id}",
                        meta_data={"career_job_id": career_job_id, "job_application_index": idx + 1, "total": total},
                    )
                except Exception:
                    failed_count += 1
                    await _create_bulk_log_and_broadcast(
                        db,
                        bulk_job_application_id,
                        user_id,
                        "job_application_failed",
                        progress=int(((idx + 1) / total) * 100) if total > 0 else 100,
                        status="error",
                        details=f"Failed to create job application for job {career_job_id}",
                        meta_data={"career_job_id": career_job_id, "job_application_index": idx + 1, "total": total},
                    )

            final_status = BulkJobApplicationStatus.COMPLETED
            if failed_count > 0 and created_count == 0:
                final_status = BulkJobApplicationStatus.ERROR
            elif failed_count > 0:
                final_status = BulkJobApplicationStatus.COMPLETED

            await update_bulk_job_application_status(
                db, bulk_job_application_id, final_status
            )
            await db.commit()

            await _create_bulk_log_and_broadcast(
                db,
                bulk_job_application_id,
                user_id,
                "bulk_completed",
                progress=100,
                status="completed",
                details=f"Bulk creation finished. Created: {created_count}, Failed: {failed_count}",
                meta_data={"created_count": created_count, "failed_count": failed_count, "total": total},
            )
        except Exception:
            await db.rollback()
            try:
                async with async_session() as err_db:
                    await update_bulk_job_application_status(
                        err_db, bulk_job_application_id, BulkJobApplicationStatus.ERROR
                    )
                    await err_db.commit()
            except Exception:
                pass


async def get_bulk_job_application_logs(
    db: AsyncSession,
    bulk_job_application_id: int,
    user_id: int,
) -> BulkJobApplicationLogListResponse:
    """Return all logs for a bulk job application."""
    bulk_job_application = await get_bulk_job_application_by_id(
        db, bulk_job_application_id
    )
    if bulk_job_application is None:
        raise NotFoundException(detail="Bulk job application not found")
    if bulk_job_application.user_id != user_id:
        raise NotFoundException(detail="Bulk job application not found")
    logs = await get_bulk_job_application_logs_by_id(db, bulk_job_application_id)
    return BulkJobApplicationLogListResponse(
        items=[BulkJobApplicationLogResponse.model_validate(log) for log in logs]
    )


async def get_job_application_file_path(
    db: AsyncSession, job_application_id: int, user_id: int
) -> Path | None:
    """Return the file path for the job application output resume PDF."""
    job_application = await get_job_application_by_id(
        db, job_application_id, user_id
    )
    if job_application is None or not job_application.output_resume_path:
        return None
    full_path = Path(os.getcwd()) / job_application.output_resume_path
    if not full_path.exists():
        return None
    return full_path
