from __future__ import annotations

from typing import Literal
from uuid import UUID

from app.schemas.base import CamelModel
from app.schemas.common_refs import EntityRef, PerformanceLevel


class KpiListItem(CamelModel):
    id: UUID
    code: str
    name: str
    description: str
    unit: str
    calculation_type: str
    weight: float
    default_target_value: float
    is_critical: bool


class KpiDetail(CamelModel):
    id: UUID
    code: str
    name: str
    description: str
    unit: str
    calculation_type: str
    success_direction_higher: bool
    default_target_value: float
    min_score: float
    max_score: float
    weight: float
    aggregation_method: str
    is_critical: bool


class KpiForemanValueItem(CamelModel):
    foreman_id: UUID
    full_name: str | None
    avg_actual: float
    avg_target: float
    avg_score: float
    record_count: int
    tier: Literal["better", "near", "worse"]
    level: PerformanceLevel | None


class KpiAnalysisKpiRef(CamelModel):
    id: UUID
    code: str
    name: str
    unit: str
    decimal_places: int


class KpiAnalysisShiftRef(CamelModel):
    id: UUID
    name: str
    score: float


class KpiAnalysisTrendPoint(CamelModel):
    date: str
    score: float


class KpiAnalysis(CamelModel):
    kpi: KpiAnalysisKpiRef
    company_avg_score: float
    company_avg_target: float | None
    company_avg_actual: float | None
    best_plants: list[EntityRef]
    worst_plants: list[EntityRef]
    shift_comparison: list[KpiAnalysisShiftRef]
    best_foremen: list[EntityRef]
    worst_foremen: list[EntityRef]
    foreman_values: list[KpiForemanValueItem]
    trend: list[KpiAnalysisTrendPoint]
