import asyncio
import json
import os
import random
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from time import time

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.database import async_session
from app.modules.career_client.crud import (
    bulk_update_career_clients_by_location as crud_bulk_update,
    create_bulk_career_client_email_send,
    create_bulk_career_client_email_send_log,
    create_career_client,
    create_career_client_email_log,
    find_career_client_for_import,
    get_bulk_career_client_email_send_by_id,
    get_bulk_career_client_email_send_logs as crud_get_bulk_cc_email_logs,
    get_career_client_by_id as crud_get_career_client_by_id,
    get_career_clients,
    get_career_clients_by_ids_or_all as crud_get_by_ids_or_all,
    get_distinct_career_client_locations as crud_get_locations,
    count_career_client_email_rows,
    get_outreach_email_logs_for_career_client,
    list_career_client_email_rows_paginated,
    scan_and_deactivate_career_clients as crud_scan_and_deactivate,
    update_career_client as crud_update_career_client,
    update_bulk_career_client_email_send_status,
)
from app.modules.career_client.models import (
    BulkCareerClientEmailSendStatus,
    CareerClient,
)
from app.modules.career_client.prompts import (
    CAREER_CLIENT_OUTREACH_SYSTEM_PROMPT,
    CAREER_CLIENT_OUTREACH_USER_PROMPT_TEMPLATE,
)
from app.modules.career_client.schemas import (
    CareerClientBulkUpdate,
    CareerClientListResponse,
    CareerClientLocationsResponse,
    CareerClientResponse,
    CareerClientScanCriteria,
    CareerClientScanResponse,
    CareerClientUpdate,
    ClientInvalidEmailsItem,
    RemoveInvalidEmailsItem,
    ValidateEmailsRequest,
    CareerClientBulkEmailSendRequest,
    CareerClientEmailRowResponse,
    CareerClientEmailRowsListResponse,
    BulkCareerClientEmailSendLogListResponse,
    BulkCareerClientEmailSendLogResponse,
    CareerClientImportErrorItem,
    CareerClientImportItem,
    CareerClientImportRequest,
    CareerClientImportResponse,
)
from app.modules.email.service import EmailService
from app.modules.job_application.schemas import EmailLogResponse
from app.modules.llm.service import LLMFactory
from app.modules.resume.crud import get_resume_by_id
from app.modules.scrap_client.services.email_validator import (
    validate_emails_by_domain,
)
from app.modules.websocket.service import broadcast_bulk_career_client_email_send_log
from app.config import get_settings


def _extract_json_object(text_value: str) -> str | None:
    """
    Extract JSON object from LLM response, handling markdown code blocks.
    """
    text_value = text_value.strip()
    if not text_value:
        return None
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text_value)
    if match:
        return match.group(1).strip()
    depth = 0
    start = text_value.find("{")
    if start < 0:
        return None
    for i, c in enumerate(text_value[start:], start):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text_value[start : i + 1]
    return None


def _generate_outreach_document_name() -> str:
    """
    Generate a unique file name prefix for outreach PDFs.
    """
    return f"cc_outreach_{int(time() * 1000)}"


def _render_resume_html(resume_content: dict) -> str:
    """
    Render resume content into HTML using the shared template.
    """
    from jinja2 import Environment, FileSystemLoader

    templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("resumes/resume.html")
    return template.render(resume=resume_content)


def _html_to_pdf(html_content: str, output_path: Path) -> None:
    """
    Convert HTML content to PDF and save to output_path.
    """
    from xhtml2pdf import pisa

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w+b") as dest:
        pisa.CreatePDF(html_content, dest=dest, encoding="utf-8")


def _get_outreach_resume_base_dir() -> Path:
    """
    Return the base directory for career client outreach PDF output.
    """
    settings = get_settings()
    base = Path(settings.JOB_APPLICATION_OUTPUT_FOLDER)
    if not base.is_absolute():
        base = Path(os.getcwd()) / base
    base.mkdir(parents=True, exist_ok=True)
    return base


async def _create_outreach_resume_pdf(
    resume_content: dict, document_name: str
) -> str | None:
    """
    Generate PDF from resume content; return relative path or None on failure.
    """
    try:
        base_dir = _get_outreach_resume_base_dir()
        filename = f"{document_name}.pdf"
        output_path = base_dir / filename
        html_content = _render_resume_html(resume_content)
        _html_to_pdf(html_content, output_path)
        return str(output_path.relative_to(Path(os.getcwd())))
    except Exception:
        return None


def _recipient_email_allowed(client_emails: list, target: str) -> bool:
    """
    Return True if normalized target matches a value in client_emails.
    """
    t = (target or "").strip().lower()
    if not t:
        return False
    for e in client_emails or []:
        if e and str(e).strip().lower() == t:
            return True
    return False


async def _create_bulk_cc_email_log_and_broadcast(
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
    Persist a bulk career client email log row and broadcast it on the user WebSocket.
    """
    async with async_session() as log_db:
        try:
            log = await create_bulk_career_client_email_send_log(
                log_db,
                bulk_career_client_email_send_id=bulk_id,
                action=action,
                progress=progress,
                status=status,
                details=details,
                meta_data=meta_data,
            )
            await log_db.commit()
            await broadcast_bulk_career_client_email_send_log(
                BulkCareerClientEmailSendLogResponse.model_validate(
                    log
                ).model_dump(),
                user_id,
            )
            return log
        except Exception:
            await log_db.rollback()
            raise


async def send_career_client_outreach_email(
    db: AsyncSession,
    client_id: int,
    client_email: str,
    resume_id: int,
    application_detail: str | None,
    user_id: int,
) -> None:
    """
    Build tailored cover letter and resume via LLM, generate PDF, send one email,
    and link the email log to the career client.
    """
    client = await crud_get_career_client_by_id(db, client_id)
    if client is None:
        raise NotFoundException(detail="Career client not found")
    if not _recipient_email_allowed(client.emails or [], client_email):
        raise BadRequestException(
            detail="client_email must be one of the client's stored emails",
        )
    verified = await validate_emails_by_domain([client_email.strip()])
    if not verified:
        raise BadRequestException(detail="client_email failed verification")

    resume = await get_resume_by_id(db, resume_id, user_id)
    if resume is None:
        raise NotFoundException(detail="Resume not found")

    company_context = {
        "name": client.name,
        "detail": client.detail or "",
        "location": client.location or "",
        "official_website": client.official_website or "",
        "size": client.size or "",
    }
    company_context_str = json.dumps(company_context, indent=2, default=str)
    resume_content_raw = resume.content or ""
    resume_extra_detail = getattr(resume, "extra_detail", None) or ""
    application_extra_detail = (application_detail or "").strip()

    prompt = CAREER_CLIENT_OUTREACH_USER_PROMPT_TEMPLATE.format(
        task="create outreach resume and cover letter for this company",
        company_context=company_context_str,
        target_email=client_email.strip(),
        resume_content=resume_content_raw,
        resume_extra_detail=(
            f"{resume_extra_detail}\n\n{application_extra_detail}".strip()
        ),
    )

    llm_client = LLMFactory.get_client(
        provider_name="grok",
        model_name="grok-4-1-fast-reasoning",
    )
    response = await llm_client.generate_content(
        system_prompt=CAREER_CLIENT_OUTREACH_SYSTEM_PROMPT,
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
            detail="Failed to parse LLM response as valid JSON",
        )

    subject = parsed.get("subject") or ""
    cover_letter = parsed.get("cover_letter") or ""
    resume_content = parsed.get("resume_content")
    if not isinstance(resume_content, dict):
        resume_content = {}

    document_name = _generate_outreach_document_name()
    attachment_path = await _create_outreach_resume_pdf(
        resume_content, document_name
    )

    email_service = EmailService()
    send_result = await email_service.send_email(
        recipient=client_email.strip(),
        subject=subject,
        content=cover_letter,
        attachment_path=attachment_path,
        attachment_filename=resume.name,
        raise_on_failure=False,
    )
    email_log_id = send_result.get("email_log_id")
    if email_log_id:
        await create_career_client_email_log(db, client_id, email_log_id)
    if send_result.get("status") != "success":
        raise BadRequestException(
            detail=send_result.get("response") or "Email send failed",
        )


async def start_bulk_career_client_email_send(
    db: AsyncSession,
    request: CareerClientBulkEmailSendRequest,
    user_id: int,
) -> dict:
    """
    Create a bulk career client email send record; processing continues in background.
    """
    resume = await get_resume_by_id(db, request.resume_id, user_id)
    if resume is None:
        raise NotFoundException(detail="Resume not found")

    recipient_dicts = [
        {"client_id": r.client_id, "client_email": r.client_email}
        for r in request.recipients
    ]
    meta_data = {
        "resume_id": request.resume_id,
        "recipients": recipient_dicts,
        "total": len(recipient_dicts),
        "application_detail": (request.application_detail or "").strip(),
    }
    bulk = await create_bulk_career_client_email_send(
        db,
        {
            "user_id": user_id,
            "status": BulkCareerClientEmailSendStatus.PENDING.value,
            "meta_data": meta_data,
        },
    )
    return {
        "id": bulk.id,
        "status": bulk.status,
        "resume_id": request.resume_id,
        "recipients": recipient_dicts,
        "application_detail": (request.application_detail or "").strip(),
    }


async def run_bulk_career_client_email_background(
    bulk_id: int,
    resume_id: int,
    recipients: list[dict],
    application_detail: str | None,
    user_id: int,
) -> None:
    """
    Process each recipient sequentially with logging and WebSocket updates.
    """
    async with async_session() as db:
        try:
            bulk = await get_bulk_career_client_email_send_by_id(db, bulk_id)
            if bulk is None:
                return

            await update_bulk_career_client_email_send_status(
                db, bulk_id, BulkCareerClientEmailSendStatus.IN_PROGRESS.value
            )
            await db.commit()

            await _create_bulk_cc_email_log_and_broadcast(
                db,
                bulk_id,
                user_id,
                "bulk_cc_email_started",
                progress=0,
                status="in_progress",
                details=(
                    "Starting bulk career client email send for "
                    f"{len(recipients)} recipients"
                ),
                meta_data={"total": len(recipients)},
            )

            total = len(recipients)
            success_count = 0
            failed_count = 0

            for idx, rec in enumerate(recipients):
                progress = int((idx / total) * 100) if total > 0 else 0
                cid = rec.get("client_id")
                cemail = rec.get("client_email")
                await _create_bulk_cc_email_log_and_broadcast(
                    db,
                    bulk_id,
                    user_id,
                    "career_client_email_started",
                    progress=progress,
                    status="in_progress",
                    details=f"Sending email {idx + 1}/{total}",
                    meta_data={
                        "client_id": cid,
                        "client_email": cemail,
                        "index": idx + 1,
                        "total": total,
                    },
                )

                try:
                    await asyncio.sleep(random.randint(1, 3))
                    async with async_session() as work_db:
                        await send_career_client_outreach_email(
                            work_db,
                            int(cid),
                            str(cemail),
                            resume_id,
                            application_detail,
                            user_id,
                        )
                        await work_db.commit()
                    success_count += 1
                    await _create_bulk_cc_email_log_and_broadcast(
                        db,
                        bulk_id,
                        user_id,
                        "career_client_email_sent",
                        progress=int(((idx + 1) / total) * 100) if total > 0 else 100,
                        status="completed",
                        details=f"Email sent for client {cid}",
                        meta_data={
                            "client_id": cid,
                            "client_email": cemail,
                            "index": idx + 1,
                            "total": total,
                        },
                    )
                except Exception:
                    failed_count += 1
                    await _create_bulk_cc_email_log_and_broadcast(
                        db,
                        bulk_id,
                        user_id,
                        "career_client_email_failed",
                        progress=int(((idx + 1) / total) * 100) if total > 0 else 100,
                        status="error",
                        details=f"Failed to send for client {cid}",
                        meta_data={
                            "client_id": cid,
                            "client_email": cemail,
                            "index": idx + 1,
                            "total": total,
                        },
                    )

            final_status = BulkCareerClientEmailSendStatus.COMPLETED.value
            if failed_count > 0 and success_count == 0:
                final_status = BulkCareerClientEmailSendStatus.ERROR.value
            elif failed_count > 0:
                final_status = BulkCareerClientEmailSendStatus.COMPLETED.value

            await update_bulk_career_client_email_send_status(
                db, bulk_id, final_status
            )
            await db.commit()

            await _create_bulk_cc_email_log_and_broadcast(
                db,
                bulk_id,
                user_id,
                "bulk_cc_email_completed",
                progress=100,
                status="completed",
                details=(
                    f"Bulk email finished. Success: {success_count}, "
                    f"Failed: {failed_count}"
                ),
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
                    await update_bulk_career_client_email_send_status(
                        err_db,
                        bulk_id,
                        BulkCareerClientEmailSendStatus.ERROR.value,
                    )
                    await err_db.commit()
            except Exception:
                pass


async def get_bulk_career_client_email_send_logs(
    db: AsyncSession,
    bulk_career_client_email_send_id: int,
    user_id: int,
) -> BulkCareerClientEmailSendLogListResponse:
    """
    Return all logs for a bulk career client email send owned by the user.
    """
    bulk = await get_bulk_career_client_email_send_by_id(
        db, bulk_career_client_email_send_id
    )
    if bulk is None:
        raise NotFoundException(detail="Bulk career client email send not found")
    if bulk.user_id != user_id:
        raise NotFoundException(detail="Bulk career client email send not found")

    logs = await crud_get_bulk_cc_email_logs(
        db, bulk_career_client_email_send_id
    )
    return BulkCareerClientEmailSendLogListResponse(
        items=[
            BulkCareerClientEmailSendLogResponse.model_validate(log)
            for log in logs
        ]
    )


async def list_career_client_email_rows(
    db: AsyncSession,
    page: int,
    email_count_sort: str | None,
    created_at_sort: str | None,
) -> CareerClientEmailRowsListResponse:
    """
    Return paginated career client email rows with historical send counts.
    """
    limit = 100
    if page < 1:
        raise BadRequestException(detail="page must be >= 1")
    skip = (page - 1) * limit
    total = await count_career_client_email_rows(db)
    rows = await list_career_client_email_rows_paginated(
        db,
        skip=skip,
        limit=limit,
        email_count_sort=email_count_sort,
        created_at_sort=created_at_sort,
    )
    items = [CareerClientEmailRowResponse.model_validate(r) for r in rows]
    return CareerClientEmailRowsListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


async def get_career_client_outreach_email_logs(
    db: AsyncSession,
    career_client_id: int,
    client_email: str | None,
    user_id: int,
) -> list[EmailLogResponse]:
    """
    Return email logs for outreach sends linked to a career client.
    """
    _ = user_id
    client = await crud_get_career_client_by_id(db, career_client_id)
    if client is None:
        raise NotFoundException(detail="Career client not found")
    logs = await get_outreach_email_logs_for_career_client(
        db, career_client_id, client_email
    )
    return [EmailLogResponse.model_validate(log) for log in logs]


async def get_career_client_by_id(
    db: AsyncSession, career_client_id: int
) -> CareerClientResponse | None:
    """Return a single career client by id or None if not found."""
    client = await crud_get_career_client_by_id(db, career_client_id)
    if client is None:
        return None
    return CareerClientResponse.model_validate(client)


def _normalize_website_host(value: str | None) -> str | None:
    """
    Normalize a website URL or host for duplicate detection during import.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.lower()
    s = re.sub(r"^https?://", "", s, flags=re.I)
    s = s.split("/")[0]
    s = s.split("?")[0]
    if s.startswith("www."):
        s = s[4:]
    s = s.rstrip("/")
    return s or None


def _merge_unique_emails(a: list[str], b: list[str]) -> list[str]:
    """
    Combine email lists while dropping duplicates case-insensitively.
    """
    seen: set[str] = set()
    out: list[str] = []
    for e in a + b:
        if not e or not str(e).strip():
            continue
        key = str(e).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(str(e).strip())
    return out


def _merge_unique_strings(a: list[str], b: list[str]) -> list[str]:
    """
    Combine string lists while dropping duplicates using case-sensitive trim.
    """
    seen: set[str] = set()
    out: list[str] = []
    for e in a + b:
        if not e or not str(e).strip():
            continue
        key = str(e).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _pick_scalar_merge(
    existing_val: str | None,
    incoming_val: str | None,
) -> str | None:
    """
    Prefer a non-empty existing scalar; otherwise fill from incoming when present.
    """
    cur = (existing_val or "").strip() if existing_val else ""
    if cur:
        return existing_val
    inc = (incoming_val or "").strip() if incoming_val else ""
    if inc:
        return inc
    return existing_val


def _build_import_merge_payload(
    existing: CareerClient,
    item: CareerClientImportItem,
    source: str,
) -> dict:
    """
    Build update fields when merging an import row into an existing client.
    """
    merged_emails = _merge_unique_emails(
        list(existing.emails or []),
        list(item.emails or []),
    )
    merged_phones = _merge_unique_strings(
        list(existing.phone_numbers or []),
        list(item.phone_numbers or []),
    )
    nm = _pick_scalar_merge(existing.name, item.name)
    ow = _pick_scalar_merge(existing.official_website, item.official_website)
    loc = _pick_scalar_merge(existing.location, item.location)
    det = _pick_scalar_merge(existing.detail, item.detail)
    meta = dict(existing.meta_data or {})
    meta["source"] = source.strip()
    return {
        "emails": merged_emails,
        "phone_numbers": merged_phones,
        "name": nm,
        "official_website": ow,
        "location": loc,
        "detail": det,
        "meta_data": meta,
    }


def _build_import_create_payload(
    item: CareerClientImportItem,
    source: str,
) -> dict:
    """
    Build column values for creating a client from an import row.
    """
    meta = {"source": source.strip()}
    return {
        "emails": list(item.emails or []),
        "phone_numbers": list(item.phone_numbers or []),
        "official_website": (item.official_website or "").strip() or None,
        "name": (item.name or "").strip() or None,
        "location": (item.location or "").strip() or None,
        "detail": (item.detail or "").strip() or None,
        "meta_data": meta,
    }


async def import_career_clients(
    db: AsyncSession,
    request: CareerClientImportRequest,
) -> CareerClientImportResponse:
    """
    Create or merge career clients from a batch, keyed by name or website host.
    """
    source = request.source.strip()
    created_count = 0
    updated_count = 0
    errors: list[CareerClientImportErrorItem] = []
    for idx, raw in enumerate(request.clients):
        try:
            item = CareerClientImportItem.model_validate(raw)
        except ValidationError as exc:
            errors.append(
                CareerClientImportErrorItem(
                    index=idx,
                    record=dict(raw) if isinstance(raw, dict) else {"raw": raw},
                    message=str(exc),
                )
            )
            continue
        name_stripped = (item.name or "").strip()
        web_key = _normalize_website_host(item.official_website)
        if not name_stripped and not web_key:
            errors.append(
                CareerClientImportErrorItem(
                    index=idx,
                    record=item.model_dump(mode="json"),
                    message="Each client requires name or official_website",
                )
            )
            continue
        try:
            existing = await find_career_client_for_import(
                db,
                name_stripped or None,
                web_key,
            )
            if existing is None:
                payload = _build_import_create_payload(item, source)
                await create_career_client(db, payload)
                created_count += 1
            else:
                payload = _build_import_merge_payload(existing, item, source)
                await crud_update_career_client(db, existing.id, payload)
                updated_count += 1
        except Exception as exc:
            errors.append(
                CareerClientImportErrorItem(
                    index=idx,
                    record=item.model_dump(mode="json"),
                    message=str(exc),
                )
            )
    return CareerClientImportResponse(
        created_count=created_count,
        updated_count=updated_count,
        errors=errors,
    )


async def list_career_clients(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    has_email_information: bool | None = None,
    email_found_error: bool | None = None,
    has_import_source: bool | None = None,
    has_company_details: bool | None = None,
) -> CareerClientListResponse:
    """Return a paginated list of active career clients in descending order."""
    items, total = await get_career_clients(
        db,
        skip=skip,
        limit=limit,
        has_email_information=has_email_information,
        email_found_error=email_found_error,
        has_import_source=has_import_source,
        has_company_details=has_company_details,
    )

    response_items = [CareerClientResponse.model_validate(item) for item in items]

    page = (skip // limit) + 1 if limit > 0 else 1
    return CareerClientListResponse(
        items=response_items,
        total=total,
        page=page,
        limit=limit,
    )


async def update_career_client(
    db: AsyncSession, career_client_id: int, update_data: CareerClientUpdate
) -> CareerClientResponse | None:
    """Update an existing career client and return the updated client or None."""
    data = update_data.model_dump(exclude_unset=True)
    if not data:
        client = await crud_get_career_client_by_id(db, career_client_id)
        return CareerClientResponse.model_validate(client) if client else None
    updated = await crud_update_career_client(db, career_client_id, data)
    return CareerClientResponse.model_validate(updated) if updated else None


async def bulk_update_career_clients(
    db: AsyncSession, location: str, update_data: CareerClientBulkUpdate
) -> int:
    """Bulk update career clients by location. Returns count of updated rows."""
    data = update_data.model_dump(exclude_unset=True)
    if not data:
        return 0
    return await crud_bulk_update(db, location, data)


async def get_career_client_locations(
    db: AsyncSession,
) -> CareerClientLocationsResponse:
    """Return all distinct locations from career clients."""
    locations = await crud_get_locations(db)
    return CareerClientLocationsResponse(locations=locations)


ProgressCallback = Callable[[int, int, int, str], Awaitable[None]] | None


async def _validate_client_emails_core(
    db: AsyncSession,
    request: ValidateEmailsRequest,
    on_progress: ProgressCallback = None,
) -> list[ClientInvalidEmailsItem]:
    """
    Validate emails for specified clients. Returns only clients that have
    invalid emails with their invalid email addresses.
    """
    from app.modules.scrap_client.services.email_validator import (
        validate_emails_by_domain,
    )

    clients = await crud_get_by_ids_or_all(
        db,
        client_ids=request.client_ids,
        all_clients=request.all_clients,
    )
    clients_with_emails = [c for c in clients if c.emails]
    total = len(clients_with_emails)
    result: list[ClientInvalidEmailsItem] = []
    for idx, client in enumerate(clients_with_emails, start=1):
        if on_progress is not None:
            await on_progress(
                idx,
                total,
                client.id,
                client.name or "Unnamed",
            )
        emails = client.emails or []
        valid_emails = await validate_emails_by_domain(emails)
        valid_set = {e.lower().strip() for e in valid_emails}
        invalid = [
            e for e in emails
            if not e or (e.lower().strip() not in valid_set)
        ]
        if invalid:
            result.append(
                ClientInvalidEmailsItem(
                    client_id=client.id,
                    client_name=client.name or "Unnamed",
                    invalid_emails=invalid,
                )
            )
    return result


async def validate_client_emails(
    db: AsyncSession, request: ValidateEmailsRequest
) -> list[ClientInvalidEmailsItem]:
    """Validate client emails (synchronous within request; no progress)."""
    return await _validate_client_emails_core(db, request)


async def run_validate_client_emails_background(
    user_id: int,
    request: ValidateEmailsRequest,
) -> None:
    """
    Run validation in a dedicated session; broadcast progress and result
    to the user's WebSocket channel.
    """
    from app.database import async_session
    from app.modules.websocket.service import (
        broadcast_client_email_validation_completed,
        broadcast_client_email_validation_error,
        broadcast_client_email_validation_progress,
    )

    async def on_progress(
        current: int,
        total: int,
        client_id: int,
        client_name: str,
    ) -> None:
        await broadcast_client_email_validation_progress(
            user_id,
            {
                "current": current,
                "total": total,
                "client_id": client_id,
                "client_name": client_name,
            },
        )

    async with async_session() as db:
        try:
            result = await _validate_client_emails_core(
                db, request, on_progress=on_progress
            )
            await db.commit()
            await broadcast_client_email_validation_completed(
                user_id,
                {
                    "invalid_clients": [
                        item.model_dump(mode="json") for item in result
                    ],
                },
            )
        except Exception as e:
            await db.rollback()
            await broadcast_client_email_validation_error(
                user_id, {"message": str(e)}
            )
            raise


async def remove_invalid_emails(
    db: AsyncSession, items: list[RemoveInvalidEmailsItem]
) -> int:
    """
    Remove specified invalid emails from clients. Returns count of updated clients.
    """
    updated_count = 0
    for item in items:
        client = await crud_get_career_client_by_id(db, item.client_id)
        if client is None:
            continue
        current = list(client.emails or [])
        to_remove = {e.lower().strip() for e in item.invalid_emails if e}
        new_emails = [
            e for e in current
            if e and e.lower().strip() not in to_remove
        ]
        if len(new_emails) != len(current):
            await crud_update_career_client(
                db, item.client_id, {"emails": new_emails}
            )
            updated_count += 1
    return updated_count


async def scan_career_clients(
    db: AsyncSession, criteria: CareerClientScanCriteria
) -> CareerClientScanResponse:
    """
    Scan active career clients and deactivate those failing the given criteria.
    Returns count of deactivated clients.
    """
    min_description = criteria.min_description
    matching_words = None
    if criteria.matching_words and criteria.matching_words.strip():
        matching_words = [
            w.strip()
            for w in criteria.matching_words.split(",")
            if w.strip()
        ]
    deactivated_count = await crud_scan_and_deactivate(
        db,
        min_description=min_description,
        matching_words=matching_words,
    )
    return CareerClientScanResponse(deactivated_count=deactivated_count)
