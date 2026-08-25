from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.foreman import Chief
from app.models.organization import Factory, Plant
from app.schemas.common import Filters


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

    def list_active_for_factories(self, factory_ids: list[UUID] | None) -> list[Plant]:
        query = select(Plant).where(Plant.is_active.is_(True))
        if factory_ids is not None:
            query = query.where(Plant.factory_id.in_(factory_ids))
        return list(self.db.scalars(query.order_by(Plant.sequence_number)))

    def list_filtered(
        self, search: str | None, factory_id: UUID | None, is_active: bool | None, filters: Filters
    ) -> list[Plant]:
        query = select(Plant)
        if search:
            query = query.where(Plant.name.ilike(f"%{search}%") | Plant.code.ilike(f"%{search}%"))
        if factory_id:
            query = query.where(Plant.factory_id == factory_id)
        if is_active is not None:
            query = query.where(Plant.is_active == is_active)
        if filters.factory_ids:
            query = query.where(Plant.factory_id.in_(filters.factory_ids))
        if filters.plant_ids:
            query = query.where(Plant.id.in_(filters.plant_ids))
        return list(self.db.scalars(query.order_by(Plant.sequence_number)))

    def plants_by_chief_id(self, chief_id: UUID) -> list[Plant]:
        return list(self.db.scalars(select(Plant).where(Plant.chief_id == chief_id)))

    def plants_grouped_by_chief_id(self) -> dict[UUID, list[Plant]]:
        grouped: dict[UUID, list[Plant]] = {}
        for p in self.db.scalars(select(Plant)):
            grouped.setdefault(p.chief_id, []).append(p)
        return grouped

    def chief_ids_by_factory_id(self, factory_id: UUID) -> set[UUID]:
        return {p.chief_id for p in self.db.scalars(select(Plant).where(Plant.factory_id == factory_id))}
