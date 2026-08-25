from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.common_refs import IdName, PerformanceLevel


class ForemanAssignmentItem(CamelModel):
    plant: IdName
    chief: IdName


class ForemanListItem(CamelModel):
    id: UUID
    employee_number: str
    full_name: str
    is_active: bool
    assignments: list[ForemanAssignmentItem]
    operational_score: float
    contribution_bonus: float
    general_performance_score: float
    is_reliable: bool
    level: PerformanceLevel


class ContributionBonusBreakdownItem(CamelModel):
    work_id: UUID
    title: str
    work_type: str | None
    score: float
    work_date: str


class ForemanDetail(CamelModel):
    id: UUID
    employee_number: str
    full_name: str
    hire_date: str
    is_active: bool
    phone_number: str | None
    email: str | None
    assignments: list[ForemanAssignmentItem]
    operational_score: float
    contribution_bonus: float
    contribution_bonus_breakdown: list[ContributionBonusBreakdownItem]
    general_performance_score: float
    is_reliable: bool
    in_scope: bool
    level: PerformanceLevel
    company_rank: int | None
    company_total: int
    plant_rank: int | None
    plant_total: int


class AgirGitme(CamelModel):
    signed_value: float
    absolute_value: float
    direction: Literal["OVERWEIGHT", "UNDERWEIGHT", "ON_TARGET"]
    ratio_to_target: float | None


class Inkita(CamelModel):
    included_total: float | None
    included_components: list[str]
    excluded_components: list[str]
    note: str


class PlanaUyum(CamelModel):
    avg_attainment_pct: float
    planned_qty: float | None
    actual_qty: float | None
    kg_diff: float | None
    signed_pct_deviation: float | None
    direction: Literal["ABOVE_PLAN", "BELOW_PLAN", "ON_PLAN"]


class CalculationPeriod(CamelModel):
    date_from: str
    date_to: str


class ForemanKpiPlantBreakdown(CamelModel):
    plant_id: UUID
    plant_name: str | None
    actual: float
    target: float
    score: float
    weight: float
    record_count: int


class ForemanKpiItem(CamelModel):
    kpi_id: UUID
    code: str
    name: str
    description: str | None
    unit: str
    avg_target: float | None
    avg_actual: float | None
    avg_raw_score: float
    avg_capped_score: float
    weight: float
    weighted_contribution_sum: float
    record_count: int
    evaluated_plant_count: int = 0
    plants: list[ForemanKpiPlantBreakdown] = Field(default_factory=list)
    calculation_version: int | None
    calculation_period: CalculationPeriod
    data_quality_status: str
    source_system: str
    agir_gitme: AgirGitme | None = None
    inkita: Inkita | None = None
    plana_uyum: PlanaUyum | None = None


class CalculationDetailPlanaUyum(CamelModel):
    planned_qty: float | None
    actual_qty: float | None
    kg_diff: float | None
    signed_pct_deviation: float | None
    status: Literal["ABOVE_PLAN", "BELOW_PLAN", "ON_PLAN"]
    formula_version: int | None


class CalculationDetail(CamelModel):
    performance_date: str
    target_value: float | None
    actual_value: float | None
    unit: str
    calculation_type: str | None
    calculation_rule_parameters: dict[str, Any] | None
    calculation_version: int
    raw_score: float
    capped_score: float
    min_score: float | None
    max_score: float | None
    kpi_weight: float
    weighted_contribution: float
    data_source: str
    source_record_id: str
    plana_uyum: CalculationDetailPlanaUyum | None = None


class AssignmentHistoryItem(CamelModel):
    plant: str | None
    chief: str | None
    shift: str | None
    start_date: str
    end_date: str | None
    is_active: bool


class ForemanContributionSummary(CamelModel):
    total_contributions: int
    smed_count: int
    led_contributions: int
    financial_gain: dict[str, float]
    total_time_saving_minutes: float
    last_contribution_date: str | None
