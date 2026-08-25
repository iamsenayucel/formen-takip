from __future__ import annotations

from typing import Generic, TypeVar

from app.schemas.base import CamelModel
from app.schemas.common_refs import EntityRef, PerformanceLevel

T = TypeVar("T")


class ItemsList(CamelModel, Generic[T]):
    items: list[T]


class WeakestKpiRef(CamelModel):
    id: str
    name: str
    avg_score: float


class DashboardSummary(CamelModel):
    total_plants: int
    active_plants: int
    total_active_foremen: int
    avg_company_score: float
    foremen_above_target: int
    foremen_below_target: int
    foremen_critical: int
    foremen_successful: int
    foremen_outstanding: int
    best_plant: EntityRef | None
    worst_plant: EntityRef | None
    best_shift: EntityRef | None
    worst_shift: EntityRef | None
    best_foreman: EntityRef | None
    weakest_kpi: WeakestKpiRef | None
    plants_with_missing_data: int
    last_sync_at: str | None
    data_source: str


class TrendPoint(CamelModel):
    date: str
    total_score: float
    is_reliable: bool


class TrendResponse(CamelModel):
    granularity: str
    points: list[TrendPoint]


class KpiSummaryItem(CamelModel):
    kpi_id: str
    code: str
    name: str
    unit: str
    avg_score: float
    avg_target: float | None
    avg_actual: float | None
    record_count: int | None = None


class PlantRankingItem(CamelModel):
    plant_id: str
    code: str
    name: str
    total_score: float
    is_reliable: bool
    level: PerformanceLevel


class ShiftComparisonItem(CamelModel):
    shift_id: str
    code: str | None
    name: str | None
    total_score: float
    record_count: int
    level: PerformanceLevel


class ForemanRankingItem(CamelModel):
    foreman_id: str
    employee_number: str
    full_name: str
    operational_score: float
    contribution_bonus: float
    general_performance_score: float
    is_reliable: bool
    level: PerformanceLevel


class ForemanTrendRankingItem(CamelModel):
    foreman_id: str
    employee_number: str
    full_name: str
    operational_score: float
    previous_operational_score: float
    delta: float
    is_reliable: bool
    level: PerformanceLevel


class DistributionItem(PerformanceLevel):
    count: int


class PerformanceDistributionResponse(CamelModel):
    items: list[DistributionItem]
    outstanding_count: int


class PerformanceLeaderEntry(CamelModel):
    foreman_id: str
    full_name: str
    general_performance_score: float


class PerformanceYearLeaderEntry(PerformanceLeaderEntry):
    monthly_wins: int


class LastCalculatedMonth(CamelModel):
    year: int
    month: int
    label: str


class PerformanceLeadersResponse(CamelModel):
    year: int
    last_calculated_month: LastCalculatedMonth
    monthly_leader: PerformanceLeaderEntry | None
    yearly_leader: PerformanceYearLeaderEntry | None


class ForemanRankingGroup(CamelModel):
    top: ItemsList[ForemanRankingItem]
    bottom: ItemsList[ForemanRankingItem]


class ForemanTrendRankingGroup(CamelModel):
    improving: ItemsList[ForemanTrendRankingItem]
    declining: ItemsList[ForemanTrendRankingItem]


class DashboardSnapshot(CamelModel):
    summary: DashboardSummary
    kpi_summary: ItemsList[KpiSummaryItem]
    shift_comparison: ItemsList[ShiftComparisonItem]
    foreman_ranking: ForemanRankingGroup
    foreman_trend_ranking: ForemanTrendRankingGroup
    performance_distribution: PerformanceDistributionResponse
