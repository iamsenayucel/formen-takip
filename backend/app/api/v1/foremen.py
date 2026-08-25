from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_identity
from app.core.pagination import cursor_envelope
from app.core.rate_limit import rate_limit_pdf
from app.db.session import get_db
from app.schemas.auth import Identity
from app.schemas.base import ApiResponse, CursorResponse
from app.schemas.common import CursorParams, Filters, common_filters, cursor_params
from app.schemas.dashboard import TrendResponse
from app.schemas.foreman import (
    AssignmentHistoryItem,
    CalculationDetail,
    ForemanContributionSummary,
    ForemanDetail,
    ForemanKpiItem,
    ForemanListItem,
)
from app.schemas.monthly_report import (
    MonthlyReportAccess,
    MonthlyReportDetail,
    MonthlyReportLatest,
    MonthlyReportSummary,
)
from app.services.audit import record_audit
from app.services.contribution_work_service import ContributionWorkService
from app.services.foreman_monthly_report_service import ForemanMonthlyReportService
from app.services.foreman_service import ForemanService

router = APIRouter(prefix="/foremen", tags=["foremen"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=CursorResponse[ForemanListItem])
def list_foremen(
    search: str | None = Query(None),
    ids: str | None = Query(None, description="Virgülle ayrılmış formen ID listesi (isim çözümleme için)"),
    plant_id: UUID | None = Query(None),
    chief_id: UUID | None = Query(None),
    shift_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    level: str | None = Query(None),
    outstanding: bool | None = Query(None),
    sort_by: str = Query("name", pattern="^(name|employee_number|plant|chief|score|level|reliability)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: CursorParams = Depends(cursor_params),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_identity),
) -> CursorResponse[ForemanListItem]:
    service = ForemanService(db)
    result = service.list_foremen(
        search=search, ids=ids, plant_id=plant_id, chief_id=chief_id, shift_id=shift_id,
        is_active=is_active, level=level, outstanding=outstanding, sort_by=sort_by, sort_dir=sort_dir,
        page=page, filters=filters,
    )
    return cursor_envelope(result)


@router.get("/{foreman_id}", response_model=ApiResponse[ForemanDetail])
def get_foreman(
    foreman_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[ForemanDetail]:
    service = ForemanService(db)
    return {"data": service.get_foreman(foreman_id, filters)}


@router.get("/{foreman_id}/kpis", response_model=ApiResponse[list[ForemanKpiItem]])
def foreman_kpis(
    foreman_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[list[ForemanKpiItem]]:
    service = ForemanService(db)
    return {"data": service.get_foreman_kpis(foreman_id, filters)["items"]}


@router.get("/{foreman_id}/kpis/{kpi_id}/calculation-detail", response_model=ApiResponse[CalculationDetail])
def foreman_kpi_calculation_detail(foreman_id: UUID, kpi_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_identity)) -> ApiResponse[CalculationDetail]:
    service = ForemanService(db)
    return {"data": service.get_foreman_kpi_calculation_detail(foreman_id, kpi_id)}


@router.get("/{foreman_id}/trend", response_model=ApiResponse[TrendResponse])
def foreman_trend(
    foreman_id: UUID,
    granularity: str = Query("day", pattern="^(day|week|month|quarter|year)$"),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_identity),
) -> ApiResponse[TrendResponse]:
    service = ForemanService(db)
    return {"data": service.get_foreman_trend(foreman_id, granularity, filters)}


@router.get("/{foreman_id}/assignment-history", response_model=ApiResponse[list[AssignmentHistoryItem]])
def assignment_history(foreman_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_identity)) -> ApiResponse[list[AssignmentHistoryItem]]:
    service = ForemanService(db)
    return {"data": service.get_assignment_history(foreman_id)["items"]}


@router.get("/{foreman_id}/contribution-summary", response_model=ApiResponse[ForemanContributionSummary])
def foreman_contribution_summary(
    foreman_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[ForemanContributionSummary]:
    service = ContributionWorkService(db)
    return {"data": service.foreman_summary(foreman_id)}


@router.get("/{foreman_id}/monthly-reports", response_model=ApiResponse[list[MonthlyReportSummary]])
def foreman_monthly_reports(foreman_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_identity)) -> ApiResponse[list[MonthlyReportSummary]]:
    service = ForemanMonthlyReportService(db)
    return {"data": service.list_reports(foreman_id)["items"]}


@router.get("/{foreman_id}/monthly-reports/latest", response_model=ApiResponse[MonthlyReportLatest])
def foreman_monthly_report_latest(foreman_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_identity)) -> ApiResponse[MonthlyReportLatest]:
    service = ForemanMonthlyReportService(db)
    return {"data": service.latest_report(foreman_id)}


@router.get("/{foreman_id}/monthly-reports/{year}/{month}", response_model=ApiResponse[MonthlyReportDetail])
def foreman_monthly_report_detail(
    foreman_id: UUID, year: int, month: int, db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[MonthlyReportDetail]:
    service = ForemanMonthlyReportService(db)
    return {"data": service.report_detail(foreman_id, year, month)}


@router.get("/{foreman_id}/monthly-reports/{year}/{month}/pdf", dependencies=[Depends(rate_limit_pdf)])
def foreman_monthly_report_pdf(
    foreman_id: UUID, year: int, month: int, request: Request,
    db: Session = Depends(get_db), current_user: Identity = Depends(get_current_identity),
) -> Response:
    service = ForemanMonthlyReportService(db)
    pdf_bytes, file_name = service.pdf_bytes(
        foreman_id, year, month,
        subject=current_user.subject, ip_address=_client_ip(request), record_audit=record_audit,
    )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/{foreman_id}/monthly-reports/{year}/{month}/access", response_model=ApiResponse[MonthlyReportAccess])
def foreman_monthly_report_access(
    foreman_id: UUID, year: int, month: int, request: Request,
    db: Session = Depends(get_db), current_user: Identity = Depends(get_current_identity),
) -> ApiResponse[MonthlyReportAccess]:
    service = ForemanMonthlyReportService(db)
    data = service.access(
        foreman_id, year, month,
        subject=current_user.subject, ip_address=_client_ip(request), record_audit=record_audit,
    )
    return {"data": data}
