from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.career_client.schemas import (
    BulkCareerClientEmailSendLogListResponse,
    CareerClientBulkEmailSendRequest,
    CareerClientBulkUpdate,
    CareerClientEmailRowsListResponse,
    CareerClientListResponse,
    CareerClientLocationsResponse,
    CareerClientResponse,
    CareerClientScanCriteria,
    CareerClientUpdate,
    RemoveInvalidEmailsRequest,
    ValidateEmailsRequest,
    ValidateEmailsStartedResponse,
)
from app.modules.job_application.schemas import EmailLogResponse
from app.modules.career_client.service import (
    bulk_update_career_clients,
    get_bulk_career_client_email_send_logs,
    get_career_client_by_id,
    get_career_client_locations,
    get_career_client_outreach_email_logs,
    list_career_client_email_rows,
    list_career_clients,
    remove_invalid_emails,
    run_bulk_career_client_email_background,
    scan_career_clients,
    start_bulk_career_client_email_send,
    update_career_client,
    run_validate_client_emails_background,
)

router = APIRouter()


async def _validate_client_emails_background_task(
    user_id: int,
    body: dict,
) -> None:
    """Run email validation with a fresh DB session; progress via WebSocket."""
    req = ValidateEmailsRequest.model_validate(body)
    await run_validate_client_emails_background(user_id, req)


@router.get(
    "/email-rows",
    response_model=CareerClientEmailRowsListResponse,
)
async def list_career_client_email_rows_endpoint(
    page: int = Query(1, ge=1),
    email_count: Literal["asc", "desc"] | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientEmailRowsListResponse:
    """
    List each career client email with send counts from email logs.
    Fixed page size 100. Optional email_count sorts rows by log count.
    """
    _ = current_user
    return await list_career_client_email_rows(
        db, page=page, email_count_sort=email_count
    )


@router.post("/bulk-email/send", status_code=201)
async def bulk_send_career_client_emails_endpoint(
    request: CareerClientBulkEmailSendRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Queue bulk outreach emails using LLM-tailored cover letter and resume per recipient.
    """
    result = await start_bulk_career_client_email_send(
        db, request, current_user.id
    )
    background_tasks.add_task(
        run_bulk_career_client_email_background,
        result["id"],
        result["resume_id"],
        result["recipients"],
        current_user.id,
    )
    return {"id": result["id"], "status": result["status"]}


@router.get(
    "/bulk-email/{bulk_id}/logs",
    response_model=BulkCareerClientEmailSendLogListResponse,
)
async def get_bulk_career_client_email_logs_endpoint(
    bulk_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkCareerClientEmailSendLogListResponse:
    """
    Return progress logs for a bulk career client email send.
    """
    return await get_bulk_career_client_email_send_logs(
        db, bulk_id, current_user.id
    )


@router.get("/", response_model=CareerClientListResponse)
async def list_career_clients_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    has_email_information: bool | None = Query(None),
    email_found_error: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientListResponse:
    """List active career clients with pagination in descending order."""
    return await list_career_clients(
        db,
        skip=skip,
        limit=limit,
        has_email_information=has_email_information,
        email_found_error=email_found_error,
    )


@router.get("/locations", response_model=CareerClientLocationsResponse)
async def get_career_client_locations_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientLocationsResponse:
    """Return all distinct locations from career clients."""
    return await get_career_client_locations(db)


@router.get(
    "/{career_client_id}/outreach-email-logs",
    response_model=list[EmailLogResponse],
)
async def get_career_client_outreach_email_logs_endpoint(
    career_client_id: int,
    client_email: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailLogResponse]:
    """
    Return email logs linked to outreach sends for this client and optional email.
    """
    return await get_career_client_outreach_email_logs(
        db,
        career_client_id,
        client_email,
        current_user.id,
    )


@router.get("/{career_client_id}", response_model=CareerClientResponse)
async def get_career_client_endpoint(
    career_client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientResponse:
    """Return a single career client by id."""
    client = await get_career_client_by_id(db, career_client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Career client not found")
    return client


@router.put("/{career_client_id}", response_model=CareerClientResponse)
async def update_career_client_endpoint(
    career_client_id: int,
    career_client_update: CareerClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerClientResponse:
    """Update an existing career client."""
    updated = await update_career_client(
        db, career_client_id, career_client_update
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Career client not found")
    return updated


@router.put("/bulk-update/location")
async def bulk_update_career_clients_endpoint(
    bulk_update: CareerClientBulkUpdate,
    location: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Bulk update career clients by location."""
    count = await bulk_update_career_clients(db, location, bulk_update)
    return {"updated_count": count}


@router.post("/scan")
async def scan_career_clients_endpoint(
    criteria: CareerClientScanCriteria,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Scan active career clients and deactivate those failing the given criteria.
    Returns count of deactivated clients.
    """
    has_min_desc = criteria.min_description is not None
    has_words = criteria.matching_words and criteria.matching_words.strip()
    if not has_min_desc and not has_words:
        raise HTTPException(
            status_code=400,
            detail="At least one criterion must be provided",
        )
    result = await scan_career_clients(db, criteria)
    return {"deactivated_count": result.deactivated_count}


@router.post("/validate-emails", response_model=ValidateEmailsStartedResponse)
async def validate_client_emails_endpoint(
    request: ValidateEmailsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> ValidateEmailsStartedResponse:
    """
    Validate client emails in the background. Accept client_ids or all_clients=true.
    Progress and final results are sent on the client_email_validation WebSocket.
    """
    background_tasks.add_task(
        _validate_client_emails_background_task,
        current_user.id,
        request.model_dump(),
    )
    return ValidateEmailsStartedResponse()


@router.post("/remove-invalid-emails")
async def remove_invalid_emails_endpoint(
    request: RemoveInvalidEmailsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove specified invalid emails from clients.
    """
    count = await remove_invalid_emails(db, request.clients)
    return {"updated_count": count}
