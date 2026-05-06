import json
import os
import re
from datetime import date
from pathlib import Path
import random
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.career_client.crud import get_career_client_by_id
from app.modules.career_job.crud import (
    create_career_job,
    get_career_job_by_id,
    get_career_job_for_user_matching_job_details,
)
from app.database import async_session
from app.modules.job_application.crud import (
    create_bulk_job_application,
    create_bulk_job_application_log,
    create_bulk_job_application_email_send,
    create_bulk_job_application_email_send_log,
    create_job_application,
    create_job_application_email_log,
    record_job_application_bulk_job_application_link,
    get_bulk_job_application_by_id,
    get_bulk_job_application_logs_by_id,
    get_bulk_job_application_email_send_by_id,
    get_bulk_job_application_email_send_logs as crud_get_bulk_email_send_logs,
    get_email_logs_for_job_application,
    get_email_send_count_for_job_application,
    filter_job_application_ids_by_min_similarity,
    get_job_application_by_id,
    get_job_application_dates_grouped as crud_get_job_application_dates_grouped,
    get_job_applications,
    get_job_applications_by_created_date,
    get_job_applications_by_search,
    get_job_applications_by_date_and_similarity,
    update_bulk_job_application_status,
    update_bulk_job_application_email_send_status,
    bulk_update_job_applications_is_active,
    update_job_application as crud_update_job_application,
)
from app.modules.job_application.prompts import (
    JOB_APPLICATION_SYSTEM_PROMPT,
    JOB_APPLICATION_USER_PROMPT_TEMPLATE,
    LIVE_JOB_APPLICATION_SYSTEM_PROMPT,
    LIVE_JOB_APPLICATION_USER_PROMPT_TEMPLATE,
    PREPARE_JOB_APPLICATION_FORM_SYSTEM_PROMPT,
    PREPARE_JOB_APPLICATION_FORM_USER_PROMPT_TEMPLATE,
)
from app.modules.job_application.models import (
    BulkJobApplicationEmailSendStatus,
    BulkJobApplicationStatus,
)

_BULK_JOB_APP_HALTED_STATUSES: frozenset[str] = frozenset(
    {
        BulkJobApplicationStatus.STOPPED.value,
        BulkJobApplicationStatus.TERMINATED.value,
    }
)
from app.modules.career_client.crud import create_career_client, update_career_client
from app.modules.job_application.schemas import (
    ApplicationFormQaItem,
    BulkJobApplicationEmailSendLogListResponse,
    BulkJobApplicationEmailSendLogResponse,
    BulkJobApplicationLogListResponse,
    BulkJobApplicationLogResponse,
    BulkJobApplicationResponse,
    EmailLogResponse,
    JobApplicationDateGroupListResponse,
    JobApplicationDateGroupResponse,
    JobApplicationListResponse,
    JobApplicationResponse,
    LiveJobApplicationAction,
    LiveJobDuplicateCheckResponse,
)
from app.modules.job_site.crud import get_job_site_by_id
from app.modules.llm.service import LLMFactory
from app.modules.resume.crud import get_resume_by_id
from app.modules.email.service import EmailService
from app.modules.scrap_client.service import discover_emails_for_career_client
from app.modules.websocket.service import (
    broadcast_bulk_job_application_email_send_log,
    broadcast_bulk_job_application_log,
)


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


LIVE_APPLICATION_SOURCE_LABEL = "Live Application"

APPLICATION_FORM_QA_COVER_LETTER_MARKER = "Application form responses"


def _cover_letter_for_email_send(cover_letter: str | None) -> str:
    """Return cover letter text for outbound email, without the application form Q&A appendix."""
    text = (cover_letter or "").strip()
    if not text:
        return ""
    idx = text.find(APPLICATION_FORM_QA_COVER_LETTER_MARKER)
    if idx == -1:
        return cover_letter or ""
    return text[:idx].rstrip()


def _format_application_form_qa_for_cover_letter(
    items: list[dict[str, str]],
) -> str:
    """Join application form Q&A pairs into a cover-letter appendix section."""
    lines: list[str] = [APPLICATION_FORM_QA_COVER_LETTER_MARKER]
    for row in items:
        q = (row.get("question") or "").strip()
        a = (row.get("answer") or "").strip()
        lines.append("")
        lines.append(f"Q: {q}")
        lines.append(f"A: {a}")
    return "\n".join(lines)


async def _run_live_job_extraction_llm(job_details: str) -> dict:
    """Call the LLM to extract career client and career job fields from pasted job text."""
    prompt = LIVE_JOB_APPLICATION_USER_PROMPT_TEMPLATE.format(job_details=job_details)
    llm_client = LLMFactory.get_client(
        provider_name="grok",
        model_name="grok-4-1-fast-reasoning",
    )
    response = await llm_client.generate_content(
        system_prompt=LIVE_JOB_APPLICATION_SYSTEM_PROMPT,
        prompt=prompt,
    )
    response_text = (response or "").strip()
    json_str = _extract_json_object(response_text) or response_text
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        raise BadRequestException(
            detail="Failed to parse LLM extraction response as valid JSON"
        )


async def _generate_application_form_answers(
    job_details: str,
    resume,
    questions: list[str],
) -> list[dict[str, str]]:
    """Produce professional answers for each application question using job text and resume."""
    if not questions:
        return []
    questions_json = json.dumps(questions, ensure_ascii=False)
    resume_content_raw = resume.content or ""
    resume_extra_detail = getattr(resume, "extra_detail", None) or ""
    prompt = PREPARE_JOB_APPLICATION_FORM_USER_PROMPT_TEMPLATE.format(
        job_details=job_details,
        resume_content=resume_content_raw,
        resume_extra_detail=resume_extra_detail,
        questions_json=questions_json,
    )
    llm_client = LLMFactory.get_client(
        provider_name="grok",
        model_name="grok-4-1-fast-reasoning",
    )
    response = await llm_client.generate_content(
        system_prompt=PREPARE_JOB_APPLICATION_FORM_SYSTEM_PROMPT,
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
            detail="Failed to parse application form LLM response as valid JSON"
        )
    answers = parsed.get("answers")
    if not isinstance(answers, list):
        raise BadRequestException(
            detail="Application form response missing answers array"
        )
    out: list[dict[str, str]] = []
    for i, q in enumerate(questions):
        answer_text = ""
        if i < len(answers) and isinstance(answers[i], dict):
            answer_text = str(answers[i].get("answer") or "").strip()
        out.append({"question": q, "answer": answer_text})
    return out


def _generate_application_name() -> str:
    """Generate a unique application name using timestamp."""
    from time import time

    return str(int(time() * 1000))


def _normalize_string_list(value: object) -> list[str]:
    """Coerce JSON or scalar values into a list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _optional_str(value: object) -> str | None:
    """Return stripped string or None."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


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
    if career_job is None or career_job.created_by != user_id:
        raise NotFoundException(detail="Career job not found")

    resume = await get_resume_by_id(db, resume_id, user_id)
    if resume is None:
        raise NotFoundException(detail="Resume not found")

    career_client = None
    if career_job.career_client_id:
        career_client = await get_career_client_by_id(db, career_job.career_client_id)
        if career_client is not None and career_client.created_by != user_id:
            career_client = None

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
        "created_by": user_id,
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


async def check_live_job_duplicate(
    db: AsyncSession,
    job_details: str,
    user_id: int,
) -> LiveJobDuplicateCheckResponse:
    """
    Detect an existing CareerJob for this user with the same pasted/extracted
    description text (trimmed) or the same stored ``original_job_details``.
    """
    text = (job_details or "").strip()
    if not text:
        raise BadRequestException(detail="job_details is required")
    row = await get_career_job_for_user_matching_job_details(db, user_id, text)
    if row is None:
        return LiveJobDuplicateCheckResponse(exists=False)
    return LiveJobDuplicateCheckResponse(
        exists=True,
        career_job_id=row.id,
        title=row.title,
        description=row.description,
    )


async def create_live_job_application_flow(
    db: AsyncSession,
    job_details: str,
    resume_id: int,
    user_id: int,
    action: LiveJobApplicationAction,
    application_form_questions: list[str] | None = None,
) -> JobApplicationResponse:
    """
    Use Grok to extract client and job fields from free-form job text, persist CareerClient
    and CareerJob with live-application metadata, run job application generation, attach
    source on the job application, and optionally send outreach emails.
    For prepare_job_application_form, also run a dedicated prompt to answer each supplied
    question from job text and resume, and store those answers in meta_data and the cover
    letter appendix.
    """
    text = (job_details or "").strip()
    if not text:
        raise BadRequestException(detail="job_details is required")

    resume = await get_resume_by_id(db, resume_id, user_id)
    if resume is None:
        raise NotFoundException(detail="Resume not found")

    prepare_qs: list[str] | None = None
    if action == LiveJobApplicationAction.PREPARE_JOB_APPLICATION_FORM:
        prepare_qs = [
            q.strip()
            for q in (application_form_questions or [])
            if isinstance(q, str) and q.strip()
        ]
        if not prepare_qs:
            raise BadRequestException(
                detail="application_form_questions is required for this action"
            )

    form_qa_list: list[dict[str, str]] | None = None
    if prepare_qs:
        parsed, form_qa_list = await asyncio.gather(
            _run_live_job_extraction_llm(text),
            _generate_application_form_answers(text, resume, prepare_qs),
        )
    else:
        parsed = await _run_live_job_extraction_llm(text)

    cc_raw = (
        parsed.get("career_client")
        if isinstance(parsed.get("career_client"), dict)
        else {}
    )
    cj_raw = (
        parsed.get("career_job")
        if isinstance(parsed.get("career_job"), dict)
        else {}
    )

    title = _optional_str(cj_raw.get("title"))
    if not title:
        raise BadRequestException(detail="Extracted job title is required")

    client_meta = {"source": LIVE_APPLICATION_SOURCE_LABEL}
    initial_client_emails = _normalize_string_list(cc_raw.get("emails"))
    client_row = await create_career_client(
        db,
        {
            "emails": initial_client_emails,
            "phone_numbers": _normalize_string_list(cc_raw.get("phone_numbers")),
            "official_website": _optional_str(cc_raw.get("official_website")),
            "name": _optional_str(cc_raw.get("name")),
            "location": _optional_str(cc_raw.get("location")),
            "detail": _optional_str(cc_raw.get("detail")),
            "link": _optional_str(cc_raw.get("link")),
            "size": _optional_str(cc_raw.get("size")),
            "meta_data": client_meta,
            "scrap_client_job_id": None,
            "created_by": user_id,
        },
    )

    if not initial_client_emails:
        company_name_for_discovery = (
            (_optional_str(cc_raw.get("name")) or title or "").strip()
        )
        if company_name_for_discovery:
            success, discovered_emails, discovered_website = (
                await discover_emails_for_career_client(
                    client_row.id,
                    company_name_for_discovery,
                    website_override=_optional_str(cc_raw.get("official_website")),
                    client_link=_optional_str(cc_raw.get("link")),
                )
            )
            fresh_client = await get_career_client_by_id(db, client_row.id)
            base_meta: dict = {}
            if fresh_client and isinstance(fresh_client.meta_data, dict):
                base_meta = dict(fresh_client.meta_data)
            if success and discovered_emails:
                base_meta["email_found_error"] = False
                await update_career_client(
                    db,
                    client_row.id,
                    {
                        "emails": discovered_emails,
                        "official_website": discovered_website
                        or (
                            fresh_client.official_website
                            if fresh_client
                            else None
                        ),
                        "meta_data": base_meta,
                    },
                )
            else:
                base_meta["email_found_error"] = True
                payload: dict = {"meta_data": base_meta}
                if discovered_website:
                    payload["official_website"] = discovered_website
                elif fresh_client and fresh_client.official_website:
                    payload["official_website"] = fresh_client.official_website
                await update_career_client(db, client_row.id, payload)

    parsed_job = cj_raw.get("parsed_data")
    if not isinstance(parsed_job, dict):
        parsed_job = {}

    job_meta = {
        "source": LIVE_APPLICATION_SOURCE_LABEL,
        "original_job_details": text,
    }
    career_job_row = await create_career_job(
        db,
        {
            "title": title,
            "description": _optional_str(cj_raw.get("description")),
            "url": _optional_str(cj_raw.get("url")),
            "job_site_id": None,
            "scrap_job_id": None,
            "career_client_id": client_row.id,
            "meta_data": job_meta,
            "parsed_data": parsed_job,
            "created_by": user_id,
        },
    )

    ja_resp = await create_job_application_flow(
        db,
        career_job_id=career_job_row.id,
        resume_id=resume_id,
        user_id=user_id,
    )

    md = dict(ja_resp.meta_data or {})
    md["source"] = LIVE_APPLICATION_SOURCE_LABEL
    update_payload: dict = {"meta_data": md}
    if (
        action == LiveJobApplicationAction.PREPARE_JOB_APPLICATION_FORM
        and form_qa_list is not None
        and prepare_qs is not None
    ):
        md["application_form_qa"] = form_qa_list
        md["application_form_questions"] = prepare_qs
        cover = (ja_resp.cover_letter or "").strip()
        qa_block = _format_application_form_qa_for_cover_letter(form_qa_list)
        combined = f"{cover}\n\n{qa_block}" if cover else qa_block
        update_payload["cover_letter"] = combined
        update_payload["meta_data"] = md
    await crud_update_job_application(
        db,
        ja_resp.id,
        user_id,
        update_payload,
    )

    if action == LiveJobApplicationAction.CREATE_AND_SEND_JOB_APPLICATION:
        sent = await send_job_application_email(db, ja_resp.id, user_id)
        return sent

    refreshed = await get_job_application_by_id(db, ja_resp.id, user_id)
    if refreshed is None:
        raise NotFoundException(detail="Job application not found")
    return await _enrich_job_application_response(db, refreshed)


def _parse_application_form_qa_from_meta(
    meta_data: object,
) -> list[ApplicationFormQaItem] | None:
    """Build typed application form Q&A from persisted meta_data JSON."""
    if not isinstance(meta_data, dict):
        return None
    raw = meta_data.get("application_form_qa")
    if not isinstance(raw, list) or not raw:
        return None
    out: list[ApplicationFormQaItem] = []
    for row in raw:
        if isinstance(row, dict):
            out.append(
                ApplicationFormQaItem(
                    question=str(row.get("question", "")),
                    answer=str(row.get("answer", "")),
                )
            )
    return out or None


def _parse_application_form_questions_from_meta(
    meta_data: object,
) -> list[str] | None:
    """Return user-supplied application form question strings from meta_data."""
    if not isinstance(meta_data, dict):
        return None
    raw = meta_data.get("application_form_questions")
    if not isinstance(raw, list) or not raw:
        return None
    out = [str(x).strip() for x in raw if isinstance(x, str) and str(x).strip()]
    return out or None


async def _enrich_job_application_response(
    db: AsyncSession, job_application
) -> JobApplicationResponse:
    """
    Enrich job application with related entity names and email send count.
    """
    career_job = await get_career_job_by_id(db, job_application.career_job_id)
    job_site = None
    career_client = None
    if career_job and career_job.job_site_id is not None:
        job_site = await get_job_site_by_id(db, career_job.job_site_id)
        if career_job.career_client_id:
            career_client = await get_career_client_by_id(
                db, career_job.career_client_id
            )

    from app.modules.resume.crud import get_resume_by_id

    resume = await get_resume_by_id(db, job_application.resume_id, job_application.user_id)
    email_send_count = await get_email_send_count_for_job_application(
        db, job_application.id
    )

    response = JobApplicationResponse.model_validate(job_application)
    response.career_job_title = career_job.title if career_job else None
    response.career_client_id = (
        career_job.career_client_id if career_job and career_job.career_client_id else None
    )
    response.career_client_name = career_client.name if career_client else None
    response.job_site_name = job_site.name if job_site else None
    response.resume_name = resume.name if resume else None
    response.email_send_count = email_send_count
    qa = _parse_application_form_qa_from_meta(job_application.meta_data)
    aq = _parse_application_form_questions_from_meta(job_application.meta_data)
    return response.model_copy(
        update={
            "application_form_qa": qa,
            "application_form_questions": aq,
        }
    )


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


async def search_job_applications(
    db: AsyncSession,
    user_id: int,
    q: str,
    skip: int = 0,
    limit: int = 20,
    is_active: bool | None = None,
) -> JobApplicationListResponse:
    """
    Search the current user's job applications by text on the application record,
    linked career job, and linked career client.
    """
    term = q.strip()
    if not term:
        raise BadRequestException(detail="Search query must not be empty")
    items, total = await get_job_applications_by_search(
        db,
        user_id,
        term,
        skip=skip,
        limit=limit,
        is_active=is_active,
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


async def get_job_application_dates_grouped(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
) -> JobApplicationDateGroupListResponse:
    """
    Return paginated distinct creation dates with application counts for the user.
    """
    rows, total = await crud_get_job_application_dates_grouped(
        db, user_id, skip=skip, limit=limit
    )
    items = [
        JobApplicationDateGroupResponse(
            date=r[0].isoformat(),
            application_count=r[1],
        )
        for r in rows
    ]
    page = (skip // limit) + 1 if limit > 0 else 1
    return JobApplicationDateGroupListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


async def list_job_applications_by_created_date(
    db: AsyncSession,
    user_id: int,
    target_date: date,
    skip: int = 0,
    limit: int = 50,
) -> JobApplicationListResponse:
    """
    Return paginated job applications created on the given calendar date.
    """
    items, total = await get_job_applications_by_created_date(
        db, user_id, target_date, skip=skip, limit=limit
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


async def bulk_update_job_applications(
    db: AsyncSession,
    user_id: int,
    job_application_ids: list[int],
    is_active: bool,
) -> int:
    """
    Bulk-update is_active for job applications owned by the user.
    Returns the number of rows updated.
    """
    return await bulk_update_job_applications_is_active(
        db,
        user_id,
        job_application_ids,
        is_active,
    )


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
    workflow_execution_id: int | None = None,
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
    bulk_data: dict = {
        "name": name,
        "user_id": user_id,
        "resume_id": resume_id,
        "status": BulkJobApplicationStatus.PENDING.value,
        "meta_data": meta_data,
    }
    if workflow_execution_id is not None:
        bulk_data["workflow_execution_id"] = workflow_execution_id
    bulk_job_application = await create_bulk_job_application(db, bulk_data)
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
            if bulk_job_application.status in _BULK_JOB_APP_HALTED_STATUSES:
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
                if (
                    bulk_job_application
                    and bulk_job_application.status in _BULK_JOB_APP_HALTED_STATUSES
                ):
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

            bulk_job_application = await get_bulk_job_application_by_id(
                db, bulk_job_application_id
            )
            if (
                bulk_job_application
                and bulk_job_application.status in _BULK_JOB_APP_HALTED_STATUSES
            ):
                await db.commit()
                return

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


async def send_job_application_email(
    db: AsyncSession,
    job_application_id: int,
    user_id: int,
    bulk_job_application_email_send_id: int | None = None,
) -> JobApplicationResponse:
    """
    Send emails for a job application to each to_email address.
    Uses subject, cover_letter (without application form Q&A appendix), output_resume_path.
    Creates JobApplicationEmailLog for each send attempt (email_logs row)
    and marks is_email_send when every recipient send succeeds.
    """
    job_application = await get_job_application_by_id(
        db, job_application_id, user_id
    )
    if job_application is None:
        raise NotFoundException(detail="Job application not found")

    to_emails = job_application.to_emails or []
    if not to_emails:
        raise BadRequestException(detail="No recipient emails configured")

    subject = job_application.subject or ""
    cover_letter = _cover_letter_for_email_send(job_application.cover_letter)
    attachment_path = job_application.output_resume_path
    resume = await get_resume_by_id(db, job_application.resume_id, user_id)
    attachment_filename = resume.name if resume else None

    email_service = EmailService()
    per_recipient_ok: list[bool] = []
    for to_email in to_emails:
        to_email = str(to_email).strip()
        if not to_email:
            continue
        result = await email_service.send_email(
            recipient=to_email,
            subject=subject,
            content=cover_letter,
            attachment_path=attachment_path,
            attachment_filename=attachment_filename,
            raise_on_failure=False,
        )
        if result.get("email_log_id"):
            await create_job_application_email_log(
                db,
                job_application_id,
                result["email_log_id"],
                bulk_job_application_email_send_id=bulk_job_application_email_send_id,
            )
        per_recipient_ok.append(result.get("status") == "success")

    if not per_recipient_ok:
        raise BadRequestException(detail="No valid recipient emails to send to")

    if not any(per_recipient_ok):
        raise BadRequestException(detail="Failed to send email to any recipient")

    if all(per_recipient_ok):
        await crud_update_job_application(
            db, job_application_id, user_id, {"is_email_send": True, "is_active": False}
        )

    job_application = await get_job_application_by_id(
        db, job_application_id, user_id
    )
    return await _enrich_job_application_response(db, job_application)


async def get_job_application_email_logs(
    db: AsyncSession, job_application_id: int, user_id: int
) -> list[EmailLogResponse]:
    """
    Return all email logs for the given job application.
    """
    job_application = await get_job_application_by_id(
        db, job_application_id, user_id
    )
    if job_application is None:
        raise NotFoundException(detail="Job application not found")

    logs = await get_email_logs_for_job_application(db, job_application_id)
    return [EmailLogResponse.model_validate(log) for log in logs]


async def list_job_applications_for_bulk_email(
    db: AsyncSession,
    user_id: int,
    target_date: str,
    min_similarity_score: float,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[JobApplicationResponse], int]:
    """
    Return job applications created on the given date with similarity_score
    >= min_similarity_score, enriched with email_send_count.
    """
    from datetime import datetime

    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise BadRequestException(detail="Invalid date format, use YYYY-MM-DD")

    items, total = await get_job_applications_by_date_and_similarity(
        db,
        user_id=user_id,
        target_date=dt,
        min_similarity_score=min_similarity_score,
        skip=skip,
        limit=limit,
    )
    response_items = []
    for item in items:
        enriched = await _enrich_job_application_response(db, item)
        response_items.append(enriched)
    return response_items, total


async def _create_bulk_email_log_and_broadcast(
    db: AsyncSession,
    bulk_id: int,
    user_id: int,
    action: str,
    progress: int = 0,
    status: str = "in_progress",
    details: str | None = None,
    meta_data: dict | None = None,
):
    """
    Create a bulk job application email send log and broadcast via WebSocket.
    """
    async with async_session() as log_db:
        try:
            log = await create_bulk_job_application_email_send_log(
                log_db,
                bulk_job_application_email_send_id=bulk_id,
                action=action,
                progress=progress,
                status=status,
                details=details,
                meta_data=meta_data,
            )
            await log_db.commit()
            await broadcast_bulk_job_application_email_send_log(
                BulkJobApplicationEmailSendLogResponse.model_validate(log).model_dump(),
                user_id,
            )
            return log
        except Exception:
            await log_db.rollback()
            raise


async def start_bulk_job_application_email_send(
    db: AsyncSession,
    job_application_ids: list[int],
    user_id: int,
    min_similarity_score: float | None = None,
    workflow_execution_id: int | None = None,
) -> dict:
    """
    Create a bulk job application email send record and return it.
    Actual processing runs in background.

    When ``min_similarity_score`` is set, only applications with
    ``similarity_score >= min_similarity_score`` (non-null) are included.
    """
    if not job_application_ids:
        raise BadRequestException(detail="No job applications selected")

    to_send = list(job_application_ids)
    if min_similarity_score is not None:
        to_send = await filter_job_application_ids_by_min_similarity(
            db,
            job_application_ids,
            user_id,
            min_similarity_score,
        )
        if not to_send:
            raise BadRequestException(
                detail="No job applications meet the minimum similarity score"
            )

    meta_data = {
        "job_application_ids": to_send,
        "total": len(to_send),
        "requested_job_application_ids": job_application_ids,
    }
    if min_similarity_score is not None:
        meta_data["min_similarity_score"] = min_similarity_score

    email_bulk_data: dict = {
        "user_id": user_id,
        "status": BulkJobApplicationEmailSendStatus.PENDING.value,
        "min_similarity_score": min_similarity_score,
        "meta_data": meta_data,
    }
    if workflow_execution_id is not None:
        email_bulk_data["workflow_execution_id"] = workflow_execution_id
    bulk = await create_bulk_job_application_email_send(db, email_bulk_data)
    return {
        "id": bulk.id,
        "status": bulk.status,
        "job_application_ids": to_send,
    }


async def run_bulk_job_application_email_background(
    bulk_id: int,
    job_application_ids: list[int],
    user_id: int,
) -> None:
    """
    Execute bulk job application email send in background.
    Sends emails for each job application, logs each step, broadcasts via WebSocket.
    """
    async with async_session() as db:
        try:
            bulk = await get_bulk_job_application_email_send_by_id(db, bulk_id)
            if bulk is None:
                return

            await update_bulk_job_application_email_send_status(
                db, bulk_id, BulkJobApplicationEmailSendStatus.IN_PROGRESS
            )
            await db.commit()

            await _create_bulk_email_log_and_broadcast(
                db,
                bulk_id,
                user_id,
                "bulk_email_started",
                progress=0,
                status="in_progress",
                details=f"Starting bulk email send for {len(job_application_ids)} applications",
                meta_data={"total": len(job_application_ids)},
            )

            total = len(job_application_ids)
            success_count = 0
            failed_count = 0

            for idx, job_application_id in enumerate(job_application_ids):
                progress = int((idx / total) * 100) if total > 0 else 0
                await _create_bulk_email_log_and_broadcast(
                    db,
                    bulk_id,
                    user_id,
                    "job_application_email_started",
                    progress=progress,
                    status="in_progress",
                    details=f"Sending emails for application {idx + 1}/{total}",
                    meta_data={
                        "job_application_id": job_application_id,
                        "index": idx + 1,
                        "total": total,
                    },
                )

                try:
                    await asyncio.sleep(random.randint(1, 3))
                    async with async_session() as app_db:
                        await send_job_application_email(
                            app_db,
                            job_application_id,
                            user_id,
                            bulk_job_application_email_send_id=bulk_id,
                        )
                        await app_db.commit()
                    success_count += 1
                    await _create_bulk_email_log_and_broadcast(
                        db,
                        bulk_id,
                        user_id,
                        "job_application_email_sent",
                        progress=int(((idx + 1) / total) * 100) if total > 0 else 100,
                        status="completed",
                        details=f"Emails sent for application {job_application_id}",
                        meta_data={
                            "job_application_id": job_application_id,
                            "index": idx + 1,
                            "total": total,
                        },
                    )
                except Exception:
                    failed_count += 1
                    await _create_bulk_email_log_and_broadcast(
                        db,
                        bulk_id,
                        user_id,
                        "job_application_email_failed",
                        progress=int(((idx + 1) / total) * 100) if total > 0 else 100,
                        status="error",
                        details=f"Failed to send emails for application {job_application_id}",
                        meta_data={
                            "job_application_id": job_application_id,
                            "index": idx + 1,
                            "total": total,
                        },
                    )

            final_status = BulkJobApplicationEmailSendStatus.COMPLETED
            if failed_count > 0 and success_count == 0:
                final_status = BulkJobApplicationEmailSendStatus.ERROR
            elif failed_count > 0:
                final_status = BulkJobApplicationEmailSendStatus.COMPLETED

            await update_bulk_job_application_email_send_status(
                db, bulk_id, final_status
            )
            await db.commit()

            await _create_bulk_email_log_and_broadcast(
                db,
                bulk_id,
                user_id,
                "bulk_email_completed",
                progress=100,
                status="completed",
                details=f"Bulk email finished. Success: {success_count}, Failed: {failed_count}",
                meta_data={
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "total": total,
                },
            )
        except Exception:
            await db.rollback()
            try:
                async with async_session() as err_db:
                    await update_bulk_job_application_email_send_status(
                        err_db, bulk_id, BulkJobApplicationEmailSendStatus.ERROR
                    )
                    await err_db.commit()
            except Exception:
                pass


async def get_bulk_job_application_email_send_logs(
    db: AsyncSession,
    bulk_job_application_email_send_id: int,
    user_id: int,
) -> BulkJobApplicationEmailSendLogListResponse:
    """
    Return all logs for a bulk job application email send.
    """
    bulk = await get_bulk_job_application_email_send_by_id(
        db, bulk_job_application_email_send_id
    )
    if bulk is None:
        raise NotFoundException(detail="Bulk email send not found")
    if bulk.user_id != user_id:
        raise NotFoundException(detail="Bulk email send not found")

    logs = await crud_get_bulk_email_send_logs(
        db, bulk_job_application_email_send_id
    )
    return BulkJobApplicationEmailSendLogListResponse(
        items=[
            BulkJobApplicationEmailSendLogResponse.model_validate(log)
            for log in logs
        ]
    )
