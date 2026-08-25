from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_identity
from app.core.errors import ShiftAnalysisNotFoundError
from app.core.pagination import cursor_envelope
from app.db.session import get_db
from app.schemas.base import ApiResponse, CursorResponse
from app.schemas.common import CursorParams, Filters, common_filters, cursor_params
from app.schemas.dashboard import KpiSummaryItem
from app.schemas.plant import (
    ForemanShiftMatrixResponse,
    PlantChiefItem,
    PlantDetail,
    PlantForemanItem,
    PlantListItem,
    PlantShiftItem,
    PlantSummary,
)
from app.services import shift_analysis
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import get_performance_levels, level_to_dict
from app.services.plant_service import PlantService

router = APIRouter(prefix="/plants", tags=["plants"])


@router.get("", response_model=CursorResponse[PlantListItem])
def list_plants(
    search: str | None = Query(None),
    factory_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str = Query("sequence", pattern="^(sequence|name|factory|active_foreman_count|score|level)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: CursorParams = Depends(cursor_params),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_identity),
) -> CursorResponse[PlantListItem]:
    service = PlantService(db)
    result = service.get_list(search, factory_id, is_active, sort_by, sort_dir, page, filters)
    return cursor_envelope(result)


@router.get("/{plant_id}", response_model=ApiResponse[PlantDetail])
def get_plant(plant_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_identity)) -> ApiResponse[PlantDetail]:
    service = PlantService(db)
    return {"data": service.get_detail(plant_id)}


@router.get("/{plant_id}/summary", response_model=ApiResponse[PlantSummary])
def plant_summary(
    plant_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[PlantSummary]:
    service = PlantService(db)
    return {"data": service.get_summary(plant_id, filters)}


@router.get("/{plant_id}/kpis", response_model=ApiResponse[list[KpiSummaryItem]])
def plant_kpis(
    plant_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[list[KpiSummaryItem]]:
    service = PlantService(db)
    return {"data": service.get_kpis(plant_id, filters)["items"]}


@router.get("/{plant_id}/shifts", response_model=ApiResponse[list[PlantShiftItem]])
def plant_shifts(
    plant_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[list[PlantShiftItem]]:
    service = PlantService(db)
    return {"data": service.get_shifts(plant_id, filters)["items"]}


@router.get("/{plant_id}/chiefs", response_model=ApiResponse[list[PlantChiefItem]])
def plant_chiefs(
    plant_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[list[PlantChiefItem]]:
    service = PlantService(db)
    return {"data": service.get_chiefs(plant_id, filters)["items"]}


@router.get("/{plant_id}/foreman-shift-matrix", response_model=ApiResponse[ForemanShiftMatrixResponse])
def plant_foreman_shift_matrix(
    plant_id: UUID,
    kpi_id: UUID = Query(...),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_identity),
) -> ApiResponse[ForemanShiftMatrixResponse]:
    matrix = shift_analysis.build_foreman_shift_matrix(db, filters, plant_id, kpi_id)
    if matrix is None:
        raise ShiftAnalysisNotFoundError("Bu tesis/KPI kombinasyonu için formen-vardiya karşılaştırması yapılacak veri bulunamadı.")

    levels = get_performance_levels(db)

    def cell_dict(cell: shift_analysis.ForemanShiftCell | None) -> dict | None:
        if cell is None:
            return None
        deviation_pct = (
            (cell.avg_actual - cell.avg_target) / abs(cell.avg_target) * 100.0 if cell.avg_target else None
        )
        return {
            "avg_actual": round(cell.avg_actual, 2), "avg_target": round(cell.avg_target, 2),
            "score": round(cell.capped_score, 2), "record_count": cell.record_count,
            "deviation_pct": round(deviation_pct, 1) if deviation_pct is not None else None,
            "level": level_to_dict(resolve_performance_level(cell.capped_score, levels)),
        }

    data = {
        "kpi": {
            "id": str(matrix.kpi_id), "code": matrix.kpi_code, "name": matrix.kpi_name, "unit": matrix.kpi_unit,
            "success_direction_higher": matrix.success_direction_higher,
        },
        "reference_target": round(matrix.reference_target, 2),
        "shifts": [{"id": str(s.id), "code": s.code, "name": s.name} for s in matrix.shifts],
        "rows": [
            {
                "foreman_id": str(row.foreman_id), "full_name": row.name, "employee_number": row.employee_number,
                "cells": {str(shift_id): cell_dict(cell) for shift_id, cell in row.cells.items()},
            }
            for row in matrix.rows
        ],
        "insight": matrix.insight,
    }
    return {"data": data}


@router.get("/{plant_id}/foremen", response_model=CursorResponse[PlantForemanItem])
def plant_foremen(
    plant_id: UUID,
    page: CursorParams = Depends(cursor_params),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_identity),
) -> CursorResponse[PlantForemanItem]:
    service = PlantService(db)
    result = service.get_foremen(plant_id, page, filters)
    return cursor_envelope(result)
