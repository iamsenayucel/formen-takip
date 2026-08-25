from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Shift


class ShiftRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_active(self) -> list[Shift]:
        return list(
            self.db.scalars(select(Shift).where(Shift.is_active.is_(True)).order_by(Shift.sequence))
        )
