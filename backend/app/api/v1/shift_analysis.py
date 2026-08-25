from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_identity
from app.core import clock
from app.core.errors import InvalidMonthParameterError, ShiftAnalysisNotFoundError
from app.db.session import get_db
from app.schemas.base import ApiResponse
from app.schemas.common import parse_uuid_list
from app.schemas.shift_analysis import (
    ShiftAnalysisCardsResponse,
    ShiftAnomalyDetail,
    ShiftHeatmapResponse,
)
from app.services import shift_analysis

router = APIRouter(prefix="/shift-analysis", tags=["shift-analysis"])


def _resolve_period(month: str | None) -> tuple[date, date]:
    if month:
        try:
            year_s, month_s = month.split("-")
            month_start = date(int(year_s), int(month_s), 1)
        except (ValueError, TypeError) as exc:
            raise InvalidMonthParameterError("month parametresi 'YYYY-MM' biçiminde olmalıdır.") from exc
        next_month = date(month_start.year + (1 if month_start.month == 12 else 0), (month_start.month % 12) + 1, 1)
        return month_start, next_month - date.resolution
    return shift_analysis.previous_completed_month(clock.today_local())


def _cards_filters(
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    kpi_ids: str | None = Query(None, description="Virgülle ayrılmış KPI ID listesi"),
    shift_ids: str | None = Query(None, description="Virgülle ayrılmış vardiya ID listesi"),
    severity: str | None = Query(None, pattern="^(medium|high)$"),
    month: str | None = Query(None, description="YYYY-MM — belirtilmezse bir önce tamamlanan ay kullanılır"),
) -> dict:
    return {
        "factory_ids": parse_uuid_list(factory_ids),
        "plant_ids": parse_uuid_list(plant_ids),
        "kpi_ids": parse_uuid_list(kpi_ids),
        "shift_ids": parse_uuid_list(shift_ids),
        "severity": severity,
        "month": month,
    }


def _card_to_dict(card: shift_analysis.ShiftAnomalyCard) -> dict:
    def foreman_dict(stat: shift_analysis.ForemanNamedStat) -> dict:
        return {
            "id": str(stat.id), "name": stat.name, "employee_number": stat.employee_number,
            "avg_actual": round(stat.avg_actual, card.kpi_decimal_places), "record_count": stat.record_count,
            "week_count": stat.week_count,
        }

    return {
        "id": f"{card.plant_id}|{card.shift_id}|{card.kpi_id}",
        "plant_id": str(card.plant_id), "plant_name": card.plant_name, "plant_sequence": card.plant_sequence,
        "factory_id": str(card.factory_id), "factory_code": card.factory_code,
        "shift_id": str(card.shift_id), "shift_name": card.shift_name,
        "kpi_id": str(card.kpi_id), "kpi_code": card.kpi_code, "kpi_name": card.kpi_name, "kpi_unit": card.kpi_unit,
        "kpi_decimal_places": card.kpi_decimal_places,
        "success_direction_higher": card.success_direction_higher,
        "severity": card.severity, "title": card.title,
        "better": foreman_dict(card.better), "worse": foreman_dict(card.worse),
        "abs_diff": round(card.abs_diff, card.kpi_decimal_places), "pct_diff": round(card.pct_diff, 1),
        "compared_weeks": card.compared_weeks,
        "period": {
            "month_start": card.month_start.isoformat(), "month_end": card.month_end.isoformat(),
            "label": card.period_label,
        },
    }


def _summary_to_dict(summary: shift_analysis.ShiftAnomalySummary) -> dict:
    return {
        "period": {
            "month_start": summary.month_start.isoformat(), "month_end": summary.month_end.isoformat(),
            "label": summary.period_label,
        },
        "total_anomalies": summary.total,
        "high_count": summary.high_count,
        "medium_count": summary.medium_count,
        "top_plant": (
            {"id": str(summary.top_plant[0]), "name": summary.top_plant[1], "count": summary.top_plant[2]}
            if summary.top_plant else None
        ),
        "top_kpi": (
            {"id": str(summary.top_kpi[0]), "name": summary.top_kpi[1], "count": summary.top_kpi[2]}
            if summary.top_kpi else None
        ),
        "max_pct_diff": round(summary.max_pct_diff, 1) if summary.max_pct_diff is not None else None,
    }


@router.get("/cards", response_model=ApiResponse[ShiftAnalysisCardsResponse])
def get_cards(filters: dict = Depends(_cards_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)) -> ApiResponse[ShiftAnalysisCardsResponse]:
    month_start, month_end = _resolve_period(filters["month"])
    cards = shift_analysis.build_cards(
        db, month_start, month_end,
        plant_ids=filters["plant_ids"], factory_ids=filters["factory_ids"],
        kpi_ids=filters["kpi_ids"], shift_ids=filters["shift_ids"], severity=filters["severity"],
    )
    summary = shift_analysis.build_summary(cards, month_start, month_end)
    return {"data": {"items": [_card_to_dict(c) for c in cards], "summary": _summary_to_dict(summary)}}


def _heatmap_filters(
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    kpi_ids: str | None = Query(None, description="Virgülle ayrılmış KPI ID listesi"),
    month: str | None = Query(None, description="YYYY-MM — belirtilmezse bir önce tamamlanan ay kullanılır"),
) -> dict:
    return {
        "factory_ids": parse_uuid_list(factory_ids),
        "plant_ids": parse_uuid_list(plant_ids),
        "kpi_ids": parse_uuid_list(kpi_ids),
        "month": month,
    }


def _shift_stat_to_dict(stat: shift_analysis.ForemanCellStat | None) -> dict | None:
    if stat is None:
        return None
    return {"avg_actual": round(stat.avg_actual, 2), "record_count": stat.record_count}


def _heatmap_cell_to_dict(cell: shift_analysis.HeatmapCell) -> dict:
    return {
        "plant_id": str(cell.plant_id), "kpi_id": str(cell.kpi_id), "level": cell.level,
        "v1": _shift_stat_to_dict(cell.v1), "v2": _shift_stat_to_dict(cell.v2),
        "abs_diff": round(cell.abs_diff, 2) if cell.abs_diff is not None else None,
        "pct_diff": round(cell.pct_diff, 1) if cell.pct_diff is not None else None,
        "better_shift_id": str(cell.better_shift_id) if cell.better_shift_id else None,
    }


@router.get("/heatmap", response_model=ApiResponse[ShiftHeatmapResponse])
def get_heatmap(filters: dict = Depends(_heatmap_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)) -> ApiResponse[ShiftHeatmapResponse]:
    month_start, month_end = _resolve_period(filters["month"])
    plant_refs, kpi_refs, cells, ordered_shifts = shift_analysis.build_heatmap(
        db, month_start, month_end,
        plant_ids=filters["plant_ids"], factory_ids=filters["factory_ids"], kpi_ids=filters["kpi_ids"],
    )
    summary = shift_analysis.build_heatmap_summary(cells, kpi_refs, month_start, month_end)

    data = {
        "period": {"month_start": month_start.isoformat(), "month_end": month_end.isoformat(), "label": shift_analysis.month_label(month_end)},
        "shifts": [
            {"id": str(s.id), "code": s.code, "name": s.name}
            for s in ordered_shifts
        ],
        "plants": [
            {"id": str(p.id), "name": p.name, "sequence_number": p.sequence_number, "factory_code": p.factory_code}
            for p in plant_refs
        ],
        "kpis": [{"id": str(k.id), "code": k.code, "name": k.name, "unit": k.unit} for k in kpi_refs],
        "cells": [_heatmap_cell_to_dict(c) for c in cells],
        "summary": {
            "anomaly_plant_count": summary.anomaly_plant_count,
            "critical_cell_count": summary.critical_cell_count,
            "priority_plant_count": summary.priority_plant_count,
            "top_kpi": (
                {"id": str(summary.top_kpi[0]), "name": summary.top_kpi[1], "count": summary.top_kpi[2]}
                if summary.top_kpi else None
            ),
        },
    }
    return {"data": data}


@router.get("/detail", response_model=ApiResponse[ShiftAnomalyDetail])
def get_detail(
    plant_id: UUID = Query(...), shift_id: UUID = Query(...), kpi_id: UUID = Query(...),
    month: str | None = Query(None, description="YYYY-MM — belirtilmezse bir önce tamamlanan ay kullanılır"),
    db: Session = Depends(get_db), _=Depends(get_current_identity),
) -> ApiResponse[ShiftAnomalyDetail]:
    month_start, month_end = _resolve_period(month)
    detail = shift_analysis.build_detail(
        db, plant_id=plant_id, shift_id=shift_id, kpi_id=kpi_id, month_start=month_start, month_end=month_end,
    )
    if detail is None:
        raise ShiftAnalysisNotFoundError("Bu tesis/vardiya/KPI kombinasyonu için karşılaştırılabilir veri bulunamadı.")

    def foreman_point_dict(p: shift_analysis.WeeklyForemanPoint) -> dict:
        return {
            "assigned": p.assigned,
            "value": round(p.value, detail.kpi_decimal_places) if p.value is not None else None,
            "day_count": p.day_count,
            "has_sufficient_data": p.has_sufficient_data,
            "shift_id": str(p.shift_id) if p.shift_id else None,
            "shift_name": p.shift_name,
        }

    out = _card_to_dict(detail)
    out["reference_target"] = round(detail.reference_target, detail.kpi_decimal_places)
    out["weekly_comparison"] = [
        {
            "week_index": p.week_index, "week_label": p.week_label,
            "better": foreman_point_dict(p.better), "worse": foreman_point_dict(p.worse),
        }
        for p in detail.weekly_comparison
    ]
    out["cross_kpi_signals"] = [
        {
            "kpi_id": str(s.kpi_id), "kpi_code": s.kpi_code, "kpi_name": s.kpi_name,
            "pct_diff": round(s.pct_diff, 1), "severity": s.severity, "same_foreman_better": s.same_foreman_better,
        }
        for s in detail.cross_kpi_signals
    ]
    out["pattern_headline"] = detail.pattern_headline
    out["pattern_detail"] = detail.pattern_detail
    out["is_recurring_pattern"] = detail.is_recurring_pattern
    return {"data": out}
