from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.models.enums import (
    ContributionRole,
    ContributionStatus,
    ContributionWorkType,
    Currency,
    FinancialGainStatus,
    GainPeriod,
    HighlightedGainMode,
    ImpactLevel,
    OtherGainType,
    RepeatPeriod,
    TimeUnit,
)
from app.schemas.base import CamelModel


class ContributionGainInput(CamelModel):
    gain_type: OtherGainType
    gain_type_other_note: str | None = None
    previous_value: float | None = None
    next_value: float | None = None
    unit: str | None = None
    measurement_period: str | None = None
    description: str | None = None


DATE_RANGE_ERROR = "work_date_end tarihi work_date tarihinden önce olamaz."


def check_date_range(work_date: date | None, work_date_end: date | None) -> None:
    if work_date is not None and work_date_end is not None and work_date_end < work_date:
        raise ValueError(DATE_RANGE_ERROR)


class ContributionWorkCreate(CamelModel):
    title: str = Field(min_length=1, max_length=300)
    status: ContributionStatus = ContributionStatus.DRAFT

    work_type: ContributionWorkType | None = None
    work_type_other_note: str | None = None
    summary: str | None = Field(default=None, max_length=500)
    detailed_description: str | None = None
    problem_description: str | None = None
    solution_description: str | None = None
    result_description: str | None = None

    foreman_ids: list[UUID] = Field(default_factory=list)
    plant_ids: list[UUID] = Field(default_factory=list)
    work_date: date | None = None
    work_date_end: date | None = None
    impact_level: ImpactLevel | None = None

    is_standardized: bool = False
    is_applicable_other_plants: bool = False
    is_permanent_solution: bool = False
    work_instruction_updated: bool = False

    financial_gain_status: FinancialGainStatus = FinancialGainStatus.NOT_CALCULATED
    gain_amount: float | None = Field(default=None, ge=0)
    currency: Currency | None = None
    gain_period: GainPeriod | None = None
    calculation_method: str | None = None

    previous_duration: float | None = Field(default=None, ge=0)
    new_duration: float | None = Field(default=None, ge=0)
    duration_unit: TimeUnit | None = None
    repeat_period: RepeatPeriod | None = None
    repeat_count: float | None = Field(default=None, ge=0)
    per_occurrence_saving: float | None = Field(default=None, ge=0)
    monthly_total_saving_minutes: float | None = Field(default=None, ge=0)

    gains: list[ContributionGainInput] = Field(default_factory=list)

    highlighted_gain_mode: HighlightedGainMode = HighlightedGainMode.AUTO
    highlighted_gain_ref: str | None = None

    @model_validator(mode="after")
    def _validate_date_range(self):
        check_date_range(self.work_date, self.work_date_end)
        return self


class ContributionWorkUpdate(CamelModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    status: ContributionStatus | None = None

    work_type: ContributionWorkType | None = None
    work_type_other_note: str | None = None
    summary: str | None = Field(default=None, max_length=500)
    detailed_description: str | None = None
    problem_description: str | None = None
    solution_description: str | None = None
    result_description: str | None = None

    foreman_ids: list[UUID] | None = None
    plant_ids: list[UUID] | None = None
    work_date: date | None = None
    work_date_end: date | None = None
    impact_level: ImpactLevel | None = None

    is_standardized: bool | None = None
    is_applicable_other_plants: bool | None = None
    is_permanent_solution: bool | None = None
    work_instruction_updated: bool | None = None

    financial_gain_status: FinancialGainStatus | None = None
    gain_amount: float | None = Field(default=None, ge=0)
    currency: Currency | None = None
    gain_period: GainPeriod | None = None
    calculation_method: str | None = None

    previous_duration: float | None = Field(default=None, ge=0)
    new_duration: float | None = Field(default=None, ge=0)
    duration_unit: TimeUnit | None = None
    repeat_period: RepeatPeriod | None = None
    repeat_count: float | None = Field(default=None, ge=0)
    per_occurrence_saving: float | None = Field(default=None, ge=0)
    monthly_total_saving_minutes: float | None = Field(default=None, ge=0)

    gains: list[ContributionGainInput] | None = None

    highlighted_gain_mode: HighlightedGainMode | None = None
    highlighted_gain_ref: str | None = None

    @model_validator(mode="after")
    def _validate_date_range(self):
        if self.model_fields_set >= {"work_date", "work_date_end"}:
            check_date_range(self.work_date, self.work_date_end)
        return self


class ContributionForemanRef(CamelModel):
    id: UUID
    name: str
    employee_number: str
    role: ContributionRole


class ContributionPlantRef(CamelModel):
    id: UUID
    name: str
    code: str
    factory_id: UUID
    factory_name: str
    factory_code: str


class ContributionGain(CamelModel):
    id: UUID
    gain_type: OtherGainType
    gain_type_label: str
    gain_type_other_note: str | None
    previous_value: float | None
    next_value: float | None
    change_amount: float | None
    change_percent: float | None
    is_improvement: bool | None
    unit: str | None
    measurement_period: str | None
    description: str | None


class ContributionHighlightedGain(CamelModel):
    source: str
    label: str
    value: float
    unit: str | None


class ContributionBeforeAfter(CamelModel):
    metric_label: str
    before: str
    after: str
    change: str
    is_improvement: bool


class ContributionScoreCriterion(CamelModel):
    label: str
    points: float
    detail: str


class ContributionWorkItem(CamelModel):
    id: UUID
    title: str
    status: ContributionStatus
    work_type: ContributionWorkType | None
    work_type_label: str | None
    work_type_other_note: str | None
    summary: str | None
    detailed_description: str | None
    problem_description: str | None
    solution_description: str | None
    result_description: str | None
    foremen: list[ContributionForemanRef]
    plants: list[ContributionPlantRef]
    work_date: str | None
    work_date_end: str | None
    impact_level: ImpactLevel | None
    created_by: str | None
    published_at: str | None
    is_standardized: bool
    is_applicable_other_plants: bool
    is_permanent_solution: bool
    work_instruction_updated: bool
    financial_gain_status: FinancialGainStatus
    gain_amount: float | None
    currency: Currency | None
    gain_period: GainPeriod | None
    calculation_method: str | None
    previous_duration: float | None
    new_duration: float | None
    duration_unit: TimeUnit | None
    per_occurrence_saving: float | None
    repeat_period: RepeatPeriod | None
    repeat_count: float | None
    monthly_total_saving_minutes: float | None
    gains: list[ContributionGain]
    highlighted_gain_mode: HighlightedGainMode
    highlighted_gain_ref: str | None
    highlighted_gain: ContributionHighlightedGain | None
    before_after: ContributionBeforeAfter | None
    badges: list[str]
    contribution_score: float | None
    contribution_score_label: str | None
    contribution_score_breakdown: list[ContributionScoreCriterion]
    created_at: str
    updated_at: str


class ContributionByPlantEntry(CamelModel):
    name: str
    count: int


class ContributionByWorkTypeEntry(CamelModel):
    label: str
    count: int


class ContributionTopForemanEntry(CamelModel):
    id: UUID
    name: str
    count: int


class ContributionSummary(CamelModel):
    total_works: int
    added_this_month: int
    total_gain_amount: float
    total_monthly_time_saving_minutes: float
    by_plant: list[ContributionByPlantEntry]
    by_work_type: list[ContributionByWorkTypeEntry]
    top_foremen: list[ContributionTopForemanEntry]
    applicable_other_plants_count: int
    standardized_ratio: float
