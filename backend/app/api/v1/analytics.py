# Analytics dashboard endpoints (v1) -- read-only and user-scoped.

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_analytics_service, get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import (
    AIUsageAnalytics,
    AnalyticsOverview,
    ApplicationAnalytics,
    MatchAnalytics,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
) -> AnalyticsOverview:
    """Return high-level dashboard metrics for the current user."""
    return service.overview(
        db,
        current_user.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@router.get("/applications", response_model=ApplicationAnalytics)
def get_application_analytics(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
) -> ApplicationAnalytics:
    """Return application funnel and time-series analytics."""
    return service.applications(
        db, current_user.id, start_date=start_date, end_date=end_date
    )


@router.get("/matches", response_model=MatchAnalytics)
def get_match_analytics(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
) -> MatchAnalytics:
    """Return deterministic job-match analytics for the current user."""
    return service.matches(
        db,
        current_user.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@router.get("/ai-usage", response_model=AIUsageAnalytics)
def get_ai_usage_analytics(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(get_current_user),
) -> AIUsageAnalytics:
    """Return generated-item and failure counts for AI-backed features."""
    return service.ai_usage(
        db, current_user.id, start_date=start_date, end_date=end_date
    )
