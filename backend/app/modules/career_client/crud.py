from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.career_client.models import (
    BulkCareerClientEmailSend,
    BulkCareerClientEmailSendLog,
    CareerClient,
    CareerClientEmailLog,
    CareerClientScrapClientJobLink,
)


def _apply_email_found_error_filter(query, email_found_error: bool | None):
    """
    Filter by meta_data.email_found_error.
    True: only clients with flag true. False: exclude flag true. None: no filter.
    """
    if email_found_error is None:
        return query
    if email_found_error is True:
        return query.where(
            text("(career_clients.meta_data->>'email_found_error') = 'true'")
        )
    return query.where(
        text(
            "coalesce(career_clients.meta_data->>'email_found_error', 'false') != 'true'"
        )
    )


def _apply_has_import_source_filter(query, has_import_source: bool | None):
    """
    When True, keep rows whose meta_data defines a non-empty source.
    When False, keep rows with no import source. When None, no filter.
    """
    if has_import_source is None:
        return query
    if has_import_source is True:
        return query.where(
            text(
                "(career_clients.meta_data->>'source') IS NOT NULL "
                "AND trim(career_clients.meta_data->>'source') != ''"
            )
        )
    return query.where(
        text(
            "coalesce(trim(career_clients.meta_data->>'source'), '') = ''"
        )
    )


def _apply_has_email_filter(query, has_email_information: bool | None):
    """
    Apply email filter to query based on has_email_information.
    True: only clients with emails. False: only clients without emails. None: no filter.
    """
    if has_email_information is None:
        return query
    if has_email_information is True:
        return query.where(func.json_array_length(CareerClient.emails) > 0)
    return query.where(
        (func.coalesce(func.json_array_length(CareerClient.emails), 0) == 0)
        | (CareerClient.emails.is_(None))
    )


def _apply_has_company_details_filter(query, has_company_details: bool | None):
    """
    Filter by company profile detail text and meta_data.company_found_error.
    True: non-empty detail and company_found_error is not true.
    False: empty or whitespace-only detail, or company_found_error is true (failed enrichment).
    None: no filter.
    """
    if has_company_details is None:
        return query
    trimmed_len = func.length(
        func.trim(func.coalesce(CareerClient.detail, ""))
    )
    company_err_true = text(
        "(career_clients.meta_data->>'company_found_error') = 'true'"
    )
    company_err_not_true = text(
        "coalesce(career_clients.meta_data->>'company_found_error', 'false') != 'true'"
    )
    if has_company_details is True:
        return query.where(and_(trimmed_len > 0, company_err_not_true))
    return query.where(
        or_(trimmed_len == 0, company_err_true),
    )


async def get_career_clients_by_ids_or_all(
    db: AsyncSession,
    client_ids: list[int] | None = None,
    all_clients: bool = False,
    created_by: int | None = None,
) -> list[CareerClient]:
    """
    Retrieve career clients by ids or all active clients.
    When client_ids provided, returns only those active clients. When all_clients
    True and no client_ids, returns all active clients.
    """
    query = select(CareerClient).where(CareerClient.is_active.is_(True))
    if created_by is not None:
        query = query.where(CareerClient.created_by == created_by)
    if client_ids:
        query = query.where(CareerClient.id.in_(client_ids))
    query = query.order_by(CareerClient.id.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_career_clients(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    has_email_information: bool | None = None,
    email_found_error: bool | None = None,
    has_import_source: bool | None = None,
    has_company_details: bool | None = None,
    created_by: int | None = None,
) -> tuple[list[CareerClient], int]:
    """Retrieve a paginated list of active career clients in descending order by id."""
    base_query = (
        select(CareerClient)
        .where(CareerClient.is_active.is_(True))
        .order_by(CareerClient.id.desc())
    )
    if created_by is not None:
        base_query = base_query.where(CareerClient.created_by == created_by)
    base_query = _apply_has_email_filter(base_query, has_email_information)
    base_query = _apply_email_found_error_filter(base_query, email_found_error)
    base_query = _apply_has_import_source_filter(base_query, has_import_source)
    base_query = _apply_has_company_details_filter(base_query, has_company_details)
    query = base_query.offset(skip).limit(limit)

    count_query = select(func.count(CareerClient.id)).where(
        CareerClient.is_active.is_(True)
    )
    if created_by is not None:
        count_query = count_query.where(CareerClient.created_by == created_by)
    if has_email_information is True:
        count_query = count_query.where(
            func.json_array_length(CareerClient.emails) > 0
        )
    elif has_email_information is False:
        count_query = count_query.where(
            (func.coalesce(func.json_array_length(CareerClient.emails), 0) == 0)
            | (CareerClient.emails.is_(None))
        )
    count_query = _apply_email_found_error_filter(count_query, email_found_error)
    count_query = _apply_has_import_source_filter(count_query, has_import_source)
    count_query = _apply_has_company_details_filter(count_query, has_company_details)

    result = await db.execute(query)
    items = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return items, total


async def get_career_client_by_id(
    db: AsyncSession, career_client_id: int
) -> CareerClient | None:
    """Retrieve a single career client by its primary key."""
    result = await db.execute(
        select(CareerClient).where(CareerClient.id == career_client_id)
    )
    return result.scalars().first()


async def get_career_client_by_link(
    db: AsyncSession, link: str | None, created_by: int | None = None
) -> CareerClient | None:
    """Retrieve a career client by link when link is non-empty."""
    if not link or not str(link).strip():
        return None
    q = select(CareerClient).where(CareerClient.link == link.strip())
    if created_by is not None:
        q = q.where(CareerClient.created_by == created_by)
    result = await db.execute(q)
    return result.scalars().first()


async def get_career_client_by_name(
    db: AsyncSession, name: str | None, created_by: int | None = None
) -> CareerClient | None:
    """Retrieve a career client by name when name is non-empty."""
    if not name or not str(name).strip():
        return None
    q = select(CareerClient).where(CareerClient.name == name.strip())
    if created_by is not None:
        q = q.where(CareerClient.created_by == created_by)
    result = await db.execute(q)
    return result.scalars().first()


async def get_career_client_by_normalized_host(
    db: AsyncSession,
    normalized_host: str,
    created_by: int | None = None,
) -> CareerClient | None:
    """
    Find a career client whose official_website normalizes to the same host key.
    """
    if not normalized_host or not str(normalized_host).strip():
        return None
    host = str(normalized_host).strip().lower()
    owner_sql = " AND created_by = :created_by " if created_by is not None else ""
    stmt = text(
        f"""
        SELECT id FROM career_clients
        WHERE official_website IS NOT NULL
          AND trim(official_website) != ''
          AND lower(
            regexp_replace(
              regexp_replace(
                split_part(
                  regexp_replace(trim(official_website), '^https?://', '', 'gi'),
                  '/',
                  1
                ),
                '^www\\.',
                '',
                'i'
              ),
              '/$',
              ''
            )
          ) = :host
          {owner_sql}
        ORDER BY id DESC
        LIMIT 1
        """
    )
    if created_by is not None:
        stmt = stmt.bindparams(host=host, created_by=created_by)
    else:
        stmt = stmt.bindparams(host=host)
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None
    return await get_career_client_by_id(db, int(row[0]))


async def find_career_client_for_import(
    db: AsyncSession,
    name: str | None,
    normalized_website_host: str | None,
    created_by: int,
) -> CareerClient | None:
    """
    Resolve an existing career client by exact name or by normalized website host.
    """
    if name and str(name).strip():
        found = await get_career_client_by_name(db, name, created_by=created_by)
        if found is not None:
            return found
    if normalized_website_host:
        return await get_career_client_by_normalized_host(
            db, normalized_website_host, created_by=created_by
        )
    return None


async def create_career_client(db: AsyncSession, data: dict) -> CareerClient:
    """Create a new career client record from the provided data dictionary."""
    career_client = CareerClient(**data)
    db.add(career_client)
    await db.flush()
    await db.refresh(career_client)
    return career_client


async def record_career_client_scrap_client_job_link(
    db: AsyncSession,
    career_client_id: int,
    scrap_client_job_id: int,
) -> CareerClientScrapClientJobLink:
    """
    Append a pivot row linking a career client to a scrap client job without removing history.
    """
    row = CareerClientScrapClientJobLink(
        career_client_id=career_client_id,
        scrap_client_job_id=scrap_client_job_id,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def update_career_client(
    db: AsyncSession,
    career_client_id: int,
    data: dict,
) -> CareerClient | None:
    """Update an existing career client with the provided data."""
    client = await get_career_client_by_id(db, career_client_id)
    if client is None:
        return None
    for key, value in data.items():
        if hasattr(client, key):
            setattr(client, key, value)
    await db.flush()
    if "scrap_client_job_id" in data and data.get("scrap_client_job_id") is not None:
        await record_career_client_scrap_client_job_link(
            db,
            career_client_id,
            int(data["scrap_client_job_id"]),
        )
    await db.refresh(client)
    return client


async def assign_scrap_client_job_to_career_clients(
    db: AsyncSession,
    career_client_ids: list[int],
    scrap_client_job_id: int,
    created_by: int,
) -> None:
    """
    Assign scrap_client_job_id to the given career clients when a job is initiated.
    """
    if not career_client_ids:
        return
    unique_ids = list(dict.fromkeys(int(x) for x in career_client_ids))
    await db.execute(
        update(CareerClient)
        .where(CareerClient.id.in_(unique_ids))
        .where(CareerClient.created_by == created_by)
        .values(scrap_client_job_id=scrap_client_job_id)
    )
    await db.flush()
    for cid in unique_ids:
        await record_career_client_scrap_client_job_link(db, cid, scrap_client_job_id)


async def get_career_clients_without_emails(
    db: AsyncSession,
    limit: int = 1000,
    client_ids: list[int] | None = None,
) -> list[CareerClient]:
    """
    Retrieve career clients that have no emails, optionally filtered by ids.
    Excludes clients with meta_data.email_found_error true (scrap already failed).
    """
    query = select(CareerClient).where(
        func.coalesce(func.json_array_length(CareerClient.emails), 0) == 0
    )
    query = query.where(
        text(
            "coalesce(career_clients.meta_data->>'email_found_error', 'false') != 'true'"
        )
    )
    if client_ids:
        query = query.where(CareerClient.id.in_(client_ids))
    query = query.where(CareerClient.name.isnot(None)).where(
        CareerClient.name != ""
    ).order_by(CareerClient.id.asc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_total_career_clients_count(db: AsyncSession) -> int:
    """Return the total count of all career clients."""
    result = await db.execute(select(func.count(CareerClient.id)))
    return result.scalar() or 0


async def bulk_update_career_clients_by_location(
    db: AsyncSession, location: str, data: dict, created_by: int
) -> int:
    """Update all career clients with the given location. Returns count of updated rows."""
    from sqlalchemy import update

    stmt = (
        update(CareerClient)
        .where(CareerClient.location == location)
        .where(CareerClient.created_by == created_by)
        .values(**data)
    )
    result = await db.execute(stmt)
    return result.rowcount or 0


async def get_distinct_career_client_locations(
    db: AsyncSession,
    created_by: int | None = None,
) -> list[str]:
    """Retrieve all distinct non-null, non-empty location values from career clients."""
    q = (
        select(CareerClient.location)
        .where(CareerClient.location.isnot(None))
        .where(CareerClient.location != "")
    )
    if created_by is not None:
        q = q.where(CareerClient.created_by == created_by)
    result = await db.execute(q.distinct().order_by(CareerClient.location))
    return [row[0] for row in result.all() if row[0]]


async def scan_and_deactivate_career_clients(
    db: AsyncSession,
    min_description: int | None = None,
    matching_words: list[str] | None = None,
    created_by: int | None = None,
) -> int:
    """
    Deactivate active career clients that fail the given criteria.
    Returns count of deactivated clients.
    """
    if not min_description and not matching_words:
        return 0
    conditions = []
    if min_description is not None:
        detail_length = func.coalesce(func.length(CareerClient.detail), 0)
        conditions.append(detail_length < min_description)
    if matching_words:
        words = [w.strip() for w in matching_words if w and w.strip()]
        if words:
            name_conditions = [
                CareerClient.name.ilike(f"%{w}%") for w in words
            ]
            conditions.append(or_(*name_conditions))
    if not conditions:
        return 0
    stmt = (
        update(CareerClient)
        .where(CareerClient.is_active.is_(True))
        .where(or_(*conditions))
    )
    if created_by is not None:
        stmt = stmt.where(CareerClient.created_by == created_by)
    stmt = stmt.values(is_active=False)
    result = await db.execute(stmt)
    return result.rowcount or 0


async def get_or_create_career_client(
    db: AsyncSession,
    name: str | None,
    link: str | None,
    location: str | None,
    emails: list[str],
    detail: str | None,
    size: str | None,
    created_by: int,
) -> CareerClient | None:
    """
    Get existing career client by link or name, or create new one if not found.
    Returns None if both name and link are empty.
    """
    client = None
    if link and str(link).strip():
        client = await get_career_client_by_link(db, link, created_by=created_by)
    if client is None and name and str(name).strip():
        client = await get_career_client_by_name(db, name, created_by=created_by)
    if client is not None:
        return client
    has_name = name and str(name).strip()
    has_link = link and str(link).strip()
    if not has_name and not has_link:
        return None
    client_data = {
        "emails": emails or [],
        "name": name.strip() if name else None,
        "location": location.strip() if location else None,
        "detail": detail.strip() if detail else None,
        "link": link.strip() if link else None,
        "size": size.strip() if size else None,
        "meta_data": {},
        "created_by": created_by,
    }
    return await create_career_client(db, client_data)


async def create_career_client_email_log(
    db: AsyncSession,
    career_client_id: int,
    email_log_id: int,
) -> CareerClientEmailLog:
    """
    Create a pivot row linking a career client to an email log entry.
    """
    row = CareerClientEmailLog(
        career_client_id=career_client_id,
        email_log_id=email_log_id,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def create_bulk_career_client_email_send(
    db: AsyncSession,
    data: dict,
) -> BulkCareerClientEmailSend:
    """
    Create a new bulk career client email send record.
    """
    record = BulkCareerClientEmailSend(**data)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def get_bulk_career_client_email_send_by_id(
    db: AsyncSession,
    bulk_id: int,
) -> BulkCareerClientEmailSend | None:
    """
    Retrieve a bulk career client email send by id.
    """
    result = await db.execute(
        select(BulkCareerClientEmailSend).where(
            BulkCareerClientEmailSend.id == bulk_id
        )
    )
    return result.scalars().first()


async def create_bulk_career_client_email_send_log(
    db: AsyncSession,
    bulk_career_client_email_send_id: int,
    action: str,
    progress: int = 0,
    status: str = "pending",
    details: str | None = None,
    meta_data: dict | None = None,
) -> BulkCareerClientEmailSendLog:
    """
    Create a new bulk career client email send log entry.
    """
    log = BulkCareerClientEmailSendLog(
        bulk_career_client_email_send_id=bulk_career_client_email_send_id,
        action=action,
        progress=progress,
        status=status,
        details=details,
        meta_data=meta_data or {},
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_bulk_career_client_email_send_logs(
    db: AsyncSession,
    bulk_career_client_email_send_id: int,
) -> list[BulkCareerClientEmailSendLog]:
    """
    Retrieve all logs for a bulk career client email send.
    """
    result = await db.execute(
        select(BulkCareerClientEmailSendLog)
        .where(
            BulkCareerClientEmailSendLog.bulk_career_client_email_send_id
            == bulk_career_client_email_send_id
        )
        .order_by(BulkCareerClientEmailSendLog.created_at.asc())
    )
    return list(result.scalars().all())


async def update_bulk_career_client_email_send_status(
    db: AsyncSession,
    bulk_id: int,
    status: str,
) -> BulkCareerClientEmailSend | None:
    """
    Update the status of a bulk career client email send.
    """
    record = await get_bulk_career_client_email_send_by_id(db, bulk_id)
    if record is None:
        return None
    record.status = status
    await db.flush()
    await db.refresh(record)
    return record


def _email_rows_order_clause(
    email_count_sort: str | None,
    created_at_sort: str | None,
) -> str:
    """
    Build an ORDER BY clause for email row listing (whitelist only).
    """
    if email_count_sort == "asc":
        return "email_count ASC, client_id DESC, client_email ASC"
    if email_count_sort == "desc":
        return "email_count DESC, client_id DESC, client_email ASC"
    if created_at_sort == "asc":
        return "created_at ASC, client_id DESC, client_email ASC"
    if created_at_sort == "desc":
        return "created_at DESC, client_id DESC, client_email ASC"
    return "client_id DESC, client_email ASC"


async def count_career_client_email_rows(
    db: AsyncSession, created_by: int | None = None
) -> int:
    """
    Count total flattened career client email rows (one per stored email).
    """
    owner_clause = " AND c.created_by = :created_by " if created_by is not None else ""
    stmt = text(
        f"""
        WITH expanded AS (
            SELECT
                c.id AS client_id,
                e.elem AS client_email
            FROM career_clients c
            CROSS JOIN LATERAL jsonb_array_elements_text(
                COALESCE(c.emails::jsonb, '[]'::jsonb)
            ) AS e(elem)
            WHERE c.is_active = true
          {owner_clause}
        )
        SELECT COUNT(*) AS n FROM expanded
        """
    )
    if created_by is not None:
        stmt = stmt.bindparams(created_by=created_by)
    result = await db.execute(stmt)
    row = result.first()
    return int(row[0]) if row and row[0] is not None else 0


async def list_career_client_email_rows_paginated(
    db: AsyncSession,
    skip: int,
    limit: int,
    email_count_sort: str | None,
    created_at_sort: str | None,
    created_by: int | None = None,
) -> list[dict]:
    """
    List flattened client emails with send counts from email_logs, paginated.
    """
    order_sql = _email_rows_order_clause(email_count_sort, created_at_sort)
    owner_clause = " AND c.created_by = :created_by " if created_by is not None else ""
    stmt = text(
        f"""
        WITH expanded AS (
            SELECT
                c.id AS client_id,
                c.name AS client_name,
                c.official_website,
                c.location,
                c.created_at,
                e.elem AS client_email
            FROM career_clients c
            CROSS JOIN LATERAL jsonb_array_elements_text(
                COALESCE(c.emails::jsonb, '[]'::jsonb)
            ) AS e(elem)
            WHERE c.is_active = true
          {owner_clause}
        ),
        counts AS (
            SELECT LOWER(TRIM(to_email)) AS norm_email, COUNT(*)::int AS email_count
            FROM email_logs
            GROUP BY LOWER(TRIM(to_email))
        ),
        with_counts AS (
            SELECT
                ex.client_id,
                ex.client_name,
                ex.official_website,
                ex.location,
                ex.created_at,
                ex.client_email,
                COALESCE(ct.email_count, 0)::int AS email_count
            FROM expanded ex
            LEFT JOIN counts ct
                ON ct.norm_email = LOWER(TRIM(ex.client_email))
        )
        SELECT
            client_id,
            client_name,
            official_website,
            location,
            created_at,
            client_email,
            email_count
        FROM with_counts
        ORDER BY {order_sql}
        OFFSET :skip LIMIT :limit
        """
    )
    if created_by is not None:
        stmt = stmt.bindparams(skip=skip, limit=limit, created_by=created_by)
    else:
        stmt = stmt.bindparams(skip=skip, limit=limit)
    result = await db.execute(stmt)
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def get_outreach_email_logs_for_career_client(
    db: AsyncSession,
    career_client_id: int,
    client_email: str | None,
) -> list:
    """
    Return email logs linked to a career client, optionally filtered by recipient email.
    """
    from app.modules.email.models import EmailLog

    q = (
        select(EmailLog)
        .join(
            CareerClientEmailLog,
            CareerClientEmailLog.email_log_id == EmailLog.id,
        )
        .where(CareerClientEmailLog.career_client_id == career_client_id)
        .order_by(EmailLog.created_at.desc())
    )
    if client_email and str(client_email).strip():
        norm = str(client_email).strip().lower()
        q = q.where(func.lower(func.trim(EmailLog.to_email)) == norm)
    result = await db.execute(q)
    return list(result.scalars().all())
