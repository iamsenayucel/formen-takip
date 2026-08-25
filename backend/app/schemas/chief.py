from __future__ import annotations

from uuid import UUID

from app.schemas.base import CamelModel
from app.schemas.common_refs import IdCodeName, IdName, PerformanceLevel


class ChiefListItem(CamelModel):
    id: UUID
    employee_number: str
    code: str
    full_name: str
    is_active: bool
    plants: list[IdName]
    factory: IdCodeName | None
    foreman_count: int
    total_score: float
    is_reliable: bool
    level: PerformanceLevel


class ChiefDetail(CamelModel):
    id: UUID
    employee_number: str
    code: str
    full_name: str
    hire_date: str
    is_active: bool
    phone_number: str | None
    email: str | None
    plants: list[IdName]
    factory: IdCodeName | None
    foreman_count: int
    total_score: float
    is_reliable: bool
    level: PerformanceLevel
    company_rank: int | None
    company_total: int
    factory_rank: int | None
    factory_total: int


class ChiefForemanItem(CamelModel):
    id: UUID
    employee_number: str | None
    full_name: str | None
    operational_score: float
    contribution_bonus: float
    general_performance_score: float
    is_reliable: bool
    level: PerformanceLevel


class ForemanComparisonKpiMeta(CamelModel):
    kpi_id: UUID
    code: str
    name: str
    unit: str
    decimal_places: int
    weight: float


class ForemanComparisonKpiValue(CamelModel):
    score: float
    actual: float | None
    target: float | None
    record_count: int


class ForemanComparisonItem(CamelModel):
    id: UUID
    employee_number: str | None
    full_name: str | None
    total_score: float
    is_reliable: bool
    level: PerformanceLevel
    kpi_scores: dict[str, ForemanComparisonKpiValue | None]


class ForemanComparisonGroupAverage(CamelModel):
    total_score: float
    kpi_scores: dict[str, float]


class ChiefForemanComparison(CamelModel):
    kpis: list[ForemanComparisonKpiMeta]
    group_average: ForemanComparisonGroupAverage
    foremen: list[ForemanComparisonItem]
