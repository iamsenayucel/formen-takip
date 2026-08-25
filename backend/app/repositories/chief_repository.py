from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.foreman import Chief, ForemanAssignment
from app.models.organization import Plant
from app.schemas.common import Filters


class ChiefRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, chief_id: UUID) -> Chief | None:
        return self.db.get(Chief, chief_id)

    def list_in_scope(self, filters: Filters, search: str | None, is_active: bool | None) -> list[Chief]:
        query = select(Chief)
        if search:
            query = query.where(
                Chief.first_name.ilike(f"%{search}%")
                | Chief.last_name.ilike(f"%{search}%")
                | Chief.employee_number.ilike(f"%{search}%")
            )
        if is_active is not None:
            query = query.where(Chief.is_active == is_active)
        if filters.chief_ids:
            query = query.where(Chief.id.in_(filters.chief_ids))
        if filters.plant_ids:
            query = query.where(Chief.id.in_(select(Plant.chief_id).where(Plant.id.in_(filters.plant_ids))))
        if filters.factory_ids:
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
        return list(self.db.scalars(query))

    def list_active_for_filter_options(
        self, plant_ids: list[UUID] | None, factory_ids: list[UUID] | None
    ) -> list[Chief]:
        query = select(Chief).where(Chief.is_active.is_(True))
        if plant_ids is not None:
            query = query.where(Chief.id.in_(select(Plant.chief_id).where(Plant.id.in_(plant_ids))))
        elif factory_ids is not None:
            query = query.where(Chief.id.in_(select(Plant.chief_id).where(Plant.factory_id.in_(factory_ids))))
        return list(self.db.scalars(query.order_by(Chief.employee_number)))
