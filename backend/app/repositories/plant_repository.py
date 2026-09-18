from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Float, Integer, Select, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.core.pagination import keyset_after, sort_value_source
from app.models.foreman import Chief
from app.models.organization import Factory, Plant
from app.schemas.common import Filters

TURKISH_COLLATION = "tr-TR-x-icu"

_SORT_VALUE_TYPES: dict[str, Any] = {
    "active_foreman_count": Integer,
    "score": Float,
    "level": Integer,
}


class PlantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, plant_id: UUID) -> Plant | None:
        return self.db.get(Plant, plant_id)

    def get_factory(self, factory_id: UUID) -> Factory | None:
        return self.db.get(Factory, factory_id)

    def chiefs_by_ids(self, chief_ids: list[UUID]) -> list[Chief]:
        return list(
            self.db.scalars(select(Chief).where(Chief.id.in_(chief_ids)).order_by(Chief.employee_number))
        )

    def all_factories_by_id(self) -> dict[UUID, Factory]:
        return {f.id: f for f in self.db.scalars(select(Factory))}

    def list_active_factories(self) -> list[Factory]:
        return list(
            self.db.scalars(select(Factory).where(Factory.is_active.is_(True)).order_by(Factory.code))
        )

    def list_active_for_factories(
        self, factory_ids: list[UUID] | None, plant_ids: list[UUID] | None = None
    ) -> list[Plant]:
        query = select(Plant).where(Plant.is_active.is_(True))
        if factory_ids is not None:
            query = query.where(Plant.factory_id.in_(factory_ids))
        if plant_ids is not None:
            query = query.where(Plant.id.in_(plant_ids))
        return list(self.db.scalars(query.order_by(Plant.sequence_number)))

    def build_filtered_query(
        self, search: str | None, factory_id: UUID | None, is_active: bool | None, filters: Filters
    ) -> Select:
        query = select(Plant)
        if search:
            query = query.where(Plant.name.ilike(f"%{search}%") | Plant.code.ilike(f"%{search}%"))
        if factory_id:
            query = query.where(Plant.factory_id == factory_id)
        if is_active is not None:
            query = query.where(Plant.is_active == is_active)
        if filters.factory_ids is not None:
            query = query.where(Plant.factory_id.in_(filters.factory_ids))
        if filters.plant_ids is not None:
            query = query.where(Plant.id.in_(filters.plant_ids))
        return query

    def count(
        self, search: str | None, factory_id: UUID | None, is_active: bool | None, filters: Filters
    ) -> int:
        query = self.build_filtered_query(search, factory_id, is_active, filters)
        return self.db.scalar(select(func.count()).select_from(query.subquery())) or 0

    def list_ids(
        self, search: str | None, factory_id: UUID | None, is_active: bool | None, filters: Filters
    ) -> list[UUID]:
        query = self.build_filtered_query(search, factory_id, is_active, filters).with_only_columns(Plant.id)
        return list(self.db.scalars(query))

    def list_page(
        self,
        search: str | None,
        factory_id: UUID | None,
        is_active: bool | None,
        filters: Filters,
        *,
        sort_by: str,
        sort_dir: str,
        sort_values: dict[UUID, Any] | None,
        cursor_value: Any,
        cursor_id: UUID | None,
        limit: int,
    ) -> list[tuple[Plant, Any]]:
        query = self.build_filtered_query(search, factory_id, is_active, filters)
        desc = sort_dir == "desc"

        if sort_by == "sequence":
            expr = Plant.sequence_number
            order_terms = [expr.desc() if desc else expr.asc()]
        elif sort_by == "name":
            expr = Plant.name.collate(TURKISH_COLLATION)
            order_terms = [expr.desc() if desc else expr.asc()]
        elif sort_by == "factory":
            query = query.outerjoin(Factory, Factory.id == Plant.factory_id)
            expr = Factory.name.collate(TURKISH_COLLATION)
            order_terms = [expr.desc().nulls_last()] if desc else [expr.asc().nulls_first()]
        else:
            source = sort_value_source(
                PGUUID(as_uuid=True), _SORT_VALUE_TYPES[sort_by], sort_values or {}, name="plant_sort_values"
            )
            if source is None:
                return []
            query = query.outerjoin(source, source.c.id == Plant.id)
            expr = source.c.sort_value
            order_terms = [expr.desc().nulls_last()] if desc else [expr.asc().nulls_first()]

        if cursor_id is not None:
            query = query.where(keyset_after(expr, sort_dir, cursor_value, Plant.id, cursor_id))

        query = query.add_columns(expr.label("sort_value")).order_by(*order_terms, Plant.id).limit(limit + 1)
        return [(row[0], row.sort_value) for row in self.db.execute(query)]

    def plants_by_chief_id(self, chief_id: UUID) -> list[Plant]:
        return list(self.db.scalars(select(Plant).where(Plant.chief_id == chief_id)))

    def plants_grouped_by_chief_id(self) -> dict[UUID, list[Plant]]:
        grouped: dict[UUID, list[Plant]] = {}
        for p in self.db.scalars(select(Plant)):
            grouped.setdefault(p.chief_id, []).append(p)
        return grouped

    def chief_ids_by_factory_id(self, factory_id: UUID) -> set[UUID]:
        return {p.chief_id for p in self.db.scalars(select(Plant).where(Plant.factory_id == factory_id))}
