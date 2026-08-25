from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.kpi import Kpi, KpiCalculationRule
from app.models.organization import Plant, Shift
from app.schemas.common import parse_uuid_list
from app.services import assignment_resolver


@dataclass
class ForemanListQueryParams:
    search: str | None = None
    ids: str | None = None
    is_active: bool | None = None
    factory_ids: list[UUID] | None = None
    plant_ids: list[UUID] | None = None
    chief_ids: list[UUID] | None = None
    date_from: date | None = None
    date_to: date | None = None


class ForemanRepository:
    """Foreman Directory/Profile için persistence erişimi.

    Yalnızca sorgu ve lookup işlemlerini kapsar — salt okunur. Business karar
    vermez (skor birleştirme, rank, level, sıralama, sayfalama) ve hiçbir
    yazma/transaction işlemi (add/delete/flush/commit) içermez.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get(self, foreman_id: UUID) -> Foreman | None:
        return self.db.get(Foreman, foreman_id)

    def list_query(self, params: ForemanListQueryParams) -> Select:
        query = select(Foreman)
        if params.search:
            query = query.where(
                Foreman.first_name.ilike(f"%{params.search}%")
                | Foreman.last_name.ilike(f"%{params.search}%")
                | Foreman.employee_number.ilike(f"%{params.search}%")
            )
        if params.ids:
            query = query.where(Foreman.id.in_(parse_uuid_list(params.ids) or []))
        if params.is_active is not None:
            query = query.where(Foreman.is_active == params.is_active)

        if params.factory_ids or params.plant_ids or params.chief_ids:
            assignment_query = select(ForemanAssignment.foreman_id).where(
                ForemanAssignment.start_date <= params.date_to,
                (ForemanAssignment.end_date.is_(None)) | (ForemanAssignment.end_date >= params.date_from),
            )
            if params.factory_ids:
                assignment_query = assignment_query.where(
                    ForemanAssignment.plant_id.in_(select(Plant.id).where(Plant.factory_id.in_(params.factory_ids)))
                )
            if params.plant_ids:
                assignment_query = assignment_query.where(ForemanAssignment.plant_id.in_(params.plant_ids))
            if params.chief_ids:
                assignment_query = assignment_query.where(ForemanAssignment.chief_id.in_(params.chief_ids))
            query = query.where(Foreman.id.in_(assignment_query))

        return query

    def list(self, params: ForemanListQueryParams) -> list[Foreman]:
        return list(self.db.scalars(self.list_query(params)))

    def batch_assignments_for_foremen(self, foreman_ids: list[UUID]) -> dict[UUID, list[ForemanAssignment]]:
        result: dict[UUID, list[ForemanAssignment]] = {}
        if not foreman_ids:
            return result
        for a in self.db.scalars(select(ForemanAssignment).where(ForemanAssignment.foreman_id.in_(foreman_ids))):
            result.setdefault(a.foreman_id, []).append(a)
        return result

    def all_foremen_by_id(self) -> dict[UUID, Foreman]:
        return {f.id: f for f in self.db.scalars(select(Foreman))}

    def all_plants_by_id(self) -> dict[UUID, Plant]:
        return {p.id: p for p in self.db.scalars(select(Plant))}

    def all_chiefs_by_id(self) -> dict[UUID, Chief]:
        return {c.id: c for c in self.db.scalars(select(Chief))}

    def all_shifts_by_id(self) -> dict[UUID, Shift]:
        return {s.id: s for s in self.db.scalars(select(Shift))}

    def assignments_as_of(self, foreman_id: UUID, as_of: date) -> list[ForemanAssignment]:
        return list(self.db.scalars(assignment_resolver.assignments_as_of(as_of, foreman_id=foreman_id)))

    def plants_by_ids(self, ids: set[UUID]) -> dict[UUID, Plant]:
        return {p.id: p for p in self.db.scalars(select(Plant).where(Plant.id.in_(ids)))}

    def chiefs_by_ids(self, ids: set[UUID]) -> dict[UUID, Chief]:
        return {c.id: c for c in self.db.scalars(select(Chief).where(Chief.id.in_(ids)))}

    def foremen_by_ids(self, ids: list[UUID]) -> dict[UUID, Foreman]:
        if not ids:
            return {}
        return {f.id: f for f in self.db.scalars(select(Foreman).where(Foreman.id.in_(ids)))}

    # ------------------------------------------------------------------
    # KPI / Performance lookups (Slice 2)
    # ------------------------------------------------------------------

    def all_kpis_by_id(self) -> dict[UUID, Kpi]:
        return {k.id: k for k in self.db.scalars(select(Kpi))}

    def plant_names_by_id(self) -> dict[UUID, str]:
        return {p.id: p.name for p in self.db.scalars(select(Plant))}

    def get_kpi(self, kpi_id: UUID) -> Kpi | None:
        return self.db.get(Kpi, kpi_id)

    def get_calculation_rule(self, rule_id: UUID) -> KpiCalculationRule | None:
        return self.db.get(KpiCalculationRule, rule_id)

    # ------------------------------------------------------------------
    # Assignment history (Slice 3)
    # ------------------------------------------------------------------

    def assignment_history(self, foreman_id: UUID) -> list[ForemanAssignment]:
        return list(
            self.db.scalars(
                select(ForemanAssignment)
                .where(ForemanAssignment.foreman_id == foreman_id)
                .order_by(ForemanAssignment.start_date)
            )
        )

    def shifts_by_ids(self, ids: set[UUID]) -> dict[UUID, Shift]:
        return {s.id: s for s in self.db.scalars(select(Shift).where(Shift.id.in_(ids)))}
