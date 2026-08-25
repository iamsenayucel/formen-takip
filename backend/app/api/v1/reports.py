from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_identity
from app.core.pagination import cursor_envelope
from app.core.rate_limit import rate_limit_report
from app.db.session import get_db
from app.models.enums import ReportFormat
from app.schemas.auth import Identity
from app.schemas.base import ApiResponse, CursorResponse
from app.schemas.common import CursorParams, cursor_params
from app.schemas.report import ReportExportMeta, ReportGenerateRequest
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

_CONTENT_TYPES = {
    ReportFormat.CSV: "text/csv",
    ReportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ReportFormat.PDF: "application/pdf",
}


@router.post("/generate", status_code=201, response_model=ApiResponse[ReportExportMeta], dependencies=[Depends(rate_limit_report)])
def generate_report(
    payload: ReportGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_identity),
) -> ApiResponse[ReportExportMeta]:
    data = ReportService(db).generate_report(
        payload, current_user.subject, request.client.host if request.client else None,
    )
    return {"data": data}


@router.get("", response_model=CursorResponse[ReportExportMeta])
def list_reports(
    page: CursorParams = Depends(cursor_params),
    db: Session = Depends(get_db),
    _=Depends(get_current_identity),
) -> CursorResponse[ReportExportMeta]:
    result = ReportService(db).list_reports(page)
    return cursor_envelope(result)


@router.get("/{report_id}/download", dependencies=[Depends(rate_limit_report)])
def download_report(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Identity = Depends(get_current_identity),
) -> Response:
    export = ReportService(db).download_report(
        report_id, current_user.subject, request.client.host if request.client else None,
    )

    return Response(
        content=export.file_content,
        media_type=_CONTENT_TYPES[export.format],
        headers={"Content-Disposition": f'attachment; filename="{export.file_name}"'},
    )
