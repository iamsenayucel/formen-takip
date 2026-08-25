from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_identity
from app.core.pagination import cursor_envelope
from app.db.session import get_db
from app.schemas.base import ApiResponse, CursorResponse
from app.schemas.chief import (
    ChiefDetail,
    ChiefForemanComparison,
    ChiefForemanItem,
    ChiefListItem,
)
from app.schemas.common import CursorParams, Filters, common_filters, cursor_params
from app.schemas.dashboard import TrendResponse
from app.schemas.foreman import ForemanKpiItem
from app.services.chief_service import ChiefService

router = APIRouter(prefix="/chiefs", tags=["chiefs"])


@router.get("", response_model=CursorResponse[ChiefListItem])
def list_chiefs(
    search: str | None = Query(None),
    plant_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str = Query("name", pattern="^(name|employee_number|plant|factory|foreman_count|score|level|reliability)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: CursorParams = Depends(cursor_params),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_identity),
) -> CursorResponse[ChiefListItem]:
    service = ChiefService(db)
    result = service.get_list(search, plant_id, is_active, sort_by, sort_dir, page, filters)
    return cursor_envelope(result)


@router.get("/{chief_id}", response_model=ApiResponse[ChiefDetail])
def get_chief(
    chief_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[ChiefDetail]:
    service = ChiefService(db)
    return {"data": service.get_detail(chief_id, filters)}


@router.get("/{chief_id}/foremen", response_model=ApiResponse[list[ChiefForemanItem]])
def chief_foremen(
    chief_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[list[ChiefForemanItem]]:
    service = ChiefService(db)
    return {"data": service.get_foremen(chief_id, filters)["items"]}


@router.get("/{chief_id}/kpis", response_model=ApiResponse[list[ForemanKpiItem]])
def chief_kpis(
    chief_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[list[ForemanKpiItem]]:
    service = ChiefService(db)
    return {"data": service.get_kpis(chief_id, filters)["items"]}


@router.get("/{chief_id}/foreman-comparison", response_model=ApiResponse[ChiefForemanComparison])
def chief_foreman_comparison(
    chief_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[ChiefForemanComparison]:
    service = ChiefService(db)
    return {"data": service.get_foreman_comparison(chief_id, filters)}


@router.get("/{chief_id}/trend", response_model=ApiResponse[TrendResponse])
def chief_trend(
    chief_id: UUID,
    granularity: str = Query("day", pattern="^(day|week|month|quarter|year)$"),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_identity),
) -> ApiResponse[TrendResponse]:
    service = ChiefService(db)
    return {"data": service.get_trend(chief_id, granularity, filters)}
