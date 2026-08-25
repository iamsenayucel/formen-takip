from __future__ import annotations

from typing import Literal
from uuid import UUID

from app.schemas.base import CamelModel
from app.schemas.common_refs import IdCodeName, IdName, IdNameCount


class ShiftAnalysisPeriod(CamelModel):
    month_start: str
    month_end: str
    label: str


class ShiftAnalysisSummary(CamelModel):
    period: ShiftAnalysisPeriod
    total_anomalies: int
    high_count: int
    medium_count: int
    top_plant: IdNameCount | None
    top_kpi: IdNameCount | None
    max_pct_diff: float | None


class ShiftAnomalyForemanStat(CamelModel):
    id: UUID
    name: str
    employee_number: str
    avg_actual: float
    record_count: int
    week_count: int


class ShiftAnomalyCard(CamelModel):
    id: str
    plant_id: UUID
    plant_name: str
    plant_sequence: int
    factory_id: UUID
    factory_code: str
    shift_id: UUID
    shift_name: str
    kpi_id: UUID
    kpi_code: str
    kpi_name: str
    kpi_unit: str
    kpi_decimal_places: int
    success_direction_higher: bool
    severity: Literal["medium", "high"]
    title: str
    better: ShiftAnomalyForemanStat
    worse: ShiftAnomalyForemanStat
    abs_diff: float
    pct_diff: float
    compared_weeks: int
    period: ShiftAnalysisPeriod


class ShiftAnalysisCardsResponse(CamelModel):
    items: list[ShiftAnomalyCard]
    summary: ShiftAnalysisSummary


class ShiftWeeklyForemanPoint(CamelModel):
    assigned: bool
    value: float | None
    day_count: int
    has_sufficient_data: bool
    shift_id: UUID | None = None
    shift_name: str | None = None


class ShiftWeeklyComparisonPoint(CamelModel):
    week_index: int
    week_label: str
    better: ShiftWeeklyForemanPoint
    worse: ShiftWeeklyForemanPoint


class ShiftAnomalyCrossKpiSignal(CamelModel):
    kpi_id: UUID
    kpi_code: str
    kpi_name: str
    pct_diff: float
    severity: Literal["medium", "high"]
    same_foreman_better: bool


class ShiftAnomalyDetail(ShiftAnomalyCard):
    reference_target: float
    weekly_comparison: list[ShiftWeeklyComparisonPoint]
    cross_kpi_signals: list[ShiftAnomalyCrossKpiSignal]
    pattern_headline: str
    pattern_detail: str
    is_recurring_pattern: bool


class HeatmapShiftPoint(CamelModel):
    avg_actual: float
    record_count: int


class HeatmapCell(CamelModel):
    plant_id: UUID
    kpi_id: UUID
    level: Literal["no_data", "normal", "attention", "significant", "critical"]
    v1: HeatmapShiftPoint | None
    v2: HeatmapShiftPoint | None
    abs_diff: float | None
    pct_diff: float | None
    better_shift_id: UUID | None


class HeatmapPlantRef(CamelModel):
    id: UUID
    name: str
    sequence_number: int
    factory_code: str


class HeatmapKpiRef(CamelModel):
    id: UUID
    code: str
    name: str
    unit: str


class ShiftHeatmapSummary(CamelModel):
    anomaly_plant_count: int
    critical_cell_count: int
    priority_plant_count: int
    top_kpi: IdNameCount | None


class ShiftHeatmapResponse(CamelModel):
    period: ShiftAnalysisPeriod
    shifts: list[IdCodeName]
    plants: list[HeatmapPlantRef]
    kpis: list[HeatmapKpiRef]
    cells: list[HeatmapCell]
    summary: ShiftHeatmapSummary
