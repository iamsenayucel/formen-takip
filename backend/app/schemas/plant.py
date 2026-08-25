from __future__ import annotations

from uuid import UUID

from app.schemas.base import CamelModel
from app.schemas.common_refs import IdCodeName, IdName, PerformanceLevel


class PlantGroupSupervisorRef(CamelModel):
    id: UUID
    name: str


class PlantGroupForemanRef(CamelModel):
    id: UUID
    name: str


class PlantGroupRef(CamelModel):
    id: UUID
    code: str
    score: float
    supervisor: PlantGroupSupervisorRef
    foremen: list[PlantGroupForemanRef]


class PlantListItem(CamelModel):
    id: UUID
    code: str
    name: str
    sequence_number: int
    factory: IdCodeName | None
    is_active: bool
    total_score: float
    level: PerformanceLevel
    active_foreman_count: int
    record_count: int
    group: PlantGroupRef | None


class PlantDetail(CamelModel):
    id: UUID
    code: str
    name: str
    sequence_number: int
    factory: IdCodeName | None
    description: str | None
    is_active: bool
    sap_plant_code: str | None


class WeakestStrongestKpiRef(CamelModel):
    id: UUID
    name: str
    avg_score: float


class PlantSummary(CamelModel):
    plant_id: UUID
    total_score: float
    level: PerformanceLevel
    foremen_average_score: float
    active_foreman_count: int
    critical_foreman_count: int
    strongest_kpi: WeakestStrongestKpiRef | None
    weakest_kpi: WeakestStrongestKpiRef | None


class PlantForemanItem(CamelModel):
    foreman_id: UUID
    employee_number: str | None
    full_name: str | None
    operational_score: float
    contribution_bonus: float
    general_performance_score: float
    level: PerformanceLevel


class PlantShiftItem(CamelModel):
    shift_id: UUID
    code: str
    name: str
    total_score: float
    level: PerformanceLevel


class PlantChiefItem(CamelModel):
    id: UUID
    employee_number: str
    full_name: str
    foreman_count: int
    total_score: float
    level: PerformanceLevel


class ForemanShiftMatrixKpiRef(CamelModel):
    id: UUID
    code: str
    name: str
    unit: str
    success_direction_higher: bool


class ForemanShiftMatrixCell(CamelModel):
    avg_actual: float
    avg_target: float
    score: float
    record_count: int
    deviation_pct: float | None
    level: PerformanceLevel


class ForemanShiftMatrixRow(CamelModel):
    foreman_id: UUID
    full_name: str
    employee_number: str
    cells: dict[str, ForemanShiftMatrixCell | None]


class ForemanShiftMatrixResponse(CamelModel):
    kpi: ForemanShiftMatrixKpiRef
    reference_target: float
    shifts: list[IdCodeName]
    rows: list[ForemanShiftMatrixRow]
    insight: str
