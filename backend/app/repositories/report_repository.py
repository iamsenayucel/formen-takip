from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.pagination import keyset_after
from app.models.report import ReportExport


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, report_id: UUID) -> ReportExport | None:
        return self.db.get(ReportExport, report_id)

    def add(self, export: ReportExport) -> None:
        self.db.add(export)

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, export: ReportExport) -> None:
        self.db.refresh(export)

    def list_page(
        self, *, cursor_value, cursor_id: UUID | None, limit: int, requested_by_subject: str | None = None,
    ) -> list[ReportExport]:
        query = select(ReportExport)
        if requested_by_subject is not None:
            query = query.where(ReportExport.requested_by_subject == requested_by_subject)
        if cursor_id is not None:
            query = query.where(keyset_after(ReportExport.created_at, "desc", cursor_value, ReportExport.id, cursor_id))
        query = query.order_by(ReportExport.created_at.desc(), ReportExport.id).limit(limit + 1)
        return list(self.db.scalars(query))
