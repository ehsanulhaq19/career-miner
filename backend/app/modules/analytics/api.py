from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.analytics.schemas import AnalyticsSummaryResponse
from app.modules.analytics.service import get_analytics_summary

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary_endpoint(
    date_from: str | None = Query(None, description="Start date YYYY-MM-DD; defaults to today"),
    date_to: str | None = Query(None, description="End date YYYY-MM-DD; defaults to today"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsSummaryResponse:
    """
    Return aggregate metrics and daily series for scrap runs, career data, applications,
    application emails, and completed workflow executions.
    """
    return await get_analytics_summary(
        db, current_user.id, date_from, date_to
    )
