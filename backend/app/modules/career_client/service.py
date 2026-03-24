from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.crud import (
    bulk_update_career_clients_by_location as crud_bulk_update,
    get_career_client_by_id as crud_get_career_client_by_id,
    get_career_clients,
    get_career_clients_by_ids_or_all as crud_get_by_ids_or_all,
    get_distinct_career_client_locations as crud_get_locations,
    scan_and_deactivate_career_clients as crud_scan_and_deactivate,
    get_total_career_clients_count,
    update_career_client as crud_update_career_client,
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
)


async def get_career_client_by_id(
    db: AsyncSession, career_client_id: int
) -> CareerClientResponse | None:
    """Return a single career client by id or None if not found."""
    client = await crud_get_career_client_by_id(db, career_client_id)
    if client is None:
        return None
    return CareerClientResponse.model_validate(client)


async def list_career_clients(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    has_email_information: bool | None = None,
) -> CareerClientListResponse:
    """Return a paginated list of active career clients in descending order."""
    items, total = await get_career_clients(
        db,
        skip=skip,
        limit=limit,
        has_email_information=has_email_information,
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
