from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Float, Integer, Select, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.core.pagination import keyset_after, sort_value_source
from app.models.foreman import Chief, ForemanAssignment
from app.models.organization import Factory, Plant
from app.schemas.common import Filters

TURKISH_COLLATION = "tr-TR-x-icu"

_SORT_VALUE_TYPES: dict[str, Any] = {
    "foreman_count": Integer,
    "score": Float,
    "level": Integer,
    "reliability": Boolean,
}


class ChiefRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, chief_id: UUID) -> Chief | None:
        return self.db.get(Chief, chief_id)

    def build_filtered_query(self, filters: Filters, search: str | None, is_active: bool | None) -> Select:
        query = select(Chief)
        if search:
            query = query.where(
                Chief.first_name.ilike(f"%{search}%")
                | Chief.last_name.ilike(f"%{search}%")
                | Chief.employee_number.ilike(f"%{search}%")
            )
        if is_active is not None:
            query = query.where(Chief.is_active == is_active)
        if filters.chief_ids is not None:
            query = query.where(Chief.id.in_(filters.chief_ids))
        if filters.plant_ids is not None:
            query = query.where(Chief.id.in_(select(Plant.chief_id).where(Plant.id.in_(filters.plant_ids))))
        if filters.factory_ids is not None:
            query = query.where(
                Chief.id.in_(select(Plant.chief_id).where(Plant.factory_id.in_(filters.factory_ids)))
            )

        query = query.where(
            Chief.id.in_(
                select(ForemanAssignment.chief_id).where(
                    ForemanAssignment.start_date <= filters.date_to,
                    (ForemanAssignment.end_date.is_(None)) | (ForemanAssignment.end_date >= filters.date_from),
                )
            )
        )
        return query

    def count(self, filters: Filters, search: str | None, is_active: bool | None) -> int:
        query = self.build_filtered_query(filters, search, is_active)
        return self.db.scalar(select(func.count()).select_from(query.subquery())) or 0

    def list_ids(self, filters: Filters, search: str | None, is_active: bool | None) -> list[UUID]:
        query = self.build_filtered_query(filters, search, is_active).with_only_columns(Chief.id)
        return list(self.db.scalars(query))

    def _first_plant_sequence_expr(self):
        return (
            select(func.min(Plant.sequence_number))
            .where(Plant.chief_id == Chief.id)
            .correlate(Chief)
            .scalar_subquery()
        )

    def _first_plant_factory_code_expr(self):
        return (
            select(Factory.code)
            .select_from(Plant)
            .join(Factory, Factory.id == Plant.factory_id)
            .where(Plant.chief_id == Chief.id)
            .order_by(Plant.sequence_number)
            .limit(1)
            .correlate(Chief)
            .scalar_subquery()
        )

    def list_page(
        self,
        filters: Filters,
        search: str | None,
        is_active: bool | None,
        *,
        sort_by: str,
        sort_dir: str,
        sort_values: dict[UUID, Any] | None,
        cursor_value: Any,
        cursor_id: UUID | None,
        limit: int,
    ) -> list[tuple[Chief, Any]]:
        query = self.build_filtered_query(filters, search, is_active)
        desc = sort_dir == "desc"

        if sort_by == "name":
            expr = func.concat(Chief.first_name, " ", Chief.last_name).collate(TURKISH_COLLATION)
            order_terms = [expr.desc() if desc else expr.asc()]
        elif sort_by == "employee_number":
            expr = Chief.employee_number
            order_terms = [expr.desc() if desc else expr.asc()]
        elif sort_by == "plant":
            expr = self._first_plant_sequence_expr()
            order_terms = [expr.desc().nulls_last()] if desc else [expr.asc().nulls_first()]
        elif sort_by == "factory":
            expr = self._first_plant_factory_code_expr().collate(TURKISH_COLLATION)
            order_terms = [expr.desc().nulls_last()] if desc else [expr.asc().nulls_first()]
        else:
            source = sort_value_source(
                PGUUID(as_uuid=True), _SORT_VALUE_TYPES[sort_by], sort_values or {}, name="chief_sort_values"
            )
            if source is None:
                return []
            query = query.outerjoin(source, source.c.id == Chief.id)
            expr = source.c.sort_value
            order_terms = [expr.desc().nulls_last()] if desc else [expr.asc().nulls_first()]

        if cursor_id is not None:
            query = query.where(keyset_after(expr, sort_dir, cursor_value, Chief.id, cursor_id))

        query = query.add_columns(expr.label("sort_value")).order_by(*order_terms, Chief.id).limit(limit + 1)
        return [(row[0], row.sort_value) for row in self.db.execute(query)]

    def list_active_for_filter_options(
        self, plant_ids: list[UUID] | None, factory_ids: list[UUID] | None
    ) -> list[Chief]:
        query = select(Chief).where(Chief.is_active.is_(True))
        if plant_ids is not None:
            query = query.where(Chief.id.in_(select(Plant.chief_id).where(Plant.id.in_(plant_ids))))
        elif factory_ids is not None:
            query = query.where(Chief.id.in_(select(Plant.chief_id).where(Plant.factory_id.in_(factory_ids))))
        return list(self.db.scalars(query.order_by(Chief.employee_number)))
