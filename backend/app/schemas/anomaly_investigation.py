from __future__ import annotations

from typing import Literal
from uuid import UUID

from app.schemas.base import CamelModel


class ForemanRef(CamelModel):
    id: UUID
    name: str
    employee_number: str


class ForemanKpiTrendPoint(CamelModel):
    period_label: str
    avg_actual: float | None
    has_data: bool


class ResponsibleForemanPrimary(ForemanRef):
    day_count: int | None = None
    total_days: int | None = None


class ResponsibleForemanOther(ForemanRef):
    day_count: int | None = None


class ResponsibleForeman(CamelModel):
    resolved: bool
    shift_specific: bool
    reason: str | None
    note: str | None
    primary: ResponsibleForemanPrimary | None
    others: list[ResponsibleForemanOther]
    kpi_trend: list[ForemanKpiTrendPoint]


class BaselinePeriod(CamelModel):
    start: str
    end: str
    days: int


class BaselineComparison(CamelModel):
    available: bool
    reason: str | None = None
    baseline_period: BaselinePeriod | None = None
    current_period: BaselinePeriod | None = None
    baseline_avg: float | None = None
    current_avg: float | None = None
    abs_change: float | None = None
    pct_change: float | None = None
    direction: Literal["improved", "worsened", "unchanged"] | None = None


class RelatedKpiChange(CamelModel):
    kpi: str
    kpi_code: str
    baseline_value: float
    current_value: float
    abs_change: float
    change_percent: float
    direction: Literal["increase", "decrease"]
    performance_direction: Literal["improved", "worsened"] | None
    sparkline: list[float]


class DowntimeCategory(CamelModel):
    category: str
    total_minutes: float
    occurrence_count: int


class DowntimeBreakdown(CamelModel):
    plant_name: str
    shift_name: str
    period_days: int
    total_downtime_minutes: float
    total_downtime_count: int
    categories: list[DowntimeCategory]
    top_reasons: list[str]
    longest_single_event_minutes: float
    previous_period_total_minutes: float
    other_shifts_average_minutes: float | None


class InvestigationImpact(CamelModel):
    additional_downtime_minutes: float | None
    additional_downtime_note: str | None
    production_loss_note: str
    cost_note: str


class SimilarCase(CamelModel):
    anomaly_id: UUID
    anomaly_code: str
    title: str
    plant_name: str | None
    kpi_name: str | None
    anomaly_type_label: str
    similarity_reason: str
    detected_at: str
    resolution_status: Literal["resolved", "open"]
    verified_root_cause: str | None
    action_taken: str | None
    action_result: str | None
    kpi_value_before: float
    kpi_value_after: float | None


class ShiftComparisonEntry(CamelModel):
    shift_id: UUID
    code: str
    name: str
    value: float | None
    is_anomaly_shift: bool


class FactoryComparisonEntry(CamelModel):
    code: str
    name: str
    value: float | None
    is_anomaly_factory: bool


class PreviousMonthPeriod(CamelModel):
    start: str
    end: str


class PreviousMonthComparison(CamelModel):
    available: bool
    label: str | None = None
    period: PreviousMonthPeriod | None = None
    value: float | None = None
    current_value: float | None = None
    change_percent: float | None = None


class AnomalyInvestigation(CamelModel):
    responsible_foreman: ResponsibleForeman
    baseline_comparison: BaselineComparison
    related_kpi_changes: list[RelatedKpiChange]
    downtime_breakdown: DowntimeBreakdown | None
    impact: InvestigationImpact
    similar_cases: list[SimilarCase]
    shift_comparison: list[ShiftComparisonEntry]
    factory_comparison: list[FactoryComparisonEntry]
    previous_month: PreviousMonthComparison
    comparison_target_value: float | None
