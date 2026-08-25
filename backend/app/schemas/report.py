from __future__ import annotations

from datetime import date
from uuid import UUID

from app.models.enums import ReportFormat, ReportType
from app.schemas.base import CamelModel


class ReportExportMeta(CamelModel):
    id: UUID
    file_name: str
    report_type: str
    format: str
    row_count: int
    status: str | None = None
    requested_by: str | None = None
    created_at: str


class ReportGenerateRequest(CamelModel):
    report_type: ReportType
    format: ReportFormat
    date_from: date | None = None
    date_to: date | None = None
    plant_ids: list[UUID] | None = None
    factory_ids: list[UUID] | None = None
    chief_ids: list[UUID] | None = None
    shift_ids: list[UUID] | None = None
    kpi_ids: list[UUID] | None = None
