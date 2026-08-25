from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import ReportNotFoundError
from app.core.pagination import decode_cursor, encode_cursor, filter_signature
from app.models.enums import ReportFormat, ReportStatus
from app.models.report import ReportExport
from app.repositories.report_repository import ReportRepository
from app.schemas.common import CursorParams, Filters
from app.services.audit import record_audit
from app.services.reporting import (
    REPORT_TITLES,
    build_filters_summary,
    build_report_rows,
    render_csv,
    render_pdf,
    render_xlsx,
)

if TYPE_CHECKING:
    from app.schemas.report import ReportGenerateRequest


class ReportService:
    def __init__(self, db: Session, repository: ReportRepository | None = None):
        self.db = db
        self.repository = repository or ReportRepository(db)

    def list_reports(self, page: CursorParams) -> dict:
        filter_sig = filter_signature()
        cursor_value = None
        cursor_id = None
        if page.cursor is not None:
            state = decode_cursor(page.cursor, sort_by="created_at", sort_dir="desc", filter_sig=filter_sig)
            cursor_value = state.sort_value
            cursor_id = UUID(state.id)

        rows = self.repository.list_page(cursor_value=cursor_value, cursor_id=cursor_id, limit=page.limit)
        has_more = len(rows) > page.limit
        page_rows = rows[: page.limit]

        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor(
                sort_by="created_at", sort_dir="desc", filter_sig=filter_sig,
                sort_value=last.created_at, id_=str(last.id),
            )
        return {
            "items": [self._to_dict(e) for e in page_rows],
            "next_cursor": next_cursor, "has_more": has_more,
        }

    def generate_report(self, payload: ReportGenerateRequest, subject: str | None, ip_address: str | None) -> dict:
        filters = self._filters_from_request(payload)
        headers, rows = build_report_rows(self.db, payload.report_type, filters)
        title = REPORT_TITLES[payload.report_type]

        if payload.format == ReportFormat.CSV:
            content = render_csv(headers, rows)
            ext = "csv"
        elif payload.format == ReportFormat.XLSX:
            content = render_xlsx(title, headers, rows)
            ext = "xlsx"
        else:
            content = render_pdf(title, build_filters_summary(self.db, filters), headers, rows)
            ext = "pdf"

        file_name = f"{payload.report_type.value}_{filters.date_from}_{filters.date_to}.{ext}"

        export = ReportExport(
            report_type=payload.report_type, format=payload.format,
            filters_json=payload.model_dump(mode="json", exclude={"report_type", "format"}),
            requested_by_subject=subject,
            file_name=file_name, file_content=content, row_count=len(rows),
            status=ReportStatus.COMPLETED, completed_at=clock.now_utc(),
        )
        self.repository.add(export)
        self.repository.flush()

        record_audit(
            self.db, subject, "report_generated", entity="report_export",
            new_value=file_name, ip_address=ip_address,
        )

        result = {
            "id": str(export.id), "file_name": file_name, "report_type": payload.report_type.value,
            "format": payload.format.value, "row_count": len(rows), "created_at": export.created_at.isoformat(),
        }
        self.db.commit()
        return result

    @staticmethod
    def _filters_from_request(payload: ReportGenerateRequest) -> Filters:
        resolved_to = payload.date_to or clock.today_local()
        resolved_from = payload.date_from or (resolved_to - timedelta(days=30))
        if resolved_from > resolved_to:
            resolved_from, resolved_to = resolved_to, resolved_from
        return Filters(
            date_from=resolved_from, date_to=resolved_to,
            plant_ids=payload.plant_ids, factory_ids=payload.factory_ids,
            chief_ids=payload.chief_ids, shift_ids=payload.shift_ids, kpi_ids=payload.kpi_ids,
        )

    def download_report(self, report_id: UUID, subject: str | None, ip_address: str | None) -> ReportExport:
        export = self.repository.get(report_id)
        if export is None:
            raise ReportNotFoundError("Rapor bulunamadı.")

        record_audit(
            self.db, subject, "report_downloaded", entity="report_export",
            new_value=export.file_name, ip_address=ip_address,
        )
        self.db.commit()
        return export

    @staticmethod
    def _to_dict(export: ReportExport) -> dict:
        return {
            "id": str(export.id), "file_name": export.file_name, "report_type": export.report_type.value,
            "format": export.format.value, "row_count": export.row_count, "status": export.status.value,
            "requested_by": export.requested_by_subject,
            "created_at": export.created_at.isoformat(),
        }
