from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AnalysisMode, AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus, AnomalyType
from app.schemas.base import CamelModel

PERIOD_RANGE_ERROR = "period_end tarihi period_start tarihinden önce olamaz."
AFFECTED_DAYS_ERROR = "affected_days, total_days değerini aşamaz."


class AnomalyCreate(BaseModel):
    code: str
    title: str
    description: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    status: AnomalyStatus = AnomalyStatus.NEW
    analysis_status: AnomalyAnalysisStatus = AnomalyAnalysisStatus.NOT_ANALYZED

    detected_at: datetime
    plant_id: UUID
    shift_id: UUID | None = None
    kpi_id: UUID

    period_start: date
    period_end: date

    observed_value: float
    expected_value: float
    unit: str
    deviation_percent: float
    ml_confidence: float = Field(ge=0, le=1)

    affected_days: int | None = Field(default=None, ge=0)
    total_days: int | None = Field(default=None, ge=0)

    comparison: dict = Field(default_factory=dict)
    related_signals: list = Field(default_factory=list)
    evidence: list = Field(default_factory=list)
    foreman_ids: list = Field(default_factory=list)

    data_quality_status: str = "valid"
    data_quality_warnings: list = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_period_range(self):
        if self.period_end < self.period_start:
            raise ValueError(PERIOD_RANGE_ERROR)
        return self

    @model_validator(mode="after")
    def _validate_affected_days(self):
        if self.affected_days is not None and self.total_days is not None and self.affected_days > self.total_days:
            raise ValueError(AFFECTED_DAYS_ERROR)
        return self


class AnomalyStatusUpdate(CamelModel):
    status: AnomalyStatus


class AnalyzeRequest(CamelModel):
    mode: AnalysisMode | None = None
    force_refresh: bool = False


class AnomalyListItem(CamelModel):
    id: UUID
    code: str
    title: str
    factory_code: str | None
    factory_name: str | None
    plant_id: UUID
    plant_name: str | None
    shift_id: UUID | None
    shift_name: str | None
    kpi_id: UUID
    kpi_code: str | None
    kpi_name: str | None
    anomaly_type: str
    anomaly_type_label: str
    detected_at: str
    period_start: str
    period_end: str
    deviation_percent: float
    ml_confidence: float
    severity: AnomalySeverity
    severity_label: str
    status: AnomalyStatus
    status_label: str
    analysis_status: AnomalyAnalysisStatus
    analysis_status_label: str


class AnomalyEvidenceItem(CamelModel):
    type: str
    label: str
    value: float
    unit: str


class AnomalyRelatedSignal(CamelModel):
    kpi: str
    kpi_code: str
    value: float
    change_percent: float
    direction: Literal["increase", "decrease"]


class AnomalyDailyPoint(CamelModel):
    date: str
    value: float


class AnomalyKpiDefinition(CamelModel):
    name: str | None
    description: str | None
    desired_direction: Literal["high", "low"] | None
    warning_threshold: float | None
    critical_threshold: float | None


class AnalysisSourceRef(CamelModel):
    tool_call_id: str
    tool_name: str


class AnalysisVerifiedFinding(CamelModel):
    finding_id: str | None = None
    finding: str
    evidence: str
    source_refs: list[AnalysisSourceRef]


class AnalysisPossibleCause(CamelModel):
    cause: str
    confidence: Literal["low", "medium", "high"]
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    source_refs: list[AnalysisSourceRef]
    verification_required: str


class AnalysisRecommendedInvestigation(CamelModel):
    step: str
    responsible_unit: str
    priority: Literal["low", "medium", "high", "critical"]
    expected_output: str


class AnalysisImmediateAction(CamelModel):
    action: str
    responsible_unit: str
    priority: Literal["low", "medium", "high", "critical"]
    timeframe: str
    expected_impact: str
    requires_approval: bool


class AnalysisMediumTermAction(CamelModel):
    action: str
    responsible_unit: str
    expected_impact: str


class AnalysisToolUsedRef(CamelModel):
    tool_name: str
    tool_call_id: str
    purpose: str


class AnalysisDataScope(CamelModel):
    start_date: str
    end_date: str
    record_count: int
    data_quality_status: str


class AnalysisResultResponse(CamelModel):
    model_config = ConfigDict(extra="allow")

    # Eski analiz satırları daha dar bir JSON şemasıyla saklanmış olabilir.
    # Okuma sözleşmesinin tam ve tipli kalması için eksik tarihsel alanlar güvenli
    # varsayılanlarla tamamlanır.
    executive_summary: str = ""
    verified_findings: list[AnalysisVerifiedFinding] = Field(default_factory=list)
    possible_causes: list[AnalysisPossibleCause] = Field(default_factory=list)
    recommended_investigations: list[AnalysisRecommendedInvestigation] = Field(default_factory=list)
    immediate_actions: list[AnalysisImmediateAction] = Field(default_factory=list)
    medium_term_actions: list[AnalysisMediumTermAction] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    analysis_confidence: float = 0.0
    requires_human_review: bool = True
    tools_used: list[AnalysisToolUsedRef] = Field(default_factory=list)
    data_scope: AnalysisDataScope | None = None
    analysis_limitations: list[str] = Field(default_factory=list)
    disclaimer: str = ""


class AnomalyAnalysisRecord(CamelModel):
    id: UUID
    code: str
    mode: AnalysisMode
    status: AnomalyAnalysisStatus
    status_label: str
    is_demo: bool
    model: str
    result: AnalysisResultResponse | None
    investigation_plan: list[str] | None
    tool_call_count: int
    error_code: str | None
    error_message: str | None
    started_at: str
    completed_at: str | None


class AnomalyToolCallItem(CamelModel):
    id: UUID
    code: str
    step_number: int
    tool_name: str
    tool_label: str
    arguments: dict
    # Tool çalıştırma sonuçları success/error/timeout olarak ayrılmadan önce tarihsel
    # satırlarda ``completed`` kullanılıyordu; okumalar geriye uyumlu kalmalıdır.
    status: Literal["success", "completed", "error", "timeout"]
    result: dict | None
    record_count: int | None
    error_code: str | None
    error_message: str | None
    started_at: str
    completed_at: str | None
    duration_ms: float | None


class AnomalyDetail(AnomalyListItem):
    description: str
    observed_value: float
    expected_value: float
    target_value: float | None
    unit: str
    affected_days: int | None
    total_days: int | None
    comparison: dict[str, float]
    related_signals: list[AnomalyRelatedSignal]
    evidence: list[AnomalyEvidenceItem]
    foreman_codes: list[str]
    data_quality_status: str
    data_quality_warnings: list[str]
    daily_history: list[AnomalyDailyPoint]
    kpi_definition: AnomalyKpiDefinition
    latest_analysis: AnomalyAnalysisRecord | None
    analysis_history: list[AnomalyAnalysisRecord]


class AnomalySummary(CamelModel):
    total_active: int
    critical_count: int
    high_count: int
    pending_analysis_count: int
    opened_last_7_days: int
    resolved_count: int
