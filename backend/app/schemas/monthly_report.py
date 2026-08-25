from __future__ import annotations

from typing import Literal
from uuid import UUID

from app.schemas.base import CamelModel
from app.schemas.common_refs import IdName, PerformanceLevel


class MonthlyReportComparison(CamelModel):
    value: float
    diff: float
    diff_pct: float | None
    status: Literal["above", "at", "below"]
    is_favorable: bool


class MonthlyReportKpiEntry(CamelModel):
    kpi_id: UUID
    code: str
    name: str
    unit: str
    weight: float
    success_direction_higher: bool
    has_data: bool
    record_count: int
    actual: float | None
    score: float | None
    level: PerformanceLevel | None
    outstanding_performance: bool
    vs_personal_target: MonthlyReportComparison | None
    vs_factory_average: MonthlyReportComparison | None


class MonthlyReportNote(CamelModel):
    kpi_code: str
    name: str
    text: str
    manager_prompt: str | None = None


class MonthlyReportPreviousMonthKpi(CamelModel):
    code: str
    name: str
    diff: float
    is_improvement: bool


class MonthlyReportForemanRef(CamelModel):
    id: UUID
    employee_number: str
    full_name: str
    hire_date: str


class MonthlyReportPeriod(CamelModel):
    year: int
    month: int
    label: str
    date_from: str
    date_to: str


class MonthlyReportOrg(CamelModel):
    factory_name: str | None
    plants: list[IdName]
    chief_name: str | None


class MonthlyReportOrgHistoryEntry(CamelModel):
    date_from: str
    date_to: str
    factory_name: str | None
    plants: list[IdName]
    chief_name: str | None


class MonthlyReportKpiCount(CamelModel):
    total: int
    above_or_at_target: int
    below_target: int
    critical: int


class MonthlyReportOverall(CamelModel):
    score: float
    operational_score: float
    contribution_bonus: float
    level: PerformanceLevel
    kpi_count: MonthlyReportKpiCount


class MonthlyReportCongratulations(CamelModel):
    shown: bool
    text: str | None
    kpi_codes: list[str]


class MonthlyReportWeeklyPoint(CamelModel):
    bucket: str
    total_score: float
    is_reliable: bool


class MonthlyReportTrend(CamelModel):
    weekly_points: list[MonthlyReportWeeklyPoint]
    shape: Literal["iyileşme", "kötüleşme", "stabil", "dalgalı"] | None
    text: str | None


class MonthlyReportPreviousMonth(CamelModel):
    available: bool
    label: str | None = None
    overall_diff: float | None = None
    per_kpi: list[MonthlyReportPreviousMonthKpi] | None = None


class MonthlyReportData(CamelModel):
    foreman: MonthlyReportForemanRef
    period: MonthlyReportPeriod
    generated_at: str
    org: MonthlyReportOrg | None
    organization_history: list[MonthlyReportOrgHistoryEntry] | None = None
    insufficient_data: bool
    insufficient_data_reason: str | None = None
    overall: MonthlyReportOverall | None
    summary_text: str | None = None
    closing_text: str | None = None
    kpis: list[MonthlyReportKpiEntry] | None = None
    strengths: list[MonthlyReportNote] | None = None
    improvements: list[MonthlyReportNote] | None = None
    critical_attention: list[MonthlyReportNote] | None = None
    congratulations: MonthlyReportCongratulations | None = None
    trend: MonthlyReportTrend | None = None
    previous_month: MonthlyReportPreviousMonth | None = None


class MonthlyReportSummary(CamelModel):
    year: int
    month: int
    generated_at: str
    overall_score: float | None
    overall_level_name: str | None
    is_reliable: bool


class MonthlyReportDetail(MonthlyReportSummary):
    report_data: MonthlyReportData


class MonthlyReportLatest(CamelModel):
    available: bool
    year: int | None = None
    month: int | None = None
    generated_at: str | None = None
    overall_score: float | None = None
    overall_level_name: str | None = None
    is_reliable: bool | None = None
    report_data: MonthlyReportData | None = None


class MonthlyReportAccess(CamelModel):
    url: str
    expires_at: str | None
    requires_auth: bool
