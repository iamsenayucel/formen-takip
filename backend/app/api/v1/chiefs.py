from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.authz_deps import assert_chief_in_scope, require_permission, scoped_filters
from app.core.pagination import cursor_envelope
from app.core.permissions import Permission
from app.db.session import get_db
from app.schemas.authz import AuthContext
from app.schemas.base import ApiResponse, CursorResponse
from app.schemas.chief import (
    ChiefDetail,
    ChiefForemanComparison,
    ChiefForemanItem,
    ChiefListItem,
)
from app.schemas.common import CursorParams, Filters, cursor_params
from app.schemas.dashboard import TrendResponse
from app.schemas.foreman import ForemanKpiItem
from app.services.chief_service import ChiefService

router = APIRouter(prefix="/chiefs", tags=["chiefs"])

_require_performance = require_permission(Permission.PERFORMANCE_VIEW)


@router.get("", response_model=CursorResponse[ChiefListItem])
def list_chiefs(
    search: str | None = Query(None),
    plant_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str = Query("name", pattern="^(name|employee_number|plant|factory|foreman_count|score|level|reliability)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: CursorParams = Depends(cursor_params),
    filters: Filters = Depends(scoped_filters),
    db: Session = Depends(get_db),
    _ctx: AuthContext = Depends(_require_performance),
) -> CursorResponse[ChiefListItem]:
    service = ChiefService(db)
    result = service.get_list(search, plant_id, is_active, sort_by, sort_dir, page, filters)
    return cursor_envelope(result)


@router.get("/{chief_id}", response_model=ApiResponse[ChiefDetail])
def get_chief(
    chief_id: UUID, filters: Filters = Depends(scoped_filters), db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_performance),
) -> ApiResponse[ChiefDetail]:
    assert_chief_in_scope(db, ctx, chief_id)
    service = ChiefService(db)
    return {"data": service.get_detail(chief_id, filters)}


@router.get("/{chief_id}/foremen", response_model=ApiResponse[list[ChiefForemanItem]])
def chief_foremen(
    chief_id: UUID, filters: Filters = Depends(scoped_filters), db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_performance),
) -> ApiResponse[list[ChiefForemanItem]]:
    assert_chief_in_scope(db, ctx, chief_id)
    service = ChiefService(db)
    return {"data": service.get_foremen(chief_id, filters)["items"]}


@router.get("/{chief_id}/kpis", response_model=ApiResponse[list[ForemanKpiItem]])
def chief_kpis(
    chief_id: UUID, filters: Filters = Depends(scoped_filters), db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_performance),
) -> ApiResponse[list[ForemanKpiItem]]:
    assert_chief_in_scope(db, ctx, chief_id)
    service = ChiefService(db)
    return {"data": service.get_kpis(chief_id, filters)["items"]}


@router.get("/{chief_id}/foreman-comparison", response_model=ApiResponse[ChiefForemanComparison])
def chief_foreman_comparison(
    chief_id: UUID, filters: Filters = Depends(scoped_filters), db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_performance),
) -> ApiResponse[ChiefForemanComparison]:
    assert_chief_in_scope(db, ctx, chief_id)
    service = ChiefService(db)
    return {"data": service.get_foreman_comparison(chief_id, filters)}


@router.get("/{chief_id}/trend", response_model=ApiResponse[TrendResponse])
def chief_trend(
    chief_id: UUID,
    granularity: str = Query("day", pattern="^(day|week|month|quarter|year)$"),
    filters: Filters = Depends(scoped_filters),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_performance),
) -> ApiResponse[TrendResponse]:
    assert_chief_in_scope(db, ctx, chief_id)
    service = ChiefService(db)
    return {"data": service.get_trend(chief_id, granularity, filters)}
