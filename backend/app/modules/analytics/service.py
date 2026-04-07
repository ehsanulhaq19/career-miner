from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.modules.analytics import crud as analytics_crud
from app.modules.analytics.schemas import AnalyticsDailyRow, AnalyticsSummaryResponse


async def get_analytics_summary(
    db: AsyncSession,
    user_id: int,
    date_from_str: str | None,
    date_to_str: str | None,
) -> AnalyticsSummaryResponse:
    """
    Resolve the requested date range (default: today only), then compute analytics totals
    and per-day buckets for dashboard visualizations.
    """
    today = datetime.utcnow().date()
    raw_from = date_from_str.strip() if date_from_str else None
    raw_to = date_to_str.strip() if date_to_str else None
    if not raw_from and not raw_to:
        d_from = d_to = today
    elif raw_from and raw_to:
        d_from = _parse_date_param(raw_from, "date_from")
        d_to = _parse_date_param(raw_to, "date_to")
    elif raw_from:
        d_from = _parse_date_param(raw_from, "date_from")
        d_to = d_from
    elif raw_to:
        d_to = _parse_date_param(raw_to, "date_to")
        d_from = d_to

    if d_from > d_to:
        raise BadRequestException(detail="date_from must be on or before date_to")

    scrap_web_rows = await analytics_crud.fetch_scrap_web_rows_for_range(
        db, d_from, d_to
    )
    scrap_client_rows = await analytics_crud.fetch_scrap_client_rows_for_range(
        db, d_from, d_to
    )
    sw_runs, sw_scraped, sw_by_day = analytics_crud.aggregate_scrap_web_from_rows(
        scrap_web_rows
    )
    sc_runs, sc_scraped, sc_by_day = analytics_crud.aggregate_scrap_client_from_rows(
        scrap_client_rows
    )

    jobs_created = await analytics_crud.count_career_jobs_created_in_range(
        db, d_from, d_to
    )
    clients_created = await analytics_crud.count_career_clients_created_in_range(
        db, d_from, d_to
    )
    apps_created = await analytics_crud.count_job_applications_created_in_range(
        db, user_id, d_from, d_to
    )
    email_by_status = await analytics_crud.count_job_application_emails_by_status_in_range(
        db, user_id, d_from, d_to
    )
    email_ok, email_err = analytics_crud.split_email_status_totals(email_by_status)
    workflows_done = await analytics_crud.count_completed_workflow_executions_in_range(
        db, user_id, d_from, d_to
    )

    jobs_by_day = await analytics_crud.career_jobs_created_by_day(db, d_from, d_to)
    clients_by_day = await analytics_crud.career_clients_created_by_day(db, d_from, d_to)
    apps_by_day = await analytics_crud.job_applications_created_by_day(
        db, user_id, d_from, d_to
    )
    emails_by_day = await analytics_crud.job_application_emails_by_day_and_status(
        db, user_id, d_from, d_to
    )
    wf_by_day = await analytics_crud.completed_workflow_executions_by_day(
        db, user_id, d_from, d_to
    )

    daily: list[AnalyticsDailyRow] = []
    for day in analytics_crud.iter_dates_inclusive(d_from, d_to):
        sw_d = sw_by_day.get(day, (0, 0))
        sc_d = sc_by_day.get(day, (0, 0))
        em_day = emails_by_day.get(day, {})
        em_ok, em_er = analytics_crud.split_email_status_totals(em_day)
        daily.append(
            AnalyticsDailyRow(
                day=day,
                scrap_web_jobs_run=sw_d[0],
                scrap_web_scraped_records=sw_d[1],
                scrap_client_jobs_run=sc_d[0],
                scrap_client_scraped_records=sc_d[1],
                jobs_created=jobs_by_day.get(day, 0),
                clients_created=clients_by_day.get(day, 0),
                job_applications_created=apps_by_day.get(day, 0),
                job_application_emails_success=em_ok,
                job_application_emails_error=em_er,
                workflows_completed=wf_by_day.get(day, 0),
            )
        )

    return AnalyticsSummaryResponse(
        date_from=d_from,
        date_to=d_to,
        scrap_web_jobs_run=sw_runs,
        scrap_web_scraped_records=sw_scraped,
        scrap_client_jobs_run=sc_runs,
        scrap_client_scraped_records=sc_scraped,
        jobs_created=jobs_created,
        clients_created=clients_created,
        job_applications_created=apps_created,
        job_application_emails_success=email_ok,
        job_application_emails_error=email_err,
        workflows_completed=workflows_done,
        daily=daily,
    )


def _parse_date_param(value: str, field_name: str) -> date:
    """Parse YYYY-MM-DD query/body values into a date or raise BadRequestException."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise BadRequestException(
            detail=f"{field_name} must be YYYY-MM-DD"
        ) from exc
