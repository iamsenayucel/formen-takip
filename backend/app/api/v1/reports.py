from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.authz_deps import require_permission
from app.core.client_ip import get_client_ip
from app.core.pagination import cursor_envelope
from app.core.permissions import Permission
from app.core.rate_limit import rate_limit_report
from app.db.session import get_db
from app.models.enums import ReportFormat
from app.schemas.authz import AuthContext
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

_require_create = require_permission(Permission.REPORTS_CREATE)
_require_download = require_permission(Permission.REPORTS_DOWNLOAD)
_require_outputs = require_permission(Permission.OUTPUTS_VIEW)


def _scope_plant_ids(ctx: AuthContext) -> list[UUID] | None:
    return sorted(ctx.plant_ids, key=str) if ctx.plant_ids is not None else None


@router.post("/generate", status_code=201, response_model=ApiResponse[ReportExportMeta], dependencies=[Depends(rate_limit_report)])
def generate_report(
    payload: ReportGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_create),
) -> ApiResponse[ReportExportMeta]:
    data = ReportService(db).generate_report(
        payload, ctx.subject, get_client_ip(request), plant_ids_scope=_scope_plant_ids(ctx),
    )
    return {"data": data}


@router.get("", response_model=CursorResponse[ReportExportMeta])
def list_reports(
    page: CursorParams = Depends(cursor_params),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_outputs),
) -> CursorResponse[ReportExportMeta]:
    requested_by = ctx.subject if ctx.plant_ids is not None else None
    result = ReportService(db).list_reports(page, requested_by_subject=requested_by)
    return cursor_envelope(result)


@router.get("/{report_id}/download", dependencies=[Depends(rate_limit_report)])
def download_report(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_download),
) -> Response:
    export = ReportService(db).download_report(
        report_id, ctx.subject, get_client_ip(request), plant_ids_scope=_scope_plant_ids(ctx),
    )

    return Response(
        content=export.file_content,
        media_type=_CONTENT_TYPES[export.format],
        headers={"Content-Disposition": f'attachment; filename="{export.file_name}"'},
    )
