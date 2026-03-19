import json
import os
import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.career_client.crud import get_career_client_by_id
from app.modules.career_job.crud import get_career_job_by_id
from app.modules.job_application.crud import (
    create_job_application,
    get_job_application_by_id,
    get_job_applications,
    update_job_application as crud_update_job_application,
)
from app.modules.job_application.prompts import (
    JOB_APPLICATION_SYSTEM_PROMPT,
    JOB_APPLICATION_USER_PROMPT_TEMPLATE,
)
from app.modules.job_application.schemas import (
    JobApplicationListResponse,
    JobApplicationResponse,
)
from app.modules.job_site.crud import get_job_site_by_id
from app.modules.llm.service import LLMFactory
from app.modules.resume.crud import get_resume_by_id


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
