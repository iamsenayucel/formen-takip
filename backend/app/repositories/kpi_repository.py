from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.kpi import Kpi


class KpiRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, kpi_id: UUID) -> Kpi | None:
        return self.db.get(Kpi, kpi_id)

    def list_active(self) -> list[Kpi]:
        return list(
            self.db.scalars(select(Kpi).where(Kpi.is_active.is_(True)).order_by(Kpi.display_order))
        )
