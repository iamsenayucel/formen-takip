from dataclasses import replace
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.authz_deps import require_permission, scoped_filters
from app.core.permissions import Permission
from app.db.session import get_db
from app.schemas.authz import AuthContext
from app.schemas.base import ApiResponse
from app.schemas.common import Filters
from app.schemas.dashboard import (
    DashboardSnapshot,
    DashboardSummary,
    ForemanRankingItem,
    ForemanTrendRankingItem,
    KpiSummaryItem,
    PerformanceDistributionResponse,
    PerformanceLeadersResponse,
    PlantRankingItem,
    ShiftComparisonItem,
    TrendResponse,
)
from app.services import analytics
from app.services.dashboard_comparison_service import DashboardComparisonService
from app.services.dashboard_foreman_service import DashboardForemanService
from app.services.dashboard_overview_service import DashboardOverviewService
from app.services.performance_leaders_service import PerformanceLeadersService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_require_overview = require_permission(Permission.OVERVIEW_VIEW)


def _previous_period_filters(filters: Filters) -> Filters:
    period_days = (filters.date_to - filters.date_from).days + 1
    return replace(
        filters,
        date_from=filters.date_from - timedelta(days=period_days),
        date_to=filters.date_from - timedelta(days=1),
    )


@router.get("/summary", response_model=ApiResponse[DashboardSummary])
def summary(
    filters: Filters = Depends(scoped_filters), db: Session = Depends(get_db), _ctx: AuthContext = Depends(_require_overview)
) -> ApiResponse[DashboardSummary]:
    service = DashboardOverviewService(db)
    return {"data": service.summary(filters)}


@router.get("/trend", response_model=ApiResponse[TrendResponse])
def trend(
    granularity: str = Query("day", pattern="^(day|week|month|quarter|year)$"),
    filters: Filters = Depends(scoped_filters),
    db: Session = Depends(get_db),
    _ctx: AuthContext = Depends(_require_overview),
) -> ApiResponse[TrendResponse]:
    points = analytics.trend(db, filters, granularity)
    return {
        "data": {
            "granularity": granularity,
            "points": [
                {"date": p.bucket.isoformat(), "total_score": round(p.total_score, 2), "is_reliable": p.is_reliable}
                for p in points
            ],
        }
    }


@router.get("/kpi-summary", response_model=ApiResponse[list[KpiSummaryItem]])
def kpi_summary(
    filters: Filters = Depends(scoped_filters), db: Session = Depends(get_db), _ctx: AuthContext = Depends(_require_overview)
) -> ApiResponse[list[KpiSummaryItem]]:
    service = DashboardComparisonService(db)
    return {"data": service.kpi_summary(filters)["items"]}


@router.get("/plant-ranking", response_model=ApiResponse[list[PlantRankingItem]])
def plant_ranking(
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=50),
    filters: Filters = Depends(scoped_filters),
    db: Session = Depends(get_db),
    _ctx: AuthContext = Depends(_require_overview),
) -> ApiResponse[list[PlantRankingItem]]:
    service = DashboardComparisonService(db)
    return {"data": service.plant_ranking(filters, order=order, limit=limit)["items"]}


@router.get("/shift-comparison", response_model=ApiResponse[list[ShiftComparisonItem]])
def shift_comparison(
    filters: Filters = Depends(scoped_filters), db: Session = Depends(get_db), _ctx: AuthContext = Depends(_require_overview)
) -> ApiResponse[list[ShiftComparisonItem]]:
    service = DashboardComparisonService(db)
    return {"data": service.shift_comparison(filters)["items"]}


@router.get("/foreman-ranking", response_model=ApiResponse[list[ForemanRankingItem]])
def foreman_ranking(
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(10, ge=1, le=100),
    filters: Filters = Depends(scoped_filters),
    db: Session = Depends(get_db),
    _ctx: AuthContext = Depends(_require_overview),
) -> ApiResponse[list[ForemanRankingItem]]:
    service = DashboardForemanService(db)
    return {"data": service.foreman_ranking(filters, order=order, limit=limit)["items"]}


@router.get("/foreman-trend-ranking", response_model=ApiResponse[list[ForemanTrendRankingItem]])
def foreman_trend_ranking(
    direction: str = Query("improving", pattern="^(improving|declining)$"),
    limit: int = Query(5, ge=1, le=100),
    filters: Filters = Depends(scoped_filters),
    db: Session = Depends(get_db),
    _ctx: AuthContext = Depends(_require_overview),
) -> ApiResponse[list[ForemanTrendRankingItem]]:
    previous_filters = _previous_period_filters(filters)
    service = DashboardForemanService(db)
    return {"data": service.foreman_trend_ranking(filters, previous_filters, direction=direction, limit=limit)["items"]}


@router.get("/performance-distribution", response_model=ApiResponse[PerformanceDistributionResponse])
def performance_distribution(
    filters: Filters = Depends(scoped_filters), db: Session = Depends(get_db), _ctx: AuthContext = Depends(_require_overview)
) -> ApiResponse[PerformanceDistributionResponse]:
    service = DashboardForemanService(db)
    return {"data": service.performance_distribution(filters)}


@router.get("/performance-leaders", response_model=ApiResponse[PerformanceLeadersResponse])
def performance_leaders(
    db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_overview)
) -> ApiResponse[PerformanceLeadersResponse]:
    service = PerformanceLeadersService(db)
    return {"data": service.leaders(ctx.plant_ids)}


@router.get("/snapshot", response_model=ApiResponse[DashboardSnapshot])
def snapshot(
    foreman_ranking_limit: int = Query(5, ge=1, le=100),
    foreman_trend_limit: int = Query(5, ge=1, le=100),
    filters: Filters = Depends(scoped_filters),
    db: Session = Depends(get_db),
    _ctx: AuthContext = Depends(_require_overview),
) -> ApiResponse[DashboardSnapshot]:
    previous_filters = _previous_period_filters(filters)
    service = DashboardOverviewService(db)
    data = service.snapshot(
        filters, previous_filters,
        foreman_ranking_limit=foreman_ranking_limit, foreman_trend_limit=foreman_trend_limit,
    )
    return {"data": data}
